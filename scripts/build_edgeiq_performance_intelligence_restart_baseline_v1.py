from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path.cwd().resolve()

PROGRAM_ROOT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "restart-v1"
)

INVENTORY_CSV = (
    PROGRAM_ROOT
    / "edgeiq_performance_intelligence_restart_inventory_v1.csv"
)

BASELINE_JSON = (
    PROGRAM_ROOT
    / "edgeiq_performance_intelligence_restart_baseline_v1.json"
)

BASELINE_MD = (
    PROGRAM_ROOT
    / "EDGEIQ_PERFORMANCE_INTELLIGENCE_RESTART_BASELINE_V1.md"
)

GIT_HISTORY_TXT = (
    PROGRAM_ROOT
    / "edgeiq_performance_intelligence_restart_git_history_v1.txt"
)

STARTED = time.monotonic()


SEARCH_ROOTS = [
    "docs/performance-intelligence",
    "contracts/performance-intelligence",
    "outputs/performance-intelligence",
    "public/data",
    "scripts",
]


IMPORTANT_EXACT_PATHS = [
    (
        "docs/performance-intelligence/"
        "canonical-identities/"
        "edgeiq_canonical_performance_identity_v1.csv"
    ),
    (
        "docs/performance-intelligence/"
        "canonical-identities/"
        "edgeiq_canonical_horse_identity_v1.csv"
    ),
    (
        "docs/performance-intelligence/"
        "canonical-identities/"
        "edgeiq_canonical_race_identity_v1.csv"
    ),
    (
        "docs/performance-intelligence/"
        "canonical-identities/"
        "edgeiq_canonical_meeting_identity_v1.csv"
    ),
    (
        "docs/performance-intelligence/"
        "canonical-identities/"
        "edgeiq_canonical_track_identity_v1.csv"
    ),
    (
        "docs/performance-intelligence/"
        "epi/"
        "edgeiq_epi_performance_fact_v1.csv"
    ),
    (
        "docs/performance-intelligence/"
        "lengths-v-standard/"
        "edgeiq_runner_lengths_v_standard_fact_v1.csv"
    ),
    "public/data/edgeiq_standard_time_fact_v1.csv",
    "public/data/edgeiq_performance_intelligence_base_fact_v1.csv",
    "public/data/edgeiq_performance_normalisation_fact_v1.csv",
    "public/data/edgeiq_performance_rating_base_fact_v1.csv",
    "public/data/edgeiq_horse_performance_observation_fact_v1.csv",
    "public/data/edgeiq_horse_performance_rating_fact_v1.csv",
    "public/data/edgeiq_horse_performance_aggregate_fact_v1.csv",
    (
        "public/data/"
        "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv"
    ),
]


IMPORTANT_NAME_TOKENS = [
    "performance_intelligence",
    "performance-intelligence",
    "standard_time",
    "standard-time",
    "lengths_v_standard",
    "lengths-v-standard",
    "canonical_performance",
    "performance_identity",
    "epi_performance",
    "performance_fact",
    "normalisation_fact",
    "rating_fact",
    "horse_performance",
    "race_entry_projection",
    "identity_profiler",
    "racingcom_ingestion",
    "racingcom-ingestion",
]


SCRIPT_NAME_TOKENS = [
    "performance",
    "standard_time",
    "lengths_v_standard",
    "identity",
    "epi",
    "rating",
    "racingcom",
]


def log(message: str) -> None:
    elapsed = time.monotonic() - STARTED
    print(f"[{elapsed:7.2f}s] {message}", flush=True)


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


def git_output(arguments: list[str]) -> str:
    process = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )

    if process.returncode != 0:
        raise RuntimeError(
            f"Git command failed: git {' '.join(arguments)}\n"
            f"STDOUT:\n{process.stdout}\n"
            f"STDERR:\n{process.stderr}"
        )

    return process.stdout.strip()


def relevant_path(relative_path: str) -> bool:
    lowered = relative_path.lower()

    if lowered.startswith(
        "docs/performance-intelligence/restart-v1/"
    ):
        return False

    if lowered.startswith("scripts/"):
        filename = Path(lowered).name

        return any(
            token in filename
            for token in SCRIPT_NAME_TOKENS
        )

    return any(
        token in lowered
        for token in IMPORTANT_NAME_TOKENS
    )


def classify(relative_path: str) -> str:
    lowered = relative_path.lower()
    suffix = Path(lowered).suffix

    if lowered.startswith("scripts/"):
        return "BUILDER_OR_AUDIT_SCRIPT"

    if lowered.startswith("contracts/"):
        return "CONTRACT"

    if lowered.startswith("outputs/"):
        return "RAW_OR_INTERMEDIATE_OUTPUT"

    if lowered.startswith("public/data/"):
        return "PUBLIC_RUNTIME_DATA"

    if "canonical-identities" in lowered:
        return "CANONICAL_IDENTITY"

    if "standard-time" in lowered or "standard_time" in lowered:
        return "STANDARD_TIME"

    if (
        "lengths-v-standard" in lowered
        or "lengths_v_standard" in lowered
    ):
        return "LENGTHS_V_STANDARD"

    if "race-entry-projection" in lowered:
        return "RACE_ENTRY_PROJECTION"

    if "identity-profiler" in lowered:
        return "IDENTITY_PROFILER"

    if suffix in {".md", ".txt"}:
        return "EVIDENCE_OR_REPORT"

    if suffix in {".csv", ".json"}:
        return "DATA_OR_AUDIT"

    return "OTHER_PERFORMANCE_INTELLIGENCE"


def inspect_csv(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "csv_status": "",
        "csv_data_rows": "",
        "csv_columns": "",
        "csv_parse_error": "",
    }

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
            errors="replace",
        ) as handle:
            reader = csv.reader(handle)
            header = next(reader, None)

            if header is None:
                result["csv_status"] = "EMPTY_FILE"
                result["csv_data_rows"] = 0
                result["csv_columns"] = 0
                return result

            row_count = sum(1 for _ in reader)

            result["csv_data_rows"] = row_count
            result["csv_columns"] = len(header)

            if row_count == 0:
                result["csv_status"] = "HEADER_ONLY"
            else:
                result["csv_status"] = "POPULATED"

    except Exception as exc:
        result["csv_status"] = "PARSE_ERROR"
        result["csv_parse_error"] = (
            f"{type(exc).__name__}: {exc}"
        )

    return result


def build_inventory() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    discovered: set[str] = set()

    for root_name in SEARCH_ROOTS:
        search_root = ROOT / root_name

        if not search_root.exists():
            continue

        if search_root.is_file():
            candidates = [search_root]
        else:
            candidates = sorted(
                path
                for path in search_root.rglob("*")
                if path.is_file()
            )

        for path in candidates:
            relative_path = path.relative_to(ROOT).as_posix()

            if relative_path in discovered:
                continue

            if not relevant_path(relative_path):
                continue

            discovered.add(relative_path)

            stat = path.stat()
            suffix = path.suffix.lower()

            row: dict[str, Any] = {
                "relative_path": relative_path,
                "category": classify(relative_path),
                "extension": suffix,
                "size_bytes": stat.st_size,
                "modified_utc": datetime.fromtimestamp(
                    stat.st_mtime,
                    tz=timezone.utc,
                ).isoformat(),
                "sha256": sha256_file(path),
                "csv_status": "",
                "csv_data_rows": "",
                "csv_columns": "",
                "csv_parse_error": "",
                "important_exact_path": (
                    "TRUE"
                    if relative_path in IMPORTANT_EXACT_PATHS
                    else "FALSE"
                ),
            }

            if suffix == ".csv":
                row.update(inspect_csv(path))

            rows.append(row)

    return sorted(
        rows,
        key=lambda row: (
            row["category"],
            row["relative_path"],
        ),
    )


def main() -> int:
    log("PI_RESTART_UNIT_001 START")

    PROGRAM_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    staged_files = git_output(
        ["diff", "--cached", "--name-only"]
    ).splitlines()

    if staged_files:
        raise RuntimeError(
            "Staging area is not empty. "
            "Refusing to mix governed work."
        )

    log("INVENTORY scanning Performance Intelligence artefacts")
    inventory = build_inventory()

    if not inventory:
        raise RuntimeError(
            "No Performance Intelligence artefacts were found."
        )

    inventory_paths = {
        row["relative_path"]
        for row in inventory
    }

    important_path_status = []

    for relative_path in IMPORTANT_EXACT_PATHS:
        path = ROOT / relative_path
        present = path.is_file()

        matched_row = next(
            (
                row
                for row in inventory
                if row["relative_path"] == relative_path
            ),
            None,
        )

        important_path_status.append(
            {
                "relative_path": relative_path,
                "present": present,
                "size_bytes": (
                    matched_row["size_bytes"]
                    if matched_row
                    else 0
                ),
                "csv_status": (
                    matched_row["csv_status"]
                    if matched_row
                    else ""
                ),
                "csv_data_rows": (
                    matched_row["csv_data_rows"]
                    if matched_row
                    else ""
                ),
            }
        )

    fieldnames = [
        "relative_path",
        "category",
        "extension",
        "size_bytes",
        "modified_utc",
        "sha256",
        "csv_status",
        "csv_data_rows",
        "csv_columns",
        "csv_parse_error",
        "important_exact_path",
    ]

    with INVENTORY_CSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(inventory)

    log("GIT collecting relevant history")

    git_history = git_output(
        [
            "log",
            "--date=iso",
            "--pretty=format:%h|%ad|%s",
            "-n",
            "250",
            "--",
            "docs/performance-intelligence",
            "contracts/performance-intelligence",
            "outputs/performance-intelligence",
            "public/data",
            "scripts",
        ]
    )

    GIT_HISTORY_TXT.write_text(
        git_history + "\n",
        encoding="utf-8",
    )

    populated_csvs = [
        row
        for row in inventory
        if row["csv_status"] == "POPULATED"
    ]

    header_only_csvs = [
        row
        for row in inventory
        if row["csv_status"] == "HEADER_ONLY"
    ]

    empty_csvs = [
        row
        for row in inventory
        if row["csv_status"] == "EMPTY_FILE"
    ]

    parse_error_csvs = [
        row
        for row in inventory
        if row["csv_status"] == "PARSE_ERROR"
    ]

    missing_important = [
        item
        for item in important_path_status
        if not item["present"]
    ]

    present_important = [
        item
        for item in important_path_status
        if item["present"]
    ]

    zero_row_important = [
        item
        for item in important_path_status
        if item["present"]
        and item["csv_status"] in {
            "HEADER_ONLY",
            "EMPTY_FILE",
        }
    ]

    categories: dict[str, int] = {}

    for row in inventory:
        categories[row["category"]] = (
            categories.get(row["category"], 0) + 1
        )

    if zero_row_important:
        next_action = (
            "FORENSICALLY_TRACE_FIRST_ZERO_ROW_CANONICAL_OUTPUT"
        )
        next_reason = (
            "At least one expected canonical Performance "
            "Intelligence CSV exists but contains zero data rows."
        )
    elif missing_important:
        next_action = (
            "TRACE_FIRST_MISSING_CANONICAL_OUTPUT_AND_BUILDER"
        )
        next_reason = (
            "At least one expected canonical Performance "
            "Intelligence output is absent."
        )
    else:
        next_action = (
            "VALIDATE_LINEAGE_AND_REPRODUCIBILITY_OF_PRESENT_OUTPUTS"
        )
        next_reason = (
            "All expected exact outputs are present and no "
            "important CSV is empty; lineage validation is next."
        )

    current_head = git_output(["rev-parse", "HEAD"])
    short_head = git_output(["rev-parse", "--short", "HEAD"])
    branch = git_output(
        ["rev-parse", "--abbrev-ref", "HEAD"]
    )

    summary = {
        "inventory_file_count": len(inventory),
        "script_count": sum(
            row["category"] == "BUILDER_OR_AUDIT_SCRIPT"
            for row in inventory
        ),
        "csv_count": sum(
            row["extension"] == ".csv"
            for row in inventory
        ),
        "json_count": sum(
            row["extension"] == ".json"
            for row in inventory
        ),
        "markdown_count": sum(
            row["extension"] == ".md"
            for row in inventory
        ),
        "populated_csv_count": len(populated_csvs),
        "header_only_csv_count": len(header_only_csvs),
        "empty_csv_count": len(empty_csvs),
        "csv_parse_error_count": len(parse_error_csvs),
        "important_expected_count": len(
            IMPORTANT_EXACT_PATHS
        ),
        "important_present_count": len(
            present_important
        ),
        "important_missing_count": len(
            missing_important
        ),
        "important_zero_row_count": len(
            zero_row_important
        ),
        "category_counts": categories,
        "current_branch": branch,
        "current_head": current_head,
        "current_head_short": short_head,
        "next_action": next_action,
        "next_reason": next_reason,
        "runtime_seconds": round(
            time.monotonic() - STARTED,
            3,
        ),
    }

    payload = {
        "program": "EDGEIQ_PERFORMANCE_INTELLIGENCE",
        "unit": "PI_RESTART_UNIT_001",
        "name": (
            "Performance Intelligence Restart Baseline"
        ),
        "version": "V1",
        "generated_utc": utc_now(),
        "verdict": "PASS",
        "governance": {
            "engine_logic_changed": False,
            "thresholds_changed": False,
            "source_data_changed": False,
            "runtime_data_changed": False,
            "react_changed": False,
            "manual_file_edits": False,
        },
        "summary": summary,
        "important_path_status": important_path_status,
        "header_only_csvs": [
            {
                "relative_path": row["relative_path"],
                "size_bytes": row["size_bytes"],
                "csv_columns": row["csv_columns"],
            }
            for row in header_only_csvs
        ],
        "empty_csvs": [
            {
                "relative_path": row["relative_path"],
                "size_bytes": row["size_bytes"],
            }
            for row in empty_csvs
        ],
        "csv_parse_errors": [
            {
                "relative_path": row["relative_path"],
                "error": row["csv_parse_error"],
            }
            for row in parse_error_csvs
        ],
        "outputs": {
            "inventory_csv": (
                INVENTORY_CSV
                .relative_to(ROOT)
                .as_posix()
            ),
            "baseline_json": (
                BASELINE_JSON
                .relative_to(ROOT)
                .as_posix()
            ),
            "baseline_markdown": (
                BASELINE_MD
                .relative_to(ROOT)
                .as_posix()
            ),
            "git_history_text": (
                GIT_HISTORY_TXT
                .relative_to(ROOT)
                .as_posix()
            ),
        },
    }

    BASELINE_JSON.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    markdown = [
        "# EDGEIQ Performance Intelligence Restart Baseline V1",
        "",
        "## Verdict",
        "",
        "**PASS**",
        "",
        "This unit is forensic only. It changed no engine logic,",
        "governed thresholds, source data, runtime data or React.",
        "",
        "## Repository Position",
        "",
        f"- Branch: `{branch}`",
        f"- Starting HEAD: `{short_head}`",
        (
            "- Performance Intelligence artefacts inventoried: "
            f"{summary['inventory_file_count']}"
        ),
        (
            "- Builder or audit scripts identified: "
            f"{summary['script_count']}"
        ),
        f"- CSV artefacts: {summary['csv_count']}",
        (
            "- Populated CSV artefacts: "
            f"{summary['populated_csv_count']}"
        ),
        (
            "- Header-only CSV artefacts: "
            f"{summary['header_only_csv_count']}"
        ),
        (
            "- Empty CSV artefacts: "
            f"{summary['empty_csv_count']}"
        ),
        (
            "- CSV parse errors: "
            f"{summary['csv_parse_error_count']}"
        ),
        "",
        "## Expected Canonical Outputs",
        "",
        "| Output | Present | CSV status | Data rows |",
        "|---|---:|---|---:|",
    ]

    for item in important_path_status:
        markdown.append(
            f"| `{item['relative_path']}` "
            f"| {'YES' if item['present'] else 'NO'} "
            f"| {item['csv_status'] or 'N/A'} "
            f"| {item['csv_data_rows'] if item['csv_data_rows'] != '' else 'N/A'} |"
        )

    markdown.extend(
        [
            "",
            "## Governed Next Action",
            "",
            f"**{next_action}**",
            "",
            next_reason,
            "",
            "No repair is authorised by this baseline.",
            "The next unit must inspect lineage and the first",
            "provable loss point before changing any builder.",
            "",
            "## Outputs",
            "",
            (
                "- `edgeiq_performance_intelligence_"
                "restart_inventory_v1.csv`"
            ),
            (
                "- `edgeiq_performance_intelligence_"
                "restart_baseline_v1.json`"
            ),
            (
                "- `EDGEIQ_PERFORMANCE_INTELLIGENCE_"
                "RESTART_BASELINE_V1.md`"
            ),
            (
                "- `edgeiq_performance_intelligence_"
                "restart_git_history_v1.txt`"
            ),
            "",
        ]
    )

    BASELINE_MD.write_text(
        "\n".join(markdown),
        encoding="utf-8",
    )

    log("PI_RESTART_UNIT_001 VERDICT=PASS")
    log(
        "INVENTORY_FILE_COUNT="
        f"{summary['inventory_file_count']}"
    )
    log(
        "IMPORTANT_PRESENT_COUNT="
        f"{summary['important_present_count']}"
    )
    log(
        "IMPORTANT_MISSING_COUNT="
        f"{summary['important_missing_count']}"
    )
    log(
        "IMPORTANT_ZERO_ROW_COUNT="
        f"{summary['important_zero_row_count']}"
    )
    log(f"NEXT_ACTION={next_action}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        log("PI_RESTART_UNIT_001 VERDICT=FAIL")
        print(
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(1)
