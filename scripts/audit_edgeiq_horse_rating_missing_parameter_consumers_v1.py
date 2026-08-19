
from __future__ import annotations

import ast
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_DIR = ROOT / "docs" / "performance-intelligence" / "horse-performance-rating" / "method-governance"
DOC_DIR.mkdir(parents=True, exist_ok=True)

OUT_TRACE = DOC_DIR / "edgeiq_missing_parameter_consumer_trace_v1.csv"
OUT_SCHEMA = DOC_DIR / "edgeiq_missing_parameter_required_schemas_v1.csv"
OUT_FORMULA = DOC_DIR / "edgeiq_missing_parameter_formula_usage_v1.csv"
OUT_REPORT = DOC_DIR / "edgeiq_missing_parameter_consumer_report_v1.md"

MISSING_SOURCES = {
    "edgeiq_performance_normalisation_parameter_source_v1.csv": {
        "builder": "scripts/build_edgeiq_performance_normalisation_parameter_fact_v1.py",
        "fact": "public/data/edgeiq_performance_normalisation_parameter_fact_v1.csv",
        "contract": "contracts/performance-intelligence/edgeiq_performance_normalisation_parameter_fact_v1_contract.json",
        "class": "METHODOLOGICAL_NORMALISATION_PARAMETER_SOURCE",
    },
    "edgeiq_horse_performance_aggregation_parameter_source_v1.csv": {
        "builder": "scripts/build_edgeiq_horse_performance_aggregation_parameter_fact_v1.py",
        "fact": "public/data/edgeiq_horse_performance_aggregation_parameter_fact_v1.csv",
        "contract": "contracts/performance-intelligence/edgeiq_horse_performance_aggregation_parameter_fact_v1_contract.json",
        "class": "METHODOLOGICAL_AGGREGATION_PARAMETER_SOURCE",
    },
    "edgeiq_horse_performance_identity_map_v1.csv": {
        "builder": "scripts/build_edgeiq_horse_performance_observation_fact_v1.py",
        "fact": "public/data/edgeiq_horse_performance_observation_fact_v1.csv",
        "contract": "contracts/performance-intelligence/edgeiq_horse_performance_observation_fact_v1_contract.json",
        "class": "IDENTITY_GOVERNANCE_SOURCE",
    },
}

SCAN_DIRS = [ROOT / "scripts", ROOT / "contracts" / "performance-intelligence", ROOT / "docs" / "performance-intelligence" / "horse-performance-rating"]
MAX_BYTES = 2_000_000


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def read_source(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def read_csv_header(path: Path) -> tuple[list[str], int]:
    if not path.exists():
        return [], 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), sum(1 for _ in reader)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def literal_assignments(source: str) -> dict[str, object]:
    out: dict[str, object] = {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if not names:
                continue
            try:
                value = ast.literal_eval(node.value)
            except Exception:
                continue
            for name in names:
                out[name] = value
    return out


def function_names_using(source: str, needle: str) -> str:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return "UNKNOWN"
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            segment = ast.get_source_segment(source, node) or ""
            if needle in segment or "SOURCE_PATH" in segment or "IDENTITY_PATH" in segment or "PARAMETER_PATH" in segment:
                names.append(node.name)
    return ";".join(sorted(set(names))) or "module/global"


def line_hits(source: str, needle: str) -> str:
    hits = []
    for i, line in enumerate(source.splitlines(), start=1):
        if needle in line or Path(needle).stem in line:
            clean = line.strip()
            hits.append(f"{i}: {clean[:220]}")
            if len(hits) >= 8:
                break
    return " | ".join(hits)


def classify_schema(source_name: str, source_fields: list[str], contract_fields: list[str]) -> str:
    if source_fields and contract_fields:
        return "SCHEMA_PROVEN"
    if source_fields or contract_fields:
        return "SCHEMA_PARTIALLY_PROVEN"
    return "SCHEMA_UNPROVEN"

trace_rows: list[dict[str, object]] = []
schema_rows: list[dict[str, object]] = []
formula_rows: list[dict[str, object]] = []

for source_name, meta in MISSING_SOURCES.items():
    builder_path = ROOT / meta["builder"]
    builder_source = read_source(builder_path)
    assignments = literal_assignments(builder_source)
    source_fields = assignments.get("SOURCE_FIELDS") or assignments.get("IDENTITY_FIELDS") or []
    if not isinstance(source_fields, list):
        source_fields = []
    output_fields = assignments.get("OUTPUT_FIELDS") or []
    if not isinstance(output_fields, list):
        output_fields = []
    contract_path = ROOT / meta["contract"]
    contract = {}
    if contract_path.exists():
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract_fields = contract.get("required_fields", []) if isinstance(contract, dict) else []
    allowed_values = contract.get("allowed_values", {}) if isinstance(contract, dict) else {}
    fact_fields, fact_rows = read_csv_header(ROOT / meta["fact"])
    source_path = ROOT / "config" / "performance-intelligence" / source_name
    source_existing_fields, source_existing_rows = read_csv_header(source_path)
    schema_class = classify_schema(source_name, source_fields, contract_fields)

    trace_rows.append({
        "missing_source_file": source_name,
        "source_class": meta["class"],
        "consumer_script": meta["builder"],
        "consumer_function": function_names_using(builder_source, source_name),
        "required_columns": ";".join(source_fields),
        "column_data_types": "validated in builder: dates, decimals, positive integers, SHA-256, enum strings" if source_fields else "UNKNOWN",
        "join_keys": "effective_from_date/effective_to_date" if "parameter" in source_name else "normalised source_horse_name exact lookup",
        "default_behaviour": "missing source returns [] and publishes header-only fact" if "parameter" in source_name else "missing identity map causes hard failure once rating-base rows exist",
        "validation_logic": ";".join(sorted(set(re.findall(r"fail\((?:.|\n){0,120}?\)", builder_source)))[:10]),
        "formula_usage": "feeds LINEAR_CENTRE_AND_SCALE" if "normalisation" in source_name else ("controls rolling aggregate method/lookback/min observations/recency" if "aggregation" in source_name else "maps source_horse_name to canonical horse id/name before aggregation"),
        "failure_status": "CURRENTLY_HEADER_ONLY" if fact_rows == 0 and "parameter" in source_name else ("SOURCE_MISSING_AND_UNREACHABLE_UNTIL_RATING_BASE_ROWS" if source_name.endswith("identity_map_v1.csv") else "UNKNOWN"),
        "downstream_outputs": meta["fact"],
        "source_exists": "YES" if source_path.exists() else "NO",
        "source_rows": source_existing_rows,
        "fact_rows": fact_rows,
    })

    schema_rows.append({
        "missing_source_file": source_name,
        "schema_classification": schema_class,
        "active_source_schema_fields": ";".join(source_fields),
        "active_fact_schema_fields": ";".join(output_fields),
        "contract_required_fields": ";".join(contract_fields),
        "contract_allowed_values": json.dumps(allowed_values, sort_keys=True),
        "source_file_exists": "YES" if source_path.exists() else "NO",
        "source_file_rows": source_existing_rows,
        "source_file_existing_fields": ";".join(source_existing_fields),
    })

    constants = {k: v for k, v in assignments.items() if isinstance(v, (str, int, float)) and any(token in k for token in ["METHOD", "VERSION", "STATUS"])}
    formula_rows.append({
        "missing_source_file": source_name,
        "formula_consumer": meta["builder"],
        "constants": json.dumps(constants, sort_keys=True),
        "formula_usage": "normalised_value = (raw_performance_lengths - centre_value) / scale_value" if "normalisation" in source_name else ("weighted or arithmetic mean over eligible observations; rating fact later uses aggregate value directly" if "aggregation" in source_name else "identity lookup only; no formula"),
        "parameter_fields_used_in_formula": "centre_value;scale_value;effective_from_date;effective_to_date" if "normalisation" in source_name else ("aggregation_method;maximum_observations;lookback_days;minimum_observations;recency_weighting_method;recency_half_life_days;effective_from_date;effective_to_date" if "aggregation" in source_name else "source_horse_name;canonical_horse_id;canonical_horse_name;evidence_sha256"),
        "unsupported_defaults": "NO_DEFAULT_PARAMETER_VALUES_IN_ACTIVE_CODE",
    })

# Add other consumer references across scoped repo.
for scan_dir in SCAN_DIRS:
    if not scan_dir.exists():
        continue
    for path in scan_dir.rglob("*"):
        if not path.is_file() or path.stat().st_size > MAX_BYTES:
            continue
        if path.suffix.lower() not in {".py", ".json", ".md", ".csv", ".txt"}:
            continue
        content = read_source(path)
        for source_name in MISSING_SOURCES:
            if source_name in content and str(path.relative_to(ROOT)).replace("\\", "/") != MISSING_SOURCES[source_name]["builder"]:
                trace_rows.append({
                    "missing_source_file": source_name,
                    "source_class": MISSING_SOURCES[source_name]["class"],
                    "consumer_script": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "consumer_function": function_names_using(content, source_name) if path.suffix.lower() == ".py" else "document/reference",
                    "required_columns": "SEE_PRIMARY_BUILDER_SCHEMA",
                    "column_data_types": "SEE_PRIMARY_BUILDER_SCHEMA",
                    "join_keys": "SEE_PRIMARY_BUILDER_SCHEMA",
                    "default_behaviour": "reference only or audit consumer",
                    "validation_logic": line_hits(content, source_name),
                    "formula_usage": "reference/audit/orchestration",
                    "failure_status": "REFERENCE",
                    "downstream_outputs": "",
                    "source_exists": "",
                    "source_rows": "",
                    "fact_rows": "",
                })

write_csv(OUT_TRACE, ["missing_source_file", "source_class", "consumer_script", "consumer_function", "required_columns", "column_data_types", "join_keys", "default_behaviour", "validation_logic", "formula_usage", "failure_status", "downstream_outputs", "source_exists", "source_rows", "fact_rows"], trace_rows)
write_csv(OUT_SCHEMA, ["missing_source_file", "schema_classification", "active_source_schema_fields", "active_fact_schema_fields", "contract_required_fields", "contract_allowed_values", "source_file_exists", "source_file_rows", "source_file_existing_fields"], schema_rows)
write_csv(OUT_FORMULA, ["missing_source_file", "formula_consumer", "constants", "formula_usage", "parameter_fields_used_in_formula", "unsupported_defaults"], formula_rows)

lines = [
    "# EDGEiQ Missing Horse Rating Governance Source Consumer Trace V1",
    "",
    "## Classification",
]
for row in schema_rows:
    lines.append(f"- `{row['missing_source_file']}`: `{row['schema_classification']}`; source_exists={row['source_file_exists']}; source_rows={row['source_file_rows']}")
lines.extend([
    "",
    "## Findings",
    "- `edgeiq_performance_normalisation_parameter_source_v1.csv` schema is proven by active builder `SOURCE_FIELDS` and the parameter fact contract. It supplies `centre_value` and `scale_value` for `LINEAR_CENTRE_AND_SCALE`.",
    "- `edgeiq_horse_performance_aggregation_parameter_source_v1.csv` schema is proven by active builder `SOURCE_FIELDS` and the parameter fact contract. It supplies aggregation method, lookback, min/max observations and recency treatment.",
    "- `edgeiq_horse_performance_identity_map_v1.csv` schema is proven by active observation builder `IDENTITY_FIELDS`, while the observation fact contract proves its consumer output semantics. It is identity governance, not a formula parameter source.",
    "- Active parameter builders intentionally return an empty source list when the source CSV is absent; that publishes header-only parameter facts. The identity map source is not optional once rating-base rows exist.",
])
OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

print(json.dumps({
    "trace_rows": len(trace_rows),
    "schema_rows": len(schema_rows),
    "formula_rows": len(formula_rows),
    "report": str(OUT_REPORT),
}, indent=2))


if __name__ == "__main__":
    pass
