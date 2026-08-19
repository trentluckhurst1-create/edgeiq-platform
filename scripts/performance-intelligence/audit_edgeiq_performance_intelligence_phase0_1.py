from __future__ import annotations

import ast
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PI_ROOT = ROOT / "docs" / "performance-intelligence"
AUDIT_DIR = PI_ROOT / "audits"
INVENTORY_DIR = PI_ROOT / "inventories"

EXCLUDED_PREFIXES = (
    "_archive_pre_git_commit/",
    "checkpoints/",
    "node_modules/",
    "dist/",
    "build/",
    ".git/",
)

EXCLUDED_PATH_PARTS = (
    "/checkpoint_",
    "_checkpoint_",
    "_backup_",
    "/backups/",
    "/archive/",
    "/archives/",
)

LIVE_PRIORITY_PREFIXES = (
    "scripts/",
    "src/",
    "public/data/",
    "data/",
    "warehouse/",
    "warehouses/",
    "docs/",
)

DATA_EXTENSIONS = {
    ".csv",
    ".json",
    ".parquet",
    ".feather",
    ".sqlite",
    ".sqlite3",
    ".db",
}

CODE_EXTENSIONS = {
    ".py",
    ".ps1",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".sql",
}

TARGET_CATEGORIES = {
    "results",
    "sectionals",
    "benchmarks",
    "length_conversion",
    "performance",
    "identity",
    "quality",
    "patterns",
}

HIGH_VALUE_TERMS = (
    "warehouse",
    "official_result",
    "race_result",
    "results",
    "sectional",
    "standardised_sectionals",
    "benchmark",
    "par_time",
    "standard_time",
    "seconds_to_lengths",
    "seconds_per_length",
    "length_conversion",
    "historical_form",
    "professional_form",
    "runner_profile",
    "performance",
    "epi",
    "eri",
    "canonical",
    "identity",
    "race_strength",
    "fingerprint",
    "campaign",
    "dna",
)

ENGINE_TERMS = (
    "build_",
    "audit_",
    "ingest",
    "normalis",
    "canonical",
    "warehouse",
    "benchmark",
    "sectional",
    "performance",
    "fingerprint",
    "pattern",
    "campaign",
    "identity",
)

FORMULA_PATTERNS = {
    "seconds_per_length": (
        r"seconds[_\s-]*per[_\s-]*length",
        r"sec(?:ond)?s?[_\s-]*per[_\s-]*length",
    ),
    "seconds_to_lengths": (
        r"seconds?[_\s-]*to[_\s-]*lengths?",
        r"lengths?\s*=\s*.*seconds?",
        r"seconds?.*/.*length",
    ),
    "benchmark": (
        r"benchmark",
        r"par[_\s-]*time",
        r"standard[_\s-]*time",
        r"track[_\s-]*standard",
    ),
    "sectional": (
        r"sectional",
        r"last[_\s-]*(?:800|600|400|200)",
        r"(?:800|600|400|200)[_\s-]*(?:600|400|200|finish|f)",
    ),
    "epi": (
        r"\bepi\b",
        r"edgeiq[_\s-]*performance[_\s-]*index",
    ),
    "eri": (
        r"\beri\b",
        r"edgeiq[_\s-]*race[_\s-]*index",
        r"race[_\s-]*strength",
    ),
    "quality": (
        r"quality[_\s-]*state",
        r"confidence",
        r"excluded",
        r"mismatch",
        r"inconsisten",
    ),
    "identity": (
        r"canonical[_\s-]*(?:horse|race|meeting|track|course)[_\s-]*id",
        r"identity[_\s-]*resolution",
        r"deduplicat",
        r"alias",
    ),
}

REFERENCE_PATTERN = re.compile(
    r"""(?P<quote>["'])(?P<target>[^"']+\.(?:csv|json|parquet|feather|sqlite|sqlite3|db))(?P=quote)""",
    re.IGNORECASE,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def latest_inventory_csv() -> Path:
    candidates = sorted(
        INVENTORY_DIR.glob(
            "edgeiq_performance_intelligence_asset_inventory_*.csv"
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(
            "No Phase 0 asset inventory CSV was found."
        )
    return candidates[0]


def read_inventory(path: Path) -> list[dict[str, Any]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


def is_excluded(path_text: str) -> bool:
    lowered = path_text.replace("\\", "/").lower()

    if lowered.startswith(EXCLUDED_PREFIXES):
        return True

    return any(part in lowered for part in EXCLUDED_PATH_PARTS)


def parse_categories(value: str) -> set[str]:
    if not value:
        return set()

    return {
        item.strip()
        for item in value.split("|")
        if item.strip()
    }


def live_priority(path_text: str) -> int:
    lowered = path_text.lower()

    for index, prefix in enumerate(LIVE_PRIORITY_PREFIXES):
        if lowered.startswith(prefix):
            return len(LIVE_PRIORITY_PREFIXES) - index

    return 0


def score_record(record: dict[str, Any]) -> tuple[int, list[str]]:
    path_text = record["path"].replace("\\", "/")
    lowered = path_text.lower()
    name = record.get("name", "").lower()
    categories = parse_categories(record.get("categories", ""))

    score = 0
    reasons: list[str] = []

    priority = live_priority(path_text)
    if priority:
        score += priority * 3
        reasons.append(f"live_path_priority={priority}")

    matched_categories = sorted(categories & TARGET_CATEGORIES)
    if matched_categories:
        score += len(matched_categories) * 4
        reasons.append(
            "categories=" + ",".join(matched_categories)
        )

    term_hits = sorted(
        term for term in HIGH_VALUE_TERMS
        if term in lowered
    )
    if term_hits:
        score += min(len(term_hits), 5) * 3
        reasons.append(
            "terms=" + ",".join(term_hits[:8])
        )

    if any(name.startswith(term) for term in ENGINE_TERMS):
        score += 8
        reasons.append("engine_or_audit_script")

    suffix = record.get("extension", "").lower()

    if suffix in DATA_EXTENSIONS:
        score += 5
        reasons.append("data_asset")

    if suffix in CODE_EXTENSIONS:
        score += 3
        reasons.append("code_asset")

    if path_text.startswith("public/data/"):
        score += 8
        reasons.append("active_public_feed")

    if path_text.startswith("scripts/"):
        score += 8
        reasons.append("active_script")

    if path_text.startswith("src/"):
        score += 5
        reasons.append("active_consumer")

    if path_text.startswith("docs/performance-intelligence/"):
        score -= 20
        reasons.append("current_audit_output")

    if "audit" in name:
        score += 2
        reasons.append("audit_evidence")

    return score, reasons


def safe_read(path: Path, limit: int = 5_000_000) -> str:
    try:
        if not path.exists() or path.stat().st_size > limit:
            return ""
        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except OSError:
        return ""


def extract_python_functions(content: str) -> list[str]:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    functions: list[str] = []

    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            functions.append(node.name)

    return sorted(set(functions))


def formula_evidence(
    path_text: str,
    content: str,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    if not content:
        return findings

    lines = content.splitlines()

    for formula_type, patterns in FORMULA_PATTERNS.items():
        compiled = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in patterns
        ]

        for line_number, line in enumerate(lines, start=1):
            if not any(pattern.search(line) for pattern in compiled):
                continue

            stripped = line.strip()
            if not stripped:
                continue

            findings.append(
                {
                    "path": path_text,
                    "formula_type": formula_type,
                    "line_number": line_number,
                    "line_text": stripped[:500],
                }
            )

            if sum(
                1
                for item in findings
                if item["formula_type"] == formula_type
            ) >= 40:
                break

    return findings


def resolve_reference(
    source_path: Path,
    target_text: str,
) -> tuple[str, str]:
    target_text = target_text.replace("\\", "/")
    candidates = []

    direct = ROOT / target_text
    candidates.append(direct)

    relative_to_source = source_path.parent / target_text
    candidates.append(relative_to_source)

    if target_text.startswith("/"):
        candidates.append(ROOT / target_text.lstrip("/"))

    if target_text.startswith("data/"):
        candidates.append(ROOT / "public" / target_text)

    if target_text.startswith("public/data/"):
        candidates.append(ROOT / target_text)

    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue

        if resolved.exists():
            try:
                relative_path = resolved.relative_to(ROOT)
                return (
                    str(relative_path).replace("\\", "/"),
                    "RESOLVED",
                )
            except ValueError:
                return (str(resolved), "OUTSIDE_REPOSITORY")

    return ("", "UNRESOLVED_OR_GENERATED")


def inspect_candidate(
    record: dict[str, Any],
    score: int,
    reasons: list[str],
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    path_text = record["path"].replace("\\", "/")
    full_path = ROOT / path_text
    content = safe_read(full_path)

    functions: list[str] = []
    if full_path.suffix.lower() == ".py" and content:
        functions = extract_python_functions(content)

    references: list[dict[str, Any]] = []

    if content:
        for match in REFERENCE_PATTERN.finditer(content):
            referenced_text = match.group("target")
            resolved_path, status = resolve_reference(
                full_path,
                referenced_text,
            )

            references.append(
                {
                    "consumer_path": path_text,
                    "referenced_text": referenced_text,
                    "resolved_path": resolved_path,
                    "reference_status": status,
                }
            )

    unique_references = {
        (
            item["consumer_path"],
            item["referenced_text"],
            item["resolved_path"],
        ): item
        for item in references
    }

    detail = {
        "path": path_text,
        "score": score,
        "score_reasons": " | ".join(reasons),
        "extension": record.get("extension", ""),
        "size_bytes": record.get("size_bytes", ""),
        "modified_utc": record.get("modified_utc", ""),
        "categories": record.get("categories", ""),
        "row_count": record.get("row_count", ""),
        "column_count": record.get("column_count", ""),
        "columns": record.get("columns", ""),
        "record_count": record.get("record_count", ""),
        "top_level_keys": record.get("top_level_keys", ""),
        "python_functions": " | ".join(functions),
        "content_scanned": bool(content),
    }

    formulas = formula_evidence(path_text, content)

    return (
        detail,
        sorted(
            unique_references.values(),
            key=lambda item: (
                item["consumer_path"],
                item["referenced_text"],
            ),
        ),
        formulas,
    )


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames: list[str] = []

    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def build_markdown(
    summary: dict[str, Any],
    candidates: list[dict[str, Any]],
    references: list[dict[str, Any]],
    formulas: list[dict[str, Any]],
) -> str:
    lines: list[str] = []

    lines.append("# EDGEiQ Performance Intelligence")
    lines.append("## Phase 0.1 Live Asset Isolation and Lineage Triage")
    lines.append("")
    lines.append(f"Generated UTC: `{summary['generated_utc']}`")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This pass removes archived and checkpoint copies from the "
        "Phase 0 inventory, ranks active assets, and extracts first-pass "
        "lineage and formula evidence."
    )
    lines.append("")
    lines.append("No asset is declared canonical by this report.")
    lines.append("")
    lines.append("## Totals")
    lines.append("")
    lines.append(
        f"- Original retained inventory: "
        f"**{summary['original_inventory_count']}**"
    )
    lines.append(
        f"- Archived/checkpoint assets excluded: "
        f"**{summary['excluded_archive_checkpoint_count']}**"
    )
    lines.append(
        f"- Live-scope assets remaining: "
        f"**{summary['live_scope_count']}**"
    )
    lines.append(
        f"- High-value candidates inspected: "
        f"**{summary['candidate_count']}**"
    )
    lines.append(
        f"- Candidate data references: "
        f"**{summary['reference_count']}**"
    )
    lines.append(
        f"- Resolved candidate references: "
        f"**{summary['resolved_reference_count']}**"
    )
    lines.append(
        f"- Unresolved or generated references: "
        f"**{summary['unresolved_reference_count']}**"
    )
    lines.append(
        f"- Formula and governance evidence lines: "
        f"**{summary['formula_evidence_count']}**"
    )
    lines.append("")
    lines.append("## Highest-ranked live assets")
    lines.append("")
    lines.append(
        "| Score | Path | Categories | Reason |"
    )
    lines.append("|---:|---|---|---|")

    for candidate in candidates[:100]:
        lines.append(
            f"| {candidate['score']} | "
            f"`{candidate['path']}` | "
            f"{candidate['categories']} | "
            f"{candidate['score_reasons']} |"
        )

    lines.append("")
    lines.append("## Formula evidence counts")
    lines.append("")
    lines.append("| Type | Matches |")
    lines.append("|---|---:|")

    for formula_type, count in (
        summary["formula_type_counts"].items()
    ):
        lines.append(f"| {formula_type} | {count} |")

    lines.append("")
    lines.append("## Length-conversion evidence")
    lines.append("")

    length_findings = [
        item
        for item in formulas
        if item["formula_type"] in {
            "seconds_per_length",
            "seconds_to_lengths",
        }
    ]

    if not length_findings:
        lines.append(
            "_No proven live length-conversion formula was identified._"
        )
    else:
        for item in length_findings[:100]:
            lines.append(
                f"- `{item['path']}:{item['line_number']}` "
                f"`{item['line_text']}`"
            )

    lines.append("")
    lines.append("## Immediate interpretation")
    lines.append("")
    lines.append(
        "- The original Phase 0 counts were materially inflated by "
        "archive and checkpoint duplication."
    )
    lines.append(
        "- This report identifies live candidates only; canonical status "
        "still requires source-to-output lineage validation."
    )
    lines.append(
        "- Length-conversion evidence requires direct inspection because "
        "the original inventory identified only three matching files."
    )
    lines.append(
        "- The next pass should open the highest-ranked scripts and data "
        "assets by domain and verify schemas, row coverage, date coverage, "
        "inputs, transformations, outputs and consumers."
    )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    INVENTORY_DIR.mkdir(parents=True, exist_ok=True)

    source_inventory = latest_inventory_csv()
    inventory = read_inventory(source_inventory)

    excluded_count = 0
    live_records: list[dict[str, Any]] = []

    for record in inventory:
        if is_excluded(record["path"]):
            excluded_count += 1
            continue

        live_records.append(record)

    ranked: list[
        tuple[int, list[str], dict[str, Any]]
    ] = []

    for record in live_records:
        score, reasons = score_record(record)

        if score >= 12:
            ranked.append((score, reasons, record))

    ranked.sort(
        key=lambda item: (
            -item[0],
            item[2]["path"].lower(),
        )
    )

    candidate_details: list[dict[str, Any]] = []
    all_references: list[dict[str, Any]] = []
    all_formulas: list[dict[str, Any]] = []

    for score, reasons, record in ranked:
        detail, references, formulas = inspect_candidate(
            record,
            score,
            reasons,
        )

        candidate_details.append(detail)
        all_references.extend(references)
        all_formulas.extend(formulas)

    unique_references = {
        (
            item["consumer_path"],
            item["referenced_text"],
            item["resolved_path"],
        ): item
        for item in all_references
    }

    all_references = sorted(
        unique_references.values(),
        key=lambda item: (
            item["consumer_path"],
            item["referenced_text"],
        ),
    )

    unique_formulas = {
        (
            item["path"],
            item["formula_type"],
            item["line_number"],
            item["line_text"],
        ): item
        for item in all_formulas
    }

    all_formulas = sorted(
        unique_formulas.values(),
        key=lambda item: (
            item["formula_type"],
            item["path"],
            item["line_number"],
        ),
    )

    resolved_count = sum(
        1
        for item in all_references
        if item["reference_status"] == "RESOLVED"
    )

    formula_type_counts = Counter(
        item["formula_type"]
        for item in all_formulas
    )

    summary = {
        "audit_name": (
            "EDGEiQ Performance Intelligence Phase 0.1 "
            "Live Asset Isolation and Lineage Triage"
        ),
        "generated_utc": utc_now(),
        "source_inventory": str(
            source_inventory.relative_to(ROOT)
        ).replace("\\", "/"),
        "original_inventory_count": len(inventory),
        "excluded_archive_checkpoint_count": excluded_count,
        "live_scope_count": len(live_records),
        "candidate_count": len(candidate_details),
        "reference_count": len(all_references),
        "resolved_reference_count": resolved_count,
        "unresolved_reference_count": (
            len(all_references) - resolved_count
        ),
        "formula_evidence_count": len(all_formulas),
        "formula_type_counts": dict(
            sorted(formula_type_counts.items())
        ),
        "top_candidate_paths": [
            item["path"]
            for item in candidate_details[:100]
        ],
        "canonical_status": (
            "NOT_YET_DETERMINED"
        ),
        "next_required_stage": (
            "Phase 0.2 domain-by-domain schema, coverage, "
            "lineage and reuse validation."
        ),
    }

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    live_inventory_csv = (
        INVENTORY_DIR
        / f"edgeiq_performance_intelligence_live_scope_{run_id}.csv"
    )
    candidates_csv = (
        INVENTORY_DIR
        / f"edgeiq_performance_intelligence_live_candidates_{run_id}.csv"
    )
    references_csv = (
        INVENTORY_DIR
        / f"edgeiq_performance_intelligence_live_lineage_{run_id}.csv"
    )
    formulas_csv = (
        INVENTORY_DIR
        / f"edgeiq_performance_intelligence_formula_evidence_{run_id}.csv"
    )
    summary_json = (
        AUDIT_DIR
        / f"edgeiq_performance_intelligence_phase0_1_summary_{run_id}.json"
    )
    report_md = (
        AUDIT_DIR
        / f"edgeiq_performance_intelligence_phase0_1_report_{run_id}.md"
    )
    latest_json = (
        AUDIT_DIR
        / "edgeiq_performance_intelligence_phase0_1_latest.json"
    )

    write_csv(live_inventory_csv, live_records)
    write_csv(candidates_csv, candidate_details)
    write_csv(references_csv, all_references)
    write_csv(formulas_csv, all_formulas)
    write_json(summary_json, summary)
    write_json(latest_json, summary)

    report_md.write_text(
        build_markdown(
            summary,
            candidate_details,
            all_references,
            all_formulas,
        ),
        encoding="utf-8",
    )

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE0_1_LIVE_TRIAGE_PASS"
    )
    print(f"SOURCE_INVENTORY={source_inventory}")
    print(f"ORIGINAL_COUNT={len(inventory)}")
    print(f"ARCHIVE_CHECKPOINT_EXCLUDED={excluded_count}")
    print(f"LIVE_SCOPE={len(live_records)}")
    print(f"CANDIDATES={len(candidate_details)}")
    print(f"REFERENCES={len(all_references)}")
    print(f"RESOLVED_REFERENCES={resolved_count}")
    print(f"FORMULA_EVIDENCE={len(all_formulas)}")
    print(f"LIVE_INVENTORY={live_inventory_csv}")
    print(f"CANDIDATES_CSV={candidates_csv}")
    print(f"LINEAGE_CSV={references_csv}")
    print(f"FORMULAS_CSV={formulas_csv}")
    print(f"SUMMARY_JSON={summary_json}")
    print(f"REPORT_MD={report_md}")


if __name__ == "__main__":
    main()
