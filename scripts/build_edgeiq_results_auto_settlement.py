from __future__ import annotations

from datetime import datetime
from pathlib import Path

from edgeiq_csv_utils import build_lookup, first, num, read_csv, runner_key, write_csv


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_results_auto_settlement.csv"
EXECUTION = DATA / "edgeiq_execution_board_v3.csv"
SUPPRESSION = DATA / "edgeiq_execution_suppression_v2.csv"
RESULTS = DATA / "race_results.csv"
CLV = DATA / "edgeiq_clv_memory.csv"

FIELDS = [
    "settled_at", "track", "race_no", "horse", "horse_key", "execution_action", "suppression_action",
    "market_price", "stake", "finish", "result", "pnl", "roi_pct", "clv_achieved_pct", "review_note",
]


def result_for(finish: str) -> str:
    return "WIN" if finish in {"1", "1.0", "FIRST"} else "LOSE" if finish else "PENDING"


def main() -> None:
    suppression = build_lookup(read_csv(SUPPRESSION))
    results = build_lookup(read_csv(RESULTS))
    clv = build_lookup(read_csv(CLV))
    rows = []
    for row in read_csv(EXECUTION):
        key = runner_key(row)
        sup = suppression.get(key, {})
        res = results.get(key, {})
        memory = clv.get(key, {})
        price = num(first(row, ["market_price"]))
        stake = num(first(row, ["recommended_stake", "stake", "ui_stake"]), 0)
        finish = first(res, ["finish", "finish_pos", "position", "result"])
        result = result_for(finish)
        if result == "WIN":
            pnl = stake * max(0, price - 1)
        elif result == "LOSE":
            pnl = -stake
        else:
            pnl = 0
        roi = (pnl / stake * 100) if stake else 0
        rows.append({
            "settled_at": datetime.now().isoformat(timespec="seconds"),
            "track": first(row, ["track"]),
            "race_no": first(row, ["race_no", "race_number"]),
            "horse": first(row, ["horse"]),
            "horse_key": first(row, ["horse_key"]) or key.split("|")[-1],
            "execution_action": first(row, ["execution_action", "v3_execution_action"]),
            "suppression_action": first(sup, ["suppression_action"]),
            "market_price": first(row, ["market_price"]),
            "stake": stake,
            "finish": finish,
            "result": result,
            "pnl": round(pnl, 2),
            "roi_pct": round(roi, 2),
            "clv_achieved_pct": first(memory, ["clv_achieved_pct"]),
            "review_note": "settled" if result != "PENDING" else "awaiting_result",
        })
    write_csv(OUT, rows, FIELDS)
    print("=" * 100)
    print("EDGEIQ RESULTS AUTO SETTLEMENT")
    print("=" * 100)
    print("ROWS:", len(rows))
    print("SETTLED:", sum(1 for row in rows if row["result"] != "PENDING"))
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
