from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import shutil
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"

DOCS = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse-v2"
    / "historical-run-observation"
)

DOCS.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

MANIFEST_PATH = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse-v2"
    / "historical-observation-source-inventory"
    / "edgeiq_historical_observation_extraction_manifest_v2.csv"
)

HORSE_MASTER_PATH = (
    DATA / "edgeiq_canonical_horse_master_v2.csv"
)

HORSE_ALIAS_PATH = (
    DATA / "edgeiq_canonical_horse_alias_v2.csv"
)

CURRENT_COVERAGE_PATH = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse-v2"
    / "canonical-horse-master"
    / "edgeiq_current_runner_horse_master_coverage_v2.csv"
)

OBSERVATION_CANDIDATE = (
    DATA
    / "edgeiq_historical_run_observation_fact_v2_CANDIDATE.csv"
)

OBSERVATION_PRODUCTION = (
    DATA
    / "edgeiq_historical_run_observation_fact_v2.csv"
)

REJECTION_PATH = (
    DOCS
    / "edgeiq_historical_run_observation_v2_rejections.csv"
)

SOURCE_CONTRIBUTION_PATH = (
    DOCS
    / "edgeiq_historical_run_observation_v2_source_contribution.csv"
)

IDENTITY_FAILURE_PATH = (
    DOCS
    / "edgeiq_historical_run_observation_v2_identity_failures.csv"
)

DUPLICATE_PATH = (
    DOCS
    / "edgeiq_historical_run_observation_v2_duplicates.csv"
)

AUDIT_JSON = (
    DOCS
    / "EDGEIQ_HISTORICAL_RUN_OBSERVATION_V2_AUDIT.json"
)

AUDIT_MD = (
    DOCS
    / "EDGEIQ_HISTORICAL_RUN_OBSERVATION_V2_AUDIT.md"
)

CONTRACT_JSON = (
    DOCS
    / "edgeiq_historical_run_observation_v2_contract.json"
)

METHOD_MD = (
    DOCS
    / "EDGEIQ_HISTORICAL_RUN_OBSERVATION_V2_METHOD.md"
)

BUILDER_VERSION = "EDGEIQ_HISTORICAL_RUN_OBSERVATION_V2"
METHOD_VERSION = "FACTUAL_MULTI_SOURCE_EXTRACTION_AND_DEDUPLICATION_V1"

RCOM_ID_PATTERN = re.compile(
    r"^(?:RCOM_HORSE_|RACINGCOM_HORSE_|HORSE\|RACINGCOM\||HORSE_)?(\d+)$",
    re.IGNORECASE,
)

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

RACE_NUMBER_ALIASES = [
    "race_number",
    "race_no",
    "race",
]

TRACK_ALIASES = [
    "canonical_track",
    "track",
    "track_name",
    "venue",
    "meeting",
]

DISTANCE_ALIASES = [
    "race_distance_metres",
    "distance_metres",
    "distance",
]

HORSE_ID_ALIASES = [
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

HORSE_NAME_ALIASES = [
    "canonical_horse_name",
    "horse_name",
    "runner_name",
    "competitor_name",
]

TRACK_CONDITION_ALIASES = [
    "track_condition",
    "track_condition_number",
    "condition",
    "going",
]

SURFACE_ALIASES = [
    "surface",
    "surface_group",
]

CLASS_ALIASES = [
    "race_class",
    "class",
    "class_name",
]

BARRIER_ALIASES = [
    "barrier",
    "barrier_number",
    "draw",
]

WEIGHT_ALIASES = [
    "weight_kg",
    "carried_weight_kg",
    "weight",
]

JOCKEY_ALIASES = [
    "jockey_name",
    "jockey",
]

TRAINER_ALIASES = [
    "trainer_name",
    "trainer",
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
    "beaten_margin_lengths",
    "margin_lengths",
    "beaten_margin",
    "margin",
]

SP_ALIASES = [
    "starting_price",
    "sp",
    "official_sp",
]

RACE_TIME_ALIASES = [
    "official_race_time_seconds",
    "race_time_seconds",
    "official_time",
    "race_time",
]

POSITION_IN_RUNNING_ALIASES = [
    "position_in_running",
    "in_running_position",
    "running_position",
]

SECTIONAL_ALIASES = {
    "sectional_800_to_600_lengths_v_standard": [
        "sectional_800_to_600_lengths_v_standard",
        "800_600_lengths_v_standard",
    ],
    "sectional_600_to_400_lengths_v_standard": [
        "sectional_600_to_400_lengths_v_standard",
        "600_400_lengths_v_standard",
    ],
    "sectional_400_to_200_lengths_v_standard": [
        "sectional_400_to_200_lengths_v_standard",
        "400_200_lengths_v_standard",
    ],
    "sectional_200_to_finish_lengths_v_standard": [
        "sectional_200_to_finish_lengths_v_standard",
        "200_finish_lengths_v_standard",
    ],
}


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalise_name(value: str) -> str:
    value = clean(value).upper().replace("’", "'")
    return re.sub(r"\s+", " ", value).strip()


def normalise_track(value: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        clean(value).upper(),
    ).strip()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def safe_relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def resolve_path(value: str) -> Path:
    path = Path(value)

    if path.is_absolute():
        return path

    return ROOT / path


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


def promote(
    candidate: Path,
    production: Path,
) -> str:
    temporary = production.with_suffix(
        production.suffix + ".tmp"
    )

    shutil.copy2(candidate, temporary)
    os.replace(temporary, production)

    candidate_hash = sha256_file(candidate)
    production_hash = sha256_file(production)

    if candidate_hash != production_hash:
        raise RuntimeError(
            "Candidate and production hashes differ."
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


def parse_date(value: str) -> str:
    value = clean(value)

    if not value:
        return ""

    value = value.replace("Z", "")

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(
                value,
                fmt,
            ).date().isoformat()
        except ValueError:
            pass

    try:
        return datetime.fromisoformat(
            value
        ).date().isoformat()
    except ValueError:
        return ""


def parse_integer(value: str) -> str:
    value = clean(value)

    if not value:
        return ""

    match = re.search(r"-?\d+", value)

    if not match:
        return ""

    return str(int(match.group(0)))


def parse_float(value: str) -> str:
    value = clean(value)

    if not value:
        return ""

    value = value.replace(",", "")

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        value,
    )

    if not match:
        return ""

    parsed = float(match.group(0))

    if not math.isfinite(parsed):
        return ""

    return f"{parsed:.12f}".rstrip("0").rstrip(".")


def racingcom_numeric_id(value: str) -> str:
    value = clean(value)

    match = RCOM_ID_PATTERN.match(value)

    if not match:
        return ""

    return match.group(1)


def source_system_from_path(path: Path) -> str:
    text = str(path).lower()

    if (
        "racingcom" in text
        or "racing_com" in text
        or "graphql" in text
    ):
        return "RACINGCOM"

    return "EDGEIQ"


manifest_fields, manifest_rows = read_csv(
    MANIFEST_PATH
)

master_fields, master_rows = read_csv(
    HORSE_MASTER_PATH
)

alias_fields, alias_rows = read_csv(
    HORSE_ALIAS_PATH
)

coverage_fields, coverage_rows = read_csv(
    CURRENT_COVERAGE_PATH
)

master_ids = {
    row["canonical_horse_id"]
    for row in master_rows
}

master_name_by_id = {
    row["canonical_horse_id"]: row["canonical_horse_name"]
    for row in master_rows
}

alias_by_source_id: dict[
    tuple[str, str],
    set[str],
] = defaultdict(set)

alias_by_name: dict[
    str,
    set[str],
] = defaultdict(set)

for alias in alias_rows:
    source_system = clean(
        alias["source_system"]
    ).upper()

    source_id = clean(
        alias["source_horse_id"]
    ).upper()

    canonical_id = alias[
        "canonical_horse_id"
    ]

    if source_system and source_id:
        alias_by_source_id[
            (source_system, source_id)
        ].add(canonical_id)

    normalised = normalise_name(
        alias["source_horse_name"]
    )

    if normalised:
        alias_by_name[normalised].add(
            canonical_id
        )

for coverage in coverage_rows:
    runner_id = coverage[
        "current_runner_id"
    ]

    numeric_id = racingcom_numeric_id(
        runner_id
    )

    canonical_id = coverage[
        "resolved_canonical_horse_id"
    ]

    if numeric_id and canonical_id:
        alias_by_source_id[
            ("RACINGCOM", numeric_id)
        ].add(canonical_id)

observation_fields = [
    "historical_run_observation_id",
    "canonical_horse_id",
    "canonical_horse_name",
    "source_horse_id",
    "source_horse_name",
    "horse_identity_resolution_status",
    "horse_identity_resolution_method",
    "canonical_race_id",
    "race_date",
    "canonical_track",
    "race_number",
    "race_distance_metres",
    "race_class",
    "surface_group",
    "track_condition",
    "barrier",
    "weight_kg",
    "jockey_name",
    "trainer_name",
    "finish_position",
    "field_size",
    "beaten_margin_lengths",
    "starting_price",
    "official_race_time_seconds",
    "position_in_running",
    "sectional_800_to_600_lengths_v_standard",
    "sectional_600_to_400_lengths_v_standard",
    "sectional_400_to_200_lengths_v_standard",
    "sectional_200_to_finish_lengths_v_standard",
    "source_system",
    "source_path",
    "source_file_sha256",
    "source_row_number",
    "source_row_evidence_sha256",
    "historical_run_builder_version",
    "historical_run_method_version",
    "historical_run_observation_evidence_sha256",
]

rejection_fields = [
    "source_path",
    "source_row_number",
    "source_horse_id",
    "source_horse_name",
    "race_date",
    "canonical_track",
    "rejection_reason_code",
    "source_row_evidence_sha256",
]

duplicate_fields = [
    "observation_natural_key",
    "retained_observation_id",
    "duplicate_observation_id",
    "retained_source_path",
    "duplicate_source_path",
    "duplicate_reason_code",
]

contribution_fields = [
    "source_path",
    "source_status",
    "source_rows_read",
    "observation_rows_accepted_before_deduplication",
    "observation_rows_retained",
    "observation_rows_rejected",
    "observation_rows_deduplicated",
]

all_candidates: list[dict[str, str]] = []
rejections: list[dict[str, str]] = []
source_counts: dict[str, Counter[str]] = defaultdict(Counter)

for source_index, manifest in enumerate(
    manifest_rows,
    start=1,
):
    source_path = resolve_path(
        manifest["source_path"]
    )

    source_key = safe_relative(
        source_path
    )

    if not source_path.exists():
        source_counts[source_key][
            "rejected"
        ] += 1

        rejections.append(
            {
                "source_path": source_key,
                "source_row_number": "",
                "source_horse_id": "",
                "source_horse_name": "",
                "race_date": "",
                "canonical_track": "",
                "rejection_reason_code": (
                    "SOURCE_FILE_MISSING"
                ),
                "source_row_evidence_sha256": "",
            }
        )
        continue

    try:
        fields, rows = read_csv(
            source_path
        )
    except Exception:
        source_counts[source_key][
            "rejected"
        ] += 1
        continue

    source_counts[source_key][
        "read"
    ] += len(rows)

    source_system = source_system_from_path(
        source_path
    )

    source_file_hash = sha256_file(
        source_path
    )

    horse_id_col = find_column(
        fields,
        HORSE_ID_ALIASES,
    )

    horse_name_col = find_column(
        fields,
        HORSE_NAME_ALIASES,
    )

    race_date_col = find_column(
        fields,
        DATE_ALIASES,
    )

    race_id_col = find_column(
        fields,
        RACE_ID_ALIASES,
    )

    race_number_col = find_column(
        fields,
        RACE_NUMBER_ALIASES,
    )

    track_col = find_column(
        fields,
        TRACK_ALIASES,
    )

    distance_col = find_column(
        fields,
        DISTANCE_ALIASES,
    )

    class_col = find_column(
        fields,
        CLASS_ALIASES,
    )

    surface_col = find_column(
        fields,
        SURFACE_ALIASES,
    )

    condition_col = find_column(
        fields,
        TRACK_CONDITION_ALIASES,
    )

    barrier_col = find_column(
        fields,
        BARRIER_ALIASES,
    )

    weight_col = find_column(
        fields,
        WEIGHT_ALIASES,
    )

    jockey_col = find_column(
        fields,
        JOCKEY_ALIASES,
    )

    trainer_col = find_column(
        fields,
        TRAINER_ALIASES,
    )

    finish_col = find_column(
        fields,
        FINISH_ALIASES,
    )

    field_size_col = find_column(
        fields,
        FIELD_SIZE_ALIASES,
    )

    margin_col = find_column(
        fields,
        MARGIN_ALIASES,
    )

    sp_col = find_column(
        fields,
        SP_ALIASES,
    )

    time_col = find_column(
        fields,
        RACE_TIME_ALIASES,
    )

    position_col = find_column(
        fields,
        POSITION_IN_RUNNING_ALIASES,
    )

    sectional_columns = {
        output_field: find_column(
            fields,
            aliases,
        )
        for output_field, aliases
        in SECTIONAL_ALIASES.items()
    }

    for row_number, source_row in enumerate(
        rows,
        start=2,
    ):
        source_horse_id = clean(
            source_row.get(
                horse_id_col or "",
                "",
            )
        )

        source_horse_name = clean(
            source_row.get(
                horse_name_col or "",
                "",
            )
        )

        race_date = parse_date(
            source_row.get(
                race_date_col or "",
                "",
            )
        )

        track = normalise_track(
            source_row.get(
                track_col or "",
                "",
            )
        )

        source_row_hash = sha256_text(
            canonical_json(source_row)
        )

        canonical_horse_id = ""
        resolution_method = ""
        resolution_status = ""

        numeric_id = racingcom_numeric_id(
            source_horse_id
        )

        source_id_candidates: set[str] = set()

        if source_horse_id:
            source_id_candidates |= (
                alias_by_source_id.get(
                    (
                        source_system,
                        source_horse_id.upper(),
                    ),
                    set(),
                )
            )

        if numeric_id:
            source_id_candidates |= (
                alias_by_source_id.get(
                    (
                        "RACINGCOM",
                        numeric_id,
                    ),
                    set(),
                )
            )

            direct_racingcom_id = (
                f"HORSE|RACINGCOM|{numeric_id}"
            )

            if direct_racingcom_id in master_ids:
                source_id_candidates.add(
                    direct_racingcom_id
                )

        if len(source_id_candidates) == 1:
            canonical_horse_id = next(
                iter(source_id_candidates)
            )
            resolution_method = (
                "EXACT_SOURCE_ID"
            )
            resolution_status = (
                "IDENTITY_RESOLVED"
            )

        elif len(source_id_candidates) > 1:
            resolution_status = (
                "IDENTITY_UNRESOLVED"
            )

        elif source_horse_name:
            name_candidates = (
                alias_by_name.get(
                    normalise_name(
                        source_horse_name
                    ),
                    set(),
                )
            )

            if len(name_candidates) == 1:
                canonical_horse_id = next(
                    iter(name_candidates)
                )
                resolution_method = (
                    "EXACT_UNIQUE_NORMALISED_NAME"
                )
                resolution_status = (
                    "IDENTITY_RESOLVED"
                )

            else:
                resolution_status = (
                    "IDENTITY_UNRESOLVED"
                )

        else:
            resolution_status = (
                "IDENTITY_UNRESOLVED"
            )

        rejection_reason = ""

        if not canonical_horse_id:
            rejection_reason = (
                "HORSE_IDENTITY_UNRESOLVED"
            )

        elif not race_date:
            rejection_reason = (
                "VALID_RACE_DATE_UNAVAILABLE"
            )

        elif not track and not clean(
            source_row.get(
                race_id_col or "",
                "",
            )
        ):
            rejection_reason = (
                "RACE_IDENTITY_UNAVAILABLE"
            )

        if rejection_reason:
            source_counts[source_key][
                "rejected"
            ] += 1

            rejections.append(
                {
                    "source_path": source_key,
                    "source_row_number": str(
                        row_number
                    ),
                    "source_horse_id": (
                        source_horse_id
                    ),
                    "source_horse_name": (
                        source_horse_name
                    ),
                    "race_date": race_date,
                    "canonical_track": track,
                    "rejection_reason_code": (
                        rejection_reason
                    ),
                    "source_row_evidence_sha256": (
                        source_row_hash
                    ),
                }
            )
            continue

        race_number = parse_integer(
            source_row.get(
                race_number_col or "",
                "",
            )
        )

        distance = parse_integer(
            source_row.get(
                distance_col or "",
                "",
            )
        )

        source_race_id = clean(
            source_row.get(
                race_id_col or "",
                "",
            )
        )

        if source_race_id:
            canonical_race_id = (
                source_race_id
            )
        else:
            canonical_race_id = (
                "RACE|"
                + race_date
                + "|"
                + track
                + "|R"
                + (race_number or "UNKNOWN")
                + "|"
                + (
                    distance + "M"
                    if distance
                    else "DISTANCE_UNKNOWN"
                )
            )

        canonical_name = master_name_by_id.get(
            canonical_horse_id,
            source_horse_name,
        )

        factual = {
            "canonical_horse_id": canonical_horse_id,
            "canonical_race_id": canonical_race_id,
            "race_date": race_date,
            "track": track,
            "race_number": race_number,
            "distance": distance,
            "finish": parse_integer(
                source_row.get(
                    finish_col or "",
                    "",
                )
            ),
            "field_size": parse_integer(
                source_row.get(
                    field_size_col or "",
                    "",
                )
            ),
            "margin": parse_float(
                source_row.get(
                    margin_col or "",
                    "",
                )
            ),
        }

        observation_id = sha256_text(
            canonical_json(
                {
                    **factual,
                    "source_path": source_key,
                    "source_row_number": (
                        row_number
                    ),
                    "source_row_hash": (
                        source_row_hash
                    ),
                }
            )
        )

        evidence_payload = {
            "observation_id": observation_id,
            "factual": factual,
            "source_file_sha256": source_file_hash,
            "source_row_evidence_sha256": (
                source_row_hash
            ),
            "method": METHOD_VERSION,
        }

        output_row = {
            "historical_run_observation_id": (
                observation_id
            ),
            "canonical_horse_id": (
                canonical_horse_id
            ),
            "canonical_horse_name": (
                canonical_name
            ),
            "source_horse_id": (
                source_horse_id
            ),
            "source_horse_name": (
                source_horse_name
            ),
            "horse_identity_resolution_status": (
                resolution_status
            ),
            "horse_identity_resolution_method": (
                resolution_method
            ),
            "canonical_race_id": (
                canonical_race_id
            ),
            "race_date": race_date,
            "canonical_track": track,
            "race_number": race_number,
            "race_distance_metres": distance,
            "race_class": clean(
                source_row.get(
                    class_col or "",
                    "",
                )
            ),
            "surface_group": clean(
                source_row.get(
                    surface_col or "",
                    "",
                )
            ),
            "track_condition": clean(
                source_row.get(
                    condition_col or "",
                    "",
                )
            ),
            "barrier": parse_integer(
                source_row.get(
                    barrier_col or "",
                    "",
                )
            ),
            "weight_kg": parse_float(
                source_row.get(
                    weight_col or "",
                    "",
                )
            ),
            "jockey_name": clean(
                source_row.get(
                    jockey_col or "",
                    "",
                )
            ),
            "trainer_name": clean(
                source_row.get(
                    trainer_col or "",
                    "",
                )
            ),
            "finish_position": factual[
                "finish"
            ],
            "field_size": factual[
                "field_size"
            ],
            "beaten_margin_lengths": factual[
                "margin"
            ],
            "starting_price": clean(
                source_row.get(
                    sp_col or "",
                    "",
                )
            ),
            "official_race_time_seconds": parse_float(
                source_row.get(
                    time_col or "",
                    "",
                )
            ),
            "position_in_running": clean(
                source_row.get(
                    position_col or "",
                    "",
                )
            ),
            "sectional_800_to_600_lengths_v_standard": (
                parse_float(
                    source_row.get(
                        sectional_columns[
                            "sectional_800_to_600_lengths_v_standard"
                        ]
                        or "",
                        "",
                    )
                )
            ),
            "sectional_600_to_400_lengths_v_standard": (
                parse_float(
                    source_row.get(
                        sectional_columns[
                            "sectional_600_to_400_lengths_v_standard"
                        ]
                        or "",
                        "",
                    )
                )
            ),
            "sectional_400_to_200_lengths_v_standard": (
                parse_float(
                    source_row.get(
                        sectional_columns[
                            "sectional_400_to_200_lengths_v_standard"
                        ]
                        or "",
                        "",
                    )
                )
            ),
            "sectional_200_to_finish_lengths_v_standard": (
                parse_float(
                    source_row.get(
                        sectional_columns[
                            "sectional_200_to_finish_lengths_v_standard"
                        ]
                        or "",
                        "",
                    )
                )
            ),
            "source_system": source_system,
            "source_path": source_key,
            "source_file_sha256": source_file_hash,
            "source_row_number": str(
                row_number
            ),
            "source_row_evidence_sha256": (
                source_row_hash
            ),
            "historical_run_builder_version": (
                BUILDER_VERSION
            ),
            "historical_run_method_version": (
                METHOD_VERSION
            ),
            "historical_run_observation_evidence_sha256": (
                sha256_text(
                    canonical_json(
                        evidence_payload
                    )
                )
            ),
        }

        all_candidates.append(output_row)
        source_counts[source_key][
            "accepted"
        ] += 1

    if source_index % 25 == 0:
        print(
            "Historical extraction progress: "
            f"{source_index}/{len(manifest_rows)} "
            f"sources; {len(all_candidates):,} "
            "candidate observations"
        )

# ============================================================
# DEDUPLICATION
# ============================================================

def completeness_score(
    row: dict[str, str],
) -> int:
    factual_fields = [
        "race_number",
        "race_distance_metres",
        "race_class",
        "surface_group",
        "track_condition",
        "barrier",
        "weight_kg",
        "jockey_name",
        "trainer_name",
        "finish_position",
        "field_size",
        "beaten_margin_lengths",
        "starting_price",
        "official_race_time_seconds",
        "position_in_running",
        "sectional_800_to_600_lengths_v_standard",
        "sectional_600_to_400_lengths_v_standard",
        "sectional_400_to_200_lengths_v_standard",
        "sectional_200_to_finish_lengths_v_standard",
    ]

    return sum(
        1
        for field in factual_fields
        if row[field]
    )


def natural_key(
    row: dict[str, str],
) -> tuple[str, ...]:
    return (
        row["canonical_horse_id"],
        row["canonical_race_id"],
        row["race_date"],
    )


candidates_by_key: dict[
    tuple[str, ...],
    list[dict[str, str]],
] = defaultdict(list)

for row in all_candidates:
    candidates_by_key[
        natural_key(row)
    ].append(row)

retained_rows: list[dict[str, str]] = []
duplicate_rows: list[dict[str, str]] = []

for key, rows in candidates_by_key.items():
    ranked = sorted(
        rows,
        key=lambda row: (
            -completeness_score(row),
            row["source_path"].lower(),
            int(row["source_row_number"]),
            row["historical_run_observation_id"],
        ),
    )

    retained = ranked[0]
    retained_rows.append(retained)

    source_counts[
        retained["source_path"]
    ]["retained"] += 1

    for duplicate in ranked[1:]:
        source_counts[
            duplicate["source_path"]
        ]["deduplicated"] += 1

        duplicate_rows.append(
            {
                "observation_natural_key": (
                    "|".join(key)
                ),
                "retained_observation_id": retained[
                    "historical_run_observation_id"
                ],
                "duplicate_observation_id": duplicate[
                    "historical_run_observation_id"
                ],
                "retained_source_path": retained[
                    "source_path"
                ],
                "duplicate_source_path": duplicate[
                    "source_path"
                ],
                "duplicate_reason_code": (
                    "DUPLICATE_HORSE_RACE_OBSERVATION"
                ),
            }
        )

retained_rows.sort(
    key=lambda row: (
        row["race_date"],
        row["canonical_race_id"],
        row["canonical_horse_id"],
    )
)

rejections.sort(
    key=lambda row: (
        row["rejection_reason_code"],
        row["source_path"],
        row["source_row_number"],
    )
)

duplicate_rows.sort(
    key=lambda row: (
        row["observation_natural_key"],
        row["duplicate_source_path"],
    )
)

write_csv(
    OBSERVATION_CANDIDATE,
    observation_fields,
    retained_rows,
)

write_csv(
    REJECTION_PATH,
    rejection_fields,
    rejections,
)

write_csv(
    IDENTITY_FAILURE_PATH,
    rejection_fields,
    [
        row
        for row in rejections
        if row["rejection_reason_code"]
        == "HORSE_IDENTITY_UNRESOLVED"
    ],
)

write_csv(
    DUPLICATE_PATH,
    duplicate_fields,
    duplicate_rows,
)

contribution_rows = []

for source_path in sorted(
    source_counts
):
    counts = source_counts[source_path]

    contribution_rows.append(
        {
            "source_path": source_path,
            "source_status": (
                "CONTRIBUTED"
                if counts["retained"] > 0
                else "NO_RETAINED_OBSERVATIONS"
            ),
            "source_rows_read": str(
                counts["read"]
            ),
            "observation_rows_accepted_before_deduplication": str(
                counts["accepted"]
            ),
            "observation_rows_retained": str(
                counts["retained"]
            ),
            "observation_rows_rejected": str(
                counts["rejected"]
            ),
            "observation_rows_deduplicated": str(
                counts["deduplicated"]
            ),
        }
    )

write_csv(
    SOURCE_CONTRIBUTION_PATH,
    contribution_fields,
    contribution_rows,
)

deterministic_path = (
    DOCS
    / "historical_run_observation_deterministic_check.csv"
)

write_csv(
    deterministic_path,
    observation_fields,
    retained_rows,
)

natural_keys = [
    natural_key(row)
    for row in retained_rows
]

status_counts = Counter(
    row[
        "horse_identity_resolution_method"
    ]
    for row in retained_rows
)

checks = {
    "source_manifest_nonzero": (
        len(manifest_rows) > 0
    ),
    "candidate_observation_population_nonzero": (
        len(all_candidates) > 0
    ),
    "production_observation_population_nonzero": (
        len(retained_rows) > 0
    ),
    "natural_keys_unique": (
        len(natural_keys)
        == len(set(natural_keys))
    ),
    "observation_ids_unique": (
        len(
            {
                row[
                    "historical_run_observation_id"
                ]
                for row in retained_rows
            }
        )
        == len(retained_rows)
    ),
    "all_rows_have_canonical_horse_id": all(
        row["canonical_horse_id"]
        for row in retained_rows
    ),
    "all_rows_have_race_date": all(
        row["race_date"]
        for row in retained_rows
    ),
    "all_rows_have_race_identity": all(
        row["canonical_race_id"]
        for row in retained_rows
    ),
    "all_horse_ids_exist_in_master": all(
        row["canonical_horse_id"]
        in master_ids
        for row in retained_rows
    ),
    "all_rows_have_source_evidence": all(
        row["source_file_sha256"]
        and row["source_row_evidence_sha256"]
        and row[
            "historical_run_observation_evidence_sha256"
        ]
        for row in retained_rows
    ),
    "no_calculated_performance_values": (
        "performance_value"
        not in observation_fields
        and "epi_value"
        not in observation_fields
    ),
    "deterministic_rerun": (
        sha256_file(
            OBSERVATION_CANDIDATE
        )
        == sha256_file(
            deterministic_path
        )
    ),
}

deterministic_path.unlink(
    missing_ok=True
)

if not all(checks.values()):
    raise RuntimeError(
        "Historical Run Observation V2 audit failed:\n"
        + json.dumps(
            checks,
            indent=2,
        )
    )

production_hash = promote(
    OBSERVATION_CANDIDATE,
    OBSERVATION_PRODUCTION,
)

audit = {
    "status": (
        "EDGEIQ_HISTORICAL_RUN_OBSERVATION_V2_AUDIT_PASS"
    ),
    "manifest_source_files": len(
        manifest_rows
    ),
    "candidate_observations_before_deduplication": len(
        all_candidates
    ),
    "production_observations": len(
        retained_rows
    ),
    "duplicate_observations_removed": len(
        duplicate_rows
    ),
    "rejected_source_rows": len(
        rejections
    ),
    "identity_failure_rows": sum(
        1
        for row in rejections
        if row["rejection_reason_code"]
        == "HORSE_IDENTITY_UNRESOLVED"
    ),
    "unique_horses": len(
        {
            row["canonical_horse_id"]
            for row in retained_rows
        }
    ),
    "unique_races": len(
        {
            row["canonical_race_id"]
            for row in retained_rows
        }
    ),
    "earliest_race_date": (
        retained_rows[0]["race_date"]
        if retained_rows
        else ""
    ),
    "latest_race_date": (
        retained_rows[-1]["race_date"]
        if retained_rows
        else ""
    ),
    "identity_resolution_method_counts": dict(
        sorted(status_counts.items())
    ),
    "checks": checks,
    "candidate_sha256": sha256_file(
        OBSERVATION_CANDIDATE
    ),
    "production_sha256": production_hash,
}

AUDIT_JSON.write_text(
    json.dumps(
        audit,
        indent=2,
    ),
    encoding="utf-8",
)

CONTRACT_JSON.write_text(
    json.dumps(
        {
            "contract_name": (
                "edgeiq_historical_run_observation_fact_v2"
            ),
            "grain": (
                "ONE FACTUAL ROW PER CANONICAL HORSE PER HISTORICAL RACE"
            ),
            "natural_key": [
                "canonical_horse_id",
                "canonical_race_id",
                "race_date",
            ],
            "rules": [
                "Only factual source fields are published.",
                "Horse identity must resolve to Canonical Horse Master V2.",
                "Race date and race identity are mandatory.",
                "Duplicate checkpoint and repeated-source rows are collapsed.",
                "The most complete deterministic source row is retained.",
                "No performance rating, EPI or suitability is calculated.",
                "Missing factual values remain blank.",
            ],
            "builder_version": BUILDER_VERSION,
            "method_version": METHOD_VERSION,
            "fields": observation_fields,
        },
        indent=2,
    ),
    encoding="utf-8",
)

METHOD_MD.write_text(
    "\n".join(
        [
            "# EDGEIQ Historical Run Observation V2 Method",
            "",
            "## Purpose",
            "",
            "Create the canonical factual historical-run warehouse underneath Performance Intelligence.",
            "",
            "## Inclusion",
            "",
            "- Canonical horse identity resolved.",
            "- Valid historical race date.",
            "- Source race ID or sufficient factual race context to construct a governed race identity.",
            "",
            "## Deduplication",
            "",
            "Rows sharing canonical horse ID, canonical race ID and race date are treated as the same historical run.",
            "",
            "The row with the greatest factual-field completeness is retained. Ties are resolved deterministically by source path, row number and observation ID.",
            "",
            "## Prohibitions",
            "",
            "- No fuzzy horse matching.",
            "- No calculated ratings.",
            "- No EPI calculation.",
            "- No zero imputation.",
            "- No market substitution.",
            "- No invented sectional values.",
            "",
        ]
    ),
    encoding="utf-8",
)

audit_lines = [
    "# EDGEIQ Historical Run Observation V2 Audit",
    "",
    f"Status: `{audit['status']}`",
    "",
    "## Population",
    "",
    f"- Manifest sources: `{audit['manifest_source_files']}`",
    (
        "- Candidate observations before deduplication: "
        f"`{audit['candidate_observations_before_deduplication']}`"
    ),
    f"- Production observations: `{audit['production_observations']}`",
    (
        "- Duplicate observations removed: "
        f"`{audit['duplicate_observations_removed']}`"
    ),
    f"- Rejected source rows: `{audit['rejected_source_rows']}`",
    f"- Identity failures: `{audit['identity_failure_rows']}`",
    f"- Unique horses: `{audit['unique_horses']}`",
    f"- Unique races: `{audit['unique_races']}`",
    f"- Earliest race date: `{audit['earliest_race_date']}`",
    f"- Latest race date: `{audit['latest_race_date']}`",
    "",
    "## Identity Resolution",
    "",
]

for key, value in audit[
    "identity_resolution_method_counts"
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
        "- Factual source values only.",
        "- No performance calculation.",
        "- No EPI calculation.",
        "- No suitability calculation.",
        "- Missing values remain unavailable.",
        "- Duplicate source copies are retained in the duplicate ledger, not silently discarded.",
        "",
        f"- Candidate SHA256: `{sha256_file(OBSERVATION_CANDIDATE)}`",
        f"- Production SHA256: `{production_hash}`",
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
            "manifest_sources": audit[
                "manifest_source_files"
            ],
            "candidate_observations_before_deduplication": audit[
                "candidate_observations_before_deduplication"
            ],
            "production_observations": audit[
                "production_observations"
            ],
            "duplicates_removed": audit[
                "duplicate_observations_removed"
            ],
            "rejected_rows": audit[
                "rejected_source_rows"
            ],
            "identity_failures": audit[
                "identity_failure_rows"
            ],
            "unique_horses": audit[
                "unique_horses"
            ],
            "unique_races": audit[
                "unique_races"
            ],
            "earliest_race_date": audit[
                "earliest_race_date"
            ],
            "latest_race_date": audit[
                "latest_race_date"
            ],
            "candidate_sha256": audit[
                "candidate_sha256"
            ],
            "production_sha256": audit[
                "production_sha256"
            ],
        },
        indent=2,
    )
)
