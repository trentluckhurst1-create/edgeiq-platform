from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any


ROOT = Path.cwd().resolve()
RECOVERY_ROOT = ROOT / "docs" / "repository-recovery-v2"

OUTPUT_CSV = (
    RECOVERY_ROOT /
    "edgeiq_repository_recovery_v2_final_closure_v1.csv"
)
OUTPUT_JSON = (
    RECOVERY_ROOT /
    "edgeiq_repository_recovery_v2_final_closure_v1.json"
)
OUTPUT_MD = (
    RECOVERY_ROOT /
    "EDGEIQ_REPOSITORY_RECOVERY_V2_FINAL_CLOSURE_V1.md"
)

UNIT_009_JSON = (
    RECOVERY_ROOT /
    "edgeiq_protected_snapshot_remediation_plan_v1.json"
)
UNIT_010_JSON = (
    RECOVERY_ROOT /
    "edgeiq_protected_snapshot_remediation_execution_v1.json"
)

EXPECTED_REMEDIATION_COMMIT = "5837c7b"
BUILD_TIMEOUT_SECONDS = 300
STARTED = time.monotonic()


EXPECTED_UNIT_010_COMMIT_FILES = [
    (
        "docs/repository-recovery-v2/"
        "EDGEIQ_PROTECTED_SNAPSHOT_REMEDIATION_EXECUTION_V1.md"
    ),
    (
        "docs/repository-recovery-v2/"
        "EDGEIQ_PROTECTED_SNAPSHOT_REMEDIATION_PLAN_V1.md"
    ),
    (
        "docs/repository-recovery-v2/archive/protected-snapshots/"
        "src/edgeiq-os/race/"
        "RaceFileV3_STABLE_BEFORE_COMPONENT_EXTRACTION_20260709.tsx"
    ),
    (
        "docs/repository-recovery-v2/archive/protected-snapshots/"
        "src/edgeiq-os/styles/"
        "edgeiqOsV2_STABLE_BEFORE_COMPONENT_EXTRACTION_20260709.css"
    ),
    (
        "docs/repository-recovery-v2/"
        "edgeiq_protected_snapshot_remediation_execution_v1.csv"
    ),
    (
        "docs/repository-recovery-v2/"
        "edgeiq_protected_snapshot_remediation_execution_v1.json"
    ),
    (
        "docs/repository-recovery-v2/"
        "edgeiq_protected_snapshot_remediation_plan_v1.csv"
    ),
    (
        "docs/repository-recovery-v2/"
        "edgeiq_protected_snapshot_remediation_plan_v1.json"
    ),
    "scripts/fix_edgeiq_product_polish_encoding_v1.py",
    "scripts/fix_edgeiq_product_polish_trademark_glyphs_v1.py",
    "scripts/run_edgeiq_repository_recovery_v2_units_009_010.py",
]


ARCHIVED_SNAPSHOTS = [
    (
        "docs/repository-recovery-v2/archive/protected-snapshots/"
        "src/edgeiq-os/race/"
        "RaceFileV3_STABLE_BEFORE_COMPONENT_EXTRACTION_20260709.tsx"
    ),
    (
        "docs/repository-recovery-v2/archive/protected-snapshots/"
        "src/edgeiq-os/styles/"
        "edgeiqOsV2_STABLE_BEFORE_COMPONENT_EXTRACTION_20260709.css"
    ),
]


ORIGINAL_ARCHIVE_CANDIDATES = [
    (
        "src/edgeiq-os/race/"
        "RaceFileV3_STABLE_BEFORE_COMPONENT_EXTRACTION_20260709.tsx"
    ),
    (
        "src/edgeiq-os/styles/"
        "edgeiqOsV2_STABLE_BEFORE_COMPONENT_EXTRACTION_20260709.css"
    ),
]


RETAINED_ROLLBACK_SNAPSHOTS = [
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


REFERENCE_CHECKS = [
    {
        "path": "scripts/fix_edgeiq_product_polish_encoding_v1.py",
        "active_reference": "src/edgeiq-os/race/RaceFileV3.tsx",
        "obsolete_reference": (
            "src/edgeiq-os/race/"
            "RaceFileV3_STABLE_BEFORE_COMPONENT_EXTRACTION_20260709.tsx"
        ),
    },
    {
        "path": (
            "scripts/fix_edgeiq_product_polish_trademark_glyphs_v1.py"
        ),
        "active_reference": "src/edgeiq-os/race/RaceFileV3.tsx",
        "obsolete_reference": (
            "src/edgeiq-os/race/"
            "RaceFileV3_STABLE_BEFORE_COMPONENT_EXTRACTION_20260709.tsx"
        ),
    },
]


def log(message: str) -> None:
    elapsed = time.monotonic() - STARTED
    print(f"[{elapsed:7.2f}s] {message}", flush=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def run_git(arguments: list[str]) -> str:
    process = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )

    if process.returncode != 0:
        raise RuntimeError(
            f"Git command failed: git {' '.join(arguments)}\n"
            f"STDOUT:\n{process.stdout}\n"
            f"STDERR:\n{process.stderr}"
        )

    return process.stdout.strip()


def add_check(
    checks: list[dict[str, Any]],
    check_id: str,
    category: str,
    subject: str,
    expected: str,
    actual: str,
    passed: bool,
    detail: str,
) -> None:
    checks.append(
        {
            "check_id": check_id,
            "category": category,
            "subject": subject,
            "expected": expected,
            "actual": actual,
            "result": "PASS" if passed else "FAIL",
            "detail": detail,
        }
    )

    log(
        f"{'PASS' if passed else 'FAIL'} "
        f"{check_id} {subject}"
    )

    if not passed:
        raise RuntimeError(
            f"Closure check failed: {check_id} — {detail}"
        )


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Required JSON evidence is missing: "
            f"{path.relative_to(ROOT).as_posix()}"
        )

    return json.loads(path.read_text(encoding="utf-8"))


def run_production_build() -> tuple[str, int]:
    log(
        "BUILD starting fresh production build "
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

    combined = "\n".join(
        part
        for part in [
            process.stdout or "",
            process.stderr or "",
        ]
        if part
    )

    if process.returncode != 0:
        raise RuntimeError(
            "Fresh production build failed.\n"
            + combined[-12000:]
        )

    log("BUILD fresh production build PASS")

    return combined, process.returncode


def write_outputs(
    checks: list[dict[str, Any]],
    build_output: str,
) -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "check_id",
        "category",
        "subject",
        "expected",
        "actual",
        "result",
        "detail",
    ]

    with OUTPUT_CSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(checks)

    summary = {
        "total_checks": len(checks),
        "passed_checks": sum(
            row["result"] == "PASS"
            for row in checks
        ),
        "failed_checks": sum(
            row["result"] == "FAIL"
            for row in checks
        ),
        "archived_snapshots_verified": len(
            ARCHIVED_SNAPSHOTS
        ),
        "retained_snapshots_verified": len(
            RETAINED_ROLLBACK_SNAPSHOTS
        ),
        "reference_redirects_verified": len(
            REFERENCE_CHECKS
        ),
        "remediation_commit": EXPECTED_REMEDIATION_COMMIT,
        "production_build_pass": True,
        "runtime_seconds": round(
            time.monotonic() - STARTED,
            3,
        ),
    }

    payload = {
        "unit": "RRV2_UNIT_011",
        "name": "Repository Recovery V2 Final Closure",
        "version": "V1",
        "verdict": "PASS",
        "summary": summary,
        "checks": checks,
        "build_output_tail": build_output[-12000:],
    }

    OUTPUT_JSON.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    lines = [
        "# EDGEIQ Repository Recovery V2 Final Closure V1",
        "",
        "## Verdict",
        "",
        "**PASS**",
        "",
        "## Closure Summary",
        "",
        f"- Total checks: {summary['total_checks']}",
        f"- Passed checks: {summary['passed_checks']}",
        f"- Failed checks: {summary['failed_checks']}",
        (
            "- Remediation commit verified: "
            f"`{EXPECTED_REMEDIATION_COMMIT}`"
        ),
        (
            "- Archived snapshots verified: "
            f"{summary['archived_snapshots_verified']}"
        ),
        (
            "- Retained rollback snapshots verified: "
            f"{summary['retained_snapshots_verified']}"
        ),
        (
            "- Reference redirects verified: "
            f"{summary['reference_redirects_verified']}"
        ),
        "- Fresh production build: PASS",
        (
            "- Runtime seconds: "
            f"{summary['runtime_seconds']}"
        ),
        "",
        "## Closure Checks",
        "",
        "| Check | Category | Subject | Result |",
        "|---|---|---|---|",
    ]

    for row in checks:
        lines.append(
            f"| {row['check_id']} "
            f"| {row['category']} "
            f"| `{row['subject']}` "
            f"| {row['result']} |"
        )

    lines.extend(
        [
            "",
            "## Final Governance Position",
            "",
            (
                "Repository Recovery V2 Units 001–011 are "
                "closed at the governed repository-recovery layer."
            ),
            "",
            (
                "The three RaceIntelligence rollback snapshots "
                "remain protected until their executable rollback "
                "dependencies are separately migrated or retired."
            ),
            "",
            (
                "No unrelated working-tree files were staged, "
                "modified or committed by Unit 011."
            ),
            "",
        ]
    )

    OUTPUT_MD.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> int:
    checks: list[dict[str, Any]] = []

    log("RRV2_UNIT_011 START")

    staged_before = run_git(
        ["diff", "--cached", "--name-only"]
    ).splitlines()

    add_check(
        checks,
        "C001",
        "GIT_PREFLIGHT",
        "staging_area",
        "empty",
        str(len(staged_before)),
        len(staged_before) == 0,
        (
            "The staging area must be empty before "
            "Unit 011 begins."
        ),
    )

    unit_009 = read_json(UNIT_009_JSON)
    unit_010 = read_json(UNIT_010_JSON)

    add_check(
        checks,
        "C002",
        "MACHINE_EVIDENCE",
        UNIT_009_JSON.relative_to(ROOT).as_posix(),
        "PASS",
        str(unit_009.get("verdict")),
        unit_009.get("verdict") == "PASS",
        "Unit 009 machine verdict must be PASS.",
    )

    add_check(
        checks,
        "C003",
        "MACHINE_EVIDENCE",
        UNIT_010_JSON.relative_to(ROOT).as_posix(),
        "PASS",
        str(unit_010.get("verdict")),
        unit_010.get("verdict") == "PASS",
        "Unit 010 machine verdict must be PASS.",
    )

    summary = unit_010.get("summary", {})

    expected_summary = {
        "references_redirected": 2,
        "snapshots_archived": 2,
        "snapshots_retained": 3,
        "build_pass": True,
        "rollback_required": False,
    }

    for index, (key, expected) in enumerate(
        expected_summary.items(),
        start=4,
    ):
        actual = summary.get(key)

        add_check(
            checks,
            f"C{index:03d}",
            "UNIT_010_SUMMARY",
            key,
            str(expected),
            str(actual),
            actual == expected,
            f"Unit 010 summary field {key} must match.",
        )

    resolved_commit = run_git(
        ["rev-parse", "--short", EXPECTED_REMEDIATION_COMMIT]
    )

    add_check(
        checks,
        "C009",
        "GIT_COMMIT",
        EXPECTED_REMEDIATION_COMMIT,
        EXPECTED_REMEDIATION_COMMIT,
        resolved_commit,
        resolved_commit == EXPECTED_REMEDIATION_COMMIT,
        "The governed remediation commit must exist.",
    )

    committed_files = sorted(
        run_git(
            [
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                EXPECTED_REMEDIATION_COMMIT,
            ]
        ).splitlines()
    )

    expected_commit_files = sorted(
        EXPECTED_UNIT_010_COMMIT_FILES
    )

    add_check(
        checks,
        "C010",
        "GIT_COMMIT",
        "remediation_commit_file_set",
        str(len(expected_commit_files)),
        str(len(committed_files)),
        committed_files == expected_commit_files,
        (
            "Commit 5837c7b must contain exactly the "
            "11 governed Unit 009/010 files."
        ),
    )

    execution_rows = unit_010.get("execution", [])

    archived_execution = {
        row.get("destination_path"): row
        for row in execution_rows
        if row.get("action") == "ARCHIVE"
    }

    next_id = 11

    for relative_path in ARCHIVED_SNAPSHOTS:
        path = ROOT / relative_path
        exists = path.is_file()

        add_check(
            checks,
            f"C{next_id:03d}",
            "ARCHIVE",
            relative_path,
            "exists",
            str(exists),
            exists,
            "Archived snapshot must exist.",
        )
        next_id += 1

        digest = sha256_file(path)
        evidence = archived_execution.get(relative_path)
        expected_digest = (
            evidence.get("post_sha256")
            if evidence
            else None
        )

        add_check(
            checks,
            f"C{next_id:03d}",
            "ARCHIVE_HASH",
            relative_path,
            str(expected_digest),
            digest,
            (
                expected_digest is not None
                and digest == expected_digest
            ),
            (
                "Archive SHA256 must match the Unit 010 "
                "execution evidence."
            ),
        )
        next_id += 1

    for relative_path in ORIGINAL_ARCHIVE_CANDIDATES:
        exists = (ROOT / relative_path).exists()

        add_check(
            checks,
            f"C{next_id:03d}",
            "ORIGINAL_PATH",
            relative_path,
            "absent",
            str(exists),
            not exists,
            (
                "Original archive candidate must no longer "
                "exist in the active source tree."
            ),
        )
        next_id += 1

    for relative_path in RETAINED_ROLLBACK_SNAPSHOTS:
        exists = (ROOT / relative_path).is_file()

        add_check(
            checks,
            f"C{next_id:03d}",
            "ROLLBACK_PROTECTION",
            relative_path,
            "exists",
            str(exists),
            exists,
            (
                "Rollback-dependent protected snapshot "
                "must remain available."
            ),
        )
        next_id += 1

    for reference_check in REFERENCE_CHECKS:
        path = ROOT / reference_check["path"]
        text = path.read_text(encoding="utf-8")

        active_count = text.count(
            reference_check["active_reference"]
        )
        obsolete_count = text.count(
            reference_check["obsolete_reference"]
        )

        add_check(
            checks,
            f"C{next_id:03d}",
            "REFERENCE_REDIRECT",
            reference_check["path"],
            "active=1; obsolete=0",
            (
                f"active={active_count}; "
                f"obsolete={obsolete_count}"
            ),
            active_count == 1 and obsolete_count == 0,
            (
                "Script must reference the active RaceFileV3 "
                "source exactly once and the archived snapshot "
                "zero times."
            ),
        )
        next_id += 1

    build_output, return_code = run_production_build()

    add_check(
        checks,
        f"C{next_id:03d}",
        "PRODUCTION_BUILD",
        "npm run build",
        "return_code=0",
        f"return_code={return_code}",
        return_code == 0,
        "Fresh production build must pass.",
    )

    write_outputs(checks, build_output)

    log("RRV2_UNIT_011 VERDICT=PASS")
    log(f"TOTAL_CHECKS={len(checks)}")
    log("FAILED_CHECKS=0")
    log("FRESH_PRODUCTION_BUILD=PASS")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.TimeoutExpired as exc:
        log(
            f"TIMEOUT command exceeded "
            f"{exc.timeout} seconds"
        )
        traceback.print_exc()
        raise SystemExit(124)
    except Exception:
        log("RRV2_UNIT_011 VERDICT=FAIL")
        traceback.print_exc()
        raise SystemExit(1)
