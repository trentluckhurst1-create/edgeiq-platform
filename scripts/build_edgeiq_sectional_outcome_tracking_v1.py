import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "public" / "data"

IN_CAL = PUB / "edgeiq_sectional_signal_calibration_v1.csv"
IN_RESULTS = PUB / "race_results.csv"
IN_GRAPH = PUB / "edgeiq_canonical_market_entity_graph_v1.csv"

OUT_TRACK = PUB / "edgeiq_sectional_outcome_tracking_v1.csv"
OUT_SUMMARY = PUB / "edgeiq_sectional_outcome_tracking_summary_v1.csv"

FIELDS = [
    "race_date","track","race_no","horse",
    "calibrated_signal","calibration_grade","calibration_score",
    "market_price","rated_price","sectional_market_gap",
    "result_status","finish_position","winner_flag",
    "expected_value_bucket","clv_proxy",
    "outcome_grade","outcome_label",
    "validation_action",
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
        val(row, "race_date", "date", "meeting_date"),
        val(row, "track", "track_name", "meeting"),
        val(row, "race_no", "race_number"),
        norm(val(row, "horse", "horse_name", "runner_name")),
    ])

def num(v):
    try:
        s = str(v or "").replace("$", "").replace(",", "").strip()
        if not s or s == "-":
            return 0.0
        return float(s)
    except Exception:
        return 0.0

def result_position(row):
    for n in ["finish_position", "position", "place", "finishing_position", "result"]:
        raw = val(row, n)
        if raw:
            digits = "".join(ch for ch in raw if ch.isdigit())
            if digits:
                return int(digits)
    return 0

def ev_bucket(score, gap):
    if score >= 85 and gap >= 0.15:
        return "HIGH_EXPECTED_VALUE"
    if score >= 75 and gap >= 0.08:
        return "MEDIUM_EXPECTED_VALUE"
    if score >= 60 and gap >= 0.03:
        return "LOW_EXPECTED_VALUE"
    if score < 45:
        return "NEGATIVE_EXPECTED_VALUE"
    return "UNCLEAR_EXPECTED_VALUE"

def main():
    cal = read_csv(IN_CAL)
    results = read_csv(IN_RESULTS)
    graph = read_csv(IN_GRAPH)

    result_lookup = {key(r): r for r in results}
    graph_lookup = {key(r): r for r in graph}

    out = []

    for r in cal:
        k = key(r)
        res = result_lookup.get(k, {})
        g = graph_lookup.get(k, {})

        pos = result_position(res)
        winner = "YES" if pos == 1 else "NO"
        result_status = "RESULTED" if res else "PENDING_OR_NO_RESULT"

        score = num(val(r, "calibration_score"))
        gap = num(val(r, "sectional_market_gap"))
        market_price = num(val(r, "market_price"))
        rated_price = num(val(r, "rated_price"))

        bucket = ev_bucket(score, gap)

        clv_proxy = ""
        if market_price > 0 and rated_price > 0:
            clv_proxy = round((1 / rated_price) - (1 / market_price), 4)

        if result_status != "RESULTED":
            outcome_grade = "PENDING"
            outcome_label = "AWAITING_RESULT"
            action = "KEEP_IN_SHADOW_TRACKING"
        elif winner == "YES" and val(r, "calibration_grade") in {"A", "B"}:
            outcome_grade = "POSITIVE"
            outcome_label = "CALIBRATED_SIGNAL_WON"
            action = "RETAIN_AND_TRACK_SAMPLE"
        elif winner == "YES":
            outcome_grade = "MIXED"
            outcome_label = "LOW_GRADE_SIGNAL_WON"
            action = "MONITOR_FALSE_NEGATIVE"
        elif val(r, "calibration_grade") in {"A", "B"}:
            outcome_grade = "NEGATIVE"
            outcome_label = "HIGH_GRADE_SIGNAL_LOST"
            action = "REVIEW_CALIBRATION"
        else:
            outcome_grade = "NEUTRAL"
            outcome_label = "NO_SIGNIFICANT_OUTCOME"
            action = "NO_ACTION"

        out.append({
            "race_date": val(r, "race_date"),
            "track": val(r, "track"),
            "race_no": val(r, "race_no"),
            "horse": val(r, "horse"),
            "calibrated_signal": val(r, "calibrated_signal"),
            "calibration_grade": val(r, "calibration_grade"),
            "calibration_score": val(r, "calibration_score"),
            "market_price": val(r, "market_price"),
            "rated_price": val(r, "rated_price"),
            "sectional_market_gap": val(r, "sectional_market_gap"),
            "result_status": result_status,
            "finish_position": pos if pos else "",
            "winner_flag": winner,
            "expected_value_bucket": bucket,
            "clv_proxy": clv_proxy,
            "outcome_grade": outcome_grade,
            "outcome_label": outcome_label,
            "validation_action": action,
            "trusted_for_live_modelling": "NO",
            "trusted_for_live_execution": "NO",
            "notes": "Outcome tracking sandbox only. No live execution impact.",
        })

    with OUT_TRACK.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)

    grades = Counter(r["outcome_grade"] for r in out)
    labels = Counter(r["outcome_label"] for r in out)
    actions = Counter(r["validation_action"] for r in out)
    buckets = Counter(r["expected_value_bucket"] for r in out)

    summary = []
    summary.append({"metric": "outcome_rows", "value": len(out)})
    summary.append({"metric": "resulted_rows", "value": sum(1 for r in out if r["result_status"] == "RESULTED")})
    summary.append({"metric": "pending_rows", "value": sum(1 for r in out if r["result_status"] != "RESULTED")})
    summary.append({"metric": "a_b_rows", "value": sum(1 for r in out if r["calibration_grade"] in {"A", "B"})})
    summary.append({"metric": "a_b_winners", "value": sum(1 for r in out if r["calibration_grade"] in {"A", "B"} and r["winner_flag"] == "YES")})
    summary.append({"metric": "live_modelling_yes", "value": 0})
    summary.append({"metric": "live_execution_yes", "value": 0})

    for k, v in grades.most_common():
        summary.append({"metric": f"outcome_grade::{k}", "value": v})
    for k, v in labels.most_common():
        summary.append({"metric": f"outcome_label::{k}", "value": v})
    for k, v in actions.most_common():
        summary.append({"metric": f"action::{k}", "value": v})
    for k, v in buckets.most_common():
        summary.append({"metric": f"ev_bucket::{k}", "value": v})

    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("=" * 88)
    print("EDGEIQ SECTIONAL OUTCOME TRACKING ENGINE V1")
    print("=" * 88)
    print(f"outcome rows built: {len(out)}")
    print(f"resulted rows: {sum(1 for r in out if r['result_status'] == 'RESULTED')}")
    print(f"A/B rows: {sum(1 for r in out if r['calibration_grade'] in {'A', 'B'})}")
    print(f"A/B winners: {sum(1 for r in out if r['calibration_grade'] in {'A', 'B'} and r['winner_flag'] == 'YES')}")
    print(f"saved: {OUT_TRACK}")
    print(f"saved: {OUT_SUMMARY}")
    print("outcome grades:")
    for k, v in grades.most_common():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
