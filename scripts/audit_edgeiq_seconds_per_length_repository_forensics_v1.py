from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


try:
    csv.field_size_limit(min(sys.maxsize, 2_147_483_647))
except OverflowError:
    csv.field_size_limit(2_147_483_647)

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "lengths-v-standard"
DOCS.mkdir(parents=True, exist_ok=True)

HITS_OUT = DOCS / "edgeiq_seconds_per_length_repository_hits_v1.csv"
METHODS_OUT = DOCS / "edgeiq_seconds_per_length_candidate_methods_v1.csv"
CONSUMERS_OUT = DOCS / "edgeiq_seconds_per_length_consumer_map_v1.csv"
AUDIT_OUT = DOCS / "edgeiq_seconds_per_length_forensics_audit_v1.csv"
REPORT_OUT = DOCS / "edgeiq_seconds_per_length_forensics_report_v1.md"
IMPLIED_OUT = DOCS / "edgeiq_historical_implied_seconds_per_length_v1.csv"
CONSISTENCY_OUT = DOCS / "edgeiq_historical_conversion_consistency_v1.csv"
RECOVERY_REPORT = DOCS / "edgeiq_historical_conversion_recovery_report_v1.md"

SEARCH_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".json", ".csv", ".md", ".txt", ".yaml", ".yml", ".toml", ".ini"
}
TERMS = [
    "seconds_per_length", "seconds per length", "sec_per_length", "secs_per_length",
    "time_per_length", "lengths_per_second", "time_to_lengths", "seconds_to_lengths",
    "lengths_from_time", "time margin", "time_margin", "length conversion",
    "lengths conversion", "beaten lengths", "margin seconds", "speed-derived length",
    "horse length", "metres per length", "meters per length", "0.14", "0.15", "0.16",
    "0.17", "0.18", "0.19", "0.20", "0.21", "0.22",
]
LOWER_TERMS = [term.casefold() for term in TERMS]
NUMERIC_TERMS = {"0.14", "0.15", "0.16", "0.17", "0.18", "0.19", "0.20", "0.21", "0.22"}
NUMERIC_CONTEXT = [
    "length", "second", "secs", "time", "margin", "conversion", "horse", "metre", "meter", "lvs"
]


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: clean(row.get(field, "")) for field in fields})


def read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            return list(reader)
    except Exception:
        return []


def iter_files() -> list[Path]:
    skip_dirs = {
        ".git",
        "node_modules",
        "dist",
        ".vite",
        "__pycache__",
        "raw",
        "checkpoints",
        "screenshots",
        "approved-ui-rebuild",
        "final-live-data",
        "final-live-runtime",
    }
    allowed_roots = {
        "scripts",
        "src",
        "docs",
        "contracts",
        "config",
        "public",
    }
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SEARCH_EXTENSIONS:
            continue
        relative_parts = path.relative_to(ROOT).parts
        if not relative_parts or relative_parts[0] not in allowed_roots:
            continue
        if any(part in skip_dirs for part in relative_parts):
            continue
        if path.stat().st_size > 10_000_000:
            continue
        files.append(path)
    return sorted(files)


def classify_evidence(path: Path, line: str) -> str:
    text = f"{rel(path)} {line}".casefold()
    if "contract" in text and "seconds_per_length" in text:
        return "DIRECT_GOVERNED_CONTRACT"
    if "build_edgeiq_lengths_versus_standard_v1.py" in text or "audit_edgeiq_lengths_versus_standard_v1.py" in text:
        return "ACTIVE_IMPLEMENTATION_WITH_TESTS"
    if "length_conversion_parameter" in text:
        return "ACTIVE_IMPLEMENTATION_WITH_TESTS"
    if "historical" in text:
        return "HISTORICAL_IMPLEMENTATION"
    if "report" in text or "md" in text or "docs/" in text:
        return "DOCUMENTED_BUT_UNUSED"
    return "UNSUPPORTED_REFERENCE"


def candidate_from_hit(hit: dict[str, object]) -> dict[str, object] | None:
    line = clean(hit.get("line"))
    file_name = clean(hit.get("file"))
    if not any(term in line.casefold() for term in ["seconds_per_length", "length conversion", "lengths_versus_standard", "seconds per length"]):
        return None
    formula = ""
    if "NEGATIVE_TIME_DELTA_DIVIDED_BY_SECONDS_PER_LENGTH" in line:
        formula = "lengths_versus_standard = -time_delta_seconds / seconds_per_length"
    elif "seconds_per_length" in line:
        formula = "seconds_per_length parameter referenced"
    elif "length conversion" in line.casefold():
        formula = "length conversion referenced"
    return {
        "file": file_name,
        "line_or_logical_location": hit.get("line_number", ""),
        "method_name": "EDGEIQ_LENGTHS_VERSUS_STANDARD_V1" if "lengths_versus_standard" in file_name else "UNKNOWN_REFERENCE",
        "constant_or_formula": formula,
        "units": "seconds per length" if "seconds_per_length" in line else "UNKNOWN",
        "scope": "DISTANCE_EXACT" if "DISTANCE_EXACT" in line or "length_conversion_parameter" in file_name else "UNKNOWN",
        "distance_dependency": "distance exact parameter lookup" if "official_distance_metres" in line or "length_conversion_parameter" in file_name else "UNKNOWN",
        "speed_dependency": "not explicit",
        "surface_dependency": "not explicit",
        "track_condition_dependency": "not explicit",
        "source_provenance": "config/performance-intelligence/edgeiq_length_conversion_parameter_source_v1.csv" if "length_conversion_parameter" in file_name else "repository reference",
        "active_or_obsolete": "ACTIVE" if "scripts/build_edgeiq_lengths_versus_standard_v1.py" in file_name or "length_conversion_parameter" in file_name else "UNKNOWN",
        "current_consumers": "Lengths v Standard builder/audit" if "length_conversion_parameter" in file_name or "lengths_versus_standard" in file_name else "",
        "test_coverage": "audit script present" if "audit_" in file_name else "",
        "governance_status": hit.get("evidence_classification", "UNSUPPORTED_REFERENCE"),
    }


def implied_rows_from_csv(path: Path) -> list[dict[str, object]]:
    rows = read_csv(path)
    if not rows:
        return []
    fields = {field.casefold(): field for field in rows[0].keys()}
    time_delta_field = next((fields[name] for name in ["time_delta_seconds", "time_difference_seconds", "time_margin_seconds", "margin_seconds"] if name in fields), "")
    lvs_field = next((fields[name] for name in ["lengths_versus_standard", "lengths_vs_standard", "lvs"] if name in fields), "")
    actual_field = next((fields[name] for name in ["actual_elapsed_time_seconds", "winner_race_time_seconds"] if name in fields), "")
    standard_field = next((fields[name] for name in ["standard_elapsed_time_seconds", "standard_time_seconds"] if name in fields), "")
    out: list[dict[str, object]] = []
    if not lvs_field or not (time_delta_field or (actual_field and standard_field)):
        return out
    for ordinal, row in enumerate(rows, start=1):
        try:
            lvs = float(clean(row.get(lvs_field)))
            if time_delta_field:
                time_delta = float(clean(row.get(time_delta_field)))
            else:
                time_delta = float(clean(row.get(actual_field))) - float(clean(row.get(standard_field)))
        except Exception:
            continue
        if not math.isfinite(lvs) or not math.isfinite(time_delta) or abs(lvs) < 1e-9 or abs(time_delta) < 1e-9:
            continue
        implied = abs(time_delta) / abs(lvs)
        if not math.isfinite(implied) or implied <= 0:
            continue
        out.append({
            "source_file": rel(path),
            "row_number": ordinal,
            "time_delta_field": time_delta_field,
            "lengths_field": lvs_field,
            "time_delta_seconds": f"{time_delta:.6f}",
            "lengths_value": f"{lvs:.6f}",
            "implied_seconds_per_length": f"{implied:.9f}",
            "identity_trace": "|".join(clean(row.get(key, "")) for key in ["race_key", "canonical_race_id", "benchmark_group_id", "horse", "winner_horse_name"] if key in row),
            "usability_status": "USABLE" if 0.05 <= implied <= 1.0 else "OUT_OF_RANGE",
        })
    return out


def main() -> int:
    files = iter_files()
    hits: list[dict[str, object]] = []
    for path in files:
        try:
            if path.stat().st_size > 50_000_000 and path.suffix.lower() == ".csv":
                continue
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        for number, line in enumerate(lines, start=1):
            lowered = line.casefold()
            matched = [term for term, low in zip(TERMS, LOWER_TERMS) if low in lowered]
            if not matched:
                continue
            if all(term in NUMERIC_TERMS for term in matched) and not any(token in lowered for token in NUMERIC_CONTEXT):
                continue
            hits.append({
                "file": rel(path),
                "line_number": number,
                "matched_terms": ";".join(matched),
                "line": line.strip()[:1000],
                "evidence_classification": classify_evidence(path, line),
            })

    candidates = [row for row in (candidate_from_hit(hit) for hit in hits) if row]
    unique_candidates: dict[tuple[str, str, str], dict[str, object]] = {}
    for row in candidates:
        key = (clean(row["file"]), clean(row["line_or_logical_location"]), clean(row["constant_or_formula"]))
        unique_candidates[key] = row
    candidates = list(unique_candidates.values())

    consumer_rows = []
    for hit in hits:
        file_name = clean(hit["file"])
        line = clean(hit["line"])
        if "lengths_versus_standard" in file_name or "standard_time" in line.casefold() or "length_conversion_parameter" in line.casefold():
            consumer_rows.append({
                "consumer_file": file_name,
                "line_number": hit["line_number"],
                "reference": line[:500],
                "consumer_type": "SCRIPT" if file_name.startswith("scripts/") else "DOC_OR_DATA",
                "active_status": "ACTIVE_REFERENCE" if file_name.startswith("scripts/") else "REFERENCE",
            })

    implied: list[dict[str, object]] = []
    for path in files:
        if path.suffix.lower() != ".csv":
            continue
        if any(token in rel(path).casefold() for token in ["length", "standard", "time_delta", "epi", "sectional", "performance"]):
            implied.extend(implied_rows_from_csv(path))

    usable_implied = [row for row in implied if row["usability_status"] == "USABLE"]
    values = [float(row["implied_seconds_per_length"]) for row in usable_implied]
    unique_values = sorted({round(value, 6) for value in values})
    consistency = [{
        "rows_evaluated": len(implied),
        "rows_usable": len(usable_implied),
        "unique_implied_values": len(unique_values),
        "median_implied_value": f"{sorted(values)[len(values)//2]:.9f}" if values else "",
        "min_implied_value": f"{min(values):.9f}" if values else "",
        "max_implied_value": f"{max(values):.9f}" if values else "",
        "variation": f"{(max(values)-min(values)):.9f}" if values else "",
        "single_historical_rule_recoverable": "YES" if values and len(unique_values) <= 3 and len(usable_implied) >= 20 else "NO",
    }]

    evidence_counts = Counter(clean(hit["evidence_classification"]) for hit in hits)
    source_exists = (ROOT / "config" / "performance-intelligence" / "edgeiq_length_conversion_parameter_source_v1.csv").exists()
    parameter_rows = read_csv(DATA / "edgeiq_length_conversion_parameter_fact_v1.csv")
    audit_rows = [
        {"check": "files_searched", "status": "PASS" if files else "FAIL", "value": len(files), "detail": "Repository text/data files scanned."},
        {"check": "repository_hits", "status": "PASS" if hits else "WARN", "value": len(hits), "detail": "Search-term hits."},
        {"check": "candidate_methods", "status": "PASS" if candidates else "WARN", "value": len(candidates), "detail": "Candidate methods or references."},
        {"check": "governed_source_config_exists", "status": "WARN" if not source_exists else "PASS", "value": str(source_exists), "detail": "Configured source for length conversion parameters."},
        {"check": "published_governed_parameter_rows", "status": "WARN" if not parameter_rows else "PASS", "value": len(parameter_rows), "detail": "Rows in edgeiq_length_conversion_parameter_fact_v1.csv."},
        {"check": "historical_implied_rows_usable", "status": "WARN" if not usable_implied else "PASS", "value": len(usable_implied), "detail": "Rows allowing algebraic recovery."},
    ]

    write_csv(HITS_OUT, hits, ["file", "line_number", "matched_terms", "line", "evidence_classification"])
    write_csv(METHODS_OUT, candidates, [
        "file", "line_or_logical_location", "method_name", "constant_or_formula", "units", "scope",
        "distance_dependency", "speed_dependency", "surface_dependency", "track_condition_dependency",
        "source_provenance", "active_or_obsolete", "current_consumers", "test_coverage", "governance_status",
    ])
    write_csv(CONSUMERS_OUT, consumer_rows, ["consumer_file", "line_number", "reference", "consumer_type", "active_status"])
    write_csv(IMPLIED_OUT, implied, [
        "source_file", "row_number", "time_delta_field", "lengths_field", "time_delta_seconds",
        "lengths_value", "implied_seconds_per_length", "identity_trace", "usability_status",
    ])
    write_csv(CONSISTENCY_OUT, consistency, [
        "rows_evaluated", "rows_usable", "unique_implied_values", "median_implied_value",
        "min_implied_value", "max_implied_value", "variation", "single_historical_rule_recoverable",
    ])
    write_csv(AUDIT_OUT, audit_rows, ["check", "status", "value", "detail"])

    selected_status = "NO_GOVERNED_METHOD_EXISTS"
    if parameter_rows:
        selected_status = "EXISTING_GOVERNED_METHOD_FOUND"
    elif consistency[0]["single_historical_rule_recoverable"] == "YES":
        selected_status = "EXISTING_METHOD_RECOVERABLE_WITH_HIGH_CONFIDENCE"

    REPORT_OUT.write_text(
        "# Seconds Per Length Repository Forensics V1\n\n"
        f"Files searched: `{len(files)}`\n\n"
        f"Repository hits: `{len(hits)}`\n\n"
        f"Candidate method references: `{len(candidates)}`\n\n"
        f"Evidence classes: `{json.dumps(dict(evidence_counts), sort_keys=True)}`\n\n"
        f"Historical implied rows usable: `{len(usable_implied)}`\n\n"
        f"Method selection status: `{selected_status}`\n\n"
        "The active Lengths v Standard implementation expects governed distance-exact seconds-per-length parameters, "
        "but the published parameter fact currently has no rows unless a governed source file is supplied.\n",
        encoding="utf-8",
    )
    RECOVERY_REPORT.write_text(
        "# Historical Conversion Recovery V1\n\n"
        f"Rows evaluated: `{len(implied)}`\n\n"
        f"Rows usable: `{len(usable_implied)}`\n\n"
        f"Unique implied values: `{len(unique_values)}`\n\n"
        f"Single historical rule recoverable: `{consistency[0]['single_historical_rule_recoverable']}`\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "files_searched": len(files),
        "hits": len(hits),
        "candidate_methods": len(candidates),
        "historical_rows_usable": len(usable_implied),
        "method_selection_status": selected_status,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
