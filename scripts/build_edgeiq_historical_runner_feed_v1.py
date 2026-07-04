from __future__ import annotations

from collections import defaultdict

from edgeiq_results_common_v1 import DATA, first, normalized_runner, now_iso, numeric_float, parse_date, read_csv, write_csv


OUT = DATA / "edgeiq_historical_runner_feed_v1.csv"
START_DATE = "2000-08-02"
END_DATE = "2026-06-24"


def finish(row: dict[str, str]) -> float | None:
    return numeric_float(first(row, ["position"]))


def main() -> None:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    source = DATA / "edgeiq_results_master_v1.csv"
    for row in read_csv(source) if source.exists() else []:
        race_date = parse_date(first(row, ["race_date"]))
        if not race_date or race_date < START_DATE or race_date > END_DATE:
            continue
        runner = normalized_runner(first(row, ["normalized_runner", "runner"]))
        if runner:
            grouped[runner].append(row)
    output = []
    for runner_key, rows in sorted(grouped.items()):
        rows = sorted(rows, key=lambda row: parse_date(first(row, ["race_date"])), reverse=True)
        latest = rows[0]
        ratings = [numeric_float(first(row, ["epi_post", "speed_rating_raw"])) for row in rows]
        ratings = [value for value in ratings if value is not None]
        wins = sum(1 for row in rows if finish(row) == 1)
        places = sum(1 for row in rows if (finish(row) or 999) <= 3)
        output.append({
            "normalized_runner": runner_key,
            "runner": first(latest, ["runner"]),
            "starts": len(rows),
            "wins": wins,
            "places": places,
            "win_pct": round((wins / len(rows)) * 100, 2) if rows else 0,
            "place_pct": round((places / len(rows)) * 100, 2) if rows else 0,
            "latest_race_date": parse_date(first(latest, ["race_date"])),
            "latest_track": first(latest, ["track"]),
            "latest_race_no": first(latest, ["race_no"]),
            "latest_position": first(latest, ["position"]),
            "average_epi": round(sum(ratings) / len(ratings), 2) if ratings else "",
            "peak_epi": round(max(ratings), 2) if ratings else "",
            "speed_rows": sum(1 for row in rows if first(row, ["speed_available"]) == "YES"),
            "sectional_rows": sum(1 for row in rows if first(row, ["sectional_status"])),
            "built_at": now_iso(),
        })
    fields = ["normalized_runner", "runner", "starts", "wins", "places", "win_pct", "place_pct", "latest_race_date", "latest_track", "latest_race_no", "latest_position", "average_epi", "peak_epi", "speed_rows", "sectional_rows", "built_at"]
    write_csv(OUT, output, fields)
    print(f"Wrote {OUT} ({len(output)} rows)")


if __name__ == "__main__":
    main()
