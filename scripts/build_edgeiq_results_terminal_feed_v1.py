from __future__ import annotations

from edgeiq_results_common_v1 import DATA, key_for, read_csv, write_csv


FIELDS = [
    "year",
    "month",
    "race_date",
    "track",
    "meeting_key",
    "race_no",
    "race_key",
    "race_name",
    "distance",
    "class",
    "condition",
    "runner_no",
    "runner",
    "barrier",
    "weight",
    "jockey",
    "trainer",
    "position",
    "margin",
    "beaten_margin",
    "sp",
    "epi_post",
    "speed_available",
    "speed_source_file",
    "speed_source_columns_used",
    "speed_raw",
    "speed_rating_raw",
    "early_raw",
    "mid_raw",
    "late_raw",
    "benchmark_raw",
    "par_raw",
    "standard_raw",
    "last_600_raw",
    "last_400_raw",
    "last_200_raw",
    "speed_rating",
    "early_rating",
    "mid_rating",
    "late_rating",
    "std_800_len",
    "std_600_len",
    "std_400_len",
    "std_200_len",
    "std_finish_len",
    "benchmark_mode",
    "benchmark_time_sec",
    "benchmark_sample_races",
    "furlong_labels",
    "source_confidence",
    "sectional_800",
    "sectional_600",
    "sectional_400",
    "sectional_200",
    "sectional_finish",
    "sectional_status",
    "official_time",
    "last_600",
    "result_status",
]


def standardised_lookup() -> dict[str, dict[str, str]]:
    path = DATA / "edgeiq_standardised_sectionals_v1.csv"
    lookup: dict[str, dict[str, str]] = {}
    if not path.exists():
        return lookup
    for row in read_csv(path):
        key = key_for(row.get("race_date", ""), row.get("track", ""), row.get("race_no", ""), row.get("runner", ""))
        existing = lookup.get(key)
        if existing is None or row.get("benchmark_mode") == "CLASS_BENCHMARK":
            lookup[key] = row
    return lookup


def main() -> None:
    rows = list(read_csv(DATA / "edgeiq_results_master_v1.csv"))
    std = standardised_lookup()
    for row in rows:
        key = key_for(row.get("race_date", ""), row.get("track", ""), row.get("race_no", ""), row.get("runner", ""))
        match = std.get(key)
        if not match:
            continue
        row["speed_rating"] = match.get("speed_rating", "")
        row["early_rating"] = match.get("early_rating", "")
        row["mid_rating"] = match.get("mid_rating", "")
        row["late_rating"] = match.get("late_rating", "")
        row["std_800_len"] = match.get("std_800_len", "")
        row["std_600_len"] = match.get("std_600_len", "")
        row["std_400_len"] = match.get("std_400_len", "")
        row["std_200_len"] = match.get("std_200_len", "")
        row["std_finish_len"] = match.get("std_finish_len", "")
        row["benchmark_mode"] = match.get("benchmark_mode", "")
        row["benchmark_time_sec"] = match.get("benchmark_time_sec", "")
        row["benchmark_sample_races"] = match.get("benchmark_sample_races", "")
        row["furlong_labels"] = match.get("furlong_labels", "")
        row["source_confidence"] = match.get("source_confidence", "")
        if match.get("sectional_status") and row.get("sectional_status") in {"", "MISSING"}:
            row["sectional_status"] = match["sectional_status"]
    rows.sort(key=lambda row: (row["race_date"], row["normalized_track"], int(row["race_no"]) if row["race_no"].isdigit() else 999, int(row["position"]) if row["position"].isdigit() else 999, row["normalized_runner"]))
    write_csv(DATA / "edgeiq_results_terminal_feed_v1.csv", rows, FIELDS)
    summary = [{
        "rows": len(rows),
        "first_date": min((row["race_date"] for row in rows), default=""),
        "last_date": max((row["race_date"] for row in rows), default=""),
        "meetings": len({row["meeting_key"] for row in rows}),
        "races": len({row["race_key"] for row in rows}),
    }]
    write_csv(DATA / "edgeiq_results_terminal_feed_summary_v1.csv", summary, list(summary[0].keys()))
    print(f"Wrote terminal feed ({len(rows)} rows)")


if __name__ == "__main__":
    main()
