from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from edgeiq_results_common_v1 import DATA, first, has_value, normalized_track, now_iso, parse_date, read_csv, race_key_for, write_csv


OUT = DATA / "edgeiq_flemington_readiness_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_flemington_readiness_summary_v1.csv"
TODAY = date(2026, 7, 3)
TOMORROW = (TODAY + timedelta(days=1)).isoformat()


def load(name: str) -> list[dict[str, str]]:
    path = DATA / name
    return list(read_csv(path)) if path.exists() else []


def race_key(row: dict[str, str]) -> str:
    date_value = parse_date(first(row, ["race_date", "meeting_date", "date"]))
    track = first(row, ["track", "meeting", "meeting_name"])
    race_no = first(row, ["race_no", "race", "race_number"])
    explicit = first(row, ["race_key"])
    return race_key_for(date_value, track, race_no) if date_value and track and race_no else explicit


def index(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = race_key(row)
        if key:
            out[key].append(row)
    return out


def missing_count(rows: list[dict[str, str]], keys: list[str]) -> int:
    return sum(1 for row in rows if not has_value(first(row, keys)))


def main() -> None:
    universe = [row for row in load("edgeiq_vic_three_day_meeting_universe.csv") if normalized_track(first(row, ["track"])) == "FLEMINGTON" and parse_date(first(row, ["race_date", "meeting_date"])) == TOMORROW]
    runner_board = index(load("edgeiq_live_runner_board_governed_v1.csv"))
    runner_intel = index(load("edgeiq_runner_intelligence_v1.csv"))
    heatmap = index(load("edgeiq_ratings_intelligence_heatmap_v1.csv"))
    speed_map = index(load("edgeiq_map_enrichment_feed_v3.csv"))
    form = index(load("runner_form_history.csv"))
    gear = index(load("edgeiq_gear_terminal_feed_v1.csv"))
    sectionals = index(load("edgeiq_form_sectional_terminal_feed_v1.csv"))
    results = index(load("edgeiq_results_master_v1.csv"))
    dna = index(load("edgeiq_runner_dna_drawer_feed_v2.csv"))
    explain = index(load("edgeiq_explainability_terminal_feed_v1_2.csv"))
    market = index(load("edgeiq_live_bet_quality_v1_1.csv"))

    race_rows = {}
    for row in universe:
        key = race_key(row)
        if key:
            race_rows.setdefault(key, row)

    output = []
    for key, race in sorted(race_rows.items()):
        board = runner_board.get(key, [])
        board_market_rows = [runner for runner in board if has_value(first(runner, ["live_price", "market_price", "fixed_win", "ui_price", "tab_fixed_win"]))]
        board_rating_rows = [runner for runner in board if has_value(first(runner, ["projected_rating_v5_2", "projected_rating_V6_1_RESEARCH", "epi", "runner_rating"]))]
        board_speed_rows = [runner for runner in board if has_value(first(runner, ["speed_map_bucket", "run_style", "map_x_pct", "map_y_px", "early_speed_rating"]))]
        external_market_rows = market.get(key, [])
        external_rating_rows = heatmap.get(key, [])
        external_speed_rows = speed_map.get(key, [])
        row = {
            "race_key": key,
            "race_date": TOMORROW,
            "track": first(race, ["track"]),
            "race_no": first(race, ["race_no"]),
            "race_list": "YES",
            "field_size": len(board),
            "runners": len(board),
            "missing_trainers": missing_count(board, ["trainer"]),
            "missing_jockeys": missing_count(board, ["jockey", "rider"]),
            "missing_barriers": missing_count(board, ["barrier", "draw"]),
            "market_prices_rows": len(external_market_rows) or len(board_market_rows),
            "ratings_rows": len(external_rating_rows) or len(board_rating_rows),
            "projected_rating_missing": missing_count(board, ["projected_rating_v5_2", "projected_rating_V6_1_RESEARCH"]),
            "speed_map_rows": len(external_speed_rows) or len(board_speed_rows),
            "form_rows": len(form.get(key, [])),
            "historical_runs_rows": len(form.get(key, [])),
            "gear_rows": len(gear.get(key, [])),
            "sectional_rows": len(sectionals.get(key, [])),
            "results_history_rows": len(results.get(key, [])),
            "dna_rows": len(dna.get(key, [])),
            "explainability_rows": len(explain.get(key, [])),
            "market_board_rows": len(external_market_rows) or len(board_market_rows),
            "runner_intelligence_rows": len(runner_intel.get(key, [])),
        }
        required = ["field_size", "runners", "ratings_rows", "speed_map_rows", "market_board_rows", "runner_intelligence_rows"]
        row["status"] = "READY" if board and all(int(row[name] or 0) > 0 for name in required) else "CHECK"
        output.append(row)

    if not output:
        output.append({
            "race_key": "",
            "race_date": TOMORROW,
            "track": "FLEMINGTON",
            "race_no": "",
            "race_list": "NO",
            "field_size": 0,
            "runners": 0,
            "missing_trainers": 0,
            "missing_jockeys": 0,
            "missing_barriers": 0,
            "market_prices_rows": 0,
            "ratings_rows": 0,
            "projected_rating_missing": 0,
            "speed_map_rows": 0,
            "form_rows": 0,
            "historical_runs_rows": 0,
            "gear_rows": 0,
            "sectional_rows": 0,
            "results_history_rows": 0,
            "dna_rows": 0,
            "explainability_rows": 0,
            "market_board_rows": 0,
            "runner_intelligence_rows": 0,
            "status": "NO_FLEMINGTON_TOMORROW_IN_UNIVERSE",
        })

    fields = list(output[0].keys())
    write_csv(OUT, output, fields)
    summary = {
        "target_date": TOMORROW,
        "flemington_races": len([row for row in output if row.get("race_key")]),
        "ready_races": sum(1 for row in output if row.get("status") == "READY"),
        "check_races": sum(1 for row in output if row.get("status") != "READY"),
        "total_runners": sum(int(row.get("runners") or 0) for row in output),
        "status": "READY" if output and all(row.get("status") == "READY" for row in output) else "CHECK",
        "built_at": now_iso(),
    }
    write_csv(SUMMARY_OUT, [summary], list(summary.keys()))
    print(f"Wrote {OUT} ({len(output)} rows)")
    print(f"Wrote {SUMMARY_OUT}")


if __name__ == "__main__":
    main()
