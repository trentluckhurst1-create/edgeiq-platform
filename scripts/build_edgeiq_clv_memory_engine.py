from __future__ import annotations

from datetime import datetime
from pathlib import Path

from edgeiq_csv_utils import build_lookup, first, num, read_csv, runner_key, write_csv


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_clv_memory.csv"

LIVE = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
EXECUTION = DATA / "edgeiq_execution_board_v3.csv"
PREVIOUS = DATA / "edgeiq_clv_memory.csv"
RESULTS = DATA / "edgeiq_results_auto_settlement.csv"

FIELDS = [
    "updated_at", "track", "race_no", "horse", "horse_key", "open_price", "mid_price", "close_price",
    "model_fair", "execution_fair", "result", "clv_achieved_pct", "runner_drift_profile", "samples",
]


def profile(open_price: float, close_price: float) -> str:
    if open_price != open_price or close_price != close_price:
        return "UNKNOWN"
    if close_price < open_price * 0.94:
        return "FIRMED"
    if close_price > open_price * 1.08:
        return "DRIFTED"
    return "STABLE"


def main() -> None:
    previous = build_lookup(read_csv(PREVIOUS))
    results = build_lookup(read_csv(RESULTS))
    execution = build_lookup(read_csv(EXECUTION))
    rows = []
    for live in read_csv(LIVE):
        key = runner_key(live)
        old = previous.get(key, {})
        ex = execution.get(key, {})
        res = results.get(key, {})
        live_price = num(first(live, ["ui_price", "sportsbet_price", "live_price", "market_price", "fixed_win"]))
        open_price = num(first(old, ["open_price"]))
        mid_price = num(first(old, ["mid_price"]))
        if open_price != open_price:
            open_price = live_price
        if mid_price != mid_price:
            mid_price = live_price
        close_price = live_price if live_price == live_price else num(first(old, ["close_price"]))
        fair = num(first(ex, ["v3_fair_price", "ui_fair_price", "rated_price"]))
        execution_fair = num(first(ex, ["v3_fair_price", "fair_price"]))
        clv = ""
        if close_price == close_price and execution_fair == execution_fair and execution_fair > 0:
            clv = round(((close_price / execution_fair) - 1) * 100, 3)
        samples = int(num(first(old, ["samples"]), 0) or 0) + 1
        rows.append({
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "track": first(live, ["track"]),
            "race_no": first(live, ["race_no", "race_number"]),
            "horse": first(live, ["horse", "runner", "horse_name"]),
            "horse_key": first(live, ["horse_key"]) or key.split("|")[-1],
            "open_price": "" if open_price != open_price else round(open_price, 4),
            "mid_price": "" if mid_price != mid_price else round(mid_price, 4),
            "close_price": "" if close_price != close_price else round(close_price, 4),
            "model_fair": "" if fair != fair else round(fair, 4),
            "execution_fair": "" if execution_fair != execution_fair else round(execution_fair, 4),
            "result": first(res, ["result", "settlement_result", "finish"]),
            "clv_achieved_pct": clv,
            "runner_drift_profile": profile(open_price, close_price),
            "samples": samples,
        })
    write_csv(OUT, rows, FIELDS)
    print("=" * 100)
    print("EDGEIQ CLV MEMORY ENGINE")
    print("=" * 100)
    print("ROWS:", len(rows))
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
