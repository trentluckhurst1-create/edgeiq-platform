from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"

MATURITY = PUBLIC / "edgeiq_ecology_memory_maturity_v1.csv"
CONFIDENCE = PUBLIC / "edgeiq_ecology_memory_confidence_v1.csv"
PRESSURE = PUBLIC / "edgeiq_ecology_memory_pressure_v1.csv"
DECAY = PUBLIC / "edgeiq_ecology_memory_decay_v1.csv"
TEMPORAL = PUBLIC / "edgeiq_ecology_temporal_drift_history_v1.csv"

OUT_RESILIENCE = PUBLIC / "edgeiq_ecology_memory_resilience_v1.csv"
OUT_ALERTS = PUBLIC / "edgeiq_ecology_memory_resilience_alerts_v1.csv"
OUT_SUMMARY = PUBLIC / "edgeiq_ecology_memory_resilience_summary_v1.csv"

ENGINE_VERSION = "EDGEIQ_ECOLOGY_MEMORY_RESILIENCE_ENGINE_V1"

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

def safe_int(v):
    try:
        return int(float(v))
    except Exception:
        return 0

def resilience_band(score):
    if score >= 85:
        return "HIGH_RESILIENCE"
    if score >= 65:
        return "MODERATE_RESILIENCE"
    if score >= 40:
        return "FRAGILE_RESILIENCE"
    return "LOW_RESILIENCE"

def resilience_action(band):
    if band == "HIGH_RESILIENCE":
        return "maintain_longitudinal_observation"
    if band == "MODERATE_RESILIENCE":
        return "continue_snapshot_accumulation"
    if band == "FRAGILE_RESILIENCE":
        return "increase_pressure_monitoring"
    return "do_not_promote_structure"

def main():
    print("=" * 88)
    print("EDGEIQ ECOLOGY MEMORY RESILIENCE ENGINE V1")
    print("=" * 88)

    maturity_rows = read_csv(MATURITY)
    confidence_rows = read_csv(CONFIDENCE)
    pressure_rows = read_csv(PRESSURE)
    decay_rows = read_csv(DECAY)
    temporal_rows = read_csv(TEMPORAL)

    confidence_by_key = {
        clean(r.get("structure_key")): r
        for r in confidence_rows
    }

    pressure_by_key = {
        clean(r.get("structure_key")): r
        for r in pressure_rows
    }

    decay_by_key = {
        clean(r.get("structure_key")): r
        for r in decay_rows
    }

    temporal_by_key = {
        clean(r.get("structure_key")): r
        for r in temporal_rows
    }

    resilience_rows = []
    alert_rows = []

    for row in maturity_rows:
        key = clean(row.get("structure_key"))

        confidence = confidence_by_key.get(key, {})
        pressure = pressure_by_key.get(key, {})
        decay = decay_by_key.get(key, {})
        temporal = temporal_by_key.get(key, {})

        track = clean(row.get("track"))
        shape = clean(row.get("dominant_transition_shape"))

        maturity_score = safe_float(row.get("maturity_score"))
        confidence_score = safe_float(confidence.get("confidence_score"))
        pressure_score = safe_float(pressure.get("pressure_score"))

        stability_ratio = safe_float(row.get("stability_ratio"))

        drift_events = safe_int(temporal.get("drift_event_count"))
        mutation_events = safe_int(temporal.get("mutation_event_count"))
        governance_changes = safe_int(temporal.get("governance_change_count"))
        boundary_violations = safe_int(temporal.get("boundary_violation_count"))

        snapshot_count = safe_int(row.get("snapshot_count"))

        decay_state = upper(decay.get("decay_state"))
        maturity_band_value = upper(row.get("maturity_band"))
        confidence_band_value = upper(confidence.get("confidence_band"))

        # Positive resilience
        persistence_component = stability_ratio * 40
        confidence_component = confidence_score * 0.25
        maturity_component = maturity_score * 0.20

        survivability_component = 0
        if snapshot_count >= 10:
            survivability_component = 20
        elif snapshot_count >= 5:
            survivability_component = 12
        elif snapshot_count >= 3:
            survivability_component = 6

        # Penalties
        penalties = 0

        penalties += pressure_score * 0.35
        penalties += drift_events * 8
        penalties += mutation_events * 10
        penalties += governance_changes * 15
        penalties += boundary_violations * 100

        if "LOW_CONFIDENCE" in confidence_band_value:
            penalties += 18
        elif "FRAGILE_CONFIDENCE" in confidence_band_value:
            penalties += 10

        if "IMMATURE" in maturity_band_value:
            penalties += 20
        elif "EARLY_STAGE" in maturity_band_value:
            penalties += 10

        if "DRIFTING" in decay_state:
            penalties += 12
        elif "ACCELERATING" in decay_state:
            penalties += 25

        resilience_score = round(
            max(
                0,
                min(
                    100,
                    persistence_component
                    + confidence_component
                    + maturity_component
                    + survivability_component
                    - penalties,
                ),
            ),
            2,
        )

        band = resilience_band(resilience_score)

        sources = []

        if stability_ratio >= 0.95:
            sources.append("LONGITUDINAL_STABILITY")

        if pressure_score >= 40:
            sources.append("PRESSURE_STRESS")

        if "LOW_CONFIDENCE" in confidence_band_value:
            sources.append("CONFIDENCE_WEAKNESS")

        if "IMMATURE" in maturity_band_value:
            sources.append("IMMATURE_MEMORY")

        if snapshot_count < 5:
            sources.append("SHORT_HISTORY")

        if mutation_events > 0:
            sources.append("MUTATION_EXPOSURE")

        resilience_rows.append({
            "structure_key": key,
            "track": track,
            "dominant_transition_shape": shape,
            "snapshot_count": snapshot_count,
            "stability_ratio": stability_ratio,
            "pressure_score": pressure_score,
            "confidence_score": confidence_score,
            "maturity_score": maturity_score,
            "resilience_score": resilience_score,
            "resilience_band": band,
            "resilience_sources": "|".join(sources),
            "recommended_action": resilience_action(band),
            "research_boundary": "OFFLINE_RESEARCH_ONLY",
            "live_modelling_yes": 0,
            "live_execution_yes": 0,
            "engine_version": ENGINE_VERSION,
            "timestamp_utc": now_iso(),
        })

        if band in {
            "LOW_RESILIENCE",
            "FRAGILE_RESILIENCE",
        }:
            alert_rows.append({
                "structure_key": key,
                "track": track,
                "resilience_band": band,
                "resilience_score": resilience_score,
                "resilience_sources": "|".join(sources),
                "recommended_action": resilience_action(band),
                "research_boundary": "OFFLINE_RESEARCH_ONLY",
                "live_modelling_yes": 0,
                "live_execution_yes": 0,
                "engine_version": ENGINE_VERSION,
                "timestamp_utc": now_iso(),
            })

    high_count = sum(1 for r in resilience_rows if r["resilience_band"] == "HIGH_RESILIENCE")
    moderate_count = sum(1 for r in resilience_rows if r["resilience_band"] == "MODERATE_RESILIENCE")
    fragile_count = sum(1 for r in resilience_rows if r["resilience_band"] == "FRAGILE_RESILIENCE")
    low_count = sum(1 for r in resilience_rows if r["resilience_band"] == "LOW_RESILIENCE")

    if high_count:
        overall_health = "HIGH_RESILIENCE_PRESENT"
    elif moderate_count:
        overall_health = "RESILIENCE_DEVELOPING"
    elif fragile_count:
        overall_health = "FRAGILE_RESILIENCE_ONLY"
    else:
        overall_health = "LOW_RESILIENCE_ONLY"

    summary_rows = [
        {"metric": "structures_assessed", "value": len(resilience_rows)},
        {"metric": "high_resilience_rows", "value": high_count},
        {"metric": "moderate_resilience_rows", "value": moderate_count},
        {"metric": "fragile_resilience_rows", "value": fragile_count},
        {"metric": "low_resilience_rows", "value": low_count},
        {"metric": "alert_rows", "value": len(alert_rows)},
        {"metric": "overall_resilience_health", "value": overall_health},
        {"metric": "research_boundary", "value": "OFFLINE_RESEARCH_ONLY"},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
    ]

    write_csv(
        OUT_RESILIENCE,
        resilience_rows,
        [
            "structure_key",
            "track",
            "dominant_transition_shape",
            "snapshot_count",
            "stability_ratio",
            "pressure_score",
            "confidence_score",
            "maturity_score",
            "resilience_score",
            "resilience_band",
            "resilience_sources",
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
            "resilience_band",
            "resilience_score",
            "resilience_sources",
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
    print("MEMORY RESILIENCE")
    print("=" * 88)

    for row in resilience_rows:
        print(
            f"{row['track']} -> "
            f"{row['resilience_band']} "
            f"score={row['resilience_score']} "
            f"sources={row['resilience_sources']}"
        )

if __name__ == "__main__":
    main()
