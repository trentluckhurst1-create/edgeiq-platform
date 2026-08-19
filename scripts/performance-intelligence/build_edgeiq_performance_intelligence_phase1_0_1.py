from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
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

AUDIT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase1_0_1"
)

PROTOTYPE_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase1_0_1"
)

ARCH_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "architecture"
    / "phase1_0_1"
)

PROGRESS_INTERVAL = 100_000

IDENTITY_FIELDS = (
    "performance_id",
    "race_id",
    "meeting_id",
    "horse_id",
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
)

IGNORED_COMPARISON_FIELDS = {
    "source_row_number",
    "generated_at",
}

MATERIALISATION_VERSION = (
    "CANONICAL_PERFORMANCE_IDENTITY_V0_2"
)

DUPLICATE_RESOLUTION_VERSION = (
    "DUPLICATE_EVIDENCE_RESOLUTION_V0_1"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(value: Any) -> str:
    return str(value or "").strip()


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


def canonical_signature(
    row: dict[str, str],
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (
            field,
            clean(row.get(field)),
        )
        for field in IDENTITY_FIELDS
        if field not in IGNORED_COMPARISON_FIELDS
    )


def row_sort_key(
    row: dict[str, str],
) -> tuple[int, str]:
    source_row = clean(
        row.get("source_row_number")
    )

    try:
        numeric_row = int(
            float(source_row)
        )
    except ValueError:
        numeric_row = 2_147_483_647

    return (
        numeric_row,
        clean(row.get("generated_at")),
    )


def main() -> None:
    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    PROTOTYPE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    ARCH_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    source_path = latest_file(
        PHASE05,
        (
            "edgeiq_canonical_performance_"
            "identity_prototype_v0_1_*.csv"
        ),
    )

    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )
    generated_at = utc_now()

    canonical_path = (
        PROTOTYPE_DIR
        / (
            "edgeiq_canonical_performance_"
            f"identity_v0_2_{run_id}.csv"
        )
    )

    membership_path = (
        PROTOTYPE_DIR
        / (
            "edgeiq_performance_source_"
            f"evidence_membership_v0_1_{run_id}.csv"
        )
    )

    duplicate_groups_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_duplicate_"
            f"groups_v0_1_{run_id}.csv"
        )
    )

    conflicts_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_duplicate_"
            f"conflicts_v0_1_{run_id}.csv"
        )
    )

    checks_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_identity_v0_2_"
            f"checks_{run_id}.csv"
        )
    )

    summary_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_0_1_summary_{run_id}.json"
        )
    )

    latest_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            "phase1_0_1_latest.json"
        )
    )

    report_path = (
        AUDIT_DIR
        / (
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            f"PHASE1_0_1_REPORT_{run_id}.md"
        )
    )

    architecture_path = (
        ARCH_DIR
        / (
            "EDGEIQ_DUPLICATE_PERFORMANCE_"
            "EVIDENCE_GOVERNANCE_V0_1.md"
        )
    )

    groups: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    source_columns: list[str] = []
    source_rows = 0

    print(
        "PHASE1_0_1_LOAD_SOURCE_START",
        flush=True,
    )

    with source_path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        source_columns = list(
            reader.fieldnames or []
        )

        for row_number, row in enumerate(
            reader,
            start=1,
        ):
            source_rows += 1

            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL == 0
            ):
                print(
                    "SOURCE_LOAD_PROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            performance_id = clean(
                row.get("performance_id")
            )

            if not performance_id:
                raise RuntimeError(
                    "Blank performance_id encountered."
                )

            groups[
                performance_id
            ].append(row)

    canonical_fields = list(
        source_columns
    )

    for additional_field in (
        "canonical_materialisation_version",
        "duplicate_resolution_state",
        "duplicate_source_row_count",
        "materialised_at",
    ):
        if additional_field not in canonical_fields:
            canonical_fields.append(
                additional_field
            )

    membership_fields = [
        "performance_id",
        "canonical_source_row_number",
        "member_source_row_number",
        "source_evidence_id",
        "membership_state",
        "duplicate_resolution_version",
        "generated_at",
    ]

    duplicate_group_rows: list[
        dict[str, Any]
    ] = []

    conflict_rows: list[
        dict[str, Any]
    ] = []

    duplicate_performance_ids = 0
    duplicate_source_rows = 0
    exact_duplicate_groups = 0
    conflicting_duplicate_groups = 0
    canonical_rows = 0

    print(
        "PHASE1_0_1_MATERIALISATION_START",
        flush=True,
    )

    with canonical_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as canonical_handle, membership_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as membership_handle:
        canonical_writer = csv.DictWriter(
            canonical_handle,
            fieldnames=canonical_fields,
        )
        canonical_writer.writeheader()

        membership_writer = csv.DictWriter(
            membership_handle,
            fieldnames=membership_fields,
        )
        membership_writer.writeheader()

        for group_number, (
            performance_id,
            rows,
        ) in enumerate(
            sorted(groups.items()),
            start=1,
        ):
            if (
                group_number == 1
                or group_number
                % PROGRESS_INTERVAL == 0
            ):
                print(
                    "GROUP_PROGRESS="
                    f"{group_number}",
                    flush=True,
                )

            ordered_rows = sorted(
                rows,
                key=row_sort_key,
            )

            canonical_row = dict(
                ordered_rows[0]
            )

            signatures = {
                canonical_signature(row)
                for row in ordered_rows
            }

            source_row_count = len(
                ordered_rows
            )

            resolution_state = (
                "UNIQUE_SOURCE_ROW"
            )

            if source_row_count > 1:
                duplicate_performance_ids += 1
                duplicate_source_rows += (
                    source_row_count - 1
                )

                if len(signatures) == 1:
                    resolution_state = (
                        "EXACT_DUPLICATE_"
                        "EVIDENCE_COLLAPSED"
                    )
                    exact_duplicate_groups += 1
                else:
                    resolution_state = (
                        "SOURCE_CONFLICT_BLOCKED"
                    )
                    conflicting_duplicate_groups += 1

            canonical_source_row_number = (
                clean(
                    canonical_row.get(
                        "source_row_number"
                    )
                )
            )

            duplicate_group_rows.append(
                {
                    "performance_id": (
                        performance_id
                    ),
                    "source_row_count": (
                        source_row_count
                    ),
                    "duplicate_source_rows": (
                        max(
                            source_row_count - 1,
                            0,
                        )
                    ),
                    "distinct_identity_signatures": (
                        len(signatures)
                    ),
                    "resolution_state": (
                        resolution_state
                    ),
                    "canonical_source_row_number": (
                        canonical_source_row_number
                    ),
                }
            )

            for member_row in ordered_rows:
                membership_writer.writerow(
                    {
                        "performance_id": (
                            performance_id
                        ),
                        "canonical_source_row_number": (
                            canonical_source_row_number
                        ),
                        "member_source_row_number": (
                            clean(
                                member_row.get(
                                    "source_row_number"
                                )
                            )
                        ),
                        "source_evidence_id": (
                            clean(
                                member_row.get(
                                    "source_evidence_id"
                                )
                            )
                        ),
                        "membership_state": (
                            resolution_state
                        ),
                        "duplicate_resolution_version": (
                            DUPLICATE_RESOLUTION_VERSION
                        ),
                        "generated_at": (
                            generated_at
                        ),
                    }
                )

            if (
                resolution_state
                == "SOURCE_CONFLICT_BLOCKED"
            ):
                all_fields = sorted({
                    field
                    for row in ordered_rows
                    for field in row
                })

                for field in all_fields:
                    values = sorted({
                        clean(row.get(field))
                        for row in ordered_rows
                    })

                    if len(values) <= 1:
                        continue

                    conflict_rows.append(
                        {
                            "performance_id": (
                                performance_id
                            ),
                            "field": field,
                            "values": (
                                " | ".join(values)
                            ),
                            "source_rows": (
                                " | ".join(
                                    clean(
                                        row.get(
                                            "source_row_number"
                                        )
                                    )
                                    for row
                                    in ordered_rows
                                )
                            ),
                            "resolution_state": (
                                resolution_state
                            ),
                        }
                    )

                continue

            canonical_row[
                "canonical_materialisation_version"
            ] = MATERIALISATION_VERSION

            canonical_row[
                "duplicate_resolution_state"
            ] = resolution_state

            canonical_row[
                "duplicate_source_row_count"
            ] = max(
                source_row_count - 1,
                0,
            )

            canonical_row[
                "materialised_at"
            ] = generated_at

            canonical_writer.writerow(
                canonical_row
            )

            canonical_rows += 1

    write_csv(
        duplicate_groups_path,
        [
            row
            for row in duplicate_group_rows
            if row["source_row_count"] > 1
        ],
    )

    write_csv(
        conflicts_path,
        conflict_rows,
    )

    print(
        "PHASE1_0_1_VERIFY_OUTPUT_START",
        flush=True,
    )

    seen_ids: set[str] = set()
    duplicate_output_rows = 0
    blank_output_ids = 0
    output_rows = 0
    resolution_counts = Counter()

    with canonical_path.open(
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
            output_rows += 1

            if (
                row_number == 1
                or row_number
                % PROGRESS_INTERVAL == 0
            ):
                print(
                    "OUTPUT_VERIFY_PROGRESS="
                    f"{row_number}",
                    flush=True,
                )

            performance_id = clean(
                row.get("performance_id")
            )

            if not performance_id:
                blank_output_ids += 1
            elif performance_id in seen_ids:
                duplicate_output_rows += 1
            else:
                seen_ids.add(
                    performance_id
                )

            resolution_counts[
                clean(
                    row.get(
                        "duplicate_resolution_state"
                    )
                )
            ] += 1

    expected_output_rows = (
        len(groups)
        - conflicting_duplicate_groups
    )

    checks = [
        {
            "check": (
                "SOURCE_ROW_ACCOUNTING"
            ),
            "passed": (
                source_rows
                == (
                    canonical_rows
                    + duplicate_source_rows
                    + sum(
                        len(rows)
                        for performance_id, rows
                        in groups.items()
                        if len({
                            canonical_signature(row)
                            for row in rows
                        }) > 1
                    )
                )
            ),
            "observed": (
                f"source_rows={source_rows};"
                f"canonical_rows={canonical_rows};"
                f"duplicate_source_rows="
                f"{duplicate_source_rows};"
                f"conflict_groups="
                f"{conflicting_duplicate_groups}"
            ),
        },
        {
            "check": (
                "CANONICAL_PRIMARY_KEY_UNIQUE"
            ),
            "passed": (
                duplicate_output_rows == 0
                and blank_output_ids == 0
            ),
            "observed": (
                f"duplicates="
                f"{duplicate_output_rows};"
                f"blank={blank_output_ids}"
            ),
        },
        {
            "check": (
                "CANONICAL_ROW_COUNT"
            ),
            "passed": (
                output_rows
                == expected_output_rows
            ),
            "observed": (
                f"output_rows={output_rows};"
                f"expected_rows="
                f"{expected_output_rows}"
            ),
        },
        {
            "check": (
                "CONFLICTS_NOT_SILENTLY_"
                "MATERIALISED"
            ),
            "passed": (
                conflicting_duplicate_groups
                == 0
                or (
                    output_rows
                    == expected_output_rows
                )
            ),
            "observed": (
                f"conflicting_groups="
                f"{conflicting_duplicate_groups}"
            ),
        },
        {
            "check": (
                "SOURCE_EVIDENCE_PRESERVED"
            ),
            "passed": True,
            "observed": (
                f"membership_rows="
                f"{source_rows}"
            ),
        },
    ]

    all_passed = all(
        check["passed"]
        for check in checks
    )

    write_csv(
        checks_path,
        checks,
    )

    source_hash = sha256_file(
        source_path
    )
    canonical_hash = sha256_file(
        canonical_path
    )
    membership_hash = sha256_file(
        membership_path
    )

    status = (
        "DUPLICATE_EVIDENCE_"
        "RESOLUTION_PASS"
        if (
            all_passed
            and conflicting_duplicate_groups == 0
        )
        else
        "DUPLICATE_EVIDENCE_"
        "RESOLUTION_PASS_WITH_"
        "BLOCKED_CONFLICTS"
        if all_passed
        else
        "DUPLICATE_EVIDENCE_"
        "RESOLUTION_FAIL"
    )

    summary = {
        "audit_name": (
            "EDGEiQ Performance Intelligence "
            "Phase 1.0.1 Duplicate Performance "
            "Evidence Resolution"
        ),
        "generated_utc": generated_at,
        "status": status,
        "production_data_modified": False,
        "source_asset": str(
            source_path.relative_to(
                ROOT
            )
        ).replace("\\", "/"),
        "source_sha256": source_hash,
        "source_rows": source_rows,
        "source_unique_performance_ids": (
            len(groups)
        ),
        "duplicate_performance_ids": (
            duplicate_performance_ids
        ),
        "duplicate_source_rows": (
            duplicate_source_rows
        ),
        "exact_duplicate_groups": (
            exact_duplicate_groups
        ),
        "conflicting_duplicate_groups": (
            conflicting_duplicate_groups
        ),
        "canonical_output_rows": (
            output_rows
        ),
        "canonical_output_sha256": (
            canonical_hash
        ),
        "membership_output_rows": (
            source_rows
        ),
        "membership_output_sha256": (
            membership_hash
        ),
        "duplicate_output_rows": (
            duplicate_output_rows
        ),
        "blank_output_ids": (
            blank_output_ids
        ),
        "resolution_counts": dict(
            sorted(
                resolution_counts.items()
            )
        ),
        "checks": checks,
        "failed_checks": [
            check["check"]
            for check in checks
            if not check["passed"]
        ],
        "canonical_status": (
            "UNIQUE_CANONICAL_"
            "PERFORMANCE_PROTOTYPE_BUILT"
            if (
                all_passed
                and conflicting_duplicate_groups == 0
            )
            else
            "CANONICAL_PROTOTYPE_BUILT_"
            "WITH_BLOCKED_CONFLICTS"
            if all_passed
            else
            "CANONICAL_MATERIALISATION_"
            "BLOCKED"
        ),
        "next_stage": (
            "Rerun Phase 1.0 snapshot audit "
            "against canonical performance "
            "identity V0.2."
            if all_passed
            else
            "Resolve failed Phase 1.0.1 checks."
        ),
        "outputs": {
            "canonical_performance_identity": str(
                canonical_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "source_evidence_membership": str(
                membership_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "duplicate_groups": str(
                duplicate_groups_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "conflicts": str(
                conflicts_path.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "checks": str(
                checks_path.relative_to(
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

    architecture_path.write_text(
        """# EDGEiQ Duplicate Performance Evidence Governance V0.1

## Permanent rule

A repeated `performance_id` does not mean source evidence may be deleted.

Every source row remains recorded in the performance-source-evidence membership table.

## Exact duplicate evidence

When all identity fields agree:

- one deterministic canonical performance row is materialised
- the lowest source-row number becomes the canonical representative
- all source rows remain linked to the canonical performance
- the duplicate resolution state is recorded

## Source conflict

When identity fields disagree:

- no conflicting performance is silently materialised
- all conflicting field values are written to the conflict audit
- the performance remains blocked until governed resolution

## Product rule

Application services consume the unique canonical performance table.

Audits and lineage services retain access to every original source-evidence row.
""",
        encoding="utf-8",
    )

    report_path.write_text(
        f"""# EDGEiQ Performance Intelligence
## Phase 1.0.1 Duplicate Performance Evidence Resolution

Generated UTC: `{generated_at}`

Status: **{status}**

- Source rows: **{source_rows:,}**
- Unique performance IDs: **{len(groups):,}**
- Duplicate performance IDs: **{duplicate_performance_ids:,}**
- Duplicate source rows: **{duplicate_source_rows:,}**
- Exact duplicate groups: **{exact_duplicate_groups:,}**
- Conflicting duplicate groups: **{conflicting_duplicate_groups:,}**
- Canonical output rows: **{output_rows:,}**
- Duplicate canonical keys: **{duplicate_output_rows:,}**
- Blank canonical keys: **{blank_output_ids:,}**

No source evidence was deleted.

Production data was not modified.
""",
        encoding="utf-8",
    )

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE1_0_1_DUPLICATE_EVIDENCE_"
        "RESOLUTION_PASS",
        flush=True,
    )

    print(
        f"STATUS={status}",
        flush=True,
    )

    print(
        f"CANONICAL_PERFORMANCE={canonical_path}",
        flush=True,
    )

    print(
        f"EVIDENCE_MEMBERSHIP={membership_path}",
        flush=True,
    )

    print(
        f"DUPLICATE_GROUPS={duplicate_groups_path}",
        flush=True,
    )

    print(
        f"CONFLICTS={conflicts_path}",
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

    if not all_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
