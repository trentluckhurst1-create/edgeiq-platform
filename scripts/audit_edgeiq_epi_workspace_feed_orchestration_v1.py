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
from typing import Any


AUDIT_ID = "EDGEIQ_EPI_WORKSPACE_FEED_ORCHESTRATION_AUDIT_V1"

CANONICAL_RELATIVE_PATH = Path(
    "public/data/edgeiq_epi_workspace_terminal_feed_v1.csv"
)

CANONICAL_FILENAME = CANONICAL_RELATIVE_PATH.name

OUTPUT_ROOT = Path(
    "docs/runtime-data-wiring-audit-v1/phase-o1-epi-feed-orchestration"
)

TEXT_EXTENSIONS = {
    ".py",
    ".ps1",
    ".tsx",
    ".ts",
    ".jsx",
    ".js",
    ".json",
    ".md",
    ".txt",
    ".csv",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".html",
    ".css",
}

SOURCE_EXTENSIONS = {
    ".py",
    ".ps1",
    ".tsx",
    ".ts",
    ".jsx",
    ".js",
}

EXCLUDED_PARTS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
}

CHECKPOINT_PARTS = {
    "checkpoint",
    "checkpoints",
    "archive",
    "archives",
    "backup",
    "backups",
}

WRITER_PATTERNS = [
    re.compile(r"\.write_text\s*\(", re.I),
    re.compile(r"\.write_bytes\s*\(", re.I),
    re.compile(r"\.open\s*\([^)]*[\"']w", re.I),
    re.compile(r"\.open\s*\([^)]*[\"']a", re.I),
    re.compile(r"open\s*\([^)]*[\"']w", re.I),
    re.compile(r"open\s*\([^)]*[\"']a", re.I),
    re.compile(r"to_csv\s*\(", re.I),
    re.compile(r"csv\.writer\s*\(", re.I),
    re.compile(r"csv\.DictWriter\s*\(", re.I),
    re.compile(r"copyfile\s*\(", re.I),
    re.compile(r"shutil\.copy", re.I),
    re.compile(r"Copy-Item", re.I),
    re.compile(r"Set-Content", re.I),
    re.compile(r"Out-File", re.I),
    re.compile(r"Add-Content", re.I),
    re.compile(r"WriteAllText", re.I),
    re.compile(r"WriteAllBytes", re.I),
]

READER_PATTERNS = [
    re.compile(r"\.read_text\s*\(", re.I),
    re.compile(r"\.read_bytes\s*\(", re.I),
    re.compile(r"\.open\s*\([^)]*[\"']r", re.I),
    re.compile(r"open\s*\([^)]*[\"']r", re.I),
    re.compile(r"read_csv\s*\(", re.I),
    re.compile(r"csv\.reader\s*\(", re.I),
    re.compile(r"csv\.DictReader\s*\(", re.I),
    re.compile(r"fetch\s*\(", re.I),
    re.compile(r"axios\.", re.I),
    re.compile(r"Get-Content", re.I),
    re.compile(r"Import-Csv", re.I),
]

ORCHESTRATION_TERMS = {
    "orchestrator",
    "orchestration",
    "pipeline",
    "build_all",
    "run_all",
    "governed",
    "beta",
    "refresh",
    "publish",
    "terminal_feed",
    "workspace",
}

LIKELY_RUNTIME_DIRS = {
    "src",
    "scripts",
    "public",
}

SIMILAR_NAME_TERMS = (
    "epi_workspace",
    "epi-workspace",
    "epiworkspace",
    "epi_terminal",
    "epi-feed",
    "epi_feed",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def safe_read(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8-sig",
            errors="replace",
        )
    except OSError:
        return ""


def is_excluded(path: Path) -> bool:
    return any(
        part.lower() in EXCLUDED_PARTS
        for part in path.parts
    )


def is_checkpoint_path(path: Path) -> bool:
    return any(
        any(
            token in part.lower()
            for token in CHECKPOINT_PARTS
        )
        for part in path.parts
    )


def runtime_relevance(path: Path) -> str:
    if not path.parts:
        return "UNKNOWN"

    first = path.parts[0].lower()

    if first in LIKELY_RUNTIME_DIRS:
        return "ACTIVE_RUNTIME_PATH"

    if is_checkpoint_path(path):
        return "CHECKPOINT_OR_ARCHIVE"

    if first == "docs":
        return "DOCUMENTATION_OR_EVIDENCE"

    return "OTHER"


def file_metadata(
    root: Path,
    path: Path,
) -> dict[str, Any]:
    stat = path.stat()
    relative = path.relative_to(root)

    return {
        "path": relative.as_posix(),
        "filename": path.name,
        "extension": path.suffix.lower(),
        "size_bytes": stat.st_size,
        "modified_utc": datetime.fromtimestamp(
            stat.st_mtime,
            tz=timezone.utc,
        ).isoformat(),
        "sha256": sha256_file(path),
        "checkpoint_or_archive": is_checkpoint_path(
            relative
        ),
        "runtime_relevance": runtime_relevance(
            relative
        ),
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


def matched_line_details(
    text: str,
    target_terms: tuple[str, ...],
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []

    for line_number, line in enumerate(
        text.splitlines(),
        start=1,
    ):
        lowered = line.lower()

        if not any(
            term.lower() in lowered
            for term in target_terms
        ):
            continue

        writer_hits = [
            pattern.pattern
            for pattern in WRITER_PATTERNS
            if pattern.search(line)
        ]

        reader_hits = [
            pattern.pattern
            for pattern in READER_PATTERNS
            if pattern.search(line)
        ]

        orchestration_hits = sorted(
            term
            for term in ORCHESTRATION_TERMS
            if term in lowered
        )

        matches.append(
            {
                "line_number": line_number,
                "source_line": line.strip(),
                "writer_pattern_hits": " | ".join(
                    writer_hits
                ),
                "reader_pattern_hits": " | ".join(
                    reader_hits
                ),
                "orchestration_terms": " | ".join(
                    orchestration_hits
                ),
            }
        )

    return matches


def ast_call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id

    if isinstance(node.func, ast.Attribute):
        parts: list[str] = []
        current: ast.AST = node.func

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return ".".join(reversed(parts))

    return ""


def python_ast_evidence(
    relative: Path,
    text: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    try:
        tree = ast.parse(
            text,
            filename=relative.as_posix(),
        )
    except SyntaxError:
        return rows

    lines = text.splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        call = ast_call_name(node)
        line = (
            lines[node.lineno - 1].strip()
            if 0 < node.lineno <= len(lines)
            else ""
        )

        lowered = line.lower()

        if CANONICAL_FILENAME.lower() not in lowered:
            continue

        classification = "REFERENCE"

        if any(
            pattern.search(line)
            for pattern in WRITER_PATTERNS
        ):
            classification = "WRITER"

        elif any(
            pattern.search(line)
            for pattern in READER_PATTERNS
        ):
            classification = "READER"

        rows.append(
            {
                "path": relative.as_posix(),
                "line_number": node.lineno,
                "call": call,
                "classification": classification,
                "source_line": line,
            }
        )

    return rows


def count_csv_rows(path: Path) -> int | None:
    if path.suffix.lower() != ".csv":
        return None

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            reader = csv.reader(handle)
            total = sum(1 for _ in reader)

        return max(total - 1, 0)
    except Exception:
        return None


def main() -> int:
    root = Path.cwd().resolve()
    canonical_path = root / CANONICAL_RELATIVE_PATH
    output_root = root / OUTPUT_ROOT

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(f"=== {AUDIT_ID} ===", flush=True)
    print(
        f"canonical_feed={canonical_path}",
        flush=True,
    )

    if not canonical_path.exists():
        print(
            "ERROR: Canonical EPI workspace feed does not exist.",
            file=sys.stderr,
        )
        return 2

    print(
        "\n[1/7] Scanning repository files...",
        flush=True,
    )

    eligible_files: list[Path] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        if is_excluded(path.relative_to(root)):
            continue

        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        eligible_files.append(path)

    eligible_files.sort()

    print(
        f"eligible_files={len(eligible_files)}",
        flush=True,
    )

    target_terms = (
        CANONICAL_FILENAME,
        CANONICAL_RELATIVE_PATH.as_posix(),
        str(CANONICAL_RELATIVE_PATH).replace(
            "/",
            "\\",
        ),
    )

    reference_rows: list[dict[str, Any]] = []
    ast_rows: list[dict[str, Any]] = []

    print(
        "\n[2/7] Locating feed references, readers and writers...",
        flush=True,
    )

    for index, path in enumerate(
        eligible_files,
        start=1,
    ):
        relative = path.relative_to(root)
        text = safe_read(path)

        if not text:
            continue

        if not any(
            term.lower() in text.lower()
            for term in target_terms
        ):
            continue

        for match in matched_line_details(
            text,
            target_terms,
        ):
            writer_hits = clean(
                match["writer_pattern_hits"]
            )
            reader_hits = clean(
                match["reader_pattern_hits"]
            )

            if writer_hits and reader_hits:
                classification = (
                    "READER_AND_WRITER_REFERENCE"
                )
            elif writer_hits:
                classification = "WRITER_REFERENCE"
            elif reader_hits:
                classification = "READER_REFERENCE"
            else:
                classification = "PATH_REFERENCE"

            reference_rows.append(
                {
                    "path": relative.as_posix(),
                    "line_number": match[
                        "line_number"
                    ],
                    "extension": path.suffix.lower(),
                    "runtime_relevance": runtime_relevance(
                        relative
                    ),
                    "checkpoint_or_archive": (
                        is_checkpoint_path(relative)
                    ),
                    "classification": classification,
                    "writer_pattern_hits": writer_hits,
                    "reader_pattern_hits": reader_hits,
                    "orchestration_terms": match[
                        "orchestration_terms"
                    ],
                    "source_line": match[
                        "source_line"
                    ],
                }
            )

        if path.suffix.lower() == ".py":
            ast_rows.extend(
                python_ast_evidence(
                    relative,
                    text,
                )
            )

        if index % 1000 == 0:
            print(
                f"[scan] {index}/{len(eligible_files)}",
                flush=True,
            )

    print(
        f"reference_rows={len(reference_rows)}",
        flush=True,
    )

    print(
        "\n[3/7] Detecting duplicate and similar feeds...",
        flush=True,
    )

    duplicate_rows: list[dict[str, Any]] = []

    canonical_hash = sha256_file(
        canonical_path
    )

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        if is_excluded(path.relative_to(root)):
            continue

        lowered_name = path.name.lower()
        lowered_path = path.as_posix().lower()

        is_exact_name = (
            lowered_name
            == CANONICAL_FILENAME.lower()
        )

        is_similar_name = any(
            term in lowered_name
            or term in lowered_path
            for term in SIMILAR_NAME_TERMS
        )

        if not is_exact_name and not is_similar_name:
            continue

        metadata = file_metadata(
            root,
            path,
        )

        row_count = count_csv_rows(path)

        metadata.update(
            {
                "exact_canonical_filename": (
                    is_exact_name
                ),
                "same_hash_as_canonical": (
                    metadata["sha256"]
                    == canonical_hash
                ),
                "csv_row_count": (
                    ""
                    if row_count is None
                    else row_count
                ),
            }
        )

        duplicate_rows.append(metadata)

    duplicate_rows.sort(
        key=lambda row: (
            not row["exact_canonical_filename"],
            row["runtime_relevance"],
            row["path"],
        )
    )

    print(
        f"duplicate_or_similar_files="
        f"{len(duplicate_rows)}",
        flush=True,
    )

    print(
        "\n[4/7] Locating orchestrators and pipeline entry points...",
        flush=True,
    )

    orchestration_rows: list[dict[str, Any]] = []

    referenced_paths = {
        row["path"]
        for row in reference_rows
    }

    for relative_text in sorted(
        referenced_paths
    ):
        relative = Path(relative_text)
        path = root / relative

        if path.suffix.lower() not in SOURCE_EXTENSIONS:
            continue

        text = safe_read(path)

        lowered = text.lower()

        terms = sorted(
            term
            for term in ORCHESTRATION_TERMS
            if term in lowered
        )

        builder_references = sorted(
            set(
                re.findall(
                    r"build_edgeiq_[a-zA-Z0-9_]+\.py",
                    text,
                )
            )
        )

        command_references = sorted(
            set(
                re.findall(
                    r"(?:python|py)\s+(?:-u\s+)?"
                    r"[^\r\n\"']+\.py",
                    text,
                    flags=re.I,
                )
            )
        )

        orchestration_rows.append(
            {
                "path": relative.as_posix(),
                "runtime_relevance": runtime_relevance(
                    relative
                ),
                "checkpoint_or_archive": (
                    is_checkpoint_path(relative)
                ),
                "orchestration_terms": " | ".join(
                    terms
                ),
                "builder_references": " | ".join(
                    builder_references
                ),
                "command_references": " | ".join(
                    command_references
                ),
                "references_canonical_feed": True,
            }
        )

    print(
        f"orchestration_candidates="
        f"{len(orchestration_rows)}",
        flush=True,
    )

    print(
        "\n[5/7] Classifying active producers and consumers...",
        flush=True,
    )

    active_references = [
        row
        for row in reference_rows
        if row["runtime_relevance"]
        == "ACTIVE_RUNTIME_PATH"
    ]

    active_writers = [
        row
        for row in active_references
        if row["classification"] in {
            "WRITER_REFERENCE",
            "READER_AND_WRITER_REFERENCE",
        }
    ]

    active_readers = [
        row
        for row in active_references
        if row["classification"] in {
            "READER_REFERENCE",
            "READER_AND_WRITER_REFERENCE",
        }
    ]

    active_path_references = [
        row
        for row in active_references
        if row["classification"]
        == "PATH_REFERENCE"
    ]

    active_writer_paths = sorted(
        {
            row["path"]
            for row in active_writers
        }
    )

    active_reader_paths = sorted(
        {
            row["path"]
            for row in active_readers
        }
    )

    active_react_paths = sorted(
        {
            row["path"]
            for row in active_references
            if row["path"].startswith("src/")
        }
    )

    exact_feed_copies = [
        row
        for row in duplicate_rows
        if row["exact_canonical_filename"]
    ]

    active_exact_feed_copies = [
        row
        for row in exact_feed_copies
        if row["runtime_relevance"]
        == "ACTIVE_RUNTIME_PATH"
    ]

    checkpoint_exact_feed_copies = [
        row
        for row in exact_feed_copies
        if row["checkpoint_or_archive"]
    ]

    classification_counts = Counter(
        row["classification"]
        for row in reference_rows
    )

    print(
        f"active_writer_paths="
        f"{len(active_writer_paths)}",
        flush=True,
    )
    print(
        f"active_reader_paths="
        f"{len(active_reader_paths)}",
        flush=True,
    )
    print(
        f"active_react_paths="
        f"{len(active_react_paths)}",
        flush=True,
    )

    print(
        "\n[6/7] Determining orchestration verdict...",
        flush=True,
    )

    canonical_metadata = file_metadata(
        root,
        canonical_path,
    )
    canonical_metadata["csv_row_count"] = (
        count_csv_rows(canonical_path)
    )

    warnings: list[str] = []
    findings: list[str] = []

    if not active_writer_paths:
        warnings.append(
            "No active runtime writer was identified "
            "for the canonical feed."
        )
    else:
        findings.append(
            f"{len(active_writer_paths)} active writer "
            f"path(s) identified."
        )

    if len(active_writer_paths) > 1:
        warnings.append(
            "Multiple active writer paths reference the "
            "canonical feed."
        )

    if not active_react_paths:
        warnings.append(
            "No React source directly references the "
            "canonical feed."
        )
    else:
        findings.append(
            f"{len(active_react_paths)} React consumer "
            f"path(s) identified."
        )

    if len(active_exact_feed_copies) > 1:
        warnings.append(
            "Multiple exact canonical feed copies exist "
            "inside active runtime paths."
        )

    if checkpoint_exact_feed_copies:
        findings.append(
            f"{len(checkpoint_exact_feed_copies)} "
            "checkpoint/archive copies of the exact feed "
            "were identified."
        )

    same_name_different_hash = [
        row
        for row in exact_feed_copies
        if not row["same_hash_as_canonical"]
    ]

    if same_name_different_hash:
        warnings.append(
            f"{len(same_name_different_hash)} exact-name "
            "feed copy or copies differ from the current "
            "canonical feed hash."
        )

    if len(active_writer_paths) > 1:
        verdict = "MULTIPLE_GENERATORS_FOUND"

    elif len(active_exact_feed_copies) > 1:
        verdict = "DUPLICATE_FEED_DETECTED"

    elif not active_writer_paths:
        verdict = "CANONICAL_WRITER_NOT_PROVEN"

    elif not active_react_paths:
        verdict = "UI_DIRECT_CONSUMER_NOT_PROVEN"

    elif same_name_different_hash:
        verdict = "STALE_COPY_RISK_DETECTED"

    else:
        verdict = "CANONICAL_PIPELINE_REFERENCES_CONFIRMED"

    print(
        f"verdict={verdict}",
        flush=True,
    )

    print(
        "\n[7/7] Writing governed evidence...",
        flush=True,
    )

    write_csv(
        output_root
        / f"{AUDIT_ID}_REFERENCES.csv",
        reference_rows,
        [
            "path",
            "line_number",
            "extension",
            "runtime_relevance",
            "checkpoint_or_archive",
            "classification",
            "writer_pattern_hits",
            "reader_pattern_hits",
            "orchestration_terms",
            "source_line",
        ],
    )

    write_csv(
        output_root
        / f"{AUDIT_ID}_PYTHON_AST_EVIDENCE.csv",
        ast_rows,
        [
            "path",
            "line_number",
            "call",
            "classification",
            "source_line",
        ],
    )

    write_csv(
        output_root
        / f"{AUDIT_ID}_DUPLICATE_AND_SIMILAR_FILES.csv",
        duplicate_rows,
        [
            "path",
            "filename",
            "extension",
            "size_bytes",
            "modified_utc",
            "sha256",
            "csv_row_count",
            "exact_canonical_filename",
            "same_hash_as_canonical",
            "checkpoint_or_archive",
            "runtime_relevance",
        ],
    )

    write_csv(
        output_root
        / f"{AUDIT_ID}_ORCHESTRATION_CANDIDATES.csv",
        orchestration_rows,
        [
            "path",
            "runtime_relevance",
            "checkpoint_or_archive",
            "orchestration_terms",
            "builder_references",
            "command_references",
            "references_canonical_feed",
        ],
    )

    write_csv(
        output_root
        / f"{AUDIT_ID}_ACTIVE_WRITERS.csv",
        active_writers,
        [
            "path",
            "line_number",
            "classification",
            "writer_pattern_hits",
            "source_line",
        ],
    )

    write_csv(
        output_root
        / f"{AUDIT_ID}_ACTIVE_READERS.csv",
        active_readers,
        [
            "path",
            "line_number",
            "classification",
            "reader_pattern_hits",
            "source_line",
        ],
    )

    summary = {
        "audit_id": AUDIT_ID,
        "generated_at_utc": utc_now(),
        "canonical_feed": (
            CANONICAL_RELATIVE_PATH.as_posix()
        ),
        "canonical_metadata": canonical_metadata,
        "eligible_files_scanned": len(
            eligible_files
        ),
        "reference_rows": len(
            reference_rows
        ),
        "reference_classifications": dict(
            classification_counts
        ),
        "active_writer_paths": active_writer_paths,
        "active_reader_paths": active_reader_paths,
        "active_react_paths": active_react_paths,
        "active_path_reference_count": len(
            active_path_references
        ),
        "duplicate_or_similar_files": len(
            duplicate_rows
        ),
        "exact_filename_copies": len(
            exact_feed_copies
        ),
        "active_exact_filename_copies": len(
            active_exact_feed_copies
        ),
        "checkpoint_exact_filename_copies": len(
            checkpoint_exact_feed_copies
        ),
        "exact_name_different_hash_count": len(
            same_name_different_hash
        ),
        "orchestration_candidates": len(
            orchestration_rows
        ),
        "findings": findings,
        "warnings": warnings,
        "verdict": verdict,
        "status": "EVIDENCE_CAPTURED",
    }

    (
        output_root
        / f"{AUDIT_ID}_SUMMARY.json"
    ).write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )

    report_lines = [
        f"# {AUDIT_ID}",
        "",
        f"- Generated UTC: `{summary['generated_at_utc']}`",
        f"- Verdict: **{verdict}**",
        f"- Canonical feed: `{summary['canonical_feed']}`",
        f"- Canonical rows: `{canonical_metadata['csv_row_count']}`",
        f"- Canonical SHA-256: `{canonical_metadata['sha256']}`",
        f"- Active writer paths: `{len(active_writer_paths)}`",
        f"- Active reader paths: `{len(active_reader_paths)}`",
        f"- React consumer paths: `{len(active_react_paths)}`",
        f"- Exact-name copies: `{len(exact_feed_copies)}`",
        f"- Different-hash exact-name copies: `{len(same_name_different_hash)}`",
        "",
        "## Active Writers",
        "",
    ]

    if active_writer_paths:
        report_lines.extend(
            f"- `{path}`"
            for path in active_writer_paths
        )
    else:
        report_lines.append(
            "- No active writer identified."
        )

    report_lines.extend(
        [
            "",
            "## Active Readers",
            "",
        ]
    )

    if active_reader_paths:
        report_lines.extend(
            f"- `{path}`"
            for path in active_reader_paths
        )
    else:
        report_lines.append(
            "- No active reader identified."
        )

    report_lines.extend(
        [
            "",
            "## React Consumers",
            "",
        ]
    )

    if active_react_paths:
        report_lines.extend(
            f"- `{path}`"
            for path in active_react_paths
        )
    else:
        report_lines.append(
            "- No direct React consumer identified."
        )

    report_lines.extend(
        [
            "",
            "## Findings",
            "",
        ]
    )

    if findings:
        report_lines.extend(
            f"- {finding}"
            for finding in findings
        )
    else:
        report_lines.append(
            "- No affirmative findings recorded."
        )

    report_lines.extend(
        [
            "",
            "## Warnings",
            "",
        ]
    )

    if warnings:
        report_lines.extend(
            f"- {warning}"
            for warning in warnings
        )
    else:
        report_lines.append(
            "- No orchestration warnings detected."
        )

    (
        output_root
        / f"{AUDIT_ID}_REPORT.md"
    ).write_text(
        "\n".join(report_lines) + "\n",
        encoding="utf-8",
    )

    print("\n=== PHASE O1 COMPLETE ===")
    print(
        json.dumps(
            {
                "status": summary["status"],
                "verdict": verdict,
                "canonical_rows": (
                    canonical_metadata[
                        "csv_row_count"
                    ]
                ),
                "active_writer_paths": (
                    len(active_writer_paths)
                ),
                "active_reader_paths": (
                    len(active_reader_paths)
                ),
                "active_react_paths": (
                    len(active_react_paths)
                ),
                "exact_feed_copies": (
                    len(exact_feed_copies)
                ),
                "different_hash_exact_copies": (
                    len(same_name_different_hash)
                ),
            },
            indent=2,
        ),
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())