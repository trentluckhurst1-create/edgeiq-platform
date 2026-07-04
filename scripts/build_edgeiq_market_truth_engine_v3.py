from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path

from edgeiq_csv_utils import boolish, build_lookup, clean, file_age_seconds, first, merge_rows, num, read_csv, runner_key, write_csv


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_market_truth_engine_v3.csv"

LIVE = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
EXECUTION = DATA / "edgeiq_execution_board_v3.csv"
PROB = DATA / "edgeiq_probability_engine_v4_1.csv"
RATED = DATA / "rated_market_v2.csv"

FIELDS = [
    "built_at", "track", "race_no", "horse", "horse_key", "market_price", "fair_price", "edge_pct",
    "truth_grade", "market_confidence", "overlay_validity", "liquidity_grade", "fake_overlay_flag",
    "market_stability", "late_drift_risk", "execution_trust_score", "suppression_reason",
]


def price(row: dict[str, str]) -> float:
    return num(first(row, ["ui_price", "market_price", "sportsbet_price", "live_price", "fixed_win", "market_price_extra"]))


def fair(row: dict[str, str]) -> float:
    return num(first(row, ["ui_fair_price", "v3_fair_price", "contextual_fair_price", "rated_price", "fair_price"]))


def edge(row: dict[str, str], market: float, model_fair: float) -> float:
    explicit = num(first(row, ["ui_edge_pct", "edge_pct", "overlay_pct", "v3_edge_pct", "contextual_overlay_pct"]))
    if not math.isnan(explicit):
        return explicit
    if not math.isnan(market) and not math.isnan(model_fair) and model_fair > 0:
        return ((market / model_fair) - 1) * 100
    return math.nan


def flucs(row: dict[str, str]) -> list[float]:
    raw = first(row, ["flucs", "market_fluctuations", "price_fluctuations", "fixed_odds_flucs", "odds_flucs"])
    if not raw:
        return []
    values = []
    for piece in raw.replace("->", " ").replace("|", " ").replace(",", " ").split():
        value = num(piece)
        if not math.isnan(value) and value > 0:
            values.append(value)
    return values[-6:]


def grade(row: dict[str, str]) -> dict[str, object]:
    market = price(row)
    model_fair = fair(row)
    overlay = edge(row, market, model_fair)
    scratched = boolish(first(row, ["is_scratched", "scratch_status", "runner_status"]))
    confidence = num(first(row, ["confidence_score", "model_confidence_score", "source_count"]), 50)
    values = flucs(row)
    late_drift = len(values) >= 2 and values[-1] > values[-2] * 1.08
    firm = len(values) >= 2 and values[-1] < values[-2] * 0.94
    stale_age = file_age_seconds(LIVE)

    reasons: list[str] = []
    score = 72.0
    if scratched:
        score = 0
        reasons.append("scratched")
    if math.isnan(market) or market <= 1:
        score -= 45
        reasons.append("no_live_price")
    if math.isnan(model_fair) or model_fair <= 1 or model_fair > 200:
        score -= 28
        reasons.append("impossible_fair")
    if math.isnan(overlay):
        score -= 22
        reasons.append("missing_edge")
    elif overlay >= 45 and market >= 25:
        score -= 32
        reasons.append("manipulated_longshot_overlay")
    elif overlay >= 30 and confidence < 40:
        score -= 24
        reasons.append("weak_confidence_overlay")
    if market >= 50:
        score -= 20
        reasons.append("illiquid_longshot")
    elif market >= 25:
        score -= 10
        reasons.append("thin_liquidity")
    if late_drift:
        score -= 18
        reasons.append("late_drift")
    if stale_age is not None and stale_age > 180:
        score -= 18
        reasons.append("stale_price_file")
    if confidence < 25:
        score -= 14
        reasons.append("low_model_confidence")
    if firm and overlay > 0:
        score += 6
    score = max(0, min(100, score))

    if score >= 80:
        truth = "TRUSTED"
    elif score >= 62:
        truth = "ACCEPTABLE"
    elif score >= 42:
        truth = "QUESTIONABLE"
    else:
        truth = "REJECT"

    liquidity = "NO_MARKET" if math.isnan(market) else "DEEP" if market <= 8 else "STANDARD" if market <= 20 else "THIN" if market <= 50 else "ILLIQUID"
    stability = "DEAD" if math.isnan(market) else "DRIFTING" if late_drift else "FIRMING" if firm else "STABLE"
    overlay_validity = "VALID" if truth in {"TRUSTED", "ACCEPTABLE"} and not math.isnan(overlay) and overlay > 0 else "INVALID" if reasons else "NEUTRAL"

    return {
        "market_price": "" if math.isnan(market) else round(market, 4),
        "fair_price": "" if math.isnan(model_fair) else round(model_fair, 4),
        "edge_pct": "" if math.isnan(overlay) else round(overlay, 3),
        "truth_grade": truth,
        "market_confidence": "HIGH" if score >= 80 else "MEDIUM" if score >= 62 else "LOW" if score >= 42 else "DO_NOT_TRUST",
        "overlay_validity": overlay_validity,
        "liquidity_grade": liquidity,
        "fake_overlay_flag": "YES" if any("overlay" in reason for reason in reasons) else "NO",
        "market_stability": stability,
        "late_drift_risk": "HIGH" if late_drift else "LOW",
        "execution_trust_score": round(score, 2),
        "suppression_reason": "|".join(reasons),
    }


def main() -> None:
    base = read_csv(LIVE)
    if not base:
        base = read_csv(EXECUTION)
    rows = merge_rows(base, [read_csv(EXECUTION), read_csv(PROB), read_csv(RATED)])
    out = []
    for row in rows:
        result = grade(row)
        out.append({
            "built_at": datetime.now().isoformat(timespec="seconds"),
            "track": first(row, ["track"]),
            "race_no": first(row, ["race_no", "race_number"]),
            "horse": first(row, ["horse", "runner", "horse_name"]),
            "horse_key": first(row, ["horse_key"]) or runner_key(row).split("|")[-1],
            **result,
        })
    write_csv(OUT, out, FIELDS)
    print("=" * 100)
    print("EDGEIQ MARKET TRUTH ENGINE V3")
    print("=" * 100)
    print("ROWS:", len(out))
    print("REJECT:", sum(1 for row in out if row["truth_grade"] == "REJECT"))
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
