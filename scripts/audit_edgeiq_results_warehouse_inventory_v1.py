from __future__ import annotations

import csv
from pathlib import Path

from edgeiq_results_common_v1 import DATA, find_inventory_files, first, has_value, parse_date, write_csv


OUTPUT = DATA / "edgeiq_results_warehouse_inventory_v1.csv"
SUMMARY = DATA / "edgeiq_results_warehouse_inventory_summary_v1.csv"


def inspect_file(path: Path) -> dict[str, object]:
    rows = 0
    dates: list[str] = []
    tracks = set()
    races = set()
    runner_rows = 0
    sp_rows = 0
    margin_rows = 0
    time_rows = 0
    sectional_rows = 0
    fieldnames: list[str] = []

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames or []
            for row in reader:
                rows += 1
                date = parse_date(first(row, ["race_date", "meeting_date", "date", "date_k", "run_date"]))
                if date:
                    dates.append(date)
                track = first(row, ["track", "venue_name", "meeting", "track_name"])
                race_no = first(row, ["race_no", "race_number", "race", "race_k"])
                runner = first(row, ["horse", "horseName", "horse_name", "runner", "runner_name"])
                if track:
                    tracks.add(track.upper())
                if date or track or race_no:
                    races.add("|".join([date, track.upper(), race_no]))
                runner_rows += int(has_value(runner))
                sp_rows += int(has_value(first(row, ["sp", "sp_num", "sp_clean", "starting_price", "starting_price_decimal", "fixed_win_dividend", "tab_fixed_win", "bb"])))
                margin_rows += int(has_value(first(row, ["margin", "margin_l", "margin_num", "beaten_margin"])))
                time_rows += int(has_value(first(row, ["winning_time", "raceTime", "race_time", "official_time", "last_600"])))
                sectional_rows += int(has_value(first(row, ["sectional_800", "sectional_600", "sectional_400", "sectional_200", "sectional_finish", "last_600", "last_400", "last_200", "early_speed", "mid_speed", "late_speed", "peak_speed", "avg_speed", "sectional_score"])))
    except Exception as exc:
        return {
            "file_path": str(path.relative_to(DATA.parent.parent) if DATA.parent.parent in path.parents else path),
            "rows": 0,
            "columns": "",
            "min_race_date": "",
            "max_race_date": "",
            "unique_tracks": 0,
            "unique_races": 0,
            "runner_rows": 0,
            "sp_populated_rows": 0,
            "margin_populated_rows": 0,
            "time_populated_rows": 0,
            "sectional_speed_populated_rows": 0,
            "error": str(exc),
        }

    return {
        "file_path": str(path.relative_to(DATA.parent.parent) if DATA.parent.parent in path.parents else path),
        "rows": rows,
        "columns": "|".join(fieldnames),
        "min_race_date": min(dates) if dates else "",
        "max_race_date": max(dates) if dates else "",
        "unique_tracks": len(tracks),
        "unique_races": len(races),
        "runner_rows": runner_rows,
        "sp_populated_rows": sp_rows,
        "margin_populated_rows": margin_rows,
        "time_populated_rows": time_rows,
        "sectional_speed_populated_rows": sectional_rows,
        "error": "",
    }


def main() -> None:
    rows = [inspect_file(path) for path in find_inventory_files()]
    fields = [
        "file_path",
        "rows",
        "columns",
        "min_race_date",
        "max_race_date",
        "unique_tracks",
        "unique_races",
        "runner_rows",
        "sp_populated_rows",
        "margin_populated_rows",
        "time_populated_rows",
        "sectional_speed_populated_rows",
        "error",
    ]
    write_csv(OUTPUT, rows, fields)
    summary = [{
        "files_scanned": len(rows),
        "total_rows": sum(int(row["rows"]) for row in rows),
        "files_with_sp": sum(1 for row in rows if int(row["sp_populated_rows"]) > 0),
        "files_with_sectionals_or_speed": sum(1 for row in rows if int(row["sectional_speed_populated_rows"]) > 0),
        "largest_file": max(rows, key=lambda row: int(row["rows"]))["file_path"] if rows else "",
    }]
    write_csv(SUMMARY, summary, list(summary[0].keys()))
    print(f"Wrote {OUTPUT} ({len(rows)} files)")


if __name__ == "__main__":
    main()
