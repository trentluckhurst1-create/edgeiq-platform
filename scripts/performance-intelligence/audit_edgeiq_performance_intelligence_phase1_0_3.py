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

PHASE102 = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase1_0_2"
)

AUDIT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase1_0_3"
)

SNAPSHOT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "snapshots"
    / "phase1_0_3"
)

ARCH_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "architecture"
    / "phase1_0_3"
)

EDGEIQ_NAMESPACE = uuid.UUID(
    "ed91a5d8-e8e7-5b0f-a108-cd9c41c36901"
)

SNAPSHOT_VERSION = (
    "PERFORMANCE_WAREHOUSE_SNAPSHOT_V0_2"
)

AUDIT_VERSION = (
    "PHASE1_0_3_REPRODUCIBILITY_AUDIT_V0_2"
)

IDENTITY_VERSION = (
    "PERFORMANCE_IDENTITY_V0_2_"
    "FULL_RACE_CONTEXT"
)

PROGRESS_INTERVAL = 100_000

PERFORMANCE_REQUIRED_COLUMNS = (
    "performance_id",
    "legacy_performance_id",
    "race_id",
    "meeting_id",
    "horse_id",
    "source_evidence_id",
    "source_row_number",
    "provider_race_id",
    "provider_runner_id",
    "race_date",
    "state",
    "track",
    "race_number",
    "horse_name",
    "identity_method",
    "identity_quality_state",
    "identity_version",
    "evidence_version",
    "performance_natural_key_version",
    "rekeyed_at",
)

SECTIONAL_REQUIRED_COLUMNS = (
    "performance_sectional_id",
    "legacy_performance_sectional_id",
    "performance_id",
    "legacy_performance_id",
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
    "identity_remap_version",
    "remapped_at",
)

PERFORMANCE_NON_NULL_COLUMNS = (
    "performance_id",
    "legacy_performance_id",
    "race_id",
    "meeting_id",
    "horse_id",
    "source_evidence_id",
    "source_row_number",
    "provider_race_id",
    "provider_runner_id",
    "race_date",
    "state",
    "track",
    "race_number",
    "horse_name",
    "identity_quality_state",
    "evidence_version",
    "performance_natural_key_version",
)

SECTIONAL_NON_NULL_COLUMNS = (
    "performance_sectional_id",
    "legacy_performance_sectional_id",
    "performance_id",
    "legacy_performance_id",
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
    "identity_remap_version",
)

ALLOWED_IDENTITY_STATES = {
    "COMPLETE",
    "PARTIAL",
    "IDENTITY_UNRESOLVED",
    "SOURCE_CONFLICT",
}

ALLOWED_TIMING_STATES = {
    "COMPLETE",
    "PARTIAL",
    "TIMING_INCONSISTENCY",
    "SECTIONAL_MISMATCH",
    "SOURCE_CONFLICT",
    "IDENTITY_UNRESOLVED",
    "INSUFFICIENT_EVIDENCE",
    "EXCLUDED",
    "SUPERSEDED",
    "PENDING_VALIDATION",
}


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def clean(value: Any) -> str:
    return str(value or "").strip()


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

    for date_format in formats:
        try:
            return datetime.strptime(
                text[:10],
                date_format,
            ).strftime("%Y-%m-%d")
        except ValueError:
            continue

    match = re.match(
        r"^(\d{4}-\d{2}-\d{2})",
        text,
    )

    return match.group(1) if match else ""


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


def normalise_text(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        clean(value).upper(),
    )


def stable_id(
    entity_type: str,
    natural_key: str,
) -> str:
    generated = uuid.uuid5(
        EDGEIQ_NAMESPACE,
        f"{entity_type}|{natural_key}",
    )

    return (
        f"eiq_{entity_type.lower()}_"
        f"{generated.hex}"
    )


def latest_file(
    directory: Path,
    pattern: str,
) -> Path:
    candidates = sorted(
        directory.glob(pattern),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not candidates:
        raise FileNotFoundError(
            f"No file matched {pattern}"
        )

    return candidates[0]


def sha256_file(path: Path) -> str:
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


def performance_natural_key(
    row: dict[str, str],
) -> str:
    components = (
        normalise_date(
            row.get("race_date")
        ),
        normalise_text(
            row.get("state")
        ),
        normalise_text(
            row.get("track")
        ),
        normalise_integer(
            row.get("race_number")
        ),
        clean(
            row.get("provider_race_id")
        ),
        clean(
            row.get("provider_runner_id")
        ),
        clean(
            row.get("horse_id")
        ),
    )

    if not all(components):
        return ""

    return "|".join(components)


def profile_asset(
    label: str,
    path: Path,
    primary_key: str,
    required_columns: tuple[str, ...],
    non_null_columns: tuple[str, ...],
    quality_column: str,
) -> dict[str, Any]:
    rows = 0
    keys: set[str] = set()
    duplicate_rows = 0
    blank_primary_keys = 0
    blank_counts = Counter()
    quality_counts = Counter()
    version_counts = Counter()
    race_ids: set[str] = set()
    horse_ids: set[str] = set()
    performance_ids: set[str] = set()
    dates: list[str] = []

    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])

        missing_columns = [
            column
            for column in required_columns
            if column not in columns
        ]

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            rows += 1

            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL
                == 0
            ):
                print(
                    f"PROFILE_PROGRESS={label} "
                    f"ROWS={row_number}",
                    flush=True,
                )

            key = clean(
                row.get(primary_key)
            )

            if not key:
                blank_primary_keys += 1
            elif key in keys:
                duplicate_rows += 1
            else:
                keys.add(key)

            for column in non_null_columns:
                if not clean(row.get(column)):
                    blank_counts[column] += 1

            race_id = clean(
                row.get("race_id")
            )
            horse_id = clean(
                row.get("horse_id")
            )
            performance_id = clean(
                row.get("performance_id")
            )
            race_date = normalise_date(
                row.get("race_date")
            )

            if race_id:
                race_ids.add(race_id)

            if horse_id:
                horse_ids.add(horse_id)

            if performance_id:
                performance_ids.add(
                    performance_id
                )

            if race_date:
                dates.append(race_date)

            quality = clean(
                row.get(quality_column)
            )

            if quality:
                quality_counts[
                    quality
                ] += 1

            for version_column in (
                "identity_version",
                "performance_natural_key_version",
                "linkage_version",
                "migration_version",
                "identity_remap_version",
                "evidence_version",
            ):
                version_value = clean(
                    row.get(version_column)
                )

                if version_value:
                    version_counts[
                        (
                            f"{version_column}="
                            f"{version_value}"
                        )
                    ] += 1

    return {
        "label": label,
        "path": str(
            path.relative_to(ROOT)
        ).replace("\\", "/"),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "rows": rows,
        "columns": columns,
        "column_count": len(columns),
        "missing_required_columns": (
            missing_columns
        ),
        "duplicate_primary_key_rows": (
            duplicate_rows
        ),
        "blank_primary_key_rows": (
            blank_primary_keys
        ),
        "blank_non_null_counts": dict(
            sorted(
                blank_counts.items()
            )
        ),
        "unique_races": len(race_ids),
        "unique_horses": len(horse_ids),
        "unique_performances": len(
            performance_ids
        ),
        "min_race_date": (
            min(dates)
            if dates
            else ""
        ),
        "max_race_date": (
            max(dates)
            if dates
            else ""
        ),
        "quality_state_counts": dict(
            sorted(
                quality_counts.items()
            )
        ),
        "version_counts": dict(
            sorted(
                version_counts.items()
            )
        ),
    }


def validate_performance_ids(
    path: Path,
) -> dict[str, Any]:
    rows = 0
    reproducible = 0
    mismatches = 0
    incomplete_keys = 0
    version_mismatches = 0
    samples: list[dict[str, Any]] = []

    with path.open(
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
            rows += 1

            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL
                == 0
            ):
                print(
                    "PERFORMANCE_REPROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            natural_key = (
                performance_natural_key(
                    row
                )
            )

            if not natural_key:
                incomplete_keys += 1
                continue

            reproduced = stable_id(
                "performance",
                natural_key,
            )

            stored = clean(
                row.get("performance_id")
            )

            if reproduced == stored:
                reproducible += 1
            else:
                mismatches += 1

                if len(samples) < 100:
                    samples.append(
                        {
                            "row": row_number,
                            "stored": stored,
                            "reproduced": (
                                reproduced
                            ),
                            "natural_key": (
                                natural_key
                            ),
                        }
                    )

            if clean(
                row.get(
                    "performance_natural_key_version"
                )
            ) != IDENTITY_VERSION:
                version_mismatches += 1

    return {
        "rows_checked": rows,
        "reproducible_rows": (
            reproducible
        ),
        "mismatch_rows": mismatches,
        "incomplete_natural_key_rows": (
            incomplete_keys
        ),
        "version_mismatch_rows": (
            version_mismatches
        ),
        "reproducibility_pct": (
            round(
                reproducible
                / rows
                * 100,
                6,
            )
            if rows
            else 0.0
        ),
        "mismatch_samples": samples,
    }


def validate_sectional_ids(
    path: Path,
) -> dict[str, Any]:
    rows = 0
    reproducible = 0
    mismatches = 0
    incomplete_keys = 0
    samples: list[dict[str, Any]] = []

    with path.open(
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
            rows += 1

            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL
                == 0
            ):
                print(
                    "SECTIONAL_REPROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            performance_id = clean(
                row.get("performance_id")
            )
            source_evidence_id = clean(
                row.get(
                    "source_evidence_id"
                )
            )
            source_row_number = clean(
                row.get(
                    "source_row_number"
                )
            )

            if not all(
                (
                    performance_id,
                    source_evidence_id,
                    source_row_number,
                )
            ):
                incomplete_keys += 1
                continue

            reproduced = stable_id(
                "performance_sectional",
                (
                    f"{performance_id}|"
                    f"{source_evidence_id}|"
                    f"{source_row_number}"
                ),
            )

            stored = clean(
                row.get(
                    "performance_sectional_id"
                )
            )

            if reproduced == stored:
                reproducible += 1
            else:
                mismatches += 1

                if len(samples) < 100:
                    samples.append(
                        {
                            "row": row_number,
                            "stored": stored,
                            "reproduced": (
                                reproduced
                            ),
                        }
                    )

    return {
        "rows_checked": rows,
        "reproducible_rows": (
            reproducible
        ),
        "mismatch_rows": mismatches,
        "incomplete_natural_key_rows": (
            incomplete_keys
        ),
        "reproducibility_pct": (
            round(
                reproducible
                / rows
                * 100,
                6,
            )
            if rows
            else 0.0
        ),
        "mismatch_samples": samples,
    }


def validate_foreign_keys(
    performance_path: Path,
    sectional_path: Path,
) -> dict[str, Any]:
    performance_ids: set[str] = set()

    with performance_path.open(
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
                    "FK_PARENT_PROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            value = clean(
                row.get("performance_id")
            )

            if value:
                performance_ids.add(value)

    rows = 0
    matched = 0
    missing = 0
    missing_samples = Counter()

    with sectional_path.open(
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
            rows += 1

            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL
                == 0
            ):
                print(
                    "FK_CHILD_PROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            value = clean(
                row.get("performance_id")
            )

            if value in performance_ids:
                matched += 1
            else:
                missing += 1
                missing_samples[
                    value or "<BLANK>"
                ] += 1

    return {
        "parent_performance_ids": len(
            performance_ids
        ),
        "sectional_rows": rows,
        "matched_rows": matched,
        "missing_rows": missing,
        "match_pct": (
            round(
                matched
                / rows
                * 100,
                6,
            )
            if rows
            else 0.0
        ),
        "missing_samples": [
            {
                "performance_id": key,
                "rows": count,
            }
            for key, count
            in missing_samples.most_common(
                100
            )
        ],
    }


def validate_legacy_collision_lineage(
    performance_path: Path,
) -> dict[str, Any]:
    legacy_counts = Counter()
    new_ids_by_legacy: dict[
        str,
        set[str],
    ] = {}

    with performance_path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            legacy_id = clean(
                row.get(
                    "legacy_performance_id"
                )
            )
            new_id = clean(
                row.get("performance_id")
            )

            if not legacy_id:
                continue

            legacy_counts[
                legacy_id
            ] += 1

            new_ids_by_legacy.setdefault(
                legacy_id,
                set(),
            ).add(new_id)

    collision_groups = [
        legacy_id
        for legacy_id, count
        in legacy_counts.items()
        if count > 1
    ]

    incorrectly_unsplit = [
        legacy_id
        for legacy_id in collision_groups
        if len(
            new_ids_by_legacy[
                legacy_id
            ]
        )
        != legacy_counts[
            legacy_id
        ]
    ]

    return {
        "legacy_ids": len(
            legacy_counts
        ),
        "legacy_collision_groups": len(
            collision_groups
        ),
        "correctly_split_groups": (
            len(collision_groups)
            - len(
                incorrectly_unsplit
            )
        ),
        "incorrectly_unsplit_groups": len(
            incorrectly_unsplit
        ),
        "incorrectly_unsplit_samples": (
            incorrectly_unsplit[:100]
        ),
    }


def make_checks(
    performance_profile: dict[str, Any],
    sectional_profile: dict[str, Any],
    performance_repro: dict[str, Any],
    sectional_repro: dict[str, Any],
    foreign_keys: dict[str, Any],
    collision_lineage: dict[str, Any],
) -> list[dict[str, Any]]:
    performance_unknown = [
        state
        for state in performance_profile[
            "quality_state_counts"
        ]
        if state
        not in ALLOWED_IDENTITY_STATES
    ]

    sectional_unknown = [
        state
        for state in sectional_profile[
            "quality_state_counts"
        ]
        if state
        not in ALLOWED_TIMING_STATES
    ]

    return [
        {
            "check": "PERFORMANCE_SCHEMA",
            "passed": (
                not performance_profile[
                    "missing_required_columns"
                ]
            ),
            "observed": (
                " | ".join(
                    performance_profile[
                        "missing_required_columns"
                    ]
                )
                or "NO_MISSING_COLUMNS"
            ),
        },
        {
            "check": "SECTIONAL_SCHEMA",
            "passed": (
                not sectional_profile[
                    "missing_required_columns"
                ]
            ),
            "observed": (
                " | ".join(
                    sectional_profile[
                        "missing_required_columns"
                    ]
                )
                or "NO_MISSING_COLUMNS"
            ),
        },
        {
            "check": (
                "PERFORMANCE_PRIMARY_KEY_UNIQUE"
            ),
            "passed": (
                performance_profile[
                    "duplicate_primary_key_rows"
                ]
                == 0
                and performance_profile[
                    "blank_primary_key_rows"
                ]
                == 0
            ),
            "observed": (
                f"duplicates="
                f"{performance_profile['duplicate_primary_key_rows']};"
                f"blank="
                f"{performance_profile['blank_primary_key_rows']}"
            ),
        },
        {
            "check": (
                "SECTIONAL_PRIMARY_KEY_UNIQUE"
            ),
            "passed": (
                sectional_profile[
                    "duplicate_primary_key_rows"
                ]
                == 0
                and sectional_profile[
                    "blank_primary_key_rows"
                ]
                == 0
            ),
            "observed": (
                f"duplicates="
                f"{sectional_profile['duplicate_primary_key_rows']};"
                f"blank="
                f"{sectional_profile['blank_primary_key_rows']}"
            ),
        },
        {
            "check": (
                "PERFORMANCE_REQUIRED_VALUES"
            ),
            "passed": not any(
                performance_profile[
                    "blank_non_null_counts"
                ].values()
            ),
            "observed": json.dumps(
                performance_profile[
                    "blank_non_null_counts"
                ],
                sort_keys=True,
            ),
        },
        {
            "check": (
                "SECTIONAL_REQUIRED_VALUES"
            ),
            "passed": not any(
                sectional_profile[
                    "blank_non_null_counts"
                ].values()
            ),
            "observed": json.dumps(
                sectional_profile[
                    "blank_non_null_counts"
                ],
                sort_keys=True,
            ),
        },
        {
            "check": (
                "PERFORMANCE_ID_REPRODUCIBILITY"
            ),
            "passed": (
                performance_repro[
                    "mismatch_rows"
                ]
                == 0
                and performance_repro[
                    "incomplete_natural_key_rows"
                ]
                == 0
                and performance_repro[
                    "version_mismatch_rows"
                ]
                == 0
            ),
            "observed": (
                f"reproducible="
                f"{performance_repro['reproducible_rows']};"
                f"mismatches="
                f"{performance_repro['mismatch_rows']};"
                f"incomplete="
                f"{performance_repro['incomplete_natural_key_rows']};"
                f"version_mismatches="
                f"{performance_repro['version_mismatch_rows']}"
            ),
        },
        {
            "check": (
                "SECTIONAL_ID_REPRODUCIBILITY"
            ),
            "passed": (
                sectional_repro[
                    "mismatch_rows"
                ]
                == 0
                and sectional_repro[
                    "incomplete_natural_key_rows"
                ]
                == 0
            ),
            "observed": (
                f"reproducible="
                f"{sectional_repro['reproducible_rows']};"
                f"mismatches="
                f"{sectional_repro['mismatch_rows']};"
                f"incomplete="
                f"{sectional_repro['incomplete_natural_key_rows']}"
            ),
        },
        {
            "check": (
                "SECTIONAL_PERFORMANCE_FOREIGN_KEY"
            ),
            "passed": (
                foreign_keys[
                    "missing_rows"
                ]
                == 0
            ),
            "observed": (
                f"matched="
                f"{foreign_keys['matched_rows']};"
                f"missing="
                f"{foreign_keys['missing_rows']}"
            ),
        },
        {
            "check": (
                "LEGACY_COLLISIONS_SPLIT"
            ),
            "passed": (
                collision_lineage[
                    "legacy_collision_groups"
                ]
                == 89
                and collision_lineage[
                    "incorrectly_unsplit_groups"
                ]
                == 0
            ),
            "observed": (
                f"collision_groups="
                f"{collision_lineage['legacy_collision_groups']};"
                f"correctly_split="
                f"{collision_lineage['correctly_split_groups']};"
                f"incorrectly_unsplit="
                f"{collision_lineage['incorrectly_unsplit_groups']}"
            ),
        },
        {
            "check": (
                "QUALITY_STATE_CONTRACT"
            ),
            "passed": (
                not performance_unknown
                and not sectional_unknown
            ),
            "observed": (
                f"performance_unknown="
                f"{performance_unknown};"
                f"sectional_unknown="
                f"{sectional_unknown}"
            ),
        },
    ]


def main() -> None:
    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    SNAPSHOT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    ARCH_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    performance_path = latest_file(
        PHASE102,
        (
            "edgeiq_canonical_performance_"
            "identity_v0_2_*.csv"
        ),
    )

    sectional_path = latest_file(
        PHASE102,
        (
            "edgeiq_canonical_sectional_"
            "evidence_v0_2_*.csv"
        ),
    )

    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    print(
        "PHASE1_0_3_PROFILE_PERFORMANCE_START",
        flush=True,
    )

    performance_profile = profile_asset(
        "canonical_performance_identity_v0_2",
        performance_path,
        "performance_id",
        PERFORMANCE_REQUIRED_COLUMNS,
        PERFORMANCE_NON_NULL_COLUMNS,
        "identity_quality_state",
    )

    print(
        "PHASE1_0_3_PROFILE_SECTIONAL_START",
        flush=True,
    )

    sectional_profile = profile_asset(
        "canonical_sectional_evidence_v0_2",
        sectional_path,
        "performance_sectional_id",
        SECTIONAL_REQUIRED_COLUMNS,
        SECTIONAL_NON_NULL_COLUMNS,
        "timing_quality_state",
    )

    print(
        "PHASE1_0_3_PERFORMANCE_REPRODUCIBILITY_START",
        flush=True,
    )

    performance_repro = (
        validate_performance_ids(
            performance_path
        )
    )

    print(
        "PHASE1_0_3_SECTIONAL_REPRODUCIBILITY_START",
        flush=True,
    )

    sectional_repro = (
        validate_sectional_ids(
            sectional_path
        )
    )

    print(
        "PHASE1_0_3_FOREIGN_KEY_START",
        flush=True,
    )

    foreign_keys = validate_foreign_keys(
        performance_path,
        sectional_path,
    )

    print(
        "PHASE1_0_3_COLLISION_LINEAGE_START",
        flush=True,
    )

    collision_lineage = (
        validate_legacy_collision_lineage(
            performance_path
        )
    )

    checks = make_checks(
        performance_profile,
        sectional_profile,
        performance_repro,
        sectional_repro,
        foreign_keys,
        collision_lineage,
    )

    all_passed = all(
        check["passed"]
        for check in checks
    )

    snapshot_id = stable_id(
        "warehouse_snapshot",
        (
            f"{SNAPSHOT_VERSION}|"
            f"{performance_profile['sha256']}|"
            f"{sectional_profile['sha256']}"
        ),
    )

    manifest = {
        "audit_name": (
            "EDGEiQ Performance Intelligence "
            "Phase 1.0.3 Corrected Snapshot "
            "Reproducibility Audit"
        ),
        "generated_utc": utc_now(),
        "warehouse_snapshot_id": (
            snapshot_id
        ),
        "snapshot_version": (
            SNAPSHOT_VERSION
        ),
        "audit_version": (
            AUDIT_VERSION
        ),
        "status": (
            "SNAPSHOT_REPRODUCIBILITY_PASS"
            if all_passed
            else
            "SNAPSHOT_REPRODUCIBILITY_FAIL"
        ),
        "production_data_modified": False,
        "performance_profile": (
            performance_profile
        ),
        "sectional_profile": (
            sectional_profile
        ),
        "performance_id_reproducibility": (
            performance_repro
        ),
        "sectional_id_reproducibility": (
            sectional_repro
        ),
        "foreign_key_validation": (
            foreign_keys
        ),
        "legacy_collision_lineage": (
            collision_lineage
        ),
        "audit_checks": checks,
        "failed_checks": [
            check["check"]
            for check in checks
            if not check["passed"]
        ],
        "canonical_status": (
            "SNAPSHOT_VALIDATED_NOT_PROMOTED"
            if all_passed
            else
            "SNAPSHOT_BLOCKED"
        ),
        "next_stage": (
            "Phase 1.1 immutable canonical raw "
            "performance warehouse materialisation."
            if all_passed
            else
            "Resolve Phase 1.0.3 failed checks."
        ),
    }

    manifest_path = (
        SNAPSHOT_DIR
        / (
            "edgeiq_performance_warehouse_"
            f"snapshot_manifest_v0_2_{run_id}.json"
        )
    )

    manifest_latest_path = (
        SNAPSHOT_DIR
        / (
            "edgeiq_performance_warehouse_"
            "snapshot_manifest_v0_2_latest.json"
        )
    )

    checks_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_0_3_checks_{run_id}.csv"
        )
    )

    summary_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_0_3_summary_{run_id}.json"
        )
    )

    latest_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            "phase1_0_3_latest.json"
        )
    )

    report_path = (
        AUDIT_DIR
        / (
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            f"PHASE1_0_3_REPORT_{run_id}.md"
        )
    )

    architecture_path = (
        ARCH_DIR
        / (
            "EDGEIQ_PERFORMANCE_WAREHOUSE_"
            "SNAPSHOT_GOVERNANCE_V0_2.md"
        )
    )

    write_json(
        manifest_path,
        manifest,
    )

    write_json(
        manifest_latest_path,
        manifest,
    )

    write_json(
        summary_path,
        manifest,
    )

    write_json(
        latest_path,
        manifest,
    )

    write_csv(
        checks_path,
        checks,
    )

    architecture_path.write_text(
        """# EDGEiQ Performance Warehouse Snapshot Governance V0.2

## Corrected identity foundation

Performance IDs are generated from full race context:

- race date
- jurisdiction
- track
- race number
- provider race ID
- provider runner ID
- canonical horse ID

Provider identifiers are evidence and are not assumed to be globally unique.

## Snapshot requirements

A valid snapshot must have:

- unique performance IDs
- unique sectional evidence IDs
- deterministic ID reproducibility
- complete sectional foreign keys
- preserved legacy performance IDs
- all 89 known V0.1 collisions split
- valid evidence quality states
- immutable SHA-256 asset hashes

## Promotion

A successful snapshot remains unpromoted until Phase 1.1 explicitly materialises the canonical raw warehouse.
""",
        encoding="utf-8",
    )

    report_path.write_text(
        f"""# EDGEiQ Performance Intelligence
## Phase 1.0.3 Corrected Snapshot Reproducibility Audit

Generated UTC: `{manifest['generated_utc']}`

Snapshot ID: `{snapshot_id}`

Status: **{manifest['status']}**

- Performance rows: **{performance_profile['rows']:,}**
- Unique performances: **{performance_profile['unique_performances']:,}**
- Sectional evidence rows: **{sectional_profile['rows']:,}**
- Performance ID reproducibility: **{performance_repro['reproducibility_pct']}%**
- Sectional ID reproducibility: **{sectional_repro['reproducibility_pct']}%**
- Sectional foreign-key match: **{foreign_keys['match_pct']}%**
- Legacy collision groups split: **{collision_lineage['correctly_split_groups']:,}**
- Failed checks: **{len(manifest['failed_checks'])}**

Production data was not modified.
""",
        encoding="utf-8",
    )

    if not all_passed:
        print(
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            "PHASE1_0_3_SNAPSHOT_"
            "REPRODUCIBILITY_FAIL",
            flush=True,
        )

        for failed in manifest[
            "failed_checks"
        ]:
            print(
                f"FAILED_CHECK={failed}",
                flush=True,
            )

        raise SystemExit(1)

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE1_0_3_SNAPSHOT_"
        "REPRODUCIBILITY_PASS",
        flush=True,
    )

    print(
        f"SNAPSHOT_ID={snapshot_id}",
        flush=True,
    )

    print(
        f"MANIFEST={manifest_path}",
        flush=True,
    )

    print(
        f"CHECKS={checks_path}",
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
