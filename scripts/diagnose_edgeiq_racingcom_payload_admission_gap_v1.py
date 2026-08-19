from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REPO = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
REPORT_DIR = REPO / "docs" / "performance-intelligence" / "standard-time-investigation"
REPORT_JSON = REPORT_DIR / "edgeiq_racingcom_payload_admission_gap_v1.json"
REPORT_MD = REPORT_DIR / "edgeiq_racingcom_payload_admission_gap_v1.md"
RAW_INVENTORY_CSV = REPORT_DIR / "edgeiq_racingcom_raw_payload_inventory_v1.csv"
REFERENCE_INVENTORY_CSV = REPORT_DIR / "edgeiq_racingcom_payload_reference_inventory_v1.csv"
SCRIPT_EVIDENCE_CSV = REPORT_DIR / "edgeiq_racingcom_payload_selector_script_evidence_v1.csv"

SOURCE_DATASET_NAMES = (
    "edgeiq_racingcom_runner_speed_fact_v1.csv",
    "edgeiq_racingcom_runner_sectional_fact_v1.csv",
    "edgeiq_racingcom_runner_split_fact_v1.csv",
    "edgeiq_racingcom_race_speed_summary_v1.csv",
)

PRIORITY_SCRIPT_NAMES = (
    "build_edgeiq_vic_dom_sectional_warehouse_v1.py",
    "build_edgeiq_vic_historical_sectional_warehouse_v1.py",
    "build_edgeiq_vic_racingcom_browser_csv_downloader_v1.py",
    "build_edgeiq_vic_racingcom_speed_data_ingestion_v1.py",
    "build_edgeiq_vic_real_chrome_csv_capture_v1.py",
    "build_edgeiq_vic_real_chrome_csv_capture_v2.py",
)

PAYLOAD_SUFFIXES = {".json", ".csv", ".txt", ".html", ".htm"}

REFERENCE_COLUMN_TERMS = (
    "payload",
    "source_file",
    "source_path",
    "raw_file",
    "raw_path",
    "file_name",
    "filename",
    "provenance",
    "evidence",
    "capture",
    "artifact",
    "origin",
    "url",
)

SELECTOR_TERMS = (
    "glob(",
    "rglob(",
    "iterdir(",
    "manifest",
    "date_from",
    "date_to",
    "start_date",
    "end_date",
    "cutoff",
    "window",
    "latest",
    "dedup",
    "duplicate",
    "seen",
    "exists(",
    "is_file(",
    "suffix",
    "startswith",
    "endswith",
    "race_id",
    "meeting_id",
    "payload",
    "racing.com",
    "racingcom",
    "victoria",
    "vic",
    "sectional",
    "speed",
)

DATE_PATTERNS = (
    re.compile(r"(?<!\d)(20\d{2})[-_/](\d{2})[-_/](\d{2})(?!\d)"),
    re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)"),
)

RACE_ID_PATTERNS = (
    re.compile(r"(?i)(?:race[_-]?id|raceid)[^0-9]{0,6}(\d{4,})"),
    re.compile(r"(?i)(?:event[_-]?id|eventid)[^0-9]{0,6}(\d{4,})"),
)


def normalise(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalise_path_text(value: str) -> str:
    text = normalise(value).replace("\\", "/")
    while "//" in text:
        text = text.replace("//", "/")
    return text.casefold()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def extract_date(text: str) -> str:
    for pattern in DATE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        try:
            value = datetime(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            )
            return value.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def extract_race_id(text: str) -> str:
    for pattern in RACE_ID_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return ""


def is_probable_racingcom_payload(path: Path) -> tuple[bool, list[str]]:
    relative = path.relative_to(REPO).as_posix()
    folded = relative.casefold()
    reasons: list[str] = []

    if "racingcom" in folded or "racing.com" in folded:
        reasons.append("PATH_RACINGCOM")

    if any(term in folded for term in ("sectional", "speedmap", "speed_data", "race-speed")):
        reasons.append("PATH_SPEED_OR_SECTIONAL")

    if any(term in folded for term in ("capture", "payload", "raw")):
        reasons.append("PATH_CAPTURE_OR_RAW")

    if path.name.casefold().startswith(("race", "meeting", "sectional", "speed")):
        reasons.append("PAYLOAD_LIKE_FILENAME")

    if path.suffix.casefold() not in PAYLOAD_SUFFIXES:
        return False, reasons

    probable = (
        "PATH_RACINGCOM" in reasons
        or (
            "PATH_SPEED_OR_SECTIONAL" in reasons
            and "PATH_CAPTURE_OR_RAW" in reasons
        )
    )
    return probable, reasons


def discover_raw_payloads() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    excluded_roots = {
        ".git",
        "node_modules",
        "dist",
        "build",
        ".vite",
        "__pycache__",
    }

    for path in sorted(REPO.rglob("*"), key=lambda p: p.as_posix().casefold()):
        if not path.is_file():
            continue

        relative_parts = path.relative_to(REPO).parts
        if any(part.casefold() in excluded_roots for part in relative_parts):
            continue

        probable, reasons = is_probable_racingcom_payload(path)
        if not probable:
            continue

        stat = path.stat()
        relative = path.relative_to(REPO).as_posix()

        rows.append(
            {
                "relative_path": relative,
                "file_name": path.name,
                "suffix": path.suffix.casefold(),
                "size_bytes": stat.st_size,
                "modified_utc": datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat(),
                "path_date": extract_date(relative),
                "path_race_id": extract_race_id(relative),
                "discovery_reasons": "|".join(reasons),
                "sha256": sha256_file(path),
            }
        )

    return rows


def locate_named_files(names: Iterable[str]) -> dict[str, list[Path]]:
    wanted = {name.casefold() for name in names}
    located: dict[str, list[Path]] = defaultdict(list)

    for path in sorted(REPO.rglob("*"), key=lambda p: p.as_posix().casefold()):
        if path.is_file() and path.name.casefold() in wanted:
            located[path.name.casefold()].append(path)

    return dict(located)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                reader = csv.DictReader(handle)
                fieldnames = list(reader.fieldnames or [])
                rows = [dict(row) for row in reader]
                return fieldnames, rows
        except UnicodeDecodeError:
            continue

    raise UnicodeError(f"Unable to decode CSV: {path}")


def collect_source_references(
    located_sources: dict[str, list[Path]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dataset_summaries: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []

    for dataset_name in SOURCE_DATASET_NAMES:
        matches = located_sources.get(dataset_name.casefold(), [])

        if not matches:
            dataset_summaries.append(
                {
                    "dataset": dataset_name,
                    "status": "NOT_FOUND",
                    "path": "",
                    "rows": 0,
                    "reference_columns": [],
                    "distinct_reference_values": 0,
                }
            )
            continue

        for path in matches:
            fieldnames, rows = read_csv(path)
            reference_columns = [
                column
                for column in fieldnames
                if any(term in column.casefold() for term in REFERENCE_COLUMN_TERMS)
            ]

            distinct_values: set[str] = set()

            for row_number, row in enumerate(rows, start=2):
                for column in reference_columns:
                    value = normalise(row.get(column))
                    if not value:
                        continue

                    distinct_values.add(value)
                    references.append(
                        {
                            "dataset": dataset_name,
                            "dataset_path": path.relative_to(REPO).as_posix(),
                            "row_number": row_number,
                            "column": column,
                            "reference_value": value,
                            "normalised_reference": normalise_path_text(value),
                            "reference_file_name": Path(
                                value.replace("\\", "/")
                            ).name.casefold(),
                            "reference_date": extract_date(value),
                            "reference_race_id": extract_race_id(value),
                        }
                    )

            dataset_summaries.append(
                {
                    "dataset": dataset_name,
                    "status": "FOUND",
                    "path": path.relative_to(REPO).as_posix(),
                    "rows": len(rows),
                    "columns": fieldnames,
                    "reference_columns": reference_columns,
                    "distinct_reference_values": len(distinct_values),
                }
            )

    return dataset_summaries, references


def inspect_script(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()

    syntax_status = "PASS"
    syntax_error = ""

    try:
        ast.parse(text)
    except SyntaxError as exc:
        syntax_status = "FAIL"
        syntax_error = f"{exc.msg} line={exc.lineno} offset={exc.offset}"

    evidence: list[dict[str, Any]] = []

    for line_number, line in enumerate(lines, start=1):
        folded = line.casefold()
        matched_terms = [term for term in SELECTOR_TERMS if term in folded]

        if matched_terms:
            evidence.append(
                {
                    "script": path.relative_to(REPO).as_posix(),
                    "line_number": line_number,
                    "matched_terms": "|".join(matched_terms),
                    "line": line.strip(),
                }
            )

    return {
        "script": path.relative_to(REPO).as_posix(),
        "syntax_status": syntax_status,
        "syntax_error": syntax_error,
        "line_count": len(lines),
        "selector_evidence_count": len(evidence),
        "evidence": evidence,
    }


def inspect_upstream_scripts() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    priority_lookup = locate_named_files(PRIORITY_SCRIPT_NAMES)
    inspected_paths: set[Path] = set()

    for matches in priority_lookup.values():
        inspected_paths.update(matches)

    for path in sorted((REPO / "scripts").rglob("*.py")):
        folded_name = path.name.casefold()
        if (
            "racingcom" in folded_name
            or "sectional" in folded_name
            or "speed_data" in folded_name
        ):
            inspected_paths.add(path)

    summaries: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []

    for path in sorted(inspected_paths, key=lambda p: p.as_posix().casefold()):
        result = inspect_script(path)
        evidence_rows.extend(result.pop("evidence"))
        summaries.append(result)

    return summaries, evidence_rows


def build_reference_match_analysis(
    raw_rows: list[dict[str, Any]],
    references: list[dict[str, Any]],
) -> dict[str, Any]:
    raw_by_path = {
        normalise_path_text(row["relative_path"]): row
        for row in raw_rows
    }
    raw_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    raw_by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in raw_rows:
        raw_by_name[row["file_name"].casefold()].append(row)
        raw_by_hash[row["sha256"]].append(row)

    referenced_paths: set[str] = set()
    referenced_names: set[str] = set()
    matched_raw_paths: set[str] = set()
    match_method_counts: Counter[str] = Counter()
    unmatched_references: list[dict[str, Any]] = []

    for reference in references:
        normalised_reference = reference["normalised_reference"]
        reference_name = reference["reference_file_name"]

        if normalised_reference:
            referenced_paths.add(normalised_reference)

        if reference_name:
            referenced_names.add(reference_name)

        direct_candidates = [
            raw_path
            for raw_path in raw_by_path
            if normalised_reference.endswith(raw_path)
            or raw_path.endswith(normalised_reference)
        ]

        if direct_candidates:
            for candidate in direct_candidates:
                matched_raw_paths.add(candidate)
            match_method_counts["PATH_SUFFIX_MATCH"] += 1
            continue

        name_candidates = raw_by_name.get(reference_name, [])
        if name_candidates:
            for candidate in name_candidates:
                matched_raw_paths.add(
                    normalise_path_text(candidate["relative_path"])
                )
            match_method_counts["FILE_NAME_MATCH"] += 1
            continue

        unmatched_references.append(reference)
        match_method_counts["UNMATCHED_REFERENCE"] += 1

    unreferenced_raw = [
        row
        for row in raw_rows
        if normalise_path_text(row["relative_path"]) not in matched_raw_paths
    ]

    raw_dates = Counter(
        row["path_date"] or "DATE_UNKNOWN"
        for row in raw_rows
    )
    admitted_dates = Counter(
        raw_by_path[path]["path_date"] or "DATE_UNKNOWN"
        for path in matched_raw_paths
        if path in raw_by_path
    )
    unreferenced_dates = Counter(
        row["path_date"] or "DATE_UNKNOWN"
        for row in unreferenced_raw
    )

    duplicate_hash_groups = [
        {
            "sha256": digest,
            "count": len(group),
            "paths": [row["relative_path"] for row in group],
        }
        for digest, group in raw_by_hash.items()
        if len(group) > 1
    ]

    return {
        "raw_payload_count": len(raw_rows),
        "reference_row_count": len(references),
        "distinct_reference_paths": len(referenced_paths),
        "distinct_reference_file_names": len(referenced_names),
        "matched_raw_payload_count": len(matched_raw_paths),
        "unreferenced_raw_payload_count": len(unreferenced_raw),
        "unmatched_reference_count": len(unmatched_references),
        "match_method_counts": dict(sorted(match_method_counts.items())),
        "raw_dates": dict(sorted(raw_dates.items())),
        "admitted_dates": dict(sorted(admitted_dates.items())),
        "unreferenced_dates": dict(sorted(unreferenced_dates.items())),
        "duplicate_content_groups": duplicate_hash_groups,
        "unmatched_references_sample": unmatched_references[:100],
        "unreferenced_raw_sample": unreferenced_raw[:100],
    }


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
            serialised = {
                key: (
                    json.dumps(value, ensure_ascii=False, sort_keys=True)
                    if isinstance(value, (list, dict))
                    else value
                )
                for key, value in row.items()
            }
            writer.writerow(serialised)


def render_markdown(report: dict[str, Any]) -> str:
    analysis = report["reference_match_analysis"]
    lines: list[str] = []

    lines.append("# EDGEIQ Racing.com Payload Admission Gap V1")
    lines.append("")
    lines.append(f"Generated UTC: `{report['generated_utc']}`")
    lines.append("")
    lines.append("## Investigation boundary")
    lines.append("")
    lines.append("- Read-only forensic diagnostic.")
    lines.append("- No governed builder or governed output was modified.")
    lines.append("- No threshold was changed.")
    lines.append("- No benchmark or standard-time data was fabricated.")
    lines.append("")
    lines.append("## Population summary")
    lines.append("")
    lines.append(f"- Probable raw Racing.com payloads: **{analysis['raw_payload_count']}**")
    lines.append(f"- Source reference rows: **{analysis['reference_row_count']}**")
    lines.append(
        f"- Raw payloads matched to governed references: "
        f"**{analysis['matched_raw_payload_count']}**"
    )
    lines.append(
        f"- Raw payloads with no governed reference: "
        f"**{analysis['unreferenced_raw_payload_count']}**"
    )
    lines.append(
        f"- Reference values not matched to discovered raw files: "
        f"**{analysis['unmatched_reference_count']}**"
    )
    lines.append("")
    lines.append("## V1 source datasets")
    lines.append("")

    for dataset in report["source_datasets"]:
        lines.append(
            f"- `{dataset['dataset']}` ? {dataset['status']} ? "
            f"rows={dataset.get('rows', 0)} ? "
            f"references={dataset.get('distinct_reference_values', 0)} ? "
            f"path=`{dataset.get('path', '')}`"
        )

    lines.append("")
    lines.append("## Admission by payload date")
    lines.append("")
    lines.append("| Date | Raw | Admitted | Unreferenced |")
    lines.append("|---|---:|---:|---:|")

    all_dates = sorted(
        set(analysis["raw_dates"])
        | set(analysis["admitted_dates"])
        | set(analysis["unreferenced_dates"])
    )

    for date_value in all_dates:
        lines.append(
            f"| {date_value} | "
            f"{analysis['raw_dates'].get(date_value, 0)} | "
            f"{analysis['admitted_dates'].get(date_value, 0)} | "
            f"{analysis['unreferenced_dates'].get(date_value, 0)} |"
        )

    lines.append("")
    lines.append("## Candidate selector scripts")
    lines.append("")

    for script in report["script_summaries"]:
        lines.append(
            f"- `{script['script']}` ? "
            f"syntax={script['syntax_status']} ? "
            f"selector evidence lines={script['selector_evidence_count']}"
        )

    lines.append("")
    lines.append("## Preliminary forensic decision")
    lines.append("")

    raw_count = analysis["raw_payload_count"]
    admitted_count = analysis["matched_raw_payload_count"]
    unreferenced_count = analysis["unreferenced_raw_payload_count"]

    if raw_count > 0 and unreferenced_count > 0:
        lines.append("**RAW_PAYLOAD_TO_GOVERNED_REFERENCE_GAP_PRESENT**")
        lines.append("")
        lines.append(
            "Raw payload files exist that cannot be matched to provenance references "
            "in the governed V1 speed datasets."
        )
    elif raw_count > 0 and admitted_count == raw_count:
        lines.append("**ALL_DISCOVERED_RAW_PAYLOADS_REFERENCED**")
        lines.append("")
        lines.append(
            "The previously reported 482-to-39 gap was not reproduced by this "
            "filesystem-to-provenance comparison."
        )
    else:
        lines.append("**RAW_PAYLOAD_DISCOVERY_REQUIRES_REFINEMENT**")
        lines.append("")
        lines.append(
            "The filesystem discovery rules did not identify a sufficient raw "
            "population to confirm the prior result."
        )

    lines.append("")
    lines.append("## Required next interpretation")
    lines.append("")
    lines.append(
        "Use the script evidence CSV to identify the first builder that enumerates "
        "raw payloads and compare its discovery rules against the unreferenced raw "
        "inventory. Do not modify that builder until its exclusion mechanism is "
        "proven."
    )
    lines.append("")
    lines.append("## Diagnostic artifacts")
    lines.append("")
    lines.append(f"- `{REPORT_JSON.relative_to(REPO).as_posix()}`")
    lines.append(f"- `{RAW_INVENTORY_CSV.relative_to(REPO).as_posix()}`")
    lines.append(f"- `{REFERENCE_INVENTORY_CSV.relative_to(REPO).as_posix()}`")
    lines.append(f"- `{SCRIPT_EVIDENCE_CSV.relative_to(REPO).as_posix()}`")

    return "\n".join(lines) + "\n"


def main() -> int:
    if not REPO.exists():
        print(f"FAIL: repository not found: {REPO}")
        return 1

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    print("EDGEIQ Racing.com Payload Admission Gap V1")
    print(f"Repository: {REPO}")
    print("")
    print("[1/5] Discovering probable raw Racing.com payloads...")
    raw_rows = discover_raw_payloads()
    print(f"Probable raw payloads: {len(raw_rows):,}")

    print("[2/5] Locating governed V1 source datasets...")
    located_sources = locate_named_files(SOURCE_DATASET_NAMES)
    source_datasets, references = collect_source_references(located_sources)
    print(f"Reference rows collected: {len(references):,}")

    print("[3/5] Matching governed references to raw payloads...")
    match_analysis = build_reference_match_analysis(raw_rows, references)
    print(
        "Matched raw payloads: "
        f"{match_analysis['matched_raw_payload_count']:,}"
    )
    print(
        "Unreferenced raw payloads: "
        f"{match_analysis['unreferenced_raw_payload_count']:,}"
    )

    print("[4/5] Inspecting upstream builder and ingestion scripts...")
    script_summaries, script_evidence = inspect_upstream_scripts()
    print(f"Scripts inspected: {len(script_summaries):,}")
    print(f"Selector evidence lines: {len(script_evidence):,}")

    report = {
        "diagnostic": "EDGEIQ_RACINGCOM_PAYLOAD_ADMISSION_GAP_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "repository": str(REPO),
        "governance": {
            "read_only": True,
            "governed_outputs_modified": False,
            "thresholds_modified": False,
            "fabricated_data": False,
        },
        "source_datasets": source_datasets,
        "reference_match_analysis": match_analysis,
        "script_summaries": script_summaries,
    }

    print("[5/5] Writing deterministic diagnostic artifacts...")
    write_csv(RAW_INVENTORY_CSV, raw_rows)
    write_csv(REFERENCE_INVENTORY_CSV, references)
    write_csv(SCRIPT_EVIDENCE_CSV, script_evidence)

    REPORT_JSON.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    REPORT_MD.write_text(render_markdown(report), encoding="utf-8")

    print("")
    print("COMPLETE")
    print(f"Report: {REPORT_MD}")
    print(f"JSON: {REPORT_JSON}")
    print(f"Raw inventory: {RAW_INVENTORY_CSV}")
    print(f"Reference inventory: {REFERENCE_INVENTORY_CSV}")
    print(f"Script evidence: {SCRIPT_EVIDENCE_CSV}")
    print("")
    print("DECISION")

    if match_analysis["unreferenced_raw_payload_count"] > 0:
        print("RAW_PAYLOAD_TO_GOVERNED_REFERENCE_GAP_PRESENT")
    else:
        print("NO_UNREFERENCED_RAW_PAYLOADS_FOUND")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
