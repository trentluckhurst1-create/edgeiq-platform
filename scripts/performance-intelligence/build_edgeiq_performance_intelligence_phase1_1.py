from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

PHASE103_SNAPSHOTS = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "snapshots"
    / "phase1_0_3"
)

WAREHOUSE_ROOT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse"
    / "raw"
)

AUDIT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase1_1"
)

ARCH_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "architecture"
    / "phase1_1"
)

WAREHOUSE_VERSION = (
    "EDGEIQ_CANONICAL_RAW_WAREHOUSE_V1_0"
)

MATERIALISATION_VERSION = (
    "PHASE1_1_IMMUTABLE_MATERIALISATION_V1_0"
)

CHUNK_SIZE = 4 * 1024 * 1024


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def rel(path: Path) -> str:
    return str(
        path.relative_to(ROOT)
    ).replace("\\", "/")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(CHUNK_SIZE),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def copy_and_hash(
    source: Path,
    destination: Path,
) -> str:
    digest = hashlib.sha256()

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with source.open(
        "rb"
    ) as source_handle, destination.open(
        "wb"
    ) as destination_handle:
        while True:
            block = source_handle.read(
                CHUNK_SIZE
            )

            if not block:
                break

            destination_handle.write(
                block
            )
            digest.update(block)

    return digest.hexdigest()


def latest_snapshot_manifest() -> Path:
    candidates = sorted(
        PHASE103_SNAPSHOTS.glob(
            "edgeiq_performance_warehouse_"
            "snapshot_manifest_v0_2_*.json"
        ),
        key=lambda path: (
            path.stat().st_mtime
        ),
        reverse=True,
    )

    candidates = [
        path
        for path in candidates
        if "latest" not in path.name
    ]

    if not candidates:
        raise FileNotFoundError(
            "No Phase 1.0.3 snapshot manifest found."
        )

    return candidates[0]


def read_json(path: Path) -> Any:
    return json.loads(
        path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    )


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


def make_read_only(path: Path) -> None:
    try:
        os.chmod(
            path,
            0o444,
        )
    except OSError:
        pass


def restore_writable(path: Path) -> None:
    try:
        os.chmod(
            path,
            0o666,
        )
    except OSError:
        pass


def main() -> None:
    WAREHOUSE_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )
    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    ARCH_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    source_manifest_path = (
        latest_snapshot_manifest()
    )
    source_manifest = read_json(
        source_manifest_path
    )

    if (
        source_manifest.get("status")
        != "SNAPSHOT_REPRODUCIBILITY_PASS"
    ):
        raise RuntimeError(
            "Source snapshot has not passed "
            "reproducibility validation."
        )

    failed_checks = (
        source_manifest.get(
            "failed_checks",
            [],
        )
    )

    if failed_checks:
        raise RuntimeError(
            "Source snapshot contains failed checks: "
            + " | ".join(failed_checks)
        )

    snapshot_id = source_manifest[
        "warehouse_snapshot_id"
    ]

    performance_profile = (
        source_manifest[
            "performance_profile"
        ]
    )
    sectional_profile = (
        source_manifest[
            "sectional_profile"
        ]
    )

    performance_source = (
        ROOT
        / performance_profile["path"]
    )
    sectional_source = (
        ROOT
        / sectional_profile["path"]
    )

    if not performance_source.exists():
        raise FileNotFoundError(
            performance_source
        )

    if not sectional_source.exists():
        raise FileNotFoundError(
            sectional_source
        )

    print(
        "PHASE1_1_VERIFY_SOURCE_HASHES_START",
        flush=True,
    )

    performance_source_hash = (
        sha256_file(
            performance_source
        )
    )
    sectional_source_hash = (
        sha256_file(
            sectional_source
        )
    )

    if (
        performance_source_hash
        != performance_profile["sha256"]
    ):
        raise RuntimeError(
            "Performance source hash changed "
            "after Phase 1.0.3 validation."
        )

    if (
        sectional_source_hash
        != sectional_profile["sha256"]
    ):
        raise RuntimeError(
            "Sectional source hash changed "
            "after Phase 1.0.3 validation."
        )

    final_snapshot_dir = (
        WAREHOUSE_ROOT
        / snapshot_id
    )
    staging_dir = (
        WAREHOUSE_ROOT
        / f".{snapshot_id}.staging"
    )

    if final_snapshot_dir.exists():
        existing_manifest = (
            final_snapshot_dir
            / "warehouse_manifest.json"
        )

        if not existing_manifest.exists():
            raise RuntimeError(
                "Snapshot directory exists without "
                "a warehouse manifest."
            )

        existing = read_json(
            existing_manifest
        )

        if (
            existing.get(
                "warehouse_snapshot_id"
            )
            != snapshot_id
        ):
            raise RuntimeError(
                "Existing snapshot directory has "
                "a mismatched snapshot ID."
            )

        print(
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            "PHASE1_1_WAREHOUSE_ALREADY_"
            "MATERIALISED_PASS",
            flush=True,
        )
        print(
            f"WAREHOUSE={final_snapshot_dir}",
            flush=True,
        )
        return

    if staging_dir.exists():
        for path in staging_dir.rglob("*"):
            if path.is_file():
                restore_writable(path)

        shutil.rmtree(
            staging_dir
        )

    staging_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    performance_destination = (
        staging_dir
        / "canonical_performance_evidence.csv"
    )
    sectional_destination = (
        staging_dir
        / "canonical_sectional_evidence.csv"
    )

    try:
        print(
            "PHASE1_1_COPY_PERFORMANCE_START",
            flush=True,
        )

        performance_copy_hash = (
            copy_and_hash(
                performance_source,
                performance_destination,
            )
        )

        print(
            "PHASE1_1_COPY_SECTIONALS_START",
            flush=True,
        )

        sectional_copy_hash = (
            copy_and_hash(
                sectional_source,
                sectional_destination,
            )
        )

        checks = [
            {
                "check": (
                    "SOURCE_SNAPSHOT_PASSED"
                ),
                "passed": True,
                "observed": snapshot_id,
            },
            {
                "check": (
                    "PERFORMANCE_SOURCE_HASH"
                ),
                "passed": (
                    performance_source_hash
                    == performance_profile[
                        "sha256"
                    ]
                ),
                "observed": (
                    performance_source_hash
                ),
            },
            {
                "check": (
                    "SECTIONAL_SOURCE_HASH"
                ),
                "passed": (
                    sectional_source_hash
                    == sectional_profile[
                        "sha256"
                    ]
                ),
                "observed": (
                    sectional_source_hash
                ),
            },
            {
                "check": (
                    "PERFORMANCE_COPY_HASH"
                ),
                "passed": (
                    performance_copy_hash
                    == performance_source_hash
                ),
                "observed": (
                    performance_copy_hash
                ),
            },
            {
                "check": (
                    "SECTIONAL_COPY_HASH"
                ),
                "passed": (
                    sectional_copy_hash
                    == sectional_source_hash
                ),
                "observed": (
                    sectional_copy_hash
                ),
            },
            {
                "check": (
                    "PERFORMANCE_ROW_COUNT"
                ),
                "passed": (
                    performance_profile[
                        "rows"
                    ]
                    == 879784
                ),
                "observed": (
                    performance_profile[
                        "rows"
                    ]
                ),
            },
            {
                "check": (
                    "SECTIONAL_ROW_COUNT"
                ),
                "passed": (
                    sectional_profile[
                        "rows"
                    ]
                    == 103766
                ),
                "observed": (
                    sectional_profile[
                        "rows"
                    ]
                ),
            },
            {
                "check": (
                    "ALL_PHASE1_0_3_CHECKS_PASSED"
                ),
                "passed": all(
                    check["passed"]
                    for check
                    in source_manifest[
                        "audit_checks"
                    ]
                ),
                "observed": (
                    len(
                        source_manifest[
                            "audit_checks"
                        ]
                    )
                ),
            },
        ]

        failed = [
            check["check"]
            for check in checks
            if not check["passed"]
        ]

        if failed:
            raise RuntimeError(
                "Materialisation checks failed: "
                + " | ".join(failed)
            )

        asset_catalog = [
            {
                "warehouse_snapshot_id": (
                    snapshot_id
                ),
                "asset_name": (
                    "canonical_performance_evidence"
                ),
                "asset_file": (
                    "canonical_performance_evidence.csv"
                ),
                "asset_type": (
                    "IMMUTABLE_CANONICAL_EVIDENCE"
                ),
                "rows": (
                    performance_profile[
                        "rows"
                    ]
                ),
                "sha256": (
                    performance_copy_hash
                ),
                "min_race_date": (
                    performance_profile[
                        "min_race_date"
                    ]
                ),
                "max_race_date": (
                    performance_profile[
                        "max_race_date"
                    ]
                ),
                "primary_key": (
                    "performance_id"
                ),
                "schema_version": (
                    "PERFORMANCE_IDENTITY_V0_2"
                ),
            },
            {
                "warehouse_snapshot_id": (
                    snapshot_id
                ),
                "asset_name": (
                    "canonical_sectional_evidence"
                ),
                "asset_file": (
                    "canonical_sectional_evidence.csv"
                ),
                "asset_type": (
                    "IMMUTABLE_CANONICAL_EVIDENCE"
                ),
                "rows": (
                    sectional_profile[
                        "rows"
                    ]
                ),
                "sha256": (
                    sectional_copy_hash
                ),
                "min_race_date": (
                    sectional_profile[
                        "min_race_date"
                    ]
                ),
                "max_race_date": (
                    sectional_profile[
                        "max_race_date"
                    ]
                ),
                "primary_key": (
                    "performance_sectional_id"
                ),
                "schema_version": (
                    "CANONICAL_SECTIONAL_"
                    "EVIDENCE_V0_2"
                ),
            },
        ]

        catalog_path = (
            staging_dir
            / "asset_catalog.csv"
        )
        checks_path = (
            staging_dir
            / "materialisation_checks.csv"
        )

        write_csv(
            catalog_path,
            asset_catalog,
        )
        write_csv(
            checks_path,
            checks,
        )

        warehouse_manifest = {
            "warehouse_name": (
                "EDGEiQ Canonical Raw "
                "Performance Warehouse"
            ),
            "warehouse_version": (
                WAREHOUSE_VERSION
            ),
            "materialisation_version": (
                MATERIALISATION_VERSION
            ),
            "warehouse_snapshot_id": (
                snapshot_id
            ),
            "generated_utc": utc_now(),
            "immutable": True,
            "production_application_modified": (
                False
            ),
            "source_snapshot_manifest": (
                rel(
                    source_manifest_path
                )
            ),
            "source_snapshot_status": (
                source_manifest[
                    "status"
                ]
            ),
            "source_snapshot_audit_version": (
                source_manifest[
                    "audit_version"
                ]
            ),
            "assets": asset_catalog,
            "materialisation_checks": (
                checks
            ),
            "failed_checks": [],
            "warehouse_status": (
                "IMMUTABLE_CANONICAL_RAW_"
                "WAREHOUSE_MATERIALISED"
            ),
            "promotion_status": (
                "WAREHOUSE_MATERIALISED_"
                "NOT_CONNECTED_TO_PRODUCT"
            ),
            "next_stage": (
                "Phase 1.2 canonical source "
                "evidence and identity dimension "
                "materialisation."
            ),
        }

        manifest_path = (
            staging_dir
            / "warehouse_manifest.json"
        )

        write_json(
            manifest_path,
            warehouse_manifest,
        )

        manifest_hash = (
            sha256_file(
                manifest_path
            )
        )

        integrity_manifest = {
            "warehouse_snapshot_id": (
                snapshot_id
            ),
            "generated_utc": utc_now(),
            "files": [
                {
                    "file": (
                        "canonical_performance_"
                        "evidence.csv"
                    ),
                    "sha256": (
                        performance_copy_hash
                    ),
                },
                {
                    "file": (
                        "canonical_sectional_"
                        "evidence.csv"
                    ),
                    "sha256": (
                        sectional_copy_hash
                    ),
                },
                {
                    "file": (
                        "warehouse_manifest.json"
                    ),
                    "sha256": (
                        manifest_hash
                    ),
                },
                {
                    "file": (
                        "asset_catalog.csv"
                    ),
                    "sha256": (
                        sha256_file(
                            catalog_path
                        )
                    ),
                },
                {
                    "file": (
                        "materialisation_checks.csv"
                    ),
                    "sha256": (
                        sha256_file(
                            checks_path
                        )
                    ),
                },
            ],
        }

        integrity_path = (
            staging_dir
            / "integrity_manifest.json"
        )

        write_json(
            integrity_path,
            integrity_manifest,
        )

        staging_dir.rename(
            final_snapshot_dir
        )

        for path in (
            final_snapshot_dir.rglob("*")
        ):
            if path.is_file():
                make_read_only(path)

    except Exception:
        if staging_dir.exists():
            for path in staging_dir.rglob("*"):
                if path.is_file():
                    restore_writable(path)

            shutil.rmtree(
                staging_dir
            )

        raise

    warehouse_manifest_path = (
        final_snapshot_dir
        / "warehouse_manifest.json"
    )

    final_manifest = read_json(
        warehouse_manifest_path
    )

    audit_checks_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_1_checks_{snapshot_id}.csv"
        )
    )

    audit_summary_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            f"phase1_1_summary_{snapshot_id}.json"
        )
    )

    audit_latest_path = (
        AUDIT_DIR
        / (
            "edgeiq_performance_intelligence_"
            "phase1_1_latest.json"
        )
    )

    report_path = (
        AUDIT_DIR
        / (
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
            f"PHASE1_1_REPORT_{snapshot_id}.md"
        )
    )

    architecture_path = (
        ARCH_DIR
        / (
            "EDGEIQ_CANONICAL_RAW_WAREHOUSE_"
            "GOVERNANCE_V1_0.md"
        )
    )

    write_csv(
        audit_checks_path,
        final_manifest[
            "materialisation_checks"
        ],
    )

    write_json(
        audit_summary_path,
        final_manifest,
    )

    write_json(
        audit_latest_path,
        final_manifest,
    )

    architecture_path.write_text(
        """# EDGEiQ Canonical Raw Warehouse Governance V1.0

## Warehouse boundary

The canonical raw warehouse contains immutable evidence only.

It does not contain:

- benchmarks
- ratings
- fingerprints
- patterns
- React calculations
- presentation fields

## Snapshot rule

Every warehouse snapshot is stored under its deterministic snapshot ID.

Existing snapshots are never overwritten.

A source byte change creates a new snapshot.

## Required assets

- canonical performance evidence
- canonical sectional evidence
- asset catalogue
- materialisation checks
- warehouse manifest
- integrity manifest

## Product separation

This warehouse is not connected directly to the production application.

Future query and intelligence engines consume governed snapshots and produce separately versioned outputs.
""",
        encoding="utf-8",
    )

    report_path.write_text(
        f"""# EDGEiQ Performance Intelligence
## Phase 1.1 Immutable Canonical Raw Warehouse Materialisation

Generated UTC: `{final_manifest['generated_utc']}`

Snapshot ID: `{snapshot_id}`

Status: **{final_manifest['warehouse_status']}**

- Canonical performance rows: **{performance_profile['rows']:,}**
- Canonical sectional evidence rows: **{sectional_profile['rows']:,}**
- Failed checks: **0**
- Production application modified: **False**
- Product connected: **False**

The warehouse snapshot is immutable and stored under its deterministic snapshot ID.
""",
        encoding="utf-8",
    )

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE1_1_IMMUTABLE_CANONICAL_"
        "RAW_WAREHOUSE_MATERIALISATION_PASS",
        flush=True,
    )

    print(
        f"SNAPSHOT_ID={snapshot_id}",
        flush=True,
    )

    print(
        f"WAREHOUSE={final_snapshot_dir}",
        flush=True,
    )

    print(
        f"MANIFEST={warehouse_manifest_path}",
        flush=True,
    )

    print(
        f"INTEGRITY_MANIFEST="
        f"{final_snapshot_dir / 'integrity_manifest.json'}",
        flush=True,
    )

    print(
        f"AUDIT_SUMMARY={audit_summary_path}",
        flush=True,
    )

    print(
        f"REPORT={report_path}",
        flush=True,
    )


if __name__ == "__main__":
    main()
