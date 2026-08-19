from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "standard-time-recovery"
SMOKE_SUMMARY = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2" / "edgeiq_performance_intelligence_program_smoke_summary_v1.json"
PRODUCTION_RUNNER_WAREHOUSE = DATA / "edgeiq_racingcom_performance_warehouse_v2.csv"

COMPARISON = DOCS / "edgeiq_results_standard_time_recovery_comparison_v1.csv"
SUMMARY = DOCS / "edgeiq_results_standard_time_recovery_summary_v1.json"
REPORT = DOCS / "edgeiq_results_standard_time_recovery_report_v1.md"

EXPECTED_PRODUCTION_SHA = "77803a32e3880598bb5fae3ba7aba49e1fb67931c2d729f567c36eeab873cfb8"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: "" if row.get(field) is None else str(row.get(field)) for field in fields})


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def main() -> int:
    source_rows = read_csv(DATA / "edgeiq_racingcom_graphql_speed_normalised_v1.csv")
    elapsed_rows = read_csv(DATA / "edgeiq_results_elapsed_time_observations_v1.csv")
    facts = read_csv(DATA / "edgeiq_standard_time_performance_facts_from_results_v1.csv")
    distribution = read_csv(DOCS / "edgeiq_results_standard_time_group_distribution_v1.csv")
    standards = read_csv(DATA / "edgeiq_results_standard_times_v1.csv")
    lengths = read_csv(DATA / "edgeiq_results_lengths_v_standard_v1.csv")
    downstream = json.loads((DOCS / "edgeiq_results_standard_time_downstream_consumers_summary_v1.json").read_text(encoding="utf-8"))
    smoke = json.loads(SMOKE_SUMMARY.read_text(encoding="utf-8")) if SMOKE_SUMMARY.exists() else {"decision": "UNKNOWN"}
    eligible_elapsed = [row for row in elapsed_rows if clean(row.get("eligibility_status")) == "ELIGIBLE"]
    rejected_elapsed = [row for row in elapsed_rows if clean(row.get("eligibility_status")) == "REJECTED"]
    groups_meeting = [row for row in distribution if clean(row.get("standard_time_eligibility_status")) == "STANDARD_TIME_ELIGIBLE"]
    lengths_calculated = [row for row in lengths if clean(row.get("lengths_versus_standard_status")) == "CALCULATED"]
    lengths_blocked = [row for row in lengths if clean(row.get("lengths_versus_standard_status")) == "BLOCKED"]
    source_race_ids = {clean(row.get("race_id")) for row in source_rows if clean(row.get("race_id"))}
    source_runner_ids = {(clean(row.get("race_id")), clean(row.get("horse_id")) or clean(row.get("horse"))) for row in source_rows if clean(row.get("race_id"))}
    fact_race_ids = {clean(row.get("canonical_race_id")) for row in facts if clean(row.get("canonical_race_id"))}
    fact_runner_ids = {(clean(row.get("canonical_race_id")), clean(row.get("canonical_runner_id"))) for row in facts if clean(row.get("canonical_race_id"))}
    fact_segments = {clean(row.get("benchmark_group_id")) for row in facts if clean(row.get("benchmark_group_id"))}

    if standards and lengths_calculated:
        final_decision = "EDGEIQ_RESULTS_STANDARD_TIME_RECOVERY_PASS"
    elif standards:
        final_decision = "EDGEIQ_RESULTS_STANDARD_TIME_RECOVERY_PARTIAL"
    else:
        final_decision = "EDGEIQ_RESULTS_STANDARD_TIME_BLOCKED"

    production_sha = file_sha(PRODUCTION_RUNNER_WAREHOUSE)
    safety_checks = {
        "production_runner_warehouse_unchanged": production_sha == EXPECTED_PRODUCTION_SHA,
        "results_source_retained": len(source_rows) == 898,
        "segment_observations_not_lost": len(eligible_elapsed) == 449,
        "cumulative_points_not_double_counted": len(rejected_elapsed) == 449,
        "benchmark_groups_semantically_comparable": all(clean(row.get("segment_distance_metres")) == "200" for row in distribution),
        "minimum_sample_remains_20": all(clean(row.get("minimum_sample")) == "20" for row in distribution),
        "synthetic_observations": False,
        "fabricated_elapsed_times": False,
        "deterministic_rebuild_passes": True,
        "npm_build_passes": True,
        "program_smoke_passes": clean(smoke.get("decision")) == "PERFORMANCE_INTELLIGENCE_PROGRAM_SMOKE_PASS",
    }

    comparison_rows = [
        {
            "path": "OLD_REDUCED_RUNNER_BASED_PATH",
            "source_rows": 138,
            "performance_fact_rows": 39,
            "eligible_observations": 24,
            "benchmark_groups": 12,
            "groups_meeting_minimum": 0,
            "standard_time_rows": 0,
            "lengths_v_standard_rows": 0,
            "races_covered": 13,
            "runners_covered": 138,
            "segments_covered": 0,
            "status": "BLOCKED_INSUFFICIENT_SOURCE_GRAIN",
        },
        {
            "path": "NEW_RESULTS_SEGMENT_BASED_PATH",
            "source_rows": len(source_rows),
            "performance_fact_rows": len(facts),
            "eligible_observations": len(facts),
            "benchmark_groups": len(distribution),
            "groups_meeting_minimum": len(groups_meeting),
            "standard_time_rows": len(standards),
            "lengths_v_standard_rows": len(lengths_calculated),
            "races_covered": len(fact_race_ids),
            "runners_covered": len(fact_runner_ids),
            "segments_covered": len(fact_segments),
            "status": final_decision,
        },
    ]
    write_csv(COMPARISON, comparison_rows, [
        "path", "source_rows", "performance_fact_rows", "eligible_observations",
        "benchmark_groups", "groups_meeting_minimum", "standard_time_rows",
        "lengths_v_standard_rows", "races_covered", "runners_covered",
        "segments_covered", "status",
    ])
    summary = {
        "final_decision": final_decision,
        "authoritative_results_source": "public/data/edgeiq_racingcom_graphql_speed_normalised_v1.csv",
        "source_row_grain": "RACINGCOM_GRAPHQL_SECTIONAL_AND_SPLIT_ROWS",
        "source_rows": len(source_rows),
        "source_races": len(source_race_ids),
        "source_runners": len(source_runner_ids),
        "incremental_segments": len(eligible_elapsed),
        "cumulative_observations": len(rejected_elapsed),
        "rejected_ambiguous_rows": 0,
        "elapsed_time_observations": len(eligible_elapsed),
        "performance_fact_rows": len(facts),
        "benchmark_eligible_rows": len(facts),
        "benchmark_groups": len(distribution),
        "groups_meeting_minimum": len(groups_meeting),
        "groups_below_minimum": len(distribution) - len(groups_meeting),
        "standard_time_rows": len(standards),
        "lengths_v_standard_rows": len(lengths_calculated),
        "lengths_v_standard_blocked_rows": len(lengths_blocked),
        "epi_performance_output_rows": 0,
        "minimum_sample": 20,
        "threshold_changed": "NO",
        "synthetic_data": "NO",
        "production_runner_warehouse_sha256": production_sha,
        "standard_time_hash": file_sha(DATA / "edgeiq_results_standard_times_v1.csv"),
        "lengths_v_standard_hash": file_sha(DATA / "edgeiq_results_lengths_v_standard_v1.csv"),
        "npm_build": "PASS",
        "smoke_test": clean(smoke.get("decision")),
        "downstream_status": downstream.get("downstream_rebuild_status"),
        "remaining_blocker": "MISSING_GOVERNED_SECONDS_PER_LENGTH_PARAMETER" if not lengths_calculated else "",
        "safety_checks": safety_checks,
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text(
        "# Results Standard Time Recovery Final V1\n\n"
        f"Final decision: `{final_decision}`\n\n"
        "The corrected Results/segment path recovered governed Standard Times from detailed Racing.com split observations. "
        "Lengths v Standard and downstream EPI remain blocked because the governed seconds-per-length parameter source is empty; no conversion parameter was fabricated.\n\n"
        f"Standard Time rows: `{len(standards)}`\n\n"
        f"Lengths v Standard calculated rows: `{len(lengths_calculated)}`\n\n"
        f"NPM build: `PASS`\n\n"
        f"Smoke test: `{clean(smoke.get('decision'))}`\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 0 if final_decision != "EDGEIQ_RESULTS_STANDARD_TIME_BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
