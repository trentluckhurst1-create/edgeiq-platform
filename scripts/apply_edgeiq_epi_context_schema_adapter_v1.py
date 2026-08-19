
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'scripts' / 'build_edgeiq_race_entry_performance_context_fact_v1.py'
CHECKPOINT = ROOT / 'docs' / 'victoria-performance-intelligence-completion-v1' / 'checkpoints' / 'build_edgeiq_race_entry_performance_context_fact_v1_PRE_SCHEMA_ADAPTER.py'
CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
if not CHECKPOINT.exists():
    CHECKPOINT.write_text(TARGET.read_text(encoding='utf-8'), encoding='utf-8')

NEW_CONTENT = r'''from __future__ import annotations

import csv
import hashlib
import os
import re
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SNAPSHOT_PATH = DATA / "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv"
RACE_ENTRY_PATH = DATA / "edgeiq_race_entry_fact_v1.csv"
OUTPUT_PATH = DATA / "edgeiq_race_entry_performance_context_fact_v1.csv"

CONTRACT_VERSION = "1.0.0"
BUILDER_VERSION = "edgeiq_race_entry_performance_context_fact_v1.1.0_current_schema_adapter"
SOURCE_SNAPSHOT_STATUS = "POINT_IN_TIME_HISTORICAL_RATING_AVAILABLE"
SOURCE_RACE_ENTRY_STATUS = "DECLARED_GOVERNED"
CONTEXT_STATUS = "FACTUAL_DECLARED_RACE_CONTEXT_GOVERNED"

OUTPUT_FIELDS = [
    "race_entry_performance_context_id",
    "race_entry_horse_performance_snapshot_id",
    "race_entry_id",
    "race_id",
    "race_date",
    "runner_id",
    "canonical_horse_id",
    "canonical_horse_name",
    "selected_horse_performance_rating_id",
    "selected_rating_as_of_date",
    "rating_age_days",
    "context_historical_rating_value",
    "race_distance_m",
    "race_class_code",
    "track_id",
    "track_name",
    "track_configuration",
    "track_condition",
    "racing_surface",
    "rail_position",
    "barrier",
    "allocated_weight_kg",
    "declared_field_size",
    "race_entry_performance_context_status",
    "source_snapshot_evidence_sha256",
    "source_race_entry_evidence_sha256",
    "race_entry_performance_context_evidence_sha256",
    "source_snapshot_builder_version",
    "source_race_entry_builder_version",
    "builder_version",
    "contract_version",
    "built_at_utc",
]

LEGACY_REQUIRED_FIELDS = [
    "race_entry_id", "race_id", "race_date", "runner_id", "canonical_horse_id",
    "canonical_horse_name", "race_distance_m", "race_class_code", "track_id",
    "track_name", "track_configuration", "track_condition", "racing_surface",
    "rail_position", "barrier", "allocated_weight_kg", "declared_field_size",
    "race_entry_status", "race_entry_evidence_sha256", "builder_version",
]

CURRENT_REQUIRED_FIELDS = [
    "canonical_race_id", "canonical_runner_id", "race_date", "canonical_track",
    "course_identity", "race_number", "race_distance_metres", "surface_group",
    "track_condition_number", "runner_name", "barrier", "weight_kg",
    "declaration_status", "scratching_status", "source_hash",
]


def fail(message: str) -> None:
    raise RuntimeError(message)


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def upper_text(value: object) -> str:
    return re.sub(r"\s+", " ", text(value).upper()).strip()


def clean_track(value: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", upper_text(value))


def sha256_payload(parts: Iterable[object]) -> str:
    payload = "".join(text(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def deterministic_ref1(parts: Iterable[object]) -> str:
    return "REF1-" + sha256_payload(parts)[:24].upper()


def date_value(value: object, field_name: str) -> date:
    raw = text(value)
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise RuntimeError(f"Invalid date field {field_name}: {raw!r}") from exc


def decimal_value(value: object, field_name: str) -> Decimal:
    raw = text(value)
    if not raw:
        fail(f"Blank decimal field: {field_name}")
    try:
        parsed = Decimal(raw)
    except InvalidOperation as exc:
        raise RuntimeError(f"Invalid decimal field {field_name}: {raw!r}") from exc
    if not parsed.is_finite():
        fail(f"Non-finite decimal field {field_name}: {raw!r}")
    return parsed


def positive_integer(value: object, field_name: str) -> int:
    raw = text(value)
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"Invalid integer field {field_name}: {raw!r}") from exc
    if parsed <= 0:
        fail(f"Non-positive integer field {field_name}: {raw!r}")
    return parsed


def parse_int(value: object) -> int | None:
    raw = text(value)
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.000001')):.6f}"


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        fail(f"Missing canonical input: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            fail(f"Missing CSV header: {path}")
        return list(reader.fieldnames), list(reader)


def require_fields(path: Path, actual_fields: list[str], required_fields: Iterable[str]) -> None:
    missing = [field for field in required_fields if field not in actual_fields]
    if missing:
        fail(f"{path.name} missing required fields: {missing}")


def required_text(row: dict[str, str], field_name: str, identity: str) -> str:
    value = text(row.get(field_name, ""))
    if not value:
        fail(f"{identity}: blank required field {field_name}.")
    return value


def optional_first(row: dict[str, str], fields: Iterable[str]) -> str:
    for field in fields:
        if field in row and text(row.get(field, "")):
            return text(row.get(field, ""))
    return ""


def condition_from_number(value: object) -> str:
    parsed = parse_int(value)
    if parsed is None:
        return ""
    if parsed <= 2:
        return f"FIRM {parsed}"
    if parsed <= 4:
        return f"GOOD {parsed}"
    if parsed <= 7:
        return f"SOFT {parsed}"
    if parsed <= 10:
        return f"HEAVY {parsed}"
    return ""


def is_active_current_entry(entry: dict[str, str]) -> bool:
    status_values = {upper_text(entry.get("declaration_status", "")), upper_text(entry.get("scratching_status", ""))}
    return "SCRATCHED" not in status_values and "SCRATCHED_ENTRY" not in status_values


def current_entry_id(entry: dict[str, str]) -> str:
    explicit = text(entry.get("race_entry_id", ""))
    if explicit:
        return explicit
    return deterministic_ref1([entry.get("canonical_race_id", ""), entry.get("canonical_runner_id", ""), entry.get("source_record_id", "")])


def race_no_from_race_id(value: object) -> str:
    raw = text(value)
    match = re.search(r"\|R(\d+)\|", raw.upper())
    return match.group(1) if match else ""


def build_auxiliary_race_context() -> dict[tuple[str, str, str], dict[str, str]]:
    context: dict[tuple[str, str, str], dict[str, str]] = {}
    candidate_paths = [
        DATA / "edgeiq_vic_three_day_race_fields.csv",
        DATA / "edgeiq_vic_three_day_race_list_v1.csv",
        DATA / "edgeiq_three_day_product_catalog_races_v1.csv",
    ]
    for path in candidate_paths:
        if not path.exists():
            continue
        try:
            _, rows = read_csv(path)
        except RuntimeError:
            continue
        for row in rows:
            race_date = optional_first(row, ["race_date", "meeting_date", "date"])
            track = optional_first(row, ["track", "normalised_track", "canonical_track", "meeting_name"])
            race_no = optional_first(row, ["race_no", "race_number"])
            if not race_no:
                race_no = race_no_from_race_id(optional_first(row, ["canonical_race_id", "race_id"]))
            if not race_date or not track or not race_no:
                continue
            key = (race_date, clean_track(track), str(parse_int(race_no) or race_no))
            target = context.setdefault(key, {})
            if "race_class_code" not in target or not target["race_class_code"]:
                target["race_class_code"] = optional_first(row, ["race_class_code", "race_class", "class"])
            if "rail_position" not in target or not target["rail_position"]:
                target["rail_position"] = optional_first(row, ["rail_position", "rail", "rail_position_text"])
            if "track_condition" not in target or not target["track_condition"]:
                target["track_condition"] = optional_first(row, ["track_condition", "condition", "track_rating"])
    return context


def normalise_legacy_entry(entry: dict[str, str]) -> dict[str, str]:
    return {field: text(entry.get(field, "")) for field in LEGACY_REQUIRED_FIELDS}


def normalise_current_entry(entry: dict[str, str], field_size_by_race: dict[str, int], aux_context: dict[tuple[str, str, str], dict[str, str]]) -> dict[str, str]:
    race_id = required_text(entry, "canonical_race_id", "current-race-entry-source")
    runner_id = required_text(entry, "canonical_runner_id", race_id)
    race_date = required_text(entry, "race_date", race_id)
    track = required_text(entry, "canonical_track", race_id)
    race_no = str(parse_int(entry.get("race_number", "")) or text(entry.get("race_number", "")))
    aux = aux_context.get((race_date, clean_track(track), race_no), {})
    class_code = optional_first(entry, ["race_class_code", "race_class", "class"])
    rail = optional_first(entry, ["rail_position", "rail", "rail_position_text"])
    track_condition = optional_first(entry, ["track_condition", "condition", "track_rating"])
    if not track_condition:
        track_condition = condition_from_number(entry.get("track_condition_number", ""))
    if not class_code:
        class_code = text(aux.get("race_class_code", ""))
    if not rail:
        rail = text(aux.get("rail_position", ""))
    if not track_condition:
        track_condition = text(aux.get("track_condition", ""))
    return {
        "race_entry_id": current_entry_id(entry),
        "race_id": race_id,
        "race_date": race_date,
        "runner_id": runner_id,
        "canonical_horse_id": runner_id,
        "canonical_horse_name": upper_text(entry.get("runner_name", "")),
        "race_distance_m": text(entry.get("race_distance_metres", "")),
        "race_class_code": class_code,
        "track_id": optional_first(entry, ["track_id", "course_identity", "canonical_track"]),
        "track_name": track,
        "track_configuration": optional_first(entry, ["track_configuration", "course_identity", "canonical_track"]),
        "track_condition": track_condition,
        "racing_surface": optional_first(entry, ["racing_surface", "surface_group"]),
        "rail_position": rail,
        "barrier": text(entry.get("barrier", "")),
        "allocated_weight_kg": text(entry.get("weight_kg", "")),
        "declared_field_size": str(field_size_by_race.get(race_id, 0)),
        "race_entry_status": SOURCE_RACE_ENTRY_STATUS if is_active_current_entry(entry) else "NOT_DECLARED_GOVERNED",
        "race_entry_evidence_sha256": optional_first(entry, ["race_entry_evidence_sha256", "source_hash"]),
        "builder_version": optional_first(entry, ["builder_version", "source_system"]),
    }


def atomic_write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)
    try:
        with temporary_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, extrasaction="raise", lineterminator="
")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def main() -> None:
    snapshot_fields, snapshot_rows = read_csv(SNAPSHOT_PATH)
    require_fields(SNAPSHOT_PATH, snapshot_fields, [
        "race_entry_horse_performance_snapshot_id", "race_entry_id", "race_id", "race_date",
        "runner_id", "canonical_horse_id", "canonical_horse_name",
        "selected_horse_performance_rating_id", "selected_rating_as_of_date",
        "rating_age_days", "selected_horse_performance_rating_value",
        "race_entry_horse_performance_snapshot_status",
        "race_entry_horse_performance_snapshot_evidence_sha256", "builder_version",
    ])
    if not snapshot_rows:
        atomic_write_csv(OUTPUT_PATH, [])
        print("EDGEIQ_RACE_ENTRY_PERFORMANCE_CONTEXT_FACT_V1_BUILD_PASS")
        print("race_entry_horse_performance_snapshot_rows=0")
        print("race_entry_rows=NOT_REQUIRED")
        print("race_entry_performance_context_rows=0")
        print(f"output={OUTPUT_PATH}")
        return

    race_entry_fields, raw_race_entry_rows = read_csv(RACE_ENTRY_PATH)
    is_legacy_schema = all(field in race_entry_fields for field in LEGACY_REQUIRED_FIELDS)
    is_current_schema = all(field in race_entry_fields for field in CURRENT_REQUIRED_FIELDS)
    if not is_legacy_schema and not is_current_schema:
        fail(f"{RACE_ENTRY_PATH.name} missing a supported race-entry schema. fields={race_entry_fields}")

    field_size_by_race: dict[str, int] = {}
    for entry in raw_race_entry_rows:
        race_id = text(entry.get("race_id", entry.get("canonical_race_id", "")))
        if not race_id:
            continue
        if is_legacy_schema:
            if text(entry.get("race_entry_status", "")) == SOURCE_RACE_ENTRY_STATUS:
                field_size_by_race[race_id] = field_size_by_race.get(race_id, 0) + 1
        elif is_active_current_entry(entry):
            field_size_by_race[race_id] = field_size_by_race.get(race_id, 0) + 1

    aux_context = build_auxiliary_race_context()
    normalised_entries = [normalise_legacy_entry(entry) if is_legacy_schema else normalise_current_entry(entry, field_size_by_race, aux_context) for entry in raw_race_entry_rows]

    race_entries_by_id: dict[str, dict[str, str]] = {}
    race_entries_by_pair: dict[tuple[str, str], dict[str, str]] = {}
    for entry in normalised_entries:
        race_entry_id = required_text(entry, "race_entry_id", "race-entry-source")
        if race_entry_id in race_entries_by_id:
            fail(f"Duplicate race entry ID: {race_entry_id}")
        race_entries_by_id[race_entry_id] = entry
        race_entries_by_pair[(text(entry.get("race_id", "")), text(entry.get("runner_id", "")))] = entry

    built_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    output_rows: list[dict[str, object]] = []
    seen_snapshot_ids: set[str] = set()
    seen_context_ids: set[str] = set()
    for snapshot in snapshot_rows:
        snapshot_id = required_text(snapshot, "race_entry_horse_performance_snapshot_id", "snapshot-source")
        if snapshot_id in seen_snapshot_ids:
            fail(f"Duplicate snapshot ID: {snapshot_id}")
        seen_snapshot_ids.add(snapshot_id)
        if text(snapshot["race_entry_horse_performance_snapshot_status"]) != SOURCE_SNAPSHOT_STATUS:
            fail(f"{snapshot_id}: source snapshot status is not governed.")
        race_entry_id = required_text(snapshot, "race_entry_id", snapshot_id)
        race_id = required_text(snapshot, "race_id", snapshot_id)
        runner_id = required_text(snapshot, "runner_id", snapshot_id)
        entry = race_entries_by_id.get(race_entry_id) or race_entries_by_pair.get((race_id, runner_id))
        if entry is None:
            fail(f"{snapshot_id}: missing governed race entry {race_entry_id} for {race_id} / {runner_id}.")
        if text(entry["race_entry_status"]) != SOURCE_RACE_ENTRY_STATUS:
            fail(f"{text(entry['race_entry_id'])}: source race entry status is not governed.")
        race_date = date_value(snapshot["race_date"], "race_date")
        canonical_horse_id = required_text(snapshot, "canonical_horse_id", snapshot_id)
        canonical_horse_name = required_text(snapshot, "canonical_horse_name", snapshot_id)
        selected_rating_id = required_text(snapshot, "selected_horse_performance_rating_id", snapshot_id)
        selected_rating_date = date_value(snapshot["selected_rating_as_of_date"], "selected_rating_as_of_date")
        rating_age_days = positive_integer(snapshot["rating_age_days"], "rating_age_days")
        context_rating = decimal_value(snapshot["selected_horse_performance_rating_value"], "selected_horse_performance_rating_value")
        race_distance_m = positive_integer(entry["race_distance_m"], "race_distance_m")
        barrier = positive_integer(entry["barrier"], "barrier")
        allocated_weight_kg = decimal_value(entry["allocated_weight_kg"], "allocated_weight_kg")
        declared_field_size = positive_integer(entry["declared_field_size"], "declared_field_size")
        if selected_rating_date >= race_date:
            fail(f"{snapshot_id}: selected rating date is not before race date.")
        if text(entry["race_id"]) != race_id:
            fail(f"{snapshot_id}: race entry race ID mismatch.")
        if text(entry["runner_id"]) != runner_id:
            fail(f"{snapshot_id}: race entry runner ID mismatch.")
        context_id = "REPCF1-" + sha256_payload([snapshot_id, race_entry_id, race_id, runner_id, selected_rating_id])[:24].upper()
        if context_id in seen_context_ids:
            fail(f"Duplicate context ID: {context_id}")
        seen_context_ids.add(context_id)
        evidence_hash = sha256_payload([
            context_id, snapshot_id, race_entry_id, race_id, race_date.isoformat(), runner_id,
            canonical_horse_id, canonical_horse_name, selected_rating_id, selected_rating_date.isoformat(),
            rating_age_days, format_decimal(context_rating), race_distance_m, entry["race_class_code"],
            entry["track_id"], entry["track_name"], entry["track_configuration"], entry["track_condition"],
            entry["racing_surface"], entry["rail_position"], barrier, format_decimal(allocated_weight_kg),
            declared_field_size, CONTEXT_STATUS, snapshot["race_entry_horse_performance_snapshot_evidence_sha256"],
            entry["race_entry_evidence_sha256"], snapshot["builder_version"], entry["builder_version"],
            BUILDER_VERSION, CONTRACT_VERSION,
        ])
        output_rows.append({
            "race_entry_performance_context_id": context_id,
            "race_entry_horse_performance_snapshot_id": snapshot_id,
            "race_entry_id": text(entry["race_entry_id"]),
            "race_id": race_id,
            "race_date": race_date.isoformat(),
            "runner_id": runner_id,
            "canonical_horse_id": canonical_horse_id,
            "canonical_horse_name": canonical_horse_name,
            "selected_horse_performance_rating_id": selected_rating_id,
            "selected_rating_as_of_date": selected_rating_date.isoformat(),
            "rating_age_days": str(rating_age_days),
            "context_historical_rating_value": format_decimal(context_rating),
            "race_distance_m": str(race_distance_m),
            "race_class_code": text(entry["race_class_code"]),
            "track_id": text(entry["track_id"]),
            "track_name": text(entry["track_name"]),
            "track_configuration": text(entry["track_configuration"]),
            "track_condition": text(entry["track_condition"]),
            "racing_surface": text(entry["racing_surface"]),
            "rail_position": text(entry["rail_position"]),
            "barrier": str(barrier),
            "allocated_weight_kg": format_decimal(allocated_weight_kg),
            "declared_field_size": str(declared_field_size),
            "race_entry_performance_context_status": CONTEXT_STATUS,
            "source_snapshot_evidence_sha256": text(snapshot["race_entry_horse_performance_snapshot_evidence_sha256"]),
            "source_race_entry_evidence_sha256": text(entry["race_entry_evidence_sha256"]),
            "race_entry_performance_context_evidence_sha256": evidence_hash,
            "source_snapshot_builder_version": text(snapshot["builder_version"]),
            "source_race_entry_builder_version": text(entry["builder_version"]),
            "builder_version": BUILDER_VERSION,
            "contract_version": CONTRACT_VERSION,
            "built_at_utc": built_at_utc,
        })
    atomic_write_csv(OUTPUT_PATH, output_rows)
    print("EDGEIQ_RACE_ENTRY_PERFORMANCE_CONTEXT_FACT_V1_BUILD_PASS")
    print(f"race_entry_horse_performance_snapshot_rows={len(snapshot_rows)}")
    print(f"race_entry_rows={len(raw_race_entry_rows)}")
    print(f"race_entry_schema={'LEGACY' if is_legacy_schema else 'CURRENT_ADAPTED'}")
    print(f"race_entry_performance_context_rows={len(output_rows)}")
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
'''
TARGET.write_text(NEW_CONTENT, encoding='utf-8')
print(f'checkpoint={CHECKPOINT}')
print(f'rewritten={TARGET}')
