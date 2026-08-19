from __future__ import annotations

import csv
import hashlib
import json
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

PHASE05 = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase0_5"
)

PHASE09 = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase0_9"
)

AUDIT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase1_0"
)

ARCH_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "architecture"
    / "phase1_0"
)

SNAPSHOT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "snapshots"
    / "phase1_0"
)

EDGEIQ_NAMESPACE = uuid.UUID(
    "ed91a5d8-e8e7-5b0f-a108-cd9c41c36901"
)

SNAPSHOT_VERSION = "PERFORMANCE_WAREHOUSE_SNAPSHOT_V0_1"
AUDIT_VERSION = "PHASE1_0_REPRODUCIBILITY_AUDIT_V0_1"
PROGRESS_INTERVAL = 100_000

PERFORMANCE_REQUIRED_COLUMNS = (
    "performance_id",
    "race_id",
    "meeting_id",
    "horse_id",
    "source_evidence_id",
    "source_row_number",
    "provider_race_id",
    "provider_runner_id",
    "race_date",
    "track",
    "race_number",
    "horse_name",
    "identity_method",
    "identity_quality_state",
    "identity_version",
    "evidence_version",
    "generated_at",
)

SECTIONAL_REQUIRED_COLUMNS = (
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
)

PERFORMANCE_NON_NULL_COLUMNS = (
    "performance_id",
    "race_id",
    "meeting_id",
    "horse_id",
    "source_evidence_id",
    "source_row_number",
    "race_date",
    "track",
    "race_number",
    "horse_name",
    "identity_method",
    "identity_quality_state",
    "identity_version",
    "evidence_version",
)

SECTIONAL_NON_NULL_COLUMNS = (
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
)

ALLOWED_SECTIONAL_QUALITY_STATES = {
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

ALLOWED_IDENTITY_QUALITY_STATES = {
    "COMPLETE",
    "PARTIAL",
    "IDENTITY_UNRESOLVED",
    "SOURCE_CONFLICT",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(value: Any) -> str:
    return str(value or "").strip()


def rel(path: Path) -> str:
    return str(
        path.relative_to(ROOT)
    ).replace("\\", "/")


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


def profile_csv(
    label: str,
    path: Path,
    required_columns: tuple[str, ...],
    non_null_columns: tuple[str, ...],
    primary_key: str,
) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "label": label,
        "path": rel(path),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "modified_utc": datetime.fromtimestamp(
            path.stat().st_mtime,
            tz=timezone.utc,
        ).isoformat(),
        "rows": 0,
        "columns": [],
        "column_count": 0,
        "missing_required_columns": [],
        "duplicate_primary_key_rows": 0,
        "duplicate_primary_keys": 0,
        "blank_primary_key_rows": 0,
        "blank_non_null_counts": {},
        "min_race_date": "",
        "max_race_date": "",
        "unique_races": 0,
        "unique_horses": 0,
        "unique_performances": 0,
        "quality_state_counts": {},
        "version_counts": {},
        "error": "",
    }

    primary_keys: set[str] = set()
    duplicated_keys: set[str] = set()
    race_ids: set[str] = set()
    horse_ids: set[str] = set()
    performance_ids: set[str] = set()
    dates: list[str] = []
    blank_counts = Counter()
    quality_counts = Counter()
    version_counts = Counter()

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            errors="ignore",
            newline="",
        ) as handle:
            reader = csv.DictReader(handle)
            columns = list(reader.fieldnames or [])

            profile["columns"] = columns
            profile["column_count"] = len(columns)
            profile["missing_required_columns"] = [
                column
                for column in required_columns
                if column not in columns
            ]

            for row_number, row in enumerate(
                reader,
                start=1,
            ):
                profile["rows"] = row_number

                if (
                    row_number == 1
                    or row_number
                    % PROGRESS_INTERVAL == 0
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
                    profile[
                        "blank_primary_key_rows"
                    ] += 1
                elif key in primary_keys:
                    profile[
                        "duplicate_primary_key_rows"
                    ] += 1
                    duplicated_keys.add(key)
                else:
                    primary_keys.add(key)

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
                race_date = clean(
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

                quality_state = clean(
                    row.get(
                        "timing_quality_state"
                    )
                    or row.get(
                        "identity_quality_state"
                    )
                )

                if quality_state:
                    quality_counts[
                        quality_state
                    ] += 1

                for version_column in (
                    "identity_version",
                    "linkage_version",
                    "migration_version",
                    "evidence_version",
                ):
                    value = clean(
                        row.get(version_column)
                    )

                    if value:
                        version_counts[
                            (
                                f"{version_column}"
                                f"={value}"
                            )
                        ] += 1

        profile["duplicate_primary_keys"] = len(
            duplicated_keys
        )
        profile["blank_non_null_counts"] = dict(
            sorted(blank_counts.items())
        )
        profile["unique_races"] = len(
            race_ids
        )
        profile["unique_horses"] = len(
            horse_ids
        )
        profile["unique_performances"] = len(
            performance_ids
        )
        profile["quality_state_counts"] = dict(
            sorted(quality_counts.items())
        )
        profile["version_counts"] = dict(
            sorted(version_counts.items())
        )

        if dates:
            profile["min_race_date"] = min(
                dates
            )
            profile["max_race_date"] = max(
                dates
            )

    except Exception as exc:
        profile["error"] = str(exc)

    return profile


def validate_performance_id_reproducibility(
    performance_path: Path,
) -> dict[str, Any]:
    rows_checked = 0
    reproducible_rows = 0
    mismatch_rows = 0
    unresolved_natural_key_rows = 0
    mismatch_samples: list[
        dict[str, Any]
    ] = []

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
            rows_checked += 1

            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL == 0
            ):
                print(
                    "PERFORMANCE_ID_REPROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            performance_id = clean(
                row.get("performance_id")
            )
            race_id = clean(
                row.get("race_id")
            )
            horse_id = clean(
                row.get("horse_id")
            )

            if not race_id or not horse_id:
                unresolved_natural_key_rows += 1
                continue

            reproduced = stable_id(
                "performance",
                f"{race_id}|{horse_id}",
            )

            if reproduced == performance_id:
                reproducible_rows += 1
            else:
                mismatch_rows += 1

                if len(mismatch_samples) < 100:
                    mismatch_samples.append(
                        {
                            "source_row": row_number,
                            "stored_performance_id": (
                                performance_id
                            ),
                            "reproduced_performance_id": (
                                reproduced
                            ),
                            "race_id": race_id,
                            "horse_id": horse_id,
                        }
                    )

    return {
        "rows_checked": rows_checked,
        "reproducible_rows": (
            reproducible_rows
        ),
        "mismatch_rows": mismatch_rows,
        "unresolved_natural_key_rows": (
            unresolved_natural_key_rows
        ),
        "reproducibility_pct": (
            round(
                reproducible_rows
                / rows_checked
                * 100,
                6,
            )
            if rows_checked
            else 0.0
        ),
        "mismatch_samples": (
            mismatch_samples
        ),
    }


def validate_sectional_id_reproducibility(
    sectional_path: Path,
) -> dict[str, Any]:
    rows_checked = 0
    reproducible_rows = 0
    mismatch_rows = 0
    unresolved_natural_key_rows = 0
    source_hash_mismatch_rows = 0
    source_hash_values: set[str] = set()
    source_evidence_ids: set[str] = set()
    mismatch_samples: list[
        dict[str, Any]
    ] = []

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
            rows_checked += 1

            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL == 0
            ):
                print(
                    "SECTIONAL_ID_REPROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            stored_id = clean(
                row.get(
                    "performance_sectional_id"
                )
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
            source_hash = clean(
                row.get("source_sha256")
            )

            if source_hash:
                source_hash_values.add(
                    source_hash
                )

            if source_evidence_id:
                source_evidence_ids.add(
                    source_evidence_id
                )

            if (
                not performance_id
                or not source_evidence_id
                or not source_row_number
            ):
                unresolved_natural_key_rows += 1
                continue

            reproduced = stable_id(
                "performance_sectional",
                (
                    f"{performance_id}|"
                    f"{source_evidence_id}|"
                    f"{source_row_number}"
                ),
            )

            if reproduced == stored_id:
                reproducible_rows += 1
            else:
                mismatch_rows += 1

                if len(mismatch_samples) < 100:
                    mismatch_samples.append(
                        {
                            "source_row": row_number,
                            "stored_id": stored_id,
                            "reproduced_id": (
                                reproduced
                            ),
                            "performance_id": (
                                performance_id
                            ),
                            "source_evidence_id": (
                                source_evidence_id
                            ),
                            "source_row_number": (
                                source_row_number
                            ),
                        }
                    )

    actual_source_hash = sha256_file(
        ROOT
        / "public"
        / "data"
        / "racingcom_sectional_warehouse_v2.csv"
    )

    for source_hash in source_hash_values:
        if source_hash != actual_source_hash:
            source_hash_mismatch_rows += 1

    return {
        "rows_checked": rows_checked,
        "reproducible_rows": (
            reproducible_rows
        ),
        "mismatch_rows": mismatch_rows,
        "unresolved_natural_key_rows": (
            unresolved_natural_key_rows
        ),
        "reproducibility_pct": (
            round(
                reproducible_rows
                / rows_checked
                * 100,
                6,
            )
            if rows_checked
            else 0.0
        ),
        "distinct_source_hashes": sorted(
            source_hash_values
        ),
        "actual_source_hash": (
            actual_source_hash
        ),
        "source_hash_mismatch_values": (
            source_hash_mismatch_rows
        ),
        "distinct_source_evidence_ids": (
            sorted(
                source_evidence_ids
            )
        ),
        "mismatch_samples": (
            mismatch_samples
        ),
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
                % PROGRESS_INTERVAL == 0
            ):
                print(
                    "FOREIGN_KEY_PARENT_PROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            performance_id = clean(
                row.get("performance_id")
            )

            if performance_id:
                performance_ids.add(
                    performance_id
                )

    sectional_rows = 0
    matched_rows = 0
    missing_rows = 0
    missing_ids: Counter[str] = Counter()

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
            sectional_rows += 1

            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL == 0
            ):
                print(
                    "FOREIGN_KEY_CHILD_PROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            performance_id = clean(
                row.get("performance_id")
            )

            if (
                performance_id
                in performance_ids
            ):
                matched_rows += 1
            else:
                missing_rows += 1
                missing_ids[
                    performance_id
                    or "<BLANK>"
                ] += 1

    return {
        "parent_performance_ids": len(
            performance_ids
        ),
        "sectional_rows": sectional_rows,
        "matched_rows": matched_rows,
        "missing_rows": missing_rows,
        "foreign_key_match_pct": (
            round(
                matched_rows
                / sectional_rows
                * 100,
                6,
            )
            if sectional_rows
            else 0.0
        ),
        "missing_id_samples": [
            {
                "performance_id": key,
                "rows": value,
            }
            for key, value
            in missing_ids.most_common(100)
        ],
    }


def validate_quality_states(
    performance_profile: dict[str, Any],
    sectional_profile: dict[str, Any],
) -> dict[str, Any]:
    performance_unknown = [
        state
        for state
        in performance_profile[
            "quality_state_counts"
        ]
        if state
        not in ALLOWED_IDENTITY_QUALITY_STATES
    ]

    sectional_unknown = [
        state
        for state
        in sectional_profile[
            "quality_state_counts"
        ]
        if state
        not in ALLOWED_SECTIONAL_QUALITY_STATES
    ]

    return {
        "performance_unknown_states": (
            performance_unknown
        ),
        "sectional_unknown_states": (
            sectional_unknown
        ),
        "status": (
            "PASS"
            if (
                not performance_unknown
                and not sectional_unknown
            )
            else "FAIL"
        ),
    }


def build_snapshot_id(
    performance_hash: str,
    sectional_hash: str,
) -> str:
    natural_key = (
        f"{SNAPSHOT_VERSION}|"
        f"{performance_hash}|"
        f"{sectional_hash}"
    )

    return stable_id(
        "warehouse_snapshot",
        natural_key,
    )


def audit_checks(
    performance_profile: dict[str, Any],
    sectional_profile: dict[str, Any],
    performance_repro: dict[str, Any],
    sectional_repro: dict[str, Any],
    foreign_keys: dict[str, Any],
    quality_validation: dict[str, Any],
) -> list[dict[str, Any]]:
    checks = [
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
            "check": "PERFORMANCE_PRIMARY_KEY_UNIQUE",
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
            "check": "SECTIONAL_PRIMARY_KEY_UNIQUE",
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
            "check": "PERFORMANCE_REQUIRED_VALUES",
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
            "check": "SECTIONAL_REQUIRED_VALUES",
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
            "check": "PERFORMANCE_ID_REPRODUCIBILITY",
            "passed": (
                performance_repro[
                    "mismatch_rows"
                ]
                == 0
                and performance_repro[
                    "unresolved_natural_key_rows"
                ]
                == 0
            ),
            "observed": (
                f"reproducible="
                f"{performance_repro['reproducible_rows']};"
                f"mismatches="
                f"{performance_repro['mismatch_rows']};"
                f"unresolved="
                f"{performance_repro['unresolved_natural_key_rows']}"
            ),
        },
        {
            "check": "SECTIONAL_ID_REPRODUCIBILITY",
            "passed": (
                sectional_repro[
                    "mismatch_rows"
                ]
                == 0
                and sectional_repro[
                    "unresolved_natural_key_rows"
                ]
                == 0
            ),
            "observed": (
                f"reproducible="
                f"{sectional_repro['reproducible_rows']};"
                f"mismatches="
                f"{sectional_repro['mismatch_rows']};"
                f"unresolved="
                f"{sectional_repro['unresolved_natural_key_rows']}"
            ),
        },
        {
            "check": "SOURCE_HASH_REPRODUCIBILITY",
            "passed": (
                sectional_repro[
                    "source_hash_mismatch_values"
                ]
                == 0
            ),
            "observed": (
                f"stored="
                f"{' | '.join(sectional_repro['distinct_source_hashes'])};"
                f"actual="
                f"{sectional_repro['actual_source_hash']}"
            ),
        },
        {
            "check": "SECTIONAL_PERFORMANCE_FOREIGN_KEY",
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
            "check": "QUALITY_STATE_CONTRACT",
            "passed": (
                quality_validation[
                    "status"
                ]
                == "PASS"
            ),
            "observed": json.dumps(
                quality_validation,
                sort_keys=True,
            ),
        },
    ]

    return checks


def architecture_markdown() -> str:
    return """# EDGEiQ Performance Warehouse Snapshot Governance V0.1

## Snapshot identity

A warehouse snapshot receives one deterministic `warehouse_snapshot_id`.

The natural key contains:

- snapshot specification version
- canonical performance identity file SHA-256
- canonical sectional evidence file SHA-256

Any byte-level change creates a different snapshot identity.

## Mandatory snapshot manifest

Every snapshot records:

- snapshot ID
- source file paths
- source SHA-256 values
- row counts
- schema columns
- date coverage
- primary-key results
- foreign-key results
- deterministic-ID results
- quality-state contract results
- audit version
- generated timestamp

## Promotion rule

A snapshot cannot be promoted when any mandatory audit check fails.

## Immutability

Existing snapshot manifests are never overwritten.

A new source or engine run creates a new snapshot manifest.

## Product separation

This snapshot is not a React feed.

React and application services must consume governed query products built downstream from canonical evidence.
"""


def markdown_report(
    summary: dict[str, Any],
) -> str:
    checks = summary[
        "audit_checks"
    ]

    lines = [
        "# EDGEiQ Performance Intelligence",
        "## Phase 1.0 Raw Warehouse Snapshot and Reproducibility Audit",
        "",
        f"Generated UTC: `{summary['generated_utc']}`",
        "",
        f"Snapshot ID: `{summary['warehouse_snapshot_id']}`",
        "",
        f"Status: **{summary['status']}**",
        "",
        "## Snapshot assets",
        "",
        f"- Canonical performances: **{summary['performance_profile']['rows']:,}**",
        f"- Canonical sectional evidence: **{summary['sectional_profile']['rows']:,}**",
        f"- Performance date coverage: **{summary['performance_profile']['min_race_date']} to {summary['performance_profile']['max_race_date']}**",
        f"- Sectional date coverage: **{summary['sectional_profile']['min_race_date']} to {summary['sectional_profile']['max_race_date']}**",
        "",
        "## Mandatory checks",
        "",
        "| Check | Passed | Observed |",
        "|---|---|---|",
    ]

    for check in checks:
        lines.append(
            f"| {check['check']} | "
            f"{check['passed']} | "
            f"{check['observed']} |"
        )

    lines.extend(
        [
            "",
            "## Production state",
            "",
            "Production data was not modified.",
            "",
            "This snapshot remains a governed prototype until an explicit promotion phase passes.",
            "",
        ]
    )

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
    SNAPSHOT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    performance_path = latest_file(
        PHASE05,
        (
            "edgeiq_canonical_performance_"
            "identity_prototype_v0_1_*.csv"
        ),
    )

    sectional_path = latest_file(
        PHASE09,
        (
            "edgeiq_canonical_sectional_"
            "evidence_v0_1_*.csv"
        ),
    )

    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    print(
        "PHASE1_0_PROFILE_PERFORMANCE_START",
        flush=True,
    )

    performance_profile = profile_csv(
        "canonical_performance_identity",
        performance_path,
        PERFORMANCE_REQUIRED_COLUMNS,
        PERFORMANCE_NON_NULL_COLUMNS,
        "performance_id",
    )

    print(
        "PHASE1_0_PROFILE_SECTIONAL_START",
        flush=True,
    )

    sectional_profile = profile_csv(
        "canonical_sectional_evidence",
        sectional_path,
        SECTIONAL_REQUIRED_COLUMNS,
        SECTIONAL_NON_NULL_COLUMNS,
        "performance_sectional_id",
    )

    print(
        "PHASE1_0_PERFORMANCE_REPRODUCIBILITY_START",
        flush=True,
    )

    performance_repro = (
        validate_performance_id_reproducibility(
            performance_path
        )
    )

    print(
        "PHASE1_0_SECTIONAL_REPRODUCIBILITY_START",
        flush=True,
    )

    sectional_repro = (
        validate_sectional_id_reproducibility(
            sectional_path
        )
    )

    print(
        "PHASE1_0_FOREIGN_KEY_AUDIT_START",
        flush=True,
    )

    foreign_keys = validate_foreign_keys(
        performance_path,
        sectional_path,
    )

    quality_validation = (
        validate_quality_states(
            performance_profile,
            sectional_profile,
        )
    )

    checks = audit_checks(
        performance_profile,
        sectional_profile,
        performance_repro,
        sectional_repro,
        foreign_keys,
        quality_validation,
    )

    all_passed = all(
        check["passed"]
        for check in checks
    )

    snapshot_id = build_snapshot_id(
        performance_profile["sha256"],
        sectional_profile["sha256"],
    )

    manifest = {
        "warehouse_snapshot_id": (
            snapshot_id
        ),
        "snapshot_version": (
            SNAPSHOT_VERSION
        ),
        "audit_version": (
            AUDIT_VERSION
        ),
        "generated_utc": utc_now(),
        "production_data_modified": False,
        "status": (
            "SNAPSHOT_REPRODUCIBILITY_PASS"
            if all_passed
            else "SNAPSHOT_REPRODUCIBILITY_FAIL"
        ),
        "performance_asset": {
            "path": rel(
                performance_path
            ),
            "sha256": (
                performance_profile[
                    "sha256"
                ]
            ),
            "rows": (
                performance_profile[
                    "rows"
                ]
            ),
        },
        "sectional_asset": {
            "path": rel(
                sectional_path
            ),
            "sha256": (
                sectional_profile[
                    "sha256"
                ]
            ),
            "rows": (
                sectional_profile[
                    "rows"
                ]
            ),
        },
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
        "quality_state_validation": (
            quality_validation
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
            else "SNAPSHOT_BLOCKED"
        ),
        "next_stage": (
            "Phase 1.1 canonical raw performance "
            "evidence migration and immutable "
            "warehouse materialisation"
            if all_passed
            else
            "Resolve Phase 1.0 failed checks "
            "before warehouse materialisation"
        ),
    }

    manifest_path = (
        SNAPSHOT_DIR
        / f"edgeiq_performance_warehouse_snapshot_manifest_v0_1_{run_id}.json"
    )

    manifest_latest_path = (
        SNAPSHOT_DIR
        / "edgeiq_performance_warehouse_snapshot_manifest_v0_1_latest.json"
    )

    checks_path = (
        AUDIT_DIR
        / f"edgeiq_performance_intelligence_phase1_0_checks_{run_id}.csv"
    )

    summary_path = (
        AUDIT_DIR
        / f"edgeiq_performance_intelligence_phase1_0_summary_{run_id}.json"
    )

    latest_path = (
        AUDIT_DIR
        / "edgeiq_performance_intelligence_phase1_0_latest.json"
    )

    report_path = (
        AUDIT_DIR
        / f"EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE1_0_REPORT_{run_id}.md"
    )

    architecture_path = (
        ARCH_DIR
        / "EDGEIQ_PERFORMANCE_WAREHOUSE_SNAPSHOT_GOVERNANCE_V0_1.md"
    )

    write_json(
        manifest_path,
        manifest,
    )

    write_json(
        manifest_latest_path,
        manifest,
    )

    write_csv(
        checks_path,
        checks,
    )

    write_json(
        summary_path,
        manifest,
    )

    write_json(
        latest_path,
        manifest,
    )

    architecture_path.write_text(
        architecture_markdown(),
        encoding="utf-8",
    )

    report_path.write_text(
        markdown_report(manifest),
        encoding="utf-8",
    )

    if not all_passed:
        print(
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            "PHASE1_0_SNAPSHOT_REPRODUCIBILITY_FAIL",
            flush=True,
        )

        for failed_check in (
            manifest["failed_checks"]
        ):
            print(
                f"FAILED_CHECK={failed_check}",
                flush=True,
            )

        raise SystemExit(1)

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE1_0_SNAPSHOT_REPRODUCIBILITY_PASS",
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
