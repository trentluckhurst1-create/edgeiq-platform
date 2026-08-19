from __future__ import annotations

import csv
import hashlib
import json
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

DOCS = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse-v2"
    / "canonical-horse-master"
)

DOCS.mkdir(parents=True, exist_ok=True)
PUBLIC_DATA.mkdir(parents=True, exist_ok=True)

MASTER_CANDIDATE = (
    PUBLIC_DATA
    / "edgeiq_canonical_horse_master_v2_CANDIDATE.csv"
)

MASTER_PRODUCTION = (
    PUBLIC_DATA
    / "edgeiq_canonical_horse_master_v2.csv"
)

ALIAS_CANDIDATE = (
    PUBLIC_DATA
    / "edgeiq_canonical_horse_alias_v2_CANDIDATE.csv"
)

ALIAS_PRODUCTION = (
    PUBLIC_DATA
    / "edgeiq_canonical_horse_alias_v2.csv"
)

SOURCE_COVERAGE_PATH = (
    DOCS
    / "edgeiq_canonical_horse_master_v2_source_coverage.csv"
)

COLLISION_PATH = (
    DOCS
    / "edgeiq_canonical_horse_master_v2_name_collisions.csv"
)

CURRENT_COVERAGE_PATH = (
    DOCS
    / "edgeiq_current_runner_horse_master_coverage_v2.csv"
)

REBUILD_POPULATION_PATH = (
    DOCS
    / "edgeiq_historical_observation_rebuild_population_v2.csv"
)

UNRESOLVED_PATH = (
    DOCS
    / "edgeiq_current_runner_unresolved_identity_v2.csv"
)

AUDIT_JSON = (
    DOCS
    / "EDGEIQ_CANONICAL_HORSE_MASTER_V2_AUDIT.json"
)

AUDIT_MD = (
    DOCS
    / "EDGEIQ_CANONICAL_HORSE_MASTER_V2_AUDIT.md"
)

CONTRACT_JSON = (
    DOCS
    / "edgeiq_canonical_horse_master_v2_contract.json"
)

SOURCE_INVENTORY_JSON = (
    DOCS
    / "edgeiq_canonical_horse_master_v2_source_inventory.json"
)

BUILDER_VERSION = "EDGEIQ_CANONICAL_HORSE_MASTER_V2"
METHOD_VERSION = "SOURCE_ID_PRESERVING_EXACT_ALIAS_CONSOLIDATION_V1"

CURRENT_CONTEXT_PATH = (
    PUBLIC_DATA / "edgeiq_race_entry_context_v2.csv"
)

CURRENT_ENTRY_PATH = (
    PUBLIC_DATA / "edgeiq_race_entry_fact_v1.csv"
)

EXCLUDED_FILENAMES = {
    MASTER_CANDIDATE.name.lower(),
    MASTER_PRODUCTION.name.lower(),
    ALIAS_CANDIDATE.name.lower(),
    ALIAS_PRODUCTION.name.lower(),
}

ID_ALIASES = [
    "canonical_horse_id",
    "horse_id",
    "runner_id",
    "canonical_runner_id",
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
    "name",
    "competitor_name",
]

DOB_ALIASES = [
    "date_of_birth",
    "dob",
    "foaling_date",
]

SEX_ALIASES = [
    "sex",
    "horse_sex",
    "gender",
]

SIRE_ALIASES = [
    "sire",
    "sire_name",
]

DAM_ALIASES = [
    "dam",
    "dam_name",
]

COUNTRY_ALIASES = [
    "country",
    "country_code",
    "horse_country",
]

STATUS_ALIASES = [
    "status",
    "horse_status",
    "runner_status",
]

SOURCE_ID_PRIORITY = {
    "canonical_horse_id": 100,
    "racingcom_horse_id": 95,
    "racing_com_horse_id": 95,
    "horse_id": 90,
    "horse_code": 85,
    "runner_id": 80,
    "canonical_runner_id": 75,
    "runner_code": 70,
    "competitor_id": 65,
}


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalise_name(value: str) -> str:
    value = clean(value).upper()
    value = value.replace("’", "'")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def safe_relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


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


def read_csv(
    path: Path,
) -> tuple[list[str], list[dict[str, str]]]:
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
            f"Promotion hash mismatch for {production}"
        )

    return production_hash


def find_column(
    fields: list[str],
    aliases: list[str],
) -> str | None:
    lookup = {
        field.strip().lower(): field
        for field in fields
    }

    for alias in aliases:
        if alias.lower() in lookup:
            return lookup[alias.lower()]

    return None


def discover_csv_files() -> list[Path]:
    roots = [
        PUBLIC_DATA,
        DATA_ROOT,
        OUTPUT_ROOT,
    ]

    files: list[Path] = []

    for root in roots:
        if not root.exists():
            continue

        for path in root.rglob("*.csv"):
            if path.name.lower() in EXCLUDED_FILENAMES:
                continue

            if "node_modules" in {
                part.lower()
                for part in path.parts
            }:
                continue

            files.append(path)

    return sorted(
        set(files),
        key=lambda path: str(path).lower(),
    )


def choose_source_id_column(
    fields: list[str],
) -> str | None:
    candidates = []

    for field in fields:
        field_lower = field.lower()

        if field_lower in ID_ALIASES:
            priority = SOURCE_ID_PRIORITY.get(
                field_lower,
                0,
            )
            candidates.append(
                (priority, field)
            )

    if not candidates:
        return None

    candidates.sort(
        key=lambda value: (
            -value[0],
            value[1].lower(),
        )
    )

    return candidates[0][1]


def canonical_id(
    source_system: str,
    source_id: str,
) -> str:
    return (
        "HORSE|"
        + source_system.upper()
        + "|"
        + source_id.upper()
    )


def source_system_from_path(path: Path) -> str:
    path_text = str(path).lower()

    if "racingcom" in path_text or "racing_com" in path_text:
        return "RACINGCOM"

    if "racing australia" in path_text or "racingaustralia" in path_text:
        return "RACINGAUSTRALIA"

    if "sportsbet" in path_text:
        return "SPORTSBET"

    if "betfair" in path_text:
        return "BETFAIR"

    if "tab" in path_text:
        return "TAB"

    return "EDGEIQ"


def first_non_blank(
    rows: list[dict[str, str]],
    column: str | None,
) -> str:
    if not column:
        return ""

    for row in rows:
        value = clean(row.get(column, ""))

        if value:
            return value

    return ""


csv_files = discover_csv_files()

source_inventory: list[dict[str, Any]] = []
identity_records: list[dict[str, str]] = []

for path in csv_files:
    try:
        fields, rows = read_csv(path)
    except Exception as exc:
        source_inventory.append(
            {
                "source_path": safe_relative(path),
                "status": "READ_FAILED",
                "reason": str(exc),
            }
        )
        continue

    id_column = choose_source_id_column(fields)
    name_column = find_column(fields, NAME_ALIASES)

    inventory_row = {
        "source_path": safe_relative(path),
        "row_count": len(rows),
        "field_count": len(fields),
        "horse_id_column": id_column or "",
        "horse_name_column": name_column or "",
        "eligible": bool(
            id_column
            and name_column
            and rows
        ),
    }

    source_inventory.append(inventory_row)

    if not inventory_row["eligible"]:
        continue

    source_system = source_system_from_path(path)

    dob_column = find_column(fields, DOB_ALIASES)
    sex_column = find_column(fields, SEX_ALIASES)
    sire_column = find_column(fields, SIRE_ALIASES)
    dam_column = find_column(fields, DAM_ALIASES)
    country_column = find_column(fields, COUNTRY_ALIASES)
    status_column = find_column(fields, STATUS_ALIASES)

    for row_number, row in enumerate(
        rows,
        start=2,
    ):
        source_id = clean(row.get(id_column, ""))
        horse_name = clean(row.get(name_column, ""))

        if not source_id or not horse_name:
            continue

        source_identity_key = (
            source_system,
            source_id.upper(),
        )

        identity_records.append(
            {
                "source_system": source_system,
                "source_horse_id": source_id,
                "source_horse_name": horse_name,
                "normalised_horse_name": normalise_name(
                    horse_name
                ),
                "date_of_birth": clean(
                    row.get(dob_column or "", "")
                ),
                "sex": clean(
                    row.get(sex_column or "", "")
                ),
                "sire": clean(
                    row.get(sire_column or "", "")
                ),
                "dam": clean(
                    row.get(dam_column or "", "")
                ),
                "country": clean(
                    row.get(country_column or "", "")
                ),
                "source_status": clean(
                    row.get(status_column or "", "")
                ),
                "source_path": safe_relative(path),
                "source_row_number": str(row_number),
                "source_identity_key": "|".join(
                    source_identity_key
                ),
                "source_row_evidence_sha256": sha256_text(
                    canonical_json(row)
                ),
            }
        )

SOURCE_INVENTORY_JSON.write_text(
    json.dumps(
        {
            "generated_at_utc": datetime.now(
                timezone.utc
            ).isoformat(),
            "csv_files_discovered": len(csv_files),
            "eligible_sources": sum(
                1
                for row in source_inventory
                if row.get("eligible")
            ),
            "sources": source_inventory,
        },
        indent=2,
    ),
    encoding="utf-8",
)

records_by_source_identity: dict[
    tuple[str, str],
    list[dict[str, str]],
] = defaultdict(list)

for record in identity_records:
    records_by_source_identity[
        (
            record["source_system"],
            record["source_horse_id"].upper(),
        )
    ].append(record)

master_fields = [
    "canonical_horse_id",
    "canonical_horse_name",
    "normalised_horse_name",
    "primary_source_system",
    "primary_source_horse_id",
    "date_of_birth",
    "sex",
    "sire",
    "dam",
    "country",
    "horse_status",
    "source_record_count",
    "source_file_count",
    "identity_resolution_status",
    "identity_resolution_method",
    "horse_master_builder_version",
    "horse_master_method_version",
    "canonical_horse_evidence_sha256",
]

alias_fields = [
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
]

master_rows: list[dict[str, str]] = []
alias_rows: list[dict[str, str]] = []

for (
    source_system,
    source_id_upper,
), records in sorted(
    records_by_source_identity.items()
):
    names = Counter(
        record["source_horse_name"]
        for record in records
        if record["source_horse_name"]
    )

    canonical_name = (
        sorted(
            names.items(),
            key=lambda value: (
                -value[1],
                value[0].upper(),
            ),
        )[0][0]
        if names
        else ""
    )

    canonical_horse_id = canonical_id(
        source_system,
        source_id_upper,
    )

    source_paths = sorted(
        {
            record["source_path"]
            for record in records
        }
    )

    master_payload = {
        "canonical_horse_id": canonical_horse_id,
        "canonical_name": canonical_name,
        "source_system": source_system,
        "source_horse_id": source_id_upper,
        "records": [
            {
                "source_path": record[
                    "source_path"
                ],
                "source_row_number": record[
                    "source_row_number"
                ],
                "evidence": record[
                    "source_row_evidence_sha256"
                ],
            }
            for record in records
        ],
    }

    master_rows.append(
        {
            "canonical_horse_id": canonical_horse_id,
            "canonical_horse_name": canonical_name,
            "normalised_horse_name": normalise_name(
                canonical_name
            ),
            "primary_source_system": source_system,
            "primary_source_horse_id": source_id_upper,
            "date_of_birth": first_non_blank(
                records,
                "date_of_birth",
            ),
            "sex": first_non_blank(
                records,
                "sex",
            ),
            "sire": first_non_blank(
                records,
                "sire",
            ),
            "dam": first_non_blank(
                records,
                "dam",
            ),
            "country": first_non_blank(
                records,
                "country",
            ),
            "horse_status": first_non_blank(
                records,
                "source_status",
            ),
            "source_record_count": str(
                len(records)
            ),
            "source_file_count": str(
                len(source_paths)
            ),
            "identity_resolution_status": (
                "CANONICAL_SOURCE_ID_AVAILABLE"
            ),
            "identity_resolution_method": (
                "SOURCE_SYSTEM_PLUS_SOURCE_HORSE_ID"
            ),
            "horse_master_builder_version": (
                BUILDER_VERSION
            ),
            "horse_master_method_version": (
                METHOD_VERSION
            ),
            "canonical_horse_evidence_sha256": (
                sha256_text(
                    canonical_json(master_payload)
                )
            ),
        }
    )

    for record in sorted(
        records,
        key=lambda value: (
            value["source_path"].lower(),
            int(value["source_row_number"]),
        ),
    ):
        alias_payload = {
            "canonical_horse_id": canonical_horse_id,
            "source_system": source_system,
            "source_horse_id": record[
                "source_horse_id"
            ],
            "source_name": record[
                "source_horse_name"
            ],
            "source_path": record["source_path"],
            "source_row_number": record[
                "source_row_number"
            ],
            "source_evidence": record[
                "source_row_evidence_sha256"
            ],
        }

        alias_rows.append(
            {
                "canonical_horse_id": canonical_horse_id,
                "source_system": source_system,
                "source_horse_id": record[
                    "source_horse_id"
                ],
                "source_horse_name": record[
                    "source_horse_name"
                ],
                "normalised_horse_name": record[
                    "normalised_horse_name"
                ],
                "source_path": record[
                    "source_path"
                ],
                "source_row_number": record[
                    "source_row_number"
                ],
                "source_row_evidence_sha256": record[
                    "source_row_evidence_sha256"
                ],
                "alias_builder_version": (
                    BUILDER_VERSION
                ),
                "alias_method_version": (
                    METHOD_VERSION
                ),
                "alias_evidence_sha256": sha256_text(
                    canonical_json(alias_payload)
                ),
            }
        )

master_rows.sort(
    key=lambda row: (
        row["canonical_horse_id"],
    )
)

alias_rows.sort(
    key=lambda row: (
        row["canonical_horse_id"],
        row["source_path"].lower(),
        int(row["source_row_number"]),
    )
)

write_csv(
    MASTER_CANDIDATE,
    master_fields,
    master_rows,
)

write_csv(
    ALIAS_CANDIDATE,
    alias_fields,
    alias_rows,
)

master_name_to_ids: dict[
    str,
    set[str],
] = defaultdict(set)

for row in master_rows:
    name = row["normalised_horse_name"]

    if name:
        master_name_to_ids[name].add(
            row["canonical_horse_id"]
        )

collision_fields = [
    "normalised_horse_name",
    "canonical_horse_id_count",
    "canonical_horse_ids",
    "collision_status",
]

collision_rows = []

for name, horse_ids in sorted(
    master_name_to_ids.items()
):
    if len(horse_ids) <= 1:
        continue

    collision_rows.append(
        {
            "normalised_horse_name": name,
            "canonical_horse_id_count": str(
                len(horse_ids)
            ),
            "canonical_horse_ids": "|".join(
                sorted(horse_ids)
            ),
            "collision_status": (
                "NAME_COLLISION_NOT_AUTO_MERGED"
            ),
        }
    )

write_csv(
    COLLISION_PATH,
    collision_fields,
    collision_rows,
)

coverage_fields = [
    "source_path",
    "source_row_count",
    "horse_identity_record_count",
    "unique_source_horse_id_count",
    "unique_normalised_horse_name_count",
    "source_system",
]

coverage_group: dict[
    str,
    list[dict[str, str]],
] = defaultdict(list)

for record in identity_records:
    coverage_group[
        record["source_path"]
    ].append(record)

inventory_by_path = {
    row["source_path"]: row
    for row in source_inventory
}

coverage_rows = []

for source_path, records in sorted(
    coverage_group.items()
):
    inventory = inventory_by_path.get(
        source_path,
        {},
    )

    coverage_rows.append(
        {
            "source_path": source_path,
            "source_row_count": str(
                inventory.get(
                    "row_count",
                    "",
                )
            ),
            "horse_identity_record_count": str(
                len(records)
            ),
            "unique_source_horse_id_count": str(
                len(
                    {
                        record[
                            "source_horse_id"
                        ].upper()
                        for record in records
                    }
                )
            ),
            "unique_normalised_horse_name_count": str(
                len(
                    {
                        record[
                            "normalised_horse_name"
                        ]
                        for record in records
                        if record[
                            "normalised_horse_name"
                        ]
                    }
                )
            ),
            "source_system": records[0][
                "source_system"
            ],
        }
    )

write_csv(
    SOURCE_COVERAGE_PATH,
    coverage_fields,
    coverage_rows,
)

current_source_path = (
    CURRENT_CONTEXT_PATH
    if CURRENT_CONTEXT_PATH.exists()
    else CURRENT_ENTRY_PATH
)

if not current_source_path.exists():
    raise FileNotFoundError(
        "No current race-entry source available."
    )

current_fields, current_rows = read_csv(
    current_source_path
)

current_id_column = find_column(
    current_fields,
    [
        "canonical_runner_id",
        "canonical_horse_id",
        "runner_id",
        "horse_id",
    ],
)

current_name_column = find_column(
    current_fields,
    [
        "canonical_horse_name",
        "runner_name",
        "horse_name",
    ],
)

if not current_name_column:
    raise RuntimeError(
        "Current race-entry source has no horse-name field."
    )

current_unique: dict[str, dict[str, str]] = {}

for row in current_rows:
    current_id = clean(
        row.get(current_id_column or "", "")
    )

    current_name = clean(
        row.get(current_name_column, "")
    )

    key = current_id or normalise_name(
        current_name
    )

    if key and key not in current_unique:
        current_unique[key] = {
            "current_runner_id": current_id,
            "current_horse_name": current_name,
            "normalised_horse_name": normalise_name(
                current_name
            ),
        }

master_source_id_lookup: dict[
    str,
    set[str],
] = defaultdict(set)

for row in master_rows:
    master_source_id_lookup[
        row["primary_source_horse_id"].upper()
    ].add(row["canonical_horse_id"])

current_coverage_fields = [
    "current_runner_id",
    "current_horse_name",
    "normalised_horse_name",
    "resolved_canonical_horse_id",
    "resolution_status",
    "resolution_method",
    "resolution_reason_code",
    "candidate_count",
]

current_coverage_rows = []
unresolved_rows = []
rebuild_population_rows = []

coverage_status_counts: Counter[str] = Counter()

for current in sorted(
    current_unique.values(),
    key=lambda value: (
        value["normalised_horse_name"],
        value["current_runner_id"],
    ),
):
    current_id = current[
        "current_runner_id"
    ].upper()

    current_name = current[
        "normalised_horse_name"
    ]

    resolved_id = ""
    method = ""
    reason = ""
    candidate_ids: set[str] = set()

    if current_id:
        candidate_ids = set(
            master_source_id_lookup.get(
                current_id,
                set(),
            )
        )

    if len(candidate_ids) == 1:
        resolved_id = next(
            iter(candidate_ids)
        )
        method = "EXACT_SOURCE_HORSE_ID"
        status = "CURRENT_RUNNER_RESOLVED"
        reason = "UNIQUE_SOURCE_ID_MATCH"

    elif len(candidate_ids) > 1:
        status = "CURRENT_RUNNER_UNRESOLVED"
        reason = "SOURCE_ID_COLLISION"

    else:
        candidate_ids = set(
            master_name_to_ids.get(
                current_name,
                set(),
            )
        )

        if len(candidate_ids) == 1:
            resolved_id = next(
                iter(candidate_ids)
            )
            method = (
                "EXACT_UNIQUE_NORMALISED_NAME"
            )
            status = "CURRENT_RUNNER_RESOLVED"
            reason = "UNIQUE_EXACT_NAME_MATCH"

        elif len(candidate_ids) > 1:
            status = "CURRENT_RUNNER_UNRESOLVED"
            reason = "NORMALISED_NAME_COLLISION"

        else:
            status = "CURRENT_RUNNER_UNRESOLVED"
            reason = "NO_EXACT_ID_OR_NAME_MATCH"

    coverage_status_counts[status] += 1

    coverage_row = {
        "current_runner_id": current[
            "current_runner_id"
        ],
        "current_horse_name": current[
            "current_horse_name"
        ],
        "normalised_horse_name": current_name,
        "resolved_canonical_horse_id": resolved_id,
        "resolution_status": status,
        "resolution_method": method,
        "resolution_reason_code": reason,
        "candidate_count": str(
            len(candidate_ids)
        ),
    }

    current_coverage_rows.append(
        coverage_row
    )

    if status == "CURRENT_RUNNER_UNRESOLVED":
        unresolved_rows.append(
            coverage_row
        )

    rebuild_population_rows.append(
        {
            **coverage_row,
            "historical_observation_rebuild_required": (
                "TRUE"
                if status
                == "CURRENT_RUNNER_UNRESOLVED"
                else "VERIFY_EXISTING_HISTORY"
            ),
            "rebuild_priority": (
                "P0_CURRENT_ACTIVE_POPULATION"
            ),
        }
    )

write_csv(
    CURRENT_COVERAGE_PATH,
    current_coverage_fields,
    current_coverage_rows,
)

write_csv(
    UNRESOLVED_PATH,
    current_coverage_fields,
    unresolved_rows,
)

rebuild_population_fields = (
    current_coverage_fields
    + [
        "historical_observation_rebuild_required",
        "rebuild_priority",
    ]
)

write_csv(
    REBUILD_POPULATION_PATH,
    rebuild_population_fields,
    rebuild_population_rows,
)

deterministic_master = (
    DOCS
    / "edgeiq_canonical_horse_master_v2_deterministic_check.csv"
)

deterministic_alias = (
    DOCS
    / "edgeiq_canonical_horse_alias_v2_deterministic_check.csv"
)

write_csv(
    deterministic_master,
    master_fields,
    master_rows,
)

write_csv(
    deterministic_alias,
    alias_fields,
    alias_rows,
)

checks = {
    "repository_csv_sources_discovered": (
        len(csv_files) > 0
    ),
    "eligible_identity_sources_available": (
        len(coverage_rows) > 0
    ),
    "master_population_nonzero": (
        len(master_rows) > 0
    ),
    "canonical_horse_ids_unique": (
        len(
            {
                row["canonical_horse_id"]
                for row in master_rows
            }
        )
        == len(master_rows)
    ),
    "master_rows_have_name": all(
        row["canonical_horse_name"]
        for row in master_rows
    ),
    "master_rows_have_evidence": all(
        row[
            "canonical_horse_evidence_sha256"
        ]
        for row in master_rows
    ),
    "alias_rows_have_evidence": all(
        row["alias_evidence_sha256"]
        for row in alias_rows
    ),
    "name_collisions_not_auto_merged": all(
        row["collision_status"]
        == "NAME_COLLISION_NOT_AUTO_MERGED"
        for row in collision_rows
    ),
    "one_current_coverage_row_per_runner": (
        len(current_coverage_rows)
        == len(current_unique)
    ),
    "current_resolution_unique_only": all(
        (
            row["resolution_status"]
            != "CURRENT_RUNNER_RESOLVED"
        )
        or int(row["candidate_count"]) == 1
        for row in current_coverage_rows
    ),
    "rebuild_population_complete": (
        len(rebuild_population_rows)
        == len(current_unique)
    ),
    "master_deterministic": (
        sha256_file(MASTER_CANDIDATE)
        == sha256_file(deterministic_master)
    ),
    "alias_deterministic": (
        sha256_file(ALIAS_CANDIDATE)
        == sha256_file(deterministic_alias)
    ),
}

deterministic_master.unlink(
    missing_ok=True
)

deterministic_alias.unlink(
    missing_ok=True
)

audit_pass = all(checks.values())

if not audit_pass:
    raise RuntimeError(
        json.dumps(
            {
                "status": (
                    "EDGEIQ_CANONICAL_HORSE_MASTER_V2_AUDIT_FAIL"
                ),
                "checks": checks,
            },
            indent=2,
        )
    )

master_production_hash = promote(
    MASTER_CANDIDATE,
    MASTER_PRODUCTION,
)

alias_production_hash = promote(
    ALIAS_CANDIDATE,
    ALIAS_PRODUCTION,
)

audit = {
    "status": (
        "EDGEIQ_CANONICAL_HORSE_MASTER_V2_AUDIT_PASS"
    ),
    "builder_version": BUILDER_VERSION,
    "method_version": METHOD_VERSION,
    "repository_csv_files_discovered": len(
        csv_files
    ),
    "eligible_identity_sources": len(
        coverage_rows
    ),
    "identity_source_records": len(
        identity_records
    ),
    "canonical_horse_rows": len(
        master_rows
    ),
    "alias_rows": len(alias_rows),
    "normalised_name_collisions": len(
        collision_rows
    ),
    "current_unique_runners": len(
        current_unique
    ),
    "current_runner_coverage_status_counts": dict(
        sorted(
            coverage_status_counts.items()
        )
    ),
    "current_resolved_count": sum(
        1
        for row in current_coverage_rows
        if row["resolution_status"]
        == "CURRENT_RUNNER_RESOLVED"
    ),
    "current_unresolved_count": len(
        unresolved_rows
    ),
    "checks": checks,
    "master_candidate_sha256": sha256_file(
        MASTER_CANDIDATE
    ),
    "master_production_sha256": (
        master_production_hash
    ),
    "alias_candidate_sha256": sha256_file(
        ALIAS_CANDIDATE
    ),
    "alias_production_sha256": (
        alias_production_hash
    ),
}

AUDIT_JSON.write_text(
    json.dumps(audit, indent=2),
    encoding="utf-8",
)

contract = {
    "contract_name": (
        "edgeiq_canonical_horse_master_v2"
    ),
    "contract_version": "V2",
    "grain": (
        "ONE ROW PER SOURCE-SYSTEM HORSE IDENTITY"
    ),
    "canonical_key": (
        "SOURCE SYSTEM PLUS SOURCE HORSE ID"
    ),
    "identity_rules": [
        "Preserve source horse identifiers.",
        "Do not merge different source identifiers solely by name.",
        "Exact unique normalised names may resolve current runners.",
        "Name collisions remain unresolved.",
        "No fuzzy or approximate matching.",
    ],
    "builder_version": BUILDER_VERSION,
    "method_version": METHOD_VERSION,
    "master_fields": master_fields,
    "alias_fields": alias_fields,
}

CONTRACT_JSON.write_text(
    json.dumps(contract, indent=2),
    encoding="utf-8",
)

audit_lines = [
    "# EDGEIQ Canonical Horse Master V2 Audit",
    "",
    f"Status: `{audit['status']}`",
    "",
    "## Population",
    "",
    (
        "- Repository CSV files discovered: "
        f"`{audit['repository_csv_files_discovered']}`"
    ),
    (
        "- Eligible identity sources: "
        f"`{audit['eligible_identity_sources']}`"
    ),
    (
        "- Identity source records: "
        f"`{audit['identity_source_records']}`"
    ),
    (
        "- Canonical horse rows: "
        f"`{audit['canonical_horse_rows']}`"
    ),
    f"- Alias rows: `{audit['alias_rows']}`",
    (
        "- Normalised-name collisions: "
        f"`{audit['normalised_name_collisions']}`"
    ),
    "",
    "## Current Runner Coverage",
    "",
    (
        "- Current unique runners: "
        f"`{audit['current_unique_runners']}`"
    ),
    (
        "- Current runners resolved: "
        f"`{audit['current_resolved_count']}`"
    ),
    (
        "- Current runners unresolved: "
        f"`{audit['current_unresolved_count']}`"
    ),
    "",
]

for key, value in audit[
    "current_runner_coverage_status_counts"
].items():
    audit_lines.append(
        f"- `{key}`: `{value}`"
    )

audit_lines.extend(
    [
        "",
        "## Audit Checks",
        "",
    ]
)

for key, value in checks.items():
    audit_lines.append(
        f"- `{key}`: `{'PASS' if value else 'FAIL'}`"
    )

audit_lines.extend(
    [
        "",
        "## Governance",
        "",
        "- Source horse identifiers are preserved.",
        "- Different source IDs are not merged merely because names match.",
        "- Exact-name resolution is permitted only where the name maps to one canonical identity.",
        "- Name collisions remain explicitly unresolved.",
        "- No fuzzy matching is used.",
        "- No horse identity is fabricated.",
        "",
        (
            "- Master SHA256: "
            f"`{master_production_hash}`"
        ),
        (
            "- Alias SHA256: "
            f"`{alias_production_hash}`"
        ),
        "",
    ]
)

AUDIT_MD.write_text(
    "\n".join(audit_lines),
    encoding="utf-8",
)

print(
    json.dumps(
        {
            "status": audit["status"],
            "repository_csv_files_discovered": audit[
                "repository_csv_files_discovered"
            ],
            "eligible_identity_sources": audit[
                "eligible_identity_sources"
            ],
            "identity_source_records": audit[
                "identity_source_records"
            ],
            "canonical_horse_rows": audit[
                "canonical_horse_rows"
            ],
            "alias_rows": audit["alias_rows"],
            "normalised_name_collisions": audit[
                "normalised_name_collisions"
            ],
            "current_unique_runners": audit[
                "current_unique_runners"
            ],
            "current_resolved_count": audit[
                "current_resolved_count"
            ],
            "current_unresolved_count": audit[
                "current_unresolved_count"
            ],
            "master_production_path": str(
                MASTER_PRODUCTION
            ),
            "alias_production_path": str(
                ALIAS_PRODUCTION
            ),
            "audit_report": str(AUDIT_MD),
        },
        indent=2,
    )
)
