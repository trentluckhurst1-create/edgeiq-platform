from __future__ import annotations

import csv
import json
import os
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
RACE_DISCOVERY = DATA / "edgeiq_racingcom_race_discovery_v2.csv"
EVIDENCE = DOCS / "edgeiq_racingcom_graphql_race_evidence_v1.csv"
ADMISSION = DOCS / "edgeiq_racingcom_graphql_source_admission_v1.csv"
ACQ = DOCS / "edgeiq_racingcom_graphql_acquisition_v1.csv"
PARSER = DOCS / "edgeiq_racingcom_graphql_parser_output_v2.csv"
OUT = DOCS / "edgeiq_racingcom_fresh_graphql_population_v1.csv"
SUMMARY = DOCS / "edgeiq_racingcom_fresh_graphql_population_summary_v1.json"
REPORT = DOCS / "edgeiq_racingcom_fresh_graphql_population_report_v1.md"


def clean(v: object) -> str:
    return "" if v is None else str(v).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["category", "count", "status", "detail"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    races = read_csv(RACE_DISCOVERY)
    evidence = read_csv(EVIDENCE)
    admission = read_csv(ADMISSION)
    acq = read_csv(ACQ)
    parser = read_csv(PARSER)
    admitted = [r for r in admission if clean(r.get("admission_status")).startswith("ADMITTED")]
    acquired_ids = {clean(r.get("race_id")) for r in acq if clean(r.get("acquisition_status")) == "ACQUIRED_GRAPHQL_RESPONSE"}
    admitted_ids = {clean(r.get("race_id")) for r in admitted}
    new_candidates = sorted(admitted_ids - acquired_ids)
    api_status = "AVAILABLE" if clean(os.environ.get("EDGEIQ_RACINGCOM_WIDGET_API_KEY")) else "MISSING"
    status = "FRESH_GRAPHQL_POPULATION_BLOCKED_BY_CONFIG" if new_candidates and api_status == "MISSING" else "FRESH_GRAPHQL_POPULATION_NO_NEW_NETWORK_WORK"
    rows = [
        {"category": "races_discovered", "count": str(len(races)), "status": "INFO", "detail": "Race Discovery V2 rows."},
        {"category": "graphql_evidence_rows", "count": str(len(evidence)), "status": "INFO", "detail": "Direct GraphQL evidence rows."},
        {"category": "graphql_eligible_races", "count": str(len(admitted_ids)), "status": "INFO", "detail": "Admitted speed races."},
        {"category": "previously_acquired_races", "count": str(len(acquired_ids)), "status": "INFO", "detail": "Valid acquisition ledger races."},
        {"category": "new_acquisition_candidates", "count": str(len(new_candidates)), "status": "BLOCKED_BY_CONFIG" if new_candidates and api_status == "MISSING" else "PASS", "detail": ",".join(new_candidates)},
        {"category": "parser_segment_rows", "count": str(len(parser)), "status": "INFO", "detail": "GraphQL segment rows already parsed."},
        {"category": "api_key_status", "count": "0" if api_status == "MISSING" else "1", "status": api_status, "detail": "EDGEIQ_RACINGCOM_WIDGET_API_KEY value not printed."},
    ]
    write_csv(OUT, rows)
    summary = {
        "decision": status,
        "races_discovered": len(races),
        "graphql_eligible_races": len(admitted_ids),
        "previously_acquired_races": len(acquired_ids),
        "new_acquisition_candidates": len(new_candidates),
        "api_key_status": api_status,
        "production_changed": "NO",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text(f"# Racing.com Fresh GraphQL Population V1\n\nDecision: `{status}`\n\nGraphQL eligible races: `{len(admitted_ids)}`\nPreviously acquired races: `{len(acquired_ids)}`\nNew acquisition candidates: `{len(new_candidates)}`\nAPI key status: `{api_status}`\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
