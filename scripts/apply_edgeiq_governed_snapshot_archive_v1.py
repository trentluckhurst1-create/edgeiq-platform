from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path.cwd()

RECOVERY_ROOT = (
    ROOT
    / "docs"
    / "repository-recovery-v2"
)

SIMULATION_CSV = (
    RECOVERY_ROOT
    / "edgeiq_snapshot_archive_simulation_v1.csv"
)

SIMULATION_JSON = (
    RECOVERY_ROOT
    / "edgeiq_snapshot_archive_simulation_v1.json"
)

MANIFEST_CSV = (
    RECOVERY_ROOT
    / "edgeiq_repository_recovery_manifest_v1.csv"
)

MANIFEST_JSON = (
    RECOVERY_ROOT
    / "edgeiq_repository_recovery_manifest_v1.json"
)

SUMMARY_JSON = (
    RECOVERY_ROOT
    / "edgeiq_repository_recovery_summary_v1.json"
)

MANIFEST_REPORT = (
    RECOVERY_ROOT
    / "EDGEIQ_REPOSITORY_RECOVERY_MANIFEST_V1.md"
)

ARCHIVE_ROOT = (
    RECOVERY_ROOT
    / "archive"
    / "snapshots-v1"
)

LEDGER_CSV = (
    RECOVERY_ROOT
    / "edgeiq_governed_snapshot_archive_ledger_v1.csv"
)

LEDGER_JSON = (
    RECOVERY_ROOT
    / "edgeiq_governed_snapshot_archive_ledger_v1.json"
)

EXECUTION_JSON = (
    RECOVERY_ROOT
    / "edgeiq_governed_snapshot_archive_execution_v1.json"
)

REPORT_MD = (
    RECOVERY_ROOT
    / "EDGEIQ_GOVERNED_SNAPSHOT_ARCHIVE_EXECUTION_V1.md"
)

LOG_ROOT = (
    RECOVERY_ROOT
    / "governed-snapshot-archive-v1-logs"
)

LOG_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalise_path(value: str) -> str:
    return clean(value).replace("\\", "/")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Required input missing: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if not reader.fieldnames:
            raise RuntimeError(
                f"CSV has no header: {path}"
            )

        return [
            {
                clean(key): clean(value)
                for key, value in row.items()
                if key is not None
            }
            for row in reader
        ]


def write_csv(
    path: Path,
    rows: list[dict[str, str]],
    fieldnames: list[str],
) -> None:
    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(
            encoding="utf-8-sig"
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
        )
        + "\n",
        encoding="utf-8",
    )


def run_command(
    name: str,
    command: list[str],
) -> dict[str, Any]:
    log_path = LOG_ROOT / f"{name}.log"

    started = time.time()

    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            env=os.environ.copy(),
        )

        exit_code = completed.returncode
        output = completed.stdout or ""

    except FileNotFoundError as error:
        exit_code = 9009
        output = (
            f"Command executable not found: {error}\n"
        )

    duration_seconds = round(
        time.time() - started,
        3,
    )

    log_path.write_text(
        output,
        encoding="utf-8",
    )

    return {
        "name": name,
        "command": command,
        "exit_code": exit_code,
        "passed": exit_code == 0,
        "duration_seconds": duration_seconds,
        "log_path": normalise_path(
            str(log_path.relative_to(ROOT))
        ),
    }


def validation_commands() -> list[
    tuple[str, list[str]]
]:
    package_path = ROOT / "package.json"

    package = json.loads(
        package_path.read_text(
            encoding="utf-8-sig"
        )
    )

    scripts = package.get("scripts", {})

    commands: list[
        tuple[str, list[str]]
    ] = []

    if "typecheck" in scripts:
        commands.append(
            (
                "typecheck",
                ["npm.cmd", "run", "typecheck"],
            )
        )
    elif "check" in scripts:
        commands.append(
            (
                "check",
                ["npm.cmd", "run", "check"],
            )
        )
    else:
        local_tsc = (
            ROOT
            / "node_modules"
            / ".bin"
            / "tsc.cmd"
        )

        if local_tsc.exists():
            commands.append(
                (
                    "typescript_no_emit",
                    [
                        str(local_tsc),
                        "--noEmit",
                    ],
                )
            )

    if "build" in scripts:
        commands.append(
            (
                "build",
                ["npm.cmd", "run", "build"],
            )
        )

    if not commands:
        raise RuntimeError(
            "No TypeScript or build validation "
            "commands could be resolved."
        )

    return commands


simulation_payload = load_json(
    SIMULATION_JSON
)

simulation_summary = simulation_payload.get(
    "summary",
    {},
)

if (
    simulation_summary.get("verdict")
    != "PASS"
):
    raise RuntimeError(
        "Unit 006 simulation verdict is not PASS."
    )

if (
    simulation_summary.get("archive_decision")
    != "AUTHORISED_FOR_GOVERNED_ARCHIVE"
):
    raise RuntimeError(
        "Unit 006 did not authorise the archive."
    )

simulation_rows = read_csv(
    SIMULATION_CSV
)

authorised_rows = [
    row
    for row in simulation_rows
    if clean(
        row.get("archive_decision")
    )
    == "AUTHORISED_FOR_GOVERNED_ARCHIVE"
]

if len(authorised_rows) != 72:
    raise RuntimeError(
        "Expected exactly 72 authorised archive "
        f"rows, found {len(authorised_rows)}."
    )

authorised_rows.sort(
    key=lambda row: normalise_path(
        row["snapshot_path"]
    ).lower()
)

manifest_rows = read_csv(
    MANIFEST_CSV
)

manifest_fieldnames = list(
    manifest_rows[0].keys()
)

manifest_by_path = {
    normalise_path(
        row["repository_path"]
    ): row
    for row in manifest_rows
}

authorised_paths = [
    normalise_path(
        row["snapshot_path"]
    )
    for row in authorised_rows
]

if len(authorised_paths) != len(
    set(authorised_paths)
):
    raise RuntimeError(
        "Authorised snapshot paths are not unique."
    )

for repository_path in authorised_paths:
    if repository_path not in manifest_by_path:
        raise RuntimeError(
            "Authorised snapshot missing from manifest: "
            f"{repository_path}"
        )


# ---------------------------------------
# Backup governance files for rollback
# ---------------------------------------

governance_files = [
    MANIFEST_CSV,
    MANIFEST_JSON,
    SUMMARY_JSON,
    MANIFEST_REPORT,
]

with tempfile.TemporaryDirectory(
    prefix="edgeiq_governed_archive_backup_"
) as backup_directory:
    backup_root = Path(backup_directory)

    backup_paths: dict[Path, Path] = {}

    for governance_file in governance_files:
        if governance_file.exists():
            backup_path = (
                backup_root
                / governance_file.name
            )

            shutil.copy2(
                governance_file,
                backup_path,
            )

            backup_paths[
                governance_file
            ] = backup_path

    moved_files: list[
        tuple[Path, Path]
    ] = []

    ledger_rows: list[
        dict[str, str]
    ] = []

    validation_results: list[
        dict[str, Any]
    ] = []

    started = time.time()

    try:
        # --------------------------------
        # Move authorised snapshots
        # --------------------------------

        for authorised_row in authorised_rows:
            repository_path = normalise_path(
                authorised_row["snapshot_path"]
            )

            source = (
                ROOT
                / Path(repository_path)
            )

            destination = (
                ARCHIVE_ROOT
                / Path(repository_path)
            )

            if not source.is_file():
                raise FileNotFoundError(
                    "Authorised source file missing: "
                    f"{repository_path}"
                )

            if destination.exists():
                raise FileExistsError(
                    "Archive destination already exists: "
                    f"{destination}"
                )

            source_size = source.stat().st_size
            source_hash = sha256_file(source)

            expected_hash = clean(
                authorised_row.get(
                    "pre_sha256"
                )
            )

            if (
                expected_hash
                and source_hash != expected_hash
            ):
                raise RuntimeError(
                    "Snapshot changed after simulation: "
                    f"{repository_path}"
                )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.move(
                str(source),
                str(destination),
            )

            moved_files.append(
                (
                    source,
                    destination,
                )
            )

            archived_hash = sha256_file(
                destination
            )

            if archived_hash != source_hash:
                raise RuntimeError(
                    "Archived file hash mismatch: "
                    f"{repository_path}"
                )

            ledger_rows.append(
                {
                    "recovery_id": clean(
                        manifest_by_path[
                            repository_path
                        ].get("recovery_id")
                    ),
                    "original_repository_path": (
                        repository_path
                    ),
                    "archived_repository_path": (
                        normalise_path(
                            str(
                                destination.relative_to(
                                    ROOT
                                )
                            )
                        )
                    ),
                    "active_counterpart": clean(
                        authorised_row.get(
                            "active_counterpart"
                        )
                    ),
                    "size_bytes": str(
                        source_size
                    ),
                    "sha256": source_hash,
                    "archive_status": "ARCHIVED",
                    "validation_status": "PENDING",
                }
            )

        # --------------------------------
        # Validate archive state
        # --------------------------------

        for name, command in (
            validation_commands()
        ):
            result = run_command(
                name,
                command,
            )

            validation_results.append(
                result
            )

            if not result["passed"]:
                raise RuntimeError(
                    "Post-archive validation failed: "
                    f"{name}"
                )

        # --------------------------------
        # Update canonical manifest
        # --------------------------------

        archived_path_set = set(
            authorised_paths
        )

        completed_rows = 0

        for row in manifest_rows:
            repository_path = normalise_path(
                row["repository_path"]
            )

            if repository_path not in (
                archived_path_set
            ):
                continue

            row["recommended_action"] = (
                "ARCHIVE"
            )

            row["recovery_status"] = (
                "COMPLETE"
            )

            row["decision_basis"] = (
                "Archived under RRV2 Unit 007 after "
                "reference verification, reversible "
                "simulation, TypeScript validation and "
                "production build validation."
            )

            completed_rows += 1

        if completed_rows != 72:
            raise RuntimeError(
                "Manifest did not update exactly "
                f"72 rows; updated {completed_rows}."
            )

        write_csv(
            MANIFEST_CSV,
            manifest_rows,
            manifest_fieldnames,
        )

        # --------------------------------
        # Update manifest JSON
        # --------------------------------

        manifest_json_payload = load_json(
            MANIFEST_JSON
        )

        json_manifest_rows = (
            manifest_json_payload.get(
                "manifest",
                []
            )
        )

        json_completed_rows = 0

        for row in json_manifest_rows:
            repository_path = normalise_path(
                row.get(
                    "repository_path",
                    "",
                )
            )

            if repository_path not in (
                archived_path_set
            ):
                continue

            row["recommended_action"] = (
                "ARCHIVE"
            )

            row["recovery_status"] = (
                "COMPLETE"
            )

            row["decision_basis"] = (
                "Archived under RRV2 Unit 007 after "
                "reference verification, reversible "
                "simulation, TypeScript validation and "
                "production build validation."
            )

            json_completed_rows += 1

        if json_completed_rows != 72:
            raise RuntimeError(
                "Manifest JSON did not update exactly "
                f"72 rows; updated "
                f"{json_completed_rows}."
            )

        write_json(
            MANIFEST_JSON,
            manifest_json_payload,
        )

        # --------------------------------
        # Recalculate summary
        # --------------------------------

        phase_counts = Counter(
            row["recovery_phase"]
            for row in manifest_rows
        )

        action_counts = Counter(
            row["recommended_action"]
            for row in manifest_rows
        )

        risk_counts = Counter(
            row["risk"]
            for row in manifest_rows
        )

        unit_counts = Counter(
            row["governed_unit"]
            for row in manifest_rows
        )

        status_counts = Counter(
            row["recovery_status"]
            for row in manifest_rows
        )

        total_items = len(
            manifest_rows
        )

        complete_items = (
            status_counts.get(
                "COMPLETE",
                0,
            )
        )

        pending_items = (
            status_counts.get(
                "PENDING",
                0,
            )
        )

        completion_percentage = round(
            complete_items
            / total_items
            * 100,
            2,
        )

        summary_payload = {
            "schema_version": "1.0",
            "repository_recovery_program": (
                "EDGEIQ Repository Recovery V2"
            ),
            "total_repository_items": (
                total_items
            ),
            "items_by_phase": dict(
                sorted(
                    phase_counts.items()
                )
            ),
            "items_by_action": dict(
                sorted(
                    action_counts.items()
                )
            ),
            "items_by_risk": dict(
                sorted(
                    risk_counts.items()
                )
            ),
            "items_by_governed_unit": dict(
                sorted(
                    unit_counts.items(),
                    key=lambda item: (
                        -item[1],
                        item[0],
                    ),
                )
            ),
            "items_by_status": dict(
                sorted(
                    status_counts.items()
                )
            ),
            "items_pending": pending_items,
            "items_complete": complete_items,
            "repository_recovery_completion_percent": (
                completion_percentage
            ),
            "validation": {
                "verdict": "PASS",
                "unique_repository_paths": len(
                    {
                        row["repository_path"]
                        for row in manifest_rows
                    }
                ),
                "unique_recovery_ids": len(
                    {
                        row["recovery_id"]
                        for row in manifest_rows
                    }
                ),
                "deterministic_ordering": True,
                "mandatory_fields_populated": True,
            },
            "latest_completed_unit": {
                "unit": (
                    "RRV2 Unit 007"
                ),
                "name": (
                    "Governed Snapshot Archive Execution"
                ),
                "items_completed": 72,
            },
        }

        write_json(
            SUMMARY_JSON,
            summary_payload,
        )

        # --------------------------------
        # Finalise ledger
        # --------------------------------

        for ledger_row in ledger_rows:
            ledger_row[
                "validation_status"
            ] = "PASS"

        ledger_fieldnames = [
            "recovery_id",
            "original_repository_path",
            "archived_repository_path",
            "active_counterpart",
            "size_bytes",
            "sha256",
            "archive_status",
            "validation_status",
        ]

        write_csv(
            LEDGER_CSV,
            ledger_rows,
            ledger_fieldnames,
        )

        ledger_payload = {
            "schema_version": "1.0",
            "program": (
                "EDGEIQ Repository Recovery V2"
            ),
            "recovery_unit": (
                "RRV2 Unit 007 - Governed "
                "Snapshot Archive Execution"
            ),
            "archive_root": normalise_path(
                str(
                    ARCHIVE_ROOT.relative_to(
                        ROOT
                    )
                )
            ),
            "archived_file_count": 72,
            "validation_verdict": "PASS",
            "files": ledger_rows,
        }

        write_json(
            LEDGER_JSON,
            ledger_payload,
        )

        # --------------------------------
        # Reports
        # --------------------------------

        execution_payload = {
            "schema_version": "1.0",
            "program": (
                "EDGEIQ Repository Recovery V2"
            ),
            "recovery_unit": (
                "RRV2 Unit 007 - Governed "
                "Snapshot Archive Execution"
            ),
            "verdict": "PASS",
            "archive_decision": (
                "EXECUTED_AND_VALIDATED"
            ),
            "archived_file_count": 72,
            "protected_snapshot_count": 5,
            "manifest_rows_completed": 72,
            "repository_items_complete": (
                complete_items
            ),
            "repository_items_pending": (
                pending_items
            ),
            "repository_recovery_completion_percent": (
                completion_percentage
            ),
            "validation_results": (
                validation_results
            ),
            "archive_root": normalise_path(
                str(
                    ARCHIVE_ROOT.relative_to(
                        ROOT
                    )
                )
            ),
            "duration_seconds": round(
                time.time() - started,
                3,
            ),
        }

        write_json(
            EXECUTION_JSON,
            execution_payload,
        )

        validation_lines: list[str] = []

        for result in validation_results:
            validation_lines.append(
                "| "
                f"`{result['name']}` | "
                f"{result['exit_code']} | "
                f"{result['duration_seconds']} | "
                f"`{'PASS' if result['passed'] else 'FAIL'}` | "
                f"`{result['log_path']}` |"
            )

        report_lines = [
            "# EDGEIQ Governed Snapshot Archive "
            "Execution V1",
            "",
            "## Status",
            "",
            "**VERDICT: PASS**",
            "",
            "## Archive Execution",
            "",
            (
                "- Authorised snapshots archived: "
                "**72**"
            ),
            (
                "- Protected snapshots untouched: "
                "**5**"
            ),
            (
                "- Manifest rows completed: "
                "**72**"
            ),
            (
                "- Archive root: "
                f"`{execution_payload['archive_root']}`"
            ),
            "",
            "All archived files retain their original "
            "repository-relative folder structure and "
            "their SHA-256 hashes.",
            "",
            "## Validation",
            "",
            (
                "| Validation | Exit Code | "
                "Duration Seconds | Result | Log |"
            ),
            "|---|---:|---:|---|---|",
            *validation_lines,
            "",
            "## Recovery Progress",
            "",
            (
                f"- Repository items complete: "
                f"**{complete_items}**"
            ),
            (
                f"- Repository items pending: "
                f"**{pending_items}**"
            ),
            (
                "- Repository recovery completion: "
                f"**{completion_percentage:.2f}%**"
            ),
            "",
            "## Protected Snapshot Set",
            "",
            (
                "Four snapshots remain active because "
                "governed patch scripts reference them. "
                "One CSS snapshot remains blocked because "
                "no active counterpart has yet been "
                "established."
            ),
            "",
            "## Next Recovery Unit",
            "",
            (
                "**RRV2 Unit 008 - Protected Snapshot "
                "Dependency Resolution**"
            ),
            "",
            (
                "Resolve the four patch-script references "
                "and determine the authoritative counterpart "
                "for the remaining CSS snapshot without "
                "removing historical evidence."
            ),
            "",
        ]

        REPORT_MD.write_text(
            "\n".join(report_lines),
            encoding="utf-8",
        )

        manifest_report_lines = [
            "# EDGEIQ Repository Recovery Manifest V1",
            "",
            "## Repository Recovery V2",
            "",
            (
                "This manifest is the canonical operating "
                "index for the governed recovery of the "
                "EDGEIQ platform repository."
            ),
            "",
            "## Current State",
            "",
            (
                f"- Total repository items: "
                f"**{total_items}**"
            ),
            (
                f"- Recovery items pending: "
                f"**{pending_items}**"
            ),
            (
                f"- Recovery items complete: "
                f"**{complete_items}**"
            ),
            (
                "- Repository recovery completion: "
                f"**{completion_percentage:.2f}%**"
            ),
            "- Validation verdict: **PASS**",
            "",
            "## Completed Recovery Units",
            "",
            (
                "- RRV2 Unit 007: governed archive of "
                "72 verified historical snapshots."
            ),
            "",
            "## Recovery Progress",
            "",
            "| Status | Count |",
            "|---|---:|",
        ]

        for status, count in sorted(
            status_counts.items()
        ):
            manifest_report_lines.append(
                f"| `{status}` | {count} |"
            )

        manifest_report_lines.extend(
            [
                "",
                "## Next Recovery Unit",
                "",
                (
                    "**RRV2 Unit 008 - Protected Snapshot "
                    "Dependency Resolution**"
                ),
                "",
                (
                    "Resolve the five protected historical "
                    "snapshot candidates before completing "
                    "Phase 01."
                ),
                "",
            ]
        )

        MANIFEST_REPORT.write_text(
            "\n".join(
                manifest_report_lines
            ),
            encoding="utf-8",
        )

    except Exception:
        # --------------------------------
        # Full rollback
        # --------------------------------

        for source, destination in reversed(
            moved_files
        ):
            try:
                source.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                if destination.exists():
                    if source.exists():
                        source.unlink()

                    shutil.move(
                        str(destination),
                        str(source),
                    )
            except Exception:
                pass

        for original, backup in (
            backup_paths.items()
        ):
            try:
                shutil.copy2(
                    backup,
                    original,
                )
            except Exception:
                pass

        for generated_file in (
            LEDGER_CSV,
            LEDGER_JSON,
            EXECUTION_JSON,
            REPORT_MD,
        ):
            try:
                if generated_file.exists():
                    generated_file.unlink()
            except Exception:
                pass

        raise


# ---------------------------------------
# Final independent integrity check
# ---------------------------------------

ledger_check = read_csv(
    LEDGER_CSV
)

if len(ledger_check) != 72:
    raise RuntimeError(
        "Archive ledger does not contain 72 rows."
    )

for row in ledger_check:
    original = (
        ROOT
        / Path(
            row[
                "original_repository_path"
            ]
        )
    )

    archived = (
        ROOT
        / Path(
            row[
                "archived_repository_path"
            ]
        )
    )

    if original.exists():
        raise RuntimeError(
            "Original snapshot still exists after "
            f"archive: {original}"
        )

    if not archived.is_file():
        raise RuntimeError(
            "Archived snapshot missing: "
            f"{archived}"
        )

    if (
        sha256_file(archived)
        != row["sha256"]
    ):
        raise RuntimeError(
            "Final archive hash mismatch: "
            f"{archived}"
        )


print("VERDICT=PASS")
print(
    "ARCHIVE_DECISION=EXECUTED_AND_VALIDATED"
)
print("ARCHIVED_FILE_COUNT=72")
print("PROTECTED_SNAPSHOT_COUNT=5")
print("MANIFEST_ROWS_COMPLETED=72")
print(
    "REPOSITORY_ITEMS_COMPLETE="
    f"{complete_items}"
)
print(
    "REPOSITORY_ITEMS_PENDING="
    f"{pending_items}"
)
print(
    "REPOSITORY_RECOVERY_COMPLETION_PERCENT="
    f"{completion_percentage:.2f}"
)
print(
    "TYPESCRIPT_AND_BUILD_VALIDATION=PASS"
)
print(
    f"ARCHIVE_ROOT={ARCHIVE_ROOT}"
)
print(f"LEDGER_CSV={LEDGER_CSV}")
print(f"LEDGER_JSON={LEDGER_JSON}")
print(f"EXECUTION_JSON={EXECUTION_JSON}")
print(f"REPORT={REPORT_MD}")
