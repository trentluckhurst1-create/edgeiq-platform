import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "public" / "data"

IN_COMPARE = PUB / "edgeiq_sectional_market_comparison_v2.csv"

OUT_CALIBRATION = PUB / "edgeiq_sectional_signal_calibration_v1.csv"
OUT_SUMMARY = PUB / "edgeiq_sectional_signal_calibration_summary_v1.csv"

FIELDS = [
    "race_date","track","race_no","horse",
    "sectional_edge_label","sectional_edge_tier","sectional_fit_score",
    "market_price","market_implied_prob","sectional_market_gap",
    "raw_sectional_value_signal","market_comparison_label",
    "raw_sandbox_action","calibrated_signal",
    "calibration_grade","calibration_score",
    "realism_filter","false_edge_risk",
    "calibrated_action",
    "trusted_for_live_modelling","trusted_for_live_execution",
    "notes"
]

def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def val(row, name):
    return str(row.get(name, "") or "").strip()

def num(row, name):
    try:
        s = val(row, name).replace("$", "").replace(",", "")
        if not s or s == "-":
            return 0.0
        return float(s)
    except Exception:
        return 0.0

def calibrate(row):
    score = num(row, "sectional_fit_score")
    price = num(row, "market_price")
    gap = num(row, "sectional_market_gap")
    edge_tier = val(row, "sectional_edge_tier")
    label = val(row, "market_comparison_label")
    trusted = val(row, "trusted_market_link")

    cal_score = 0
    filters = []
    risks = []

    if trusted == "YES":
        cal_score += 25
    else:
        risks.append("NO_TRUSTED_MARKET_LINK")

    if edge_tier in {"A", "B"}:
        cal_score += 25
    elif edge_tier == "C":
        cal_score += 10
    else:
        risks.append("WEAK_SECTIONAL_EDGE_TIER")

    if price >= 5:
        cal_score += 15
    elif price > 0:
        cal_score += 5
        filters.append("SHORT_PRICE_FILTER")
    else:
        risks.append("NO_MARKET_PRICE")

    if gap >= 0.15:
        cal_score += 20
    elif gap >= 0.08:
        cal_score += 12
    elif gap >= 0.03:
        cal_score += 5
    elif gap < 0:
        risks.append("NEGATIVE_MARKET_GAP")

    if label in {
        "PRIMARY_SECTIONAL_EDGE_BIG_PRICE",
        "PRIMARY_SECTIONAL_EDGE_PRICE_ROOM",
        "SECONDARY_SECTIONAL_EDGE_PRICE_ROOM",
    }:
        cal_score += 15
    elif "NEGATIVE" in label:
        risks.append("NEGATIVE_SHAPE_OR_MARKET_LABEL")

    if score >= 90 and gap > 0.45:
        filters.append("EXTREME_GAP_REALISM_CAP")
        cal_score -= 20

    if price >= 20 and gap >= 0.40:
        filters.append("LONG_PRICE_LIQUIDITY_CAUTION")
        cal_score -= 10

    cal_score = max(0, min(100, cal_score))

    if cal_score >= 85:
        calibrated = "A_CALIBRATED_SECTIONAL_VALUE"
        grade = "A"
        action = "SANDBOX_WATCHLIST_PRIMARY"
    elif cal_score >= 75:
        calibrated = "B_CALIBRATED_SECTIONAL_VALUE"
        grade = "B"
        action = "SANDBOX_WATCHLIST_SECONDARY"
    elif cal_score >= 60:
        calibrated = "C_MONITOR_SECTIONAL_VALUE"
        grade = "C"
        action = "SANDBOX_MONITOR"
    elif cal_score >= 45:
        calibrated = "D_UNCLEAR_OR_PRICE_SENSITIVE"
        grade = "D"
        action = "NO_ACTION"
    else:
        calibrated = "F_FALSE_OR_WEAK_SECTIONAL_SIGNAL"
        grade = "F"
        action = "SUPPRESS_SANDBOX_SIGNAL"

    if not filters:
        filters.append("PASSED_BASIC_REALISM_FILTER")
    if not risks:
        risks.append("LOW_FALSE_EDGE_RISK")

    return calibrated, grade, cal_score, "|".join(filters), "|".join(risks), action

def main():
    rows = read_csv(IN_COMPARE)
    out = []

    for r in rows:
        calibrated, grade, cal_score, realism, risk, action = calibrate(r)

        out.append({
            "race_date": val(r, "race_date"),
            "track": val(r, "track"),
            "race_no": val(r, "race_no"),
            "horse": val(r, "horse"),
            "sectional_edge_label": val(r, "sectional_edge_label"),
            "sectional_edge_tier": val(r, "sectional_edge_tier"),
            "sectional_fit_score": val(r, "sectional_fit_score"),
            "market_price": val(r, "market_price"),
            "market_implied_prob": val(r, "market_implied_prob"),
            "sectional_market_gap": val(r, "sectional_market_gap"),
            "raw_sectional_value_signal": val(r, "sectional_value_signal"),
            "market_comparison_label": val(r, "market_comparison_label"),
            "raw_sandbox_action": val(r, "sandbox_action"),
            "calibrated_signal": calibrated,
            "calibration_grade": grade,
            "calibration_score": cal_score,
            "realism_filter": realism,
            "false_edge_risk": risk,
            "calibrated_action": action,
            "trusted_for_live_modelling": "NO",
            "trusted_for_live_execution": "NO",
            "notes": "Calibration sandbox only. No live pricing/execution impact.",
        })

    with OUT_CALIBRATION.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)

    signals = Counter(r["calibrated_signal"] for r in out)
    grades = Counter(r["calibration_grade"] for r in out)
    actions = Counter(r["calibrated_action"] for r in out)
    risks = Counter()
    filters = Counter()

    for r in out:
        for x in r["false_edge_risk"].split("|"):
            if x:
                risks[x] += 1
        for x in r["realism_filter"].split("|"):
            if x:
                filters[x] += 1

    summary = []
    summary.append({"metric": "calibration_rows", "value": len(out)})
    summary.append({"metric": "live_modelling_yes", "value": 0})
    summary.append({"metric": "live_execution_yes", "value": 0})
    summary.append({"metric": "calibrated_a_b_rows", "value": grades.get("A", 0) + grades.get("B", 0)})

    for k, v in signals.most_common():
        summary.append({"metric": f"signal::{k}", "value": v})
    for k, v in grades.most_common():
        summary.append({"metric": f"grade::{k}", "value": v})
    for k, v in actions.most_common():
        summary.append({"metric": f"action::{k}", "value": v})
    for k, v in risks.most_common():
        summary.append({"metric": f"risk::{k}", "value": v})
    for k, v in filters.most_common():
        summary.append({"metric": f"filter::{k}", "value": v})

    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("=" * 88)
    print("EDGEIQ SECTIONAL SIGNAL CALIBRATION ENGINE V1")
    print("=" * 88)
    print(f"calibration rows built: {len(out)}")
    print(f"calibrated A/B rows: {grades.get('A', 0) + grades.get('B', 0)}")
    print(f"saved: {OUT_CALIBRATION}")
    print(f"saved: {OUT_SUMMARY}")
    print("calibrated signals:")
    for k, v in signals.most_common():
        print(f"  {k}: {v}")
    print("grades:")
    for k, v in grades.most_common():
        print(f"  {k}: {v}")
    print("actions:")
    for k, v in actions.most_common():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
