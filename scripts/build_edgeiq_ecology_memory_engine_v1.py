from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"

TRACK_STATE = PUBLIC / "edgeiq_transition_track_ecology_state_v1.csv"
DRIFT = PUBLIC / "edgeiq_transition_ecology_drift_v1.csv"
PERSISTENCE = PUBLIC / "edgeiq_transition_persistence_memory_v1.csv"
REGIMES = PUBLIC / "edgeiq_transition_regime_clusters_v1.csv"

OUT_MEMORY = PUBLIC / "edgeiq_ecology_longitudinal_memory_v1.csv"
OUT_MUTATIONS = PUBLIC / "edgeiq_ecology_mutation_events_v1.csv"
OUT_CLIMATE = PUBLIC / "edgeiq_ecology_climate_matrix_v1.csv"
OUT_STABILITY = PUBLIC / "edgeiq_ecology_stability_index_v1.csv"
OUT_SUMMARY = PUBLIC / "edgeiq_ecology_memory_summary_v1.csv"

ENGINE_VERSION = "EDGEIQ_ECOLOGY_MEMORY_ENGINE_V1"

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

def ecology_stability_score(dominant_pct, drift_risk):
    base = dominant_pct

    if drift_risk == "LOW":
        base += 20
    elif drift_risk == "MEDIUM":
        base += 5
    else:
        base -= 15

    return round(max(0, min(100, base)), 2)

def classify_climate(score):
    if score >= 90:
        return "PERSISTENT_STABLE_CLIMATE"

    if score >= 70:
        return "EMERGING_STABLE_CLIMATE"

    if score >= 45:
        return "TRANSITIONAL_CLIMATE"

    return "FRAGMENTED_CLIMATE"

def mutation_risk(shape_count, drift_risk):
    if shape_count >= 4 and drift_risk == "MEDIUM":
        return "ELEVATED_MUTATION_RISK"

    if shape_count >= 5 or drift_risk == "HIGH":
        return "HIGH_MUTATION_RISK"

    return "LOW_MUTATION_RISK"

def main():
    print("=" * 88)
    print("EDGEIQ ECOLOGY MEMORY ENGINE V1")
    print("=" * 88)

    track_state = read_csv(TRACK_STATE)
    drift = read_csv(DRIFT)
    persistence = read_csv(PERSISTENCE)
    regimes = read_csv(REGIMES)

    drift_by_track = defaultdict(list)

    for row in drift:
        drift_by_track[row.get("track", "")].append(row)

    memory_rows = []
    mutation_rows = []
    climate_rows = []
    stability_rows = []

    summary = Counter()

    for row in track_state:
        track = row.get("track", "")
        ecology_state = row.get("ecology_state", "")
        drift_risk = row.get("drift_risk", "")
        dominant_shape = row.get("dominant_transition_shape", "")
        dominant_pct = safe_float(row.get("dominant_shape_pct"))
        shape_count = int(row.get("transition_shape_count", "0"))

        stability_score = ecology_stability_score(
            dominant_pct,
            drift_risk,
        )

        climate = classify_climate(stability_score)

        mutation = mutation_risk(shape_count, drift_risk)

        memory_rows.append({
            "track": track,
            "ecology_state": ecology_state,
            "dominant_transition_shape": dominant_shape,
            "dominant_shape_pct": dominant_pct,
            "ecology_stability_score": stability_score,
            "ecology_climate": climate,
            "mutation_risk": mutation,
            "longitudinal_memory_status": (
                "PERSISTING"
                if stability_score >= 70
                else "EMERGING"
                if stability_score >= 45
                else "UNSTABLE"
            ),
            "research_boundary": "OFFLINE_RESEARCH_ONLY",
            "live_modelling_yes": 0,
            "live_execution_yes": 0,
            "engine_version": ENGINE_VERSION,
            "timestamp_utc": now_iso(),
        })

        stability_rows.append({
            "track": track,
            "stability_score": stability_score,
            "climate": climate,
            "drift_risk": drift_risk,
            "shape_count": shape_count,
            "dominant_transition_shape": dominant_shape,
            "research_boundary": "OFFLINE_RESEARCH_ONLY",
            "engine_version": ENGINE_VERSION,
        })

        climate_rows.append({
            "track": track,
            "ecology_climate": climate,
            "ecology_state": ecology_state,
            "dominant_transition_shape": dominant_shape,
            "dominant_shape_pct": dominant_pct,
            "research_boundary": "OFFLINE_RESEARCH_ONLY",
            "engine_version": ENGINE_VERSION,
        })

        if mutation != "LOW_MUTATION_RISK":
            mutation_rows.append({
                "track": track,
                "mutation_risk": mutation,
                "ecology_state": ecology_state,
                "drift_risk": drift_risk,
                "shape_count": shape_count,
                "recommended_action": (
                    "increase_longitudinal_observation"
                ),
                "research_boundary": "OFFLINE_RESEARCH_ONLY",
                "engine_version": ENGINE_VERSION,
                "timestamp_utc": now_iso(),
            })

    regime_counter = Counter(
        r.get("regime_cluster", "")
        for r in regimes
    )

    summary_rows = [
        {"metric": "track_states_loaded", "value": len(track_state)},
        {"metric": "drift_rows_loaded", "value": len(drift)},
        {"metric": "persistence_rows_loaded", "value": len(persistence)},
        {"metric": "regime_rows_loaded", "value": len(regimes)},
        {"metric": "memory_rows", "value": len(memory_rows)},
        {"metric": "mutation_rows", "value": len(mutation_rows)},
        {"metric": "climate_rows", "value": len(climate_rows)},
        {"metric": "stability_rows", "value": len(stability_rows)},
        {"metric": "offline_research_only", "value": "YES"},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
    ]

    write_csv(
        OUT_MEMORY,
        memory_rows,
        [
            "track",
            "ecology_state",
            "dominant_transition_shape",
            "dominant_shape_pct",
            "ecology_stability_score",
            "ecology_climate",
            "mutation_risk",
            "longitudinal_memory_status",
            "research_boundary",
            "live_modelling_yes",
            "live_execution_yes",
            "engine_version",
            "timestamp_utc",
        ],
    )

    write_csv(
        OUT_MUTATIONS,
        mutation_rows,
        [
            "track",
            "mutation_risk",
            "ecology_state",
            "drift_risk",
            "shape_count",
            "recommended_action",
            "research_boundary",
            "engine_version",
            "timestamp_utc",
        ],
    )

    write_csv(
        OUT_CLIMATE,
        climate_rows,
        [
            "track",
            "ecology_climate",
            "ecology_state",
            "dominant_transition_shape",
            "dominant_shape_pct",
            "research_boundary",
            "engine_version",
        ],
    )

    write_csv(
        OUT_STABILITY,
        stability_rows,
        [
            "track",
            "stability_score",
            "climate",
            "drift_risk",
            "shape_count",
            "dominant_transition_shape",
            "research_boundary",
            "engine_version",
        ],
    )

    write_csv(
        OUT_SUMMARY,
        summary_rows,
        ["metric", "value"],
    )

    print("SUMMARY")
    print("=" * 88)

    for row in summary_rows:
        print(f"{row['metric']}: {row['value']}")

    print("=" * 88)
    print("LONGITUDINAL ECOLOGY MEMORY")
    print("=" * 88)

    for row in memory_rows:
        print(
            f"{row['track']} -> "
            f"{row['ecology_climate']} "
            f"score={row['ecology_stability_score']} "
            f"memory={row['longitudinal_memory_status']}"
        )

    print("=" * 88)
    print("OUTPUTS")
    print("=" * 88)

    print(OUT_MEMORY)
    print(OUT_MUTATIONS)
    print(OUT_CLIMATE)
    print(OUT_STABILITY)
    print(OUT_SUMMARY)

if __name__ == "__main__":
    main()
