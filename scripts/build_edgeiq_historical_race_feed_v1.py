from __future__ import annotations

from collections import defaultdict

from edgeiq_results_common_v1 import DATA, first, now_iso, parse_date, read_csv, write_csv, numeric_float


OUT = DATA / "edgeiq_historical_race_feed_v1.csv"
START_DATE = "2000-08-02"
END_DATE = "2026-06-24"


def position(row: dict[str, str]) -> float:
    return numeric_float(first(row, ["position"])) or 9999


def main() -> None:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    source = DATA / "edgeiq_results_master_v1.csv"
    for row in read_csv(source) if source.exists() else []:
        race_date = parse_date(first(row, ["race_date"]))
        if not race_date or race_date < START_DATE or race_date > END_DATE:
            continue
        key = first(row, ["race_key"])
        if key:
            grouped[key].append(row)
    output = []
    for key, rows in sorted(grouped.items()):
        ordered = sorted(rows, key=position)
        winner = ordered[0] if ordered else {}
        output.append({
            "race_key": key,
            "meeting_key": first(winner, ["meeting_key"]),
            "race_date": parse_date(first(winner, ["race_date"])),
            "track": first(winner, ["track"]),
            "race_no": first(winner, ["race_no"]),
            "race_name": first(winner, ["race_name"]),
            "distance": first(winner, ["distance"]),
            "class": first(winner, ["class"]),
            "condition": first(winner, ["condition"]),
            "field_size": len(rows),
            "winner": first(winner, ["runner"]),
            "winner_no": first(winner, ["runner_no"]),
            "winner_sp": first(winner, ["sp", "starting_price"]),
            "official_time": first(winner, ["official_time"]),
            "last_600": first(winner, ["last_600"]),
            "speed_rows": sum(1 for row in rows if first(row, ["speed_available"]) == "YES"),
            "sectional_rows": sum(1 for row in rows if first(row, ["sectional_status"])),
            "built_at": now_iso(),
        })
    fields = ["race_key", "meeting_key", "race_date", "track", "race_no", "race_name", "distance", "class", "condition", "field_size", "winner", "winner_no", "winner_sp", "official_time", "last_600", "speed_rows", "sectional_rows", "built_at"]
    write_csv(OUT, output, fields)
    print(f"Wrote {OUT} ({len(output)} rows)")


if __name__ == "__main__":
    main()
