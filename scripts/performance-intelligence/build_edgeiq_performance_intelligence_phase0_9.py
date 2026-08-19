from __future__ import annotations

import csv
import hashlib
import json
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

SECTIONALS = (
    ROOT
    / "public"
    / "data"
    / "racingcom_sectional_warehouse_v2.csv"
)

PHASE05 = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase0_5"
)

PHASE07 = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase0_7"
)

AUDIT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase0_9"
)

ARCH_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "architecture"
    / "phase0_9"
)

PROTOTYPE_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase0_9"
)

EDGEIQ_NAMESPACE = uuid.UUID(
    "ed91a5d8-e8e7-5b0f-a108-cd9c41c36901"
)

SOURCE_PROVIDER = "RACING_COM_SECTIONALS"
SOURCE_EVIDENCE_VERSION = 1
LINKAGE_VERSION = "SECTIONAL_LINKAGE_V0_2"
MIGRATION_VERSION = "CANONICAL_SECTIONAL_EVIDENCE_V0_1"
QUALITY_STATE = "COMPLETE"
PROGRESS_INTERVAL = 100_000

STRONG_METHOD = (
    "DATE_TRACK_RACE_HORSE_NORMALISED"
)

TRACK_ALIAS_MAP = {
    "VALLEY": "MOONEEVALLEY",
    "THEVALLEY": "MOONEEVALLEY",
    "MOONEEVALLEY": "MOONEEVALLEY",

    "PARKHILLSIDE": "SANDOWNHILLSIDE",
    "SANDOWNHILLSIDE": "SANDOWNHILLSIDE",
    "LADBROKESPARKHILLSIDE": "SANDOWNHILLSIDE",
    "SANDOWNPARKHILLSIDE": "SANDOWNHILLSIDE",

    "PARKLAKESIDE": "SANDOWNLAKESIDE",
    "SANDOWNLAKESIDE": "SANDOWNLAKESIDE",
    "LADBROKESPARKLAKESIDE": "SANDOWNLAKESIDE",
    "SANDOWNPARKLAKESIDE": "SANDOWNLAKESIDE",

    "PARKKILMORE": "KILMORE",
    "KILMORE": "KILMORE",
    "BET365PARKKILMORE": "KILMORE",

    "APIAMBENDIGO": "BENDIGO",
    "BET365BENDIGO": "BENDIGO",
    "BENDIGO": "BENDIGO",

    "PAKENHAMSYN": "PAKENHAMSYNTHETIC",
    "PAKENHAMSYNTH": "PAKENHAMSYNTHETIC",
    "PAKENHAMSYNTHETIC": "PAKENHAMSYNTHETIC",
    "SPORTSBETPAKENHAMSYNTHETIC": "PAKENHAMSYNTHETIC",

    "BALLARATSYN": "BALLARATSYNTHETIC",
    "BALLARATSYNTH": "BALLARATSYNTHETIC",
    "BALLARATSYNTHETIC": "BALLARATSYNTHETIC",
    "BET365BALLARATSYNTHETIC": "BALLARATSYNTHETIC",

    "GEELONGSYN": "GEELONGSYNTHETIC",
    "GEELONGSYNTH": "GEELONGSYNTHETIC",
    "GEELONGSYNTHETIC": "GEELONGSYNTHETIC",
    "BET365GEELONGSYNTHETIC": "GEELONGSYNTHETIC",
}

COUNTRY_SUFFIX_PATTERN = re.compile(
    r"\s*(?:\((?:AUS|NZ|IRE|GB|USA|FR|JPN|SAF|ARG|BRZ|GER|CAN|CHI|URU|ITY|SWE|DEN|SIN|HK)\)\s*)+$",
    re.IGNORECASE,
)


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def clean(value: Any) -> str:
    return str(value or "").strip()


def base_key(value: Any) -> str:
    return re.sub(
        r"[^A-Z0-9]+",
        "",
        clean(value).upper(),
    )


def normalise_date(value: Any) -> str:
    text = clean(value)

    if not text:
        return ""

    formats = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
    )

    for fmt in formats:
        try:
            return datetime.strptime(
                text[:10],
                fmt,
            ).strftime("%Y-%m-%d")
        except ValueError:
            continue

    match = re.match(
        r"^(\d{4}-\d{2}-\d{2})",
        text,
    )

    return (
        match.group(1)
        if match
        else ""
    )


def normalise_integer(value: Any) -> str:
    text = clean(value)

    if not text:
        return ""

    try:
        number = float(text)
    except ValueError:
        match = re.search(
            r"\d+",
            text,
        )
        return (
            match.group(0)
            if match
            else ""
        )

    if not number.is_integer():
        return ""

    return str(int(number))


def normalise_horse(value: Any) -> str:
    text = clean(value).upper()

    text = COUNTRY_SUFFIX_PATTERN.sub(
        "",
        text,
    )

    return re.sub(
        r"[^A-Z0-9]+",
        "",
        text,
    )


def normalise_track(value: Any) -> str:
    key = base_key(value)

    if key in TRACK_ALIAS_MAP:
        return TRACK_ALIAS_MAP[key]

    prefixes = (
        "BET365",
        "LADBROKES",
        "SPORTSBET",
        "APIAM",
        "TAB",
    )

    for prefix in prefixes:
        if key.startswith(prefix):
            stripped = key[
                len(prefix):
            ]

            if stripped in TRACK_ALIAS_MAP:
                return TRACK_ALIAS_MAP[
                    stripped
                ]

            key = stripped
            break

    return TRACK_ALIAS_MAP.get(
        key,
        key,
    )


def stable_id(
    entity_type: str,
    natural_key: str,
) -> str:
    generated = uuid.uuid5(
        EDGEIQ_NAMESPACE,
        (
            f"{entity_type}|"
            f"{natural_key}"
        ),
    )

    return (
        f"eiq_{entity_type.lower()}_"
        f"{generated.hex}"
    )


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(
                4 * 1024 * 1024
            ),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def latest_file(
    directory: Path,
    pattern: str,
) -> Path:
    candidates = sorted(
        directory.glob(pattern),
        key=lambda path: (
            path.stat().st_mtime
        ),
        reverse=True,
    )

    if not candidates:
        raise FileNotFoundError(
            f"No file matched {pattern}"
        )

    return candidates[0]


def write_json(
    path: Path,
    payload: Any,
) -> None:
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        path.write_text(
            "",
            encoding="utf-8",
        )
        return

    fields: list[str] = []

    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(rows)


def build_performance_lookup(
    identity_path: Path,
) -> dict[str, dict[str, str]]:
    lookup: dict[
        str,
        dict[str, str],
    ] = {}

    with identity_path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL
                == 0
            ):
                print(
                    "PERFORMANCE_LOOKUP_PROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            performance_id = clean(
                row.get(
                    "performance_id"
                )
            )

            if not performance_id:
                continue

            lookup[
                performance_id
            ] = {
                "race_date": (
                    normalise_date(
                        row.get(
                            "race_date"
                        )
                    )
                ),
                "track": (
                    normalise_track(
                        row.get(
                            "track"
                        )
                    )
                ),
                "race_number": (
                    normalise_integer(
                        row.get(
                            "race_number"
                        )
                    )
                ),
                "horse": (
                    normalise_horse(
                        row.get(
                            "horse_name"
                        )
                    )
                ),
                "race_id": clean(
                    row.get(
                        "race_id"
                    )
                ),
                "horse_id": clean(
                    row.get(
                        "horse_id"
                    )
                ),
                "meeting_id": clean(
                    row.get(
                        "meeting_id"
                    )
                ),
                "provider_race_id": clean(
                    row.get(
                        "provider_race_id"
                    )
                ),
                "provider_runner_id": clean(
                    row.get(
                        "provider_runner_id"
                    )
                ),
            }

    return lookup


def revalidate_links(
    linkage_path: Path,
    performance_lookup: dict[
        str,
        dict[str, str],
    ],
    validation_path: Path,
) -> dict[str, Any]:
    status_counts = Counter()
    method_counts = Counter()
    validation_counts = Counter()
    alias_repairs = Counter()

    validated_strong_rows: set[int] = set()
    mismatch_samples: list[
        dict[str, Any]
    ] = []

    linked_rows = 0
    validated_rows = 0
    strong_validated_rows = 0
    repaired_rows = 0
    mismatch_rows = 0

    fields = [
        "sectional_source_row",
        "performance_id",
        "link_status",
        "link_method",
        "validation_state",
        "strong_migration_eligible",
        "sectional_race_date",
        "result_race_date",
        "sectional_track",
        "result_track",
        "sectional_race_number",
        "result_race_number",
        "sectional_horse",
        "result_horse",
        "date_match",
        "track_match",
        "race_number_match",
        "horse_match",
        "alias_repair_applied",
    ]

    with linkage_path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as source_handle, validation_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as output_handle:
        reader = csv.DictReader(
            source_handle
        )
        writer = csv.DictWriter(
            output_handle,
            fieldnames=fields,
        )
        writer.writeheader()

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL
                == 0
            ):
                print(
                    "REVALIDATION_PROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            performance_id = clean(
                row.get(
                    "performance_id"
                )
            )
            link_status = clean(
                row.get(
                    "link_status"
                )
            )
            link_method = clean(
                row.get(
                    "link_method"
                )
            )

            status_counts[
                link_status
            ] += 1
            method_counts[
                link_method
            ] += 1

            sectional_source_row = (
                normalise_integer(
                    row.get(
                        "sectional_source_row"
                    )
                )
            )

            sectional_date = (
                normalise_date(
                    row.get(
                        "race_date"
                    )
                )
            )

            raw_sectional_track = clean(
                row.get(
                    "raw_track"
                )
                or row.get(
                    "canonical_track"
                )
            )

            sectional_track = (
                normalise_track(
                    raw_sectional_track
                )
            )

            sectional_race_number = (
                normalise_integer(
                    row.get(
                        "race_number"
                    )
                )
            )

            sectional_horse = (
                normalise_horse(
                    row.get(
                        "raw_horse"
                    )
                    or row.get(
                        "canonical_horse"
                    )
                )
            )

            result = (
                performance_lookup.get(
                    performance_id
                )
            )

            result_date = ""
            result_track = ""
            result_race_number = ""
            result_horse = ""

            date_match = False
            track_match = False
            race_number_match = False
            horse_match = False
            alias_repair_applied = False
            validation_state = (
                "NOT_LINKED"
            )
            strong_eligible = False

            if performance_id and result:
                linked_rows += 1

                result_date = result[
                    "race_date"
                ]
                result_track = result[
                    "track"
                ]
                result_race_number = (
                    result[
                        "race_number"
                    ]
                )
                result_horse = result[
                    "horse"
                ]

                date_match = (
                    sectional_date
                    == result_date
                )
                track_match = (
                    sectional_track
                    == result_track
                )
                race_number_match = (
                    sectional_race_number
                    == result_race_number
                )
                horse_match = (
                    sectional_horse
                    == result_horse
                )

                if (
                    date_match
                    and track_match
                    and race_number_match
                    and horse_match
                ):
                    validation_state = (
                        "VALIDATED_FULL_KEY"
                    )
                    validated_rows += 1

                    if (
                        link_method
                        == STRONG_METHOD
                    ):
                        strong_eligible = True
                        strong_validated_rows += 1

                        if sectional_source_row:
                            validated_strong_rows.add(
                                int(
                                    sectional_source_row
                                )
                            )

                else:
                    validation_state = (
                        "VALIDATION_MISMATCH"
                    )
                    mismatch_rows += 1

                    previous_track = base_key(
                        raw_sectional_track
                    )

                    if (
                        previous_track
                        != sectional_track
                        and track_match
                    ):
                        alias_repair_applied = (
                            True
                        )
                        repaired_rows += 1
                        alias_repairs[
                            (
                                f"{previous_track}"
                                f"->{sectional_track}"
                            )
                        ] += 1

                    if (
                        len(
                            mismatch_samples
                        )
                        < 250
                    ):
                        mismatch_samples.append(
                            {
                                "performance_id": (
                                    performance_id
                                ),
                                "link_method": (
                                    link_method
                                ),
                                "sectional_date": (
                                    sectional_date
                                ),
                                "result_date": (
                                    result_date
                                ),
                                "raw_sectional_track": (
                                    raw_sectional_track
                                ),
                                "sectional_track": (
                                    sectional_track
                                ),
                                "result_track": (
                                    result_track
                                ),
                                "sectional_race_number": (
                                    sectional_race_number
                                ),
                                "result_race_number": (
                                    result_race_number
                                ),
                                "sectional_horse": (
                                    sectional_horse
                                ),
                                "result_horse": (
                                    result_horse
                                ),
                            }
                        )

            validation_counts[
                validation_state
            ] += 1

            writer.writerow(
                {
                    "sectional_source_row": (
                        sectional_source_row
                    ),
                    "performance_id": (
                        performance_id
                    ),
                    "link_status": (
                        link_status
                    ),
                    "link_method": (
                        link_method
                    ),
                    "validation_state": (
                        validation_state
                    ),
                    "strong_migration_eligible": (
                        strong_eligible
                    ),
                    "sectional_race_date": (
                        sectional_date
                    ),
                    "result_race_date": (
                        result_date
                    ),
                    "sectional_track": (
                        sectional_track
                    ),
                    "result_track": (
                        result_track
                    ),
                    "sectional_race_number": (
                        sectional_race_number
                    ),
                    "result_race_number": (
                        result_race_number
                    ),
                    "sectional_horse": (
                        sectional_horse
                    ),
                    "result_horse": (
                        result_horse
                    ),
                    "date_match": (
                        date_match
                    ),
                    "track_match": (
                        track_match
                    ),
                    "race_number_match": (
                        race_number_match
                    ),
                    "horse_match": (
                        horse_match
                    ),
                    "alias_repair_applied": (
                        alias_repair_applied
                    ),
                }
            )

    return {
        "linked_rows": linked_rows,
        "validated_rows": (
            validated_rows
        ),
        "validated_pct_of_linked": (
            round(
                validated_rows
                / linked_rows
                * 100,
                4,
            )
            if linked_rows
            else 0.0
        ),
        "strong_validated_rows": (
            strong_validated_rows
        ),
        "validation_mismatch_rows": (
            mismatch_rows
        ),
        "alias_repaired_rows": (
            repaired_rows
        ),
        "status_counts": dict(
            sorted(
                status_counts.items()
            )
        ),
        "method_counts": dict(
            sorted(
                method_counts.items()
            )
        ),
        "validation_counts": dict(
            sorted(
                validation_counts.items()
            )
        ),
        "alias_repair_counts": dict(
            sorted(
                alias_repairs.items()
            )
        ),
        "mismatch_samples": (
            mismatch_samples
        ),
        "validated_strong_source_rows": (
            validated_strong_rows
        ),
    }


def load_linkage_metadata(
    validation_path: Path,
) -> dict[int, dict[str, str]]:
    metadata: dict[
        int,
        dict[str, str],
    ] = {}

    with validation_path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            if clean(
                row.get(
                    "strong_migration_eligible"
                )
            ).lower() != "true":
                continue

            source_row = normalise_integer(
                row.get(
                    "sectional_source_row"
                )
            )

            if not source_row:
                continue

            metadata[
                int(source_row)
            ] = {
                "performance_id": clean(
                    row.get(
                        "performance_id"
                    )
                ),
                "link_method": clean(
                    row.get(
                        "link_method"
                    )
                ),
                "validation_state": clean(
                    row.get(
                        "validation_state"
                    )
                ),
                "canonical_track": clean(
                    row.get(
                        "sectional_track"
                    )
                ),
                "canonical_horse": clean(
                    row.get(
                        "sectional_horse"
                    )
                ),
                "race_date": clean(
                    row.get(
                        "sectional_race_date"
                    )
                ),
                "race_number": clean(
                    row.get(
                        "sectional_race_number"
                    )
                ),
            }

    return metadata


def build_canonical_sectional_evidence(
    validation_path: Path,
    performance_lookup: dict[
        str,
        dict[str, str],
    ],
    output_path: Path,
    duplicate_path: Path,
) -> dict[str, Any]:
    linkage_metadata = (
        load_linkage_metadata(
            validation_path
        )
    )

    source_hash = sha256_file(
        SECTIONALS
    )

    source_evidence_id = stable_id(
        "source_evidence",
        (
            f"{SOURCE_PROVIDER}|"
            f"{SECTIONALS.name}|"
            f"{source_hash}"
        ),
    )

    generated_at = utc_now()
    evidence_ids: set[str] = set()
    duplicate_rows: list[
        dict[str, Any]
    ] = []

    migrated_rows = 0
    skipped_rows = 0
    missing_performance_rows = 0
    duplicate_evidence_rows = 0

    with SECTIONALS.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as source_handle:
        reader = csv.DictReader(
            source_handle
        )

        source_columns = list(
            reader.fieldnames or []
        )

        canonical_columns = [
            "performance_sectional_id",
            "performance_id",
            "race_id",
            "meeting_id",
            "horse_id",
            "source_evidence_id",
            "source_row_number",
            "provider_code",
            "race_date",
            "canonical_track",
            "race_number",
            "canonical_horse",
            "link_method",
            "linkage_version",
            "timing_quality_state",
            "evidence_version",
            "source_sha256",
            "migration_version",
            "generated_at",
        ]

        raw_columns = [
            f"raw_{column}"
            for column in source_columns
        ]

        output_fields = (
            canonical_columns
            + raw_columns
        )

        with output_path.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as output_handle:
            writer = csv.DictWriter(
                output_handle,
                fieldnames=output_fields,
            )
            writer.writeheader()

            for source_row_number, row in enumerate(
                reader,
                start=2,
            ):
                if (
                    source_row_number == 2
                    or source_row_number
                    % PROGRESS_INTERVAL
                    == 0
                ):
                    print(
                        "CANONICAL_SECTIONAL_"
                        "MIGRATION_PROGRESS="
                        f"{source_row_number}",
                        flush=True,
                    )

                metadata = (
                    linkage_metadata.get(
                        source_row_number
                    )
                )

                if not metadata:
                    skipped_rows += 1
                    continue

                performance_id = (
                    metadata[
                        "performance_id"
                    ]
                )

                performance = (
                    performance_lookup.get(
                        performance_id
                    )
                )

                if not performance:
                    missing_performance_rows += 1
                    continue

                evidence_natural_key = (
                    f"{performance_id}|"
                    f"{source_evidence_id}|"
                    f"{source_row_number}"
                )

                performance_sectional_id = (
                    stable_id(
                        "performance_sectional",
                        evidence_natural_key,
                    )
                )

                if (
                    performance_sectional_id
                    in evidence_ids
                ):
                    duplicate_evidence_rows += 1

                    duplicate_rows.append(
                        {
                            "performance_sectional_id": (
                                performance_sectional_id
                            ),
                            "performance_id": (
                                performance_id
                            ),
                            "source_row_number": (
                                source_row_number
                            ),
                        }
                    )
                    continue

                evidence_ids.add(
                    performance_sectional_id
                )

                output_row = {
                    "performance_sectional_id": (
                        performance_sectional_id
                    ),
                    "performance_id": (
                        performance_id
                    ),
                    "race_id": (
                        performance[
                            "race_id"
                        ]
                    ),
                    "meeting_id": (
                        performance[
                            "meeting_id"
                        ]
                    ),
                    "horse_id": (
                        performance[
                            "horse_id"
                        ]
                    ),
                    "source_evidence_id": (
                        source_evidence_id
                    ),
                    "source_row_number": (
                        source_row_number
                    ),
                    "provider_code": (
                        SOURCE_PROVIDER
                    ),
                    "race_date": (
                        metadata[
                            "race_date"
                        ]
                    ),
                    "canonical_track": (
                        metadata[
                            "canonical_track"
                        ]
                    ),
                    "race_number": (
                        metadata[
                            "race_number"
                        ]
                    ),
                    "canonical_horse": (
                        metadata[
                            "canonical_horse"
                        ]
                    ),
                    "link_method": (
                        metadata[
                            "link_method"
                        ]
                    ),
                    "linkage_version": (
                        LINKAGE_VERSION
                    ),
                    "timing_quality_state": (
                        QUALITY_STATE
                    ),
                    "evidence_version": (
                        SOURCE_EVIDENCE_VERSION
                    ),
                    "source_sha256": (
                        source_hash
                    ),
                    "migration_version": (
                        MIGRATION_VERSION
                    ),
                    "generated_at": (
                        generated_at
                    ),
                }

                for source_column in (
                    source_columns
                ):
                    output_row[
                        f"raw_{source_column}"
                    ] = clean(
                        row.get(
                            source_column
                        )
                    )

                writer.writerow(
                    output_row
                )
                migrated_rows += 1

    write_csv(
        duplicate_path,
        duplicate_rows,
    )

    return {
        "eligible_source_rows": len(
            linkage_metadata
        ),
        "migrated_rows": (
            migrated_rows
        ),
        "skipped_noneligible_rows": (
            skipped_rows
        ),
        "missing_performance_rows": (
            missing_performance_rows
        ),
        "duplicate_evidence_rows": (
            duplicate_evidence_rows
        ),
        "unique_evidence_ids": len(
            evidence_ids
        ),
        "source_sha256": (
            source_hash
        ),
        "source_evidence_id": (
            source_evidence_id
        ),
        "linkage_version": (
            LINKAGE_VERSION
        ),
        "migration_version": (
            MIGRATION_VERSION
        ),
    }


def architecture_markdown() -> str:
    return """# EDGEiQ Canonical Sectional Evidence V0.1

## Purpose

This prototype creates immutable canonical sectional-evidence rows from only the strongest validated linkage method.

## Promotion rule

A source sectional row is eligible only when:

1. It has a deterministic `performance_id`.
2. It was linked using `DATE_TRACK_RACE_HORSE_NORMALISED`.
3. Date, canonical track, race number and canonical horse all validate against the performance identity record.
4. The source row is preserved unchanged through `raw_*` fields.
5. A source file SHA-256 is recorded.
6. A deterministic `performance_sectional_id` is generated.
7. Evidence version, linkage version and migration version are recorded.

## Excluded from this prototype

The following remain outside canonical migration:

- conditional date-track-horse links
- conditional date-race-horse links
- date-horse-only research links
- ambiguous links
- unlinked rows
- validation mismatches

## Track aliases added

- `VALLEY` and `THE VALLEY` become `MOONEEVALLEY`
- `PARK HILLSIDE` becomes `SANDOWNHILLSIDE`
- `PARK LAKESIDE` becomes `SANDOWNLAKESIDE`
- `PARK KILMORE` becomes `KILMORE`
- synthetic course aliases are normalised explicitly

No fuzzy matching is permitted.
"""


def markdown_report(
    summary: dict[str, Any],
) -> str:
    validation = summary[
        "revalidation"
    ]
    migration = summary[
        "canonical_sectional_evidence"
    ]

    lines = [
        "# EDGEiQ Performance Intelligence",
        "## Phase 0.9 Immutable Canonical Sectional Evidence Prototype",
        "",
        f"Generated UTC: `{summary['generated_utc']}`",
        "",
        "## Revalidation",
        "",
        f"- Linked rows checked: **{validation['linked_rows']:,}**",
        f"- Fully validated rows: **{validation['validated_rows']:,}**",
        f"- Fully validated percentage: **{validation['validated_pct_of_linked']}%**",
        f"- Strong validated rows: **{validation['strong_validated_rows']:,}**",
        f"- Validation mismatches: **{validation['validation_mismatch_rows']:,}**",
        "",
        "## Immutable evidence prototype",
        "",
        f"- Eligible source rows: **{migration['eligible_source_rows']:,}**",
        f"- Migrated evidence rows: **{migration['migrated_rows']:,}**",
        f"- Unique evidence IDs: **{migration['unique_evidence_ids']:,}**",
        f"- Duplicate evidence rows: **{migration['duplicate_evidence_rows']:,}**",
        f"- Missing performance rows: **{migration['missing_performance_rows']:,}**",
        "",
        "## Status",
        "",
        "**PROTOTYPE ONLY — PRODUCTION DATA NOT MODIFIED**",
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    ARCH_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    PROTOTYPE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    identity_path = latest_file(
        PHASE05,
        (
            "edgeiq_canonical_performance_"
            "identity_prototype_v0_1_*.csv"
        ),
    )

    linkage_path = latest_file(
        PHASE07,
        (
            "edgeiq_governed_sectional_"
            "performance_linkage_v0_1_*.csv"
        ),
    )

    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    validation_path = (
        PROTOTYPE_DIR
        / f"edgeiq_sectional_link_revalidation_v0_2_{run_id}.csv"
    )

    evidence_path = (
        PROTOTYPE_DIR
        / f"edgeiq_canonical_sectional_evidence_v0_1_{run_id}.csv"
    )

    duplicate_path = (
        AUDIT_DIR
        / f"edgeiq_canonical_sectional_evidence_duplicates_v0_1_{run_id}.csv"
    )

    summary_path = (
        AUDIT_DIR
        / f"edgeiq_performance_intelligence_phase0_9_summary_{run_id}.json"
    )

    latest_path = (
        AUDIT_DIR
        / "edgeiq_performance_intelligence_phase0_9_latest.json"
    )

    report_path = (
        AUDIT_DIR
        / f"EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE0_9_REPORT_{run_id}.md"
    )

    architecture_path = (
        ARCH_DIR
        / "EDGEIQ_CANONICAL_SECTIONAL_EVIDENCE_V0_1.md"
    )

    alias_path = (
        ARCH_DIR
        / "edgeiq_track_alias_registry_v0_1.csv"
    )

    alias_rows = [
        {
            "raw_track_key": raw,
            "canonical_track_key": canonical,
            "registry_version": "0.1",
            "automatic": True,
        }
        for raw, canonical
        in sorted(
            TRACK_ALIAS_MAP.items()
        )
    ]

    write_csv(
        alias_path,
        alias_rows,
    )

    architecture_path.write_text(
        architecture_markdown(),
        encoding="utf-8",
    )

    print(
        "PHASE0_9_BUILD_PERFORMANCE_LOOKUP_START",
        flush=True,
    )

    performance_lookup = (
        build_performance_lookup(
            identity_path
        )
    )

    print(
        "PHASE0_9_REVALIDATION_START",
        flush=True,
    )

    revalidation_summary = (
        revalidate_links(
            linkage_path,
            performance_lookup,
            validation_path,
        )
    )

    print(
        "PHASE0_9_CANONICAL_SECTIONAL_"
        "EVIDENCE_BUILD_START",
        flush=True,
    )

    migration_summary = (
        build_canonical_sectional_evidence(
            validation_path,
            performance_lookup,
            evidence_path,
            duplicate_path,
        )
    )

    summary = {
        "audit_name": (
            "EDGEiQ Performance Intelligence "
            "Phase 0.9 Immutable Canonical "
            "Sectional Evidence Prototype"
        ),
        "generated_utc": utc_now(),
        "production_data_modified": False,
        "identity_source": str(
            identity_path.relative_to(
                ROOT
            )
        ).replace("\\", "/"),
        "linkage_source": str(
            linkage_path.relative_to(
                ROOT
            )
        ).replace("\\", "/"),
        "sectional_source": str(
            SECTIONALS.relative_to(
                ROOT
            )
        ).replace("\\", "/"),
        "revalidation": {
            key: value
            for key, value
            in revalidation_summary.items()
            if key
            != "validated_strong_source_rows"
        },
        "canonical_sectional_evidence": (
            migration_summary
        ),
        "canonical_status": (
            "IMMUTABLE_SECTIONAL_EVIDENCE_"
            "PROTOTYPE_BUILT_NOT_PROMOTED"
        ),
        "promotion_rule": (
            "Only fully validated strong "
            "date-track-race-horse links "
            "were migrated."
        ),
        "next_stage": (
            "Phase 1.0 canonical raw warehouse "
            "schema validation, snapshot manifest "
            "and reproducibility audit"
        ),
        "outputs": {
            "revalidation": str(
                validation_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "canonical_sectional_evidence": str(
                evidence_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "duplicate_audit": str(
                duplicate_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "track_alias_registry": str(
                alias_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "architecture": str(
                architecture_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
        },
    }

    write_json(
        summary_path,
        summary,
    )

    write_json(
        latest_path,
        summary,
    )

    report_path.write_text(
        markdown_report(summary),
        encoding="utf-8",
    )

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE0_9_IMMUTABLE_CANONICAL_"
        "SECTIONAL_EVIDENCE_PROTOTYPE_PASS",
        flush=True,
    )

    print(
        f"REVALIDATION={validation_path}",
        flush=True,
    )

    print(
        f"CANONICAL_SECTIONAL_EVIDENCE={evidence_path}",
        flush=True,
    )

    print(
        f"DUPLICATE_AUDIT={duplicate_path}",
        flush=True,
    )

    print(
        f"TRACK_ALIAS_REGISTRY={alias_path}",
        flush=True,
    )

    print(
        f"ARCHITECTURE={architecture_path}",
        flush=True,
    )

    print(
        f"SUMMARY={summary_path}",
        flush=True,
    )

    print(
        f"REPORT={report_path}",
        flush=True,
    )


if __name__ == "__main__":
    main()
