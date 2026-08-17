from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

csv.field_size_limit(sys.maxsize)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "victoria-performance-intelligence-race-context-authority-v1"

RACE_ENTRY_PATH = DATA / "edgeiq_race_entry_fact_v1.csv"
PERFORMANCE_CONTEXT_PATH = DATA / "edgeiq_race_entry_performance_context_fact_v1.csv"
SNAPSHOT_PATH = DATA / "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv"
OUTPUT_PATH = DATA / "edgeiq_race_context_authority_fact_v1.csv"
AUDIT_PATH = DATA / "edgeiq_race_context_authority_fact_v1_audit.json"
SUMMARY_PATH = DATA / "edgeiq_race_context_authority_fact_v1_summary.csv"

INVENTORY_CSV = DOCS / "EDGEIQ_RACE_CONTEXT_SOURCE_INVENTORY_V1.csv"
INVENTORY_JSON = DOCS / "EDGEIQ_RACE_CONTEXT_SOURCE_INVENTORY_V1.json"
INVENTORY_MD = DOCS / "EDGEIQ_RACE_CONTEXT_SOURCE_INVENTORY_V1.md"
TRACE_CSV = DOCS / "EDGEIQ_RACE_CONTEXT_TARGET_RACE_TRACE_V1.csv"
TRACE_JSON = DOCS / "EDGEIQ_RACE_CONTEXT_TARGET_RACE_TRACE_V1.json"
TRACE_MD = DOCS / "EDGEIQ_RACE_CONTEXT_TARGET_RACE_TRACE_V1.md"
REPORT_JSON = DOCS / "EDGEIQ_RACE_CONTEXT_AUTHORITY_DECISION_V1.json"
REPORT_MD = DOCS / "EDGEIQ_RACE_CONTEXT_AUTHORITY_DECISION_V1.md"
IDENTITY_MD = DOCS / "EDGEIQ_DETERMINISTIC_IDENTITY_BRIDGE_REQUIREMENT_V1.md"

BUILDER_VERSION = "edgeiq_race_context_authority_fact_v1.1.0_official_visible_page_source"
CONTRACT_VERSION = "1.0.0"

OUTPUT_FIELDS = [
    "race_context_authority_id",
    "canonical_race_id",
    "race_date",
    "track_id",
    "race_no",
    "race_name",
    "race_distance_m",
    "race_class_code",
    "rail_position",
    "track_condition",
    "race_class_source_file",
    "rail_source_file",
    "race_class_source_value",
    "rail_source_value",
    "race_class_governance_status",
    "rail_governance_status",
    "race_context_authority_status",
    "official_evidence_files",
    "official_evidence_sha256",
    "builder_version",
    "contract_version",
    "built_at_utc",
]

SOURCE_SPECS = [
    {
        "path": DATA / "edgeiq_official_race_context_source_v1.csv",
        "authority": "RACING_COM_VISIBLE_PAGE_OFFICIAL_CONTEXT",
        "class_fields": ["race_class_code", "race_class_source_value", "race_class"],
        "rail_fields": ["rail_position"],
        "date_fields": ["race_date", "meeting_date", "date"],
        "track_fields": ["track", "normalised_track", "canonical_track"],
        "race_no_fields": ["race_no", "race_number"],
        "distance_fields": ["race_distance_m", "distance"],
        "race_name_fields": ["race_name", "name"],
        "condition_fields": ["track_condition", "condition", "track_rating"],
        "url_fields": ["source_url"],
        "source_role": "official_visible_page_race_context",
    },
    {
        "path": DATA / "edgeiq_graphql_getRacesForMeet_meeting_warehouse_v1.csv",
        "authority": "RACING_COM_GRAPHQL_ARCHIVE",
        "class_fields": ["race_class", "raceClass", "class", "race_class_code"],
        "rail_fields": ["rail_position", "rail", "rail_position_text"],
        "date_fields": ["race_date", "meeting_date", "date"],
        "track_fields": ["track", "venue", "meeting_name", "normalised_track"],
        "race_no_fields": ["race_no", "race_number", "number"],
        "distance_fields": ["distance", "race_distance_metres", "distance_metres"],
        "race_name_fields": ["race_name", "title"],
        "condition_fields": ["track_condition", "condition", "track_rating"],
        "url_fields": ["meet_url", "source_url", "formUrl"],
        "source_role": "official_archive_race_context",
    },
    {
        "path": DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv",
        "authority": "RACING_COM_GRAPHQL_RESULTS_WAREHOUSE",
        "class_fields": ["race_class", "race_class_code", "class"],
        "rail_fields": ["rail_position", "rail", "previous_rail_position"],
        "date_fields": ["race_date", "meeting_date", "date"],
        "track_fields": ["track", "venue", "normalised_track"],
        "race_no_fields": ["race_no", "race_number"],
        "distance_fields": ["distance", "distance_metres", "race_distance_metres"],
        "race_name_fields": ["race_name"],
        "condition_fields": ["track_condition", "condition", "track_rating"],
        "url_fields": ["source_url", "url"],
        "source_role": "official_historical_results_context",
    },
    {
        "path": DATA / "edgeiq_benchmark_observation_current_window_v2_1.csv",
        "authority": "EDGEIQ_CURRENT_WINDOW_OBSERVATION",
        "class_fields": ["race_class", "race_class_code", "class"],
        "rail_fields": ["rail_position", "rail"],
        "date_fields": ["race_date", "meeting_date", "date"],
        "track_fields": ["track", "venue", "normalised_track"],
        "race_no_fields": ["race_no", "race_number"],
        "distance_fields": ["distance_metres", "distance", "race_distance_metres"],
        "race_name_fields": ["race_name"],
        "condition_fields": ["track_condition", "condition", "track_rating"],
        "url_fields": ["source_url", "url"],
        "source_role": "official_current_window_context",
    },
    {
        "path": DATA / "edgeiq_benchmark_observation_fact_v1.csv",
        "authority": "EDGEIQ_BENCHMARK_OBSERVATION",
        "class_fields": ["race_class", "race_class_code", "class"],
        "rail_fields": ["rail_position", "rail"],
        "date_fields": ["race_date", "meeting_date", "date"],
        "track_fields": ["track", "venue", "normalised_track"],
        "race_no_fields": ["race_no", "race_number"],
        "distance_fields": ["distance_metres", "distance", "race_distance_metres"],
        "race_name_fields": ["race_name"],
        "condition_fields": ["track_condition", "condition", "track_rating"],
        "url_fields": ["source_url", "url"],
        "source_role": "official_benchmark_context",
    },
    {
        "path": DATA / "edgeiq_canonical_historical_timing_warehouse_v1.csv",
        "authority": "EDGEIQ_CANONICAL_TIMING_WAREHOUSE",
        "class_fields": ["race_class", "race_class_code", "race_class_group"],
        "rail_fields": ["rail_position", "rail"],
        "date_fields": ["race_date", "meeting_date", "date"],
        "track_fields": ["track", "venue", "track_name", "normalised_track"],
        "race_no_fields": ["race_no", "race_number"],
        "distance_fields": ["distance_metres", "distance", "race_distance_metres"],
        "race_name_fields": ["race_name"],
        "condition_fields": ["track_condition", "condition", "track_rating"],
        "url_fields": ["source_url", "url"],
        "source_role": "canonical_timing_class_context_only",
    },
    {
        "path": DATA / "edgeiq_vic_three_day_race_fields.csv",
        "authority": "RACING_COM_CURRENT_FIELDS",
        "class_fields": ["race_class", "race_class_code", "class"],
        "rail_fields": ["rail_position", "rail", "rail_position_text"],
        "date_fields": ["race_date", "meeting_date", "date"],
        "track_fields": ["track", "normalised_track", "meeting_name", "canonical_track"],
        "race_no_fields": ["race_no", "race_number"],
        "distance_fields": ["distance_metres", "distance", "race_distance_metres"],
        "race_name_fields": ["race_name"],
        "condition_fields": ["track_condition", "condition", "track_rating"],
        "url_fields": ["source_url", "url", "race_url"],
        "source_role": "official_current_fields_context",
    },
    {
        "path": DATA / "edgeiq_vic_three_day_race_list_v1.csv",
        "authority": "RACING_COM_CURRENT_RACE_LIST",
        "class_fields": ["race_class", "race_class_code", "class"],
        "rail_fields": ["rail_position", "rail", "rail_position_text"],
        "date_fields": ["race_date", "meeting_date", "date"],
        "track_fields": ["track", "normalised_track", "meeting_name", "canonical_track"],
        "race_no_fields": ["race_no", "race_number"],
        "distance_fields": ["distance_metres", "distance", "race_distance_metres"],
        "race_name_fields": ["race_name"],
        "condition_fields": ["track_condition", "condition", "track_rating"],
        "url_fields": ["source_url", "url", "race_url"],
        "source_role": "official_current_race_list_context",
    },
    {
        "path": DATA / "edgeiq_daily_race_discovery_v1.csv",
        "authority": "EDGEIQ_DAILY_RACE_DISCOVERY",
        "class_fields": ["race_class", "race_class_code", "class"],
        "rail_fields": ["rail_position", "rail"],
        "date_fields": ["meeting_date", "race_date", "date"],
        "track_fields": ["meeting_name", "track", "canonical_track"],
        "race_no_fields": ["race_number", "race_no"],
        "distance_fields": ["distance_metres", "race_distance_metres", "distance"],
        "race_name_fields": ["race_name"],
        "condition_fields": ["current_condition", "track_condition"],
        "url_fields": ["source_url"],
        "source_role": "official_current_discovery_context",
    },
    {
        "path": ROOT / "data" / "processed" / "racing-com-public-v1" / "race_fact.csv",
        "authority": "RACING_COM_PUBLIC_DATA_V1",
        "class_fields": ["race_class", "raceClass", "class"],
        "rail_fields": ["rail_position", "rail"],
        "date_fields": ["meeting_date", "race_date", "date"],
        "track_fields": ["venue", "track", "canonical_track"],
        "race_no_fields": ["race_number", "race_no"],
        "distance_fields": ["race_distance_metres", "distance_metres", "distance"],
        "race_name_fields": ["race_name", "title"],
        "condition_fields": ["track_condition", "condition"],
        "url_fields": ["source_page_url", "source_url"],
        "source_role": "public_current_race_fact_context",
    },
]


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def clean_track(value: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", text(value).upper())


def first_text(row: dict[str, str], fields: Iterable[str]) -> str:
    for field in fields:
        value = text(row.get(field, ""))
        if value:
            return value
    return ""


def parse_race_no(value: object) -> str:
    raw = text(value)
    if not raw:
        return ""
    match = re.search(r"R(?:ACE)?\s*0*(\d+)", raw, flags=re.I)
    if match:
        return str(int(match.group(1)))
    match = re.search(r"\b0*(\d{1,2})(?:\.0)?\b", raw)
    if match:
        return str(int(match.group(1)))
    return raw


def parse_distance_m(value: object) -> str:
    raw = text(value)
    if not raw:
        return ""
    match = re.search(r"(\d{3,4})(?:\.0)?", raw)
    return match.group(1) if match else raw


def parse_date_from_url(value: object) -> str:
    raw = text(value)
    match = re.search(r"(20\d{2}-\d{2}-\d{2})", raw)
    return match.group(1) if match else ""


def parse_track_from_url(value: object) -> str:
    raw = text(value)
    match = re.search(r"/form/20\d{2}-\d{2}-\d{2}/([^/#?]+)", raw)
    if not match:
        return ""
    slug = match.group(1)
    return slug.replace("-", " ").upper()


def race_no_from_race_id(value: object) -> str:
    raw = text(value)
    match = re.search(r"\|R(\d+)\|", raw.upper())
    return str(int(match.group(1))) if match else ""


def sha256_payload(parts: Iterable[object]) -> str:
    return hashlib.sha256("\x1f".join(text(part) for part in parts).encode("utf-8")).hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return [], []
        return list(reader.fieldnames), list(reader)


def atomic_write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp_path = Path(tmp)
    try:
        with tmp_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def race_key(date_value: object, track_value: object, race_no_value: object) -> tuple[str, str, str]:
    return (text(date_value), clean_track(track_value), parse_race_no(race_no_value))


def race_key_display(key: tuple[str, str, str]) -> str:
    return f"{key[0]}|{key[1]}|R{key[2]}"


def load_target_races() -> dict[tuple[str, str, str], dict[str, str]]:
    fields, rows = read_csv(RACE_ENTRY_PATH)
    races: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in rows:
        race_id = first_text(row, ["canonical_race_id", "race_id"])
        race_no = first_text(row, ["race_number", "race_no"])
        if not race_no:
            race_no = race_no_from_race_id(race_id)
        date_value = first_text(row, ["race_date", "meeting_date", "date"])
        track = first_text(row, ["canonical_track", "track", "course_identity", "venue", "meeting_name"])
        if not date_value or not track or not race_no:
            continue
        key = race_key(date_value, track, race_no)
        current = races.setdefault(key, {
            "canonical_race_id": race_id,
            "race_date": date_value,
            "track_id": clean_track(track),
            "race_no": key[2],
            "race_name": first_text(row, ["race_name"]),
            "race_distance_m": parse_distance_m(first_text(row, ["race_distance_metres", "distance_metres", "distance"])),
            "track_condition": first_text(row, ["track_condition", "current_condition"]),
            "runner_count": "0",
        })
        current["runner_count"] = str(int(current.get("runner_count", "0") or 0) + 1)
        if not current.get("race_name"):
            current["race_name"] = first_text(row, ["race_name"])
        if not current.get("race_distance_m"):
            current["race_distance_m"] = parse_distance_m(first_text(row, ["race_distance_metres", "distance_metres", "distance"]))
    return races


def load_snapshot_target_keys() -> set[tuple[str, str, str]]:
    keys: set[tuple[str, str, str]] = set()
    fields, rows = read_csv(PERFORMANCE_CONTEXT_PATH)
    for row in rows:
        race_id = first_text(row, ["race_id", "canonical_race_id"])
        keys.add(race_key(first_text(row, ["race_date", "meeting_date"]), first_text(row, ["track_name", "track_id", "canonical_track"]), race_no_from_race_id(race_id)))
    return {key for key in keys if key[0] and key[1] and key[2]}


def source_row_key(row: dict[str, str], spec: dict[str, object]) -> tuple[str, str, str]:
    url = first_text(row, spec["url_fields"])
    date_value = first_text(row, spec["date_fields"]) or parse_date_from_url(url)
    track_value = first_text(row, spec["track_fields"]) or parse_track_from_url(url)
    race_no = first_text(row, spec["race_no_fields"])
    if not race_no:
        race_no = race_no_from_race_id(first_text(row, ["race_id", "canonical_race_id", "race_key"]))
    return race_key(date_value, track_value, race_no)


def summarise_source(spec: dict[str, object], target_keys: set[tuple[str, str, str]]) -> tuple[dict[str, object], dict[tuple[str, str, str], list[dict[str, str]]]]:
    path = spec["path"]
    assert isinstance(path, Path)
    fields, rows = read_csv(path)
    class_fields = [f for f in spec["class_fields"] if f in fields]
    rail_fields = [f for f in spec["rail_fields"] if f in fields]
    target_matches: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    class_nonblank = 0
    rail_nonblank = 0
    any_target_class = 0
    any_target_rail = 0
    rows_scanned = len(rows)
    for row in rows:
        class_value = first_text(row, spec["class_fields"])
        rail_value = first_text(row, spec["rail_fields"])
        if class_value:
            class_nonblank += 1
        if rail_value:
            rail_nonblank += 1
        key = source_row_key(row, spec)
        if key in target_keys:
            target_matches[key].append(row)
            if class_value:
                any_target_class += 1
            if rail_value:
                any_target_rail += 1
    if not path.exists():
        status = "NOT_FOUND"
    elif rows_scanned == 0:
        status = "NOT_FOUND"
    elif (class_nonblank > 0 and rail_nonblank > 0):
        status = "FOUND"
    elif class_nonblank > 0 or rail_nonblank > 0 or class_fields or rail_fields:
        status = "PARTIAL"
    else:
        status = "NOT_FOUND"
    summary = {
        "source_file": str(path.relative_to(ROOT)) if path.exists() else str(path),
        "authority": spec["authority"],
        "source_role": spec["source_role"],
        "file_exists": "YES" if path.exists() else "NO",
        "rows": rows_scanned,
        "class_fields_found": "|".join(class_fields),
        "rail_fields_found": "|".join(rail_fields),
        "race_class_nonblank_rows": class_nonblank,
        "rail_position_nonblank_rows": rail_nonblank,
        "target_race_matches": sum(len(v) for v in target_matches.values()),
        "target_races_with_class": len({k for k, matches in target_matches.items() if any(first_text(m, spec["class_fields"]) for m in matches)}),
        "target_races_with_rail": len({k for k, matches in target_matches.items() if any(first_text(m, spec["rail_fields"]) for m in matches)}),
        "target_class_rows": any_target_class,
        "target_rail_rows": any_target_rail,
        "source_status": status,
    }
    return summary, target_matches


def source_records_for_target_sources(target_keys: set[tuple[str, str, str]]) -> tuple[list[dict[str, object]], dict[tuple[str, str, str], list[dict[str, str]]]]:
    inventory_rows: list[dict[str, object]] = []
    matches: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for spec in SOURCE_SPECS:
        summary, target_matches = summarise_source(spec, target_keys)
        inventory_rows.append(summary)
        path = spec["path"]
        rel = str(path.relative_to(ROOT)) if isinstance(path, Path) and path.exists() else str(path)
        for key, rows in target_matches.items():
            for row in rows:
                row_copy = dict(row)
                row_copy["__source_file"] = rel
                row_copy["__authority"] = text(spec["authority"])
                row_copy["__source_role"] = text(spec["source_role"])
                row_copy["__class_value"] = first_text(row, spec["class_fields"])
                row_copy["__rail_value"] = first_text(row, spec["rail_fields"])
                row_copy["__condition_value"] = first_text(row, spec["condition_fields"])
                row_copy["__race_name_value"] = first_text(row, spec["race_name_fields"])
                row_copy["__distance_value"] = parse_distance_m(first_text(row, spec["distance_fields"]))
                matches[key].append(row_copy)
    return inventory_rows, matches


def build_authority_rows(target_races: dict[tuple[str, str, str], dict[str, str]], matches: dict[tuple[str, str, str], list[dict[str, str]]]) -> list[dict[str, object]]:
    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    output: list[dict[str, object]] = []
    for key in sorted(target_races):
        base = target_races[key]
        race_matches = matches.get(key, [])
        class_match = next((row for row in race_matches if text(row.get("__class_value"))), None)
        rail_match = next((row for row in race_matches if text(row.get("__rail_value"))), None)
        class_value = text(class_match.get("__class_value")) if class_match else ""
        rail_value = text(rail_match.get("__rail_value")) if rail_match else ""
        condition_value = first_text(base, ["track_condition"])
        if not condition_value:
            condition_match = next((row for row in race_matches if text(row.get("__condition_value"))), None)
            condition_value = text(condition_match.get("__condition_value")) if condition_match else ""
        race_name = first_text(base, ["race_name"])
        if not race_name:
            name_match = next((row for row in race_matches if text(row.get("__race_name_value"))), None)
            race_name = text(name_match.get("__race_name_value")) if name_match else ""
        distance = first_text(base, ["race_distance_m"])
        if not distance:
            distance_match = next((row for row in race_matches if text(row.get("__distance_value"))), None)
            distance = text(distance_match.get("__distance_value")) if distance_match else ""
        class_status = "FOUND_OFFICIAL_SOURCE" if class_value else "MISSING_OFFICIAL_SOURCE"
        rail_status = "FOUND_OFFICIAL_SOURCE" if rail_value else "MISSING_OFFICIAL_SOURCE"
        if class_value and rail_value:
            status = "COMPLETE_OFFICIAL_RACE_CONTEXT"
        elif class_value or rail_value:
            status = "PARTIAL_OFFICIAL_RACE_CONTEXT"
        else:
            status = "BLOCKED_MISSING_OFFICIAL_RACE_CONTEXT"
        files = sorted({text(row.get("__source_file")) for row in race_matches if text(row.get("__source_file"))})
        context_id = "RCAF1-" + sha256_payload([base.get("canonical_race_id", ""), key[0], key[1], key[2]])[:24].upper()
        evidence_sha = sha256_payload([context_id, base.get("canonical_race_id", ""), class_value, rail_value, "|".join(files), BUILDER_VERSION])
        output.append({
            "race_context_authority_id": context_id,
            "canonical_race_id": base.get("canonical_race_id", ""),
            "race_date": key[0],
            "track_id": key[1],
            "race_no": key[2],
            "race_name": race_name,
            "race_distance_m": distance,
            "race_class_code": class_value,
            "rail_position": rail_value,
            "track_condition": condition_value,
            "race_class_source_file": text(class_match.get("__source_file")) if class_match else "",
            "rail_source_file": text(rail_match.get("__source_file")) if rail_match else "",
            "race_class_source_value": class_value,
            "rail_source_value": rail_value,
            "race_class_governance_status": class_status,
            "rail_governance_status": rail_status,
            "race_context_authority_status": status,
            "official_evidence_files": "|".join(files),
            "official_evidence_sha256": evidence_sha,
            "builder_version": BUILDER_VERSION,
            "contract_version": CONTRACT_VERSION,
            "built_at_utc": built_at,
        })
    return output


def write_markdown_reports(inventory_rows: list[dict[str, object]], trace_rows: list[dict[str, object]], output_rows: list[dict[str, object]]) -> dict[str, object]:
    status_counts = Counter(row["race_context_authority_status"] for row in output_rows)
    target_blocked = [row for row in output_rows if row["race_context_authority_status"] != "COMPLETE_OFFICIAL_RACE_CONTEXT"]
    full_completion = status_counts.get("COMPLETE_OFFICIAL_RACE_CONTEXT", 0)
    final_status = "PASS_VICTORIA_PERFORMANCE_INTELLIGENCE_COMPLETE" if full_completion == len(output_rows) and output_rows else "BLOCKED_SOURCE_DATA_UNAVAILABLE"
    inventory_status = Counter(row["source_status"] for row in inventory_rows)
    target_class_sources = [row for row in output_rows if row["race_class_code"]]
    target_rail_sources = [row for row in output_rows if row["rail_position"]]
    payload = {
        "status": final_status,
        "builder_version": BUILDER_VERSION,
        "target_races": len(output_rows),
        "complete_race_context_races": full_completion,
        "partial_or_blocked_races": len(target_blocked),
        "inventory_status_counts": dict(inventory_status),
        "race_context_status_counts": dict(status_counts),
        "race_class_source_rows": len(target_class_sources),
        "rail_position_source_rows": len(target_rail_sources),
        "primary_blocker": "OFFICIAL_RACE_CLASS_AND_RAIL_SOURCE_NOT_AVAILABLE_FOR_CURRENT_SNAPSHOT_RACES" if target_blocked else "NONE",
        "identity_bridge_requirement": "A durable shared horse identifier is required: Racing Australia horse ID plus Racing.com horse_code mapping, or an Australian Stud Book identifier available in both sources. Name-only bridges remain rejected.",
        "protected_systems": {
            "pricing_changed": "NO",
            "probability_changed": "NO",
            "v6_1_changed": "NO",
            "v7_2g2_changed": "NO",
            "ui_changed": "NO",
            "governance_weakened": "NO",
        },
    }
    write_json(REPORT_JSON, payload)
    REPORT_MD.write_text("\n".join([
        "# EDGEiQ Race Context Authority Decision V1",
        "",
        f"Status: {final_status}",
        "",
        "## Decision",
        "A canonical Race Context Authority fact has been created. It only admits race_class_code and rail_position when an exact official evidence row matches race_date, normalised track and race number. No race name or prize-money inference is used, and no rail default is applied.",
        "",
        "## Current EPI blocker",
        f"Target races: {len(output_rows)}",
        f"Complete official context races: {full_completion}",
        f"Partial/blocked races: {len(target_blocked)}",
        f"Primary blocker: {payload['primary_blocker']}",
        "",
        "## Source inventory counts",
        *[f"- {key}: {value}" for key, value in sorted(inventory_status.items())],
        "",
        "## Race context status counts",
        *[f"- {key}: {value}" for key, value in sorted(status_counts.items())],
        "",
        "## Governance",
        "- race_class_code is not derived from race name or prize money.",
        "- rail_position is not defaulted or estimated.",
        "- missing official values remain blank with MISSING_OFFICIAL_SOURCE status.",
        "- EPI mandatory component requirements are unchanged.",
        "",
    ]) + "\n", encoding="utf-8")
    INVENTORY_MD.write_text("\n".join([
        "# EDGEiQ Race Context Source Inventory V1",
        "",
        "| Source | Status | Rows | Class nonblank | Rail nonblank | Target matches | Target class races | Target rail races |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        *[
            f"| {row['source_file']} | {row['source_status']} | {row['rows']} | {row['race_class_nonblank_rows']} | {row['rail_position_nonblank_rows']} | {row['target_race_matches']} | {row['target_races_with_class']} | {row['target_races_with_rail']} |"
            for row in inventory_rows
        ],
        "",
    ]) + "\n", encoding="utf-8")
    TRACE_MD.write_text("\n".join([
        "# EDGEiQ Race Context Target Race Trace V1",
        "",
        "| Race | Source | Class | Rail | Status |",
        "|---|---|---|---|---|",
        *[
            f"| {row['race_key']} | {row['source_file']} | {row['race_class_value']} | {row['rail_position_value']} | {row['trace_status']} |"
            for row in trace_rows
        ],
        "",
    ]) + "\n", encoding="utf-8")
    IDENTITY_MD.write_text("\n".join([
        "# EDGEiQ Deterministic Identity Bridge Requirement V1",
        "",
        "The RA to Racing.com investigation remains closed for implementation: no durable repository bridge currently exists, and name-only matching is rejected.",
        "",
        "A deterministic future bridge requires at least one shared durable identifier exposed by official evidence:",
        "",
        "- Racing Australia durable horse identifier matched to Racing.com horse_code, or",
        "- Racing.com durable horse_code matched to Racing Australia horse code, or",
        "- Australian Stud Book identifier present in both source families.",
        "",
        "Until one of those identifiers is available, current RA horses must not be bridged to Racing.com historical identities by name alone.",
        "",
    ]) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    target_races = load_target_races()
    target_keys = set(target_races.keys())
    inventory_rows, source_matches = source_records_for_target_sources(target_keys)
    output_rows = build_authority_rows({key: target_races[key] for key in target_keys if key in target_races}, source_matches)
    trace_rows: list[dict[str, object]] = []
    for key in sorted(target_keys):
        matches = source_matches.get(key, [])
        if not matches:
            trace_rows.append({
                "race_key": race_key_display(key),
                "source_file": "NO_MATCHING_OFFICIAL_CONTEXT_SOURCE",
                "race_class_value": "",
                "rail_position_value": "",
                "trace_status": "NOT_FOUND",
            })
            continue
        for row in matches:
            trace_rows.append({
                "race_key": race_key_display(key),
                "source_file": row.get("__source_file", ""),
                "authority": row.get("__authority", ""),
                "source_role": row.get("__source_role", ""),
                "race_class_value": row.get("__class_value", ""),
                "rail_position_value": row.get("__rail_value", ""),
                "track_condition_value": row.get("__condition_value", ""),
                "trace_status": "FOUND" if row.get("__class_value") and row.get("__rail_value") else "PARTIAL",
            })
    atomic_write_csv(OUTPUT_PATH, output_rows, OUTPUT_FIELDS)
    atomic_write_csv(INVENTORY_CSV, inventory_rows, [
        "source_file", "authority", "source_role", "file_exists", "rows", "class_fields_found", "rail_fields_found",
        "race_class_nonblank_rows", "rail_position_nonblank_rows", "target_race_matches", "target_races_with_class",
        "target_races_with_rail", "target_class_rows", "target_rail_rows", "source_status",
    ])
    atomic_write_csv(TRACE_CSV, trace_rows, [
        "race_key", "source_file", "authority", "source_role", "race_class_value", "rail_position_value", "track_condition_value", "trace_status",
    ])
    write_json(INVENTORY_JSON, inventory_rows)
    write_json(TRACE_JSON, trace_rows)
    audit_payload = write_markdown_reports(inventory_rows, trace_rows, output_rows)
    audit_payload.update({
        "output": str(OUTPUT_PATH.relative_to(ROOT)),
        "inventory_csv": str(INVENTORY_CSV.relative_to(ROOT)),
        "trace_csv": str(TRACE_CSV.relative_to(ROOT)),
    })
    write_json(AUDIT_PATH, audit_payload)
    atomic_write_csv(SUMMARY_PATH, [{"metric": key, "value": value} for key, value in audit_payload.items() if not isinstance(value, dict)], ["metric", "value"])
    print("EDGEIQ_RACE_CONTEXT_AUTHORITY_FACT_V1_BUILD_PASS")
    print(f"race_context_authority_rows={len(output_rows)}")
    print(f"status={audit_payload['status']}")
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
