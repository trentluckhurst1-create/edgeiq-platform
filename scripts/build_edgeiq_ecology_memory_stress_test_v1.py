from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"

RESILIENCE = PUBLIC / "edgeiq_ecology_memory_resilience_v1.csv"
CONFIDENCE = PUBLIC / "edgeiq_ecology_memory_confidence_v1.csv"
PRESSURE = PUBLIC / "edgeiq_ecology_memory_pressure_v1.csv"
MATURITY = PUBLIC / "edgeiq_ecology_memory_maturity_v1.csv"
DECAY = PUBLIC / "edgeiq_ecology_memory_decay_v1.csv"

OUT_STRESS = PUBLIC / "edgeiq_ecology_memory_stress_test_v1.csv"
OUT_SCENARIOS = PUBLIC / "edgeiq_ecology_memory_stress_scenarios_v1.csv"
OUT_SUMMARY = PUBLIC / "edgeiq_ecology_memory_stress_summary_v1.csv"

ENGINE_VERSION = "EDGEIQ_ECOLOGY_MEMORY_STRESS_TEST_ENGINE_V1"

SCENARIOS = [
    {
        "scenario_id": "BASELINE",
        "scenario_name": "Current observed state",
        "pressure_add": 0,
        "confidence_penalty": 0,
        "maturity_penalty": 0,
        "resilience_penalty": 0,
        "mutation_events_add": 0,
        "drift_events_add": 0,
        "governance_penalty": 0,
    },
    {
        "scenario_id": "MUTATION_ESCALATION",
        "scenario_name": "Mutation pressure escalates",
        "pressure_add": 20,
        "confidence_penalty": 12,
        "maturity_penalty": 10,
        "resilience_penalty": 18,
        "mutation_events_add": 2,
        "drift_events_add": 0,
        "governance_penalty": 0,
    },
    {
        "scenario_id": "DRIFT_ACCELERATION",
        "scenario_name": "Drift velocity accelerates",
        "pressure_add": 25,
        "confidence_penalty": 10,
        "maturity_penalty": 8,
        "resilience_penalty": 20,
        "mutation_events_add": 0,
        "drift_events_add": 2,
        "governance_penalty": 0,
    },
    {
        "scenario_id": "GOVERNANCE_DETERIORATION",
        "scenario_name": "Governance status weakens",
        "pressure_add": 15,
        "confidence_penalty": 15,
        "maturity_penalty": 15,
        "resilience_penalty": 25,
        "mutation_events_add": 0,
        "drift_events_add": 0,
        "governance_penalty": 25,
    },
    {
        "scenario_id": "COMBINED_STRESS",
        "scenario_name": "Mutation + drift + governance stress",
        "pressure_add": 35,
        "confidence_penalty": 25,
        "maturity_penalty": 25,
        "resilience_penalty": 40,
        "mutation_events_add": 3,
        "drift_events_add": 3,
        "governance_penalty": 30,
    },
]

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def read_csv(path: Path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

def clean(v):
    return str(v or "").strip()

def safe_float(v):
    try:
        return float(v)
    except Exception:
        return 0.0

def survival_band(score):
    if score >= 75:
        return "SURVIVES_STRESS"
    if score >= 50:
        return "PARTIAL_SURVIVAL"
    if score >= 25:
        return "FRAGILE_UNDER_STRESS"
    return "FAILS_STRESS"

def stress_action(band):
    if band == "SURVIVES_STRESS":
        return "maintain_observation"
    if band == "PARTIAL_SURVIVAL":
        return "increase_snapshot_depth"
    if band == "FRAGILE_UNDER_STRESS":
        return "hold_for_more_evidence"
    return "block_promotion_and_continue_research_only"

def main():
    print("=" * 88)
    print("EDGEIQ ECOLOGY MEMORY STRESS TEST ENGINE V1")
    print("=" * 88)

    resilience_rows = read_csv(RESILIENCE)
    confidence_rows = read_csv(CONFIDENCE)
    pressure_rows = read_csv(PRESSURE)
    maturity_rows = read_csv(MATURITY)
    decay_rows = read_csv(DECAY)

    confidence_by_key = {clean(r.get("structure_key")): r for r in confidence_rows}
    pressure_by_key = {clean(r.get("structure_key")): r for r in pressure_rows}
    maturity_by_key = {clean(r.get("structure_key")): r for r in maturity_rows}
    decay_by_key = {clean(r.get("structure_key")): r for r in decay_rows}

    stress_rows = []
    scenario_rows = []

    for scenario in SCENARIOS:
        scenario_rows.append({
            "scenario_id": scenario["scenario_id"],
            "scenario_name": scenario["scenario_name"],
            "pressure_add": scenario["pressure_add"],
            "confidence_penalty": scenario["confidence_penalty"],
            "maturity_penalty": scenario["maturity_penalty"],
            "resilience_penalty": scenario["resilience_penalty"],
            "mutation_events_add": scenario["mutation_events_add"],
            "drift_events_add": scenario["drift_events_add"],
            "governance_penalty": scenario["governance_penalty"],
            "research_boundary": "OFFLINE_RESEARCH_ONLY",
            "live_modelling_yes": 0,
            "live_execution_yes": 0,
            "engine_version": ENGINE_VERSION,
        })

    for row in resilience_rows:
        key = clean(row.get("structure_key"))
        track = clean(row.get("track"))
        shape = clean(row.get("dominant_transition_shape"))

        confidence = confidence_by_key.get(key, {})
        pressure = pressure_by_key.get(key, {})
        maturity = maturity_by_key.get(key, {})
        decay = decay_by_key.get(key, {})

        base_resilience = safe_float(row.get("resilience_score"))
        base_confidence = safe_float(confidence.get("confidence_score"))
        base_pressure = safe_float(pressure.get("pressure_score"))
        base_maturity = safe_float(maturity.get("maturity_score"))
        stability_ratio = safe_float(row.get("stability_ratio"))

        for scenario in SCENARIOS:
            stressed_pressure = min(100, base_pressure + scenario["pressure_add"])
            stressed_confidence = max(0, base_confidence - scenario["confidence_penalty"])
            stressed_maturity = max(0, base_maturity - scenario["maturity_penalty"])
            stressed_resilience = max(0, base_resilience - scenario["resilience_penalty"] - scenario["governance_penalty"])

            survival_score = round(
                max(
                    0,
                    min(
                        100,
                        (stressed_resilience * 0.40)
                        + (stressed_confidence * 0.25)
                        + (stressed_maturity * 0.20)
                        + (stability_ratio * 15)
                        - (stressed_pressure * 0.20),
                    ),
                ),
                2,
            )

            band = survival_band(survival_score)

            stress_rows.append({
                "structure_key": key,
                "track": track,
                "dominant_transition_shape": shape,
                "scenario_id": scenario["scenario_id"],
                "scenario_name": scenario["scenario_name"],
                "base_pressure_score": base_pressure,
                "stressed_pressure_score": stressed_pressure,
                "base_confidence_score": base_confidence,
                "stressed_confidence_score": stressed_confidence,
                "base_maturity_score": base_maturity,
                "stressed_maturity_score": stressed_maturity,
                "base_resilience_score": base_resilience,
                "stressed_resilience_score": stressed_resilience,
                "stress_survival_score": survival_score,
                "stress_survival_band": band,
                "recommended_action": stress_action(band),
                "research_boundary": "OFFLINE_RESEARCH_ONLY",
                "live_modelling_yes": 0,
                "live_execution_yes": 0,
                "engine_version": ENGINE_VERSION,
                "timestamp_utc": now_iso(),
            })

    survives = sum(1 for r in stress_rows if r["stress_survival_band"] == "SURVIVES_STRESS")
    partial = sum(1 for r in stress_rows if r["stress_survival_band"] == "PARTIAL_SURVIVAL")
    fragile = sum(1 for r in stress_rows if r["stress_survival_band"] == "FRAGILE_UNDER_STRESS")
    fails = sum(1 for r in stress_rows if r["stress_survival_band"] == "FAILS_STRESS")

    if fails:
        health = "STRESS_FAILURE_PRESENT"
    elif fragile:
        health = "FRAGILE_UNDER_STRESS"
    elif partial:
        health = "PARTIAL_STRESS_SURVIVAL"
    else:
        health = "STRESS_RESILIENT"

    summary_rows = [
        {"metric": "structures_tested", "value": len(resilience_rows)},
        {"metric": "scenarios_tested", "value": len(SCENARIOS)},
        {"metric": "stress_rows", "value": len(stress_rows)},
        {"metric": "survives_stress_rows", "value": survives},
        {"metric": "partial_survival_rows", "value": partial},
        {"metric": "fragile_under_stress_rows", "value": fragile},
        {"metric": "fails_stress_rows", "value": fails},
        {"metric": "overall_stress_health", "value": health},
        {"metric": "research_boundary", "value": "OFFLINE_RESEARCH_ONLY"},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
    ]

    write_csv(
        OUT_STRESS,
        stress_rows,
        [
            "structure_key",
            "track",
            "dominant_transition_shape",
            "scenario_id",
            "scenario_name",
            "base_pressure_score",
            "stressed_pressure_score",
            "base_confidence_score",
            "stressed_confidence_score",
            "base_maturity_score",
            "stressed_maturity_score",
            "base_resilience_score",
            "stressed_resilience_score",
            "stress_survival_score",
            "stress_survival_band",
            "recommended_action",
            "research_boundary",
            "live_modelling_yes",
            "live_execution_yes",
            "engine_version",
            "timestamp_utc",
        ],
    )

    write_csv(
        OUT_SCENARIOS,
        scenario_rows,
        [
            "scenario_id",
            "scenario_name",
            "pressure_add",
            "confidence_penalty",
            "maturity_penalty",
            "resilience_penalty",
            "mutation_events_add",
            "drift_events_add",
            "governance_penalty",
            "research_boundary",
            "live_modelling_yes",
            "live_execution_yes",
            "engine_version",
        ],
    )

    write_csv(OUT_SUMMARY, summary_rows, ["metric", "value"])

    for row in summary_rows:
        print(f"{row['metric']}: {row['value']}")

    print("=" * 88)
    print("STRESS TEST RESULTS")
    print("=" * 88)

    for row in stress_rows:
        print(
            f"{row['track']} {row['scenario_id']} -> "
            f"{row['stress_survival_band']} "
            f"score={row['stress_survival_score']}"
        )

if __name__ == "__main__":
    main()
