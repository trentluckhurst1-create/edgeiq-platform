from __future__ import annotations

from collections import Counter

from edgeiq_results_common_v1 import DATA, SPEED_RAW_FIELDS, coverage_pct, has_value, read_csv, row_has_speed, write_csv


OUT = DATA / "edgeiq_speed_master_quality_v1.csv"
SUMMARY = DATA / "edgeiq_speed_master_quality_summary_v1.csv"


def main() -> None:
    master = list(read_csv(DATA / "edgeiq_results_master_v1.csv"))
    speed = list(read_csv(DATA / "edgeiq_speed_master_v1.csv")) if (DATA / "edgeiq_speed_master_v1.csv").exists() else []
    retry_summary = next(iter(read_csv(DATA / "edgeiq_sectionals_retry_queue_summary_v1.csv")), {}) if (DATA / "edgeiq_sectionals_retry_queue_summary_v1.csv").exists() else {}

    speed_rows = [row for row in master if row_has_speed(row) or row.get("speed_available") == "YES"]
    resulted_races = {row.get("race_key", "") for row in master if row.get("result_status") == "RESULTED" and row.get("race_key", "")}
    speed_races = {row.get("race_key", "") for row in speed_rows if row.get("race_key", "")}
    resulted_speed_races = speed_races.intersection(resulted_races)
    speed_meetings = {row.get("meeting_key", "") for row in speed_rows if row.get("meeting_key", "")}
    dates = [row.get("race_date", "") for row in speed_rows if row.get("race_date", "")]
    source_counts = Counter(row.get("speed_source_file", "") for row in speed_rows if row.get("speed_source_file", ""))
    field_rows = []
    for field in SPEED_RAW_FIELDS + ["sectional_800", "sectional_600", "sectional_400", "sectional_200", "sectional_finish"]:
        count = sum(1 for row in master if has_value(row.get(field, "")))
        field_rows.append({"metric": field, "rows": count, "coverage_pct": coverage_pct(count, len(master))})
    write_csv(OUT, field_rows, ["metric", "rows", "coverage_pct"])

    summary = {
        "speed_master_rows": len(speed),
        "results_master_rows": len(master),
        "speed_joined_runner_rows": len(speed_rows),
        "speed_joined_runner_coverage_pct": coverage_pct(len(speed_rows), len(master)),
        "speed_race_coverage": len(resulted_speed_races),
        "resulted_races": len(resulted_races),
        "speed_race_coverage_pct": coverage_pct(len(resulted_speed_races), len(resulted_races)),
        "speed_meeting_coverage": len(speed_meetings),
        "first_speed_date": min(dates) if dates else "",
        "last_speed_date": max(dates) if dates else "",
        "source_file_breakdown": ";".join(f"{k}:{v}" for k, v in source_counts.most_common(20)),
        "after_retry_queue_count": retry_summary.get("retry_queue_races", ""),
    }
    write_csv(SUMMARY, [summary], list(summary.keys()))
    print(f"Wrote {SUMMARY}")


if __name__ == "__main__":
    main()
