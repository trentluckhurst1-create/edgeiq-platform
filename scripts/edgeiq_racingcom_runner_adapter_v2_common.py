from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"

PRODUCTION = DATA / "edgeiq_racingcom_performance_warehouse_v2.csv"
CSV_PARSER = DOCS / "edgeiq_racingcom_parser_output_v2.csv"
CSV_ACQ = DOCS / "edgeiq_racingcom_csv_acquisition_v2.csv"
CANONICAL_DOCS = DOCS / "edgeiq_racingcom_canonical_speed_contract_v1.csv"
GRAPHQL_PARSER = DOCS / "edgeiq_racingcom_graphql_parser_output_v2.csv"
GRAPHQL_ACQ = DOCS / "edgeiq_racingcom_graphql_acquisition_v1.csv"
GRAPHQL_ADMISSION = DOCS / "edgeiq_racingcom_graphql_source_admission_v1.csv"

CANONICAL_PUBLIC = DATA / "edgeiq_racingcom_canonical_speed_data_v2.csv"
GRAPHQL_NORMALISED_PUBLIC = DATA / "edgeiq_racingcom_graphql_speed_normalised_v1.csv"
RUNNER_CANDIDATE = DATA / "edgeiq_racingcom_performance_warehouse_v2_RUNNER_CANDIDATE.csv"
RUNNER_EXTENDED = DATA / "edgeiq_racingcom_performance_warehouse_v2_RUNNER_EXTENDED.csv"

PRODUCTION_COLUMNS = [
    "warehouse_record_id", "race_id", "race_date", "track", "state", "race_no", "distance", "horse", "horse_key", "barrier",
    "last200", "last400", "last600", "last_200", "last_400", "last_600", "early_speed", "mid_speed", "late_speed",
    "peak_speed", "avg_speed", "race_time", "tempo_grade", "pace_profile", "sectional_source", "source_csv_url", "source_cache_path",
    "source_sha256", "acquisition_timestamp", "parser_version", "pipeline_version", "meeting_discovery_version", "race_discovery_version",
    "admission_version", "warehouse_built_utc",
]


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"", "NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def columns(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle).fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, Any]], cols: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if cols is None:
        cols = list(rows[0].keys()) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: clean(row.get(col, "")) for col in cols})


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def key(row: dict[str, Any]) -> tuple[str, str]:
    return clean(row.get("race_id")), clean(row.get("horse_key"))


def horse_key_from_name(name: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean(name).upper())


def fnum(value: Any) -> float | None:
    text = clean(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_time_seconds(value: Any) -> float | None:
    text = clean(value)
    if not text:
        return None
    if re.fullmatch(r"\d+(\.\d+)?", text):
        return float(text)
    bits = text.split(":")
    try:
        if len(bits) == 3:
            return int(bits[0]) * 3600 + int(bits[1]) * 60 + float(bits[2])
        if len(bits) == 2:
            return int(bits[0]) * 60 + float(bits[1])
    except ValueError:
        return None
    return None


def fmt_seconds(value: float | None) -> str:
    return "" if value is None else f"{value:.2f}"


def fmt_speed(value: float | None) -> str:
    return "" if value is None else f"{value:.3f}"


def distance_start(label: str) -> int | None:
    label = clean(label).upper()
    if "FINISH" in label:
        match = re.match(r"(\d+)\s*M", label)
        return int(match.group(1)) if match else 0
    match = re.match(r"(\d+)\s*M", label)
    return int(match.group(1)) if match else None


def race_distance_from_splits(rows: list[dict[str, str]]) -> str:
    starts = [distance_start(r.get("distance_label", "")) for r in rows if clean(r.get("row_type")) == "SPLIT"]
    starts = [s for s in starts if s is not None]
    if starts:
        return str(max(starts))
    distances = [fnum(r.get("distance_run")) for r in rows]
    distances = [d for d in distances if d is not None]
    return str(int(round(max(distances)))) if distances else ""


def latest_graphql_acquired_utc() -> str:
    values = [clean(r.get("acquired_utc") or r.get("request_timestamp") or r.get("parsed_utc")) for r in read_csv(GRAPHQL_ACQ)]
    values = sorted(v for v in values if v)
    return values[-1] if values else "GRAPHQL_ACQUISITION_UTC_UNKNOWN"


def copy_public_canonical_sources() -> None:
    canonical = read_csv(CANONICAL_DOCS)
    write_csv(CANONICAL_PUBLIC, canonical, columns(CANONICAL_DOCS))
    graphql = read_csv(GRAPHQL_PARSER)
    write_csv(GRAPHQL_NORMALISED_PUBLIC, graphql, columns(GRAPHQL_PARSER))


def build_runner_candidate() -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, Any]]]:
    copy_public_canonical_sources()
    production_rows = [row for row in read_csv(PRODUCTION) if clean(row.get("sectional_source")) == "RACING.COM_DIRECT_CSV_V2"]
    graphql_rows = read_csv(GRAPHQL_PARSER)
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in graphql_rows:
        race_id = clean(row.get("race_id"))
        hkey = horse_key_from_name(row.get("horse"))
        if race_id and hkey:
            grouped[(race_id, hkey)].append(row)

    acquired_utc = latest_graphql_acquired_utc()
    runner_rows: list[dict[str, str]] = [dict(row) for row in production_rows]
    extended_rows: list[dict[str, str]] = [{**row, "source_format": "DIRECT_CSV", "source_adapter": "HISTORICAL_PASS_THROUGH", "segment_count": "1", "sectional_segment_count": "0", "split_segment_count": "0", "source_payload_sha256": clean(row.get("source_sha256")), "aggregation_version": "runner_aggregate_adapter_v2", "aggregation_trace": "Historical production row copied byte-for-byte at field level."} for row in production_rows]
    mapping_rows: list[dict[str, Any]] = []

    for (race_id, hkey), rows in sorted(grouped.items()):
        base = rows[0]
        split_rows = [r for r in rows if clean(r.get("row_type")) == "SPLIT"]
        sectional_rows = [r for r in rows if clean(r.get("row_type")) == "SECTIONAL"]
        split_by_label = {clean(r.get("distance_label")).upper(): r for r in split_rows}

        last200 = parse_time_seconds(split_by_label.get("200M-FINISH", {}).get("time"))
        last400 = sum(v for v in [parse_time_seconds(split_by_label.get("400M-200M", {}).get("time")), last200] if v is not None) if last200 is not None else None
        last600_parts = [
            parse_time_seconds(split_by_label.get("600M-400M", {}).get("time")),
            parse_time_seconds(split_by_label.get("400M-200M", {}).get("time")),
            parse_time_seconds(split_by_label.get("200M-FINISH", {}).get("time")),
        ]
        last600 = sum(v for v in last600_parts if v is not None) if all(v is not None for v in last600_parts) else None

        ordered_splits = sorted(split_rows, key=lambda r: distance_start(r.get("distance_label", "")) or -1, reverse=True)
        speeds = [fnum(r.get("avg_speed_mps")) for r in ordered_splits]
        speeds = [s for s in speeds if s is not None]
        third = max(1, math.ceil(len(speeds) / 3)) if speeds else 1

        def mean(vals: list[float]) -> float | None:
            return sum(vals) / len(vals) if vals else None

        race_time = parse_time_seconds(base.get("race_time"))
        distance_run = fnum(base.get("distance_run"))
        avg_speed = distance_run / race_time if distance_run is not None and race_time and race_time > 0 else mean(speeds)
        record = {
            "warehouse_record_id": f"{race_id}_{hkey}",
            "race_id": race_id,
            "race_date": clean(base.get("race_date")),
            "track": clean(base.get("track")),
            "state": "VIC",
            "race_no": clean(base.get("race_no_numeric") or base.get("race_no")),
            "distance": race_distance_from_splits(rows),
            "horse": clean(base.get("horse")),
            "horse_key": hkey,
            "barrier": clean(base.get("barrier_number")),
            "last200": fmt_seconds(last200),
            "last400": fmt_seconds(last400),
            "last600": fmt_seconds(last600),
            "last_200": fmt_seconds(last200),
            "last_400": fmt_seconds(last400),
            "last_600": fmt_seconds(last600),
            "early_speed": fmt_speed(mean(speeds[:third])),
            "mid_speed": fmt_speed(mean(speeds[third:third * 2])),
            "late_speed": fmt_speed(mean(speeds[third * 2:])),
            "peak_speed": fmt_speed(max(speeds) if speeds else None),
            "avg_speed": fmt_speed(avg_speed),
            "race_time": clean(base.get("race_time")),
            "tempo_grade": "GRAPHQL_SEGMENT_AGGREGATE",
            "pace_profile": "",
            "sectional_source": "RACING.COM_GRAPHQL_GETRACEFORM_V2",
            "source_csv_url": "https://graphql.rmdprod.racing.com/",
            "source_cache_path": clean(base.get("response_path")),
            "source_sha256": clean(base.get("response_sha256")),
            "acquisition_timestamp": acquired_utc,
            "parser_version": "racingcom_graphql_parser_v2",
            "pipeline_version": "racingcom_runner_aggregate_adapter_v2",
            "meeting_discovery_version": "edgeiq_racingcom_meeting_discovery_v2",
            "race_discovery_version": "edgeiq_racingcom_race_discovery_v2_graphql_evidence_extension",
            "admission_version": "edgeiq_racingcom_graphql_source_admission_v1",
            "warehouse_built_utc": acquired_utc,
        }
        runner_rows.append(record)
        extended_rows.append({
            **record,
            "source_format": "GRAPHQL",
            "source_adapter": "SEGMENT_TO_RUNNER_AGGREGATE",
            "segment_count": str(len(rows)),
            "sectional_segment_count": str(len(sectional_rows)),
            "split_segment_count": str(len(split_rows)),
            "source_payload_sha256": clean(base.get("response_sha256")),
            "aggregation_version": "runner_aggregate_adapter_v2",
            "aggregation_trace": "last200/400/600 from final split sums; early/mid/late from ordered split thirds; avg_speed from distance_run/race_time.",
        })
        for source in rows:
            mapping_rows.append({
                "aggregate_record_id": record["warehouse_record_id"],
                "race_id": race_id,
                "horse_key": hkey,
                "source_row_type": clean(source.get("row_type")),
                "source_distance_label": clean(source.get("distance_label")),
                "source_position": clean(source.get("position")),
                "source_time": clean(source.get("time")),
                "source_avg_speed_mps": clean(source.get("avg_speed_mps")),
                "aggregation_rule": "SEGMENT_TO_RUNNER_AGGREGATE_V2",
            })

    runner_rows = sorted(runner_rows, key=lambda r: (r["race_date"], r["track"], int(float(r["race_no"] or 9999)), r["horse_key"]))
    extended_rows = sorted(extended_rows, key=lambda r: (r["race_date"], r["track"], int(float(r["race_no"] or 9999)), r["horse_key"]))
    return runner_rows, extended_rows, mapping_rows


def run_script(path: Path) -> tuple[int, str]:
    result = subprocess.run([sys.executable, str(path)], cwd=str(ROOT), text=True, capture_output=True)
    return result.returncode, (result.stdout + result.stderr).strip()
