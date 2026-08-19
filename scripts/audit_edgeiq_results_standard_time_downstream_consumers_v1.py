from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "standard-time-recovery"
OUT = DOCS / "edgeiq_results_standard_time_downstream_consumers_v1.csv"
SUMMARY = DOCS / "edgeiq_results_standard_time_downstream_consumers_summary_v1.json"
REPORT = DOCS / "edgeiq_results_standard_time_downstream_consumers_report_v1.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def row_count(path: Path) -> int:
    return len(read_csv(path))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: "" if row.get(field) is None else str(row.get(field)) for field in fields})


def main() -> int:
    result_st = DATA / "edgeiq_results_standard_times_v1.csv"
    result_lvs = DATA / "edgeiq_results_lengths_v_standard_v1.csv"
    canonical_st = DATA / "edgeiq_standard_time_fact_v1.csv"
    canonical_lvs = DATA / "edgeiq_lengths_versus_standard_fact_v1.csv"
    result_st_rows = row_count(result_st)
    result_lvs_rows = [row for row in read_csv(result_lvs) if row.get("lengths_versus_standard_status") == "CALCULATED"]
    result_lvs_blocked = [row for row in read_csv(result_lvs) if row.get("lengths_versus_standard_status") == "BLOCKED"]
    consumers = [
        {
            "consumer": "Standard Time candidate warehouse",
            "input": "edgeiq_standard_time_performance_facts_from_results_v1.csv",
            "output": "edgeiq_results_standard_times_v1.csv",
            "row_count": result_st_rows,
            "status": "READY_BACKEND_CANDIDATE" if result_st_rows else "BLOCKED",
            "detail": "Results/segment path produces governed Standard Times.",
        },
        {
            "consumer": "Lengths v Standard candidate warehouse",
            "input": "edgeiq_results_standard_times_v1.csv + edgeiq_length_conversion_parameter_fact_v1.csv",
            "output": "edgeiq_results_lengths_v_standard_v1.csv",
            "row_count": len(result_lvs_rows),
            "status": "BLOCKED_MISSING_GOVERNED_CONVERSION_PARAMETER" if not result_lvs_rows else "READY_BACKEND_CANDIDATE",
            "detail": f"Blocked rows with standard-time matches: {len(result_lvs_blocked)}.",
        },
        {
            "consumer": "Canonical production Standard Time contract",
            "input": "edgeiq_benchmark_accumulation_fact_v1.csv",
            "output": "edgeiq_standard_time_fact_v1.csv",
            "row_count": row_count(canonical_st),
            "status": "UNCHANGED_PRODUCTION_COMPATIBILITY_PATH",
            "detail": "Not overwritten by candidate recovery.",
        },
        {
            "consumer": "Canonical production Lengths v Standard contract",
            "input": "edgeiq_race_time_delta_versus_standard_fact_v1.csv + parameter fact",
            "output": "edgeiq_lengths_versus_standard_fact_v1.csv",
            "row_count": row_count(canonical_lvs),
            "status": "UNCHANGED_PRODUCTION_COMPATIBILITY_PATH",
            "detail": "Not overwritten by candidate recovery.",
        },
        {
            "consumer": "EPI / sectional performance intelligence",
            "input": "Lengths v Standard",
            "output": "dependent performance intelligence outputs",
            "row_count": 0,
            "status": "NOT_REBUILT_LENGTHS_PARAMETER_BLOCKED",
            "detail": "No honest EPI score rebuild until seconds-per-length parameter exists.",
        },
    ]
    write_csv(OUT, consumers, ["consumer", "input", "output", "row_count", "status", "detail"])
    summary = {
        "results_standard_time_rows": result_st_rows,
        "results_lengths_v_standard_calculated_rows": len(result_lvs_rows),
        "results_lengths_v_standard_blocked_rows": len(result_lvs_blocked),
        "canonical_standard_time_rows_preserved": row_count(canonical_st),
        "canonical_lengths_v_standard_rows_preserved": row_count(canonical_lvs),
        "downstream_rebuild_status": "PARTIAL_STANDARD_TIME_READY_LENGTHS_BLOCKED",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text(
        "# Results Standard Time Downstream Consumers V1\n\n"
        f"Results Standard Time rows: `{summary['results_standard_time_rows']}`\n\n"
        f"Lengths v Standard calculated rows: `{summary['results_lengths_v_standard_calculated_rows']}`\n\n"
        f"Lengths v Standard blocked rows: `{summary['results_lengths_v_standard_blocked_rows']}`\n\n"
        "The production compatibility contracts were preserved. Downstream EPI is not rebuilt because the governed conversion parameter is unavailable.\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
