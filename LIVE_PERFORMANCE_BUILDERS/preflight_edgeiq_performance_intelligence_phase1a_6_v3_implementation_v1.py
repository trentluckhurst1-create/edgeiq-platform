from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path.cwd().resolve()

PHASE = "EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE1A_6_V3_IMPLEMENTATION_PREFLIGHT_V1"

SCRIPT_OUT = (
    ROOT
    / "scripts"
    / "preflight_edgeiq_performance_intelligence_phase1a_6_v3_implementation_v1.py"
)

DOC_ROOT = ROOT / "docs" / "performance-intelligence"
V3_ROOT = (
    DOC_ROOT
    / "warehouse-v2"
    / "historical-observation-warehouse-v3"
)

REPORT_JSON = DOC_ROOT / f"{PHASE}_REPORT.json"
REPORT_MD = DOC_ROOT / f"{PHASE}_REPORT.md"
INVENTORY_CSV = DOC_ROOT / f"{PHASE}_INVENTORY.csv"
REFERENCES_CSV = DOC_ROOT / f"{PHASE}_PATH_REFERENCES.csv"
AUDIT_JSON = DOC_ROOT / f"{PHASE}_AUDIT.json"
AUDIT_MD = DOC_ROOT / f"{PHASE}_AUDIT.md"

EXPECTED_COMMIT = "8c607b0"
EXPECTED_PHYSICAL_ROWS = 879_784
EXPECTED_UNIQUE_RAW_KEYS = 879_695
EXPECTED_DUPLICATE_GROUPS = 89
EXPECTED_DUPLICATE_EXCESS_ROWS = 89

CANDIDATE_FILES = [
    ROOT / "scripts" / "rebuild_edgeiq_historical_observation_warehouse_v3.py",
    ROOT / "scripts" / "checkpoint_edgeiq_performance_intelligence_phase1a_5_historical_observation_correction_specification_v1.py",
]

PHASE_1A5_PATTERNS = [
    "*PHASE1A_5*",
    "*PHASE_1A_5*",
    "*HISTORICAL_OBSERVATION_CORRECTION_SPECIFICATION*",
    "*historical*observation*correction*specification*",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def git_output(*args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = (result.stdout or result.stderr).strip()
    return result.returncode, output


def classify_path_reference(raw_value: str) -> str:
    value = raw_value.lower()

    if "graphql" in value and any(
        token in value
        for token in ("consolidated", "warehouse", "canonical", "master")
    ):
        return "GRAPHQL_AUTHORITY_CANDIDATE"

    if "graphql" in value and any(
        token in value for token in ("monthly", "month", "legacy")
    ):
        return "GRAPHQL_EXCLUDED_SOURCE_CANDIDATE"

    if any(token in value for token in ("speed", "sectional", "split")):
        return "ENRICHMENT_CANDIDATE"

    if any(token in value for token in ("live", "upcoming", "three_day", "three-day")):
        return "LIVE_OR_UPCOMING_CANDIDATE"

    if any(token in value for token in ("checkpoint", "backup", "before_")):
        return "CHECKPOINT_OR_BACKUP_CANDIDATE"

    return "OTHER_PATH_REFERENCE"


def extract_python_references(path: Path) -> list[dict[str, str]]:
    references: list[dict[str, str]] = []

    if not path.exists() or path.suffix.lower() != ".py":
        return references

    text = path.read_text(encoding="utf-8", errors="replace")

    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        references.append(
            {
                "source_file": relative(path),
                "line_number": str(exc.lineno or ""),
                "reference_type": "PYTHON_SYNTAX_ERROR",
                "classification": "ERROR",
                "raw_value": str(exc),
            }
        )
        return references

    for node in ast.walk(tree):
        values: list[str] = []

        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            values.append(node.value)

        elif isinstance(node, ast.JoinedStr):
            literal_parts = [
                part.value
                for part in node.values
                if isinstance(part, ast.Constant) and isinstance(part.value, str)
            ]
            if literal_parts:
                values.append("".join(literal_parts))

        for value in values:
            normalised = value.strip()

            if not normalised:
                continue

            looks_like_path = (
                "/" in normalised
                or "\\" in normalised
                or normalised.lower().endswith(
                    (".csv", ".json", ".md", ".txt", ".parquet")
                )
            )

            relevant_word = any(
                token in normalised.lower()
                for token in (
                    "graphql",
                    "historical",
                    "observation",
                    "warehouse",
                    "speed",
                    "sectional",
                    "live",
                    "upcoming",
                    "checkpoint",
                    "backup",
                )
            )

            if not (looks_like_path and relevant_word):
                continue

            references.append(
                {
                    "source_file": relative(path),
                    "line_number": str(getattr(node, "lineno", "")),
                    "reference_type": "PYTHON_STRING_LITERAL",
                    "classification": classify_path_reference(normalised),
                    "raw_value": normalised,
                }
            )

    return references


def extract_text_references(path: Path) -> list[dict[str, str]]:
    references: list[dict[str, str]] = []

    if not path.exists() or path.suffix.lower() not in {
        ".md",
        ".json",
        ".txt",
        ".csv",
    }:
        return references

    text = path.read_text(encoding="utf-8", errors="replace")

    path_pattern = re.compile(
        r"""(?ix)
        (?:
            [A-Z]:[\\/][^"'<>\r\n]+
            |
            (?:docs|data|public|outputs|scripts|contracts)[\\/][^"'<>\r\n,]+
        )
        """
    )

    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in path_pattern.findall(line):
            value = match.strip().rstrip(").]}")

            references.append(
                {
                    "source_file": relative(path),
                    "line_number": str(line_number),
                    "reference_type": "TEXT_PATH_REFERENCE",
                    "classification": classify_path_reference(value),
                    "raw_value": value,
                }
            )

    return references


def discover_phase_1a5_files() -> list[Path]:
    discovered: dict[str, Path] = {}

    for pattern in PHASE_1A5_PATTERNS:
        for path in DOC_ROOT.rglob(pattern):
            if path.is_file():
                discovered[str(path.resolve()).lower()] = path

    return sorted(discovered.values(), key=lambda item: relative(item).lower())


def discover_v3_files() -> list[Path]:
    discovered: dict[str, Path] = {}

    for path in CANDIDATE_FILES:
        if path.exists() and path.is_file():
            discovered[str(path.resolve()).lower()] = path

    if V3_ROOT.exists():
        for path in V3_ROOT.rglob("*"):
            if path.is_file():
                discovered[str(path.resolve()).lower()] = path

    return sorted(discovered.values(), key=lambda item: relative(item).lower())


def build_inventory(paths: list[Path], group: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for path in paths:
        stat = path.stat()

        rows.append(
            {
                "group": group,
                "path": relative(path),
                "suffix": path.suffix.lower(),
                "bytes": stat.st_size,
                "sha256": sha256_file(path),
                "modified_utc": datetime.fromtimestamp(
                    stat.st_mtime,
                    tz=timezone.utc,
                ).isoformat(),
            }
        )

    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    print("")
    print(PHASE)
    print("=" * len(PHASE))

    DOC_ROOT.mkdir(parents=True, exist_ok=True)

    git_head_code, git_head = git_output("rev-parse", "--short", "HEAD")
    git_log_code, git_log = git_output("log", "-1", "--oneline")
    branch_code, branch = git_output("branch", "--show-current")
    status_code, status_short = git_output("status", "--short")

    phase_1a5_files = discover_phase_1a5_files()
    v3_files = discover_v3_files()

    inventory = (
        build_inventory(phase_1a5_files, "PHASE_1A5_GOVERNANCE")
        + build_inventory(v3_files, "EXISTING_V3_IMPLEMENTATION")
    )

    references: list[dict[str, str]] = []

    for path in phase_1a5_files + v3_files:
        if path.suffix.lower() == ".py":
            references.extend(extract_python_references(path))
        else:
            references.extend(extract_text_references(path))

    reference_counts: dict[str, int] = {}

    for row in references:
        classification = row["classification"]
        reference_counts[classification] = (
            reference_counts.get(classification, 0) + 1
        )

    existing_v3_builder = (
        ROOT / "scripts" / "rebuild_edgeiq_historical_observation_warehouse_v3.py"
    )

    checks = [
        {
            "check": "git_head_readable",
            "expected": "git command succeeds",
            "actual": git_head,
            "status": "PASS" if git_head_code == 0 else "FAIL",
        },
        {
            "check": "phase_1a5_commit_is_ancestor",
            "expected": EXPECTED_COMMIT,
            "actual": "",
            "status": "PENDING",
        },
        {
            "check": "phase_1a5_governance_files_found",
            "expected": "> 0",
            "actual": len(phase_1a5_files),
            "status": "PASS" if phase_1a5_files else "FAIL",
        },
        {
            "check": "existing_v3_builder_found",
            "expected": "True",
            "actual": existing_v3_builder.exists(),
            "status": "PASS" if existing_v3_builder.exists() else "FAIL",
        },
        {
            "check": "existing_v3_output_directory_found",
            "expected": "True",
            "actual": V3_ROOT.exists(),
            "status": "PASS" if V3_ROOT.exists() else "FAIL",
        },
        {
            "check": "authority_path_reference_found",
            "expected": "> 0",
            "actual": reference_counts.get(
                "GRAPHQL_AUTHORITY_CANDIDATE",
                0,
            ),
            "status": (
                "PASS"
                if reference_counts.get("GRAPHQL_AUTHORITY_CANDIDATE", 0) > 0
                else "REVIEW"
            ),
        },
    ]

    ancestor_code, _ = git_output(
        "merge-base",
        "--is-ancestor",
        EXPECTED_COMMIT,
        "HEAD",
    )

    checks[1]["actual"] = ancestor_code == 0
    checks[1]["status"] = "PASS" if ancestor_code == 0 else "FAIL"

    failing = [
        row
        for row in checks
        if row["status"] == "FAIL"
    ]

    review = [
        row
        for row in checks
        if row["status"] == "REVIEW"
    ]

    overall_status = "PASS"

    if failing:
        overall_status = "FAIL"
    elif review:
        overall_status = "REVIEW"

    report = {
        "phase": PHASE,
        "generated_utc": utc_now(),
        "repository_root": str(ROOT),
        "branch": branch if branch_code == 0 else "",
        "git_head": git_head,
        "git_log": git_log,
        "expected_governance_commit": EXPECTED_COMMIT,
        "expected_population_contract": {
            "physical_rows": EXPECTED_PHYSICAL_ROWS,
            "unique_raw_keys": EXPECTED_UNIQUE_RAW_KEYS,
            "duplicate_groups": EXPECTED_DUPLICATE_GROUPS,
            "duplicate_excess_rows": EXPECTED_DUPLICATE_EXCESS_ROWS,
        },
        "phase_1a5_files_found": len(phase_1a5_files),
        "existing_v3_files_found": len(v3_files),
        "path_references_found": len(references),
        "path_reference_classification_counts": reference_counts,
        "remaining_worktree_line_count": (
            len(status_short.splitlines())
            if status_code == 0 and status_short
            else 0
        ),
        "checks": checks,
        "overall_status": overall_status,
        "governance": {
            "v2_modification_permitted": False,
            "v3_overwrite_permitted": False,
            "production_build_executed": False,
            "source_data_modified": False,
            "purpose": (
                "Inventory and inspect existing Phase 1A.6 implementation "
                "before any builder is changed or executed."
            ),
        },
    }

    REPORT_JSON.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    audit = {
        "phase": PHASE,
        "generated_utc": report["generated_utc"],
        "overall_status": overall_status,
        "checks": checks,
    }

    AUDIT_JSON.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    write_csv(
        INVENTORY_CSV,
        inventory,
        [
            "group",
            "path",
            "suffix",
            "bytes",
            "sha256",
            "modified_utc",
        ],
    )

    write_csv(
        REFERENCES_CSV,
        references,
        [
            "source_file",
            "line_number",
            "reference_type",
            "classification",
            "raw_value",
        ],
    )

    report_lines = [
        f"# {PHASE}",
        "",
        f"- Generated UTC: `{report['generated_utc']}`",
        f"- Overall status: **{overall_status}**",
        f"- Branch: `{report['branch']}`",
        f"- HEAD: `{report['git_log']}`",
        f"- Required governance commit: `{EXPECTED_COMMIT}`",
        "",
        "## Population contract",
        "",
        f"- Physical rows: `{EXPECTED_PHYSICAL_ROWS:,}`",
        f"- Unique raw keys: `{EXPECTED_UNIQUE_RAW_KEYS:,}`",
        f"- Duplicate groups: `{EXPECTED_DUPLICATE_GROUPS:,}`",
        f"- Duplicate excess rows: `{EXPECTED_DUPLICATE_EXCESS_ROWS:,}`",
        "",
        "## Existing implementation inventory",
        "",
        f"- Phase 1A.5 files found: `{len(phase_1a5_files)}`",
        f"- Existing V3 files found: `{len(v3_files)}`",
        f"- Path references found: `{len(references)}`",
        "",
        "## Governance",
        "",
        "- V2 was not modified.",
        "- The existing V3 builder was not modified.",
        "- The existing V3 builder was not executed.",
        "- No source data was modified.",
        "- No production warehouse was rebuilt.",
        "",
        "## Checks",
        "",
        "| Check | Expected | Actual | Status |",
        "|---|---|---:|---|",
    ]

    for row in checks:
        report_lines.append(
            f"| {row['check']} | {row['expected']} | "
            f"{row['actual']} | {row['status']} |"
        )

    report_lines.extend(
        [
            "",
            "## Next decision",
            "",
            (
                "Review the inventory and extracted path references. "
                "Only then determine whether the existing V3 builder "
                "conforms to the committed Phase 1A.5 specification, "
                "requires correction, or must be replaced."
            ),
            "",
        ]
    )

    REPORT_MD.write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    audit_lines = [
        f"# {PHASE} — Audit",
        "",
        f"## Overall status: {overall_status}",
        "",
    ]

    for row in checks:
        audit_lines.append(
            f"- `{row['status']}` — {row['check']}: "
            f"expected `{row['expected']}`, actual `{row['actual']}`"
        )

    audit_lines.append("")

    AUDIT_MD.write_text(
        "\n".join(audit_lines),
        encoding="utf-8",
    )

    print("")
    print(f"OVERALL STATUS: {overall_status}")
    print(f"HEAD: {git_log}")
    print(f"PHASE 1A.5 FILES FOUND: {len(phase_1a5_files):,}")
    print(f"EXISTING V3 FILES FOUND: {len(v3_files):,}")
    print(f"PATH REFERENCES FOUND: {len(references):,}")
    print("")
    print("REFERENCE CLASSIFICATIONS")

    for key in sorted(reference_counts):
        print(f"  {key}: {reference_counts[key]:,}")

    print("")
    print("FILES WRITTEN")
    for path in (
        REPORT_JSON,
        REPORT_MD,
        INVENTORY_CSV,
        REFERENCES_CSV,
        AUDIT_JSON,
        AUDIT_MD,
    ):
        print(f"  {relative(path)}")

    print("")
    print("NO V2 OR V3 BUILDER WAS MODIFIED OR EXECUTED.")
    print("")

    return 1 if overall_status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
