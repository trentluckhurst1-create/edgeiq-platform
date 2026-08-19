from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path.cwd()

RECOVERY_ROOT = (
    ROOT
    / "docs"
    / "repository-recovery-v2"
)

VERIFICATION_CSV = (
    RECOVERY_ROOT
    / "edgeiq_snapshot_reference_verification_v1.csv"
)

OUTPUT_CSV = (
    RECOVERY_ROOT
    / "edgeiq_snapshot_archive_simulation_v1.csv"
)

OUTPUT_JSON = (
    RECOVERY_ROOT
    / "edgeiq_snapshot_archive_simulation_v1.json"
)

REPORT_MD = (
    RECOVERY_ROOT
    / "EDGEIQ_SNAPSHOT_ARCHIVE_SIMULATION_V1.md"
)

LOG_ROOT = (
    RECOVERY_ROOT
    / "snapshot-archive-simulation-v1-logs"
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def run_command(
    name: str,
    command: list[str],
    phase: str,
) -> dict[str, Any]:
    log_path = (
        LOG_ROOT
        / f"{phase}_{name}.log"
    )

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
        "phase": phase,
        "command": command,
        "exit_code": exit_code,
        "passed": exit_code == 0,
        "duration_seconds": duration_seconds,
        "log_path": normalise_path(
            str(log_path.relative_to(ROOT))
        ),
    }


def load_package_json() -> dict[str, Any]:
    package_path = ROOT / "package.json"

    if not package_path.exists():
        raise FileNotFoundError(
            f"package.json missing: {package_path}"
        )

    return json.loads(
        package_path.read_text(
            encoding="utf-8-sig"
        )
    )


def determine_validation_commands() -> list[
    tuple[str, list[str]]
]:
    package = load_package_json()

    scripts = package.get(
        "scripts",
        {},
    )

    if not isinstance(scripts, dict):
        scripts = {}

    commands: list[
        tuple[str, list[str]]
    ] = []

    # Use the governed project scripts when available.
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

    if "test" in scripts:
        test_script = clean(
            scripts.get("test")
        ).lower()

        placeholder_tokens = (
            "no test specified",
            "error: no test",
            "exit 1",
        )

        if not any(
            token in test_script
            for token in placeholder_tokens
        ):
            commands.append(
                (
                    "test",
                    [
                        "npm.cmd",
                        "run",
                        "test",
                        "--",
                        "--run",
                    ],
                )
            )

    if not commands:
        raise RuntimeError(
            "No build, typecheck, check or usable test "
            "command could be determined."
        )

    return commands


verification_rows = read_csv(
    VERIFICATION_CSV
)

eligible_rows = [
    row
    for row in verification_rows
    if clean(
        row.get("archive_authorisation")
    )
    == "ELIGIBLE_AFTER_BUILD_VALIDATION"
]

blocked_rows = [
    row
    for row in verification_rows
    if clean(
        row.get("archive_authorisation")
    )
    != "ELIGIBLE_AFTER_BUILD_VALIDATION"
]

if len(verification_rows) != 77:
    raise RuntimeError(
        "Expected 77 snapshot verification rows, "
        f"found {len(verification_rows)}."
    )

if len(eligible_rows) != 72:
    raise RuntimeError(
        "Expected 72 archive candidates, "
        f"found {len(eligible_rows)}."
    )

eligible_paths = sorted(
    {
        normalise_path(
            row["snapshot_path"]
        )
        for row in eligible_rows
    },
    key=str.lower,
)

if len(eligible_paths) != 72:
    raise RuntimeError(
        "Archive candidate paths are not unique."
    )

blocked_paths = {
    normalise_path(
        row["snapshot_path"]
    )
    for row in blocked_rows
}

intersection = (
    set(eligible_paths)
    & blocked_paths
)

if intersection:
    raise RuntimeError(
        "A snapshot is both eligible and blocked: "
        + ", ".join(
            sorted(intersection)
        )
    )


# ---------------------------------------
# Establish exact pre-simulation state
# ---------------------------------------

pre_state: dict[str, dict[str, Any]] = {}

for repository_path in eligible_paths:
    absolute_path = (
        ROOT
        / Path(repository_path)
    )

    if not absolute_path.is_file():
        raise FileNotFoundError(
            "Archive candidate does not exist: "
            f"{repository_path}"
        )

    pre_state[repository_path] = {
        "size_bytes": absolute_path.stat().st_size,
        "sha256": sha256_file(
            absolute_path
        ),
    }


validation_commands = (
    determine_validation_commands()
)

baseline_results: list[
    dict[str, Any]
] = []

simulation_results: list[
    dict[str, Any]
] = []

restoration_errors: list[str] = []

simulation_started = time.time()

temporary_root_path = ""

try:
    # -----------------------------------
    # Baseline validation
    # -----------------------------------

    for command_name, command in (
        validation_commands
    ):
        baseline_results.append(
            run_command(
                command_name,
                command,
                "baseline",
            )
        )

    # -----------------------------------
    # Reversible archive simulation
    # -----------------------------------

    with tempfile.TemporaryDirectory(
        prefix="edgeiq_snapshot_archive_simulation_"
    ) as temporary_root:
        temporary_root_path = temporary_root

        temp_root = Path(temporary_root)

        moved_paths: list[
            tuple[Path, Path]
        ] = []

        try:
            for repository_path in eligible_paths:
                source = (
                    ROOT
                    / Path(repository_path)
                )

                destination = (
                    temp_root
                    / Path(repository_path)
                )

                destination.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                shutil.move(
                    str(source),
                    str(destination),
                )

                moved_paths.append(
                    (
                        source,
                        destination,
                    )
                )

            still_present = [
                repository_path
                for repository_path in eligible_paths
                if (
                    ROOT
                    / Path(repository_path)
                ).exists()
            ]

            if still_present:
                raise RuntimeError(
                    "Simulation removal failed for: "
                    + ", ".join(
                        still_present[:20]
                    )
                )

            for command_name, command in (
                validation_commands
            ):
                simulation_results.append(
                    run_command(
                        command_name,
                        command,
                        "simulation",
                    )
                )

        finally:
            for source, destination in reversed(
                moved_paths
            ):
                try:
                    source.parent.mkdir(
                        parents=True,
                        exist_ok=True,
                    )

                    if source.exists():
                        restoration_errors.append(
                            "Restore destination already "
                            f"exists: {source}"
                        )
                        continue

                    if not destination.exists():
                        restoration_errors.append(
                            "Temporary source missing during "
                            f"restore: {destination}"
                        )
                        continue

                    shutil.move(
                        str(destination),
                        str(source),
                    )

                except Exception as error:
                    restoration_errors.append(
                        f"{source}: {error}"
                    )

finally:
    # This second-level verification runs regardless
    # of command success or simulation exceptions.
    pass


# ---------------------------------------
# Restoration integrity validation
# ---------------------------------------

post_state: dict[str, dict[str, Any]] = {}

missing_after_restore: list[str] = []
hash_mismatches: list[str] = []
size_mismatches: list[str] = []

for repository_path in eligible_paths:
    absolute_path = (
        ROOT
        / Path(repository_path)
    )

    if not absolute_path.is_file():
        missing_after_restore.append(
            repository_path
        )
        continue

    post_state[repository_path] = {
        "size_bytes": absolute_path.stat().st_size,
        "sha256": sha256_file(
            absolute_path
        ),
    }

    if (
        post_state[repository_path]["sha256"]
        != pre_state[repository_path]["sha256"]
    ):
        hash_mismatches.append(
            repository_path
        )

    if (
        post_state[repository_path]["size_bytes"]
        != pre_state[repository_path]["size_bytes"]
    ):
        size_mismatches.append(
            repository_path
        )

restoration_integrity_passed = not any(
    (
        restoration_errors,
        missing_after_restore,
        hash_mismatches,
        size_mismatches,
    )
)

baseline_passed = (
    bool(baseline_results)
    and all(
        result["passed"]
        for result in baseline_results
    )
)

simulation_passed = (
    bool(simulation_results)
    and all(
        result["passed"]
        for result in simulation_results
    )
)

if not restoration_integrity_passed:
    final_verdict = "FAIL"
    archive_decision = (
        "BLOCKED_RESTORATION_INTEGRITY_FAILURE"
    )
    decision_basis = (
        "One or more snapshot files were not restored "
        "exactly to their pre-simulation state."
    )

elif not baseline_passed:
    final_verdict = "PARTIAL"
    archive_decision = (
        "BLOCKED_BASELINE_VALIDATION_FAILURE"
    )
    decision_basis = (
        "The repository baseline did not pass all "
        "available validation commands. Archive safety "
        "cannot be authorised from an unstable baseline."
    )

elif not simulation_passed:
    final_verdict = "FAIL"
    archive_decision = (
        "BLOCKED_SIMULATION_VALIDATION_FAILURE"
    )
    decision_basis = (
        "The baseline passed, but validation failed while "
        "the 72 archive candidates were temporarily absent."
    )

else:
    final_verdict = "PASS"
    archive_decision = (
        "AUTHORISED_FOR_GOVERNED_ARCHIVE"
    )
    decision_basis = (
        "Baseline validation passed, simulated archive "
        "validation passed, and every candidate was "
        "restored byte-for-byte."
    )


# ---------------------------------------
# Per-file results
# ---------------------------------------

output_rows: list[
    dict[str, str]
] = []

for row in eligible_rows:
    repository_path = normalise_path(
        row["snapshot_path"]
    )

    output_rows.append(
        {
            "snapshot_path": repository_path,
            "active_counterpart": clean(
                row.get(
                    "active_counterpart"
                )
            ),
            "pre_size_bytes": str(
                pre_state[
                    repository_path
                ]["size_bytes"]
            ),
            "pre_sha256": pre_state[
                repository_path
            ]["sha256"],
            "restored_exists": str(
                repository_path
                not in missing_after_restore
            ).upper(),
            "restored_size_match": str(
                repository_path
                not in size_mismatches
            ).upper(),
            "restored_hash_match": str(
                repository_path
                not in hash_mismatches
            ).upper(),
            "simulation_validation_status": (
                "PASS"
                if simulation_passed
                else "FAIL"
            ),
            "archive_decision": (
                archive_decision
            ),
        }
    )

output_rows.sort(
    key=lambda row: row[
        "snapshot_path"
    ].lower()
)


# ---------------------------------------
# Outputs
# ---------------------------------------

fieldnames = [
    "snapshot_path",
    "active_counterpart",
    "pre_size_bytes",
    "pre_sha256",
    "restored_exists",
    "restored_size_match",
    "restored_hash_match",
    "simulation_validation_status",
    "archive_decision",
]

with OUTPUT_CSV.open(
    "w",
    encoding="utf-8-sig",
    newline="",
) as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=fieldnames,
    )
    writer.writeheader()
    writer.writerows(output_rows)

summary_payload = {
    "schema_version": "1.0",
    "program": (
        "EDGEIQ Repository Recovery V2"
    ),
    "recovery_unit": (
        "RRV2 Unit 006 - Snapshot Archive "
        "Simulation and Build Validation"
    ),
    "verdict": final_verdict,
    "archive_decision": archive_decision,
    "decision_basis": decision_basis,
    "archive_candidates_simulated": len(
        eligible_paths
    ),
    "blocked_snapshots_untouched": len(
        blocked_rows
    ),
    "validation_commands": [
        {
            "name": name,
            "command": command,
        }
        for name, command in (
            validation_commands
        )
    ],
    "baseline_validation_passed": (
        baseline_passed
    ),
    "simulation_validation_passed": (
        simulation_passed
    ),
    "restoration_integrity_passed": (
        restoration_integrity_passed
    ),
    "restored_file_count": (
        len(eligible_paths)
        - len(missing_after_restore)
    ),
    "missing_after_restore": (
        missing_after_restore
    ),
    "hash_mismatches": hash_mismatches,
    "size_mismatches": size_mismatches,
    "restoration_errors": (
        restoration_errors
    ),
    "baseline_results": baseline_results,
    "simulation_results": (
        simulation_results
    ),
    "duration_seconds": round(
        time.time() - simulation_started,
        3,
    ),
}

with OUTPUT_JSON.open(
    "w",
    encoding="utf-8",
) as handle:
    json.dump(
        {
            "summary": summary_payload,
            "snapshot_results": (
                output_rows
            ),
        },
        handle,
        indent=2,
        ensure_ascii=False,
    )
    handle.write("\n")


def command_table(
    title: str,
    results: list[dict[str, Any]],
) -> list[str]:
    lines = [
        f"## {title}",
        "",
        (
            "| Validation | Exit Code | "
            "Duration Seconds | Result | Log |"
        ),
        (
            "|---|---:|---:|---|---|"
        ),
    ]

    for result in results:
        status = (
            "PASS"
            if result["passed"]
            else "FAIL"
        )

        lines.append(
            "| "
            f"`{result['name']}` | "
            f"{result['exit_code']} | "
            f"{result['duration_seconds']} | "
            f"`{status}` | "
            f"`{result['log_path']}` |"
        )

    lines.append("")

    return lines


report_lines: list[str] = [
    "# EDGEIQ Snapshot Archive Simulation V1",
    "",
    "## Status",
    "",
    f"**VERDICT: {final_verdict}**",
    "",
    "## Archive Decision",
    "",
    f"**{archive_decision}**",
    "",
    decision_basis,
    "",
    "## Scope",
    "",
    (
        "- Archive candidates simulated: "
        f"**{len(eligible_paths)}**"
    ),
    (
        "- Blocked snapshots left untouched: "
        f"**{len(blocked_rows)}**"
    ),
    (
        "- Candidate files restored: "
        f"**{len(eligible_paths) - len(missing_after_restore)}**"
    ),
    (
        "- Restoration integrity: "
        f"**{'PASS' if restoration_integrity_passed else 'FAIL'}**"
    ),
    "",
    (
        "The candidate files were temporarily moved "
        "outside the repository, validated while absent "
        "and restored in a guaranteed restoration block."
    ),
    "",
    (
        "No candidate remains moved, deleted or archived "
        "by this simulation."
    ),
    "",
]

report_lines.extend(
    command_table(
        "Baseline Validation",
        baseline_results,
    )
)

report_lines.extend(
    command_table(
        "Simulated Archive Validation",
        simulation_results,
    )
)

report_lines.extend(
    [
        "## Restoration Validation",
        "",
        (
            f"- Missing files: "
            f"**{len(missing_after_restore)}**"
        ),
        (
            f"- Hash mismatches: "
            f"**{len(hash_mismatches)}**"
        ),
        (
            f"- Size mismatches: "
            f"**{len(size_mismatches)}**"
        ),
        (
            f"- Restoration errors: "
            f"**{len(restoration_errors)}**"
        ),
        "",
        "## Protected Snapshots",
        "",
        (
            "The four snapshots with operational script "
            "references and the one snapshot without an "
            "active counterpart were excluded from the "
            "simulation."
        ),
        "",
        "## Governance",
        "",
        (
            "This simulation does not itself archive, "
            "delete, stage or commit any snapshot."
        ),
        "",
        "## Next Recovery Unit",
        "",
    ]
)

if (
    archive_decision
    == "AUTHORISED_FOR_GOVERNED_ARCHIVE"
):
    report_lines.extend(
        [
            (
                "**RRV2 Unit 007 - Governed Snapshot "
                "Archive Execution**"
            ),
            "",
            (
                "Move the 72 authorised historical "
                "snapshots into a governed repository "
                "archive, update the canonical recovery "
                "manifest, rerun validation and create "
                "the first Repository Recovery V2 commit."
            ),
            "",
        ]
    )
else:
    report_lines.extend(
        [
            (
                "**RRV2 Unit 006A - Validation Failure "
                "Investigation**"
            ),
            "",
            (
                "Inspect the generated validation logs "
                "and identify whether the failure is a "
                "baseline defect, simulated archive "
                "dependency or restoration problem."
            ),
            "",
        ]
    )

REPORT_MD.write_text(
    "\n".join(report_lines),
    encoding="utf-8",
)

print(
    f"VERDICT={final_verdict}"
)
print(
    f"ARCHIVE_DECISION={archive_decision}"
)
print(
    "ARCHIVE_CANDIDATES_SIMULATED="
    f"{len(eligible_paths)}"
)
print(
    "BLOCKED_SNAPSHOTS_UNTOUCHED="
    f"{len(blocked_rows)}"
)
print(
    "BASELINE_VALIDATION_PASSED="
    f"{str(baseline_passed).upper()}"
)
print(
    "SIMULATION_VALIDATION_PASSED="
    f"{str(simulation_passed).upper()}"
)
print(
    "RESTORATION_INTEGRITY_PASSED="
    f"{str(restoration_integrity_passed).upper()}"
)
print(
    "RESTORED_FILE_COUNT="
    f"{len(eligible_paths) - len(missing_after_restore)}"
)
print(
    f"MISSING_AFTER_RESTORE="
    f"{len(missing_after_restore)}"
)
print(
    f"HASH_MISMATCHES="
    f"{len(hash_mismatches)}"
)
print(
    f"RESTORATION_ERRORS="
    f"{len(restoration_errors)}"
)
print(f"CSV={OUTPUT_CSV}")
print(f"JSON={OUTPUT_JSON}")
print(f"REPORT={REPORT_MD}")

if not restoration_integrity_passed:
    raise RuntimeError(
        "Snapshot restoration integrity failed."
    )
