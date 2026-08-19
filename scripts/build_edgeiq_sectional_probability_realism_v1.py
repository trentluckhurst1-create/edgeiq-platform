import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "public" / "data"

IN_CAL = PUB / "edgeiq_sectional_signal_calibration_v1.csv"
IN_COMPARE = PUB / "edgeiq_sectional_market_comparison_v2.csv"
IN_EDGE = PUB / "edgeiq_sectional_edge_detection_v1.csv"
IN_CLUSTER = PUB / "edgeiq_sectional_archetype_cluster_v1.csv"
IN_SHAPE = PUB / "edgeiq_race_shape_response_v1.csv"

OUT_REALISM = PUB / "edgeiq_sectional_probability_realism_v1.csv"
OUT_SUMMARY = PUB / "edgeiq_sectional_probability_realism_summary_v1.csv"

FIELDS = [
    "race_date","track","race_no","horse",
    "calibration_grade","sectional_fit_score","market_price",
    "raw_sectional_prob","market_implied_prob",
    "field_size","race_shape_risk","cluster_family","cluster_risk",
    "base_rate_prob","field_size_penalty","risk_penalty",
    "volatility_penalty","longshot_penalty","entropy_penalty",
    "realistic_sectional_prob","realistic_market_gap",
    "probability_realism_grade","probability_realism_label",
    "realism_action","trusted_for_live_modelling",
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

def key(row):
    return "|".join([
        val(row, "race_date"),
        val(row, "track"),
        val(row, "race_no"),
        norm(val(row, "horse")),
    ])

def race_key(row):
    return "|".join([val(row, "race_date"), val(row, "track"), val(row, "race_no")])

def num(row, name):
    try:
        s = val(row, name).replace("$", "").replace(",", "")
        if not s or s == "-":
            return 0.0
        return float(s)
    except Exception:
        return 0.0

def risk_factor(shape_risk, cluster_risk):
    penalty = 0.0
    if shape_risk == "HIGH":
        penalty += 0.035
    elif shape_risk == "MEDIUM_HIGH":
        penalty += 0.025
    elif shape_risk == "MEDIUM":
        penalty += 0.015

    if cluster_risk in {"EXTREME"}:
        penalty += 0.06
    elif cluster_risk in {"HIGH"}:
        penalty += 0.04
    elif cluster_risk in {"MEDIUM"}:
        penalty += 0.02
    elif cluster_risk in {"LOW_MEDIUM"}:
        penalty += 0.01

    return penalty

def realism_grade(real_gap, prob, price):
    if price <= 0:
        return "NO_PRICE", "NO_MARKET_PRICE", "NO_ACTION"
    if real_gap >= 0.08 and prob <= 0.35:
        return "A", "REALISTIC_SECTIONAL_VALUE", "SANDBOX_WATCHLIST_REALISTIC_A"
    if real_gap >= 0.045 and prob <= 0.30:
        return "B", "PLAUSIBLE_SECTIONAL_VALUE", "SANDBOX_WATCHLIST_REALISTIC_B"
    if real_gap >= 0.02:
        return "C", "MARGINAL_SECTIONAL_VALUE", "SANDBOX_MONITOR_REALISTIC"
    if real_gap <= -0.05:
        return "F", "OVERSTATED_OR_NEGATIVE_VALUE", "SUPPRESS_REALISM_FAIL"
    return "D", "NO_REALISTIC_VALUE_EDGE", "NO_ACTION"

def main():
    cal = read_csv(IN_CAL)
    compare = {key(r): r for r in read_csv(IN_COMPARE)}
    edge = {key(r): r for r in read_csv(IN_EDGE)}
    cluster = {key(r): r for r in read_csv(IN_CLUSTER)}
    shapes = {race_key(r): r for r in read_csv(IN_SHAPE)}

    out = []

    for r in cal:
        k = key(r)
        rk = race_key(r)

        c = compare.get(k, {})
        e = edge.get(k, {})
        cl = cluster.get(k, {})
        sh = shapes.get(rk, {})

        fit = num(r, "sectional_fit_score")
        price = num(r, "market_price")
        market_prob = round(1 / price, 4) if price > 0 else 0.0

        raw_prob = round(fit / 100, 4)

        field_size = int(num(sh, "field_size") or 10)
        base_rate = round(1 / field_size, 4) if field_size > 0 else 0.10

        field_penalty = min(0.18, max(0.0, (field_size - 8) * 0.01))
        risk_pen = risk_factor(val(sh, "race_shape_risk"), val(cl, "cluster_risk"))

        volatility_pen = 0.0
        if val(cl, "cluster_family") in {"VOLATILITY", "COLLAPSE"}:
            volatility_pen += 0.07
        elif val(cl, "cluster_family") == "PRESSURE_ATTACK":
            volatility_pen += 0.025

        longshot_pen = 0.0
        if price >= 20:
            longshot_pen = 0.08
        elif price >= 12:
            longshot_pen = 0.045
        elif price >= 8:
            longshot_pen = 0.025

        entropy_pen = 0.04 if val(sh, "race_shape_risk") == "HIGH" else 0.02

        compressed_edge_prob = base_rate + ((raw_prob - base_rate) * 0.18)
        realistic_prob = compressed_edge_prob - field_penalty - risk_pen - volatility_pen - longshot_pen - entropy_pen
        realistic_prob = max(0.01, min(0.40, realistic_prob))
        realistic_prob = round(realistic_prob, 4)

        realistic_gap = round(realistic_prob - market_prob, 4)

        grade, label, action = realism_grade(realistic_gap, realistic_prob, price)

        out.append({
            "race_date": val(r, "race_date"),
            "track": val(r, "track"),
            "race_no": val(r, "race_no"),
            "horse": val(r, "horse"),
            "calibration_grade": val(r, "calibration_grade"),
            "sectional_fit_score": fit,
            "market_price": price if price > 0 else "-",
            "raw_sectional_prob": raw_prob,
            "market_implied_prob": market_prob,
            "field_size": field_size,
            "race_shape_risk": val(sh, "race_shape_risk"),
            "cluster_family": val(cl, "cluster_family"),
            "cluster_risk": val(cl, "cluster_risk"),
            "base_rate_prob": base_rate,
            "field_size_penalty": round(field_penalty, 4),
            "risk_penalty": round(risk_pen, 4),
            "volatility_penalty": round(volatility_pen, 4),
            "longshot_penalty": round(longshot_pen, 4),
            "entropy_penalty": round(entropy_pen, 4),
            "realistic_sectional_prob": realistic_prob,
            "realistic_market_gap": realistic_gap,
            "probability_realism_grade": grade,
            "probability_realism_label": label,
            "realism_action": action,
            "trusted_for_live_modelling": "NO",
            "trusted_for_live_execution": "NO",
            "notes": "Probability realism sandbox only. No live pricing/execution impact.",
        })

    with OUT_REALISM.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)

    grades = Counter(r["probability_realism_grade"] for r in out)
    labels = Counter(r["probability_realism_label"] for r in out)
    actions = Counter(r["realism_action"] for r in out)

    summary = []
    summary.append({"metric": "realism_rows", "value": len(out)})
    summary.append({"metric": "realistic_a_b_rows", "value": grades.get("A", 0) + grades.get("B", 0)})
    summary.append({"metric": "live_modelling_yes", "value": 0})
    summary.append({"metric": "live_execution_yes", "value": 0})

    for k, v in grades.most_common():
        summary.append({"metric": f"grade::{k}", "value": v})
    for k, v in labels.most_common():
        summary.append({"metric": f"label::{k}", "value": v})
    for k, v in actions.most_common():
        summary.append({"metric": f"action::{k}", "value": v})

    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("=" * 88)
    print("EDGEIQ SECTIONAL PROBABILITY REALISM ENGINE V1")
    print("=" * 88)
    print(f"realism rows built: {len(out)}")
    print(f"realistic A/B rows: {grades.get('A', 0) + grades.get('B', 0)}")
    print(f"saved: {OUT_REALISM}")
    print(f"saved: {OUT_SUMMARY}")
    print("grades:")
    for k, v in grades.most_common():
        print(f"  {k}: {v}")
    print("actions:")
    for k, v in actions.most_common():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
