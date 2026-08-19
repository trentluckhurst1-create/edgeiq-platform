
from __future__ import annotations

import ast
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

REPORT_DIR = (
    REPO
    / "docs"
    / "performance-intelligence"
    / "standard-time-investigation"
)

REPORT_JSON = REPORT_DIR / "edgeiq_active_racingcom_payload_universe_v1.json"
REPORT_MD = REPORT_DIR / "edgeiq_active_racingcom_payload_universe_v1.md"
RAW_CSV = REPORT_DIR / "edgeiq_active_racingcom_raw_payload_inventory_v1.csv"
DIRECTORY_CSV = REPORT_DIR / "edgeiq_active_racingcom_raw_directory_summary_v1.csv"
SELECTOR_CSV = REPORT_DIR / "edgeiq_active_racingcom_selector_trace_v1.csv"

ACTIVE_DATASETS = (
    REPO / "public" / "data" / "edgeiq_racingcom_runner_speed_fact_v1.csv",
    REPO / "public" / "data" / "edgeiq_racingcom_runner_sectional_fact_v1.csv",
    REPO / "public" / "data" / "edgeiq_racingcom_runner_split_fact_v1.csv",
    REPO / "public" / "data" / "edgeiq_racingcom_race_speed_summary_v1.csv",
)

ACTIVE_CHAIN = (
    REPO / "scripts" / "build_edgeiq_raw_sectional_payload_discovery_v1.py",
    REPO / "scripts" / "build_edgeiq_raw_sectional_payload_schema_parser_v1.py",
    REPO / "scripts" / "build_edgeiq_racingcom_csv_ingestion_v1.py",
    REPO / "scripts" / "build_edgeiq_vic_racingcom_speed_data_ingestion_v1.py",
    REPO / "scripts" / "build_edgeiq_racingcom_runner_speed_warehouse_v1.py",
    REPO / "scripts" / "build_edgeiq_racingcom_canonical_speed_warehouse_v2.py",
    REPO / "scripts" / "build_edgeiq_racingcom_canonical_speed_warehouse_v2_1.py",
    REPO / "scripts" / "build_racingcom_sectionals_from_downloads_v1.py",
    REPO / "scripts" / "build_racingcom_sectional_history_master_v1.py",
    REPO / "scripts" / "build_racingcom_sectional_warehouse_v1.py",
    REPO / "scripts" / "build_racingcom_sectional_warehouse_v2.py",
)

EXCLUDED_TOP_LEVEL = {
    ".git",
    "checkpoints",
    "docs",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".vite",
}

PAYLOAD_SUFFIXES = {
    ".json",
    ".csv",
    ".html",
    ".htm",
    ".txt",
}

RAW_PATH_TERMS = (
    "raw",
    "payload",
    "capture",
    "captures",
    "download",
    "downloads",
    "network",
    "browser",
    "chrome",
    "graphql",
    "racingcom",
    "racing.com",
    "sectional",
    "speeddata",
    "speed_data",
)

SELECTOR_TERMS = (
    "glob(",
    "rglob(",
    "iterdir(",
    "os.walk",
    "manifest",
    "input_dir",
    "input_path",
    "source_dir",
    "source_path",
    "raw_dir",
    "raw_path",
    "download",
    "capture",
    "payload",
    "latest",
    "window",
    "cutoff",
    "date_from",
    "date_to",
    "start_date",
    "end_date",
    "dedup",
    "duplicate",
    "seen",
    "race_id",
    "meeting_id",
    "suffix",
    "startswith",
    "endswith",
    "exists(",
    "is_file(",
    "is_dir(",
)

REFERENCE_TERMS = (
    "payload",
    "source_file",
    "source_path",
    "raw_file",
    "raw_path",
    "filename",
    "file_name",
    "capture",
    "evidence",
    "provenance",
    "origin",
    "artifact",
)


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def relative_text(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)

    return digest.hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                reader = csv.DictReader(handle)
                return list(reader.fieldnames or []), [dict(row) for row in reader]
        except UnicodeDecodeError:
            continue

    raise UnicodeError(f"Unable to decode CSV: {path}")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames: list[str] = []
    seen: set[str] = set()

    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            serialised: dict[str, Any] = {}

            for key in fieldnames:
                value = row.get(key, "")

                if isinstance(value, (list, tuple, dict)):
                    value = json.dumps(
                        value,
                        ensure_ascii=False,
                        sort_keys=True,
                    )

                serialised[key] = value

            writer.writerow(serialised)


def is_excluded(path: Path) -> bool:
    relative = path.relative_to(REPO)
    parts = relative.parts

    if not parts:
        return True

    if parts[0].casefold() in EXCLUDED_TOP_LEVEL:
        return True

    folded = relative.as_posix().casefold()

    return (
        "/checkpoint" in folded
        or "__pycache__" in folded
        or "/standard-time-investigation/" in folded
    )


def is_possible_raw_payload(path: Path) -> tuple[bool, list[str]]:
    if path.suffix.casefold() not in PAYLOAD_SUFFIXES:
        return False, []

    relative = relative_text(path)
    folded = relative.casefold()
    reasons: list[str] = []

    for term in RAW_PATH_TERMS:
        if term in folded:
            reasons.append(term)

    if not reasons:
        return False, []

    if folded.startswith("public/data/"):
        return False, ["PUBLIC_DATA_DERIVED"]

    if folded.startswith("scripts/"):
        return False, ["SCRIPT_DIRECTORY"]

    if path.name.casefold().startswith("edgeiq_"):
        return False, ["EDGEIQ_DERIVED_PREFIX"]

    return True, sorted(set(reasons))


def discover_active_raw_payloads() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for path in sorted(
        REPO.rglob("*"),
        key=lambda item: item.as_posix().casefold(),
    ):
        if not path.is_file():
            continue

        if is_excluded(path):
            continue

        possible, reasons = is_possible_raw_payload(path)

        if not possible:
            continue

        stat = path.stat()
        relative = relative_text(path)

        rows.append(
            {
                "relative_path": relative,
                "parent_directory": path.parent.relative_to(REPO).as_posix(),
                "file_name": path.name,
                "suffix": path.suffix.casefold(),
                "size_bytes": stat.st_size,
                "modified_utc": datetime.fromtimestamp(
                    stat.st_mtime,
                    tz=timezone.utc,
                ).isoformat(),
                "discovery_reasons": "|".join(reasons),
                "sha256": sha256_file(path),
            }
        )

    return rows


def summarise_directories(
    raw_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in raw_rows:
        grouped[row["parent_directory"]].append(row)

    summaries: list[dict[str, Any]] = []

    for directory, rows in grouped.items():
        hashes = {
            row["sha256"]
            for row in rows
            if row["sha256"]
        }

        suffixes = Counter(row["suffix"] for row in rows)

        summaries.append(
            {
                "parent_directory": directory,
                "file_count": len(rows),
                "unique_content_hashes": len(hashes),
                "duplicate_file_count": len(rows) - len(hashes),
                "total_bytes": sum(
                    int(row["size_bytes"])
                    for row in rows
                ),
                "suffixes": dict(sorted(suffixes.items())),
            }
        )

    return sorted(
        summaries,
        key=lambda row: (
            -int(row["unique_content_hashes"]),
            -int(row["file_count"]),
            row["parent_directory"],
        ),
    )


def inspect_active_datasets() -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []

    for path in ACTIVE_DATASETS:
        if not path.exists():
            summaries.append(
                {
                    "dataset": path.name,
                    "status": "NOT_FOUND",
                    "path": relative_text(path),
                    "rows": 0,
                    "reference_columns": [],
                    "distinct_reference_values": 0,
                }
            )
            continue

        columns, rows = read_csv(path)

        reference_columns = [
            column
            for column in columns
            if any(
                term in column.casefold()
                for term in REFERENCE_TERMS
            )
        ]

        reference_values: set[str] = set()

        for row in rows:
            for column in reference_columns:
                value = clean(row.get(column))

                if value:
                    reference_values.add(value)

        summaries.append(
            {
                "dataset": path.name,
                "status": "FOUND",
                "path": relative_text(path),
                "rows": len(rows),
                "columns": columns,
                "reference_columns": reference_columns,
                "distinct_reference_values": len(reference_values),
            }
        )

    return summaries


def inspect_active_chain() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    summaries: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []

    for path in ACTIVE_CHAIN:
        relative = relative_text(path)

        if not path.exists():
            summaries.append(
                {
                    "script": relative,
                    "status": "NOT_FOUND",
                    "syntax_status": "",
                    "line_count": 0,
                    "selector_evidence_lines": 0,
                }
            )
            continue

        text = path.read_text(
            encoding="utf-8-sig",
            errors="replace",
        )
        lines = text.splitlines()

        syntax_status = "PASS"
        syntax_error = ""

        try:
            ast.parse(text)
        except SyntaxError as exc:
            syntax_status = "FAIL"
            syntax_error = (
                f"{exc.msg}; line={exc.lineno}; offset={exc.offset}"
            )

        script_evidence_count = 0

        for line_number, line in enumerate(lines, start=1):
            folded = line.casefold()

            matched_terms = [
                term
                for term in SELECTOR_TERMS
                if term in folded
            ]

            if not matched_terms:
                continue

            script_evidence_count += 1

            evidence.append(
                {
                    "script": relative,
                    "line_number": line_number,
                    "matched_terms": "|".join(matched_terms),
                    "line": line.strip(),
                }
            )

        summaries.append(
            {
                "script": relative,
                "status": "FOUND",
                "syntax_status": syntax_status,
                "syntax_error": syntax_error,
                "line_count": len(lines),
                "selector_evidence_lines": script_evidence_count,
            }
        )

    return summaries, evidence


def render_markdown(report: dict[str, Any]) -> str:
    population = report["active_raw_population"]

    lines = [
        "# EDGEIQ Active Racing.com Payload Universe V1",
        "",
        f"Generated UTC: `{report['generated_utc']}`",
        "",
        "## Governance boundary",
        "",
        "- Read-only forensic diagnostic.",
        "- Checkpoints and documentation snapshots excluded.",
        "- Active public data inspected separately.",
        "- Active scripts inspected separately.",
        "- No governed builder modified.",
        "- No governed output modified.",
        "- No threshold modified.",
        "- No benchmark data fabricated.",
        "",
        "## Active raw-looking payload population",
        "",
        f"- Files: **{population['file_count']}**",
        f"- Unique content hashes: **{population['unique_content_hashes']}**",
        f"- Duplicate file copies: **{population['duplicate_file_count']}**",
        "",
        "## Active raw directories",
        "",
        "| Directory | Files | Unique content | Duplicates |",
        "|---|---:|---:|---:|",
    ]

    for row in report["directory_summaries"]:
        lines.append(
            f"| `{row['parent_directory']}` | "
            f"{row['file_count']} | "
            f"{row['unique_content_hashes']} | "
            f"{row['duplicate_file_count']} |"
        )

    lines.extend(
        [
            "",
            "## Active governed V1 datasets",
            "",
        ]
    )

    for dataset in report["active_datasets"]:
        lines.append(
            f"- `{dataset['dataset']}` ? "
            f"{dataset['status']} ? "
            f"rows={dataset['rows']} ? "
            f"distinct references="
            f"{dataset['distinct_reference_values']}"
        )

    lines.extend(
        [
            "",
            "## Active ingestion chain",
            "",
        ]
    )

    for script in report["script_summaries"]:
        lines.append(
            f"- `{script['script']}` ? "
            f"{script['status']} ? "
            f"syntax={script['syntax_status']} ? "
            f"selector evidence lines="
            f"{script['selector_evidence_lines']}"
        )

    lines.extend(
        [
            "",
            "## Forensic decision",
            "",
        ]
    )

    unique_count = population["unique_content_hashes"]

    if unique_count > 39:
        lines.extend(
            [
                "**ACTIVE_UNIQUE_RAW_POPULATION_EXCEEDS_39**",
                "",
                "The active repository contains more than 39 unique raw-looking "
                "Racing.com payload artifacts after checkpoint and documentation "
                "copies are excluded.",
                "",
                "The selector trace must identify which active ingestion stage "
                "does not consume that population.",
            ]
        )
    elif population["file_count"] > 39:
        lines.extend(
            [
                "**ACTIVE_RAW_FILE_COUNT_EXCEEDS_39_BUT_UNIQUE_CONTENT_DOES_NOT**",
                "",
                "The apparent population gap is substantially explained by "
                "duplicate file copies.",
            ]
        )
    else:
        lines.extend(
            [
                "**ACTIVE_RAW_POPULATION_NOT_PROVEN_ABOVE_39**",
                "",
                "The larger prior counts were primarily generated artifacts, "
                "checkpoints, documentation snapshots, or derived data rather "
                "than unique active raw payloads.",
            ]
        )

    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- `{REPORT_JSON.relative_to(REPO).as_posix()}`",
            f"- `{RAW_CSV.relative_to(REPO).as_posix()}`",
            f"- `{DIRECTORY_CSV.relative_to(REPO).as_posix()}`",
            f"- `{SELECTOR_CSV.relative_to(REPO).as_posix()}`",
        ]
    )

    return "\n".join(lines) + "\n"


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    print("EDGEIQ Active Racing.com Payload Universe V1")
    print(f"Repository: {REPO}")
    print("")

    print("[1/4] Discovering active raw-looking payload files...")
    raw_rows = discover_active_raw_payloads()

    hashes = {
        row["sha256"]
        for row in raw_rows
        if row["sha256"]
    }

    active_population = {
        "file_count": len(raw_rows),
        "unique_content_hashes": len(hashes),
        "duplicate_file_count": len(raw_rows) - len(hashes),
    }

    print(f"Active raw-looking files: {len(raw_rows):,}")
    print(f"Unique content hashes: {len(hashes):,}")

    print("[2/4] Inspecting active public V1 datasets...")
    dataset_summaries = inspect_active_datasets()

    for dataset in dataset_summaries:
        print(
            f"{dataset['dataset']}: "
            f"status={dataset['status']} "
            f"rows={dataset['rows']:,} "
            f"references={dataset['distinct_reference_values']:,}"
        )

    print("[3/4] Inspecting active selector chain...")
    script_summaries, selector_evidence = inspect_active_chain()

    print(f"Active chain scripts: {len(script_summaries):,}")
    print(f"Selector evidence rows: {len(selector_evidence):,}")

    print("[4/4] Writing deterministic forensic artifacts...")
    directory_summaries = summarise_directories(raw_rows)

    report = {
        "diagnostic": "EDGEIQ_ACTIVE_RACINGCOM_PAYLOAD_UNIVERSE_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "repository": str(REPO),
        "governance": {
            "read_only": True,
            "checkpoints_excluded": True,
            "documentation_snapshots_excluded": True,
            "governed_builders_modified": False,
            "governed_outputs_modified": False,
            "thresholds_modified": False,
            "fabricated_data": False,
        },
        "active_raw_population": active_population,
        "directory_summaries": directory_summaries,
        "active_datasets": dataset_summaries,
        "script_summaries": script_summaries,
    }

    write_csv(RAW_CSV, raw_rows)
    write_csv(DIRECTORY_CSV, directory_summaries)
    write_csv(SELECTOR_CSV, selector_evidence)

    REPORT_JSON.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    REPORT_MD.write_text(
        render_markdown(report),
        encoding="utf-8",
    )

    print("")
    print("COMPLETE")
    print(f"Report: {REPORT_MD}")
    print(f"Raw inventory: {RAW_CSV}")
    print(f"Directory summary: {DIRECTORY_CSV}")
    print(f"Selector trace: {SELECTOR_CSV}")
    print("")
    print("DECISION")

    if active_population["unique_content_hashes"] > 39:
        print("ACTIVE_UNIQUE_RAW_POPULATION_EXCEEDS_39")
    elif active_population["file_count"] > 39:
        print("ACTIVE_RAW_FILE_COUNT_EXCEEDS_39_BUT_UNIQUE_CONTENT_DOES_NOT")
    else:
        print("ACTIVE_RAW_POPULATION_NOT_PROVEN_ABOVE_39")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
