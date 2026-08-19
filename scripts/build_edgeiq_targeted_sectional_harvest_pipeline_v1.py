from __future__ import annotations

import csv
import re
import time
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUTS = {
    "acquisition": DATA / "edgeiq_sectional_acquisition_priority_v1.csv",
    "shadow_state": DATA / "edgeiq_shadow_environment_state_v1.csv",
    "stable_regimes": DATA / "edgeiq_stable_regime_isolation_v1.csv",
    "walkforward": DATA / "edgeiq_temporal_walkforward_stability_v1.csv",
}

OUT = DATA / "edgeiq_targeted_sectional_harvest_targets_v1.csv"
SUMMARY = DATA / "edgeiq_targeted_sectional_harvest_summary_v1.csv"

TARGET_FIELDS = [
    "priority",
    "track",
    "race_class",
    "distance_bucket",
    "tempo_bucket",
    "environment_type",
    "current_quality_grade",
    "quality_blocker",
    "stable_research_status",
    "walkforward_status",
    "recommended_source_priority",
    "recommended_capture_strategy",
    "target_reason",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

FOCUS_TRACKS = {"HORSHAM"}
FOCUS_TRACK_FAMILIES = {"COUNTRY"}
FOCUS_CLASSES = {"BM56", "BM64"}
FOCUS_DISTANCE_BUCKETS = {"MILE"}
FOCUS_TEMPOS = {"MEDIUM"}
FOCUS_WALKFORWARD = {"SURVIVED_WALKFORWARD", "TEMPORALLY_STABLE"}
FOCUS_SHADOW_STATUS = {"ACTIVE_STABLE_RESEARCH", "SAMPLE_GROWTH_PHASE", "DECAYING_RESEARCH"}
STABLE_STATUS_VALUES = {"PERSISTENT_STABLE_RESEARCH_ENVIRONMENT", "STABLE_RESEARCH_POCKET", "WATCHLIST_STABLE_POCKET"}

GRADE_RANK = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1, "UNKNOWN": 0, "": 0}
PRIORITY_RANK = {"CRITICAL_TARGET": 4, "HIGH_VALUE_TARGET": 3, "MONITOR_ONLY": 2, "LOW_PRIORITY": 1}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{time.time_ns()}.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    tmp.replace(path)


def clean(value: object) -> str:
    return str(value or "").strip()


def upper(value: object) -> str:
    return clean(value).upper()


def normal_key(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", upper(value)).strip("_")


def split_environment(value: str) -> tuple[str, str]:
    text = clean(value)
    if ":" not in text:
        return "", text
    left, right = text.split(":", 1)
    return left.strip().lower(), right.strip().upper()


def first_nonblank(*values: object) -> str:
    for value in values:
        text = clean(value)
        if text:
            return text
    return ""


def parse_float(value: object, default: float = 0.0) -> float:
    try:
        text = clean(value).replace("%", "")
        if not text:
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def parse_int(value: object, default: int = 0) -> int:
    try:
        text = clean(value).replace(",", "")
        if not text:
            return default
        return int(float(text))
    except (TypeError, ValueError):
        return default


def target_dimension_from_acquisition(row: dict[str, str]) -> tuple[str, str]:
    target_type = upper(row.get("target_type"))
    target_value = upper(row.get("target_value"))
    if target_type == "SHADOW_ENVIRONMENT":
        env_type, env_value = split_environment(target_value)
        return env_type.upper(), env_value
    return target_type, target_value


def dimension_key(dimension: str, value: str) -> tuple[str, str]:
    return upper(dimension), upper(value)


def build_acquisition_index(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, object]]:
    index: dict[tuple[str, str], dict[str, object]] = {}
    for row in rows:
        dimension, value = target_dimension_from_acquisition(row)
        if not dimension or not value:
            continue
        key = dimension_key(dimension, value)
        existing = index.get(key, {})
        grade = upper(row.get("current_quality_grade")) or "UNKNOWN"
        affected = parse_int(row.get("affected_rows"))
        safe_shadow = parse_int(row.get("safe_shadow_rows"))
        blocker = upper(row.get("dominant_blocker")) or "UNKNOWN"
        priority = upper(row.get("priority")) or "LOW"
        if not existing or affected > parse_int(existing.get("affected_rows")):
            index[key] = {
                "quality_grade": grade,
                "blocker": blocker,
                "affected_rows": affected,
                "safe_shadow_rows": safe_shadow,
                "priority": priority,
                "source_hint": clean(row.get("target_source_hint")),
                "recommended_action": clean(row.get("recommended_acquisition_action")),
            }
    return index


def env_key(segment_type: object, segment_value: object) -> str:
    return f"{clean(segment_type).lower()}:{upper(segment_value)}"


def build_shadow_index(rows: list[dict[str, str]]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = clean(row.get("environment_key")) or env_key(row.get("segment_type"), row.get("segment_value"))
        if key:
            grouped[key.lower()].append(row)

    index: dict[str, dict[str, object]] = {}
    for key, values in grouped.items():
        statuses = [upper(row.get("current_status")) for row in values if clean(row.get("current_status"))]
        priorities = [upper(row.get("watch_priority")) for row in values if clean(row.get("watch_priority"))]
        samples = sum(parse_int(row.get("current_sample_count")) for row in values)
        health = max((parse_float(row.get("environment_health_score")) for row in values), default=0.0)
        index[key] = {
            "status": first_nonblank(*statuses) or "UNKNOWN",
            "priority": first_nonblank(*priorities) or "LOW",
            "sample_count": samples,
            "health_score": f"{health:.2f}",
            "rows": len(values),
        }
    return index


def build_stable_index(rows: list[dict[str, str]]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = env_key(row.get("segment_type"), row.get("segment_value"))
        if key:
            grouped[key.lower()].append(row)

    index: dict[str, dict[str, object]] = {}
    for key, values in grouped.items():
        statuses = [upper(row.get("isolation_status")) for row in values if clean(row.get("isolation_status"))]
        best_status = "UNKNOWN"
        if any(status == "PERSISTENT_STABLE_RESEARCH_ENVIRONMENT" for status in statuses):
            best_status = "PERSISTENT_STABLE_RESEARCH_ENVIRONMENT"
        elif any(status == "STABLE_RESEARCH_POCKET" for status in statuses):
            best_status = "STABLE_RESEARCH_POCKET"
        elif statuses:
            best_status = statuses[0]
        index[key] = {
            "status": best_status,
            "sample_size": sum(parse_int(row.get("sample_size")) for row in values),
            "stability_score": f"{max((parse_float(row.get('stability_score')) for row in values), default=0.0):.2f}",
            "phase_patterns": ",".join(sorted({upper(row.get("phase_transition_pattern")) for row in values if clean(row.get("phase_transition_pattern"))})),
        }
    return index


def build_walkforward_index(rows: list[dict[str, str]]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = clean(row.get("environment_key")) or env_key(row.get("segment_type"), row.get("segment_value"))
        if key:
            grouped[key.lower()].append(row)

    index: dict[str, dict[str, object]] = {}
    for key, values in grouped.items():
        statuses = [upper(row.get("walkforward_classification")) for row in values if clean(row.get("walkforward_classification"))]
        if any(status == "SURVIVED_WALKFORWARD" for status in statuses):
            best_status = "SURVIVED_WALKFORWARD"
        elif any(status == "TEMPORALLY_STABLE" for status in statuses):
            best_status = "TEMPORALLY_STABLE"
        elif statuses:
            best_status = statuses[0]
        else:
            best_status = "UNKNOWN"
        index[key] = {
            "status": best_status,
            "sample_size": sum(parse_int(row.get("window_sample_size")) for row in values if upper(row.get("window_name")) in {"FULL", ""}),
            "resilience_score": f"{max((parse_float(row.get('resilience_score')) for row in values), default=0.0):.2f}",
        }
    return index


def focus_dimensions() -> list[tuple[str, str]]:
    dims = []
    dims.extend(("TRACK", value) for value in sorted(FOCUS_TRACKS))
    dims.extend(("TRACK_FAMILY", value) for value in sorted(FOCUS_TRACK_FAMILIES))
    dims.extend(("RACE_CLASS", value) for value in sorted(FOCUS_CLASSES))
    dims.extend(("DISTANCE_BUCKET", value) for value in sorted(FOCUS_DISTANCE_BUCKETS))
    dims.extend(("TEMPO_BUCKET", value) for value in sorted(FOCUS_TEMPOS))
    return dims


def key_for_dimension(dimension: str, value: str) -> str:
    return f"{dimension.lower()}:{upper(value)}"


def build_environment_type(dimension: str, value: str) -> str:
    if dimension == "TRACK":
        return "STABLE_TRACK_SECTIONAL_TARGET"
    if dimension == "TRACK_FAMILY":
        return "STABLE_TRACK_FAMILY_SECTIONAL_TARGET"
    if dimension == "RACE_CLASS":
        return "STABLE_CLASS_SECTIONAL_TARGET"
    if dimension == "DISTANCE_BUCKET":
        return "STABLE_DISTANCE_SECTIONAL_TARGET"
    if dimension == "TEMPO_BUCKET":
        return "STABLE_TEMPO_SECTIONAL_TARGET"
    return f"STABLE_{normal_key(dimension)}_SECTIONAL_TARGET"


def infer_capture_strategy(blocker: str, grade: str, shadow_status: str, walk_status: str) -> str:
    blocker = upper(blocker)
    grade = upper(grade)
    parts: list[str] = []
    if blocker == "WEAK_PHASE_CONFIDENCE":
        parts.append("improve phase extraction depth")
        parts.append("prioritise complete early/mid/late chains")
    elif blocker == "LOW_SPLIT_COMPLETENESS":
        parts.append("fuller split ladders")
        parts.append("direct source payloads")
    elif blocker == "UNSAFE_RECONSTRUCTION_RISK":
        parts.append("avoid reconstruction-only rows")
        parts.append("prioritise direct source payloads")
    elif blocker == "WEAK_PHYSICS_CONSISTENCY":
        parts.append("repair early/mid/late phase extraction")
        parts.append("validate complete split chains")
    else:
        parts.append("fuller split ladders")
        parts.append("direct source payloads")

    if grade in {"C", "D", "F", "UNKNOWN"}:
        parts.append("avoid reconstruction-only rows")
    if shadow_status in {"ACTIVE_STABLE_RESEARCH", "DECAYING_RESEARCH"} or walk_status in FOCUS_WALKFORWARD:
        parts.append("prioritise complete early/mid/late chains")

    seen: set[str] = set()
    unique = []
    for part in parts:
        if part not in seen:
            unique.append(part)
            seen.add(part)
    return "; ".join(unique)


def source_priority(blocker: str, grade: str) -> str:
    blocker = upper(blocker)
    grade = upper(grade)
    if blocker in {"LOW_SPLIT_COMPLETENESS", "UNSAFE_RECONSTRUCTION_RISK"} or grade in {"D", "F", "UNKNOWN"}:
        return "DIRECT_OFFICIAL_SOURCE_FIRST"
    if blocker in {"WEAK_PHASE_CONFIDENCE", "WEAK_PHYSICS_CONSISTENCY"}:
        return "DIRECT_SOURCE_WITH_FULL_SPLIT_LADDER"
    return "DIRECT_SOURCE_PREFERRED"


def classify_target(
    dimension: str,
    value: str,
    quality_grade: str,
    blocker: str,
    safe_shadow_rows: int,
    shadow_status: str,
    stable_status: str,
    walk_status: str,
) -> str:
    dimension = upper(dimension)
    value = upper(value)
    quality_grade = upper(quality_grade) or "UNKNOWN"
    blocker = upper(blocker)
    stable = stable_status in STABLE_STATUS_VALUES
    walked = walk_status in FOCUS_WALKFORWARD
    shadow_active = shadow_status in FOCUS_SHADOW_STATUS
    is_core = (
        (dimension == "TRACK" and value in FOCUS_TRACKS)
        or (dimension == "TRACK_FAMILY" and value in FOCUS_TRACK_FAMILIES)
        or (dimension == "RACE_CLASS" and value in FOCUS_CLASSES)
        or (dimension == "DISTANCE_BUCKET" and value in FOCUS_DISTANCE_BUCKETS)
        or (dimension == "TEMPO_BUCKET" and value in FOCUS_TEMPOS)
    )
    weak_quality = quality_grade in {"C", "D", "F", "UNKNOWN"} or blocker in {"WEAK_PHASE_CONFIDENCE", "LOW_SPLIT_COMPLETENESS", "UNSAFE_RECONSTRUCTION_RISK"}

    if is_core and weak_quality and (stable or walked or shadow_active):
        return "CRITICAL_TARGET"
    if is_core and (weak_quality or safe_shadow_rows <= 2500):
        return "HIGH_VALUE_TARGET"
    if stable or walked or shadow_active:
        return "MONITOR_ONLY"
    return "LOW_PRIORITY"


def target_reason(
    dimension: str,
    value: str,
    grade: str,
    blocker: str,
    stable_status: str,
    walk_status: str,
    shadow_status: str,
) -> str:
    reasons = [f"{dimension}={value} is in the targeted sectional acquisition focus set"]
    if grade:
        reasons.append(f"current quality grade {grade}")
    if blocker and blocker != "UNKNOWN":
        reasons.append(f"dominant blocker {blocker}")
    if stable_status and stable_status != "UNKNOWN":
        reasons.append(f"stable research status {stable_status}")
    if walk_status and walk_status != "UNKNOWN":
        reasons.append(f"walk-forward status {walk_status}")
    if shadow_status and shadow_status != "UNKNOWN":
        reasons.append(f"shadow state {shadow_status}")
    return "; ".join(reasons)


def build_target_rows(
    acquisition: dict[tuple[str, str], dict[str, object]],
    shadow: dict[str, dict[str, object]],
    stable: dict[str, dict[str, object]],
    walkforward: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()

    candidate_dims = focus_dimensions()
    for key in acquisition:
        dimension, value = key
        if dimension in {"TRACK", "TRACK_FAMILY", "RACE_CLASS", "DISTANCE_BUCKET", "TEMPO_BUCKET"}:
            if key not in candidate_dims:
                candidate_dims.append(key)

    for dimension, value in candidate_dims:
        dimension = upper(dimension)
        value = upper(value)
        key = dimension_key(dimension, value)
        if key in seen:
            continue
        seen.add(key)

        acq = acquisition.get(key, {})
        env = key_for_dimension(dimension, value).lower()
        shadow_info = shadow.get(env, {})
        stable_info = stable.get(env, {})
        walk_info = walkforward.get(env, {})

        grade = upper(acq.get("quality_grade")) or "UNKNOWN"
        blocker = upper(acq.get("blocker")) or "UNKNOWN"
        safe_shadow = parse_int(acq.get("safe_shadow_rows"))
        stable_status = upper(stable_info.get("status")) or "UNKNOWN"
        walk_status = upper(walk_info.get("status")) or "UNKNOWN"
        shadow_status = upper(shadow_info.get("status")) or "UNKNOWN"
        priority = classify_target(dimension, value, grade, blocker, safe_shadow, shadow_status, stable_status, walk_status)

        if priority == "LOW_PRIORITY" and key not in acquisition:
            continue

        row = {
            "priority": priority,
            "track": value if dimension == "TRACK" else "",
            "race_class": value if dimension == "RACE_CLASS" else "",
            "distance_bucket": value if dimension == "DISTANCE_BUCKET" else "",
            "tempo_bucket": value if dimension == "TEMPO_BUCKET" else "",
            "environment_type": build_environment_type(dimension, value),
            "current_quality_grade": grade,
            "quality_blocker": blocker,
            "stable_research_status": stable_status,
            "walkforward_status": walk_status,
            "recommended_source_priority": source_priority(blocker, grade),
            "recommended_capture_strategy": infer_capture_strategy(blocker, grade, shadow_status, walk_status),
            "target_reason": target_reason(dimension, value, grade, blocker, stable_status, walk_status, shadow_status),
            "notes": "Offline sectional acquisition roadmap only. No modelling, overlays, ratings, live execution, or live modelling enabled.",
            "_rank": PRIORITY_RANK.get(priority, 0),
            "_grade_rank": GRADE_RANK.get(grade, 0),
            "_affected": parse_int(acq.get("affected_rows")),
            "_dimension": dimension,
            "_value": value,
        }
        rows.append(row)

    rows.sort(key=lambda row: (-parse_int(row.get("_rank")), parse_int(row.get("_grade_rank")), -parse_int(row.get("_affected")), clean(row.get("_dimension")), clean(row.get("_value"))))
    for row in rows:
        row.pop("_rank", None)
        row.pop("_grade_rank", None)
        row.pop("_affected", None)
        row.pop("_dimension", None)
        row.pop("_value", None)
    return rows


def build_summary(rows: list[dict[str, object]], missing_inputs: list[str]) -> list[dict[str, object]]:
    counter = defaultdict(int)
    for row in rows:
        counter[upper(row.get("priority"))] += 1

    critical = [row for row in rows if upper(row.get("priority")) == "CRITICAL_TARGET"]
    high = [row for row in rows if upper(row.get("priority")) == "HIGH_VALUE_TARGET"]
    monitor = [row for row in rows if upper(row.get("priority")) == "MONITOR_ONLY"]
    low = [row for row in rows if upper(row.get("priority")) == "LOW_PRIORITY"]

    def grade_for(field: str, value: str) -> str:
        for row in rows:
            if upper(row.get(field)) == value:
                return upper(row.get("current_quality_grade")) or "UNKNOWN"
        return "UNKNOWN"

    summary = [
        {"metric": "target_rows", "value": len(rows)},
        {"metric": "critical_targets", "value": len(critical)},
        {"metric": "high_value_targets", "value": len(high)},
        {"metric": "monitor_only_targets", "value": len(monitor)},
        {"metric": "low_priority_targets", "value": len(low)},
        {"metric": "horsham_targets", "value": sum(1 for row in rows if upper(row.get("track")) == "HORSHAM")},
        {"metric": "country_targets", "value": sum(1 for row in rows if "COUNTRY" in upper(row.get("target_reason")))},
        {"metric": "bm56_targets", "value": sum(1 for row in rows if upper(row.get("race_class")) == "BM56")},
        {"metric": "bm64_targets", "value": sum(1 for row in rows if upper(row.get("race_class")) == "BM64")},
        {"metric": "mile_targets", "value": sum(1 for row in rows if upper(row.get("distance_bucket")) == "MILE")},
        {"metric": "medium_tempo_targets", "value": sum(1 for row in rows if upper(row.get("tempo_bucket")) == "MEDIUM")},
        {"metric": "survived_walkforward_targets", "value": sum(1 for row in rows if upper(row.get("walkforward_status")) == "SURVIVED_WALKFORWARD")},
        {"metric": "active_stable_research_targets", "value": sum(1 for row in rows if "ACTIVE_STABLE_RESEARCH" in upper(row.get("stable_research_status")) or "ACTIVE_STABLE_RESEARCH" in upper(row.get("target_reason")))},
        {"metric": "horsham_quality_grade", "value": grade_for("track", "HORSHAM")},
        {"metric": "bm56_quality_grade", "value": grade_for("race_class", "BM56")},
        {"metric": "bm64_quality_grade", "value": grade_for("race_class", "BM64")},
        {"metric": "mile_quality_grade", "value": grade_for("distance_bucket", "MILE")},
        {"metric": "medium_tempo_quality_grade", "value": grade_for("tempo_bucket", "MEDIUM")},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "offline_research_only", "value": "YES"},
    ]
    for filename in missing_inputs:
        summary.append({"metric": f"missing_input::{filename}", "value": "YES"})
    return summary


def main() -> None:
    missing_inputs = [path.name for path in INPUTS.values() if not path.exists()]
    acquisition_rows = read_csv(INPUTS["acquisition"])
    shadow_rows = read_csv(INPUTS["shadow_state"])
    stable_rows = read_csv(INPUTS["stable_regimes"])
    walkforward_rows = read_csv(INPUTS["walkforward"])

    acquisition = build_acquisition_index(acquisition_rows)
    shadow = build_shadow_index(shadow_rows)
    stable = build_stable_index(stable_rows)
    walkforward = build_walkforward_index(walkforward_rows)

    target_rows = build_target_rows(acquisition, shadow, stable, walkforward)
    summary_rows = build_summary(target_rows, missing_inputs)

    write_csv(OUT, target_rows, TARGET_FIELDS)
    write_csv(SUMMARY, summary_rows, SUMMARY_FIELDS)

    print("=" * 88)
    print("EDGEIQ TARGETED SECTIONAL HARVEST PIPELINE V1")
    print("=" * 88)
    for row in summary_rows:
        if not clean(row.get("metric")).startswith("missing_input::"):
            print(f"{row['metric']}: {row['value']}")
    if missing_inputs:
        print("missing inputs:", ", ".join(missing_inputs))
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")


if __name__ == "__main__":
    main()
