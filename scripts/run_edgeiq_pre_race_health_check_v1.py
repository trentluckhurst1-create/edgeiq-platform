from __future__ import annotations

from pathlib import Path

from edgeiq_results_common_v1 import DATA, first, has_value, now_iso, read_csv, write_csv


OUT = DATA / "edgeiq_pre_race_health_check_v1.csv"


def rows(name: str) -> list[dict[str, str]]:
    path = DATA / name
    return list(read_csv(path)) if path.exists() else []


def file_status(name: str, minimum_rows: int = 1) -> tuple[str, int]:
    count = len(rows(name))
    return ("READY" if count >= minimum_rows else "FAIL", count)


def main() -> None:
    board = rows("edgeiq_live_runner_board_governed_v1.csv")
    races = {first(row, ["race_key"]) for row in board if first(row, ["race_key"])}
    meetings = {first(row, ["meeting_key"]) for row in board if first(row, ["meeting_key"])}
    rated = sum(1 for row in board if has_value(first(row, ["projected_rating_v5_2", "projected_rating_V6_1_RESEARCH", "projected_rating_backfill_v1"])))
    market = sum(1 for row in board if has_value(first(row, ["live_price", "market_price", "fixed_win", "ui_price"])))
    checks = [
        ("meetings_loaded", "READY" if meetings else "FAIL", len(meetings), "Meeting keys in governed runner board."),
        ("races_loaded", "READY" if races else "FAIL", len(races), "Race keys in governed runner board."),
        ("runners_loaded", "READY" if board else "FAIL", len(board), "Runner rows in governed runner board."),
        ("ratings_loaded", "READY" if board and rated == len(board) else "WARN", f"{rated}/{len(board)}", "Projected rating or display backfill present."),
        ("market_loaded", "READY" if market else "WARN", f"{market}/{len(board)}", "Current market source may not exist before market release."),
    ]
    for name, minimum in [
        ("edgeiq_live_runner_board_governed_v1.csv", 1),
        ("edgeiq_form_sectional_terminal_feed_v1.csv", 1),
        ("edgeiq_gear_terminal_feed_v1.csv", 1),
        ("edgeiq_historical_year_feed_v1.csv", 1),
        ("edgeiq_historical_month_feed_v1.csv", 1),
        ("edgeiq_historical_meeting_feed_v1.csv", 1),
        ("edgeiq_historical_race_feed_v1.csv", 1),
        ("edgeiq_historical_runner_feed_v1.csv", 1),
    ]:
        status, count = file_status(name, minimum)
        checks.append((name.replace(".csv", ""), status, count, "Required terminal/backend feed present."))

    output = [{"check": check, "status": status, "value": value, "detail": detail, "built_at": now_iso()} for check, status, value, detail in checks]
    write_csv(OUT, output, ["check", "status", "value", "detail", "built_at"])
    final = "FAIL" if any(row["status"] == "FAIL" for row in output) else "WARN" if any(row["status"] == "WARN" for row in output) else "READY"
    print(f"Wrote {OUT} ({len(output)} rows)")
    print(f"status={final}")


if __name__ == "__main__":
    main()
