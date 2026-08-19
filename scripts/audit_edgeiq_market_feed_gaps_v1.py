from __future__ import annotations

from collections import Counter, defaultdict

from edgeiq_results_common_v1 import DATA, first, has_value, now_iso, read_csv, race_key_for, parse_date, write_csv


OUT = DATA / "edgeiq_market_feed_gaps_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_market_feed_gaps_summary_v1.csv"


def load(name: str) -> list[dict[str, str]]:
    path = DATA / name
    return list(read_csv(path)) if path.exists() else []


def race_key(row: dict[str, str]) -> str:
    return first(row, ["race_key"]) or race_key_for(parse_date(first(row, ["race_date", "meeting_date"])), first(row, ["track"]), first(row, ["race_no"]))


def price_available(row: dict[str, str]) -> bool:
    return has_value(first(row, ["live_price", "market_price", "fixed_win", "ui_price", "tab_fixed_win", "sportsbet_price", "current_price"]))


def main() -> None:
    board = load("edgeiq_live_runner_board_v1.csv")
    universe = load("edgeiq_vic_three_day_meeting_universe.csv")
    market_sources = {
        "sportsbet_live_market_v1": load("sportsbet_live_market_v1.csv"),
        "ladbrokes_affiliate_market_odds": load("ladbrokes_affiliate_market_odds.csv"),
        "edgeiq_live_bet_quality_v1_1": load("edgeiq_live_bet_quality_v1_1.csv"),
        "edgeiq_market_tape": load("edgeiq_market_tape.csv"),
    }

    source_counts: dict[str, Counter[str]] = {}
    for name, rows in market_sources.items():
        counter: Counter[str] = Counter()
        for row in rows:
            key = race_key(row)
            if key and price_available(row):
                counter[key] += 1
        source_counts[name] = counter

    universe_by_race: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in universe:
        key = race_key(row)
        if key:
            universe_by_race[key].append(row)

    board_by_race: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in board:
        key = race_key(row)
        if key:
            board_by_race[key].append(row)

    output: list[dict[str, object]] = []
    for key in sorted(universe_by_race):
        rows = board_by_race.get(key, [])
        source_total = sum(counter.get(key, 0) for counter in source_counts.values())
        prices = sum(1 for row in rows if price_available(row))
        status = "MARKET_AVAILABLE" if prices else "MARKET_SOURCE_UNAVAILABLE" if source_total == 0 else "JOIN_FAILURE"
        sample = rows[0] if rows else universe_by_race[key][0]
        output.append(
            {
                "race_key": key,
                "race_date": first(sample, ["race_date", "meeting_date"]),
                "track": first(sample, ["track"]),
                "race_no": first(sample, ["race_no"]),
                "runner_rows": len(rows),
                "board_price_rows": prices,
                "sportsbet_price_rows": source_counts["sportsbet_live_market_v1"].get(key, 0),
                "tab_price_rows": source_counts["ladbrokes_affiliate_market_odds"].get(key, 0),
                "market_quality_price_rows": source_counts["edgeiq_live_bet_quality_v1_1"].get(key, 0),
                "market_tape_price_rows": source_counts["edgeiq_market_tape"].get(key, 0),
                "price_timestamp": first(sample, ["market_capture_timestamp", "price_timestamp", "updated_at"], ""),
                "gap_status": status,
                "built_at": now_iso(),
            }
        )

    write_csv(OUT, output, list(output[0].keys()) if output else ["status"])
    summary_rows = [
        {"metric": "races_audited", "value": len(output)},
        {"metric": "market_available_races", "value": sum(1 for row in output if row["gap_status"] == "MARKET_AVAILABLE")},
        {"metric": "market_unavailable_races", "value": sum(1 for row in output if row["gap_status"] == "MARKET_SOURCE_UNAVAILABLE")},
        {"metric": "market_join_failure_races", "value": sum(1 for row in output if row["gap_status"] == "JOIN_FAILURE")},
        {"metric": "built_at", "value": now_iso()},
    ]
    write_csv(SUMMARY_OUT, summary_rows, ["metric", "value"])
    print(f"Wrote {OUT} ({len(output)} rows)")
    print(f"Wrote {SUMMARY_OUT}")


if __name__ == "__main__":
    main()
