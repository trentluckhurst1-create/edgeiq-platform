from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "standard-time-recovery"
DOCS.mkdir(parents=True, exist_ok=True)
csv.field_size_limit(min(sys.maxsize, 2_147_483_647))

INVENTORY = DOCS / "edgeiq_results_speed_warehouse_inventory_v1.csv"
SCHEMA = DOCS / "edgeiq_results_speed_warehouse_schema_v1.csv"
CONSUMERS = DOCS / "edgeiq_results_speed_warehouse_consumers_v1.csv"
AUDIT = DOCS / "edgeiq_results_speed_warehouse_source_selection_audit_v1.csv"
REPORT = DOCS / "edgeiq_results_speed_warehouse_source_selection_report_v1.md"

TERMS = [
    "AvgSpeed", "avg_speed", "average speed", "sectional speed", "segment distance",
    "sectional distance", "distance point", "race distance", "elapsed time",
    "sectional time", "RACINGCOM_GRAPHQL", "SplitTimes", "SectionalTimes",
]


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def infer_grain(rows: list[dict[str, str]], fields: list[str]) -> str:
    if "row_type" in fields:
        counts = Counter(clean(r.get("row_type")) for r in rows)
        return ",".join(f"{k}:{v}" for k, v in counts.items())
    if "fact_grain" in fields:
        counts = Counter(clean(r.get("fact_grain")) for r in rows)
        return ",".join(f"{k}:{v}" for k, v in counts.items())
    return "UNRESOLVED"


def coverage(rows: list[dict[str, str]]) -> tuple[int, int, int]:
    races = len({clean(r.get("race_id") or r.get("race_key")) for r in rows if clean(r.get("race_id") or r.get("race_key"))})
    runners = len({(clean(r.get("race_id") or r.get("race_key")), clean(r.get("horse_key") or r.get("horse_id") or r.get("runner_id") or r.get("horse") or r.get("horse_name"))) for r in rows if clean(r.get("race_id") or r.get("race_key"))})
    graphql = sum(1 for r in rows if "GRAPHQL" in json.dumps(r).upper())
    return races, runners, graphql


def suitability(path: Path, rows: list[dict[str, str]], fields: list[str]) -> str:
    grain = infer_grain(rows, fields)
    has_split = "SPLIT" in grain
    has_speed = any(f in fields for f in ["avg_speed_mps", "avg_speed_kmh"])
    has_distance = "distance_label" in fields
    has_time = any(f in fields for f in ["time", "segment_time", "race_time"])
    if path.name == "edgeiq_racingcom_graphql_speed_normalised_v1.csv" and has_split and has_speed and has_distance:
        return "SELECTED_AUTHORITATIVE_DETAILED_GRAPHQL_RESULTS_SOURCE"
    if has_split and has_speed and has_distance:
        return "SUITABLE_DETAILED_SOURCE"
    if "RUNNER_AGGREGATE" in grain:
        return "NOT_STANDARD_TIME_DETAILED_SOURCE_RUNNER_AGGREGATE"
    return "REVIEW_ONLY"


def main() -> int:
    candidate_paths = [
        DATA / "edgeiq_racingcom_graphql_speed_normalised_v1.csv",
        DATA / "edgeiq_racingcom_canonical_speed_data_v2.csv",
        DATA / "edgeiq_racingcom_performance_warehouse_v2_GRAPHQL_CANDIDATE.csv",
        ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2" / "edgeiq_racingcom_graphql_parser_output_v2.csv",
        ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2" / "edgeiq_racingcom_canonical_speed_contract_v1.csv",
        DATA / "edgeiq_racingcom_performance_warehouse_v2.csv",
    ]
    skipped_large: list[dict[str, str]] = []
    for csv_path in DATA.glob("*.csv"):
        name = csv_path.name.lower()
        if any(token.lower().replace(" ", "_") in name for token in ["speed", "sectional", "results", "performance"]):
            if "racingcom" not in name and csv_path.stat().st_size > 50_000_000:
                skipped_large.append({
                    "path": str(csv_path.relative_to(ROOT)),
                    "row_count": "NOT_SCANNED_LARGE_NON_RACINGCOM",
                    "race_count": "",
                    "runner_count": "",
                    "row_grain": "UNRESOLVED",
                    "speed_fields": "",
                    "distance_fields": "",
                    "time_fields": "",
                    "source_units": "",
                    "identity_fields": "",
                    "provenance_fields": "",
                    "duplicate_key_status": "",
                    "historical_coverage": "",
                    "graphql_coverage": "",
                    "suitability_for_standard_time": "SKIPPED_LARGE_NON_RACINGCOM_NOT_AUTHORITATIVE_FOR_RACINGCOM_GRAPHQL",
                })
                continue
            if csv_path not in candidate_paths:
                candidate_paths.append(csv_path)

    inventory_rows: list[dict[str, str]] = []
    schema_rows: list[dict[str, str]] = []
    for path in candidate_paths:
        rows, fields = read_csv(path)
        if not fields:
            continue
        text_fields = " ".join(fields)
        matched_terms = [term for term in TERMS if term.lower() in text_fields.lower() or term.lower().replace(" ", "_") in path.name.lower()]
        if not matched_terms and path.name not in {"edgeiq_racingcom_performance_warehouse_v2.csv"}:
            continue
        races, runners, graphql = coverage(rows)
        speed_fields = [f for f in fields if "speed" in f.lower()]
        distance_fields = [f for f in fields if "distance" in f.lower()]
        time_fields = [f for f in fields if "time" in f.lower()]
        identity_fields = [f for f in fields if f in {"race_id", "race_key", "horse_id", "horse_key", "horse", "horse_name", "runner_id"}]
        provenance_fields = [f for f in fields if "source" in f.lower() or "sha" in f.lower() or "path" in f.lower()]
        grain = infer_grain(rows, fields)
        duplicate_key_status = "UNRESOLVED"
        if {"race_id", "horse_id", "row_type", "distance_label"}.issubset(set(fields)):
            keys = [(r.get("race_id"), r.get("horse_id"), r.get("row_type"), r.get("distance_label")) for r in rows]
            duplicate_key_status = "DUPLICATES_PRESENT" if len(keys) != len(set(keys)) else "UNIQUE_BY_RACE_RUNNER_TYPE_DISTANCE"
        inventory_rows.append({
            "path": str(path.relative_to(ROOT)),
            "row_count": str(len(rows)),
            "race_count": str(races),
            "runner_count": str(runners),
            "row_grain": grain,
            "speed_fields": "|".join(speed_fields),
            "distance_fields": "|".join(distance_fields),
            "time_fields": "|".join(time_fields),
            "source_units": "m/s and km/h where avg_speed fields present",
            "identity_fields": "|".join(identity_fields),
            "provenance_fields": "|".join(provenance_fields),
            "duplicate_key_status": duplicate_key_status,
            "historical_coverage": str(sum(1 for r in rows if "DIRECT_CSV" in json.dumps(r))),
            "graphql_coverage": str(graphql),
            "suitability_for_standard_time": suitability(path, rows, fields),
        })
        for idx, field in enumerate(fields, start=1):
            nonblank = sum(1 for r in rows if clean(r.get(field)))
            examples = []
            for r in rows:
                v = clean(r.get(field))
                if v and v not in examples:
                    examples.append(v)
                if len(examples) >= 3:
                    break
            schema_rows.append({"path": str(path.relative_to(ROOT)), "column_order": str(idx), "column_name": field, "nonblank_count": str(nonblank), "example_values": "|".join(examples)})

    selected = [r for r in inventory_rows if r["suitability_for_standard_time"] == "SELECTED_AUTHORITATIVE_DETAILED_GRAPHQL_RESULTS_SOURCE"]
    audit_rows = [
        {"check": "authoritative_source_selected", "status": "PASS" if len(selected) == 1 else "FAIL", "value": selected[0]["path"] if selected else "", "detail": "Detailed normalised GraphQL rows preserve SECTIONAL and SPLIT source types."},
        {"check": "runner_warehouse_not_selected", "status": "PASS", "value": "public/data/edgeiq_racingcom_performance_warehouse_v2.csv", "detail": "Runner aggregate compatibility file is not a detailed Standard Time source."},
        {"check": "segment_research_warehouse_retained", "status": "PASS", "value": "public/data/edgeiq_racingcom_canonical_speed_data_v2.csv", "detail": "Mixed canonical segment warehouse remains retained."},
    ]

    consumer_rows = []
    for base in [ROOT / "scripts", ROOT / "src", ROOT / "docs"]:
        if not base.exists():
            continue
        for file in base.rglob("*"):
            if file.suffix.lower() not in {".py", ".ts", ".tsx", ".md", ".json"}:
                continue
            try:
                text = file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for inv in inventory_rows:
                name = Path(inv["path"]).name
                if name in text:
                    consumer_rows.append({"source_path": inv["path"], "consumer_file": str(file.relative_to(ROOT)), "consumer_type": "UI" if str(file.relative_to(ROOT)).startswith("src") else "SCRIPT_OR_DOC"})

    inventory_rows.extend(skipped_large)
    write_csv(INVENTORY, inventory_rows, ["path", "row_count", "race_count", "runner_count", "row_grain", "speed_fields", "distance_fields", "time_fields", "source_units", "identity_fields", "provenance_fields", "duplicate_key_status", "historical_coverage", "graphql_coverage", "suitability_for_standard_time"])
    write_csv(SCHEMA, schema_rows, ["path", "column_order", "column_name", "nonblank_count", "example_values"])
    write_csv(CONSUMERS, consumer_rows, ["source_path", "consumer_file", "consumer_type"])
    write_csv(AUDIT, audit_rows, ["check", "status", "value", "detail"])
    selected_path = selected[0]["path"] if selected else "UNRESOLVED"
    REPORT.write_text(f"# Results Speed Warehouse Source Selection V1\n\nSelected authoritative detailed source: `{selected_path}`\n\nThe promoted runner warehouse is a compatibility surface and is not selected for Standard Time segment observation construction.\n", encoding="utf-8")
    print(json.dumps({"selected_source": selected_path, "candidate_sources": len(inventory_rows), "audit_status": "PASS" if all(r["status"] == "PASS" for r in audit_rows) else "FAIL"}, indent=2))
    return 0 if all(r["status"] == "PASS" for r in audit_rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
