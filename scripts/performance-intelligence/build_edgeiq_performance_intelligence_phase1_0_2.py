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
    / "phase1_0_2"
)

PROTOTYPE_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "prototypes"
    / "phase1_0_2"
)

ARCH_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "architecture"
    / "phase1_0_2"
)

EDGEIQ_NAMESPACE = uuid.UUID(
    "ed91a5d8-e8e7-5b0f-a108-cd9c41c36901"
)

IDENTITY_VERSION = (
    "PERFORMANCE_IDENTITY_V0_2_"
    "FULL_RACE_CONTEXT"
)

REMAP_VERSION = (
    "LEGACY_PERFORMANCE_ID_REMAP_V0_1"
)

PROGRESS_INTERVAL = 100_000


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
    race_date = normalise_date(
        row.get("race_date")
    )
    state = normalise_text(
        row.get("state")
    )
    track = normalise_text(
        row.get("track")
    )
    race_number = normalise_integer(
        row.get("race_number")
    )
    provider_race_id = clean(
        row.get("provider_race_id")
    )
    provider_runner_id = clean(
        row.get("provider_runner_id")
    )
    horse_id = clean(
        row.get("horse_id")
    )

    components = (
        race_date,
        state,
        track,
        race_number,
        provider_race_id,
        provider_runner_id,
        horse_id,
    )

    if not all(components):
        raise RuntimeError(
            "Incomplete performance natural key: "
            + repr(components)
        )

    return "|".join(components)


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

    source_performance = latest_file(
        PHASE05,
        (
            "edgeiq_canonical_performance_"
            "identity_prototype_v0_1_*.csv"
        ),
    )

    source_sectional = latest_file(
        PHASE09,
        (
            "edgeiq_canonical_sectional_"
            "evidence_v0_1_*.csv"
        ),
    )

    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )
    generated_at = utc_now()

    performance_output = (
        PROTOTYPE_DIR
        / (
            "edgeiq_canonical_performance_"
            f"identity_v0_2_{run_id}.csv"
        )
    )

    remap_output = (
        PROTOTYPE_DIR
        / (
            "edgeiq_legacy_performance_id_"
            f"remap_v0_1_{run_id}.csv"
        )
    )

    sectional_output = (
        PROTOTYPE_DIR
        / (
            "edgeiq_canonical_sectional_"
            f"evidence_v0_2_{run_id}.csv"
        )
    )

    collision_output = (
        AUDIT_DIR
        / (
            "edgeiq_performance_identity_"
            f"collisions_v0_2_{run_id}.csv"
        )
    )

    checks_output = (
        AUDIT_DIR
        / (
            "edgeiq_performance_identity_"
            f"v0_2_checks_{run_id}.csv"
        )
    )

    summary_output = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_0_2_summary_{run_id}.json"
        )
    )

    latest_output = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            "phase1_0_2_latest.json"
        )
    )

    report_output = (
        AUDIT_DIR
        / (
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            f"PHASE1_0_2_REPORT_{run_id}.md"
        )
    )

    architecture_output = (
        ARCH_DIR
        / (
            "EDGEIQ_PERFORMANCE_IDENTITY_"
            "NATURAL_KEY_V0_2.md"
        )
    )

    old_to_new: dict[
        tuple[str, str],
        str,
    ] = {}

    legacy_to_new_ids: dict[
        str,
        set[str],
    ] = {}

    new_ids: set[str] = set()
    duplicate_new_ids = 0
    source_rows = 0

    print(
        "PHASE1_0_2_PERFORMANCE_REKEY_START",
        flush=True,
    )

    with source_performance.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as source_handle:
        reader = csv.DictReader(
            source_handle
        )

        source_fields = list(
            reader.fieldnames or []
        )

        output_fields = list(
            source_fields
        )

        for field in (
            "legacy_performance_id",
            "performance_natural_key_version",
            "rekeyed_at",
        ):
            if field not in output_fields:
                output_fields.append(field)

        remap_rows: list[
            dict[str, Any]
        ] = []

        with performance_output.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as output_handle:
            writer = csv.DictWriter(
                output_handle,
                fieldnames=output_fields,
            )
            writer.writeheader()

            for row_number, row in enumerate(
                reader,
                start=1,
            ):
                source_rows += 1

                if (
                    row_number == 1
                    or row_number
                    % PROGRESS_INTERVAL
                    == 0
                ):
                    print(
                        "PERFORMANCE_REKEY_PROGRESS="
                        f"{row_number}",
                        flush=True,
                    )

                legacy_id = clean(
                    row.get(
                        "performance_id"
                    )
                )

                source_row_number = clean(
                    row.get(
                        "source_row_number"
                    )
                )

                natural_key = (
                    performance_natural_key(
                        row
                    )
                )

                new_id = stable_id(
                    "performance",
                    natural_key,
                )

                if new_id in new_ids:
                    duplicate_new_ids += 1

                new_ids.add(new_id)

                old_to_new[
                    (
                        legacy_id,
                        source_row_number,
                    )
                ] = new_id

                legacy_to_new_ids.setdefault(
                    legacy_id,
                    set(),
                ).add(new_id)

                output_row = dict(row)
                output_row[
                    "legacy_performance_id"
                ] = legacy_id
                output_row[
                    "performance_id"
                ] = new_id
                output_row[
                    "performance_natural_key_version"
                ] = IDENTITY_VERSION
                output_row[
                    "rekeyed_at"
                ] = generated_at

                writer.writerow(
                    output_row
                )

                remap_rows.append(
                    {
                        "legacy_performance_id": (
                            legacy_id
                        ),
                        "source_row_number": (
                            source_row_number
                        ),
                        "new_performance_id": (
                            new_id
                        ),
                        "race_date": (
                            normalise_date(
                                row.get(
                                    "race_date"
                                )
                            )
                        ),
                        "track": clean(
                            row.get("track")
                        ),
                        "race_number": (
                            normalise_integer(
                                row.get(
                                    "race_number"
                                )
                            )
                        ),
                        "horse_name": clean(
                            row.get(
                                "horse_name"
                            )
                        ),
                        "remap_version": (
                            REMAP_VERSION
                        ),
                    }
                )

    write_csv(
        remap_output,
        remap_rows,
    )

    collision_rows = []

    for legacy_id, new_id_set in sorted(
        legacy_to_new_ids.items()
    ):
        if len(new_id_set) <= 1:
            continue

        collision_rows.append(
            {
                "legacy_performance_id": (
                    legacy_id
                ),
                "new_performance_count": (
                    len(new_id_set)
                ),
                "new_performance_ids": (
                    " | ".join(
                        sorted(new_id_set)
                    )
                ),
                "classification": (
                    "LEGACY_IDENTITY_COLLISION_"
                    "SPLIT_INTO_DISTINCT_"
                    "PERFORMANCES"
                ),
            }
        )

    write_csv(
        collision_output,
        collision_rows,
    )

    print(
        "PHASE1_0_2_SECTIONAL_REMAP_START",
        flush=True,
    )

    sectional_rows = 0
    sectional_remapped = 0
    sectional_unresolved = 0
    sectional_ids: set[str] = set()
    duplicate_sectional_ids = 0

    with source_sectional.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as source_handle:
        reader = csv.DictReader(
            source_handle
        )

        source_fields = list(
            reader.fieldnames or []
        )

        output_fields = list(
            source_fields
        )

        for field in (
            "legacy_performance_id",
            "legacy_performance_sectional_id",
            "identity_remap_version",
            "remapped_at",
        ):
            if field not in output_fields:
                output_fields.append(field)

        with sectional_output.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as output_handle:
            writer = csv.DictWriter(
                output_handle,
                fieldnames=output_fields,
            )
            writer.writeheader()

            for row_number, row in enumerate(
                reader,
                start=1,
            ):
                sectional_rows += 1

                if (
                    row_number == 1
                    or row_number
                    % PROGRESS_INTERVAL
                    == 0
                ):
                    print(
                        "SECTIONAL_REMAP_PROGRESS="
                        f"{row_number}",
                        flush=True,
                    )

                legacy_performance_id = clean(
                    row.get(
                        "performance_id"
                    )
                )

                legacy_sectional_id = clean(
                    row.get(
                        "performance_sectional_id"
                    )
                )

                source_row_number = clean(
                    row.get(
                        "source_row_number"
                    )
                )

                candidate_new_ids = (
                    legacy_to_new_ids.get(
                        legacy_performance_id,
                        set(),
                    )
                )

                if len(candidate_new_ids) == 1:
                    new_performance_id = next(
                        iter(
                            candidate_new_ids
                        )
                    )
                else:
                    new_performance_id = ""

                if not new_performance_id:
                    sectional_unresolved += 1
                    continue

                new_sectional_id = stable_id(
                    "performance_sectional",
                    (
                        f"{new_performance_id}|"
                        f"{clean(row.get('source_evidence_id'))}|"
                        f"{source_row_number}"
                    ),
                )

                if new_sectional_id in sectional_ids:
                    duplicate_sectional_ids += 1

                sectional_ids.add(
                    new_sectional_id
                )

                output_row = dict(row)
                output_row[
                    "legacy_performance_id"
                ] = legacy_performance_id
                output_row[
                    "legacy_performance_sectional_id"
                ] = legacy_sectional_id
                output_row[
                    "performance_id"
                ] = new_performance_id
                output_row[
                    "performance_sectional_id"
                ] = new_sectional_id
                output_row[
                    "identity_remap_version"
                ] = REMAP_VERSION
                output_row[
                    "remapped_at"
                ] = generated_at

                writer.writerow(
                    output_row
                )
                sectional_remapped += 1

    checks = [
        {
            "check": (
                "PERFORMANCE_ROW_COUNT_PRESERVED"
            ),
            "passed": (
                source_rows
                == len(new_ids)
            ),
            "observed": (
                f"source_rows={source_rows};"
                f"unique_new_ids={len(new_ids)}"
            ),
        },
        {
            "check": (
                "NEW_PERFORMANCE_IDS_UNIQUE"
            ),
            "passed": (
                duplicate_new_ids == 0
            ),
            "observed": (
                f"duplicates="
                f"{duplicate_new_ids}"
            ),
        },
        {
            "check": (
                "LEGACY_COLLISIONS_SPLIT"
            ),
            "passed": (
                len(collision_rows) == 89
            ),
            "observed": (
                f"collision_groups="
                f"{len(collision_rows)}"
            ),
        },
        {
            "check": (
                "SECTIONAL_REMAP_COMPLETE"
            ),
            "passed": (
                sectional_unresolved == 0
            ),
            "observed": (
                f"remapped="
                f"{sectional_remapped};"
                f"unresolved="
                f"{sectional_unresolved}"
            ),
        },
        {
            "check": (
                "NEW_SECTIONAL_IDS_UNIQUE"
            ),
            "passed": (
                duplicate_sectional_ids == 0
            ),
            "observed": (
                f"duplicates="
                f"{duplicate_sectional_ids}"
            ),
        },
    ]

    all_passed = all(
        check["passed"]
        for check in checks
    )

    write_csv(
        checks_output,
        checks,
    )

    summary = {
        "audit_name": (
            "EDGEiQ Performance Intelligence "
            "Phase 1.0.2 Performance Identity "
            "Collision Repair"
        ),
        "generated_utc": generated_at,
        "status": (
            "PERFORMANCE_IDENTITY_"
            "COLLISION_REPAIR_PASS"
            if all_passed
            else
            "PERFORMANCE_IDENTITY_"
            "COLLISION_REPAIR_FAIL"
        ),
        "production_data_modified": False,
        "source_performance_rows": (
            source_rows
        ),
        "new_unique_performance_ids": (
            len(new_ids)
        ),
        "legacy_collision_groups": (
            len(collision_rows)
        ),
        "duplicate_new_performance_ids": (
            duplicate_new_ids
        ),
        "source_sectional_rows": (
            sectional_rows
        ),
        "remapped_sectional_rows": (
            sectional_remapped
        ),
        "unresolved_sectional_rows": (
            sectional_unresolved
        ),
        "duplicate_new_sectional_ids": (
            duplicate_sectional_ids
        ),
        "checks": checks,
        "failed_checks": [
            check["check"]
            for check in checks
            if not check["passed"]
        ],
        "canonical_status": (
            "IDENTITY_COLLISIONS_REPAIRED_"
            "PROTOTYPE_NOT_PROMOTED"
            if all_passed
            else
            "IDENTITY_REPAIR_BLOCKED"
        ),
        "next_stage": (
            "Rerun Phase 1.0 snapshot "
            "reproducibility audit against "
            "performance identity V0.2 and "
            "sectional evidence V0.2."
        ),
        "outputs": {
            "performance_identity_v0_2": str(
                performance_output.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "legacy_id_remap": str(
                remap_output.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "sectional_evidence_v0_2": str(
                sectional_output.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "collision_audit": str(
                collision_output.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
            "checks": str(
                checks_output.relative_to(
                    ROOT
                )
            ).replace("\\", "/"),
        },
        "sha256": {
            "performance_identity_v0_2": (
                sha256_file(
                    performance_output
                )
            ),
            "legacy_id_remap": (
                sha256_file(
                    remap_output
                )
            ),
            "sectional_evidence_v0_2": (
                sha256_file(
                    sectional_output
                )
            ),
        },
    }

    write_json(
        summary_output,
        summary,
    )

    write_json(
        latest_output,
        summary,
    )

    architecture_output.write_text(
        """# EDGEiQ Performance Identity Natural Key V0.2

## Failure corrected

The V0.1 performance identity relied on provider race and runner identities that were reused across separate meetings.

This created 89 false performance collisions.

## V0.2 natural key

A performance identity now contains:

- official race date
- jurisdiction or state
- canonical track
- official race number
- provider race identity
- provider runner identity
- canonical horse identity

## Permanent rule

A provider identifier is evidence, not automatically a globally permanent canonical identity.

No two different race dates or race numbers may share one canonical performance ID.

## Legacy lineage

The former performance ID remains stored as `legacy_performance_id`.

Every V0.1-to-V0.2 mapping is preserved in the remap table.

No historical source row is deleted.
""",
        encoding="utf-8",
    )

    report_output.write_text(
        f"""# EDGEiQ Performance Intelligence
## Phase 1.0.2 Performance Identity Collision Repair

Generated UTC: `{generated_at}`

Status: **{summary['status']}**

- Performance source rows: **{source_rows:,}**
- New unique performance IDs: **{len(new_ids):,}**
- Legacy identity collisions split: **{len(collision_rows):,}**
- Duplicate new performance IDs: **{duplicate_new_ids:,}**
- Sectional rows remapped: **{sectional_remapped:,}**
- Unresolved sectional rows: **{sectional_unresolved:,}**
- Duplicate new sectional IDs: **{duplicate_sectional_ids:,}**

The 89 legacy collisions represented distinct performances, not duplicate evidence.

Production data was not modified.
""",
        encoding="utf-8",
    )

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE1_0_2_PERFORMANCE_IDENTITY_"
        "COLLISION_REPAIR_PASS"
        if all_passed
        else
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE1_0_2_PERFORMANCE_IDENTITY_"
        "COLLISION_REPAIR_FAIL",
        flush=True,
    )

    print(
        f"PERFORMANCE_V0_2={performance_output}",
        flush=True,
    )

    print(
        f"LEGACY_REMAP={remap_output}",
        flush=True,
    )

    print(
        f"SECTIONALS_V0_2={sectional_output}",
        flush=True,
    )

    print(
        f"COLLISIONS={collision_output}",
        flush=True,
    )

    print(
        f"CHECKS={checks_output}",
        flush=True,
    )

    print(
        f"SUMMARY={summary_output}",
        flush=True,
    )

    if not all_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
