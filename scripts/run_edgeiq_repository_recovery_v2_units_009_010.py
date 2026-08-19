from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path.cwd().resolve()
RECOVERY_ROOT = ROOT / "docs" / "repository-recovery-v2"
ARCHIVE_ROOT = RECOVERY_ROOT / "archive" / "protected-snapshots"

UNIT_009_CSV = (
    RECOVERY_ROOT /
    "edgeiq_protected_snapshot_remediation_plan_v1.csv"
)
UNIT_009_JSON = (
    RECOVERY_ROOT /
    "edgeiq_protected_snapshot_remediation_plan_v1.json"
)
UNIT_009_REPORT = (
    RECOVERY_ROOT /
    "EDGEIQ_PROTECTED_SNAPSHOT_REMEDIATION_PLAN_V1.md"
)

UNIT_010_CSV = (
    RECOVERY_ROOT /
    "edgeiq_protected_snapshot_remediation_execution_v1.csv"
)
UNIT_010_JSON = (
    RECOVERY_ROOT /
    "edgeiq_protected_snapshot_remediation_execution_v1.json"
)
UNIT_010_REPORT = (
    RECOVERY_ROOT /
    "EDGEIQ_PROTECTED_SNAPSHOT_REMEDIATION_EXECUTION_V1.md"
)

STARTED = time.monotonic()
MAX_RUNTIME_SECONDS = 360
BUILD_TIMEOUT_SECONDS = 300


PROTECTED_SNAPSHOTS = [
    {
        "snapshot_path": (
            "src/components/"
            "RaceIntelligenceScreen_BEFORE_DNA_EXPLAINABILITY_UI_WIRE_V1.tsx"
        ),
        "dependency_class": "ROLLBACK_DEPENDENCY",
        "risk": "HIGH",
        "recommended_action": "RETAIN_UNTIL_PATCH_REMOVED",
        "active_counterpart": (
            "src/components/RaceIntelligenceScreen.tsx"
        ),
        "validation_required": (
            "Patch verification; rollback verification; repository build"
        ),
        "final_recommendation": (
            "Retain because a governed patch script still uses this file "
            "as its rollback source."
        ),
    },
    {
        "snapshot_path": (
            "src/components/"
            "RaceIntelligenceScreen_BEFORE_FACTOR_JOIN_KEY_FIX.tsx"
        ),
        "dependency_class": "ROLLBACK_DEPENDENCY",
        "risk": "HIGH",
        "recommended_action": "RETAIN_UNTIL_PATCH_REMOVED",
        "active_counterpart": (
            "src/components/RaceIntelligenceScreen.tsx"
        ),
        "validation_required": (
            "Patch verification; rollback verification; repository build"
        ),
        "final_recommendation": (
            "Retain because a governed patch script still uses this file "
            "as its rollback source."
        ),
    },
    {
        "snapshot_path": (
            "src/components/"
            "RaceIntelligenceScreen_BEFORE_FACTOR_SCORECARD_V2_PY_PATCH.tsx"
        ),
        "dependency_class": "ROLLBACK_DEPENDENCY",
        "risk": "HIGH",
        "recommended_action": "RETAIN_UNTIL_PATCH_REMOVED",
        "active_counterpart": (
            "src/components/RaceIntelligenceScreen.tsx"
        ),
        "validation_required": (
            "Patch verification; rollback verification; repository build"
        ),
        "final_recommendation": (
            "Retain because a governed patch script still uses this file "
            "as its rollback source."
        ),
    },
    {
        "snapshot_path": (
            "src/edgeiq-os/race/"
            "RaceFileV3_STABLE_BEFORE_COMPONENT_EXTRACTION_20260709.tsx"
        ),
        "dependency_class": "TEXT_REFERENCE",
        "risk": "MEDIUM",
        "recommended_action": "ARCHIVE_AFTER_VALIDATION",
        "active_counterpart": "src/edgeiq-os/race/RaceFileV3.tsx",
        "validation_required": (
            "Redirect textual references; Python compile; React build; "
            "archive verification"
        ),
        "final_recommendation": (
            "Redirect the two non-runtime script references to the active "
            "RaceFileV3 source and archive the snapshot after validation."
        ),
    },
    {
        "snapshot_path": (
            "src/edgeiq-os/styles/"
            "edgeiqOsV2_STABLE_BEFORE_COMPONENT_EXTRACTION_20260709.css"
        ),
        "dependency_class": "NONE",
        "risk": "LOW",
        "recommended_action": "ARCHIVE_AFTER_VALIDATION",
        "active_counterpart": "src/edgeiq-os/styles/edgeiqOsV2.css",
        "validation_required": (
            "Active counterpart verification; React build; archive verification"
        ),
        "final_recommendation": (
            "Archive after confirming the active edgeiqOsV2 stylesheet exists "
            "and the production build passes."
        ),
    },
]


REFERENCE_REDIRECTS = [
    {
        "script_path": (
            "scripts/fix_edgeiq_product_polish_encoding_v1.py"
        ),
        "old_reference": (
            "src/edgeiq-os/race/"
            "RaceFileV3_STABLE_BEFORE_COMPONENT_EXTRACTION_20260709.tsx"
        ),
        "new_reference": "src/edgeiq-os/race/RaceFileV3.tsx",
    },
    {
        "script_path": (
            "scripts/fix_edgeiq_product_polish_trademark_glyphs_v1.py"
        ),
        "old_reference": (
            "src/edgeiq-os/race/"
            "RaceFileV3_STABLE_BEFORE_COMPONENT_EXTRACTION_20260709.tsx"
        ),
        "new_reference": "src/edgeiq-os/race/RaceFileV3.tsx",
    },
]


ARCHIVE_CANDIDATES = [
    (
        "src/edgeiq-os/race/"
        "RaceFileV3_STABLE_BEFORE_COMPONENT_EXTRACTION_20260709.tsx"
    ),
    (
        "src/edgeiq-os/styles/"
        "edgeiqOsV2_STABLE_BEFORE_COMPONENT_EXTRACTION_20260709.css"
    ),
]


RETAINED_SNAPSHOTS = [
    (
        "src/components/"
        "RaceIntelligenceScreen_BEFORE_DNA_EXPLAINABILITY_UI_WIRE_V1.tsx"
    ),
    (
        "src/components/"
        "RaceIntelligenceScreen_BEFORE_FACTOR_JOIN_KEY_FIX.tsx"
    ),
    (
        "src/components/"
        "RaceIntelligenceScreen_BEFORE_FACTOR_SCORECARD_V2_PY_PATCH.tsx"
    ),
]


@dataclass
class ExecutionRow:
    item_type: str
    source_path: str
    destination_path: str
    action: str
    pre_sha256: str
    post_sha256: str
    result: str
    detail: str


def log(message: str) -> None:
    elapsed = time.monotonic() - STARTED
    print(f"[{elapsed:7.2f}s] {message}", flush=True)


def check_runtime() -> None:
    elapsed = time.monotonic() - STARTED
    if elapsed > MAX_RUNTIME_SECONDS:
        raise TimeoutError(
            f"Internal runtime limit exceeded: {elapsed:.2f}s"
        )


def normalise_rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def file_metadata(relative_path: str) -> dict[str, Any]:
    path = ROOT / relative_path
    exists = path.is_file()

    return {
        "snapshot_path": relative_path,
        "exists": exists,
        "file_size_bytes": path.stat().st_size if exists else 0,
        "sha256": sha256_file(path) if exists else "",
        "snapshot_type": path.suffix.lower().lstrip(".").upper(),
    }


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def assert_git_preflight() -> None:
    log("PREFLIGHT checking staged repository state")

    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
        check=True,
    )

    staged = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]

    if staged:
        raise RuntimeError(
            "Repository already has staged files. "
            "Commit or unstage them before this governed unit:\n"
            + "\n".join(staged)
        )


def validate_inputs() -> None:
    log("PREFLIGHT validating governed files")

    required = set(RETAINED_SNAPSHOTS)
    required.update(ARCHIVE_CANDIDATES)

    for redirect in REFERENCE_REDIRECTS:
        required.add(redirect["script_path"])
        required.add(redirect["new_reference"])

    required.add("package.json")

    missing = [
        relative_path
        for relative_path in sorted(required)
        if not (ROOT / relative_path).is_file()
    ]

    if missing:
        raise FileNotFoundError(
            "Required repository files are missing:\n"
            + "\n".join(missing)
        )

    for redirect in REFERENCE_REDIRECTS:
        script = ROOT / redirect["script_path"]
        text = script.read_text(
            encoding="utf-8",
            errors="strict",
        )
        count = text.count(redirect["old_reference"])

        if count != 1:
            raise RuntimeError(
                f"{redirect['script_path']} must contain exactly one "
                f"old reference; found {count}."
            )


def create_unit_009_plan() -> list[dict[str, Any]]:
    log("UNIT_009 building remediation plan")

    rows: list[dict[str, Any]] = []

    for index, decision in enumerate(
        PROTECTED_SNAPSHOTS,
        start=1,
    ):
        check_runtime()
        metadata = file_metadata(decision["snapshot_path"])

        if not metadata["exists"]:
            raise FileNotFoundError(
                f"Protected snapshot missing: "
                f"{decision['snapshot_path']}"
            )

        row = {
            **metadata,
            **decision,
            "decision_category": (
                "PROTECTED_UNTIL_MIGRATION"
                if decision["recommended_action"]
                == "RETAIN_UNTIL_PATCH_REMOVED"
                else "ARCHIVE_CANDIDATE"
            ),
        }
        rows.append(row)

        log(
            f"UNIT_009 PLAN {index}/5 "
            f"{decision['recommended_action']} "
            f"{decision['snapshot_path']}"
        )

    fieldnames = [
        "snapshot_path",
        "exists",
        "file_size_bytes",
        "sha256",
        "snapshot_type",
        "dependency_class",
        "risk",
        "decision_category",
        "recommended_action",
        "active_counterpart",
        "validation_required",
        "final_recommendation",
    ]

    write_csv(UNIT_009_CSV, rows, fieldnames)

    summary = {
        "protected_snapshot_count": len(rows),
        "retain_until_patch_removed": sum(
            row["recommended_action"]
            == "RETAIN_UNTIL_PATCH_REMOVED"
            for row in rows
        ),
        "archive_after_validation": sum(
            row["recommended_action"]
            == "ARCHIVE_AFTER_VALIDATION"
            for row in rows
        ),
        "rollback_dependencies": sum(
            row["dependency_class"] == "ROLLBACK_DEPENDENCY"
            for row in rows
        ),
        "text_references": sum(
            row["dependency_class"] == "TEXT_REFERENCE"
            for row in rows
        ),
        "no_dependencies": sum(
            row["dependency_class"] == "NONE"
            for row in rows
        ),
        "high_risk": sum(row["risk"] == "HIGH" for row in rows),
        "medium_risk": sum(row["risk"] == "MEDIUM" for row in rows),
        "low_risk": sum(row["risk"] == "LOW" for row in rows),
    }

    write_json(
        UNIT_009_JSON,
        {
            "unit": "RRV2_UNIT_009",
            "version": "V1",
            "verdict": "PASS",
            "summary": summary,
            "decisions": rows,
        },
    )

    report_lines = [
        "# EDGEIQ Protected Snapshot Remediation Plan V1",
        "",
        "## Verdict",
        "",
        "**PASS**",
        "",
        "## Purpose",
        "",
        (
            "Define the governed remediation action for all five "
            "remaining protected snapshots."
        ),
        "",
        "## Decision Summary",
        "",
        f"- Protected snapshots: {summary['protected_snapshot_count']}",
        (
            "- Retain until patch removal: "
            f"{summary['retain_until_patch_removed']}"
        ),
        (
            "- Archive after validation: "
            f"{summary['archive_after_validation']}"
        ),
        "",
        "## Decisions",
        "",
        "| Snapshot | Dependency | Risk | Action |",
        "|---|---|---|---|",
    ]

    for row in rows:
        report_lines.append(
            f"| `{row['snapshot_path']}` "
            f"| {row['dependency_class']} "
            f"| {row['risk']} "
            f"| {row['recommended_action']} |"
        )

    report_lines.extend(
        [
            "",
            "## Governance",
            "",
            (
                "Unit 009 is planning-only. Repository remediation is "
                "performed and validated by Unit 010."
            ),
            "",
        ]
    )

    UNIT_009_REPORT.write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    log("UNIT_009_COMPLETE verdict=PASS outputs=3")
    return rows


def archive_destination(relative_path: str) -> Path:
    return ARCHIVE_ROOT / relative_path


def run_python_compile(paths: list[Path]) -> None:
    log("VALIDATION compiling changed Python scripts")

    command = [
        sys.executable,
        "-m",
        "py_compile",
        *[str(path) for path in paths],
    ]

    subprocess.run(
        command,
        cwd=ROOT,
        timeout=60,
        check=True,
    )


def run_build() -> tuple[str, str]:
    log(
        f"VALIDATION starting npm production build "
        f"timeout={BUILD_TIMEOUT_SECONDS}s"
    )

    npm_command = "npm.cmd" if os.name == "nt" else "npm"

    process = subprocess.run(
        [npm_command, "run", "build"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=BUILD_TIMEOUT_SECONDS,
        check=False,
    )

    stdout = process.stdout or ""
    stderr = process.stderr or ""

    build_stdout = RECOVERY_ROOT / "UNIT_010_BUILD_STDOUT.log"
    build_stderr = RECOVERY_ROOT / "UNIT_010_BUILD_STDERR.log"

    build_stdout.write_text(stdout, encoding="utf-8")
    build_stderr.write_text(stderr, encoding="utf-8")

    if process.returncode != 0:
        raise RuntimeError(
            "Production build failed. See:\n"
            f"{normalise_rel(build_stdout)}\n"
            f"{normalise_rel(build_stderr)}"
        )

    log("VALIDATION npm production build PASS")
    return (
        normalise_rel(build_stdout),
        normalise_rel(build_stderr),
    )


def apply_unit_010() -> tuple[
    list[ExecutionRow],
    str,
    str,
]:
    log("UNIT_010 starting governed remediation")

    execution_rows: list[ExecutionRow] = []
    backup_root = Path(
        tempfile.mkdtemp(prefix="edgeiq_rrv2_unit010_")
    )

    changed_scripts: list[Path] = []
    moved_files: list[tuple[Path, Path]] = []

    try:
        log("UNIT_010A redirecting obsolete textual references")

        for index, redirect in enumerate(
            REFERENCE_REDIRECTS,
            start=1,
        ):
            check_runtime()

            script = ROOT / redirect["script_path"]
            backup = backup_root / redirect["script_path"]
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(script, backup)

            before_hash = sha256_file(script)
            original = script.read_text(encoding="utf-8")

            updated = original.replace(
                redirect["old_reference"],
                redirect["new_reference"],
            )

            if updated == original:
                raise RuntimeError(
                    f"No replacement applied to "
                    f"{redirect['script_path']}"
                )

            if redirect["old_reference"] in updated:
                raise RuntimeError(
                    f"Old reference remains in "
                    f"{redirect['script_path']}"
                )

            script.write_text(updated, encoding="utf-8")
            after_hash = sha256_file(script)
            changed_scripts.append(script)

            execution_rows.append(
                ExecutionRow(
                    item_type="SCRIPT_REFERENCE",
                    source_path=redirect["script_path"],
                    destination_path=redirect["script_path"],
                    action="REDIRECT_TO_ACTIVE_SOURCE",
                    pre_sha256=before_hash,
                    post_sha256=after_hash,
                    result="PASS",
                    detail=(
                        f"{redirect['old_reference']} -> "
                        f"{redirect['new_reference']}"
                    ),
                )
            )

            log(
                f"REFERENCE_REDIRECT {index}/2 "
                f"{redirect['script_path']}"
            )

        run_python_compile(changed_scripts)

        log("UNIT_010B archiving approved candidates")

        for index, relative_path in enumerate(
            ARCHIVE_CANDIDATES,
            start=1,
        ):
            check_runtime()

            source = ROOT / relative_path
            destination = archive_destination(relative_path)

            if destination.exists():
                raise FileExistsError(
                    f"Archive destination already exists: "
                    f"{normalise_rel(destination)}"
                )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            before_hash = sha256_file(source)
            shutil.move(str(source), str(destination))
            moved_files.append((source, destination))

            if source.exists():
                raise RuntimeError(
                    f"Source still exists after archive move: "
                    f"{relative_path}"
                )

            if not destination.is_file():
                raise RuntimeError(
                    f"Archive destination missing: "
                    f"{normalise_rel(destination)}"
                )

            after_hash = sha256_file(destination)

            if after_hash != before_hash:
                raise RuntimeError(
                    f"Archive hash mismatch: {relative_path}"
                )

            execution_rows.append(
                ExecutionRow(
                    item_type="PROTECTED_SNAPSHOT",
                    source_path=relative_path,
                    destination_path=normalise_rel(destination),
                    action="ARCHIVE",
                    pre_sha256=before_hash,
                    post_sha256=after_hash,
                    result="PASS",
                    detail="Moved with SHA256 identity preserved.",
                )
            )

            log(
                f"ARCHIVE {index}/2 "
                f"{relative_path}"
            )

        log("UNIT_010C verifying retained rollback snapshots")

        for index, relative_path in enumerate(
            RETAINED_SNAPSHOTS,
            start=1,
        ):
            path = ROOT / relative_path

            if not path.is_file():
                raise FileNotFoundError(
                    f"Retained rollback snapshot missing: "
                    f"{relative_path}"
                )

            digest = sha256_file(path)

            execution_rows.append(
                ExecutionRow(
                    item_type="PROTECTED_SNAPSHOT",
                    source_path=relative_path,
                    destination_path=relative_path,
                    action="RETAIN",
                    pre_sha256=digest,
                    post_sha256=digest,
                    result="PASS",
                    detail=(
                        "Retained because executable rollback "
                        "dependency remains."
                    ),
                )
            )

            log(
                f"RETAIN_VERIFY {index}/3 "
                f"{relative_path}"
            )

        build_stdout, build_stderr = run_build()

        log("UNIT_010D validating references after remediation")

        old_snapshot_reference = ARCHIVE_CANDIDATES[0]

        for redirect in REFERENCE_REDIRECTS:
            text = (
                ROOT /
                redirect["script_path"]
            ).read_text(encoding="utf-8")

            if old_snapshot_reference in text:
                raise RuntimeError(
                    f"Archived RaceFileV3 reference remains in "
                    f"{redirect['script_path']}"
                )

            if redirect["new_reference"] not in text:
                raise RuntimeError(
                    f"Active RaceFileV3 reference missing from "
                    f"{redirect['script_path']}"
                )

        log("UNIT_010 remediation and validation PASS")

        return (
            execution_rows,
            build_stdout,
            build_stderr,
        )

    except Exception:
        log("UNIT_010 failure detected; starting automatic rollback")

        for source, destination in reversed(moved_files):
            if destination.exists() and not source.exists():
                source.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(destination), str(source))
                log(
                    f"ROLLBACK restored archived source "
                    f"{normalise_rel(source)}"
                )

        for script in reversed(changed_scripts):
            backup = backup_root / normalise_rel(script)
            if backup.is_file():
                shutil.copy2(backup, script)
                log(
                    f"ROLLBACK restored script "
                    f"{normalise_rel(script)}"
                )

        raise

    finally:
        shutil.rmtree(backup_root, ignore_errors=True)


def write_unit_010_outputs(
    execution_rows: list[ExecutionRow],
    build_stdout: str,
    build_stderr: str,
) -> None:
    rows = [asdict(row) for row in execution_rows]

    fieldnames = [
        "item_type",
        "source_path",
        "destination_path",
        "action",
        "pre_sha256",
        "post_sha256",
        "result",
        "detail",
    ]

    write_csv(UNIT_010_CSV, rows, fieldnames)

    summary = {
        "execution_row_count": len(rows),
        "references_redirected": sum(
            row["action"] == "REDIRECT_TO_ACTIVE_SOURCE"
            for row in rows
        ),
        "snapshots_archived": sum(
            row["action"] == "ARCHIVE"
            for row in rows
        ),
        "snapshots_retained": sum(
            row["action"] == "RETAIN"
            for row in rows
        ),
        "build_pass": True,
        "rollback_required": False,
        "runtime_seconds": round(
            time.monotonic() - STARTED,
            3,
        ),
    }

    write_json(
        UNIT_010_JSON,
        {
            "unit": "RRV2_UNIT_010",
            "version": "V1",
            "verdict": "PASS",
            "summary": summary,
            "build_stdout": build_stdout,
            "build_stderr": build_stderr,
            "execution": rows,
        },
    )

    report_lines = [
        "# EDGEIQ Protected Snapshot Remediation Execution V1",
        "",
        "## Verdict",
        "",
        "**PASS**",
        "",
        "## Execution Summary",
        "",
        (
            f"- Script references redirected: "
            f"{summary['references_redirected']}"
        ),
        (
            f"- Protected snapshots archived: "
            f"{summary['snapshots_archived']}"
        ),
        (
            f"- Protected rollback snapshots retained: "
            f"{summary['snapshots_retained']}"
        ),
        "- Production build: PASS",
        f"- Runtime seconds: {summary['runtime_seconds']}",
        "",
        "## Executed Actions",
        "",
        "| Type | Source | Action | Destination | Result |",
        "|---|---|---|---|---|",
    ]

    for row in rows:
        report_lines.append(
            f"| {row['item_type']} "
            f"| `{row['source_path']}` "
            f"| {row['action']} "
            f"| `{row['destination_path']}` "
            f"| {row['result']} |"
        )

    report_lines.extend(
        [
            "",
            "## Validation",
            "",
            "- Changed Python scripts compiled successfully.",
            "- Archived files retained identical SHA256 hashes.",
            "- All three executable rollback snapshots remain in place.",
            "- Obsolete RaceFileV3 snapshot references were removed.",
            "- Active RaceFileV3 references are present.",
            "- Production build completed successfully.",
            "",
            "## Build Evidence",
            "",
            f"- Standard output: `{build_stdout}`",
            f"- Standard error: `{build_stderr}`",
            "",
        ]
    )

    UNIT_010_REPORT.write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )


def main() -> int:
    log(
        "RRV2_UNITS_009_010 START "
        f"hard_internal_limit={MAX_RUNTIME_SECONDS}s"
    )

    assert_git_preflight()
    validate_inputs()

    create_unit_009_plan()

    execution_rows, build_stdout, build_stderr = (
        apply_unit_010()
    )

    write_unit_010_outputs(
        execution_rows,
        build_stdout,
        build_stderr,
    )

    log("===== UNITS 009 AND 010 COMPLETE =====")
    log("VERDICT=PASS")
    log("UNIT_009_VERDICT=PASS")
    log("UNIT_010_VERDICT=PASS")
    log("REFERENCES_REDIRECTED=2")
    log("SNAPSHOTS_ARCHIVED=2")
    log("SNAPSHOTS_RETAINED=3")
    log("BUILD_PASS=TRUE")
    log(
        f"RUNTIME_SECONDS="
        f"{time.monotonic() - STARTED:.3f}"
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.TimeoutExpired as exc:
        log(
            f"TIMEOUT command exceeded {exc.timeout} seconds"
        )
        traceback.print_exc()
        raise SystemExit(124)
    except Exception:
        log("VERDICT=FAIL")
        traceback.print_exc()
        raise SystemExit(1)
