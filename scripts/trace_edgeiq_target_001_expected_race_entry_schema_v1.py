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

EXPECTED_FIELDS = [
    "race_entry_id",
    "race_id",
    "race_date",
    "runner_id",
    "canonical_horse_id",
    "canonical_horse_name",
    "race_entry_status",
    "race_entry_evidence_sha256",
    "builder_version",
]

CURRENT_INPUT = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_race_entry_fact_v1.csv"
)

PRODUCER = (
    ROOT
    / "scripts"
    / "build_edgeiq_race_entry_horse_performance_snapshot_fact_v1.py"
)

OUTPUT_JSON = (
    PROGRAM_ROOT
    / "edgeiq_performance_intelligence_target_001_expected_race_entry_schema_trace_v1.json"
)

OUTPUT_CSV = (
    PROGRAM_ROOT
    / "edgeiq_performance_intelligence_target_001_race_entry_schema_candidates_v1.csv"
)

OUTPUT_MD = (
    PROGRAM_ROOT
    / "EDGEIQ_PERFORMANCE_INTELLIGENCE_TARGET_001_EXPECTED_RACE_ENTRY_SCHEMA_TRACE_V1.md"
)

STARTED = time.monotonic()

SKIP_DIRECTORIES = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
}


def log(message: str) -> None:
    elapsed = time.monotonic() - STARTED
    print(
        f"[{elapsed:7.2f}s] {message}",
        flush=True,
    )


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def git_output(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    return completed.stdout.strip()


def read_csv_header(path: Path) -> list[str]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as handle:
        reader = csv.reader(handle)

        try:
            return [
                value.strip()
                for value in next(reader)
            ]
        except StopIteration:
            return []


def count_csv_rows(path: Path) -> int:
    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as handle:
        reader = csv.reader(handle)

        try:
            next(reader)
        except StopIteration:
            return 0

        return sum(1 for _ in reader)


def candidate_score(
    header: list[str],
) -> tuple[int, list[str], list[str]]:
    header_set = set(header)

    matched = [
        field
        for field in EXPECTED_FIELDS
        if field in header_set
    ]

    missing = [
        field
        for field in EXPECTED_FIELDS
        if field not in header_set
    ]

    return (
        len(matched),
        matched,
        missing,
    )


def main() -> int:
    log("PI_RESTART_UNIT_002D START")
    log(
        "SEARCHING_FOR_EXPECTED_RACE_ENTRY_SCHEMA"
    )

    if not CURRENT_INPUT.is_file():
        raise FileNotFoundError(
            relative(CURRENT_INPUT)
        )

    if not PRODUCER.is_file():
        raise FileNotFoundError(
            relative(PRODUCER)
        )

    current_header = read_csv_header(
        CURRENT_INPUT
    )

    current_score, current_matched, current_missing = (
        candidate_score(current_header)
    )

    candidates: list[dict[str, Any]] = []

    scanned_csv_files = 0

    for path in ROOT.rglob("*.csv"):
        if any(
            part in SKIP_DIRECTORIES
            for part in path.parts
        ):
            continue

        scanned_csv_files += 1

        try:
            header = read_csv_header(path)
        except Exception as exc:
            candidates.append(
                {
                    "relative_path": relative(path),
                    "status": "READ_ERROR",
                    "matched_field_count": 0,
                    "expected_field_count": len(
                        EXPECTED_FIELDS
                    ),
                    "coverage_percent": 0.0,
                    "row_count": "",
                    "matched_fields": "",
                    "missing_fields": "",
                    "error": (
                        f"{type(exc).__name__}: {exc}"
                    ),
                }
            )
            continue

        score, matched, missing = candidate_score(
            header
        )

        if score == 0:
            continue

        try:
            row_count: int | str = count_csv_rows(
                path
            )
        except Exception:
            row_count = ""

        candidates.append(
            {
                "relative_path": relative(path),
                "status": (
                    "EXACT_SCHEMA_MATCH"
                    if score == len(EXPECTED_FIELDS)
                    else "PARTIAL_SCHEMA_MATCH"
                ),
                "matched_field_count": score,
                "expected_field_count": len(
                    EXPECTED_FIELDS
                ),
                "coverage_percent": round(
                    score
                    / len(EXPECTED_FIELDS)
                    * 100,
                    3,
                ),
                "row_count": row_count,
                "matched_fields": "|".join(
                    matched
                ),
                "missing_fields": "|".join(
                    missing
                ),
                "error": "",
            }
        )

    candidates.sort(
        key=lambda row: (
            -int(row["matched_field_count"]),
            -int(row["row_count"])
            if str(row["row_count"]).isdigit()
            else 0,
            str(row["relative_path"]),
        )
    )

    exact_matches = [
        row
        for row in candidates
        if row["status"] == "EXACT_SCHEMA_MATCH"
    ]

    populated_exact_matches = [
        row
        for row in exact_matches
        if (
            str(row["row_count"]).isdigit()
            and int(row["row_count"]) > 0
        )
    ]

    if populated_exact_matches:
        classification = (
            "POPULATED_COMPATIBLE_RACE_ENTRY_DATASET_EXISTS"
        )
        strongest_candidate = populated_exact_matches[
            0
        ]["relative_path"]
        next_action = (
            "TRACE_COMPATIBLE_RACE_ENTRY_DATASET_PRODUCER_AND_AUTHORITY"
        )
    elif exact_matches:
        classification = (
            "ONLY_EMPTY_COMPATIBLE_RACE_ENTRY_DATASETS_EXIST"
        )
        strongest_candidate = exact_matches[
            0
        ]["relative_path"]
        next_action = (
            "TRACE_COMPATIBLE_RACE_ENTRY_DATASET_POPULATION_CHAIN"
        )
    else:
        classification = (
            "NO_COMPATIBLE_RACE_ENTRY_DATASET_FOUND"
        )
        strongest_candidate = ""
        next_action = (
            "TRACE_CANONICAL_RACE_ENTRY_SCHEMA_EVOLUTION"
        )

    with OUTPUT_CSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        fieldnames = [
            "relative_path",
            "status",
            "matched_field_count",
            "expected_field_count",
            "coverage_percent",
            "row_count",
            "matched_fields",
            "missing_fields",
            "error",
        ]

        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(candidates)

    payload = {
        "unit": "PI_RESTART_UNIT_002D",
        "generated_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "verdict": "PASS",
        "repository": {
            "branch": git_output(
                "rev-parse",
                "--abbrev-ref",
                "HEAD",
            ),
            "head": git_output(
                "rev-parse",
                "HEAD",
            ),
        },
        "producer": {
            "relative_path": relative(PRODUCER),
            "sha256": sha256_file(PRODUCER),
        },
        "current_input": {
            "relative_path": relative(
                CURRENT_INPUT
            ),
            "row_count": count_csv_rows(
                CURRENT_INPUT
            ),
            "column_count": len(
                current_header
            ),
            "matched_expected_fields": (
                current_matched
            ),
            "missing_expected_fields": (
                current_missing
            ),
            "expected_field_coverage": (
                current_score
            ),
        },
        "expected_fields": EXPECTED_FIELDS,
        "search": {
            "scanned_csv_files": (
                scanned_csv_files
            ),
            "candidate_count": len(candidates),
            "exact_match_count": len(
                exact_matches
            ),
            "populated_exact_match_count": len(
                populated_exact_matches
            ),
            "strongest_candidate": (
                strongest_candidate
            ),
        },
        "finding": {
            "classification": classification,
            "first_collapse_stage": (
                "RACE_ENTRY_INPUT_CONTRACT_VALIDATION"
            ),
            "repair_authorised": False,
            "next_action": next_action,
        },
        "governance": {
            "engine_logic_changed": False,
            "thresholds_changed": False,
            "source_data_changed": False,
            "warehouse_data_changed": False,
            "runtime_data_changed": False,
            "react_changed": False,
        },
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
        "# EDGEIQ Performance Intelligence Target 001 Expected Race-Entry Schema Trace V1",
        "",
        "## Verdict",
        "",
        "**PASS**",
        "",
        "## Proven Contract Mismatch",
        "",
        (
            f"- Current input: "
            f"`{relative(CURRENT_INPUT)}`"
        ),
        (
            f"- Current input rows: "
            f"`{payload['current_input']['row_count']}`"
        ),
        (
            f"- Expected fields present: "
            f"`{current_score}/{len(EXPECTED_FIELDS)}`"
        ),
        "",
        "## Repository Search",
        "",
        (
            f"- CSV files scanned: "
            f"`{scanned_csv_files}`"
        ),
        (
            f"- Candidates with at least one "
            f"expected field: `{len(candidates)}`"
        ),
        (
            f"- Exact schema matches: "
            f"`{len(exact_matches)}`"
        ),
        (
            f"- Populated exact matches: "
            f"`{len(populated_exact_matches)}`"
        ),
        "",
        "## Finding",
        "",
        f"**{classification}**",
        "",
        (
            f"Strongest candidate: "
            f"`{strongest_candidate or 'NONE'}`"
        ),
        "",
        "## Next Action",
        "",
        f"**{next_action}**",
        "",
        "No repair is authorised.",
        "",
    ]

    OUTPUT_MD.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    log("PI_RESTART_UNIT_002D VERDICT=PASS")
    log(
        "SCANNED_CSV_FILES="
        f"{scanned_csv_files}"
    )
    log(
        "CANDIDATE_COUNT="
        f"{len(candidates)}"
    )
    log(
        "EXACT_MATCH_COUNT="
        f"{len(exact_matches)}"
    )
    log(
        "POPULATED_EXACT_MATCH_COUNT="
        f"{len(populated_exact_matches)}"
    )
    log(
        "STRONGEST_CANDIDATE="
        f"{strongest_candidate or 'NONE'}"
    )
    log(
        "CLASSIFICATION="
        f"{classification}"
    )
    log(
        "NEXT_ACTION="
        f"{next_action}"
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        log("PI_RESTART_UNIT_002D VERDICT=FAIL")
        print(
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(1)
