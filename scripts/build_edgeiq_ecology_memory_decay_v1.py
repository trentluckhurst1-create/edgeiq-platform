from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"

TEMPORAL_HISTORY = PUBLIC / "edgeiq_ecology_temporal_drift_history_v1.csv"
TEMPORAL_DURATION = PUBLIC / "edgeiq_ecology_temporal_stability_duration_v1.csv"
SNAPSHOT_COMPARISON = PUBLIC / "edgeiq_ecology_snapshot_comparison_v1.csv"
SNAPSHOT_CHANGES = PUBLIC / "edgeiq_ecology_snapshot_drift_changes_v1.csv"

OUT_DECAY = PUBLIC / "edgeiq_ecology_memory_decay_v1.csv"
OUT_DECAY_ALERTS = PUBLIC / "edgeiq_ecology_memory_decay_alerts_v1.csv"
OUT_DECAY_SUMMARY = PUBLIC / "edgeiq_ecology_memory_decay_summary_v1.csv"

ENGINE_VERSION = "EDGEIQ_ECOLOGY_MEMORY_DECAY_ENGINE_V1"

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
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

def clean(v):
    return str(v or "").strip()

def upper(v):
    return clean(v).upper()

def safe_int(v):
    try:
        return int(float(v))
    except Exception:
        return 0

def safe_float(v):
    try:
        return float(v)
    except Exception:
        return 0.0

def classify_decay(
    stability_ratio,
    drift_velocity,
    drift_events,
    mutation_events,
    governance_changes,
    boundary_violations,
):
    if boundary_violations > 0:
        return "GOVERNANCE_BREACH"

    if governance_changes > 0:
        return "GOVERNANCE_DECAY"

    if drift_velocity == "HIGH":
        return "ACCELERATING_DECAY"

    if mutation_events >= 2:
        return "MUTATING_MEMORY"

    if drift_events >= 2:
        return "DRIFTING_MEMORY"

    if stability_ratio < 0.50:
        return "WEAKENING_MEMORY"

    if stability_ratio >= 0.80 and drift_velocity == "LOW":
        return "PERSISTENT_MEMORY"

    return "STABLE_MEMORY"

def classify_decay_risk(decay_state):
    if decay_state in {
        "GOVERNANCE_BREACH",
        "ACCELERATING_DECAY",
    }:
        return "HIGH"

    if decay_state in {
        "GOVERNANCE_DECAY",
        "MUTATING_MEMORY",
        "DRIFTING_MEMORY",
    }:
        return "MEDIUM"

    return "LOW"

def main():
    print("=" * 88)
    print("EDGEIQ ECOLOGY MEMORY DECAY ENGINE V1")
    print("=" * 88)

    temporal_history = read_csv(TEMPORAL_HISTORY)
    temporal_duration = read_csv(TEMPORAL_DURATION)
    snapshot_comparison = read_csv(SNAPSHOT_COMPARISON)
    snapshot_changes = read_csv(SNAPSHOT_CHANGES)

    decay_rows = []
    alert_rows = []

    total_high = 0
    total_medium = 0
    total_low = 0

    for row in temporal_history:
        structure_key = clean(row.get("structure_key"))
        track = clean(row.get("track"))
        shape = clean(row.get("dominant_transition_shape"))

        snapshot_count = safe_int(row.get("snapshot_count"))
        stable_snapshot_count = safe_int(row.get("stable_snapshot_count"))
        possible_transition_count = max(
            safe_int(row.get("possible_transition_count")),
            1,
        )

        drift_event_count = safe_int(row.get("drift_event_count"))
        mutation_event_count = safe_int(row.get("mutation_event_count"))
        governance_change_count = safe_int(row.get("governance_change_count"))
        boundary_violation_count = safe_int(row.get("boundary_violation_count"))

        drift_velocity = clean(row.get("drift_velocity"))
        memory_trend = clean(row.get("memory_trend"))

        stability_ratio = round(
            stable_snapshot_count / possible_transition_count,
            4,
        )

        decay_state = classify_decay(
            stability_ratio,
            drift_velocity,
            drift_event_count,
            mutation_event_count,
            governance_change_count,
            boundary_violation_count,
        )

        decay_risk = classify_decay_risk(decay_state)

        if decay_risk == "HIGH":
            total_high += 1
        elif decay_risk == "MEDIUM":
            total_medium += 1
        else:
            total_low += 1

        decay_rows.append({
            "structure_key": structure_key,
            "track": track,
            "dominant_transition_shape": shape,
            "snapshot_count": snapshot_count,
            "stable_snapshot_count": stable_snapshot_count,
            "possible_transition_count": possible_transition_count,
            "stability_ratio": stability_ratio,
            "drift_event_count": drift_event_count,
            "mutation_event_count": mutation_event_count,
            "governance_change_count": governance_change_count,
            "boundary_violation_count": boundary_violation_count,
            "drift_velocity": drift_velocity,
            "memory_trend": memory_trend,
            "decay_state": decay_state,
            "decay_risk": decay_risk,
            "recommended_action": (
                "continue_longitudinal_monitoring"
                if decay_risk == "LOW"
                else "increase_observation_frequency"
                if decay_risk == "MEDIUM"
                else "freeze_structure_and_audit"
            ),
            "research_boundary": "OFFLINE_RESEARCH_ONLY",
            "live_modelling_yes": 0,
            "live_execution_yes": 0,
            "engine_version": ENGINE_VERSION,
            "timestamp_utc": now_iso(),
        })

        if decay_risk in {"HIGH", "MEDIUM"}:
            alert_rows.append({
                "structure_key": structure_key,
                "track": track,
                "decay_state": decay_state,
                "decay_risk": decay_risk,
                "recommended_action": (
                    "increase_observation_frequency"
                    if decay_risk == "MEDIUM"
                    else "freeze_structure_and_audit"
                ),
                "research_boundary": "OFFLINE_RESEARCH_ONLY",
                "live_modelling_yes": 0,
                "live_execution_yes": 0,
                "engine_version": ENGINE_VERSION,
                "timestamp_utc": now_iso(),
            })

    if total_high > 0:
        overall_health = "DECAY_RISK_ELEVATED"
    elif total_medium > 0:
        overall_health = "MONITORING_REQUIRED"
    else:
        overall_health = "PERSISTENT_MEMORY_STABLE"

    summary_rows = [
        {"metric": "structures_assessed", "value": len(decay_rows)},
        {"metric": "high_decay_risk_rows", "value": total_high},
        {"metric": "medium_decay_risk_rows", "value": total_medium},
        {"metric": "low_decay_risk_rows", "value": total_low},
        {"metric": "alert_rows", "value": len(alert_rows)},
        {"metric": "overall_decay_health", "value": overall_health},
        {"metric": "research_boundary", "value": "OFFLINE_RESEARCH_ONLY"},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
    ]

    write_csv(
        OUT_DECAY,
        decay_rows,
        [
            "structure_key",
            "track",
            "dominant_transition_shape",
            "snapshot_count",
            "stable_snapshot_count",
            "possible_transition_count",
            "stability_ratio",
            "drift_event_count",
            "mutation_event_count",
            "governance_change_count",
            "boundary_violation_count",
            "drift_velocity",
            "memory_trend",
            "decay_state",
            "decay_risk",
            "recommended_action",
            "research_boundary",
            "live_modelling_yes",
            "live_execution_yes",
            "engine_version",
            "timestamp_utc",
        ],
    )

    write_csv(
        OUT_DECAY_ALERTS,
        alert_rows,
        [
            "structure_key",
            "track",
            "decay_state",
            "decay_risk",
            "recommended_action",
            "research_boundary",
            "live_modelling_yes",
            "live_execution_yes",
            "engine_version",
            "timestamp_utc",
        ],
    )

    write_csv(
        OUT_DECAY_SUMMARY,
        summary_rows,
        ["metric", "value"],
    )

    for row in summary_rows:
        print(f"{row['metric']}: {row['value']}")

    print("=" * 88)
    print("MEMORY DECAY STATES")
    print("=" * 88)

    for row in decay_rows:
        print(
            f"{row['track']} -> "
            f"{row['decay_state']} "
            f"risk={row['decay_risk']} "
            f"ratio={row['stability_ratio']}"
        )

if __name__ == "__main__":
    main()
