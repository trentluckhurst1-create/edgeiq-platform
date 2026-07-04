import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "public" / "data"

IN_EDGE = PUB / "edgeiq_sectional_edge_detection_v1.csv"
IN_MARKET = PUB / "sportsbet_live_market_v1.csv"
IN_EXEC = PUB / "edgeiq_execution_engine_v4.csv"

OUT_COMPARE = PUB / "edgeiq_sectional_market_comparison_v1.csv"
OUT_SUMMARY = PUB / "edgeiq_sectional_market_comparison_summary_v1.csv"

FIELDS = [
    "race_date","track","race_no","horse",
    "sectional_edge_label","sectional_edge_tier","sectional_fit_score",
    "cluster_family","race_shape_label",
    "market_price","rated_price","market_implied_prob",
    "sectional_value_signal","sectional_market_gap",
    "market_comparison_label","market_comparison_tier",
    "sandbox_action","trusted_for_live_modelling",
    "trusted_for_live_execution","notes"
]

def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def val(row, *names):
    for n in names:
        if n in row and str(row.get(n, "")).strip():
            return str(row.get(n, "")).strip()
    return ""

def norm(v):
    return "".join(ch for ch in str(v or "").upper().strip() if ch.isalnum())

def race_horse_key(row):
    return (
        val(row, "race_date", "date", "meeting_date"),
        val(row, "track", "track_name", "meeting"),
        val(row, "race_no", "race_number"),
        norm(val(row, "horse", "horse_name", "runner_name", "selection_name")),
    )

def to_float(v):
    try:
        if v is None:
            return 0.0
        s = str(v).strip().replace("$", "")
        if not s or s == "-":
            return 0.0
        return float(s)
    except Exception:
        return 0.0

def comparison_label(score, price):
    if price <= 0:
        return "NO_MARKET_PRICE", "NO_PRICE", "NO_ACTION"
    if score >= 85 and price >= 6:
        return "SECTIONAL_EDGE_WITH_PRICE_ROOM", "A", "WATCHLIST_MARKET_MISPRICE"
    if score >= 85 and price < 6:
        return "SECTIONAL_EDGE_BUT_SHORT_PRICE", "B", "WATCHLIST_PRICE_SENSITIVE"
    if score >= 75 and price >= 8:
        return "SECONDARY_EDGE_WITH_PRICE_ROOM", "B", "WATCHLIST_SECONDARY_MISPRICE"
    if score >= 60 and price >= 10:
        return "MONITOR_LONG_PRICE_SHAPE", "C", "MONITOR_ONLY"
    if score < 45 and price <= 5:
        return "SHORT_PRICE_NEGATIVE_SHAPE", "F", "NEGATIVE_MARKET_RISK"
    if score < 45:
        return "NEGATIVE_SHAPE", "F", "NEGATIVE_MARK"
    return "FAIR_OR_UNCLEAR", "D", "NO_ACTION"

def main():
    edges = read_csv(IN_EDGE)
    market = read_csv(IN_MARKET)
    execution = read_csv(IN_EXEC)

    market_lookup = {}
    for r in market:
        k = race_horse_key(r)
        if any(k):
            market_lookup[k] = r

    exec_lookup = {}
    for r in execution:
        k = race_horse_key(r)
        if any(k):
            exec_lookup[k] = r

    out = []

    for e in edges:
        k = race_horse_key(e)
        m = market_lookup.get(k, {})
        x = exec_lookup.get(k, {})

        market_price = to_float(val(m, "sportsbet_price", "price", "fixed_win_price", "win_price", "odds") or val(x, "sportsbet_price", "market_price", "price"))
        rated_price = to_float(val(x, "rated_price", "fair_price", "edgeiq_price"))

        implied = round(1 / market_price, 4) if market_price > 0 else 0

        score = to_float(val(e, "sectional_fit_score"))
        label, tier, action = comparison_label(score, market_price)

        if market_price > 0:
            gap = round((score / 100) - implied, 4)
        else:
            gap = 0

        if gap >= 0.15:
            signal = "STRONG_SECTIONAL_VALUE_SIGNAL"
        elif gap >= 0.08:
            signal = "POSITIVE_SECTIONAL_VALUE_SIGNAL"
        elif gap >= 0.03:
            signal = "MILD_SECTIONAL_VALUE_SIGNAL"
        elif gap <= -0.15:
            signal = "NEGATIVE_SECTIONAL_VALUE_SIGNAL"
        else:
            signal = "NO_CLEAR_SECTIONAL_VALUE"

        out.append({
            "race_date": val(e, "race_date"),
            "track": val(e, "track"),
            "race_no": val(e, "race_no"),
            "horse": val(e, "horse"),
            "sectional_edge_label": val(e, "sectional_edge_label"),
            "sectional_edge_tier": val(e, "sectional_edge_tier"),
            "sectional_fit_score": val(e, "sectional_fit_score"),
            "cluster_family": val(e, "cluster_family"),
            "race_shape_label": val(e, "race_shape_label"),
            "market_price": market_price if market_price > 0 else "-",
            "rated_price": rated_price if rated_price > 0 else "-",
            "market_implied_prob": implied,
            "sectional_value_signal": signal,
            "sectional_market_gap": gap,
            "market_comparison_label": label,
            "market_comparison_tier": tier,
            "sandbox_action": action,
            "trusted_for_live_modelling": "NO",
            "trusted_for_live_execution": "NO",
            "notes": "Sandbox comparison only. No pricing/execution impact.",
        })

    with OUT_COMPARE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)

    labels = Counter(r["market_comparison_label"] for r in out)
    signals = Counter(r["sectional_value_signal"] for r in out)
    actions = Counter(r["sandbox_action"] for r in out)

    summary = []
    summary.append({"metric": "comparison_rows", "value": len(out)})
    summary.append({"metric": "live_modelling_yes", "value": 0})
    summary.append({"metric": "live_execution_yes", "value": 0})
    summary.append({"metric": "watchlist_market_misprice", "value": actions.get("WATCHLIST_MARKET_MISPRICE", 0)})
    summary.append({"metric": "watchlist_secondary_misprice", "value": actions.get("WATCHLIST_SECONDARY_MISPRICE", 0)})

    for k, v in labels.most_common():
        summary.append({"metric": f"comparison::{k}", "value": v})
    for k, v in signals.most_common():
        summary.append({"metric": f"signal::{k}", "value": v})
    for k, v in actions.most_common():
        summary.append({"metric": f"action::{k}", "value": v})

    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("=" * 88)
    print("EDGEIQ SECTIONAL MARKET COMPARISON ENGINE V1")
    print("=" * 88)
    print(f"comparison rows built: {len(out)}")
    print(f"saved: {OUT_COMPARE}")
    print(f"saved: {OUT_SUMMARY}")
    print("comparison labels:")
    for k, v in labels.most_common():
        print(f"  {k}: {v}")
    print("signals:")
    for k, v in signals.most_common():
        print(f"  {k}: {v}")
    print("actions:")
    for k, v in actions.most_common():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
