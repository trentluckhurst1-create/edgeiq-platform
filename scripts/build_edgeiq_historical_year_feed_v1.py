from __future__ import annotations

from collections import defaultdict

from edgeiq_results_common_v1 import DATA, first, now_iso, parse_date, read_csv, write_csv


OUT = DATA / "edgeiq_historical_year_feed_v1.csv"
START_DATE = "2000-08-02"
END_DATE = "2026-06-24"


def main() -> None:
    rows = read_csv(DATA / "edgeiq_results_master_v1.csv") if (DATA / "edgeiq_results_master_v1.csv").exists() else []
    grouped: dict[str, dict[str, object]] = defaultdict(lambda: {"year": "", "races": set(), "meetings": set(), "runner_rows": 0, "resulted_rows": 0, "speed_rows": 0, "sectional_rows": 0})
    for row in rows:
        race_date = parse_date(first(row, ["race_date"]))
        if not race_date or race_date < START_DATE or race_date > END_DATE:
            continue
        year = race_date[:4]
        bucket = grouped[year]
        bucket["year"] = year
        bucket["races"].add(first(row, ["race_key"]))
        bucket["meetings"].add(first(row, ["meeting_key"]))
        bucket["runner_rows"] += 1
        if first(row, ["result_status"]) == "RESULTED":
            bucket["resulted_rows"] += 1
        if first(row, ["speed_available"]) == "YES":
            bucket["speed_rows"] += 1
        if first(row, ["sectional_status"]):
            bucket["sectional_rows"] += 1
    output = []
    for year, bucket in sorted(grouped.items()):
        output.append({
            "year": year,
            "meetings": len(bucket["meetings"]),
            "races": len(bucket["races"]),
            "runner_rows": bucket["runner_rows"],
            "resulted_rows": bucket["resulted_rows"],
            "speed_rows": bucket["speed_rows"],
            "sectional_rows": bucket["sectional_rows"],
            "built_at": now_iso(),
        })
    write_csv(OUT, output, ["year", "meetings", "races", "runner_rows", "resulted_rows", "speed_rows", "sectional_rows", "built_at"])
    print(f"Wrote {OUT} ({len(output)} rows)")


if __name__ == "__main__":
    main()
