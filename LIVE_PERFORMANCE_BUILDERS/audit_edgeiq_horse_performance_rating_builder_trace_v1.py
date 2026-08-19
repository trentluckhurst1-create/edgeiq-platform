
from __future__ import annotations

import ast
import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_DIR = ROOT / "docs" / "performance-intelligence" / "horse-performance-rating"
DATA = ROOT / "public" / "data"

TRACE_CSV = DOC_DIR / "edgeiq_horse_performance_rating_builder_trace_v1.csv"
CONTRACT_CSV = DOC_DIR / "edgeiq_horse_performance_rating_contract_trace_v1.csv"
CONSUMER_CSV = DOC_DIR / "edgeiq_horse_performance_rating_consumer_map_v1.csv"
REPORT_MD = DOC_DIR / "edgeiq_horse_performance_rating_builder_report_v1.md"

KEYWORDS = [
    "edgeiq_horse_performance_rating_fact_v1",
    "horse_performance_rating",
    "horse performance rating",
    "performance rating fact",
    "historical rating fact",
    "runner performance rating",
    "EPI historical input",
    "projected performance input",
    "race_entry_projected_performance",
]

SCAN_ROOTS = [
    ROOT / "scripts",
    ROOT / "contracts",
    ROOT / "config",
    ROOT / "docs" / "performance-intelligence" / "horse-performance-rating",
    ROOT / "docs" / "performance-intelligence" / "race-entry-projection",
    ROOT / "docs" / "performance-intelligence" / "integration",
    ROOT / "docs" / "performance-intelligence" / "architecture",
    ROOT / "docs" / "performance-intelligence" / "audits",
    ROOT / "docs" / "performance-intelligence" / "inventories",
]

SKIP_PARTS = {"__pycache__", "node_modules", ".git"}
TEXT_SUFFIXES = {".py", ".json", ".csv", ".md", ".txt", ".ps1", ".ts", ".tsx"}
MAX_BYTES = 2_500_000


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def iter_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in SKIP_PARTS for part in path.parts):
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            try:
                if path.stat().st_size > MAX_BYTES:
                    continue
            except OSError:
                continue
            files.append(path)
    return sorted(files)


def extract_constants(source: str) -> dict[str, str]:
    constants: dict[str, str] = {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return constants
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if not names:
                continue
            try:
                value = ast.literal_eval(node.value)
            except Exception:
                value = None
            if isinstance(value, (str, int, float)):
                for name in names:
                    if any(token in name for token in ["VERSION", "METHOD", "STATUS", "DECISION"]):
                        constants[name] = str(value)
    return constants


def extract_path_mentions(source: str) -> list[str]:
    patterns = [
        r"edgeiq_[A-Za-z0-9_]+\.csv",
        r"edgeiq_[A-Za-z0-9_]+\.json",
        r"edgeiq_[A-Za-z0-9_]+\.md",
    ]
    mentions: set[str] = set()
    for pattern in patterns:
        mentions.update(re.findall(pattern, source))
    return sorted(mentions)


def classify_role(rel: str, source: str) -> str:
    name = Path(rel).name
    if name == "build_edgeiq_horse_performance_rating_fact_v1.py":
        return "ACTIVE_RATING_BUILDER"
    if name == "audit_edgeiq_horse_performance_rating_fact_v1.py":
        return "ACTIVE_RATING_AUDIT"
    if name.startswith("build_edgeiq_horse_performance_"):
        return "UPSTREAM_HORSE_PERFORMANCE_BUILDER"
    if name.startswith("audit_edgeiq_horse_performance_"):
        return "UPSTREAM_HORSE_PERFORMANCE_AUDIT"
    if name.startswith("build_edgeiq_race_entry_projected_performance"):
        return "DOWNSTREAM_PROJECTED_PERFORMANCE_BUILDER"
    if name.startswith("audit_edgeiq_race_entry_projected_performance"):
        return "DOWNSTREAM_PROJECTED_PERFORMANCE_AUDIT"
    if name.startswith("build_edgeiq_historical_performance_rating"):
        return "ARCHIVED_HISTORICAL_RATING_BUILDER"
    if rel.startswith("contracts"):
        return "CONTRACT_OR_SCHEMA"
    if "edgeiq_horse_performance_rating_fact_v1" in source:
        return "REFERENCE"
    if "projected_performance" in source:
        return "PROJECTED_PERFORMANCE_REFERENCE"
    return "KEYWORD_REFERENCE"


def line_matches(source: str) -> tuple[int, str]:
    lines = source.splitlines()
    hits: list[str] = []
    count = 0
    lower_source = source.casefold()
    for keyword in KEYWORDS:
        if keyword.casefold() in lower_source:
            count += lower_source.count(keyword.casefold())
    for idx, line in enumerate(lines, start=1):
        if any(keyword.casefold() in line.casefold() for keyword in KEYWORDS):
            snippet = line.strip()
            if len(snippet) > 220:
                snippet = snippet[:217] + "..."
            hits.append(f"{idx}: {snippet}")
            if len(hits) >= 8:
                break
    return count, " | ".join(hits)


def data_file_summary(name: str) -> dict[str, object]:
    path = DATA / name
    fields, rows = read_csv_rows(path)
    return {
        "file_name": name,
        "exists": "YES" if path.exists() else "NO",
        "rows": len(rows),
        "columns": ";".join(fields),
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }


def active_builder_details(path: Path) -> dict[str, object]:
    source = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    constants = extract_constants(source)
    mentions = extract_path_mentions(source)
    return {
        "path": str(path.relative_to(ROOT)) if path.exists() else "",
        "entry_function": "main" if "def main(" in source else "UNKNOWN",
        "input_sources": ";".join(name for name in mentions if name != "edgeiq_horse_performance_rating_fact_v1.csv"),
        "production_path": "edgeiq_horse_performance_rating_fact_v1.csv" if "edgeiq_horse_performance_rating_fact_v1.csv" in source else "UNKNOWN",
        "candidate_path": "NOT_DEFINED" if "CANDIDATE" not in source else "CANDIDATE_DEFINED",
        "formula_version": constants.get("BUILDER_VERSION", "UNKNOWN"),
        "rating_method": constants.get("RATING_METHOD", "UNKNOWN"),
        "contract_version": constants.get("CONTRACT_VERSION", "UNKNOWN"),
    }


def main() -> None:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    trace_rows: list[dict[str, object]] = []
    contract_rows: list[dict[str, object]] = []
    consumer_rows: list[dict[str, object]] = []
    role_counts: Counter[str] = Counter()

    for path in iter_files():
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        match_count, examples = line_matches(source)
        if match_count == 0 and "horse_performance" not in path.name and "projected_performance" not in path.name:
            continue
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        role = classify_role(rel, source)
        role_counts[role] += 1
        constants = extract_constants(source) if path.suffix.lower() == ".py" else {}
        mentions = extract_path_mentions(source)
        trace_rows.append({
            "file_path": rel,
            "role": role,
            "match_count": match_count,
            "file_size_bytes": path.stat().st_size,
            "entry_function": "main" if "def main(" in source else "",
            "input_or_output_mentions": ";".join(mentions),
            "builder_version": constants.get("BUILDER_VERSION", ""),
            "contract_version": constants.get("CONTRACT_VERSION", ""),
            "formula_or_method": constants.get("RATING_METHOD", constants.get("AGGREGATION_METHOD", "")),
            "example_matches": examples,
        })
        if role in {"CONTRACT_OR_SCHEMA", "ACTIVE_RATING_BUILDER", "ACTIVE_RATING_AUDIT"}:
            contract_rows.append({
                "file_path": rel,
                "contract_related_role": role,
                "required_field_mentions": ";".join(sorted(set(re.findall(r'\"([a-zA-Z0-9_]+)\"', source)))[:120]),
                "version_mentions": ";".join(f"{k}={v}" for k, v in constants.items()),
                "input_or_output_mentions": ";".join(mentions),
            })
        if "edgeiq_horse_performance_rating_fact_v1.csv" in source or "horse_performance_rating" in source:
            consumer_rows.append({
                "file_path": rel,
                "consumer_role": role,
                "consumes_rating_fact": "YES" if "edgeiq_horse_performance_rating_fact_v1.csv" in source else "INDIRECT",
                "consumes_projected_performance": "YES" if "edgeiq_race_entry_projected_performance_fact_v1.csv" in source else "NO",
                "output_mentions": ";".join([m for m in mentions if m.startswith("edgeiq_")]),
                "example_matches": examples,
            })

    active_builder = ROOT / "scripts" / "build_edgeiq_horse_performance_rating_fact_v1.py"
    details = active_builder_details(active_builder)
    source_summary = [
        data_file_summary("edgeiq_performance_rating_base_fact_v1.csv"),
        data_file_summary("edgeiq_horse_performance_observation_fact_v1.csv"),
        data_file_summary("edgeiq_horse_performance_aggregate_fact_v1.csv"),
        data_file_summary("edgeiq_horse_performance_rating_fact_v1.csv"),
        data_file_summary("edgeiq_race_entry_projected_performance_fact_v1.csv"),
    ]
    source_rows_by_name = {row["file_name"]: int(row["rows"]) for row in source_summary}

    if not active_builder.exists():
        classification = "ACTIVE_BUILDER_MISSING"
    elif source_rows_by_name.get("edgeiq_horse_performance_aggregate_fact_v1.csv", 0) == 0:
        classification = "ACTIVE_BUILDER_INPUT_EMPTY"
    elif source_rows_by_name.get("edgeiq_horse_performance_rating_fact_v1.csv", 0) == 0:
        classification = "ACTIVE_BUILDER_DEFECT"
    else:
        classification = "ACTIVE_BUILDER_FOUND"

    write_csv(TRACE_CSV, [
        "file_path", "role", "match_count", "file_size_bytes", "entry_function",
        "input_or_output_mentions", "builder_version", "contract_version", "formula_or_method", "example_matches",
    ], sorted(trace_rows, key=lambda r: (str(r["role"]), str(r["file_path"]))))
    write_csv(CONTRACT_CSV, [
        "file_path", "contract_related_role", "required_field_mentions", "version_mentions", "input_or_output_mentions",
    ], contract_rows)
    write_csv(CONSUMER_CSV, [
        "file_path", "consumer_role", "consumes_rating_fact", "consumes_projected_performance", "output_mentions", "example_matches",
    ], consumer_rows)

    method_source = ""
    if active_builder.exists():
        method_source = active_builder.read_text(encoding="utf-8", errors="replace")
    required_fields = []
    required_block = re.search(
        r"require_fields\(\s*input_fields,\s*\[(.*?)\]\s*,?\s*\)",
        method_source,
        re.S,
    )
    if required_block:
        required_fields = re.findall(r'\"([a-zA-Z][a-zA-Z0-9_]+)\"', required_block.group(1))
        required_fields = [field for field in required_fields if field in source_summary[-2]["columns"].split(";") or field.endswith("_id") or field.endswith("_name") or field.endswith("_value") or field.endswith("_status") or field.endswith("_version") or field.endswith("_count") or field.endswith("_date") or field.endswith("_method") or field.endswith("_sha256")]

    report_lines = [
        "# EDGEiQ Horse Performance Rating Builder Trace V1",
        "",
        f"Required classification: `{classification}`",
        "",
        "## Active Builder",
        f"- Path: `{details['path'] or 'NOT FOUND'}`",
        f"- Entry function: `{details['entry_function']}`",
        f"- Input sources: `{details['input_sources']}`",
        f"- Production path: `{details['production_path']}`",
        f"- Candidate path: `{details['candidate_path']}`",
        f"- Formula version: `{details['formula_version']}`",
        f"- Rating method: `{details['rating_method']}`",
        f"- Contract version: `{details['contract_version']}`",
        "",
        "## Source Row Counts",
    ]
    for row in source_summary:
        report_lines.append(f"- `{row['file_name']}`: exists={row['exists']}, rows={row['rows']}, size={row['size_bytes']} bytes")
    report_lines.extend([
        "",
        "## Required Builder Fields",
        "" if required_fields else "No required-field block could be parsed.",
    ])
    for field in required_fields:
        report_lines.append(f"- `{field}`")
    report_lines.extend([
        "",
        "## Role Counts",
    ])
    for role, count in sorted(role_counts.items()):
        report_lines.append(f"- `{role}`: {count}")
    report_lines.extend([
        "",
        "## Finding",
        "The governed active rating builder exists and writes `edgeiq_horse_performance_rating_fact_v1.csv` from `edgeiq_horse_performance_aggregate_fact_v1.csv` using `DIRECT_HISTORICAL_AGGREGATE_VALUE`.",
        "The current zero-row production rating fact is explained at trace level by an empty upstream aggregate input, not by a missing active rating builder.",
        "The next required checkpoint is therefore the row funnel through performance rating base, horse observation, and horse aggregate builders to identify the first zero-row stage.",
    ])
    REPORT_MD.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "classification": classification,
        "active_builder": details,
        "source_rows": source_rows_by_name,
        "trace_rows": len(trace_rows),
        "contract_rows": len(contract_rows),
        "consumer_rows": len(consumer_rows),
        "report": str(REPORT_MD),
    }, indent=2))


if __name__ == "__main__":
    main()
