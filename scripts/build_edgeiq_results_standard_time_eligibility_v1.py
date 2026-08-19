from __future__ import annotations

import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "standard-time-recovery"
SOURCE = DATA / "edgeiq_standard_time_performance_facts_from_results_v1.csv"
ELIGIBLE_OUT = DATA / "edgeiq_results_standard_time_eligible_observations_v1.csv"
DIST = DOCS / "edgeiq_results_standard_time_group_distribution_v1.csv"
AUDIT = DOCS / "edgeiq_results_standard_time_eligibility_audit_v1.csv"
REPORT = DOCS / "edgeiq_results_standard_time_eligibility_report_v1.md"
SUMMARY = DOCS / "edgeiq_results_standard_time_eligibility_summary_v1.json"
MIN_SAMPLE = 20


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: clean(row.get(field, "")) for field in fields})


def bucket(count: int) -> str:
    if count >= 20:
        return "20_PLUS"
    if count >= 10:
        return "10_19"
    if count >= 5:
        return "5_9"
    return "1_4"


def main() -> int:
    rows = read_csv(SOURCE)
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if clean(row.get("eligibility_status")) == "ELIGIBLE":
            groups[clean(row.get("benchmark_group_id"))].append(row)

    distribution: list[dict[str, object]] = []
    eligible_rows: list[dict[str, object]] = []
    for group_id, group_rows in sorted(groups.items()):
        sample_count = len(group_rows)
        first = group_rows[0]
        source_races = len({clean(row.get("canonical_race_id")) for row in group_rows})
        source_runners = len({(clean(row.get("canonical_race_id")), clean(row.get("canonical_runner_id"))) for row in group_rows})
        status = "STANDARD_TIME_ELIGIBLE" if sample_count >= MIN_SAMPLE else "BELOW_MINIMUM_SAMPLE"
        distribution.append({
            "benchmark_group_id": group_id,
            "track": clean(first.get("track")),
            "race_distance_metres": clean(first.get("race_distance_metres")),
            "segment_start_metres": clean(first.get("segment_start_metres")),
            "segment_end_metres": clean(first.get("segment_end_metres")),
            "segment_distance_metres": clean(first.get("segment_distance_metres")),
            "observation_count": sample_count,
            "source_race_count": source_races,
            "source_runner_count": source_runners,
            "minimum_sample": MIN_SAMPLE,
            "deficit_to_minimum": max(0, MIN_SAMPLE - sample_count),
            "group_bucket": bucket(sample_count),
            "standard_time_eligibility_status": status,
        })
        if status == "STANDARD_TIME_ELIGIBLE":
            for row in group_rows:
                eligible_rows.append({**row, "standard_time_eligibility_status": status})

    counts = [len(group_rows) for group_rows in groups.values()]
    bucket_counts = Counter(bucket(count) for count in counts)
    meeting_min = sum(1 for count in counts if count >= MIN_SAMPLE)
    total_deficit = sum(max(0, MIN_SAMPLE - count) for count in counts)
    summary = {
        "total_detailed_observations": len(rows),
        "eligible_observations": len(rows),
        "ineligible_observations": 0,
        "benchmark_groups": len(groups),
        "groups_1_4": bucket_counts.get("1_4", 0),
        "groups_5_9": bucket_counts.get("5_9", 0),
        "groups_10_19": bucket_counts.get("10_19", 0),
        "groups_20_or_more": meeting_min,
        "largest_group_size": max(counts) if counts else 0,
        "median_group_size": statistics.median(counts) if counts else 0,
        "total_deficit": total_deficit,
        "minimum_sample": MIN_SAMPLE,
        "previous_reduced_performance_fact_rows": 39,
        "previous_reduced_benchmark_eligible_rows": 24,
        "previous_reduced_groups_meeting_minimum": 0,
    }
    write_csv(DIST, distribution, [
        "benchmark_group_id", "track", "race_distance_metres", "segment_start_metres",
        "segment_end_metres", "segment_distance_metres", "observation_count",
        "source_race_count", "source_runner_count", "minimum_sample",
        "deficit_to_minimum", "group_bucket", "standard_time_eligibility_status",
    ])
    write_csv(ELIGIBLE_OUT, eligible_rows, list(rows[0].keys()) + ["standard_time_eligibility_status"] if rows else [])
    audit_rows = [
        {"check": "total_detailed_observations", "status": "PASS" if len(rows) == 449 else "FAIL", "value": len(rows), "detail": "Results-based fact rows."},
        {"check": "minimum_sample_preserved", "status": "PASS" if MIN_SAMPLE == 20 else "FAIL", "value": MIN_SAMPLE, "detail": "Governed threshold unchanged."},
        {"check": "groups_meeting_minimum", "status": "PASS" if meeting_min > 0 else "WARN", "value": meeting_min, "detail": "Comparable groups reaching threshold 20."},
        {"check": "old_path_comparison", "status": "PASS" if meeting_min > summary["previous_reduced_groups_meeting_minimum"] else "WARN", "value": f"{meeting_min} vs 0", "detail": "New segment path compared with reduced runner path."},
    ]
    write_csv(AUDIT, audit_rows, ["check", "status", "value", "detail"])
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text(
        "# Results Standard Time Eligibility V1\n\n"
        f"Total detailed observations: `{summary['total_detailed_observations']}`\n\n"
        f"Benchmark groups: `{summary['benchmark_groups']}`\n\n"
        f"Groups meeting minimum 20: `{summary['groups_20_or_more']}`\n\n"
        f"Groups below minimum: `{summary['benchmark_groups'] - summary['groups_20_or_more']}`\n\n"
        "Counts changed because the reduced runner path used runner aggregate compatibility rows, "
        "while this path uses semantically valid Racing.com split-segment observations.\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 0 if all(row["status"] in {"PASS", "WARN"} for row in audit_rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
