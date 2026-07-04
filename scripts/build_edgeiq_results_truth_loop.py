from __future__ import annotations

import math
from datetime import datetime, timedelta
from pathlib import Path

from edgeiq_csv_utils import build_lookup, clean, first, num, read_csv, runner_key, write_csv


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

EXECUTION = DATA / "edgeiq_execution_engine_v4.csv"
SETTLEMENT = DATA / "edgeiq_results_auto_settlement.csv"
TAPE = DATA / "edgeiq_market_tape_summary.csv"
CLV = DATA / "edgeiq_clv_memory.csv"
TRUTH_OUT = DATA / "edgeiq_results_truth_loop.csv"
ACCOUNT_OUT = DATA / "edgeiq_execution_accountability.csv"

TRUTH_FIELDS = [
    "built_at", "race_date", "track", "race_no", "horse", "horse_key", "execution_decision",
    "stake", "starting_price", "closing_price", "finish_position", "result_status", "pnl",
    "clv_result", "execution_quality", "suppression_correctness", "accountability_grade",
]

ACCOUNT_FIELDS = [
    "built_at", "decision_group", "rows", "pending", "settled", "turnover", "pnl",
    "avg_clv_pct", "positive_clv_rows", "accountability_grade", "summary",
]


def now_stamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def settled_status(row: dict[str, str]) -> str:
    raw = clean(first(row, ["result_status", "result", "settlement_status", "status"])).upper()
    if raw in {"WON", "LOST", "SETTLED", "RESULTED", "FINAL", "OFFICIAL"}:
        return raw
    return "PENDING"


def merge(row: dict[str, str], maps: list[dict[str, dict[str, str]]]) -> dict[str, str]:
    out = dict(row)
    key = runner_key(row)
    for mapping in maps:
        extra = mapping.get(key)
        if not extra:
            continue
        for col, value in extra.items():
            if clean(value) and not clean(out.get(col)):
                out[col] = value
            elif clean(value):
                out[f"{col}_extra"] = value
    return out


def calc_pnl(row: dict[str, str], result: str, stake: float, sp: float) -> str:
    supplied = num(first(row, ["pnl", "profit_loss", "net_result"]))
    if not math.isnan(supplied):
        return f"{supplied:.2f}"
    if result == "PENDING" or stake <= 0:
        return ""
    if result == "WON" and not math.isnan(sp) and sp > 1:
        return f"{stake * (sp - 1):.2f}"
    if result in {"LOST", "SETTLED", "RESULTED", "FINAL", "OFFICIAL"}:
        return f"{-stake:.2f}"
    return ""


def quality(decision: str, result: str, clv_pct: float, pnl: float) -> tuple[str, str, str]:
    if result == "PENDING":
        return "PENDING", "PENDING", "PENDING"
    active = decision in {"EXECUTE", "ALLOW", "REDUCE"}
    if active and pnl > 0 and (math.isnan(clv_pct) or clv_pct >= 0):
        return "GOOD_EXECUTION", "N/A", "A"
    if active and pnl < 0 and not math.isnan(clv_pct) and clv_pct < -5:
        return "POOR_PRICE_DISCIPLINE", "N/A", "C"
    if decision in {"KILL", "SUPPRESS", "NO_PRICE", "SCRATCHED"}:
        return "NO_BET_REVIEW", "REVIEW_REQUIRED", "B"
    return "NEUTRAL", "UNKNOWN", "B"


def truth_rows() -> list[dict[str, object]]:
    execution = read_csv(EXECUTION)
    maps = [build_lookup(read_csv(SETTLEMENT)), build_lookup(read_csv(TAPE)), build_lookup(read_csv(CLV))]
    out: list[dict[str, object]] = []
    built_at = now_stamp()
    for base in execution:
        row = merge(base, maps)
        decision = clean(first(row, ["execution_decision"]))
        stake = num(first(row, ["stake"]), 0)
        starting = num(first(row, ["starting_price", "sp", "open_price", "live_price"]))
        closing = num(first(row, ["closing_price", "close_price", "last_price"]))
        result = settled_status(row)
        pnl_text = calc_pnl(row, result, stake, closing if not math.isnan(closing) else starting)
        pnl_value = num(pnl_text)
        clv_pct = num(first(row, ["clv_result", "clv_achieved_pct", "move_pct"]))
        quality_label, suppression_correctness, grade = quality(decision, result, clv_pct, pnl_value if not math.isnan(pnl_value) else 0)
        out.append({
            "built_at": built_at,
            "race_date": first(row, ["race_date", "date"]),
            "track": first(row, ["track", "meeting"]),
            "race_no": first(row, ["race_no", "race_number"]),
            "horse": first(row, ["horse", "runner", "horse_name", "runner_name"]),
            "horse_key": first(row, ["horse_key"]) or runner_key(row).split("|")[-1],
            "execution_decision": decision,
            "stake": "" if stake <= 0 else f"{stake:.2f}",
            "starting_price": "" if math.isnan(starting) else f"{starting:.2f}",
            "closing_price": "" if math.isnan(closing) else f"{closing:.2f}",
            "finish_position": first(row, ["finish_position", "placing", "position"]),
            "result_status": result,
            "pnl": pnl_text,
            "clv_result": "" if math.isnan(clv_pct) else f"{clv_pct:.2f}",
            "execution_quality": quality_label,
            "suppression_correctness": suppression_correctness,
            "accountability_grade": grade,
        })
    return out


def accountability(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(clean(row.get("execution_decision")) or "UNKNOWN", []).append(row)
    out: list[dict[str, object]] = []
    built_at = now_stamp()
    for decision, items in sorted(grouped.items()):
        pending = sum(1 for row in items if clean(row.get("result_status")).upper() == "PENDING")
        settled = len(items) - pending
        turnover = sum(num(row.get("stake"), 0) for row in items if not math.isnan(num(row.get("stake"), 0)))
        pnl = sum(num(row.get("pnl"), 0) for row in items if not math.isnan(num(row.get("pnl"), 0)))
        clv_values = [num(row.get("clv_result")) for row in items if not math.isnan(num(row.get("clv_result")))]
        avg_clv = sum(clv_values) / len(clv_values) if clv_values else math.nan
        positive_clv = sum(1 for value in clv_values if value >= 0)
        grade = "PENDING" if settled == 0 else "A" if pnl >= 0 and (math.isnan(avg_clv) or avg_clv >= 0) else "C"
        out.append({
            "built_at": built_at,
            "decision_group": decision,
            "rows": len(items),
            "pending": pending,
            "settled": settled,
            "turnover": f"{turnover:.2f}",
            "pnl": f"{pnl:.2f}",
            "avg_clv_pct": "" if math.isnan(avg_clv) else f"{avg_clv:.2f}",
            "positive_clv_rows": positive_clv,
            "accountability_grade": grade,
            "summary": f"{decision}: {pending} pending, {settled} settled",
        })
    return out


def main() -> None:
    rows = truth_rows()
    account = accountability(rows)
    write_csv(TRUTH_OUT, rows, TRUTH_FIELDS)
    write_csv(ACCOUNT_OUT, account, ACCOUNT_FIELDS)
    print("=" * 90)
    print("EDGEIQ RESULTS TRUTH LOOP")
    print("=" * 90)
    print("ROWS:", len(rows))
    print("PENDING:", sum(1 for row in rows if row["result_status"] == "PENDING"))
    print("ACCOUNTABILITY ROWS:", len(account))
    print("OUT:", TRUTH_OUT)
    print("ACCOUNTABILITY:", ACCOUNT_OUT)


if __name__ == "__main__":
    main()
