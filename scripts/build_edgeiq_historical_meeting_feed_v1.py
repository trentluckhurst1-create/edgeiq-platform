from __future__ import annotations

from collections import defaultdict

from edgeiq_results_common_v1 import DATA, first, now_iso, parse_date, read_csv, write_csv


OUT = DATA / "edgeiq_historical_meeting_feed_v1.csv"
START_DATE = "2000-08-02"
END_DATE = "2026-06-24"


def main() -> None:
    grouped: dict[str, dict[str, object]] = defaultdict(lambda: {"race_date": "", "track": "", "races": set(), "runner_rows": 0, "resulted_rows": 0, "speed_rows": 0})
    source = DATA / "edgeiq_results_master_v1.csv"
    for row in read_csv(source) if source.exists() else []:
        race_date = parse_date(first(row, ["race_date"]))
        if not race_date or race_date < START_DATE or race_date > END_DATE:
            continue
        meeting_key = first(row, ["meeting_key"])
        if not meeting_key:
            continue
        bucket = grouped[meeting_key]
        bucket["race_date"] = race_date
        bucket["track"] = first(row, ["track"])
        bucket["races"].add(first(row, ["race_key"]))
        bucket["runner_rows"] += 1
        if first(row, ["result_status"]) == "RESULTED":
            bucket["resulted_rows"] += 1
        if first(row, ["speed_available"]) == "YES":
            bucket["speed_rows"] += 1
    output = [{
        "meeting_key": key,
        "race_date": bucket["race_date"],
        "track": bucket["track"],
        "races": len(bucket["races"]),
        "runner_rows": bucket["runner_rows"],
        "resulted_rows": bucket["resulted_rows"],
        "speed_rows": bucket["speed_rows"],
        "built_at": now_iso(),
    } for key, bucket in sorted(grouped.items())]
    write_csv(OUT, output, ["meeting_key", "race_date", "track", "races", "runner_rows", "resulted_rows", "speed_rows", "built_at"])
    print(f"Wrote {OUT} ({len(output)} rows)")


if __name__ == "__main__":
    main()
