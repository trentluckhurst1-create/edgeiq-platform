from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"

SOURCE = PUBLIC / "edgeiq_qld_race_state_transition_profiles_v1.csv"

OUT_PERSISTENCE = PUBLIC / "edgeiq_transition_persistence_memory_v1.csv"
OUT_REGIMES = PUBLIC / "edgeiq_transition_regime_clusters_v1.csv"
OUT_SURVIVAL = PUBLIC / "edgeiq_transition_survival_matrix_v1.csv"
OUT_TRACK_MEMORY = PUBLIC / "edgeiq_transition_track_memory_v1.csv"
OUT_SUMMARY = PUBLIC / "edgeiq_transition_persistence_summary_v1.csv"

ENGINE_VERSION = "EDGEIQ_TRANSITION_PERSISTENCE_ENGINE_V1"

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
        return None

def classify_persistence(count: int, tracks: int) -> str:
    score = count + (tracks * 2)

    if score >= 20:
        return "DURABLE_BEHAVIOURAL_STRUCTURE"

    if score >= 10:
        return "STABLE_EMERGING_STRUCTURE"

    if score >= 5:
        return "OBSERVATIONAL_STRUCTURE"

    return "WEAK_OR_DECAYING_STRUCTURE"

def classify_regime(avg_seconds, range_seconds):
    if avg_seconds is None or range_seconds is None:
        return "UNKNOWN_REGIME"

    if avg_seconds <= 11.4 and range_seconds <= 0.6:
        return "HIGH_PRESSURE_STABLE"

    if avg_seconds <= 11.8 and range_seconds > 1.2:
        return "HIGH_PRESSURE_VARIABLE"

    if avg_seconds >= 12.3 and range_seconds <= 0.7:
        return "SLOW_CONTROLLED"

    if avg_seconds >= 12.3 and range_seconds > 1.2:
        return "FATIGUE_COLLAPSE"

    return "BALANCED_TRANSITION_ENVIRONMENT"

def main():
    print("=" * 88)
    print("EDGEIQ TRANSITION PERSISTENCE ENGINE V1")
    print("=" * 88)

    rows = read_csv(SOURCE)

    shape_memory = defaultdict(list)
    regime_memory = defaultdict(list)
    track_memory = defaultdict(lambda: defaultdict(int))

    persistence_rows = []
    regime_rows = []
    survival_rows = []
    track_rows = []

    summary = Counter()

    for row in rows:
        shape = row.get("transition_shape", "")
        track = row.get("track", "")

        avg_seconds = safe_float(row.get("avg_segment_seconds"))
        range_seconds = safe_float(row.get("range_seconds"))

        regime = classify_regime(avg_seconds, range_seconds)

        shape_memory[shape].append(row)
        regime_memory[regime].append(row)

        track_memory[track][shape] += 1

    for shape, entries in shape_memory.items():
        tracks = sorted(set(e.get("track", "") for e in entries))
        persistence_class = classify_persistence(len(entries), len(tracks))

        avg_values = [
            safe_float(e.get("avg_segment_seconds"))
            for e in entries
            if safe_float(e.get("avg_segment_seconds")) is not None
        ]

        avg_transition_seconds = (
            round(sum(avg_values) / len(avg_values), 3)
            if avg_values else ""
        )

        persistence_rows.append({
            "transition_shape": shape,
            "observed_count": len(entries),
            "track_count": len(tracks),
            "tracks": "|".join(tracks),
            "avg_transition_seconds": avg_transition_seconds,
            "persistence_class": persistence_class,
            "memory_strength": (
                "HIGH" if len(entries) >= 10
                else "MEDIUM" if len(entries) >= 5
                else "LOW"
            ),
            "research_boundary": "OFFLINE_RESEARCH_ONLY",
            "live_modelling_yes": 0,
            "live_execution_yes": 0,
            "engine_version": ENGINE_VERSION,
            "timestamp_utc": now_iso(),
        })

    for regime, entries in regime_memory.items():
        avg_ranges = [
            safe_float(e.get("range_seconds"))
            for e in entries
            if safe_float(e.get("range_seconds")) is not None
        ]

        avg_range = (
            round(sum(avg_ranges) / len(avg_ranges), 3)
            if avg_ranges else ""
        )

        regime_rows.append({
            "regime_cluster": regime,
            "observed_profiles": len(entries),
            "avg_range_seconds": avg_range,
            "stability_grade": (
                "HIGH" if len(entries) >= 8
                else "MEDIUM" if len(entries) >= 4
                else "LOW"
            ),
            "research_boundary": "OFFLINE_RESEARCH_ONLY",
            "engine_version": ENGINE_VERSION,
        })

    for shape, entries in shape_memory.items():
        stable_count = sum(
            1 for e in entries
            if "STABLE" in e.get("transition_shape", "")
        )

        accel_count = sum(
            1 for e in entries
            if "ACCELERATION" in e.get("transition_shape", "")
        )

        variable_count = sum(
            1 for e in entries
            if "VARIABLE" in e.get("transition_shape", "")
        )

        survival_rows.append({
            "transition_shape": shape,
            "observed_profiles": len(entries),
            "stable_profiles": stable_count,
            "acceleration_profiles": accel_count,
            "variable_profiles": variable_count,
            "survival_bias": (
                "STABLE"
                if stable_count >= accel_count and stable_count >= variable_count
                else "ACCELERATION"
                if accel_count >= variable_count
                else "VARIABLE"
            ),
            "survival_grade": (
                "HIGH"
                if len(entries) >= 10
                else "MEDIUM"
                if len(entries) >= 5
                else "LOW"
            ),
            "research_boundary": "OFFLINE_RESEARCH_ONLY",
            "engine_version": ENGINE_VERSION,
        })

    for track, shapes in track_memory.items():
        total = sum(shapes.values())

        for shape, count in shapes.items():
            pct = round((count / total) * 100, 2) if total else 0

            track_rows.append({
                "track": track,
                "transition_shape": shape,
                "observed_count": count,
                "track_shape_pct": pct,
                "track_memory_grade": (
                    "HIGH" if pct >= 45
                    else "MEDIUM" if pct >= 20
                    else "LOW"
                ),
                "research_boundary": "OFFLINE_RESEARCH_ONLY",
                "engine_version": ENGINE_VERSION,
            })

    summary_rows = [
        {"metric": "profiles_loaded", "value": len(rows)},
        {"metric": "persistence_rows", "value": len(persistence_rows)},
        {"metric": "regime_clusters", "value": len(regime_rows)},
        {"metric": "survival_rows", "value": len(survival_rows)},
        {"metric": "track_memory_rows", "value": len(track_rows)},
        {"metric": "offline_research_only", "value": "YES"},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
    ]

    write_csv(
        OUT_PERSISTENCE,
        persistence_rows,
        [
            "transition_shape",
            "observed_count",
            "track_count",
            "tracks",
            "avg_transition_seconds",
            "persistence_class",
            "memory_strength",
            "research_boundary",
            "live_modelling_yes",
            "live_execution_yes",
            "engine_version",
            "timestamp_utc",
        ],
    )

    write_csv(
        OUT_REGIMES,
        regime_rows,
        [
            "regime_cluster",
            "observed_profiles",
            "avg_range_seconds",
            "stability_grade",
            "research_boundary",
            "engine_version",
        ],
    )

    write_csv(
        OUT_SURVIVAL,
        survival_rows,
        [
            "transition_shape",
            "observed_profiles",
            "stable_profiles",
            "acceleration_profiles",
            "variable_profiles",
            "survival_bias",
            "survival_grade",
            "research_boundary",
            "engine_version",
        ],
    )

    write_csv(
        OUT_TRACK_MEMORY,
        track_rows,
        [
            "track",
            "transition_shape",
            "observed_count",
            "track_shape_pct",
            "track_memory_grade",
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
    print("PERSISTENCE MEMORY")
    print("=" * 88)

    for row in persistence_rows:
        print(
            f"{row['transition_shape']} -> "
            f"{row['persistence_class']} "
            f"({row['observed_count']} observations)"
        )

    print("=" * 88)
    print("OUTPUTS")
    print("=" * 88)

    print(OUT_PERSISTENCE)
    print(OUT_REGIMES)
    print(OUT_SURVIVAL)
    print(OUT_TRACK_MEMORY)
    print(OUT_SUMMARY)

if __name__ == "__main__":
    main()
