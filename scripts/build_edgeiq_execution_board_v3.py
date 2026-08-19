from __future__ import annotations

import csv
import math
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
PROB = DATA / "edgeiq_probability_engine_v4_1.csv"
LIVE = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
OUT = DATA / "edgeiq_execution_board_v3.csv"
DIAG = DATA / "edgeiq_execution_board_v3_diagnostics.csv"

FIELDS = [
    "built_at", "source", "race_date", "track", "race_no", "race_time", "horse", "horse_key", "is_scratched",
    "market_price", "v3_fair_price", "edge_pct", "v3_edge_pct", "confidence_score", "market_state",
    "execution_action", "v3_execution_action", "v3_realism_grade", "execution_reason", "execution_score",
]


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null", "-"} else text


def num(value: object) -> float:
    try:
        text = clean(value).replace("$", "").replace(",", "").replace("%", "")
        return float(text) if text else math.nan
    except ValueError:
        return math.nan


def boolish(value: object) -> bool:
    return clean(value).upper() in {"1", "Y", "YES", "TRUE", "SCR", "SCRATCHED", "WITHDRAWN", "LATE SCR"}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def first(row: dict[str, str], names: list[str]) -> str:
    for name in names:
        if clean(row.get(name)):
            return clean(row.get(name))
    return ""


def fmt(value: float) -> str:
    return "" if math.isnan(value) else str(round(value, 4))


def classify(edge: float, price: float, confidence: float, scratched: bool) -> tuple[str, str, str, float]:
    if scratched:
        return "SCRATCHED", "SCRATCHED", "scratched runner removed from execution", 0
    if math.isnan(edge) or math.isnan(price) or price <= 1:
        return "PASS", "NO_MARKET", "missing live market or edge", 0
    score = 50 + min(30, max(-30, edge)) + min(12, max(-10, 12 - price))
    if not math.isnan(confidence):
        score += (confidence - 50) * 0.2
    score = max(0, min(100, score))
    if edge >= 18 and price <= 20 and score >= 72:
        return "EXECUTE", "ACTIONABLE_OVERLAY", "edge, price and confidence align", score
    if edge >= 8:
        return "WATCH", "VALUE_WATCH", "positive model edge but not execution-grade", score
    if edge <= -10:
        return "PASS", "UNDERLAY", "market is shorter than model fair", score
    return "PASS", "NEUTRAL", "no actionable edge", score


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    source = read_csv(PROB)
    source_name = "edgeiq_probability_engine_v4_1"
    if not source:
        source = read_csv(LIVE)
        source_name = "edgeiq_vic_live_terminal_feed_v1"
    if not source:
        raise SystemExit("No probability or live feed available for execution board v3")

    rows: list[dict[str, object]] = []
    for row in source:
        scratched = boolish(first(row, ["is_scratched", "scratch_status", "runner_status"]))
        price = num(first(row, ["market_price", "ui_price", "sportsbet_price", "live_price", "fixed_win"]))
        fair = num(first(row, ["contextual_fair_price", "v5_contextual_fair_price", "ui_fair_price", "fair_price", "rated_price"]))
        edge = num(first(row, ["contextual_overlay_pct", "v5_contextual_overlay_pct", "ui_edge_pct", "edge_pct", "overlay_pct"]))
        confidence = num(first(row, ["confidence_score", "model_confidence_score", "energy_confidence_score", "source_count"]))
        action, state, reason, score = classify(edge, price, confidence, scratched)
        if scratched:
            price = fair = edge = math.nan
        rows.append({
            "built_at": datetime.now().isoformat(timespec="seconds"),
            "source": source_name,
            "race_date": first(row, ["race_date", "date"]),
            "track": first(row, ["track"]),
            "race_no": first(row, ["race_no", "race_number"]),
            "race_time": first(row, ["race_time", "time"]),
            "horse": first(row, ["horse", "runner", "horse_name"]),
            "horse_key": first(row, ["horse_key"]),
            "is_scratched": "1" if scratched else "",
            "market_price": fmt(price),
            "v3_fair_price": fmt(fair),
            "edge_pct": fmt(edge),
            "v3_edge_pct": fmt(edge),
            "confidence_score": fmt(confidence),
            "market_state": state,
            "execution_action": action,
            "v3_execution_action": action,
            "v3_realism_grade": state,
            "execution_reason": reason,
            "execution_score": round(score, 3),
        })

    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    diag = [{
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "source": source_name,
        "rows": len(rows),
        "scratched_removed": sum(1 for row in rows if row["is_scratched"] == "1"),
        "execute": sum(1 for row in rows if row["execution_action"] == "EXECUTE"),
        "watch": sum(1 for row in rows if row["execution_action"] == "WATCH"),
        "pass": sum(1 for row in rows if row["execution_action"] == "PASS"),
    }]
    with DIAG.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(diag[0].keys()))
        writer.writeheader()
        writer.writerows(diag)

    print("=" * 100)
    print("EDGEIQ EXECUTION BOARD V3")
    print("=" * 100)
    print(diag[0])
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
