from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
OUT = DOCS / "edgeiq_performance_fact_dependency_trace_v1.csv"
SUMMARY = DOCS / "edgeiq_performance_fact_dependency_trace_summary_v1.json"
REPORT = DOCS / "edgeiq_performance_fact_dependency_trace_report_v1.md"


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["order", "layer", "builder", "input_paths", "output_paths", "row_grain", "key_contract", "eligibility_or_threshold", "status"])
        writer.writeheader()
        writer.writerows(rows)


def row_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def main() -> int:
    rows = [
        {"order": "1", "layer": "Racing.com production runner warehouse", "builder": "scripts/run_edgeiq_racingcom_ingestion_v2_production.py", "input_paths": "GraphQL cache + historical CSV adapter", "output_paths": "public/data/edgeiq_racingcom_performance_warehouse_v2.csv", "row_grain": "race-runner aggregate", "key_contract": "race_id + horse_key", "eligibility_or_threshold": "runner-only; no segment rows", "status": "PROMOTED"},
        {"order": "2", "layer": "Legacy Racing.com raw speed facts", "builder": "scripts/build_edgeiq_racingcom_runner_speed_warehouse_v1.py", "input_paths": "public/data/edgeiq_racingcom_speed_network_probe_v1.csv", "output_paths": "runner/sectional/split/race speed fact v1", "row_grain": "race, runner, sectional, split", "key_contract": "race_key + runner_id/horse", "eligibility_or_threshold": "source payload availability", "status": "ACTIVE_CONSUMER_PATH"},
        {"order": "3", "layer": "Canonical speed warehouse V2.1", "builder": "scripts/build_edgeiq_racingcom_canonical_speed_warehouse_v2_1.py", "input_paths": "runner/sectional/split/race speed fact v1", "output_paths": "edgeiq_racingcom_canonical_*_v2_1.csv", "row_grain": "race, runner, sectional, split", "key_contract": "race_key, runner_key", "eligibility_or_threshold": "semantics v1.1", "status": "ACTIVE_CONSUMER_PATH"},
        {"order": "4", "layer": "Benchmark observation", "builder": "scripts/build_edgeiq_benchmark_observation_fact_v1.py", "input_paths": "canonical race/runner/sectional/split v2_1", "output_paths": "edgeiq_benchmark_observation_fact_v1.csv", "row_grain": "race benchmark observation", "key_contract": "benchmark_observation_id", "eligibility_or_threshold": "winner timing and coverage", "status": "ACTIVE"},
        {"order": "5", "layer": "Benchmark eligibility", "builder": "scripts/build_edgeiq_benchmark_eligibility_fact_v1.py", "input_paths": "benchmark observation fact", "output_paths": "edgeiq_benchmark_eligibility_fact_v1.csv", "row_grain": "benchmark observation eligibility", "key_contract": "benchmark_observation_id", "eligibility_or_threshold": "governed evidence filters", "status": "ACTIVE"},
        {"order": "6", "layer": "Benchmark accumulation", "builder": "scripts/build_edgeiq_benchmark_accumulation_fact_v1.py", "input_paths": "benchmark observation + eligibility", "output_paths": "edgeiq_benchmark_accumulation_fact_v1.csv and membership", "row_grain": "track-distance-condition benchmark group", "key_contract": "benchmark_group_id", "eligibility_or_threshold": "group observations", "status": "ACTIVE"},
        {"order": "7", "layer": "Standard Time", "builder": "scripts/build_edgeiq_standard_time_engine_v1.py", "input_paths": "benchmark observation + accumulation membership", "output_paths": "edgeiq_standard_time_fact_v1.csv", "row_grain": "benchmark group standard time", "key_contract": "benchmark_group_id", "eligibility_or_threshold": "minimum_required_sample = 20", "status": "ACTIVE_ZERO_ROWS_CURRENTLY"},
    ]
    write_csv(OUT, rows)
    summary = {
        "production_runner_rows": row_count(DATA / "edgeiq_racingcom_performance_warehouse_v2.csv"),
        "canonical_runner_rows": row_count(DATA / "edgeiq_racingcom_canonical_runner_speed_fact_v2_1.csv"),
        "benchmark_observation_rows": row_count(DATA / "edgeiq_benchmark_observation_fact_v1.csv"),
        "standard_time_rows": row_count(DATA / "edgeiq_standard_time_fact_v1.csv"),
        "direct_disconnect": "Production runner warehouse lacks segment and finish-position fields required by the active benchmark observation builder; active path remains canonical speed facts.",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text("# Performance Fact Dependency Trace V1\n\nThe active Standard Time path consumes canonical Racing.com speed fact V2.1 outputs. The promoted 35-column runner warehouse is runner-only and production-compatible, but it is not a complete segment/finish-position fact source for benchmark observation building by itself.\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
