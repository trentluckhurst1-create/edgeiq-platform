from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"

STRESS = PUBLIC / "edgeiq_ecology_memory_stress_test_v1.csv"
RESILIENCE = PUBLIC / "edgeiq_ecology_memory_resilience_v1.csv"
CONFIDENCE = PUBLIC / "edgeiq_ecology_memory_confidence_v1.csv"
MATURITY = PUBLIC / "edgeiq_ecology_memory_maturity_v1.csv"

OUT_RECOVERY = PUBLIC / "edgeiq_ecology_memory_recovery_v1.csv"
OUT_ALERTS = PUBLIC / "edgeiq_ecology_memory_recovery_alerts_v1.csv"
OUT_SUMMARY = PUBLIC / "edgeiq_ecology_memory_recovery_summary_v1.csv"

ENGINE_VERSION = "EDGEIQ_ECOLOGY_MEMORY_RECOVERY_ENGINE_V1"

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

def upper(v):
    return clean(v).upper()

def safe_float(v):
    try:
        return float(v)
    except Exception:
        return 0.0

def recovery_band(score):
    if score >= 75:
        return "HIGH_RECOVERY_CAPACITY"
    if score >= 55:
        return "MODERATE_RECOVERY_CAPACITY"
    if score >= 35:
        return "FRAGILE_RECOVERY_CAPACITY"
    return "LOW_RECOVERY_CAPACITY"

def recovery_action(band):
    if band == "HIGH_RECOVERY_CAPACITY":
        return "continue_longitudinal_monitoring"
    if band == "MODERATE_RECOVERY_CAPACITY":
        return "increase_snapshot_density"
    if band == "FRAGILE_RECOVERY_CAPACITY":
        return "hold_under_research_observation"
    return "prevent_promotion_and_continue_research"

def main():
    print("=" * 88)
    print("EDGEIQ ECOLOGY MEMORY RECOVERY ENGINE V1")
    print("=" * 88)

    stress_rows = read_csv(STRESS)
    resilience_rows = read_csv(RESILIENCE)
    confidence_rows = read_csv(CONFIDENCE)
    maturity_rows = read_csv(MATURITY)

    resilience_by_key = {
        clean(r.get("structure_key")): r
        for r in resilience_rows
    }

    confidence_by_key = {
        clean(r.get("structure_key")): r
        for r in confidence_rows
    }

    maturity_by_key = {
        clean(r.get("structure_key")): r
        for r in maturity_rows
    }

    grouped_stress = {}

    for row in stress_rows:
        key = clean(row.get("structure_key"))

        grouped_stress.setdefault(key, []).append(row)

    recovery_rows = []
    alert_rows = []

    for key, rows in grouped_stress.items():
        base_row = rows[0]

        track = clean(base_row.get("track"))
        shape = clean(base_row.get("dominant_transition_shape"))

        resilience = resilience_by_key.get(key, {})
        confidence = confidence_by_key.get(key, {})
        maturity = maturity_by_key.get(key, {})

        resilience_score = safe_float(resilience.get("resilience_score"))
        confidence_score = safe_float(confidence.get("confidence_score"))
        maturity_score = safe_float(maturity.get("maturity_score"))

        survival_scores = [
            safe_float(r.get("stress_survival_score"))
            for r in rows
        ]

        average_survival = (
            sum(survival_scores) / len(survival_scores)
            if survival_scores
            else 0
        )

        best_survival = max(survival_scores) if survival_scores else 0
        worst_survival = min(survival_scores) if survival_scores else 0

        survives_count = sum(
            1 for r in rows
            if upper(r.get("stress_survival_band")) == "SURVIVES_STRESS"
        )

        partial_count = sum(
            1 for r in rows
            if upper(r.get("stress_survival_band")) == "PARTIAL_SURVIVAL"
        )

        fragile_count = sum(
            1 for r in rows
            if upper(r.get("stress_survival_band")) == "FRAGILE_UNDER_STRESS"
        )

        fail_count = sum(
            1 for r in rows
            if upper(r.get("stress_survival_band")) == "FAILS_STRESS"
        )

        # Recovery potential
        structural_recovery = resilience_score * 0.35
        confidence_recovery = confidence_score * 0.20
        maturity_recovery = maturity_score * 0.20
        survivability_recovery = average_survival * 0.25

        penalties = 0
        penalties += fail_count * 10
        penalties += fragile_count * 5

        if worst_survival <= 5:
            penalties += 15

        recovery_score = round(
            max(
                0,
                min(
                    100,
                    structural_recovery
                    + confidence_recovery
                    + maturity_recovery
                    + survivability_recovery
                    - penalties,
                ),
            ),
            2,
        )

        band = recovery_band(recovery_score)

        sources = []

        if resilience_score >= 40:
            sources.append("STRUCTURAL_RECOVERY_FOUNDATION")

        if confidence_score < 40:
            sources.append("CONFIDENCE_RECOVERY_WEAKNESS")

        if maturity_score < 40:
            sources.append("IMMATURE_RECOVERY_STATE")

        if fail_count >= 3:
            sources.append("MULTI_SCENARIO_FAILURE")

        if partial_count > 0 or fragile_count > 0:
            sources.append("PARTIAL_STRESS_SURVIVAL")

        if best_survival >= 40:
            sources.append("RECOVERABLE_STRESS_RESPONSE")

        recovery_rows.append({
            "structure_key": key,
            "track": track,
            "dominant_transition_shape": shape,
            "resilience_score": resilience_score,
            "confidence_score": confidence_score,
            "maturity_score": maturity_score,
            "average_stress_survival": round(average_survival, 2),
            "best_stress_survival": round(best_survival, 2),
            "worst_stress_survival": round(worst_survival, 2),
            "survives_count": survives_count,
            "partial_count": partial_count,
            "fragile_count": fragile_count,
            "fail_count": fail_count,
            "recovery_score": recovery_score,
            "recovery_band": band,
            "recovery_sources": "|".join(sources),
            "recommended_action": recovery_action(band),
            "research_boundary": "OFFLINE_RESEARCH_ONLY",
            "live_modelling_yes": 0,
            "live_execution_yes": 0,
            "engine_version": ENGINE_VERSION,
            "timestamp_utc": now_iso(),
        })

        if band in {
            "LOW_RECOVERY_CAPACITY",
            "FRAGILE_RECOVERY_CAPACITY",
        }:
            alert_rows.append({
                "structure_key": key,
                "track": track,
                "recovery_band": band,
                "recovery_score": recovery_score,
                "recovery_sources": "|".join(sources),
                "recommended_action": recovery_action(band),
                "research_boundary": "OFFLINE_RESEARCH_ONLY",
                "live_modelling_yes": 0,
                "live_execution_yes": 0,
                "engine_version": ENGINE_VERSION,
                "timestamp_utc": now_iso(),
            })

    high_count = sum(1 for r in recovery_rows if r["recovery_band"] == "HIGH_RECOVERY_CAPACITY")
    moderate_count = sum(1 for r in recovery_rows if r["recovery_band"] == "MODERATE_RECOVERY_CAPACITY")
    fragile_count = sum(1 for r in recovery_rows if r["recovery_band"] == "FRAGILE_RECOVERY_CAPACITY")
    low_count = sum(1 for r in recovery_rows if r["recovery_band"] == "LOW_RECOVERY_CAPACITY")

    if high_count:
        health = "RECOVERY_CAPABLE_MEMORY_PRESENT"
    elif moderate_count:
        health = "RECOVERY_DEVELOPING"
    elif fragile_count:
        health = "FRAGILE_RECOVERY_ONLY"
    else:
        health = "LOW_RECOVERY_ONLY"

    summary_rows = [
        {"metric": "structures_assessed", "value": len(recovery_rows)},
        {"metric": "high_recovery_rows", "value": high_count},
        {"metric": "moderate_recovery_rows", "value": moderate_count},
        {"metric": "fragile_recovery_rows", "value": fragile_count},
        {"metric": "low_recovery_rows", "value": low_count},
        {"metric": "alert_rows", "value": len(alert_rows)},
        {"metric": "overall_recovery_health", "value": health},
        {"metric": "research_boundary", "value": "OFFLINE_RESEARCH_ONLY"},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
    ]

    write_csv(
        OUT_RECOVERY,
        recovery_rows,
        [
            "structure_key",
            "track",
            "dominant_transition_shape",
            "resilience_score",
            "confidence_score",
            "maturity_score",
            "average_stress_survival",
            "best_stress_survival",
            "worst_stress_survival",
            "survives_count",
            "partial_count",
            "fragile_count",
            "fail_count",
            "recovery_score",
            "recovery_band",
            "recovery_sources",
            "recommended_action",
            "research_boundary",
            "live_modelling_yes",
            "live_execution_yes",
            "engine_version",
            "timestamp_utc",
        ],
    )

    write_csv(
        OUT_ALERTS,
        alert_rows,
        [
            "structure_key",
            "track",
            "recovery_band",
            "recovery_score",
            "recovery_sources",
            "recommended_action",
            "research_boundary",
            "live_modelling_yes",
            "live_execution_yes",
            "engine_version",
            "timestamp_utc",
        ],
    )

    write_csv(
        OUT_SUMMARY,
        summary_rows,
        ["metric", "value"],
    )

    for row in summary_rows:
        print(f"{row['metric']}: {row['value']}")

    print("=" * 88)
    print("MEMORY RECOVERY")
    print("=" * 88)

    for row in recovery_rows:
        print(
            f"{row['track']} -> "
            f"{row['recovery_band']} "
            f"score={row['recovery_score']} "
            f"sources={row['recovery_sources']}"
        )

if __name__ == "__main__":
    main()
