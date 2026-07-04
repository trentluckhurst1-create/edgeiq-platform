from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"

PROFILES = PUBLIC / "edgeiq_qld_race_state_transition_profiles_v1.csv"
PERSISTENCE = PUBLIC / "edgeiq_transition_persistence_memory_v1.csv"
TRACK_MEMORY = PUBLIC / "edgeiq_transition_track_memory_v1.csv"
REGIMES = PUBLIC / "edgeiq_transition_regime_clusters_v1.csv"

OUT_DRIFT = PUBLIC / "edgeiq_transition_ecology_drift_v1.csv"
OUT_TRACK_STATE = PUBLIC / "edgeiq_transition_track_ecology_state_v1.csv"
OUT_ALERTS = PUBLIC / "edgeiq_transition_ecology_alerts_v1.csv"
OUT_SUMMARY = PUBLIC / "edgeiq_transition_ecology_drift_summary_v1.csv"

ENGINE_VERSION = "EDGEIQ_TRANSITION_ECOLOGY_DRIFT_ENGINE_V1"

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

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

def classify_ecology(track_rows: list[dict]) -> tuple[str, str, float]:
    if not track_rows:
        return "NO_ECOLOGY", "HIGH", 0.0

    total = sum(safe_int(r.get("observed_count")) for r in track_rows)
    if total <= 0:
        return "NO_ECOLOGY", "HIGH", 0.0

    dominant = max(track_rows, key=lambda r: safe_float(r.get("track_shape_pct")))
    dominant_pct = safe_float(dominant.get("track_shape_pct"))
    shape_count = len(track_rows)

    if dominant_pct >= 85 and shape_count <= 2:
        return "STABLE_DOMINANT_ECOLOGY", "LOW", dominant_pct

    if dominant_pct >= 60 and shape_count <= 4:
        return "EMERGING_DOMINANT_ECOLOGY", "MEDIUM", dominant_pct

    if shape_count >= 4 and dominant_pct < 50:
        return "FRAGMENTED_ECOLOGY", "HIGH", dominant_pct

    return "MIXED_ECOLOGY", "MEDIUM", dominant_pct

def main():
    print("=" * 88)
    print("EDGEIQ TRANSITION ECOLOGY DRIFT ENGINE V1")
    print("=" * 88)

    profiles = read_csv(PROFILES)
    persistence = read_csv(PERSISTENCE)
    track_memory = read_csv(TRACK_MEMORY)
    regimes = read_csv(REGIMES)

    persistence_lookup = {
        r.get("transition_shape", ""): r
        for r in persistence
    }

    track_groups = defaultdict(list)
    for row in track_memory:
        track_groups[row.get("track", "")].append(row)

    drift_rows = []
    track_state_rows = []
    alert_rows = []

    for track, rows in track_groups.items():
        ecology_state, drift_risk, dominant_pct = classify_ecology(rows)

        dominant_row = max(rows, key=lambda r: safe_float(r.get("track_shape_pct")))
        dominant_shape = dominant_row.get("transition_shape", "")
        dominant_persistence = persistence_lookup.get(dominant_shape, {}).get("persistence_class", "UNKNOWN")

        total_observations = sum(safe_int(r.get("observed_count")) for r in rows)
        shape_count = len(rows)

        track_state_rows.append({
            "track": track,
            "ecology_state": ecology_state,
            "drift_risk": drift_risk,
            "dominant_transition_shape": dominant_shape,
            "dominant_shape_pct": dominant_pct,
            "dominant_persistence_class": dominant_persistence,
            "transition_shape_count": shape_count,
            "observed_transition_profiles": total_observations,
            "research_boundary": "OFFLINE_RESEARCH_ONLY",
            "live_modelling_yes": 0,
            "live_execution_yes": 0,
            "engine_version": ENGINE_VERSION,
            "timestamp_utc": now_iso(),
        })

        for r in rows:
            shape = r.get("transition_shape", "")
            shape_pct = safe_float(r.get("track_shape_pct"))
            persistence_class = persistence_lookup.get(shape, {}).get("persistence_class", "UNKNOWN")

            if shape == dominant_shape:
                drift_status = "DOMINANT_STRUCTURE"
            elif shape_pct >= 20:
                drift_status = "SECONDARY_STRUCTURE"
            else:
                drift_status = "MINOR_STRUCTURE"

            drift_rows.append({
                "track": track,
                "transition_shape": shape,
                "track_shape_pct": shape_pct,
                "observed_count": r.get("observed_count", ""),
                "persistence_class": persistence_class,
                "ecology_state": ecology_state,
                "drift_status": drift_status,
                "drift_risk": drift_risk,
                "research_boundary": "OFFLINE_RESEARCH_ONLY",
                "live_modelling_yes": 0,
                "live_execution_yes": 0,
                "engine_version": ENGINE_VERSION,
            })

        if drift_risk == "HIGH":
            alert_rows.append({
                "track": track,
                "alert_type": "HIGH_DRIFT_RISK",
                "alert_message": "Transition ecology is fragmented or insufficiently stable. Research-only monitoring required.",
                "severity": "HIGH",
                "recommended_action": "monitor_only_do_not_model_do_not_execute",
                "research_boundary": "OFFLINE_RESEARCH_ONLY",
                "engine_version": ENGINE_VERSION,
                "timestamp_utc": now_iso(),
            })

        if dominant_persistence in {"WEAK_OR_DECAYING_STRUCTURE", "UNKNOWN"}:
            alert_rows.append({
                "track": track,
                "alert_type": "DOMINANT_STRUCTURE_NOT_VALIDATED",
                "alert_message": "Dominant transition structure is not yet persistence-validated.",
                "severity": "MEDIUM",
                "recommended_action": "collect_more_longitudinal_evidence",
                "research_boundary": "OFFLINE_RESEARCH_ONLY",
                "engine_version": ENGINE_VERSION,
                "timestamp_utc": now_iso(),
            })

    regime_counter = Counter(r.get("regime_cluster", "") for r in regimes)

    summary_rows = [
        {"metric": "profiles_loaded", "value": len(profiles)},
        {"metric": "persistence_rows_loaded", "value": len(persistence)},
        {"metric": "track_memory_rows_loaded", "value": len(track_memory)},
        {"metric": "regime_rows_loaded", "value": len(regimes)},
        {"metric": "track_ecology_states", "value": len(track_state_rows)},
        {"metric": "drift_rows", "value": len(drift_rows)},
        {"metric": "alert_rows", "value": len(alert_rows)},
        {"metric": "offline_research_only", "value": "YES"},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
    ]

    write_csv(
        OUT_DRIFT,
        drift_rows,
        [
            "track",
            "transition_shape",
            "track_shape_pct",
            "observed_count",
            "persistence_class",
            "ecology_state",
            "drift_status",
            "drift_risk",
            "research_boundary",
            "live_modelling_yes",
            "live_execution_yes",
            "engine_version",
        ],
    )

    write_csv(
        OUT_TRACK_STATE,
        track_state_rows,
        [
            "track",
            "ecology_state",
            "drift_risk",
            "dominant_transition_shape",
            "dominant_shape_pct",
            "dominant_persistence_class",
            "transition_shape_count",
            "observed_transition_profiles",
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
            "track",
            "alert_type",
            "alert_message",
            "severity",
            "recommended_action",
            "research_boundary",
            "engine_version",
            "timestamp_utc",
        ],
    )

    write_csv(OUT_SUMMARY, summary_rows, ["metric", "value"])

    print("SUMMARY")
    print("=" * 88)
    for row in summary_rows:
        print(f"{row['metric']}: {row['value']}")

    print("=" * 88)
    print("TRACK ECOLOGY STATES")
    print("=" * 88)
    for row in track_state_rows:
        print(
            f"{row['track']} -> {row['ecology_state']} "
            f"dominant={row['dominant_transition_shape']} "
            f"drift={row['drift_risk']}"
        )

    print("=" * 88)
    print("OUTPUTS")
    print("=" * 88)
    print(OUT_DRIFT)
    print(OUT_TRACK_STATE)
    print(OUT_ALERTS)
    print(OUT_SUMMARY)

if __name__ == "__main__":
    main()
