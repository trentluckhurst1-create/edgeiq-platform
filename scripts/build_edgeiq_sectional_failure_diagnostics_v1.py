import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "public" / "data"

IN_OUTCOME = PUB / "edgeiq_sectional_outcome_tracking_v1.csv"
IN_CAL = PUB / "edgeiq_sectional_signal_calibration_v1.csv"
IN_COMPARE = PUB / "edgeiq_sectional_market_comparison_v2.csv"
IN_EDGE = PUB / "edgeiq_sectional_edge_detection_v1.csv"
IN_CLUSTER = PUB / "edgeiq_sectional_archetype_cluster_v1.csv"
IN_SHAPE = PUB / "edgeiq_race_shape_response_v1.csv"

OUT_FAIL = PUB / "edgeiq_sectional_failure_diagnostics_v1.csv"
OUT_SUMMARY = PUB / "edgeiq_sectional_failure_diagnostics_summary_v1.csv"
OUT_BACKLOG = PUB / "edgeiq_sectional_model_repair_backlog_v1.csv"

FAIL_FIELDS = [
    "race_date","track","race_no","horse",
    "calibration_grade","calibration_score","market_price",
    "sectional_fit_score","cluster_family","cluster_name",
    "race_shape_label","race_shape_risk",
    "outcome_label","finish_position","winner_flag",
    "failure_reason","failure_class","repair_priority",
    "recommended_repair","notes"
]

BACKLOG_FIELDS = [
    "priority","repair_category","failure_class","affected_rows",
    "recommended_repair","status","notes"
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

def num(row, name):
    try:
        s = val(row, name).replace("$", "").replace(",", "")
        if not s or s == "-":
            return 0.0
        return float(s)
    except Exception:
        return 0.0

def classify_failure(outcome, cal, compare, edge, cluster, shape):
    grade = val(outcome, "calibration_grade")
    if grade not in {"A", "B"}:
        return None

    if val(outcome, "winner_flag") == "YES":
        return None

    price = num(outcome, "market_price")
    fit = num(edge, "sectional_fit_score")
    gap = num(outcome, "sectional_market_gap")
    family = val(cluster, "cluster_family")
    shape_label = val(shape, "race_shape_label")
    shape_risk = val(shape, "race_shape_risk")
    comparison_label = val(compare, "market_comparison_label")

    if price >= 20:
        return (
            "LONG_PRICE_FALSE_SIGNAL",
            "PRICE_DISCIPLINE_FAILURE",
            "HIGH",
            "Add long-price liquidity and base-rate penalty before A/B promotion."
        )

    if gap >= 0.35:
        return (
            "OVERSTATED_MARKET_GAP",
            "CALIBRATION_OVERCONFIDENCE",
            "HIGH",
            "Tighten sectional_market_gap calibration and cap synthetic probability advantage."
        )

    if family in {"CLOSING_POWER", "ENERGY_SUSTAIN"} and "COLLAPSE" in shape_label:
        return (
            "SHAPE_ASSUMPTION_NOT_CONFIRMED",
            "RACE_SHAPE_MODEL_FAILURE",
            "HIGH",
            "Require post-race pace confirmation before reinforcing collapse/closer assumptions."
        )

    if shape_risk == "HIGH" and fit >= 85:
        return (
            "HIGH_RISK_SHAPE_OVERPROMOTION",
            "RISK_ADJUSTMENT_FAILURE",
            "MEDIUM",
            "Apply stronger penalty when shape instability is high."
        )

    if "PRIMARY_SECTIONAL_EDGE" in comparison_label:
        return (
            "PRIMARY_EDGE_NOT_PREDICTIVE",
            "EDGE_LABEL_FAILURE",
            "HIGH",
            "Recalibrate PRIMARY edge criteria using realised outcome evidence."
        )

    return (
        "UNEXPLAINED_A_B_FAILURE",
        "UNKNOWN_MODEL_FAILURE",
        "MEDIUM",
        "Add deeper feature attribution and post-race sectional validation."
    )

def main():
    outcome = read_csv(IN_OUTCOME)
    cal = {key(r): r for r in read_csv(IN_CAL)}
    compare = {key(r): r for r in read_csv(IN_COMPARE)}
    edge = {key(r): r for r in read_csv(IN_EDGE)}
    cluster = {key(r): r for r in read_csv(IN_CLUSTER)}
    shape = {
        "|".join([val(r, "race_date"), val(r, "track"), val(r, "race_no")]): r
        for r in read_csv(IN_SHAPE)
    }

    failures = []

    for r in outcome:
        k = key(r)
        race_k = "|".join([val(r, "race_date"), val(r, "track"), val(r, "race_no")])

        result = classify_failure(
            r,
            cal.get(k, {}),
            compare.get(k, {}),
            edge.get(k, {}),
            cluster.get(k, {}),
            shape.get(race_k, {}),
        )

        if not result:
            continue

        reason, fclass, priority, repair = result

        failures.append({
            "race_date": val(r, "race_date"),
            "track": val(r, "track"),
            "race_no": val(r, "race_no"),
            "horse": val(r, "horse"),
            "calibration_grade": val(r, "calibration_grade"),
            "calibration_score": val(r, "calibration_score"),
            "market_price": val(r, "market_price"),
            "sectional_fit_score": val(edge.get(k, {}), "sectional_fit_score"),
            "cluster_family": val(cluster.get(k, {}), "cluster_family"),
            "cluster_name": val(cluster.get(k, {}), "cluster_name"),
            "race_shape_label": val(shape.get(race_k, {}), "race_shape_label"),
            "race_shape_risk": val(shape.get(race_k, {}), "race_shape_risk"),
            "outcome_label": val(r, "outcome_label"),
            "finish_position": val(r, "finish_position"),
            "winner_flag": val(r, "winner_flag"),
            "failure_reason": reason,
            "failure_class": fclass,
            "repair_priority": priority,
            "recommended_repair": repair,
            "notes": "Failure diagnostic only. No live model changes applied.",
        })

    with OUT_FAIL.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FAIL_FIELDS)
        w.writeheader()
        w.writerows(failures)

    reasons = Counter(r["failure_reason"] for r in failures)
    classes = Counter(r["failure_class"] for r in failures)
    priorities = Counter(r["repair_priority"] for r in failures)

    backlog = []
    for fclass, count in classes.most_common():
        examples = [r for r in failures if r["failure_class"] == fclass]
        first = examples[0] if examples else {}
        priority = first.get("repair_priority", "MEDIUM")
        backlog.append({
            "priority": priority,
            "repair_category": fclass,
            "failure_class": fclass,
            "affected_rows": count,
            "recommended_repair": first.get("recommended_repair", ""),
            "status": "OPEN",
            "notes": "Generated from failed A/B sectional signals.",
        })

    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    backlog.sort(key=lambda r: (order.get(r["priority"], 9), -int(r["affected_rows"])))

    with OUT_BACKLOG.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=BACKLOG_FIELDS)
        w.writeheader()
        w.writerows(backlog)

    summary = []
    summary.append({"metric": "failed_ab_rows", "value": len(failures)})
    for k, v in reasons.most_common():
        summary.append({"metric": f"failure_reason::{k}", "value": v})
    for k, v in classes.most_common():
        summary.append({"metric": f"failure_class::{k}", "value": v})
    for k, v in priorities.most_common():
        summary.append({"metric": f"priority::{k}", "value": v})

    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("=" * 88)
    print("EDGEIQ SECTIONAL FAILURE DIAGNOSTICS V1")
    print("=" * 88)
    print(f"failed A/B rows diagnosed: {len(failures)}")
    print(f"repair backlog rows: {len(backlog)}")
    print(f"saved: {OUT_FAIL}")
    print(f"saved: {OUT_SUMMARY}")
    print(f"saved: {OUT_BACKLOG}")
    print("failure classes:")
    for k, v in classes.most_common():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
