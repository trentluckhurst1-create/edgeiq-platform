from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from edgeiq_results_common_v1 import DATA, first, has_value, normalized_runner, normalized_track, now_iso, parse_date, read_csv, race_key_for, write_csv


OUT = DATA / "edgeiq_flemington_final_readiness_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_flemington_final_readiness_summary_v1.csv"
TARGET_DATE = (date(2026, 7, 3) + timedelta(days=1)).isoformat()


def load(name: str) -> list[dict[str, str]]:
    path = DATA / name
    return list(read_csv(path)) if path.exists() else []


def race_key(row: dict[str, str]) -> str:
    explicit = first(row, ["race_key"])
    built = race_key_for(parse_date(first(row, ["race_date", "meeting_date"])), first(row, ["track"]), first(row, ["race_no"]))
    return built or explicit


def index(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = race_key(row)
        if key:
            out[key].append(row)
    return out


def runner_index(rows: list[dict[str, str]]) -> set[str]:
    out = set()
    for row in rows:
        runner = normalized_runner(first(row, ["horse", "runner", "runner_name", "normalized_runner"]))
        if runner:
            out.add(runner)
    return out


def main() -> None:
    board = [row for row in load("edgeiq_live_runner_board_governed_v1.csv") if normalized_track(first(row, ["track"])) == "FLEMINGTON" and first(row, ["race_date"])[:10] == TARGET_DATE]
    races: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in board:
        races[race_key(row)].append(row)
    gear_runners = runner_index(load("edgeiq_gear_terminal_feed_v1.csv"))
    sectional_runners = runner_index(load("edgeiq_form_sectional_terminal_feed_v1.csv"))
    dna_runners = runner_index(load("edgeiq_runner_dna_drawer_feed_v2.csv"))
    profile_runners = runner_index(load("edgeiq_runners_enrichment_feed_v1_1.csv"))
    results = index(load("edgeiq_results_master_v1.csv"))
    output = []
    for key, rows in sorted(races.items()):
        sample = rows[0]
        ratings = sum(1 for row in rows if has_value(first(row, ["projected_rating_v5_2", "projected_rating_V6_1_RESEARCH", "projected_rating_backfill_v1"])))
        market = sum(1 for row in rows if has_value(first(row, ["live_price", "market_price", "fixed_win", "ui_price"])))
        maps = sum(1 for row in rows if has_value(first(row, ["barrier", "draw", "speed_map_bucket", "run_style", "map_x_pct"])))
        current_runners = {normalized_runner(first(row, ["horse", "runner", "runner_name"])) for row in rows}
        current_runners.discard("")
        row = {
            "race_key": key,
            "race_date": TARGET_DATE,
            "track": "FLEMINGTON",
            "race_no": first(sample, ["race_no"]),
            "runners": len(rows),
            "ratings": ratings,
            "projected_ratings": ratings,
            "market": market,
            "gear": len(current_runners & gear_runners),
            "sectionals": len(current_runners & sectional_runners),
            "maps": maps,
            "dna": len(current_runners & dna_runners),
            "profiles": len(current_runners & profile_runners),
            "results_history": len(results.get(key, [])),
            "status": "READY" if ratings == len(rows) and maps == len(rows) else "WARN",
            "built_at": now_iso(),
        }
        output.append(row)
    fields = list(output[0].keys()) if output else ["status"]
    write_csv(OUT, output, fields)
    summary = {
        "target_date": TARGET_DATE,
        "flemington_races": len(output),
        "total_runners": sum(int(row["runners"]) for row in output),
        "races_with_full_projected_ratings": sum(1 for row in output if row["ratings"] == row["runners"]),
        "races_with_market": sum(1 for row in output if int(row["market"]) > 0),
        "status": "READY" if output and all(row["status"] == "READY" for row in output) else "WARN",
        "built_at": now_iso(),
    }
    write_csv(SUMMARY_OUT, [summary], list(summary.keys()))
    print(f"Wrote {OUT} ({len(output)} rows)")
    print(f"Wrote {SUMMARY_OUT}")


if __name__ == "__main__":
    main()
