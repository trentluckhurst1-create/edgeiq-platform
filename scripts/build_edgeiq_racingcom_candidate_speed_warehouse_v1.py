from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DOCS = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
PUBLIC = ROOT / "public" / "data"
CANONICAL = DOCS / "edgeiq_racingcom_canonical_speed_contract_v1.csv"
CANDIDATE = PUBLIC / "edgeiq_racingcom_performance_warehouse_v2_GRAPHQL_CANDIDATE.csv"
DOCS_CANDIDATE = DOCS / "edgeiq_racingcom_performance_warehouse_v2_graphql_candidate.csv"
AUDIT_OUT = DOCS / "edgeiq_racingcom_performance_warehouse_v2_graphql_candidate_audit.csv"
SUMMARY_OUT = DOCS / "edgeiq_racingcom_performance_warehouse_v2_graphql_candidate_summary.json"
REPORT_OUT = DOCS / "edgeiq_racingcom_performance_warehouse_v2_graphql_candidate_report.md"

BUILT_UTC = datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"", "NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: clean(row.get(column, "")) for column in columns})


def main() -> int:
    rows, columns = read_csv(CANONICAL)
    candidate_rows = []
    for row in rows:
        candidate_rows.append({**row, "warehouse_status": "GRAPHQL_CANDIDATE_NOT_MIGRATED", "candidate_built_utc": BUILT_UTC})
    out_columns = columns + ["warehouse_status", "candidate_built_utc"]
    write_csv(CANDIDATE, candidate_rows, out_columns)
    write_csv(DOCS_CANDIDATE, candidate_rows, out_columns)
    production_path = PUBLIC / "edgeiq_racingcom_performance_warehouse_v2.csv"
    audit = [
        ("candidate_rows_gt_zero", len(candidate_rows) > 0, len(candidate_rows), "Candidate warehouse rows emitted."),
        ("candidate_preserves_canonical_rows", len(candidate_rows) == len(rows), len(candidate_rows), "Candidate row count equals canonical contract."),
        ("production_warehouse_not_overwritten", production_path != CANDIDATE, str(CANDIDATE.name), "Candidate path is separate from production warehouse path."),
        ("graphql_rows_present", sum(1 for row in candidate_rows if row.get("source_type") == "RACINGCOM_GRAPHQL_GETRACEFORM") == 898, sum(1 for row in candidate_rows if row.get("source_type") == "RACINGCOM_GRAPHQL_GETRACEFORM"), "GraphQL rows retained."),
        ("candidate_status_explicit", all(row["warehouse_status"] == "GRAPHQL_CANDIDATE_NOT_MIGRATED" for row in candidate_rows), sum(1 for row in candidate_rows if row["warehouse_status"] == "GRAPHQL_CANDIDATE_NOT_MIGRATED"), "Rows clearly marked candidate only."),
    ]
    audit_rows = [{"check": name, "status": "PASS" if passed else "FAIL", "count": count, "detail": detail} for name, passed, count, detail in audit]
    hard_pass = all(row["status"] == "PASS" for row in audit_rows)
    summary = {
        "built_utc": BUILT_UTC,
        "status": "RACINGCOM_GRAPHQL_CANDIDATE_WAREHOUSE_V1_PASS" if hard_pass else "RACINGCOM_GRAPHQL_CANDIDATE_WAREHOUSE_V1_REVIEW_REQUIRED",
        "candidate_rows": len(candidate_rows),
        "graphql_rows": sum(1 for row in candidate_rows if row.get("source_type") == "RACINGCOM_GRAPHQL_GETRACEFORM"),
        "csv_rows": sum(1 for row in candidate_rows if row.get("fact_grain") == "RUNNER_AGGREGATE"),
        "candidate_public_path": str(CANDIDATE.relative_to(ROOT)),
        "production_changed": "NO",
        "ui_changed": "NO",
    }
    write_csv(AUDIT_OUT, audit_rows, ["check", "status", "count", "detail"])
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    REPORT_OUT.write_text(
        "\n".join(
            [
                "# Racing.com GraphQL Candidate Warehouse V1",
                "",
                f"Built UTC: `{BUILT_UTC}`",
                f"Status: `{summary['status']}`",
                "",
                "## Counts",
                f"- Candidate rows: `{summary['candidate_rows']}`",
                f"- GraphQL rows: `{summary['graphql_rows']}`",
                f"- CSV aggregate rows: `{summary['csv_rows']}`",
                "",
                "## Promotion",
                "",
                "Candidate warehouse only. Production warehouse was not overwritten.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0 if hard_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
