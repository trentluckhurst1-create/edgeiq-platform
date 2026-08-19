import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "public" / "data"

IN_EDGE = PUB / "edgeiq_sectional_edge_detection_v1.csv"
IN_GRAPH = PUB / "edgeiq_canonical_market_entity_graph_v1.csv"

OUT_COMPARE = PUB / "edgeiq_sectional_market_comparison_v2.csv"
OUT_SUMMARY = PUB / "edgeiq_sectional_market_comparison_summary_v2.csv"

FIELDS = [
    "race_date","track","race_no","horse",
    "sectional_edge_label","sectional_edge_tier","sectional_fit_score",
    "cluster_family","race_shape_label",
    "market_price","rated_price","market_implied_prob",
    "entity_match_score","entity_match_confidence",
    "entity_resolution_status","trusted_market_link",
    "sectional_market_gap","sectional_value_signal",
    "market_comparison_label","market_comparison_tier",
    "sandbox_action",
    "trusted_for_live_modelling","trusted_for_live_execution",
    "notes"
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

def key(row):
    return "|".join([
        val(row, "race_date"),
        val(row, "track"),
        val(row, "race_no"),
        norm(val(row, "horse")),
    ])

def to_float(v):
    try:
        s = str(v or "").strip().replace("$", "").replace(",", "")
        if not s or s == "-":
            return 0.0
        return float(s)
    except Exception:
        return 0.0

def comparison(score, price, trusted):
    if trusted != "YES":
        return "NO_TRUSTED_MARKET_LINK", "NO_LINK", "NO_ACTION"

    if price <= 0:
        return "NO_MARKET_PRICE", "NO_PRICE", "NO_ACTION"

    if score >= 85 and price >= 8:
        return "PRIMARY_SECTIONAL_EDGE_BIG_PRICE", "A+", "WATCHLIST_PRIMARY_BIG_PRICE"
    if score >= 85 and price >= 5:
        return "PRIMARY_SECTIONAL_EDGE_PRICE_ROOM", "A", "WATCHLIST_PRIMARY_PRICE_ROOM"
    if score >= 85:
        return "PRIMARY_SECTIONAL_EDGE_SHORT_PRICE", "B", "WATCHLIST_PRICE_SENSITIVE"
    if score >= 75 and price >= 8:
        return "SECONDARY_SECTIONAL_EDGE_PRICE_ROOM", "B", "WATCHLIST_SECONDARY_PRICE_ROOM"
    if score >= 60 and price >= 10:
        return "MONITOR_LONG_PRICE_SHAPE", "C", "MONITOR_ONLY"
    if score < 45 and price <= 5:
        return "SHORT_PRICE_NEGATIVE_SHAPE", "F", "NEGATIVE_MARKET_RISK"
    if score < 45:
        return "NEGATIVE_SHAPE_MATCH", "F", "NEGATIVE_MARK"
    return "FAIR_OR_UNCLEAR", "D", "NO_ACTION"

def signal(gap):
    if gap >= 0.25:
        return "EXTREME_SECTIONAL_VALUE_SIGNAL"
    if gap >= 0.15:
        return "STRONG_SECTIONAL_VALUE_SIGNAL"
    if gap >= 0.08:
        return "POSITIVE_SECTIONAL_VALUE_SIGNAL"
    if gap >= 0.03:
        return "MILD_SECTIONAL_VALUE_SIGNAL"
    if gap <= -0.15:
        return "NEGATIVE_SECTIONAL_VALUE_SIGNAL"
    return "NO_CLEAR_SECTIONAL_VALUE"

def main():
    edges = read_csv(IN_EDGE)
    graph = read_csv(IN_GRAPH)

    graph_lookup = {key(r): r for r in graph}

    out = []

    for e in edges:
        g = graph_lookup.get(key(e), {})
        trusted = val(g, "trusted_market_link")
        price = to_float(val(g, "market_price"))
        rated = to_float(val(g, "rated_price"))
        score = to_float(val(e, "sectional_fit_score"))

        implied = round(1 / price, 4) if price > 0 else 0.0
        gap = round((score / 100) - implied, 4) if price > 0 and trusted == "YES" else 0.0

        label, tier, action = comparison(score, price, trusted)

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
            "market_price": price if price > 0 else "-",
            "rated_price": rated if rated > 0 else "-",
            "market_implied_prob": implied,
            "entity_match_score": val(g, "entity_match_score"),
            "entity_match_confidence": val(g, "entity_match_confidence"),
            "entity_resolution_status": val(g, "entity_resolution_status") or "NO_ENTITY_GRAPH_ROW",
            "trusted_market_link": trusted or "NO",
            "sectional_market_gap": gap,
            "sectional_value_signal": signal(gap),
            "market_comparison_label": label,
            "market_comparison_tier": tier,
            "sandbox_action": action,
            "trusted_for_live_modelling": "NO",
            "trusted_for_live_execution": "NO",
            "notes": "V2 uses canonical market entity graph. Sandbox only. No execution impact.",
        })

    with OUT_COMPARE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)

    labels = Counter(r["market_comparison_label"] for r in out)
    signals = Counter(r["sectional_value_signal"] for r in out)
    actions = Counter(r["sandbox_action"] for r in out)
    trusted_count = sum(1 for r in out if r["trusted_market_link"] == "YES")

    summary = []
    summary.append({"metric": "comparison_rows", "value": len(out)})
    summary.append({"metric": "trusted_market_link_rows", "value": trusted_count})
    summary.append({"metric": "live_modelling_yes", "value": 0})
    summary.append({"metric": "live_execution_yes", "value": 0})
    summary.append({"metric": "watchlist_primary_big_price", "value": actions.get("WATCHLIST_PRIMARY_BIG_PRICE", 0)})
    summary.append({"metric": "watchlist_primary_price_room", "value": actions.get("WATCHLIST_PRIMARY_PRICE_ROOM", 0)})
    summary.append({"metric": "watchlist_secondary_price_room", "value": actions.get("WATCHLIST_SECONDARY_PRICE_ROOM", 0)})

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
    print("EDGEIQ SECTIONAL MARKET COMPARISON ENGINE V2")
    print("=" * 88)
    print(f"comparison rows built: {len(out)}")
    print(f"trusted market linked rows: {trusted_count}")
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
