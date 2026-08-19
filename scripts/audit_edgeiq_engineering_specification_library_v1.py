from __future__ import annotations

import csv
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINEERING = ROOT / "docs" / "beta-specifications" / "ENGINEERING"
OUT_DIR = ROOT / "public" / "data"
AUDIT_TXT = OUT_DIR / "edgeiq_engineering_specification_library_v1_audit.txt"
AUDIT_JSON = OUT_DIR / "edgeiq_engineering_specification_library_v1_audit.json"
INVENTORY_CSV = OUT_DIR / "edgeiq_engineering_specification_library_v1_inventory.csv"
PASS_STATUS = "EDGEIQ_ENGINEERING_SPECIFICATION_LIBRARY_V1_AUDIT_PASS"

REQUIRED_SECTIONS = [
    "Document Control",
    "Purpose",
    "Scope",
    "Explicit Non-Goals",
    "Locked Product Decisions",
    "Current Repository Trace",
    "Active File Ownership",
    "Approved Target Architecture",
    "Component Hierarchy",
    "React Component Contracts",
    "TypeScript Interfaces",
    "Canonical Data Contracts",
    "Builder and Service Ownership",
    "Data Lineage",
    "State Ownership",
    "Routing and Navigation",
    "Desktop Layout Geometry",
    "Responsive Behaviour",
    "Design Tokens",
    "Typography",
    "Spacing",
    "Borders and Surfaces",
    "Table Specifications",
    "Component-by-Component Rendering Rules",
    "Interaction Behaviour",
    "Hover Behaviour",
    "Keyboard Behaviour",
    "Selection Behaviour",
    "Sorting",
    "Filtering",
    "Searching",
    "Expansion and Collapse",
    "Loading States",
    "Empty States",
    "Unavailable States",
    "Stale Data States",
    "Error States",
    "Scratching Behaviour",
    "Accessibility",
    "Performance Budget",
    "Builder Tests",
    "TypeScript Unit Tests",
    "Integration Tests",
    "Data Contract Audits",
    "Visual Regression Requirements",
    "Screenshot Acceptance Matrix",
    "Migration Plan",
    "Files Expected to Change During Implementation",
    "Files That Must Not Change",
    "Codex Implementation Sequence",
    "Acceptance Criteria",
    "Completion Report Contract",
    "Engineering Governance",
    "Revision History",
]


@dataclass(frozen=True)
class Spec:
    spec_id: str
    workspace: str
    path: Path
    min_bytes: int
    locked_columns: str | None = None


SPECS = [
    Spec(
        "MASTER-001",
        "Design System",
        ENGINEERING / "MASTER" / "MASTER-001_EDGEIQ_BETA_ENGINEERING_DESIGN_SYSTEM.md",
        25_000,
    ),
    Spec(
        "BETA-001",
        "FORM GUIDE",
        ENGINEERING / "WORKSPACES" / "BETA-001_FORM_GUIDE_ENGINEERING.md",
        25_000,
        "NO|SILKS|LAST 5|HORSE|TRAINER|JOCKEY|WT|BAR|DAYS|EPI|EARLY SPEED|LATE SPEED|SUITABILITY|FORM MOMENTUM|MARKET|EDGEiQ PRICE",
    ),
    Spec(
        "BETA-002",
        "MEETINGS",
        ENGINEERING / "WORKSPACES" / "BETA-002_MEETINGS_ENGINEERING.md",
        20_000,
        "SELECT|MEETING|STATE|RAIL|TRACK|WEATHER|WIND|TEMP|RACES|DECLARED|SCRATCHINGS|FIRST|LAST|STATUS|EDGEiQ READ|OPEN",
    ),
    Spec(
        "BETA-003",
        "MEETING DETAIL",
        ENGINEERING / "WORKSPACES" / "BETA-003_MEETING_DETAIL_ENGINEERING.md",
        16_000,
        "RACE|TIME|DISTANCE|CLASS|RACE NAME|RESTRICTION|FIELD SIZE|STATUS|OPEN",
    ),
    Spec(
        "BETA-004",
        "SCRATCHINGS",
        ENGINEERING / "WORKSPACES" / "BETA-004_SCRATCHINGS_ENGINEERING.md",
        14_000,
        "RACE|NO|SILK|HORSE|TRAINER|JOCKEY|SCRATCHED AT|REASON|SOURCE|STATUS",
    ),
    Spec(
        "BETA-005",
        "GEAR CHANGES",
        ENGINEERING / "WORKSPACES" / "BETA-005_GEAR_CHANGES_ENGINEERING.md",
        14_000,
        "RACE|NO|SILK|HORSE|CHANGE|PREVIOUS|TODAY|FIRST TIME|COMMENT|SOURCE",
    ),
    Spec(
        "BETA-006",
        "TRACK",
        ENGINEERING / "WORKSPACES" / "BETA-006_TRACK_ENGINEERING.md",
        18_000,
        "METRIC|TODAY|LAST 3 MEETINGS|LAST 10 MEETINGS",
    ),
    Spec(
        "BETA-007",
        "WEATHER",
        ENGINEERING / "WORKSPACES" / "BETA-007_WEATHER_ENGINEERING.md",
        18_000,
        "TIME|WEATHER|TEMP (C)|WIND (km/h)|GUSTS (km/h)|RAIN PROB.|RAIN (mm)",
    ),
    Spec(
        "BETA-008",
        "RESULTS",
        ENGINEERING / "WORKSPACES" / "BETA-008_RESULTS_ENGINEERING.md",
        25_000,
        "RACE|TIME|WINNER|JOCKEY|TRAINER|SP (TAB)|MARGIN|TIME|TRACK|STATUS|OPEN",
    ),
    Spec(
        "BETA-009",
        "MAP",
        ENGINEERING / "WORKSPACES" / "BETA-009_MAP_ENGINEERING.md",
        22_000,
        "NO|HORSE|BARRIER|EFFECTIVE BARRIER|RUN STYLE|EARLY SPEED|PROJECTED POSITION",
    ),
    Spec(
        "BETA-010",
        "MARKET",
        ENGINEERING / "WORKSPACES" / "BETA-010_MARKET_ENGINEERING.md",
        20_000,
        "NO|HORSE|EPI|MARKET|OPEN|HIGH|LOW|MOVE|EDGEiQ PRICE|EDGE|STATUS",
    ),
    Spec(
        "BETA-011",
        "OVERVIEW",
        ENGINEERING / "WORKSPACES" / "BETA-011_OVERVIEW_ENGINEERING.md",
        20_000,
        "SECTION|EVIDENCE|SOURCE|STATUS|OPEN",
    ),
    Spec(
        "BETA-012",
        "INSIGHTS",
        ENGINEERING / "WORKSPACES" / "BETA-012_INSIGHTS_ENGINEERING.md",
        20_000,
        "NO|HORSE|KEY INSIGHT|EDGE|CONFIDENCE",
    ),
    Spec(
        "BETA-013",
        "EPI WORKSPACE",
        ENGINEERING / "WORKSPACES" / "BETA-013_EPI_WORKSPACE_ENGINEERING.md",
        22_000,
        "NO|HORSE|CURRENT EPI|RANK|FIELD AVG|DIFF|START 10|START 9|START 8|START 7|START 6|START 5|START 4|START 3|START 2|START 1",
    ),
]

OLD_ACTIVE_NAMES = {
    "BETA-001_FORM_GUIDE.md",
    "BETA-002_MEETINGS.md",
    "BETA-003_MEETING_DETAIL.md",
    "BETA-004_SCRATCHINGS.md",
    "BETA-005_GEAR_CHANGES.md",
    "BETA-006_TRACK.md",
    "BETA-007_WEATHER.md",
    "BETA-008_RESULTS.md",
    "BETA-009_MAP.md",
    "BETA-010_MARKET.md",
    "BETA-011_OVERVIEW.md",
    "BETA-012_INSIGHTS.md",
    "BETA-013_EPI_WORKSPACE.md",
}


def count_fenced(text: str, kind: str) -> int:
    return text.count(f"```{kind}")


def git_status() -> list[str]:
    proc = subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return [line for line in proc.stdout.splitlines() if line.strip()]


def inspect_spec(spec: Spec) -> tuple[dict[str, object], list[str]]:
    failures: list[str] = []
    if not spec.path.exists():
        return (
            {
                "spec_id": spec.spec_id,
                "workspace": spec.workspace,
                "path": str(spec.path),
                "bytes": 0,
                "lines": 0,
                "headings": 0,
                "typescript_blocks": 0,
                "json_blocks": 0,
                "tables": 0,
                "current_trace_present": False,
                "data_contract_present": False,
                "tests_present": False,
                "acceptance_present": False,
                "status": "FAIL",
            },
            [f"{spec.spec_id}: missing file {spec.path}"],
        )

    try:
        text = spec.path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return (
            {
                "spec_id": spec.spec_id,
                "workspace": spec.workspace,
                "path": str(spec.path),
                "bytes": spec.path.stat().st_size,
                "lines": 0,
                "headings": 0,
                "typescript_blocks": 0,
                "json_blocks": 0,
                "tables": 0,
                "current_trace_present": False,
                "data_contract_present": False,
                "tests_present": False,
                "acceptance_present": False,
                "status": "FAIL",
            },
            [f"{spec.spec_id}: UTF-8 read failed: {exc}"],
        )

    byte_count = len(text.encode("utf-8"))
    headings = sum(1 for line in text.splitlines() if line.startswith("#"))
    inventory = {
        "spec_id": spec.spec_id,
        "workspace": spec.workspace,
        "path": str(spec.path),
        "bytes": byte_count,
        "lines": len(text.splitlines()),
        "headings": headings,
        "typescript_blocks": count_fenced(text, "ts"),
        "json_blocks": count_fenced(text, "json"),
        "tables": text.count("| ---"),
        "current_trace_present": "Current Repository Trace" in text,
        "data_contract_present": "Canonical Data Contracts" in text,
        "tests_present": "Builder Tests" in text and "Integration Tests" in text,
        "acceptance_present": "Acceptance Criteria" in text,
        "status": "PASS",
    }

    if byte_count < spec.min_bytes:
        failures.append(f"{spec.spec_id}: {byte_count} bytes below minimum {spec.min_bytes}")
    if spec.spec_id.startswith("BETA"):
        for section in REQUIRED_SECTIONS:
            if f". {section}" not in text and f"## {section}" not in text:
                failures.append(f"{spec.spec_id}: missing section {section}")
        required_phrases = [
            "CURRENT IMPLEMENTATION TRACE",
            "TARGET IMPLEMENTATION CONTRACT",
            "PROPOSED TARGET PATH",
            "React",
            "display-only",
            "Data Lineage",
            "Loading States",
            "Empty States",
            "Unavailable States",
            "Stale Data States",
            "Error States",
            "Accessibility",
            "Performance Budget",
            "Acceptance Criteria",
        ]
        for phrase in required_phrases:
            if phrase not in text:
                failures.append(f"{spec.spec_id}: missing required phrase {phrase}")
        if spec.locked_columns and spec.locked_columns not in text:
            failures.append(f"{spec.spec_id}: locked column order missing or altered")
    else:
        master_phrases = [
            "EDGEiQ is professional racing intelligence software",
            "Canvas #F4F6F9",
            "Primary surface #FFFFFF",
            "No gradients",
            "No glow",
            "No dark terminal panels",
            "No stars",
            "No medals",
            "Negative means inside standard",
            "Positive means outside standard",
            "React is display-only",
            "Missing evidence remains null",
        ]
        for phrase in master_phrases:
            if phrase not in text:
                failures.append(f"MASTER-001: missing design-system phrase {phrase}")

    if failures:
        inventory["status"] = "FAIL"
    return inventory, failures


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    warnings: list[str] = []
    inventory: list[dict[str, object]] = []

    readme = ENGINEERING / "README.md"
    index = ENGINEERING / "INDEX.md"
    if not readme.exists():
        failures.append("README.md missing")
    if not index.exists():
        failures.append("INDEX.md missing")

    active_workspace_files = {p.name for p in (ENGINEERING / "WORKSPACES").glob("*.md")}
    old_active = sorted(active_workspace_files.intersection(OLD_ACTIVE_NAMES))
    if old_active:
        failures.append(f"Old outline files still active: {old_active}")

    archive = ENGINEERING / "ARCHIVE" / "OUTLINE_RECOVERY_V0"
    if not archive.exists():
        failures.append("Archive folder missing")
    elif len(list(archive.rglob("*.md"))) < 10:
        failures.append("Archive does not contain enough original outline files")

    for spec in SPECS:
        item, spec_failures = inspect_spec(spec)
        inventory.append(item)
        failures.extend(spec_failures)

    status_lines = git_status()
    unrelated_dirty = [
        line
        for line in status_lines
        if not any(
            token in line.replace("\\", "/")
            for token in [
                "docs/",
                "scripts/checkpoint_edgeiq_engineering_specification_library_v1.py",
                "scripts/audit_edgeiq_engineering_specification_library_v1.py",
                "scripts/validate_edgeiq_engineering_specification_library_v1.ps1",
                "public/data/edgeiq_engineering_specification_library_v1_",
            ]
        )
    ]
    if unrelated_dirty:
        warnings.append(
            "Pre-existing unrelated dirty worktree entries detected; audit records them but does not mutate them."
        )

    status = PASS_STATUS if not failures else "EDGEIQ_ENGINEERING_SPECIFICATION_LIBRARY_V1_AUDIT_FAIL"
    payload = {
        "status": status,
        "failures": failures,
        "warnings": warnings,
        "inventory": inventory,
        "git_status_entries": status_lines,
        "unrelated_dirty_entries": unrelated_dirty,
    }

    with INVENTORY_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "spec_id",
                "workspace",
                "path",
                "bytes",
                "lines",
                "headings",
                "typescript_blocks",
                "json_blocks",
                "tables",
                "current_trace_present",
                "data_contract_present",
                "tests_present",
                "acceptance_present",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(inventory)

    AUDIT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines = [status, "", "Failures:"]
    lines.extend(f"- {failure}" for failure in failures)
    lines.append("")
    lines.append("Warnings:")
    lines.extend(f"- {warning}" for warning in warnings)
    lines.append("")
    lines.append("Inventory:")
    lines.extend(
        f"- {item['spec_id']} {item['workspace']}: {item['bytes']} bytes, {item['lines']} lines, {item['status']}"
        for item in inventory
    )
    AUDIT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(status)
    if warnings:
        for warning in warnings:
            print(f"WARNING: {warning}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
