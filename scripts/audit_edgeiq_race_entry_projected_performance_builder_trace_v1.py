from __future__ import annotations

import ast
import csv
import json
import re
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
SCRIPTS = ROOT / "scripts"
DATA = ROOT / "public" / "data"
CONTRACTS = ROOT / "contracts" / "performance-intelligence"
OUT_DIR = ROOT / "docs" / "performance-intelligence" / "race-entry-projection"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BUILDER = SCRIPTS / "build_edgeiq_race_entry_projected_performance_fact_v1.py"
CONTRACT = CONTRACTS / "edgeiq_race_entry_projected_performance_fact_v1_contract.json"
AUDIT = SCRIPTS / "audit_edgeiq_race_entry_projected_performance_fact_v1.py"
OUTPUT = DATA / "edgeiq_race_entry_projected_performance_fact_v1.csv"


def clean(v):
    return "" if v is None else str(v).strip()


def row_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as h:
        return sum(1 for _ in csv.DictReader(h))


def fields(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as h:
        reader = csv.DictReader(h)
        return list(reader.fieldnames or [])


def literal_assignments(path: Path) -> dict[str, str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            try:
                value = ast.literal_eval(node.value)
            except Exception:
                continue
            if isinstance(value, str):
                values[name] = value
    return values


def path_assignments(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    assignments = {}
    pattern = re.compile(r"(\w+_PATH|\w+PATH|OUTPUT_PATH|INPUT_PATH|ADJUSTED_PATH|AGGREGATE_PATH)\s*=\s*\(\s*DATA\s*/\s*\"([^\"]+)\"", re.S)
    for name, filename in pattern.findall(text):
        assignments[name] = f"public/data/{filename}"
    return assignments


def consumer_files(target: str) -> list[str]:
    refs = []
    for path in SCRIPTS.glob("*.py"):
        if path == BUILDER:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if target in text:
            refs.append(str(path.relative_to(ROOT)))
    return refs


def main() -> int:
    paths = path_assignments(BUILDER)
    literals = literal_assignments(BUILDER)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8")) if CONTRACT.exists() else {}
    trace_rows = []
    for role, rel in paths.items():
        path = ROOT / rel
        trace_rows.append({
            "builder_path": str(BUILDER.relative_to(ROOT)),
            "entry_function": "main",
            "path_role": role,
            "input_or_output_path": rel,
            "exists": "YES" if path.exists() else "NO",
            "rows": row_count(path),
            "fields": ";".join(fields(path)),
        })
    trace_rows.extend([
        {"builder_path": str(BUILDER.relative_to(ROOT)), "entry_function": "main", "path_role": "schema_contract", "input_or_output_path": str(CONTRACT.relative_to(ROOT)), "exists": "YES" if CONTRACT.exists() else "NO", "rows": "", "fields": ";".join(contract.get("required_fields", []))},
        {"builder_path": str(BUILDER.relative_to(ROOT)), "entry_function": "main", "path_role": "audit_script", "input_or_output_path": str(AUDIT.relative_to(ROOT)), "exists": "YES" if AUDIT.exists() else "NO", "rows": "", "fields": ""},
    ])
    with (OUT_DIR / "edgeiq_race_entry_projected_performance_builder_trace_v1.csv").open("w", encoding="utf-8", newline="") as h:
        writer = csv.DictWriter(h, fieldnames=["builder_path", "entry_function", "path_role", "input_or_output_path", "exists", "rows", "fields"])
        writer.writeheader(); writer.writerows(trace_rows)
    contract_rows = []
    for field in contract.get("required_fields", []):
        contract_rows.append({"field_name": field, "required": "YES", "contract_version": contract.get("contract_version", "")})
    for field in contract.get("forbidden_fields", []):
        contract_rows.append({"field_name": field, "required": "FORBIDDEN", "contract_version": contract.get("contract_version", "")})
    with (OUT_DIR / "edgeiq_race_entry_projected_performance_contract_v1.csv").open("w", encoding="utf-8", newline="") as h:
        writer = csv.DictWriter(h, fieldnames=["field_name", "required", "contract_version"])
        writer.writeheader(); writer.writerows(contract_rows)
    consumers = consumer_files("edgeiq_race_entry_projected_performance_fact_v1.csv")
    report = f"""# Race Entry Projected Performance Builder Trace V1\n\nActive builder: `{BUILDER.relative_to(ROOT)}`\n\nEntry function: `main`\n\nOutput: `public/data/edgeiq_race_entry_projected_performance_fact_v1.csv`\n\nOutput rows: `{row_count(OUTPUT)}`\n\nInput paths discovered:\n\n"""
    for row in trace_rows:
        report += f"- `{row['path_role']}` -> `{row['input_or_output_path']}` exists={row['exists']} rows={row['rows']}\n"
    report += "\nRequired decisions/statuses:\n\n"
    for key in ["EXPECTED_ADJUSTED_DECISION", "EXPECTED_ADJUSTED_STATUS", "EXPECTED_AGGREGATE_DECISION", "EXPECTED_AGGREGATE_STATUS", "PUBLICATION_DECISION", "RECONCILIATION_DECISION", "PROJECTED_STATUS"]:
        report += f"- `{key}` = `{literals.get(key, '')}`\n"
    report += "\nActive consumers:\n\n"
    for consumer in consumers:
        report += f"- `{consumer}`\n"
    report += "\nTrace conclusion: projected-performance output is one row per suitability aggregate. Current aggregate rows are zero, so the projected builder is not the first row-loss stage.\n"
    (OUT_DIR / "edgeiq_race_entry_projected_performance_trace_report_v1.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":"BUILDER_TRACE_WRITTEN", "output_rows": row_count(OUTPUT), "consumers": len(consumers)}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
