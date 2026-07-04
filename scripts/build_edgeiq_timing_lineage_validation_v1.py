from __future__ import annotations

import csv
import re
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LADDERS = DATA / "edgeiq_raw_sectional_extracted_split_ladders_v1.csv"
PARSER = DATA / "edgeiq_raw_sectional_payload_schema_parser_v1.csv"
ENHANCED = DATA / "edgeiq_enhanced_temporal_phase_confidence_v2.csv"
QUALITY = DATA / "edgeiq_sectional_payload_quality_v1.csv"

OUT = DATA / "edgeiq_timing_lineage_validation_v1.csv"
SUMMARY = DATA / "edgeiq_timing_lineage_summary_v1.csv"
CONFLICTS = DATA / "edgeiq_timing_lineage_conflicts_v1.csv"

OUT_FIELDS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "payload_source",
    "schema_type",
    "lineage_depth",
    "direct_source_confidence",
    "reconstruction_dependency",
    "schema_consistency_score",
    "timing_chain_integrity",
    "duplicate_lineage_detected",
    "conflicting_timing_detected",
    "lineage_trust_grade",
    "lineage_status",
    "safe_for_temporal_research",
    "safe_for_shadow_research",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

CONFLICT_FIELDS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "payload_source",
    "schema_type",
    "conflict_type",
    "conflict_severity",
    "split_marker",
    "values_seen",
    "lineage_count",
    "recommended_resolution",
    "notes",
]

GRADE_LABEL = {
    "A": "DIRECT_HIGH_CONFIDENCE_LINEAGE",
    "B": "STRONG_LINEAGE",
    "C": "USABLE_LINEAGE",
    "D": "WEAK_LINEAGE",
    "F": "UNTRUSTED_LINEAGE",
}


def clean(value: object) -> str:
    return str(value or "").strip()


def upper(value: object) -> str:
    return clean(value).upper()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="", errors="ignore") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    except (OSError, csv.Error):
        return []


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{time.time_ns()}.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    tmp.replace(path)


def parse_float(value: object, default: float = 0.0) -> float:
    text = clean(value).replace(",", "")
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def normal_date(value: object) -> str:
    text = clean(value)
    if not text:
        return ""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text


def normal_track(value: object) -> str:
    text = upper(value)
    aliases = {
        "BET365 YARRA VALLEY": "YARRA VALLEY",
        "BET365 PARK KILMORE": "KILMORE",
        "BET365 KILMORE": "KILMORE",
        "LADBROKES GEELONG": "GEELONG",
        "SPORTSBET SANDOWN HILLSIDE": "SANDOWN",
        "SPORTSBET SANDOWN LAKESIDE": "SANDOWN",
        "SANDOWN HILLSIDE": "SANDOWN",
        "SANDOWN LAKESIDE": "SANDOWN",
    }
    return aliases.get(text, text)


def normal_horse(value: object) -> str:
    text = upper(value)
    text = re.sub(r"\([A-Z]{2,3}\)", "", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return " ".join(text.split())


def runner_key(row: dict[str, str]) -> str:
    return "|".join([normal_date(row.get("race_date")), normal_track(row.get("track")), clean(row.get("race_no")), normal_horse(row.get("horse"))])


def lineage_key(row: dict[str, str]) -> str:
    return "|".join([runner_key(row), clean(row.get("payload_source")), clean(row.get("schema_type"))])


def build_parser_index(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    best: dict[str, dict[str, str]] = {}
    for row in rows:
        key = lineage_key(row)
        if not key.strip("|"):
            continue
        existing = best.get(key)
        if not existing or parse_float(row.get("schema_confidence")) > parse_float(existing.get("schema_confidence")):
            best[key] = row
    return best


def build_runner_index(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = runner_key(row)
        if key.strip("|"):
            grouped[key].append(row)
    return grouped


def build_enhanced_index(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    best: dict[str, dict[str, str]] = {}
    for row in rows:
        key = runner_key(row)
        if not key.strip("|"):
            continue
        existing = best.get(key)
        if not existing or parse_float(row.get("new_phase_confidence")) > parse_float(existing.get("new_phase_confidence")):
            best[key] = row
    return best


def build_quality_index(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = runner_key(row)
        if key.strip("|"):
            grouped[key].append(row)
    return grouped


def split_values(values: list[dict[str, str]]) -> dict[str, list[float]]:
    result: dict[str, list[float]] = defaultdict(list)
    for row in values:
        marker = upper(row.get("split_marker"))
        value = parse_float(row.get("split_time") or row.get("sectional_time"), default=-1)
        if marker and value >= 0:
            result[marker].append(value)
    return result


def detect_conflicts(values: list[dict[str, str]]) -> tuple[bool, list[dict[str, object]]]:
    conflicts: list[dict[str, object]] = []
    if not values:
        return False, conflicts
    base = values[0]
    grouped = split_values(values)
    for marker, nums in grouped.items():
        rounded = sorted({round(num, 2) for num in nums})
        if len(rounded) > 1 and (max(rounded) - min(rounded)) > 0.08:
            conflicts.append(
                {
                    "race_date": clean(base.get("race_date")),
                    "track": clean(base.get("track")),
                    "race_no": clean(base.get("race_no")),
                    "horse": clean(base.get("horse")),
                    "payload_source": clean(base.get("payload_source")),
                    "schema_type": clean(base.get("schema_type")),
                    "conflict_type": "CONFLICTING_SPLIT_TIME",
                    "conflict_severity": "HIGH" if (max(rounded) - min(rounded)) > 0.3 else "MEDIUM",
                    "split_marker": marker,
                    "values_seen": "|".join(f"{num:.2f}" for num in rounded),
                    "lineage_count": len(values),
                    "recommended_resolution": "Preserve all chains and prefer direct source with highest schema confidence; do not silently merge.",
                    "notes": "Timing lineage conflict diagnostics only. Offline research; no execution impact.",
                }
            )
    return bool(conflicts), conflicts


def direct_confidence(schema_type: str, payload_source: str, parser_row: dict[str, str] | None, values: list[dict[str, str]]) -> float:
    schema = upper(schema_type)
    source = upper(payload_source)
    base = 35.0
    if "DIRECT_SECTIONAL_CSV_SPLIT_LADDER" in schema:
        base = 91.0
    elif "PAYLOAD_QUALITY_CONFIRMED" in schema:
        base = 70.0
    elif "GRAPHQL" in schema:
        base = 55.0
    if "RECONSTRUCTION" in source or "RECONSTRUCTION" in schema:
        base -= 35.0
    if parser_row:
        base = max(base, parse_float(parser_row.get("schema_confidence")) * 0.9)
    markers = {upper(row.get("split_marker")) for row in values if clean(row.get("split_marker"))}
    if {"LAST_600", "LAST_400", "LAST_200"}.issubset(markers):
        base += 6.0
    return max(0.0, min(100.0, base))


def reconstruction_dependency(schema_type: str, payload_source: str, quality_rows: list[dict[str, str]]) -> str:
    text = f"{schema_type} {payload_source}".upper()
    if "RECONSTRUCTION" in text:
        return "HIGH"
    if any(upper(row.get("quality_blocker")) == "UNSAFE_RECONSTRUCTION_RISK" for row in quality_rows):
        return "HIGH"
    if any(parse_float(row.get("reconstruction_risk_score")) >= 45 for row in quality_rows):
        return "MEDIUM"
    if "DIRECT_SECTIONAL_CSV" in text:
        return "LOW"
    return "MEDIUM"


def schema_consistency(parser_row: dict[str, str] | None, values: list[dict[str, str]]) -> float:
    markers = {upper(row.get("split_marker")) for row in values if clean(row.get("split_marker"))}
    split_score = min(100.0, len(markers) / 3.0 * 100.0)
    parser_score = parse_float(parser_row.get("schema_confidence")) if parser_row else 35.0
    return min(100.0, split_score * 0.58 + parser_score * 0.42)


def timing_integrity(values: list[dict[str, str]], conflict: bool) -> float:
    if not values:
        return 0.0
    grouped = split_values(values)
    score = 40.0
    if {"LAST_600", "LAST_400", "LAST_200"}.issubset(grouped.keys()):
        score += 38.0
    elif grouped:
        score += min(30.0, len(grouped) * 10.0)
    first = values[0]
    if clean(first.get("early_phase_value")) and clean(first.get("mid_phase_value")) and clean(first.get("late_phase_value")):
        score += 16.0
    if conflict:
        score -= 35.0
    return max(0.0, min(100.0, score))


def grade_lineage(score: float, conflict: bool, dependency: str) -> str:
    if conflict or score < 35:
        return "F"
    if score >= 88 and dependency == "LOW":
        return "A"
    if score >= 75:
        return "B"
    if score >= 58:
        return "C"
    if score >= 42:
        return "D"
    return "F"


def safe_flags(grade: str, conflict: bool, dependency: str) -> tuple[str, str]:
    temporal = "YES" if grade in {"A", "B", "C"} and not conflict else "NO"
    shadow = "YES" if grade in {"A", "B"} and not conflict and dependency != "HIGH" else "NO"
    return temporal, shadow


def main() -> None:
    ladder_rows = read_csv(LADDERS)
    parser_rows = read_csv(PARSER)
    enhanced_rows = read_csv(ENHANCED)
    quality_rows = read_csv(QUALITY)

    parser_index = build_parser_index(parser_rows)
    runner_lineages: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in ladder_rows:
        key = lineage_key(row)
        if key.strip("|"):
            runner_lineages[key].append(row)

    quality_index = build_quality_index(quality_rows)
    enhanced_index = build_enhanced_index(enhanced_rows)
    runner_to_lineage_count = Counter(runner_key(row) for row in ladder_rows if runner_key(row).strip("|"))

    out_rows: list[dict[str, object]] = []
    conflict_rows: list[dict[str, object]] = []
    for key, values in runner_lineages.items():
        first = values[0]
        runner = runner_key(first)
        parser_row = parser_index.get(key)
        q_rows = quality_index.get(runner, [])
        enhanced = enhanced_index.get(runner, {})
        conflict, conflicts = detect_conflicts(values)
        conflict_rows.extend(conflicts)
        duplicate = runner_to_lineage_count[runner] > len(values)
        depth = len({upper(row.get("split_marker")) for row in values if clean(row.get("split_marker"))})
        source = clean(first.get("payload_source"))
        schema = clean(first.get("schema_type"))
        direct = direct_confidence(schema, source, parser_row, values)
        dependency = reconstruction_dependency(schema, source, q_rows)
        consistency = schema_consistency(parser_row, values)
        integrity = timing_integrity(values, conflict)
        enhanced_conf = parse_float(enhanced.get("new_phase_confidence"))
        combined = direct * 0.30 + consistency * 0.24 + integrity * 0.28 + enhanced_conf * 0.18
        if dependency == "HIGH":
            combined -= 18.0
        elif dependency == "MEDIUM":
            combined -= 5.0
        if duplicate:
            combined -= 6.0
        grade = grade_lineage(combined, conflict, dependency)
        temporal_safe, shadow_safe = safe_flags(grade, conflict, dependency)
        out_rows.append(
            {
                "race_date": clean(first.get("race_date")),
                "track": clean(first.get("track")),
                "race_no": clean(first.get("race_no")),
                "horse": clean(first.get("horse")),
                "payload_source": source,
                "schema_type": schema,
                "lineage_depth": depth,
                "direct_source_confidence": f"{direct:.2f}",
                "reconstruction_dependency": dependency,
                "schema_consistency_score": f"{consistency:.2f}",
                "timing_chain_integrity": f"{integrity:.2f}",
                "duplicate_lineage_detected": "YES" if duplicate else "NO",
                "conflicting_timing_detected": "YES" if conflict else "NO",
                "lineage_trust_grade": grade,
                "lineage_status": GRADE_LABEL[grade],
                "safe_for_temporal_research": temporal_safe,
                "safe_for_shadow_research": shadow_safe,
                "notes": "Offline timing lineage validation only. No predictions, overlays, live modelling, ratings, or execution.",
            }
        )

    out_rows.sort(key=lambda row: (clean(row.get("lineage_trust_grade")), clean(row.get("race_date")), clean(row.get("track")), clean(row.get("race_no")), clean(row.get("horse"))))
    conflict_rows.sort(key=lambda row: (clean(row.get("race_date")), clean(row.get("track")), clean(row.get("race_no")), clean(row.get("horse")), clean(row.get("split_marker"))))

    grades = Counter(clean(row.get("lineage_trust_grade")) for row in out_rows)
    statuses = Counter(clean(row.get("lineage_status")) for row in out_rows)
    dependencies = Counter(clean(row.get("reconstruction_dependency")) for row in out_rows)
    summary_rows = [
        {"metric": "lineage_rows", "value": len(out_rows)},
        {"metric": "direct_low_dependency_rows", "value": dependencies.get("LOW", 0)},
        {"metric": "medium_reconstruction_dependency_rows", "value": dependencies.get("MEDIUM", 0)},
        {"metric": "high_reconstruction_dependency_rows", "value": dependencies.get("HIGH", 0)},
        {"metric": "duplicate_lineage_rows", "value": sum(1 for row in out_rows if row.get("duplicate_lineage_detected") == "YES")},
        {"metric": "conflicting_timing_rows", "value": sum(1 for row in out_rows if row.get("conflicting_timing_detected") == "YES")},
        {"metric": "conflict_records", "value": len(conflict_rows)},
        {"metric": "grade_A_direct_high_confidence", "value": grades.get("A", 0)},
        {"metric": "grade_B_strong", "value": grades.get("B", 0)},
        {"metric": "grade_C_usable", "value": grades.get("C", 0)},
        {"metric": "grade_D_weak", "value": grades.get("D", 0)},
        {"metric": "grade_F_untrusted", "value": grades.get("F", 0)},
        {"metric": "safe_for_temporal_research_yes", "value": sum(1 for row in out_rows if row.get("safe_for_temporal_research") == "YES")},
        {"metric": "safe_for_shadow_research_yes", "value": sum(1 for row in out_rows if row.get("safe_for_shadow_research") == "YES")},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "offline_research_only", "value": "YES"},
    ]
    for status, count in statuses.most_common():
        summary_rows.append({"metric": f"lineage_status::{status}", "value": count})

    write_csv(OUT, out_rows, OUT_FIELDS)
    write_csv(SUMMARY, summary_rows, SUMMARY_FIELDS)
    write_csv(CONFLICTS, conflict_rows, CONFLICT_FIELDS)

    print("=" * 88)
    print("EDGEIQ TIMING LINEAGE VALIDATION V1")
    print("=" * 88)
    for row in summary_rows[:17]:
        print(f"{row['metric']}: {row['value']}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {CONFLICTS}")


if __name__ == "__main__":
    main()
