from __future__ import annotations

import csv
import hashlib
import json
import re
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

TARGETS_JSON = (
    PROGRAM_ROOT
    / "edgeiq_performance_intelligence_lineage_targets_v1.json"
)

TARGET_NUMBER = 1

OUTPUT_JSON = (
    PROGRAM_ROOT
    / "edgeiq_performance_intelligence_target_001_producer_trace_v1.json"
)

OUTPUT_CSV = (
    PROGRAM_ROOT
    / "edgeiq_performance_intelligence_target_001_references_v1.csv"
)

OUTPUT_MD = (
    PROGRAM_ROOT
    / "EDGEIQ_PERFORMANCE_INTELLIGENCE_TARGET_001_PRODUCER_TRACE_V1.md"
)

TEXT_EXTENSIONS = {
    ".py",
    ".ps1",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".txt",
    ".csv",
    ".yaml",
    ".yml",
    ".toml",
}

EXCLUDED_PARTS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".vite",
}

DATA_PATH_PATTERN = re.compile(
    r"""(?ix)
    (?:
        [A-Za-z0-9_.-]+
        [\\/]
    )*
    [A-Za-z0-9_.-]+
    \.
    (?:
        csv|
        json|
        parquet|
        feather|
        sqlite|
        db
    )
    """
)

PATH_ASSIGNMENT_PATTERN = re.compile(
    r"""(?ix)
    (?P<name>
        [A-Za-z_][A-Za-z0-9_]*
    )
    \s*=\s*
    (?P<value>
        (?:
            Path\s*\([^)]*\)
            |
            ["'][^"']+["']
            |
            [A-Za-z_][A-Za-z0-9_]*
            \s*/\s*
            ["'][^"']+["']
        )
    )
    """
)

STARTED = time.monotonic()


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
        while True:
            block = handle.read(1024 * 1024)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Required JSON is missing: {relative(path)}"
        )

    return json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )


def run_git(*arguments: str) -> str:
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


def classify_reference(path: Path) -> str:
    name = path.name.lower()
    rel = relative(path).lower()

    if path.suffix.lower() == ".py":
        if "audit" in name or "check" in name or "verify" in name:
            return "AUDIT_OR_VERIFIER"

        if (
            "orchestr" in name
            or "pipeline" in name
            or name.startswith("run_")
        ):
            return "ORCHESTRATOR"

        if (
            "build" in name
            or "builder" in name
            or "project" in name
            or "material" in name
        ):
            return "BUILDER_CANDIDATE"

        return "PYTHON_REFERENCE"

    if path.suffix.lower() == ".ps1":
        return "POWERSHELL_REFERENCE"

    if "contract" in rel or "schema" in rel:
        return "CONTRACT_OR_SCHEMA"

    if path.suffix.lower() in {".md", ".txt"}:
        return "DOCUMENTATION_OR_EVIDENCE"

    if path.suffix.lower() == ".json":
        return "JSON_REFERENCE"

    if path.suffix.lower() == ".csv":
        return "CSV_REFERENCE"

    if path.suffix.lower() in {".ts", ".tsx", ".js", ".jsx"}:
        return "RUNTIME_OR_REACT_REFERENCE"

    return "OTHER_REFERENCE"


def producer_score(
    path: Path,
    lines: list[str],
    target_filename: str,
) -> int:
    score = 0
    name = path.name.lower()
    content = "\n".join(lines).lower()

    if path.suffix.lower() == ".py":
        score += 20

    if "build" in name or "builder" in name:
        score += 30

    if "race_entry" in name:
        score += 15

    if "performance_snapshot" in name:
        score += 20

    if "output" in content:
        score += 10

    if "write_text" in content:
        score += 10

    if "to_csv" in content:
        score += 15

    if "csv.writer" in content or "dictwriter" in content:
        score += 15

    if "open(" in content and target_filename.lower() in content:
        score += 10

    if "audit" in name or "check" in name or "verify" in name:
        score -= 25

    if path.suffix.lower() in {".md", ".txt", ".json", ".csv"}:
        score -= 30

    if "archive" in relative(path).lower():
        score -= 20

    return score


def extract_dataset_references(
    path: Path,
    text: str,
    target_filename: str,
) -> list[dict[str, Any]]:
    references: dict[str, dict[str, Any]] = {}

    for line_number, line in enumerate(
        text.splitlines(),
        start=1,
    ):
        for match in DATA_PATH_PATTERN.finditer(line):
            candidate = match.group(0).replace("\\", "/")
            candidate = candidate.strip("\"'()[]{},")

            if not candidate:
                continue

            if candidate.lower().endswith(
                target_filename.lower()
            ):
                role = "TARGET_OUTPUT"
            else:
                role = "POSSIBLE_DIRECT_DEPENDENCY"

            key = candidate.lower()

            if key not in references:
                references[key] = {
                    "referenced_path_text": candidate,
                    "role": role,
                    "first_line_number": line_number,
                    "source_line": line.strip(),
                    "resolved_repository_path": "",
                    "exists": False,
                    "size_bytes": None,
                    "csv_data_rows": None,
                    "csv_status": "",
                }

    for assignment in PATH_ASSIGNMENT_PATTERN.finditer(text):
        value = assignment.group("value")

        for match in DATA_PATH_PATTERN.finditer(value):
            candidate = match.group(0).replace("\\", "/")
            candidate = candidate.strip("\"'()[]{},")

            if not candidate:
                continue

            key = candidate.lower()

            if key not in references:
                references[key] = {
                    "referenced_path_text": candidate,
                    "role": "POSSIBLE_DIRECT_DEPENDENCY",
                    "first_line_number": None,
                    "source_line": assignment.group(0).strip(),
                    "resolved_repository_path": "",
                    "exists": False,
                    "size_bytes": None,
                    "csv_data_rows": None,
                    "csv_status": "",
                }

    for item in references.values():
        candidate = item["referenced_path_text"]

        possible_paths = [
            ROOT / candidate,
            path.parent / candidate,
            ROOT / "public" / "data" / Path(candidate).name,
            ROOT / "docs" / "performance-intelligence" / Path(candidate).name,
        ]

        resolved = None

        for possible in possible_paths:
            try:
                possible = possible.resolve()
            except OSError:
                continue

            if possible.is_file():
                resolved = possible
                break

        if resolved is None:
            continue

        item["resolved_repository_path"] = relative(resolved)
        item["exists"] = True
        item["size_bytes"] = resolved.stat().st_size

        if resolved.suffix.lower() == ".csv":
            status, rows = inspect_csv(resolved)
            item["csv_status"] = status
            item["csv_data_rows"] = rows

    return sorted(
        references.values(),
        key=lambda item: (
            item["role"],
            item["referenced_path_text"].lower(),
        ),
    )


def inspect_csv(path: Path) -> tuple[str, int | None]:
    if path.stat().st_size == 0:
        return "EMPTY_FILE", 0

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            reader = csv.reader(handle)
            header = next(reader, None)

            if header is None:
                return "EMPTY_FILE", 0

            rows = sum(1 for _ in reader)

            if rows == 0:
                return "HEADER_ONLY", 0

            return "POPULATED", rows

    except Exception:
        return "PARSE_ERROR", None


def main() -> int:
    log("PI_RESTART_UNIT_002B START")

    targets_payload = read_json(TARGETS_JSON)

    if targets_payload.get("verdict") != "PASS":
        raise RuntimeError(
            "Unit 002A lineage targets verdict is not PASS."
        )

    targets = targets_payload.get("targets", [])

    target = next(
        (
            item
            for item in targets
            if int(item.get("target_number", 0))
            == TARGET_NUMBER
        ),
        None,
    )

    if target is None:
        raise RuntimeError(
            "Target 001 was not found in Unit 002A evidence."
        )

    target_relative_path = str(
        target.get("relative_path", "")
    ).strip()

    if not target_relative_path:
        raise RuntimeError(
            "Target 001 has no relative path."
        )

    target_path = ROOT / target_relative_path

    if not target_path.is_file():
        raise FileNotFoundError(
            f"Target 001 is missing: {target_relative_path}"
        )

    target_filename = target_path.name

    log(
        "TARGET_001="
        f"{target_relative_path}"
    )

    references: list[dict[str, Any]] = []
    scanned_file_count = 0

    log("Scanning repository text files for exact target reference")

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue

        try:
            relative_parts = set(
                path.relative_to(ROOT).parts
            )
        except ValueError:
            continue

        if relative_parts & EXCLUDED_PARTS:
            continue

        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        if path.resolve() in {
            OUTPUT_JSON.resolve(),
            OUTPUT_CSV.resolve(),
            OUTPUT_MD.resolve(),
        }:
            continue

        scanned_file_count += 1

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except OSError:
            continue

        matching_lines = [
            line
            for line in text.splitlines()
            if target_filename.lower()
            in line.lower()
        ]

        if not matching_lines:
            continue

        line_numbers = [
            number
            for number, line in enumerate(
                text.splitlines(),
                start=1,
            )
            if target_filename.lower()
            in line.lower()
        ]

        reference_type = classify_reference(path)
        score = producer_score(
            path,
            matching_lines,
            target_filename,
        )

        references.append(
            {
                "relative_path": relative(path),
                "reference_type": reference_type,
                "producer_score": score,
                "match_count": len(matching_lines),
                "line_numbers": ",".join(
                    str(number)
                    for number in line_numbers
                ),
                "first_matching_line": (
                    matching_lines[0].strip()
                ),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )

    references.sort(
        key=lambda item: (
            -int(item["producer_score"]),
            item["relative_path"],
        )
    )

    if not references:
        raise RuntimeError(
            "No repository references to Target 001 were found."
        )

    producer_candidates = [
        item
        for item in references
        if item["reference_type"]
        in {
            "BUILDER_CANDIDATE",
            "PYTHON_REFERENCE",
        }
        and int(item["producer_score"]) > 0
    ]

    if not producer_candidates:
        raise RuntimeError(
            "References were found, but no credible producer "
            "candidate was identified."
        )

    strongest_producer = producer_candidates[0]
    strongest_producer_path = (
        ROOT
        / strongest_producer["relative_path"]
    )

    producer_text = strongest_producer_path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    direct_dataset_references = extract_dataset_references(
        strongest_producer_path,
        producer_text,
        target_filename,
    )

    likely_inputs = [
        item
        for item in direct_dataset_references
        if item["role"]
        == "POSSIBLE_DIRECT_DEPENDENCY"
    ]

    orchestrators = [
        item
        for item in references
        if item["reference_type"] == "ORCHESTRATOR"
    ]

    audits = [
        item
        for item in references
        if item["reference_type"]
        == "AUDIT_OR_VERIFIER"
    ]

    contracts = [
        item
        for item in references
        if item["reference_type"]
        == "CONTRACT_OR_SCHEMA"
    ]

    runtime_references = [
        item
        for item in references
        if item["reference_type"]
        == "RUNTIME_OR_REACT_REFERENCE"
    ]

    with OUTPUT_CSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        fieldnames = [
            "relative_path",
            "reference_type",
            "producer_score",
            "match_count",
            "line_numbers",
            "first_matching_line",
            "sha256",
            "size_bytes",
        ]

        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(references)

    git_head = run_git("rev-parse", "HEAD")
    git_head_short = run_git(
        "rev-parse",
        "--short",
        "HEAD",
    )
    git_branch = run_git(
        "rev-parse",
        "--abbrev-ref",
        "HEAD",
    )

    payload = {
        "program": "EDGEIQ_PERFORMANCE_INTELLIGENCE",
        "unit": "PI_RESTART_UNIT_002B",
        "name": "Target 001 Producer Trace",
        "version": "V1",
        "generated_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "verdict": "PASS",
        "governance": {
            "engine_logic_changed": False,
            "thresholds_changed": False,
            "source_data_changed": False,
            "warehouse_data_changed": False,
            "runtime_data_changed": False,
            "react_changed": False,
        },
        "repository": {
            "branch": git_branch,
            "head": git_head,
            "head_short": git_head_short,
        },
        "target": {
            "target_number": TARGET_NUMBER,
            "relative_path": target_relative_path,
            "filename": target_filename,
            "csv_status": target.get("csv_status"),
            "csv_data_rows": target.get("csv_data_rows"),
            "csv_columns": target.get("csv_columns"),
            "size_bytes": target_path.stat().st_size,
            "sha256": sha256_file(target_path),
        },
        "summary": {
            "scanned_file_count": scanned_file_count,
            "reference_count": len(references),
            "producer_candidate_count": len(
                producer_candidates
            ),
            "orchestrator_reference_count": len(
                orchestrators
            ),
            "audit_reference_count": len(audits),
            "contract_reference_count": len(
                contracts
            ),
            "runtime_reference_count": len(
                runtime_references
            ),
            "direct_dataset_reference_count": len(
                direct_dataset_references
            ),
            "possible_direct_input_count": len(
                likely_inputs
            ),
            "strongest_producer_candidate": (
                strongest_producer["relative_path"]
            ),
            "next_action": (
                "TRACE_TARGET_001_DIRECT_INPUT_ROW_COUNTS"
            ),
        },
        "strongest_producer_candidate": (
            strongest_producer
        ),
        "producer_candidates": producer_candidates,
        "orchestrators": orchestrators,
        "audits": audits,
        "contracts": contracts,
        "runtime_references": runtime_references,
        "all_references": references,
        "direct_dataset_references": (
            direct_dataset_references
        ),
        "possible_direct_inputs": likely_inputs,
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

    markdown = [
        "# EDGEIQ Performance Intelligence Target 001 Producer Trace V1",
        "",
        "## Verdict",
        "",
        "**PASS**",
        "",
        "## Target",
        "",
        f"`{target_relative_path}`",
        "",
        f"- CSV status: `{target.get('csv_status')}`",
        f"- Data rows: `{target.get('csv_data_rows')}`",
        f"- Columns: `{target.get('csv_columns')}`",
        "",
        "## Strongest Producer Candidate",
        "",
        f"`{strongest_producer['relative_path']}`",
        "",
        (
            f"- Producer score: "
            f"`{strongest_producer['producer_score']}`"
        ),
        (
            f"- Exact target matches: "
            f"`{strongest_producer['match_count']}`"
        ),
        (
            f"- Matching lines: "
            f"`{strongest_producer['line_numbers']}`"
        ),
        "",
        "## Reference Summary",
        "",
        (
            f"- Repository text files scanned: "
            f"`{scanned_file_count}`"
        ),
        f"- Exact references found: `{len(references)}`",
        (
            f"- Producer candidates: "
            f"`{len(producer_candidates)}`"
        ),
        f"- Orchestrators: `{len(orchestrators)}`",
        f"- Audits/verifiers: `{len(audits)}`",
        f"- Contracts/schemas: `{len(contracts)}`",
        (
            f"- Runtime/React references: "
            f"`{len(runtime_references)}`"
        ),
        "",
        "## Producer Candidates",
        "",
        "| Rank | File | Type | Score | Matches |",
        "|---:|---|---|---:|---:|",
    ]

    for rank, item in enumerate(
        producer_candidates,
        start=1,
    ):
        markdown.append(
            f"| {rank} "
            f"| `{item['relative_path']}` "
            f"| {item['reference_type']} "
            f"| {item['producer_score']} "
            f"| {item['match_count']} |"
        )

    markdown.extend(
        [
            "",
            "## Possible Direct Dataset Dependencies",
            "",
            "| Referenced path | Role | Exists | CSV status | Rows |",
            "|---|---|---:|---|---:|",
        ]
    )

    for item in direct_dataset_references:
        rows = (
            ""
            if item["csv_data_rows"] is None
            else str(item["csv_data_rows"])
        )

        markdown.append(
            f"| `{item['referenced_path_text']}` "
            f"| {item['role']} "
            f"| {str(item['exists']).upper()} "
            f"| {item['csv_status']} "
            f"| {rows} |"
        )

    markdown.extend(
        [
            "",
            "## Governed Finding",
            "",
            (
                "The strongest producing script has been "
                "identified using exact filename references, "
                "file role and output-writing indicators."
            ),
            "",
            (
                "This unit does not claim that any possible "
                "dataset reference is definitively an input "
                "until Unit 002C validates how the producer "
                "opens and consumes it."
            ),
            "",
            "## Governed Next Action",
            "",
            "**TRACE_TARGET_001_DIRECT_INPUT_ROW_COUNTS**",
            "",
            (
                "Inspect the strongest producer candidate and "
                "measure each directly consumed upstream input. "
                "Stop at the first populated-to-zero transition."
            ),
            "",
            "No repair is authorised.",
            "",
        ]
    )

    OUTPUT_MD.write_text(
        "\n".join(markdown),
        encoding="utf-8",
    )

    log("PI_RESTART_UNIT_002B VERDICT=PASS")
    log(
        "REFERENCE_COUNT="
        f"{len(references)}"
    )
    log(
        "PRODUCER_CANDIDATE_COUNT="
        f"{len(producer_candidates)}"
    )
    log(
        "STRONGEST_PRODUCER_CANDIDATE="
        f"{strongest_producer['relative_path']}"
    )
    log(
        "POSSIBLE_DIRECT_INPUT_COUNT="
        f"{len(likely_inputs)}"
    )
    log(
        "NEXT_ACTION="
        "TRACE_TARGET_001_DIRECT_INPUT_ROW_COUNTS"
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        log("PI_RESTART_UNIT_002B VERDICT=FAIL")
        print(
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(1)
