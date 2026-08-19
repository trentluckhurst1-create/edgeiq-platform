from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
RACE_ENTRY = ROOT / "public" / "data" / "edgeiq_race_entry_fact_v1.csv"

OUT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "live-projection"
)
OUT_DIR.mkdir(parents=True, exist_ok=True)

JSON_OUT = OUT_DIR / "edgeiq_race_entry_snapshot_schema_trace_v1.json"
MD_OUT = OUT_DIR / "edgeiq_race_entry_snapshot_schema_trace_v1.md"


def read_header(path: Path) -> list[str]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            return [value.strip() for value in next(reader)]
        except StopIteration:
            return []


def count_rows(path: Path) -> int:
    if not path.exists():
        return 0

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for row in reader if any(value.strip() for value in row))


def find_candidate_files() -> list[Path]:
    candidates: list[Path] = []

    search_roots = [
        ROOT / "scripts",
        ROOT / "contracts" / "performance-intelligence",
    ]

    required_terms = (
        "race_entry",
        "projected_performance",
        "snapshot",
        "suitability",
        "context",
    )

    for search_root in search_roots:
        if not search_root.exists():
            continue

        for path in search_root.rglob("*"):
            if not path.is_file():
                continue

            if path.suffix.lower() not in {".py", ".json", ".md"}:
                continue

            name_lower = path.name.lower()
            try:
                text_lower = path.read_text(
                    encoding="utf-8",
                    errors="replace",
                ).lower()
            except OSError:
                continue

            if (
                "edgeiq_race_entry_fact_v1" in text_lower
                or "race_entry_projected_performance" in text_lower
                or any(term in name_lower for term in required_terms)
            ):
                candidates.append(path)

    return sorted(set(candidates), key=lambda item: str(item).lower())


def extract_column_evidence(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")

    quoted_tokens = sorted(
        {
            match.group(1)
            for match in re.finditer(
                r"""["']([A-Za-z][A-Za-z0-9_]{2,80})["']""",
                text,
            )
        }
    )

    likely_columns = [
        token
        for token in quoted_tokens
        if any(
            marker in token.lower()
            for marker in (
                "race",
                "horse",
                "runner",
                "entry",
                "track",
                "surface",
                "distance",
                "class",
                "date",
                "time",
                "status",
                "barrier",
                "weight",
                "jockey",
                "trainer",
                "rating",
                "suitability",
                "context",
                "performance",
            )
        )
    ]

    references_race_entry = (
        "edgeiq_race_entry_fact_v1" in text
        or "race_entry_fact" in text
    )

    references_projected = (
        "projected_performance" in text
        or "race_entry_projected" in text
    )

    references_snapshot = "snapshot" in text.lower()
    references_suitability = "suitability" in text.lower()
    references_context = "context" in text.lower()

    return {
        "file": str(path.relative_to(ROOT)),
        "references_race_entry": references_race_entry,
        "references_projected_performance": references_projected,
        "references_snapshot": references_snapshot,
        "references_suitability": references_suitability,
        "references_context": references_context,
        "likely_column_tokens": likely_columns,
    }


def main() -> None:
    actual_columns = read_header(RACE_ENTRY)
    row_count = count_rows(RACE_ENTRY)

    candidate_files = find_candidate_files()
    evidence = [extract_column_evidence(path) for path in candidate_files]

    all_referenced_tokens = sorted(
        {
            column
            for item in evidence
            for column in item["likely_column_tokens"]
        }
    )

    actual_lookup = {column.lower(): column for column in actual_columns}

    referenced_present = [
        token
        for token in all_referenced_tokens
        if token.lower() in actual_lookup
    ]

    referenced_missing = [
        token
        for token in all_referenced_tokens
        if token.lower() not in actual_lookup
    ]

    likely_active_builders = [
        item
        for item in evidence
        if item["file"].lower().endswith(".py")
        and (
            item["references_projected_performance"]
            or item["references_snapshot"]
            or item["references_suitability"]
            or item["references_context"]
        )
    ]

    result = {
        "status": "EDGEIQ_RACE_ENTRY_SNAPSHOT_SCHEMA_TRACE_COMPLETE",
        "race_entry_file": str(RACE_ENTRY.relative_to(ROOT)),
        "race_entry_exists": RACE_ENTRY.exists(),
        "race_entry_rows": row_count,
        "actual_columns": actual_columns,
        "candidate_file_count": len(candidate_files),
        "likely_active_builders": likely_active_builders,
        "referenced_tokens_present_in_current_schema": referenced_present,
        "referenced_tokens_missing_from_current_schema": referenced_missing,
        "all_candidate_files": evidence,
    }

    JSON_OUT.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    lines: list[str] = [
        "# EDGEIQ Race-Entry Snapshot Schema Trace V1",
        "",
        f"Status: `{result['status']}`",
        "",
        "## Current Race-Entry Fact",
        "",
        f"- File: `{result['race_entry_file']}`",
        f"- Exists: `{result['race_entry_exists']}`",
        f"- Rows: `{result['race_entry_rows']}`",
        "",
        "## Current Columns",
        "",
    ]

    if actual_columns:
        lines.extend(f"- `{column}`" for column in actual_columns)
    else:
        lines.append("- No columns found.")

    lines.extend(
        [
            "",
            "## Likely Active Builders",
            "",
        ]
    )

    if likely_active_builders:
        for item in likely_active_builders:
            lines.append(f"### `{item['file']}`")
            lines.append("")
            lines.append(
                "- Race-entry reference: "
                f"`{item['references_race_entry']}`"
            )
            lines.append(
                "- Projected-performance reference: "
                f"`{item['references_projected_performance']}`"
            )
            lines.append(
                f"- Snapshot reference: `{item['references_snapshot']}`"
            )
            lines.append(
                f"- Suitability reference: `{item['references_suitability']}`"
            )
            lines.append(
                f"- Context reference: `{item['references_context']}`"
            )
            lines.append("")
            lines.append("Likely referenced columns:")
            lines.append("")
            if item["likely_column_tokens"]:
                lines.extend(
                    f"- `{column}`"
                    for column in item["likely_column_tokens"]
                )
            else:
                lines.append("- No likely column literals detected.")
            lines.append("")
    else:
        lines.append("- No likely active builder detected.")

    lines.extend(
        [
            "## Referenced Tokens Missing From Current Schema",
            "",
        ]
    )

    if referenced_missing:
        lines.extend(f"- `{column}`" for column in referenced_missing)
    else:
        lines.append("- None detected.")

    lines.extend(
        [
            "",
            "## Required Decision",
            "",
            "Use this evidence to patch the active snapshot/context builder "
            "to consume the current governed race-entry schema.",
            "",
            "Do not add fake columns to the canonical race-entry fact.",
            "",
            "Do not weaken horse-history or EPI eligibility rules.",
            "",
        ]
    )

    MD_OUT.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": result["status"],
        "race_entry_rows": row_count,
        "actual_column_count": len(actual_columns),
        "candidate_file_count": len(candidate_files),
        "likely_active_builder_count": len(likely_active_builders),
        "json_report": str(JSON_OUT),
        "markdown_report": str(MD_OUT),
    }, indent=2))


if __name__ == "__main__":
    main()
