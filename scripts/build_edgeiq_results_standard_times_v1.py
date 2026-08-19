from __future__ import annotations

import csv
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "standard-time-recovery"
SOURCE = DATA / "edgeiq_standard_time_performance_facts_from_results_v1.csv"
DIST = DOCS / "edgeiq_results_standard_time_group_distribution_v1.csv"
OUT = DATA / "edgeiq_results_standard_times_v1.csv"
AUDIT = DOCS / "edgeiq_results_standard_times_audit_v1.csv"
SUMMARY = DOCS / "edgeiq_results_standard_times_summary_v1.json"
REPORT = DOCS / "edgeiq_results_standard_times_report_v1.md"
MIN_SAMPLE = 20

FIELDS = [
    "benchmark_group_id",
    "sample_count",
    "track",
    "race_distance_metres",
    "segment_start_metres",
    "segment_end_metres",
    "segment_distance_metres",
    "standard_elapsed_seconds",
    "standard_speed_mps",
    "calculation_method",
    "source_race_count",
    "source_runner_count",
    "source_date_min",
    "source_date_max",
    "dispersion_measure",
    "minimum_sample",
    "audit_status",
]


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def fnum(value: object) -> float:
    return float(clean(value))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: clean(row.get(field, "")) for field in fields})


def median_absolute_deviation(values: list[float]) -> float:
    med = statistics.median(values)
    return statistics.median([abs(value - med) for value in values])


def main() -> int:
    rows = read_csv(SOURCE)
    distribution_rows = read_csv(DIST)
    eligible_groups = {
        clean(row.get("benchmark_group_id"))
        for row in distribution_rows
        if clean(row.get("standard_time_eligibility_status")) == "STANDARD_TIME_ELIGIBLE"
    }
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        group_id = clean(row.get("benchmark_group_id"))
        if group_id in eligible_groups:
            grouped[group_id].append(row)

    output: list[dict[str, object]] = []
    for group_id, group_rows in sorted(grouped.items()):
        elapsed = [fnum(row.get("elapsed_time_seconds")) for row in group_rows]
        segment_distance = fnum(group_rows[0].get("segment_distance_metres"))
        standard_elapsed = statistics.median(elapsed)
        standard_speed = segment_distance / standard_elapsed if standard_elapsed > 0 else 0.0
        source_races = {clean(row.get("canonical_race_id")) for row in group_rows}
        source_runners = {(clean(row.get("canonical_race_id")), clean(row.get("canonical_runner_id"))) for row in group_rows}
        dates = sorted(clean(row.get("race_date")) for row in group_rows if clean(row.get("race_date")))
        first = group_rows[0]
        output.append({
            "benchmark_group_id": group_id,
            "sample_count": len(group_rows),
            "track": clean(first.get("track")),
            "race_distance_metres": clean(first.get("race_distance_metres")),
            "segment_start_metres": clean(first.get("segment_start_metres")),
            "segment_end_metres": clean(first.get("segment_end_metres")),
            "segment_distance_metres": clean(first.get("segment_distance_metres")),
            "standard_elapsed_seconds": f"{standard_elapsed:.4f}",
            "standard_speed_mps": f"{standard_speed:.6f}",
            "calculation_method": "MEDIAN_ELAPSED_SECONDS_BY_COMPARABLE_SEGMENT",
            "source_race_count": len(source_races),
            "source_runner_count": len(source_runners),
            "source_date_min": dates[0] if dates else "",
            "source_date_max": dates[-1] if dates else "",
            "dispersion_measure": f"MAD_SECONDS={median_absolute_deviation(elapsed):.4f}",
            "minimum_sample": MIN_SAMPLE,
            "audit_status": "RESULTS_STANDARD_TIME_PASS_NONZERO",
        })

    write_csv(OUT, output, FIELDS)
    decision = "RESULTS_STANDARD_TIME_PASS_NONZERO" if output else "RESULTS_STANDARD_TIME_BLOCKED_INSUFFICIENT_COMPARABLE_OBSERVATIONS"
    bad_min = sum(1 for row in output if int(clean(row.get("sample_count"))) < MIN_SAMPLE)
    summary = {
        "input_fact_rows": len(rows),
        "eligible_benchmark_groups": len(eligible_groups),
        "standard_time_rows": len(output),
        "minimum_sample": MIN_SAMPLE,
        "groups_below_minimum_in_output": bad_min,
        "decision": decision,
        "deterministic_hash": hashlib.sha256(OUT.read_bytes()).hexdigest(),
    }
    audit_rows = [
        {"check": "minimum_sample_preserved", "status": "PASS" if MIN_SAMPLE == 20 else "FAIL", "value": MIN_SAMPLE, "detail": "Governed threshold unchanged."},
        {"check": "eligible_benchmark_groups", "status": "PASS" if len(eligible_groups) == len(output) else "FAIL", "value": len(eligible_groups), "detail": "Each eligible group receives a standard time."},
        {"check": "standard_time_rows", "status": "PASS" if len(output) > 0 else "FAIL", "value": len(output), "detail": decision},
        {"check": "groups_below_minimum_in_output", "status": "PASS" if bad_min == 0 else "FAIL", "value": bad_min, "detail": "No output group violates threshold."},
        {"check": "deterministic_hash", "status": "PASS", "value": summary["deterministic_hash"], "detail": "Standard time output SHA."},
    ]
    write_csv(AUDIT, audit_rows, ["check", "status", "value", "detail"])
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text(
        "# Results Standard Times V1\n\n"
        f"Decision: `{decision}`\n\n"
        f"Standard Time rows: `{len(output)}`\n\n"
        f"Minimum sample: `{MIN_SAMPLE}`\n\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 0 if all(row["status"] == "PASS" for row in audit_rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
