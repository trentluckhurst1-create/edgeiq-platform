from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


PROGRAM_ID = "EDGEIQ_CANONICAL_PLATFORM_REGISTRY_INPUT_CONTRACT_V1"
PROGRAM_VERSION = "1.0.0"

REQUIRED_BASELINE_COMMITS = (
    "b551089",
    "805042e",
    "1e6f2ab",
    "7b069c4",
    "d7171c6",
    "1946062",
)

TARGET_EVIDENCE_FAMILIES = {
    "CANONICAL_BUILDER_REGISTRY": (
        "canonical builder registry",
        "builder registry",
        "canonical_builder_registry",
    ),
    "CANONICAL_PARSE_FAILURE_AUDITOR": (
        "canonical parse failure",
        "parse failure auditor",
        "canonical_parse_failure",
    ),
    "CANONICAL_SCOPE_REFINER": (
        "canonical scope",
        "scope refiner",
        "canonical_scope",
    ),
    "CANONICAL_DEPENDENCY_GRAPH": (
        "canonical dependency graph",
        "dependency graph",
        "canonical_dependency_graph",
    ),
    "PRODUCT_FEED_REGISTRY": (
        "product feed registry",
        "feed registry",
        "product_feed_registry",
    ),
    "PLATFORM_GOVERNANCE_DASHBOARD": (
        "platform governance dashboard",
        "governance dashboard",
        "platform_governance_dashboard",
    ),
}

TEXT_EXTENSIONS = {
    ".csv",
    ".json",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
}

EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
}


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_family: str
    repository_path: str
    file_name: str
    extension: str
    size_bytes: int
    modified_utc: str
    sha256: str
    match_basis: str
    matched_terms: str
    readable: bool


def utc_iso_from_timestamp(timestamp: float) -> str:
    return (
        datetime.fromtimestamp(timestamp, tz=timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def normalise_text(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[_\-./\\]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def iter_candidate_files(repository_root: Path) -> Iterable[Path]:
    preferred_roots = [
        repository_root / "docs",
        repository_root / "data",
        repository_root / "outputs",
        repository_root / "reports",
        repository_root / "artifacts",
        repository_root / "scripts",
    ]

    roots = [path for path in preferred_roots if path.exists()]

    if not roots:
        roots = [repository_root]

    seen: set[Path] = set()

    for root in roots:
        for current_root, directory_names, file_names in os.walk(root):
            directory_names[:] = sorted(
                name
                for name in directory_names
                if name.lower() not in EXCLUDED_DIRECTORY_NAMES
            )

            current_path = Path(current_root)

            for file_name in sorted(file_names):
                path = current_path / file_name

                if path in seen:
                    continue

                seen.add(path)

                if path.suffix.lower() not in TEXT_EXTENSIONS:
                    continue

                yield path


def inspect_file_for_family(
    path: Path,
    repository_root: Path,
    family: str,
    terms: tuple[str, ...],
) -> EvidenceRecord | None:
    relative_path = path.relative_to(repository_root).as_posix()
    path_search_text = normalise_text(relative_path)

    normalised_terms = tuple(normalise_text(term) for term in terms)
    path_matches = sorted(
        term
        for term in normalised_terms
        if term and term in path_search_text
    )

    content_matches: list[str] = []
    readable = True

    if not path_matches:
        try:
            max_bytes = 2 * 1024 * 1024

            with path.open("rb") as handle:
                raw = handle.read(max_bytes)

            content = raw.decode("utf-8", errors="replace")
            content_search_text = normalise_text(content)

            content_matches = sorted(
                term
                for term in normalised_terms
                if term and term in content_search_text
            )
        except OSError:
            readable = False

    matched_terms = sorted(set(path_matches + content_matches))

    if not matched_terms:
        return None

    if path_matches and content_matches:
        match_basis = "PATH_AND_CONTENT"
    elif path_matches:
        match_basis = "PATH"
    else:
        match_basis = "CONTENT"

    stat = path.stat()

    return EvidenceRecord(
        evidence_family=family,
        repository_path=relative_path,
        file_name=path.name,
        extension=path.suffix.lower(),
        size_bytes=stat.st_size,
        modified_utc=utc_iso_from_timestamp(stat.st_mtime),
        sha256=sha256_file(path),
        match_basis=match_basis,
        matched_terms=" | ".join(matched_terms),
        readable=readable,
    )


def build_records(repository_root: Path) -> list[EvidenceRecord]:
    records: list[EvidenceRecord] = []

    for path in iter_candidate_files(repository_root):
        for family, terms in TARGET_EVIDENCE_FAMILIES.items():
            record = inspect_file_for_family(
                path=path,
                repository_root=repository_root,
                family=family,
                terms=terms,
            )

            if record is not None:
                records.append(record)

    records.sort(
        key=lambda item: (
            item.evidence_family,
            item.repository_path.lower(),
            item.sha256,
        )
    )

    return records


def write_csv(path: Path, records: list[EvidenceRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "evidence_family",
        "repository_path",
        "file_name",
        "extension",
        "size_bytes",
        "modified_utc",
        "sha256",
        "match_basis",
        "matched_terms",
        "readable",
    ]

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for record in records:
            writer.writerow(asdict(record))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(
            payload,
            handle,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        handle.write("\n")


def write_report(
    path: Path,
    repository_root: Path,
    records: list[EvidenceRecord],
    family_summary: dict[str, dict[str, object]],
    verdict: str,
) -> None:
    lines = [
        "# EDGEIQ Canonical Platform Registry Input Contract V1",
        "",
        f"- Program ID: `{PROGRAM_ID}`",
        f"- Program version: `{PROGRAM_VERSION}`",
        f"- Repository root: `{repository_root}`",
        f"- Verdict: **{verdict}**",
        f"- Evidence rows: **{len(records)}**",
        "",
        "## Governance baseline",
        "",
    ]

    for commit in REQUIRED_BASELINE_COMMITS:
        lines.append(f"- `{commit}`")

    lines.extend(
        [
            "",
            "## Evidence families",
            "",
            "| Evidence family | Files found | CSV | JSON | Markdown | Status |",
            "|---|---:|---:|---:|---:|---|",
        ]
    )

    for family in sorted(family_summary):
        row = family_summary[family]
        lines.append(
            "| {family} | {files} | {csv_count} | {json_count} | "
            "{md_count} | {status} |".format(
                family=family,
                files=row["files_found"],
                csv_count=row["csv_files"],
                json_count=row["json_files"],
                md_count=row["markdown_files"],
                status=row["status"],
            )
        )

    lines.extend(
        [
            "",
            "## Contract interpretation",
            "",
            "This governed unit identifies the repository evidence that will be "
            "used as input to the Canonical Platform Registry.",
            "",
            "It does not modify, infer, repair, consolidate or replace any "
            "existing governance artefact.",
            "",
            "A family is considered available when at least one deterministic "
            "repository evidence file is identified.",
            "",
        ]
    )

    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the governed EDGEIQ Canonical Platform Registry "
            "input evidence contract."
        )
    )
    parser.add_argument(
        "--repository-root",
        required=True,
        help="EDGEIQ repository root.",
    )
    parser.add_argument(
        "--output-root",
        required=True,
        help="Output directory for governed contract artefacts.",
    )
    args = parser.parse_args()

    repository_root = Path(args.repository_root).resolve()
    output_root = Path(args.output_root).resolve()

    if not repository_root.exists():
        raise FileNotFoundError(
            f"Repository root does not exist: {repository_root}"
        )

    records = build_records(repository_root)

    family_summary: dict[str, dict[str, object]] = {}

    for family in sorted(TARGET_EVIDENCE_FAMILIES):
        family_records = [
            record
            for record in records
            if record.evidence_family == family
        ]

        family_summary[family] = {
            "files_found": len(family_records),
            "csv_files": sum(
                record.extension == ".csv"
                for record in family_records
            ),
            "json_files": sum(
                record.extension == ".json"
                for record in family_records
            ),
            "markdown_files": sum(
                record.extension == ".md"
                for record in family_records
            ),
            "readable_files": sum(
                record.readable
                for record in family_records
            ),
            "status": "AVAILABLE" if family_records else "MISSING",
        }

    missing_families = [
        family
        for family, details in family_summary.items()
        if details["status"] == "MISSING"
    ]

    verdict = "PASS" if not missing_families else "FAIL_MISSING_EVIDENCE"

    csv_path = (
        output_root
        / "edgeiq_canonical_platform_registry_input_evidence_v1.csv"
    )
    json_path = (
        output_root
        / "edgeiq_canonical_platform_registry_input_evidence_v1.json"
    )
    summary_path = (
        output_root
        / "edgeiq_canonical_platform_registry_input_contract_summary_v1.json"
    )
    report_path = (
        output_root
        / "EDGEIQ_CANONICAL_PLATFORM_REGISTRY_INPUT_CONTRACT_V1.md"
    )

    write_csv(csv_path, records)

    write_json(
        json_path,
        {
            "program_id": PROGRAM_ID,
            "program_version": PROGRAM_VERSION,
            "records": [asdict(record) for record in records],
        },
    )

    summary = {
        "program_id": PROGRAM_ID,
        "program_version": PROGRAM_VERSION,
        "verdict": verdict,
        "repository_root": str(repository_root),
        "required_baseline_commits": list(REQUIRED_BASELINE_COMMITS),
        "evidence_rows": len(records),
        "evidence_families_expected": len(TARGET_EVIDENCE_FAMILIES),
        "evidence_families_available": sum(
            details["status"] == "AVAILABLE"
            for details in family_summary.values()
        ),
        "evidence_families_missing": len(missing_families),
        "missing_families": missing_families,
        "family_summary": family_summary,
        "outputs": {
            "csv": str(csv_path),
            "json": str(json_path),
            "summary": str(summary_path),
            "report": str(report_path),
        },
    }

    write_json(summary_path, summary)
    write_report(
        path=report_path,
        repository_root=repository_root,
        records=records,
        family_summary=family_summary,
        verdict=verdict,
    )

    print(f"PROGRAM_ID={PROGRAM_ID}")
    print(f"PROGRAM_VERSION={PROGRAM_VERSION}")
    print(f"VERDICT={verdict}")
    print(f"EVIDENCE_ROWS={len(records)}")
    print(
        "EVIDENCE_FAMILIES_AVAILABLE="
        f"{summary['evidence_families_available']}"
    )
    print(
        "EVIDENCE_FAMILIES_MISSING="
        f"{summary['evidence_families_missing']}"
    )
    print(f"OUTPUT_CSV={csv_path}")
    print(f"OUTPUT_JSON={json_path}")
    print(f"OUTPUT_SUMMARY={summary_path}")
    print(f"OUTPUT_REPORT={report_path}")

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"FATAL_ERROR={type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise
