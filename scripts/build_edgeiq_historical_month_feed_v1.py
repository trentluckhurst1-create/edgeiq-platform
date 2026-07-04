from __future__ import annotations

from collections import defaultdict

from edgeiq_results_common_v1 import DATA, first, month_name, now_iso, parse_date, read_csv, write_csv


OUT = DATA / "edgeiq_historical_month_feed_v1.csv"
START_DATE = "2000-08-02"
END_DATE = "2026-06-24"


def main() -> None:
    grouped: dict[tuple[str, str], dict[str, object]] = defaultdict(lambda: {"races": set(), "meetings": set(), "runner_rows": 0, "resulted_rows": 0, "speed_rows": 0})
    source = DATA / "edgeiq_results_master_v1.csv"
    for row in read_csv(source) if source.exists() else []:
        race_date = parse_date(first(row, ["race_date"]))
        if not race_date or race_date < START_DATE or race_date > END_DATE:
            continue
        key = (race_date[:4], race_date[5:7])
        bucket = grouped[key]
        bucket["races"].add(first(row, ["race_key"]))
        bucket["meetings"].add(first(row, ["meeting_key"]))
        bucket["runner_rows"] += 1
        if first(row, ["result_status"]) == "RESULTED":
            bucket["resulted_rows"] += 1
        if first(row, ["speed_available"]) == "YES":
            bucket["speed_rows"] += 1
    output = [{
        "year": year,
        "month": month,
        "month_name": month_name(month),
        "meetings": len(bucket["meetings"]),
        "races": len(bucket["races"]),
        "runner_rows": bucket["runner_rows"],
        "resulted_rows": bucket["resulted_rows"],
        "speed_rows": bucket["speed_rows"],
        "built_at": now_iso(),
    } for (year, month), bucket in sorted(grouped.items())]
    write_csv(OUT, output, ["year", "month", "month_name", "meetings", "races", "runner_rows", "resulted_rows", "speed_rows", "built_at"])
    print(f"Wrote {OUT} ({len(output)} rows)")


if __name__ == "__main__":
    main()
