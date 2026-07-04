from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUTS = {
    "holdout": DATA / "edgeiq_regime_segment_holdout_v1.csv",
    "stability_map": DATA / "edgeiq_regime_segment_stability_map_v1.csv",
    "validation": DATA / "edgeiq_temporal_physics_validation_v1.csv",
}

OUT = DATA / "edgeiq_stable_regime_isolation_v1.csv"
SUMMARY = DATA / "edgeiq_stable_regime_isolation_summary_v1.csv"
PERSISTENCE = DATA / "edgeiq_stable_regime_persistence_v1.csv"

OUT_FIELDS = [
    "segment_type",
    "segment_value",
    "phase_transition_pattern",
    "sample_size",
    "win_rate",
    "place_rate",
    "top4_rate",
    "stability_score",
    "repeatability_score",
    "regime_persistence_score",
    "variance_decay_score",
    "survival_score",
    "environmental_dependency_score",
    "isolation_status",
    "research_interpretation",
    "live_modelling_allowed",
    "live_execution_allowed",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

PERSISTENCE_FIELDS = [
    "environment_key",
    "segment_type",
    "segment_value",
    "stable_phase_count",
    "total_stable_sample",
    "avg_stability_score",
    "avg_repeatability_score",
    "avg_persistence_score",
    "avg_survival_score",
    "environmental_dependency_score",
    "dominant_phase_pattern",
    "persistence_label",
    "live_modelling_allowed",
    "live_execution_allowed",
    "notes",
]

WATCH_SEGMENTS = {
    ("track", "HORSHAM"),
    ("track_family", "COUNTRY"),
    ("tempo_bucket", "MEDIUM"),
}


def clean(value: object) -> str:
    text = str(value or "").strip()
    if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"}:
        return ""
    return text


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{int(datetime.now().timestamp() * 1000)}.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def to_int(value: object) -> int:
    try:
        return int(float(clean(value)))
    except ValueError:
        return 0


def to_float(value: object) -> float:
    try:
        return float(clean(value))
    except ValueError:
        return math.nan


def fmt(value: float) -> str:
    return f"{max(0.0, min(100.0, value)):.2f}"


def build_map_index() -> dict[tuple[str, str], dict[str, str]]:
    return {
        (clean(row.get("segment_type")), clean(row.get("segment_value"))): row
        for row in read_csv(INPUTS["stability_map"])
    }


def validation_phase_totals() -> Counter[str]:
    totals: Counter[str] = Counter()
    for row in read_csv(INPUTS["validation"]):
        if clean(row.get("finish_position")):
            totals[clean(row.get("phase_transition_pattern")) or "UNKNOWN"] += 1
    return totals


def dependency_score(row: dict[str, str], stable_map: dict[tuple[str, str], dict[str, str]], phase_totals: Counter[str]) -> float:
    segment_type = clean(row.get("segment_type"))
    segment_value = clean(row.get("segment_value"))
    sample = to_int(row.get("sample_size"))
    phase = clean(row.get("phase_transition_pattern")) or "UNKNOWN"
    phase_total = max(1, phase_totals.get(phase, sample))
    share_of_phase = (sample / phase_total) * 100.0
    map_row = stable_map.get((segment_type, segment_value), {})
    stable_segments = to_int(map_row.get("stable_segments"))
    conflicted = to_int(map_row.get("conflicted_segments"))
    high_variance = to_int(map_row.get("high_variance_segments"))
    low_sample = to_int(map_row.get("low_sample_segments"))
    concentration = min(70.0, share_of_phase)
    fragility = min(30.0, (conflicted * 6.0) + (high_variance * 5.0) + (low_sample * 3.0))
    breadth_relief = min(20.0, stable_segments * 3.0)
    return max(0.0, min(100.0, concentration + fragility - breadth_relief))


def repeatability_score(row: dict[str, str]) -> float:
    positive = to_float(row.get("positive_repeatability"))
    negative = to_float(row.get("negative_repeatability"))
    return max(0.0, min(100.0, positive - (negative * 1.5)))


def variance_decay_score(row: dict[str, str]) -> float:
    variance = to_float(row.get("variance_score"))
    if math.isnan(variance):
        return 0.0
    return max(0.0, min(100.0, 100.0 - variance))


def survival_score(row: dict[str, str], dependency: float) -> float:
    sample = to_int(row.get("sample_size"))
    top4 = to_float(row.get("top4_rate"))
    stability = to_float(row.get("stability_score"))
    sample_score = min(25.0, sample / 120.0)
    return max(0.0, min(100.0, (top4 * 0.35) + (stability * 0.35) + sample_score - (dependency * 0.15)))


def persistence_score(row: dict[str, str], dependency: float) -> float:
    stability = to_float(row.get("stability_score"))
    repeatability = repeatability_score(row)
    variance_decay = variance_decay_score(row)
    survival = survival_score(row, dependency)
    return max(0.0, min(100.0, (stability * 0.30) + (repeatability * 0.25) + (variance_decay * 0.20) + (survival * 0.25) - (dependency * 0.20)))


def isolation_status(row: dict[str, str], persistence: float, dependency: float, survival: float) -> str:
    segment_type = clean(row.get("segment_type"))
    segment_value = clean(row.get("segment_value"))
    if dependency >= 70.0:
        return "STABLE_BUT_ENVIRONMENT_DEPENDENT"
    if persistence >= 75.0 and survival >= 65.0 and dependency < 45.0:
        return "PERSISTENT_STABLE_RESEARCH_ENVIRONMENT"
    if (segment_type, segment_value) in WATCH_SEGMENTS:
        return "WATCHLIST_STABLE_POCKET"
    if persistence >= 60.0:
        return "STABLE_RESEARCH_POCKET"
    return "WEAK_STABLE_RESEARCH_POCKET"


def interpretation(row: dict[str, str], status: str) -> str:
    segment = f"{clean(row.get('segment_type'))}={clean(row.get('segment_value'))}"
    phase = clean(row.get("phase_transition_pattern"))
    if status == "STABLE_BUT_ENVIRONMENT_DEPENDENT":
        return f"{phase} is stable inside {segment}, but dependency is too high for broad interpretation."
    if status == "WATCHLIST_STABLE_POCKET":
        return f"{segment} is a named stable pocket to monitor longitudinally for {phase}."
    if status == "PERSISTENT_STABLE_RESEARCH_ENVIRONMENT":
        return f"{phase} remains stable in {segment} under offline research isolation only."
    return f"{phase} has a stable holdout label in {segment}, but persistence remains research-only."


def build_rows() -> list[dict[str, object]]:
    stable_map = build_map_index()
    phase_totals = validation_phase_totals()
    rows: list[dict[str, object]] = []
    for row in read_csv(INPUTS["holdout"]):
        if clean(row.get("holdout_classification")) != "STABLE_HOLDOUT_ENVIRONMENT":
            continue
        dependency = dependency_score(row, stable_map, phase_totals)
        repeatability = repeatability_score(row)
        variance_decay = variance_decay_score(row)
        survival = survival_score(row, dependency)
        persistence = persistence_score(row, dependency)
        status = isolation_status(row, persistence, dependency, survival)
        rows.append(
            {
                "segment_type": clean(row.get("segment_type")),
                "segment_value": clean(row.get("segment_value")),
                "phase_transition_pattern": clean(row.get("phase_transition_pattern")),
                "sample_size": clean(row.get("sample_size")),
                "win_rate": clean(row.get("win_rate")),
                "place_rate": clean(row.get("place_rate")),
                "top4_rate": clean(row.get("top4_rate")),
                "stability_score": clean(row.get("stability_score")),
                "repeatability_score": fmt(repeatability),
                "regime_persistence_score": fmt(persistence),
                "variance_decay_score": fmt(variance_decay),
                "survival_score": fmt(survival),
                "environmental_dependency_score": fmt(dependency),
                "isolation_status": status,
                "research_interpretation": interpretation(row, status),
                "live_modelling_allowed": "NO",
                "live_execution_allowed": "NO",
                "notes": "Stable regime isolation is offline research only. No predictions, overlays, ratings, live modelling, or execution.",
            }
        )
    rows.sort(key=lambda item: (-to_float(item["regime_persistence_score"]), -to_int(item["sample_size"]), str(item["segment_type"]), str(item["segment_value"])))
    return rows


def build_persistence(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["segment_type"]), str(row["segment_value"]))].append(row)
    out: list[dict[str, object]] = []
    for (segment_type, segment_value), items in sorted(grouped.items()):
        phase_counts = Counter(str(row["phase_transition_pattern"]) for row in items)
        dominant_phase = phase_counts.most_common(1)[0][0] if phase_counts else ""
        total_sample = sum(to_int(row["sample_size"]) for row in items)
        avg_stability = sum(to_float(row["stability_score"]) for row in items) / len(items)
        avg_repeat = sum(to_float(row["repeatability_score"]) for row in items) / len(items)
        avg_persist = sum(to_float(row["regime_persistence_score"]) for row in items) / len(items)
        avg_survival = sum(to_float(row["survival_score"]) for row in items) / len(items)
        avg_dependency = sum(to_float(row["environmental_dependency_score"]) for row in items) / len(items)
        if avg_dependency >= 70:
            label = "ENVIRONMENT_DEPENDENT_STABILITY"
        elif avg_persist >= 75 and len(items) >= 3:
            label = "MULTI_PHASE_PERSISTENT_STABILITY"
        elif avg_persist >= 60:
            label = "SINGLE_ENVIRONMENT_STABLE_RESEARCH"
        else:
            label = "WEAK_STABLE_RESEARCH"
        out.append(
            {
                "environment_key": f"{segment_type}:{segment_value}",
                "segment_type": segment_type,
                "segment_value": segment_value,
                "stable_phase_count": len(items),
                "total_stable_sample": total_sample,
                "avg_stability_score": fmt(avg_stability),
                "avg_repeatability_score": fmt(avg_repeat),
                "avg_persistence_score": fmt(avg_persist),
                "avg_survival_score": fmt(avg_survival),
                "environmental_dependency_score": fmt(avg_dependency),
                "dominant_phase_pattern": dominant_phase,
                "persistence_label": label,
                "live_modelling_allowed": "NO",
                "live_execution_allowed": "NO",
                "notes": "Persistence map is descriptive research only and cannot authorise live modelling.",
            }
        )
    out.sort(key=lambda item: (-to_float(item["avg_persistence_score"]), -to_int(item["total_stable_sample"])))
    return out


def build_summary(rows: list[dict[str, object]], persistence: list[dict[str, object]]) -> list[dict[str, object]]:
    statuses = Counter(str(row["isolation_status"]) for row in rows)
    watched = [row for row in rows if (str(row["segment_type"]), str(row["segment_value"])) in WATCH_SEGMENTS]
    pocket_counts = Counter(f"{row['segment_type']}::{row['segment_value']}" for row in watched)
    values: list[dict[str, object]] = [
        {"metric": "stable_regime_rows", "value": len(rows)},
        {"metric": "persistence_rows", "value": len(persistence)},
        {"metric": "persistent_stable_research_environments", "value": statuses.get("PERSISTENT_STABLE_RESEARCH_ENVIRONMENT", 0)},
        {"metric": "watchlist_stable_pockets", "value": statuses.get("WATCHLIST_STABLE_POCKET", 0)},
        {"metric": "stable_but_environment_dependent", "value": statuses.get("STABLE_BUT_ENVIRONMENT_DEPENDENT", 0)},
        {"metric": "stable_research_pockets", "value": statuses.get("STABLE_RESEARCH_POCKET", 0)},
        {"metric": "weak_stable_research_pockets", "value": statuses.get("WEAK_STABLE_RESEARCH_POCKET", 0)},
        {"metric": "h orsham_stable_rows".replace(" ", ""), "value": pocket_counts.get("track::HORSHAM", 0)},
        {"metric": "country_stable_rows", "value": pocket_counts.get("track_family::COUNTRY", 0)},
        {"metric": "medium_tempo_stable_rows", "value": pocket_counts.get("tempo_bucket::MEDIUM", 0)},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "offline_research_only", "value": "YES"},
    ]
    for path in INPUTS.values():
        if not path.exists():
            values.append({"metric": f"missing_input::{path.name}", "value": "YES"})
    return values


def main() -> None:
    rows = build_rows()
    persistence = build_persistence(rows)
    summary = build_summary(rows, persistence)
    write_csv(OUT, rows, OUT_FIELDS)
    write_csv(PERSISTENCE, persistence, PERSISTENCE_FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    print("=" * 88)
    print("EDGEIQ STABLE REGIME ISOLATION V1")
    print("=" * 88)
    print(f"stable rows: {len(rows)}")
    print(f"persistence rows: {len(persistence)}")
    for row in summary:
        if row["metric"] in {"stable_regime_rows", "persistence_rows", "horsham_stable_rows", "country_stable_rows", "medium_tempo_stable_rows", "live_modelling_yes", "live_execution_yes"}:
            print(f"{row['metric']}: {row['value']}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {PERSISTENCE}")


if __name__ == "__main__":
    main()
