from __future__ import annotations

import csv
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

DISCOVERY = DATA / "edgeiq_raw_sectional_payload_discovery_v1.csv"
SOURCE_MAP = DATA / "edgeiq_raw_sectional_payload_source_map_v1.csv"
QUALITY = DATA / "edgeiq_sectional_payload_quality_v1.csv"

OUT = DATA / "edgeiq_raw_sectional_payload_schema_parser_v1.csv"
SUMMARY = DATA / "edgeiq_raw_sectional_payload_schema_summary_v1.csv"
LADDERS = DATA / "edgeiq_raw_sectional_extracted_split_ladders_v1.csv"

PARSE_FIELDS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "payload_source",
    "schema_type",
    "split_marker",
    "split_distance",
    "split_time",
    "sectional_time",
    "cumulative_time",
    "rank_at_split",
    "position_at_split",
    "early_phase_value",
    "mid_phase_value",
    "late_phase_value",
    "schema_confidence",
    "extraction_status",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

TARGET_DISCOVERIES = {"HIGH_VALUE_PAYLOAD_DISCOVERY", "MEDIUM_VALUE_DISCOVERY"}
STATUS_ORDER = {
    "FULL_SPLIT_LADDER_EXTRACTED": 5,
    "PARTIAL_SPLIT_LADDER_EXTRACTED": 4,
    "HORSE_LEVEL_TIMING_EXTRACTED": 3,
    "SCHEMA_DETECTED_NOT_EXTRACTED": 2,
    "UNUSABLE_SCHEMA": 1,
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


def parse_float(value: object) -> float | None:
    text = clean(value)
    if not text:
        return None
    text = text.replace("$", "").replace(",", "").replace("L", "")
    try:
        return float(text)
    except ValueError:
        return None


def parse_int(value: object) -> int | None:
    num = parse_float(value)
    if num is None:
        return None
    return int(num)


def relative_source_path(path_text: str) -> Path | None:
    text = clean(path_text).replace("/", "\\")
    if not text:
        return None
    candidate = ROOT / text
    if candidate.exists():
        return candidate
    if text.lower().startswith("dashboard\\racing-dashboard\\"):
        stripped = text.split("dashboard\\racing-dashboard\\", 1)[1]
        candidate = ROOT / stripped
        if candidate.exists():
            return candidate
    return None


def target_source_files(source_map_rows: list[dict[str, str]]) -> set[str]:
    files = set()
    for row in source_map_rows:
        if upper(row.get("opportunity_type")) not in TARGET_DISCOVERIES:
            continue
        source_file = clean(row.get("source_file"))
        if source_file:
            files.add(source_file.replace("/", "\\"))
    return files


def discovery_hints(discovery_rows: list[dict[str, str]]) -> set[str]:
    hints = set()
    for row in discovery_rows:
        if upper(row.get("payload_quality_potential")) not in TARGET_DISCOVERIES:
            continue
        hint = clean(row.get("source_hint"))
        if hint:
            hints.add(hint.replace("/", "\\"))
    return hints


def status_for_row(row: dict[str, str]) -> str:
    last_count = sum(1 for key in ["last_600", "last_400", "last_200"] if parse_float(row.get(key)) is not None)
    phase_count = sum(1 for key in ["early_speed", "mid_speed", "late_speed"] if parse_float(row.get(key)) is not None)
    if last_count == 3 and phase_count >= 2:
        return "FULL_SPLIT_LADDER_EXTRACTED"
    if last_count >= 1:
        return "PARTIAL_SPLIT_LADDER_EXTRACTED"
    if phase_count >= 1 or parse_float(row.get("race_time")) is not None or parse_float(row.get("top_speed")) is not None:
        return "HORSE_LEVEL_TIMING_EXTRACTED"
    return "UNUSABLE_SCHEMA"


def confidence_for_status(status: str, row: dict[str, str]) -> str:
    base = {
        "FULL_SPLIT_LADDER_EXTRACTED": 88,
        "PARTIAL_SPLIT_LADDER_EXTRACTED": 68,
        "HORSE_LEVEL_TIMING_EXTRACTED": 52,
        "SCHEMA_DETECTED_NOT_EXTRACTED": 35,
        "UNUSABLE_SCHEMA": 10,
    }.get(status, 10)
    if upper(row.get("parse_status")) == "PARSED":
        base += 5
    if upper(row.get("source_quality_grade")) in {"A", "B"}:
        base += 4
    if upper(row.get("source_quality_grade")) == "F":
        base -= 10
    return str(max(0, min(100, base)))


def make_summary_parse_row(row: dict[str, str], source: str, schema_type: str, status: str) -> dict[str, object]:
    return {
        "race_date": clean(row.get("race_date")),
        "track": clean(row.get("track")),
        "race_no": clean(row.get("race_no")),
        "horse": clean(row.get("horse")),
        "payload_source": source,
        "schema_type": schema_type,
        "split_marker": "",
        "split_distance": "",
        "split_time": "",
        "sectional_time": "",
        "cumulative_time": clean(row.get("race_time") or row.get("winningTime")),
        "rank_at_split": clean(row.get("sectional_rank")),
        "position_at_split": clean(row.get("position") or row.get("finish_pos") or row.get("finish")),
        "early_phase_value": clean(row.get("early_speed") or row.get("early_phase_value")),
        "mid_phase_value": clean(row.get("mid_speed") or row.get("mid_phase_value")),
        "late_phase_value": clean(row.get("late_speed") or row.get("late_phase_value")),
        "schema_confidence": confidence_for_status(status, row),
        "extraction_status": status,
        "notes": "Offline cached/local schema parse only. No scraping, live modelling, predictions, overlays, ratings, or execution.",
    }


def ladder_rows_from_sectional_row(row: dict[str, str], source: str, schema_type: str, status: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    split_defs = [
        ("LAST_600", "600", "last_600", "last_600_rank"),
        ("LAST_400", "400", "last_400", "last_400_rank"),
        ("LAST_200", "200", "last_200", "last_200_rank"),
    ]
    for marker, distance, time_key, rank_key in split_defs:
        value = parse_float(row.get(time_key))
        if value is None:
            continue
        rows.append(
            {
                "race_date": clean(row.get("race_date")),
                "track": clean(row.get("track")),
                "race_no": clean(row.get("race_no")),
                "horse": clean(row.get("horse")),
                "payload_source": source,
                "schema_type": schema_type,
                "split_marker": marker,
                "split_distance": distance,
                "split_time": f"{value:.2f}",
                "sectional_time": f"{value:.2f}",
                "cumulative_time": "",
                "rank_at_split": clean(row.get(rank_key)),
                "position_at_split": clean(row.get("sectional_rank")),
                "early_phase_value": clean(row.get("early_speed")),
                "mid_phase_value": clean(row.get("mid_speed")),
                "late_phase_value": clean(row.get("late_speed")),
                "schema_confidence": confidence_for_status(status, row),
                "extraction_status": status,
                "notes": "Extracted from cached/local parsed sectional source. Offline research only.",
            }
        )
    return rows


def parse_sectional_source_ingestion() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    path = DATA / "edgeiq_sectional_source_ingestion_v1.csv"
    source = "public/data/edgeiq_sectional_source_ingestion_v1.csv"
    rows = read_csv(path)
    parser_rows: list[dict[str, object]] = []
    ladder_rows: list[dict[str, object]] = []
    for row in rows:
        status = status_for_row(row)
        if status == "UNUSABLE_SCHEMA":
            continue
        schema_type = "DIRECT_SECTIONAL_CSV_SPLIT_LADDER"
        parser_rows.append(make_summary_parse_row(row, source, schema_type, status))
        ladder_rows.extend(ladder_rows_from_sectional_row(row, source, schema_type, status))
    return parser_rows, ladder_rows


def decode_json(value: object) -> dict[str, object]:
    text = clean(value)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def parse_graphql_parser_rows() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    path = DATA / "edgeiq_racingcom_graphql_parser_v1.csv"
    source = "public/data/edgeiq_racingcom_graphql_parser_v1.csv"
    rows = read_csv(path)
    parser_rows: list[dict[str, object]] = []
    ladder_rows: list[dict[str, object]] = []
    for row in rows:
        runner_json = decode_json(row.get("runner_fields_json"))
        sectional_json = decode_json(row.get("sectional_fields_json"))
        merged = dict(row)
        for key in ["position", "finish", "winningTime", "standardTimeDifference"]:
            if key in runner_json and not clean(merged.get(key)):
                merged[key] = clean(runner_json.get(key))
        for key in ["last_600", "last_400", "last_200", "early_speed", "mid_speed", "late_speed"]:
            if key in sectional_json and not clean(merged.get(key)):
                merged[key] = clean(sectional_json.get(key))
        has_timing = any(clean(merged.get(key)) for key in ["speed_value", "top_speed", "distance_travelled", "race_time", "winningTime"])
        has_horse = clean(merged.get("horse"))
        if not has_horse:
            continue
        status = status_for_row(merged)
        if status == "UNUSABLE_SCHEMA" and has_timing:
            status = "HORSE_LEVEL_TIMING_EXTRACTED"
        elif status == "UNUSABLE_SCHEMA":
            status = "SCHEMA_DETECTED_NOT_EXTRACTED"
        schema_type = "RACINGCOM_GRAPHQL_RUNNER_TIMING_METADATA"
        parser_rows.append(make_summary_parse_row(merged, source, schema_type, status))
        ladder_rows.extend(ladder_rows_from_sectional_row(merged, source, schema_type, status))
    return parser_rows, ladder_rows


def parse_payload_quality_rows() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    source = "public/data/edgeiq_sectional_payload_quality_v1.csv"
    rows = read_csv(QUALITY)
    parser_rows: list[dict[str, object]] = []
    ladder_rows: list[dict[str, object]] = []
    for row in rows:
        grade = upper(row.get("source_quality_grade"))
        if grade not in {"A", "B"} and upper(row.get("safe_for_shadow_research")) != "YES":
            continue
        merged = dict(row)
        merged["early_speed"] = row.get("early_phase_value", "")
        merged["mid_speed"] = row.get("mid_phase_value", "")
        merged["late_speed"] = row.get("late_phase_value", "")
        status = status_for_row(merged)
        if status == "UNUSABLE_SCHEMA":
            if parse_float(row.get("phase_confidence_score")) is not None:
                status = "HORSE_LEVEL_TIMING_EXTRACTED"
            else:
                continue
        schema_type = "PAYLOAD_QUALITY_CONFIRMED_SECTIONAL_SCHEMA"
        parser_rows.append(make_summary_parse_row(merged, source, schema_type, status))
    return parser_rows, ladder_rows


def schema_detected_rows(source_map_rows: list[dict[str, str]], existing_sources: set[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in source_map_rows:
        if upper(row.get("opportunity_type")) not in TARGET_DISCOVERIES:
            continue
        source_file = clean(row.get("source_file"))
        if source_file in existing_sources:
            continue
        status = "SCHEMA_DETECTED_NOT_EXTRACTED"
        if not clean(row.get("detected_fields")):
            status = "UNUSABLE_SCHEMA"
        rows.append(
            {
                "race_date": "",
                "track": "",
                "race_no": "",
                "horse": "",
                "payload_source": source_file or clean(row.get("source_hint")),
                "schema_type": clean(row.get("payload_family")) or clean(row.get("source_type")),
                "split_marker": "",
                "split_distance": "",
                "split_time": "",
                "sectional_time": "",
                "cumulative_time": "",
                "rank_at_split": "",
                "position_at_split": "",
                "early_phase_value": "",
                "mid_phase_value": "",
                "late_phase_value": "",
                "schema_confidence": "35" if status == "SCHEMA_DETECTED_NOT_EXTRACTED" else "10",
                "extraction_status": status,
                "notes": "Schema is present in high/medium discovery map, but no parseable local horse-level payload was available in this workspace.",
            }
        )
    return rows


def dedupe(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    seen = set()
    out = []
    for row in rows:
        key = tuple(clean(row.get(field)) for field in ["race_date", "track", "race_no", "horse", "payload_source", "schema_type", "split_marker", "split_distance", "split_time", "extraction_status"])
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def build_summary(parser_rows: list[dict[str, object]], ladder_rows: list[dict[str, object]], source_map_rows: list[dict[str, str]], discovery_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    statuses = Counter(clean(row.get("extraction_status")) for row in parser_rows)
    schemas = Counter(clean(row.get("schema_type")) for row in parser_rows)
    horses = {upper(row.get("horse")) for row in parser_rows if clean(row.get("horse"))}
    races = {f"{clean(row.get('race_date'))}|{upper(row.get('track'))}|{clean(row.get('race_no'))}" for row in parser_rows if clean(row.get("race_date")) or clean(row.get("track")) or clean(row.get("race_no"))}
    high_medium_discoveries = sum(1 for row in discovery_rows if upper(row.get("payload_quality_potential")) in TARGET_DISCOVERIES)
    high_medium_sources = sum(1 for row in source_map_rows if upper(row.get("opportunity_type")) in TARGET_DISCOVERIES)
    summary = [
        {"metric": "parser_rows", "value": len(parser_rows)},
        {"metric": "extracted_split_ladder_rows", "value": len(ladder_rows)},
        {"metric": "unique_horses_extracted", "value": len(horses)},
        {"metric": "unique_races_extracted", "value": len(races)},
        {"metric": "high_medium_discoveries_processed", "value": high_medium_discoveries},
        {"metric": "high_medium_source_map_rows_processed", "value": high_medium_sources},
        {"metric": "full_split_ladder_extracted", "value": statuses.get("FULL_SPLIT_LADDER_EXTRACTED", 0)},
        {"metric": "partial_split_ladder_extracted", "value": statuses.get("PARTIAL_SPLIT_LADDER_EXTRACTED", 0)},
        {"metric": "horse_level_timing_extracted", "value": statuses.get("HORSE_LEVEL_TIMING_EXTRACTED", 0)},
        {"metric": "schema_detected_not_extracted", "value": statuses.get("SCHEMA_DETECTED_NOT_EXTRACTED", 0)},
        {"metric": "unusable_schema", "value": statuses.get("UNUSABLE_SCHEMA", 0)},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "offline_research_only", "value": "YES"},
    ]
    for schema, count in schemas.most_common():
        summary.append({"metric": f"schema::{schema}", "value": count})
    return summary


def main() -> None:
    discovery_rows = read_csv(DISCOVERY)
    source_map_rows = read_csv(SOURCE_MAP)
    target_files = target_source_files(source_map_rows)
    hints = discovery_hints(discovery_rows)

    parser_rows: list[dict[str, object]] = []
    ladder_rows: list[dict[str, object]] = []
    parsed_sources: set[str] = set()

    if any("edgeiq_sectional_source_ingestion_v1.csv" in item for item in target_files | hints):
        rows, ladders = parse_sectional_source_ingestion()
        parser_rows.extend(rows)
        ladder_rows.extend(ladders)
        parsed_sources.add("public\\data\\edgeiq_sectional_source_ingestion_v1.csv")

    if any("edgeiq_racingcom_graphql_parser_v1.csv" in item for item in target_files | hints):
        rows, ladders = parse_graphql_parser_rows()
        parser_rows.extend(rows)
        ladder_rows.extend(ladders)
        parsed_sources.add("public\\data\\edgeiq_racingcom_graphql_parser_v1.csv")

    rows, ladders = parse_payload_quality_rows()
    parser_rows.extend(rows)
    ladder_rows.extend(ladders)
    parsed_sources.add("public\\data\\edgeiq_sectional_payload_quality_v1.csv")

    parser_rows.extend(schema_detected_rows(source_map_rows, parsed_sources))
    parser_rows = dedupe(parser_rows)
    ladder_rows = dedupe(ladder_rows)
    parser_rows.sort(key=lambda row: (-STATUS_ORDER.get(clean(row.get("extraction_status")), 0), clean(row.get("payload_source")), clean(row.get("race_date")), clean(row.get("track")), clean(row.get("race_no")), clean(row.get("horse"))))
    ladder_rows.sort(key=lambda row: (clean(row.get("payload_source")), clean(row.get("race_date")), clean(row.get("track")), clean(row.get("race_no")), clean(row.get("horse")), clean(row.get("split_distance"))))
    summary_rows = build_summary(parser_rows, ladder_rows, source_map_rows, discovery_rows)

    write_csv(OUT, parser_rows, PARSE_FIELDS)
    write_csv(SUMMARY, summary_rows, SUMMARY_FIELDS)
    write_csv(LADDERS, ladder_rows, PARSE_FIELDS)

    print("=" * 88)
    print("EDGEIQ RAW SECTIONAL PAYLOAD SCHEMA PARSER V1")
    print("=" * 88)
    for row in summary_rows[:14]:
        print(f"{row['metric']}: {row['value']}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {LADDERS}")


if __name__ == "__main__":
    main()
