from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
PUBLIC_DATA = ROOT / "public" / "data"
DATA_ROOT = ROOT / "data"
OUTPUT_ROOT = ROOT / "outputs"

HORSE_MASTER = PUBLIC_DATA / "edgeiq_canonical_horse_master_v2.csv"
HORSE_MASTER_CANDIDATE = (
    PUBLIC_DATA / "edgeiq_canonical_horse_master_v2_CANDIDATE.csv"
)

HORSE_ALIAS = PUBLIC_DATA / "edgeiq_canonical_horse_alias_v2.csv"
HORSE_ALIAS_CANDIDATE = (
    PUBLIC_DATA / "edgeiq_canonical_horse_alias_v2_CANDIDATE.csv"
)

CURRENT_CONTEXT = PUBLIC_DATA / "edgeiq_race_entry_context_v2.csv"

HORSE_DOCS = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse-v2"
    / "canonical-horse-master"
)

OBSERVATION_DOCS = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse-v2"
    / "historical-observation-source-inventory"
)

OBSERVATION_DOCS.mkdir(parents=True, exist_ok=True)

CURRENT_COVERAGE = (
    HORSE_DOCS
    / "edgeiq_current_runner_horse_master_coverage_v2.csv"
)

CURRENT_UNRESOLVED = (
    HORSE_DOCS
    / "edgeiq_current_runner_unresolved_identity_v2.csv"
)

REBUILD_POPULATION = (
    HORSE_DOCS
    / "edgeiq_historical_observation_rebuild_population_v2.csv"
)

REPAIR_AUDIT_JSON = (
    HORSE_DOCS
    / "EDGEIQ_CANONICAL_HORSE_MASTER_V2_CURRENT_RUNNER_REPAIR_AUDIT.json"
)

REPAIR_AUDIT_MD = (
    HORSE_DOCS
    / "EDGEIQ_CANONICAL_HORSE_MASTER_V2_CURRENT_RUNNER_REPAIR_AUDIT.md"
)

SOURCE_INVENTORY_CSV = (
    OBSERVATION_DOCS
    / "edgeiq_historical_observation_source_inventory_v2.csv"
)

SOURCE_MANIFEST_CSV = (
    OBSERVATION_DOCS
    / "edgeiq_historical_observation_extraction_manifest_v2.csv"
)

SOURCE_REJECTION_CSV = (
    OBSERVATION_DOCS
    / "edgeiq_historical_observation_source_rejections_v2.csv"
)

SOURCE_AUDIT_JSON = (
    OBSERVATION_DOCS
    / "EDGEIQ_HISTORICAL_OBSERVATION_SOURCE_INVENTORY_V2_AUDIT.json"
)

SOURCE_AUDIT_MD = (
    OBSERVATION_DOCS
    / "EDGEIQ_HISTORICAL_OBSERVATION_SOURCE_INVENTORY_V2_AUDIT.md"
)

SOURCE_CONTRACT = (
    OBSERVATION_DOCS
    / "edgeiq_historical_observation_source_inventory_v2_contract.json"
)

REPAIR_BUILDER = (
    "EDGEIQ_CANONICAL_HORSE_MASTER_V2_CURRENT_RUNNER_REPAIR"
)

REPAIR_METHOD = (
    "CURRENT_RACINGCOM_ID_REGISTRATION_AND_EXACT_ID_BINDING_V1"
)

INVENTORY_BUILDER = (
    "EDGEIQ_HISTORICAL_OBSERVATION_SOURCE_INVENTORY_V2"
)

INVENTORY_METHOD = (
    "REPOSITORY_SCHEMA_DISCOVERY_WITHOUT_VALUE_INVENTION_V1"
)

RCOM_PATTERN = re.compile(
    r"^(?:RCOM_HORSE_|RACINGCOM_HORSE_|HORSE_)?(\d+)$",
    re.IGNORECASE,
)

ID_ALIASES = [
    "canonical_horse_id",
    "canonical_runner_id",
    "horse_id",
    "runner_id",
    "racingcom_horse_id",
    "racing_com_horse_id",
    "horse_code",
    "runner_code",
    "competitor_id",
]

NAME_ALIASES = [
    "canonical_horse_name",
    "horse_name",
    "runner_name",
    "competitor_name",
]

DATE_ALIASES = [
    "race_date",
    "meeting_date",
    "performance_date",
    "observation_date",
    "event_date",
]

RACE_ID_ALIASES = [
    "canonical_race_id",
    "race_id",
    "event_id",
]

TRACK_ALIASES = [
    "canonical_track",
    "track",
    "track_name",
    "venue",
]

DISTANCE_ALIASES = [
    "race_distance_metres",
    "distance_metres",
    "distance",
]

FINISH_ALIASES = [
    "finish_position",
    "finishing_position",
    "position",
    "place",
]

FIELD_SIZE_ALIASES = [
    "field_size",
    "declared_field_size",
    "starters",
    "runner_count",
]

MARGIN_ALIASES = [
    "margin",
    "beaten_margin",
    "margin_lengths",
]

TIME_ALIASES = [
    "race_time",
    "official_time",
    "elapsed_time",
]

PERFORMANCE_VALUE_ALIASES = [
    "horse_performance_observation_value",
    "performance_rating_value",
    "normalised_performance_value",
    "performance_intelligence_value",
    "performance_value",
    "rating_value",
    "epi",
    "epi_value",
]


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalise_name(value: str) -> str:
    value = clean(value).upper()
    value = value.replace("’", "'")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def safe_relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_csv(
    path: Path,
) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
        errors="replace",
    ) as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])

        rows = [
            {
                key: clean(value)
                for key, value in row.items()
            }
            for row in reader
        ]

    return fields, rows


def write_csv(
    path: Path,
    fields: list[str],
    rows: list[dict[str, str]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            lineterminator="\n",
        )

        writer.writeheader()
        writer.writerows(rows)


def promote(candidate: Path, production: Path) -> str:
    temporary = production.with_suffix(
        production.suffix + ".tmp"
    )

    shutil.copy2(candidate, temporary)
    os.replace(temporary, production)

    candidate_hash = sha256_file(candidate)
    production_hash = sha256_file(production)

    if candidate_hash != production_hash:
        raise RuntimeError(
            f"Candidate/production hash mismatch: {production}"
        )

    return production_hash


def find_column(
    fields: list[str],
    aliases: list[str],
) -> str | None:
    lookup = {
        field.lower(): field
        for field in fields
    }

    for alias in aliases:
        if alias.lower() in lookup:
            return lookup[alias.lower()]

    return None


def parse_racingcom_id(value: str) -> str:
    value = clean(value)

    match = RCOM_PATTERN.match(value)

    if not match:
        return ""

    return match.group(1)


def deterministic_check(
    path: Path,
    fields: list[str],
    rows: list[dict[str, str]],
    directory: Path,
    filename: str,
) -> bool:
    check_path = directory / filename

    write_csv(
        check_path,
        fields,
        rows,
    )

    passed = (
        sha256_file(path)
        == sha256_file(check_path)
    )

    check_path.unlink(missing_ok=True)

    return passed


# ============================================================
# INPUTS
# ============================================================

master_fields, master_rows = read_csv(HORSE_MASTER)
alias_fields, alias_rows = read_csv(HORSE_ALIAS)
context_fields, context_rows = read_csv(CURRENT_CONTEXT)

required_master = {
    "canonical_horse_id",
    "canonical_horse_name",
    "normalised_horse_name",
    "primary_source_system",
    "primary_source_horse_id",
    "source_record_count",
    "source_file_count",
    "identity_resolution_status",
    "identity_resolution_method",
    "horse_master_builder_version",
    "horse_master_method_version",
    "canonical_horse_evidence_sha256",
}

required_alias = {
    "canonical_horse_id",
    "source_system",
    "source_horse_id",
    "source_horse_name",
    "normalised_horse_name",
    "source_path",
    "source_row_number",
    "source_row_evidence_sha256",
    "alias_builder_version",
    "alias_method_version",
    "alias_evidence_sha256",
}

required_context = {
    "canonical_runner_id",
    "canonical_horse_name",
}

missing_master = sorted(
    required_master - set(master_fields)
)

missing_alias = sorted(
    required_alias - set(alias_fields)
)

missing_context = sorted(
    required_context - set(context_fields)
)

if missing_master:
    raise RuntimeError(
        "Horse Master fields missing: "
        + ", ".join(missing_master)
    )

if missing_alias:
    raise RuntimeError(
        "Horse Alias fields missing: "
        + ", ".join(missing_alias)
    )

if missing_context:
    raise RuntimeError(
        "Current context fields missing: "
        + ", ".join(missing_context)
    )


# ============================================================
# REGISTER CURRENT RACING.COM IDENTITIES
# ============================================================

master_by_id = {
    row["canonical_horse_id"]: row
    for row in master_rows
}

alias_natural_keys = {
    (
        row["canonical_horse_id"],
        row["source_system"],
        row["source_horse_id"],
        row["source_path"],
        row["source_row_number"],
    )
    for row in alias_rows
}

current_unique: dict[str, dict[str, str]] = {}

for context in context_rows:
    runner_id = context["canonical_runner_id"]
    horse_name = context["canonical_horse_name"]

    if runner_id not in current_unique:
        current_unique[runner_id] = {
            "canonical_runner_id": runner_id,
            "canonical_horse_name": horse_name,
        }

registered_count = 0
existing_count = 0
invalid_current_id_count = 0

for runner_id, current in sorted(
    current_unique.items()
):
    racingcom_id = parse_racingcom_id(runner_id)

    if not racingcom_id:
        invalid_current_id_count += 1
        continue

    horse_name = current["canonical_horse_name"]
    normalised = normalise_name(horse_name)

    canonical_horse_id = (
        f"HORSE|RACINGCOM|{racingcom_id}"
    )

    source_payload = {
        "canonical_horse_id": canonical_horse_id,
        "canonical_runner_id": runner_id,
        "canonical_horse_name": horse_name,
        "source": safe_relative(CURRENT_CONTEXT),
        "method": REPAIR_METHOD,
    }

    evidence_hash = sha256_text(
        canonical_json(source_payload)
    )

    if canonical_horse_id not in master_by_id:
        new_master = {
            field: ""
            for field in master_fields
        }

        new_master.update(
            {
                "canonical_horse_id": canonical_horse_id,
                "canonical_horse_name": horse_name,
                "normalised_horse_name": normalised,
                "primary_source_system": "RACINGCOM",
                "primary_source_horse_id": racingcom_id,
                "date_of_birth": "",
                "sex": "",
                "sire": "",
                "dam": "",
                "country": "",
                "horse_status": "CURRENT_DECLARED_RUNNER",
                "source_record_count": "1",
                "source_file_count": "1",
                "identity_resolution_status": (
                    "CANONICAL_SOURCE_ID_AVAILABLE"
                ),
                "identity_resolution_method": (
                    "CURRENT_RACINGCOM_RUNNER_ID"
                ),
                "horse_master_builder_version": (
                    REPAIR_BUILDER
                ),
                "horse_master_method_version": (
                    REPAIR_METHOD
                ),
                "canonical_horse_evidence_sha256": (
                    evidence_hash
                ),
            }
        )

        master_rows.append(new_master)
        master_by_id[canonical_horse_id] = new_master
        registered_count += 1

    else:
        existing_count += 1

    alias_key = (
        canonical_horse_id,
        "RACINGCOM",
        racingcom_id,
        safe_relative(CURRENT_CONTEXT),
        runner_id,
    )

    if alias_key not in alias_natural_keys:
        alias_payload = {
            "canonical_horse_id": canonical_horse_id,
            "source_system": "RACINGCOM",
            "source_horse_id": racingcom_id,
            "source_horse_name": horse_name,
            "source_path": safe_relative(CURRENT_CONTEXT),
            "source_row_number": runner_id,
            "source_evidence": evidence_hash,
        }

        new_alias = {
            field: ""
            for field in alias_fields
        }

        new_alias.update(
            {
                "canonical_horse_id": canonical_horse_id,
                "source_system": "RACINGCOM",
                "source_horse_id": racingcom_id,
                "source_horse_name": horse_name,
                "normalised_horse_name": normalised,
                "source_path": safe_relative(
                    CURRENT_CONTEXT
                ),
                "source_row_number": runner_id,
                "source_row_evidence_sha256": evidence_hash,
                "alias_builder_version": REPAIR_BUILDER,
                "alias_method_version": REPAIR_METHOD,
                "alias_evidence_sha256": sha256_text(
                    canonical_json(alias_payload)
                ),
            }
        )

        alias_rows.append(new_alias)
        alias_natural_keys.add(alias_key)

master_rows.sort(
    key=lambda row: row["canonical_horse_id"]
)

alias_rows.sort(
    key=lambda row: (
        row["canonical_horse_id"],
        row["source_system"],
        row["source_horse_id"],
        row["source_path"],
        row["source_row_number"],
    )
)

write_csv(
    HORSE_MASTER_CANDIDATE,
    master_fields,
    master_rows,
)

write_csv(
    HORSE_ALIAS_CANDIDATE,
    alias_fields,
    alias_rows,
)


# ============================================================
# REBUILD CURRENT COVERAGE
# ============================================================

coverage_fields = [
    "current_runner_id",
    "current_horse_name",
    "normalised_horse_name",
    "resolved_canonical_horse_id",
    "resolution_status",
    "resolution_method",
    "resolution_reason_code",
    "candidate_count",
]

coverage_rows: list[dict[str, str]] = []
unresolved_rows: list[dict[str, str]] = []
rebuild_rows: list[dict[str, str]] = []

for runner_id, current in sorted(
    current_unique.items(),
    key=lambda item: (
        normalise_name(
            item[1]["canonical_horse_name"]
        ),
        item[0],
    ),
):
    racingcom_id = parse_racingcom_id(runner_id)
    canonical_horse_id = (
        f"HORSE|RACINGCOM|{racingcom_id}"
        if racingcom_id
        else ""
    )

    if (
        canonical_horse_id
        and canonical_horse_id in master_by_id
    ):
        status = "CURRENT_RUNNER_RESOLVED"
        method = "CURRENT_RACINGCOM_ID_EXACT"
        reason = "RACINGCOM_ID_REGISTERED_IN_HORSE_MASTER"
        candidate_count = 1

    else:
        status = "CURRENT_RUNNER_UNRESOLVED"
        method = ""
        reason = (
            "CURRENT_RUNNER_ID_NOT_VALID_RACINGCOM_ID"
            if not racingcom_id
            else "REGISTERED_CANONICAL_ID_NOT_FOUND"
        )
        candidate_count = 0

    coverage_row = {
        "current_runner_id": runner_id,
        "current_horse_name": current[
            "canonical_horse_name"
        ],
        "normalised_horse_name": normalise_name(
            current["canonical_horse_name"]
        ),
        "resolved_canonical_horse_id": canonical_horse_id,
        "resolution_status": status,
        "resolution_method": method,
        "resolution_reason_code": reason,
        "candidate_count": str(candidate_count),
    }

    coverage_rows.append(coverage_row)

    if status == "CURRENT_RUNNER_UNRESOLVED":
        unresolved_rows.append(coverage_row)

    rebuild_rows.append(
        {
            **coverage_row,
            "historical_observation_rebuild_required": "TRUE",
            "rebuild_priority": "P0_CURRENT_ACTIVE_POPULATION",
        }
    )

write_csv(
    CURRENT_COVERAGE,
    coverage_fields,
    coverage_rows,
)

write_csv(
    CURRENT_UNRESOLVED,
    coverage_fields,
    unresolved_rows,
)

rebuild_fields = coverage_fields + [
    "historical_observation_rebuild_required",
    "rebuild_priority",
]

write_csv(
    REBUILD_POPULATION,
    rebuild_fields,
    rebuild_rows,
)


# ============================================================
# HORSE MASTER REPAIR AUDIT
# ============================================================

master_ids = [
    row["canonical_horse_id"]
    for row in master_rows
]

current_resolved = sum(
    1
    for row in coverage_rows
    if row["resolution_status"]
    == "CURRENT_RUNNER_RESOLVED"
)

repair_checks = {
    "all_current_runner_ids_parse": (
        invalid_current_id_count == 0
    ),
    "all_current_runners_resolved": (
        current_resolved == len(current_unique)
    ),
    "no_current_runners_unresolved": (
        len(unresolved_rows) == 0
    ),
    "canonical_horse_ids_unique": (
        len(master_ids) == len(set(master_ids))
    ),
    "every_current_runner_has_racingcom_master": all(
        row["resolved_canonical_horse_id"]
        in master_by_id
        for row in coverage_rows
    ),
    "every_resolution_has_one_candidate": all(
        row["candidate_count"] == "1"
        for row in coverage_rows
    ),
    "master_evidence_complete": all(
        row["canonical_horse_evidence_sha256"]
        for row in master_rows
    ),
    "alias_evidence_complete": all(
        row["alias_evidence_sha256"]
        for row in alias_rows
    ),
    "master_deterministic": deterministic_check(
        HORSE_MASTER_CANDIDATE,
        master_fields,
        master_rows,
        HORSE_DOCS,
        "horse_master_repair_deterministic_check.csv",
    ),
    "alias_deterministic": deterministic_check(
        HORSE_ALIAS_CANDIDATE,
        alias_fields,
        alias_rows,
        HORSE_DOCS,
        "horse_alias_repair_deterministic_check.csv",
    ),
}

if not all(repair_checks.values()):
    raise RuntimeError(
        "Horse Master current-runner repair failed:\n"
        + json.dumps(repair_checks, indent=2)
    )

master_hash = promote(
    HORSE_MASTER_CANDIDATE,
    HORSE_MASTER,
)

alias_hash = promote(
    HORSE_ALIAS_CANDIDATE,
    HORSE_ALIAS,
)

repair_audit = {
    "status": (
        "EDGEIQ_CANONICAL_HORSE_MASTER_V2_CURRENT_RUNNER_REPAIR_PASS"
    ),
    "current_unique_runners": len(current_unique),
    "current_runner_ids_registered": registered_count,
    "current_runner_ids_already_present": existing_count,
    "current_runner_ids_invalid": invalid_current_id_count,
    "current_runners_resolved": current_resolved,
    "current_runners_unresolved": len(unresolved_rows),
    "horse_master_rows_after_repair": len(master_rows),
    "horse_alias_rows_after_repair": len(alias_rows),
    "checks": repair_checks,
    "master_candidate_sha256": sha256_file(
        HORSE_MASTER_CANDIDATE
    ),
    "master_production_sha256": master_hash,
    "alias_candidate_sha256": sha256_file(
        HORSE_ALIAS_CANDIDATE
    ),
    "alias_production_sha256": alias_hash,
}

REPAIR_AUDIT_JSON.write_text(
    json.dumps(repair_audit, indent=2),
    encoding="utf-8",
)

repair_md = [
    "# EDGEIQ Canonical Horse Master V2 Current-Runner Repair",
    "",
    f"Status: `{repair_audit['status']}`",
    "",
    "## Population",
    "",
    f"- Current runners: `{len(current_unique)}`",
    f"- New Racing.com identities registered: `{registered_count}`",
    f"- Existing Racing.com identities retained: `{existing_count}`",
    f"- Current runners resolved: `{current_resolved}`",
    f"- Current runners unresolved: `{len(unresolved_rows)}`",
    f"- Horse Master rows after repair: `{len(master_rows)}`",
    f"- Alias rows after repair: `{len(alias_rows)}`",
    "",
    "## Audit Checks",
    "",
]

for key, value in repair_checks.items():
    repair_md.append(
        f"- `{key}`: `{'PASS' if value else 'FAIL'}`"
    )

repair_md.extend(
    [
        "",
        "## Governance",
        "",
        "- `RCOM_HORSE_<id>` is parsed as a governed Racing.com source identity.",
        "- Current runners are registered as `HORSE|RACINGCOM|<id>`.",
        "- Horse names are descriptive attributes, not the primary identity key.",
        "- No fuzzy matching or cross-horse merging is performed.",
        "",
        f"- Master SHA256: `{master_hash}`",
        f"- Alias SHA256: `{alias_hash}`",
        "",
    ]
)

REPAIR_AUDIT_MD.write_text(
    "\n".join(repair_md),
    encoding="utf-8",
)


# ============================================================
# HISTORICAL OBSERVATION SOURCE INVENTORY
# ============================================================

excluded_names = {
    HORSE_MASTER.name.lower(),
    HORSE_MASTER_CANDIDATE.name.lower(),
    HORSE_ALIAS.name.lower(),
    HORSE_ALIAS_CANDIDATE.name.lower(),
    "edgeiq_race_entry_context_v2.csv",
    "edgeiq_race_entry_context_v2_candidate.csv",
    "edgeiq_race_entry_suitability_v2.csv",
    "edgeiq_race_entry_suitability_v2_candidate.csv",
    "edgeiq_race_entry_projected_performance_v2.csv",
    "edgeiq_race_entry_projected_performance_v2_candidate.csv",
    "edgeiq_race_entry_epi_v2.csv",
    "edgeiq_race_entry_epi_v2_candidate.csv",
    "edgeiq_race_intelligence_feed_v2.csv",
    "edgeiq_race_intelligence_feed_v2_candidate.csv",
}

repository_csvs: list[Path] = []

for search_root in (
    PUBLIC_DATA,
    DATA_ROOT,
    OUTPUT_ROOT,
):
    if not search_root.exists():
        continue

    for path in search_root.rglob("*.csv"):
        if path.name.lower() in excluded_names:
            continue

        repository_csvs.append(path)

repository_csvs = sorted(
    set(repository_csvs),
    key=lambda path: str(path).lower(),
)

inventory_fields = [
    "source_path",
    "source_file_sha256",
    "row_count",
    "field_count",
    "horse_id_column",
    "horse_name_column",
    "race_date_column",
    "race_id_column",
    "track_column",
    "distance_column",
    "finish_position_column",
    "field_size_column",
    "margin_column",
    "race_time_column",
    "performance_value_column",
    "identity_available",
    "race_date_available",
    "race_context_field_count",
    "performance_result_field_count",
    "observation_source_status",
    "observation_source_reason_code",
    "inventory_evidence_sha256",
]

manifest_fields = inventory_fields + [
    "extraction_priority",
    "target_observation_grain",
    "target_builder_action",
]

inventory_rows: list[dict[str, str]] = []
manifest_rows: list[dict[str, str]] = []
rejection_rows: list[dict[str, str]] = []

status_counts: Counter[str] = Counter()
total_candidate_rows = 0

for index, path in enumerate(
    repository_csvs,
    start=1,
):
    try:
        fields, rows = read_csv(path)
        read_error = ""
    except Exception as exc:
        fields = []
        rows = []
        read_error = str(exc)

    horse_id_column = find_column(
        fields,
        ID_ALIASES,
    )

    horse_name_column = find_column(
        fields,
        NAME_ALIASES,
    )

    race_date_column = find_column(
        fields,
        DATE_ALIASES,
    )

    race_id_column = find_column(
        fields,
        RACE_ID_ALIASES,
    )

    track_column = find_column(
        fields,
        TRACK_ALIASES,
    )

    distance_column = find_column(
        fields,
        DISTANCE_ALIASES,
    )

    finish_column = find_column(
        fields,
        FINISH_ALIASES,
    )

    field_size_column = find_column(
        fields,
        FIELD_SIZE_ALIASES,
    )

    margin_column = find_column(
        fields,
        MARGIN_ALIASES,
    )

    race_time_column = find_column(
        fields,
        TIME_ALIASES,
    )

    performance_column = find_column(
        fields,
        PERFORMANCE_VALUE_ALIASES,
    )

    identity_available = bool(
        horse_id_column or horse_name_column
    )

    race_context_columns = [
        race_id_column,
        track_column,
        distance_column,
    ]

    performance_result_columns = [
        finish_column,
        field_size_column,
        margin_column,
        race_time_column,
        performance_column,
    ]

    race_context_count = sum(
        1
        for value in race_context_columns
        if value
    )

    performance_result_count = sum(
        1
        for value in performance_result_columns
        if value
    )

    if read_error:
        status = "SOURCE_REJECTED"
        reason = "CSV_READ_FAILED"

    elif not rows:
        status = "SOURCE_REJECTED"
        reason = "SOURCE_EMPTY"

    elif not identity_available:
        status = "SOURCE_REJECTED"
        reason = "HORSE_IDENTITY_UNAVAILABLE"

    elif not race_date_column:
        status = "SOURCE_REJECTED"
        reason = "RACE_DATE_UNAVAILABLE"

    elif (
        race_context_count == 0
        and performance_result_count == 0
    ):
        status = "SOURCE_REJECTED"
        reason = "NO_RACE_OR_PERFORMANCE_OBSERVATION_FIELDS"

    elif performance_column:
        status = "OBSERVATION_VALUE_SOURCE_ELIGIBLE"
        reason = "GOVERNED_PERFORMANCE_VALUE_AVAILABLE"

    elif performance_result_count >= 2:
        status = "RAW_RUN_SOURCE_ELIGIBLE"
        reason = "MULTIPLE_FACTUAL_RESULT_FIELDS_AVAILABLE"

    else:
        status = "RAW_RUN_SOURCE_PARTIAL"
        reason = "IDENTITY_DATE_AND_LIMITED_RUN_CONTEXT_AVAILABLE"

    status_counts[status] += 1

    if status != "SOURCE_REJECTED":
        total_candidate_rows += len(rows)

    payload = {
        "source_path": safe_relative(path),
        "source_sha256": (
            sha256_file(path)
            if path.exists()
            else ""
        ),
        "row_count": len(rows),
        "fields": fields,
        "status": status,
        "reason": reason,
    }

    inventory_row = {
        "source_path": safe_relative(path),
        "source_file_sha256": (
            sha256_file(path)
            if path.exists()
            else ""
        ),
        "row_count": str(len(rows)),
        "field_count": str(len(fields)),
        "horse_id_column": horse_id_column or "",
        "horse_name_column": horse_name_column or "",
        "race_date_column": race_date_column or "",
        "race_id_column": race_id_column or "",
        "track_column": track_column or "",
        "distance_column": distance_column or "",
        "finish_position_column": finish_column or "",
        "field_size_column": field_size_column or "",
        "margin_column": margin_column or "",
        "race_time_column": race_time_column or "",
        "performance_value_column": performance_column or "",
        "identity_available": str(
            identity_available
        ).upper(),
        "race_date_available": str(
            bool(race_date_column)
        ).upper(),
        "race_context_field_count": str(
            race_context_count
        ),
        "performance_result_field_count": str(
            performance_result_count
        ),
        "observation_source_status": status,
        "observation_source_reason_code": reason,
        "inventory_evidence_sha256": sha256_text(
            canonical_json(payload)
        ),
    }

    inventory_rows.append(inventory_row)

    if status == "SOURCE_REJECTED":
        rejection_rows.append(inventory_row)
    else:
        if status == "OBSERVATION_VALUE_SOURCE_ELIGIBLE":
            priority = "P0_VALUE_SOURCE"
            action = "EXTRACT_GOVERNED_OBSERVATION_VALUE"

        elif status == "RAW_RUN_SOURCE_ELIGIBLE":
            priority = "P1_RAW_RUN_SOURCE"
            action = "EXTRACT_FACTUAL_RUN_OBSERVATION"

        else:
            priority = "P2_PARTIAL_SOURCE"
            action = "EXTRACT_PARTIAL_OBSERVATION_WITH_UNAVAILABLE_FIELDS"

        manifest_rows.append(
            {
                **inventory_row,
                "extraction_priority": priority,
                "target_observation_grain": (
                    "ONE ROW PER HORSE PER HISTORICAL RACE"
                ),
                "target_builder_action": action,
            }
        )

    if index % 500 == 0:
        print(
            f"Observation inventory progress: "
            f"{index}/{len(repository_csvs)}"
        )

inventory_rows.sort(
    key=lambda row: row["source_path"].lower()
)

manifest_rows.sort(
    key=lambda row: (
        row["extraction_priority"],
        row["source_path"].lower(),
    )
)

rejection_rows.sort(
    key=lambda row: (
        row["observation_source_reason_code"],
        row["source_path"].lower(),
    )
)

write_csv(
    SOURCE_INVENTORY_CSV,
    inventory_fields,
    inventory_rows,
)

write_csv(
    SOURCE_MANIFEST_CSV,
    manifest_fields,
    manifest_rows,
)

write_csv(
    SOURCE_REJECTION_CSV,
    inventory_fields,
    rejection_rows,
)

inventory_checks = {
    "repository_csv_population_nonzero": (
        len(repository_csvs) > 0
    ),
    "one_inventory_row_per_discovered_csv": (
        len(inventory_rows)
        == len(repository_csvs)
    ),
    "eligible_source_population_nonzero": (
        len(manifest_rows) > 0
    ),
    "eligible_sources_have_identity": all(
        row["identity_available"] == "TRUE"
        for row in manifest_rows
    ),
    "eligible_sources_have_race_date": all(
        row["race_date_available"] == "TRUE"
        for row in manifest_rows
    ),
    "rejected_sources_have_reason": all(
        row["observation_source_reason_code"]
        for row in rejection_rows
    ),
    "inventory_evidence_complete": all(
        row["inventory_evidence_sha256"]
        for row in inventory_rows
    ),
    "inventory_deterministic": deterministic_check(
        SOURCE_INVENTORY_CSV,
        inventory_fields,
        inventory_rows,
        OBSERVATION_DOCS,
        "source_inventory_deterministic_check.csv",
    ),
    "manifest_deterministic": deterministic_check(
        SOURCE_MANIFEST_CSV,
        manifest_fields,
        manifest_rows,
        OBSERVATION_DOCS,
        "source_manifest_deterministic_check.csv",
    ),
}

if not all(inventory_checks.values()):
    raise RuntimeError(
        "Historical source inventory audit failed:\n"
        + json.dumps(inventory_checks, indent=2)
    )

inventory_audit = {
    "status": (
        "EDGEIQ_HISTORICAL_OBSERVATION_SOURCE_INVENTORY_V2_AUDIT_PASS"
    ),
    "repository_csv_files_discovered": len(repository_csvs),
    "eligible_source_files": len(manifest_rows),
    "rejected_source_files": len(rejection_rows),
    "candidate_source_rows": total_candidate_rows,
    "status_counts": dict(
        sorted(status_counts.items())
    ),
    "checks": inventory_checks,
    "inventory_sha256": sha256_file(
        SOURCE_INVENTORY_CSV
    ),
    "manifest_sha256": sha256_file(
        SOURCE_MANIFEST_CSV
    ),
    "rejections_sha256": sha256_file(
        SOURCE_REJECTION_CSV
    ),
}

SOURCE_AUDIT_JSON.write_text(
    json.dumps(inventory_audit, indent=2),
    encoding="utf-8",
)

SOURCE_CONTRACT.write_text(
    json.dumps(
        {
            "contract_name": (
                "edgeiq_historical_observation_source_inventory_v2"
            ),
            "grain": "ONE ROW PER DISCOVERED CSV SOURCE",
            "eligibility_rules": [
                "Horse identity or horse name is required.",
                "Historical race date is required.",
                "At least one race-context or performance-result field is required.",
                "A governed performance value source receives highest priority.",
                "No performance value is calculated during source discovery.",
            ],
            "builder_version": INVENTORY_BUILDER,
            "method_version": INVENTORY_METHOD,
            "inventory_fields": inventory_fields,
            "manifest_fields": manifest_fields,
        },
        indent=2,
    ),
    encoding="utf-8",
)

inventory_md = [
    "# EDGEIQ Historical Observation Source Inventory V2",
    "",
    f"Status: `{inventory_audit['status']}`",
    "",
    "## Population",
    "",
    (
        "- Repository CSV files discovered: "
        f"`{len(repository_csvs)}`"
    ),
    (
        "- Eligible source files: "
        f"`{len(manifest_rows)}`"
    ),
    (
        "- Rejected source files: "
        f"`{len(rejection_rows)}`"
    ),
    (
        "- Candidate source rows: "
        f"`{total_candidate_rows}`"
    ),
    "",
    "## Source Status",
    "",
]

for key, value in inventory_audit[
    "status_counts"
].items():
    inventory_md.append(
        f"- `{key}`: `{value}`"
    )

inventory_md.extend(
    [
        "",
        "## Governance",
        "",
        "- This unit discovers and classifies source data only.",
        "- It does not calculate or invent performance values.",
        "- Every selected source retains its file hash and detected schema.",
        "- Rejected sources retain an explicit rejection reason.",
        "",
    ]
)

SOURCE_AUDIT_MD.write_text(
    "\n".join(inventory_md),
    encoding="utf-8",
)

print(
    json.dumps(
        {
            "horse_master_repair_status": repair_audit[
                "status"
            ],
            "current_runners": len(current_unique),
            "current_runners_registered": registered_count,
            "current_runners_resolved": current_resolved,
            "current_runners_unresolved": len(unresolved_rows),
            "horse_master_rows_after_repair": len(master_rows),
            "historical_source_inventory_status": inventory_audit[
                "status"
            ],
            "repository_csv_files_discovered": len(
                repository_csvs
            ),
            "eligible_historical_source_files": len(
                manifest_rows
            ),
            "rejected_historical_source_files": len(
                rejection_rows
            ),
            "candidate_historical_source_rows": (
                total_candidate_rows
            ),
        },
        indent=2,
    )
)
