from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from edgeiq_results_common_v1 import DATA, first, has_value, meeting_key_for, normalized_runner, normalized_track, now_iso, normalize_race_no, parse_date, read_csv, race_key_for, write_csv


OUT = DATA / "edgeiq_terminal_data_integrity_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_terminal_data_integrity_summary_v1.csv"


def path(name: str) -> Path:
    return DATA / name


def load_rows(name: str) -> list[dict[str, str]]:
    p = path(name)
    return list(read_csv(p)) if p.exists() else []


def race_key(row: dict[str, str]) -> str:
    date = parse_date(first(row, ["race_date", "meeting_date", "date"]))
    track = first(row, ["track", "meeting", "meeting_name"])
    race_no = first(row, ["race_no", "race", "race_number"])
    explicit = first(row, ["race_key"])
    return race_key_for(date, track, race_no) if date and track and race_no else explicit


def runner_key(row: dict[str, str]) -> str:
    return normalized_runner(first(row, ["horse", "runner", "runner_name", "normalized_runner", "horse_key"]))


def count_missing(rows: list[dict[str, str]], keys: list[str]) -> int:
    return sum(1 for row in rows if not has_value(first(row, keys)))


def index_by_race(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = race_key(row)
        if key:
            out[key].append(row)
    return out


def main() -> None:
    universe = load_rows("edgeiq_vic_three_day_meeting_universe.csv")
    runner_board = load_rows("edgeiq_live_runner_board_governed_v1.csv")
    runner_intel = load_rows("edgeiq_runner_intelligence_v1.csv")
    bet_quality = load_rows("edgeiq_live_bet_quality_v1_1.csv")
    heatmap = load_rows("edgeiq_ratings_intelligence_heatmap_v1.csv")
    form_rows = load_rows("runner_form_history.csv")
    map_rows = load_rows("edgeiq_map_enrichment_feed_v3.csv")
    lab_rows = load_rows("edgeiq_live_nexus_contextual_feed_v2_1.csv") or load_rows("edgeiq_live_nexus_contextual_feed_v2.csv")
    results = load_rows("edgeiq_results_master_v1.csv")
    speed = load_rows("edgeiq_speed_master_v1.csv")
    sectionals = load_rows("edgeiq_form_sectional_terminal_feed_v1.csv")
    gear = load_rows("edgeiq_gear_terminal_feed_v1.csv")

    indexes = {
        "runner_board": index_by_race(runner_board),
        "intelligence_board": index_by_race(runner_intel),
        "market_board": index_by_race(bet_quality),
        "performance": index_by_race(heatmap),
        "form": index_by_race(form_rows),
        "map": index_by_race(map_rows),
        "lab": index_by_race(lab_rows),
        "results": index_by_race(results),
        "speed": index_by_race(speed),
        "sectionals": index_by_race(sectionals),
        "gear": index_by_race(gear),
    }

    race_rows = {}
    for row in universe:
        key = race_key(row)
        if key:
            race_rows.setdefault(key, row)

    output: list[dict[str, object]] = []
    for key, race in sorted(race_rows.items()):
        board = indexes["runner_board"].get(key, [])
        runner_counts = Counter(runner_key(row) for row in board if runner_key(row))
        duplicate_runners = sum(1 for count in runner_counts.values() if count > 1)
        expected_field_size = first(race, ["field_size", "runners", "runner_count", "field"], "")
        expected_n = int(float(expected_field_size)) if str(expected_field_size).replace(".", "", 1).isdigit() else 0
        result_rows = indexes["results"].get(key, [])
        sectional_rows = indexes["sectionals"].get(key, [])
        gear_rows = indexes["gear"].get(key, [])
        speed_rows = indexes["speed"].get(key, [])
        row = {
            "race_key": key,
            "meeting_key": first(race, ["meeting_key"]) or meeting_key_for(parse_date(first(race, ["race_date", "meeting_date"])), first(race, ["track"])),
            "race_date": parse_date(first(race, ["race_date", "meeting_date"])),
            "day_bucket": first(race, ["day_bucket"]),
            "track": first(race, ["track"]),
            "race_no": normalize_race_no(first(race, ["race_no"])),
            "field_expected": expected_n or "",
            "runner_rows": len(board),
            "duplicates": duplicate_runners,
            "missing_runners": max(0, expected_n - len(board)) if expected_n else "",
            "missing_prices": count_missing(board, ["live_price", "market_price", "fixed_win", "ui_price", "tab_fixed_win"]),
            "missing_ratings": count_missing(board, ["projected_rating_v5_2", "projected_rating_V6_1_RESEARCH", "epi", "runner_rating"]),
            "missing_jockeys": count_missing(board, ["jockey", "rider"]),
            "missing_trainers": count_missing(board, ["trainer"]),
            "missing_barrier": count_missing(board, ["barrier", "draw"]),
            "missing_saddlecloth": count_missing(board, ["saddlecloth", "horse_no", "runner_no", "number"]),
            "missing_sp": count_missing(result_rows, ["sp", "starting_price"]) if result_rows else len(board),
            "missing_gear": 0 if gear_rows else len(board),
            "missing_sectionals": 0 if sectional_rows else len(board),
            "missing_speed_data": 0 if speed_rows else len(board),
            "missing_results": 0 if result_rows else len(board),
        }
        for feed_name, feed_index in indexes.items():
            row[f"{feed_name}_rows"] = len(feed_index.get(key, []))
        issue_fields = [
            "duplicates",
            "missing_runners",
            "missing_prices",
            "missing_ratings",
            "missing_jockeys",
            "missing_trainers",
            "missing_barrier",
            "missing_saddlecloth",
            "missing_gear",
            "missing_sectionals",
            "missing_speed_data",
            "missing_results",
        ]
        issue_count = sum(int(row[field] or 0) for field in issue_fields)
        row["status"] = "OK" if issue_count == 0 else "CHECK"
        output.append(row)

    fields = list(output[0].keys()) if output else ["status"]
    write_csv(OUT, output, fields)

    total = len(output)
    summary = {
        "races_audited": total,
        "ok_races": sum(1 for row in output if row["status"] == "OK"),
        "check_races": sum(1 for row in output if row["status"] != "OK"),
        "races_with_runner_rows": sum(1 for row in output if int(row["runner_rows"] or 0) > 0),
        "total_runner_rows": sum(int(row["runner_rows"] or 0) for row in output),
        "total_duplicate_runners": sum(int(row["duplicates"] or 0) for row in output),
        "total_missing_prices": sum(int(row["missing_prices"] or 0) for row in output),
        "total_missing_ratings": sum(int(row["missing_ratings"] or 0) for row in output),
        "total_missing_jockeys": sum(int(row["missing_jockeys"] or 0) for row in output),
        "total_missing_trainers": sum(int(row["missing_trainers"] or 0) for row in output),
        "total_missing_barriers": sum(int(row["missing_barrier"] or 0) for row in output),
        "total_missing_saddlecloth": sum(int(row["missing_saddlecloth"] or 0) for row in output),
        "built_at": now_iso(),
    }
    write_csv(SUMMARY_OUT, [summary], list(summary.keys()))
    print(f"Wrote {OUT} ({len(output)} rows)")
    print(f"Wrote {SUMMARY_OUT}")


if __name__ == "__main__":
    main()
