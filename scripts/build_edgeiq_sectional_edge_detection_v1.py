import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "public" / "data"

IN_CLUSTERS = PUB / "edgeiq_sectional_archetype_cluster_v1.csv"
IN_SHAPES = PUB / "edgeiq_race_shape_response_v1.csv"

OUT_EDGE = PUB / "edgeiq_sectional_edge_detection_v1.csv"
OUT_SUMMARY = PUB / "edgeiq_sectional_edge_detection_summary_v1.csv"

FIELDS = [
    "race_date","track","race_no","horse",
    "cluster_name","cluster_family","cluster_risk",
    "race_shape_label","race_shape_risk",
    "best_suited_family","vulnerable_family",
    "sectional_fit_score","shape_advantage",
    "shape_vulnerability","sectional_edge_label",
    "sectional_edge_tier","sectional_edge_action",
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

def race_key(row):
    return (val(row, "race_date"), val(row, "track"), val(row, "race_no"))

def edge_score(cluster, shape):
    family = val(cluster, "cluster_family")
    risk = val(cluster, "cluster_risk")
    label = val(shape, "race_shape_label")
    best = val(shape, "best_suited_family")
    vulnerable = val(shape, "vulnerable_family")
    shape_risk = val(shape, "race_shape_risk")

    score = 50
    advantage = []
    vulnerability = []

    if family == best:
        score += 25
        advantage.append("MATCHES_BEST_SHAPE_FAMILY")

    if family == vulnerable:
        score -= 30
        vulnerability.append("MATCHES_VULNERABLE_FAMILY")

    if label == "PACE_COLLAPSE_WITH_CLOSER_OPPORTUNITY":
        if family == "CLOSING_POWER":
            score += 35
            advantage.append("CLOSER_IN_COLLAPSE_SHAPE")
        if family == "ENERGY_SUSTAIN":
            score += 15
            advantage.append("SUSTAINER_CAN_SURVIVE_COLLAPSE")
        if family in {"COLLAPSE", "VOLATILITY"}:
            score -= 25
            vulnerability.append("FRAGILE_IN_COLLAPSE_SHAPE")

    elif label == "PRESSURE_SUSTAIN_BATTLE":
        if family == "ENERGY_SUSTAIN":
            score += 30
            advantage.append("SUSTAINER_IN_PRESSURE_BATTLE")
        if family == "PRESSURE_ATTACK":
            score += 10
            advantage.append("PRESSURE_STYLE_RELEVANT")
        if family == "VOLATILITY":
            score -= 20
            vulnerability.append("VOLATILE_UNDER_PRESSURE")

    elif label == "FRAGILE_FIELD_COLLAPSE_RISK":
        if family in {"SURVIVAL", "ENERGY_SUSTAIN", "CLOSING_POWER"}:
            score += 25
            advantage.append("SURVIVES_FRAGILE_FIELD")
        if family == "COLLAPSE":
            score -= 35
            vulnerability.append("COLLAPSE_TYPE_IN_FRAGILE_FIELD")

    elif label == "UNSTABLE_VOLATILE_FIELD":
        if family in {"ENERGY_SUSTAIN", "SURVIVAL"}:
            score += 20
            advantage.append("STABILITY_EDGE_IN_VOLATILE_FIELD")
        if family == "VOLATILITY":
            score -= 30
            vulnerability.append("VOLATILE_IN_VOLATILE_FIELD")

    elif label == "LOW_PRESSURE_LATE_SPEED_RACE":
        if family == "CLOSING_POWER":
            score += 20
            advantage.append("LATE_SPEED_EDGE")
        if family == "PRESSURE_ATTACK":
            score -= 10
            vulnerability.append("PRESSURE_STYLE_MAY_BE_MUTED")

    if risk in {"EXTREME", "HIGH"}:
        score -= 10
        vulnerability.append("HIGH_CLUSTER_RISK")

    if shape_risk == "HIGH" and family in {"ENERGY_SUSTAIN", "CLOSING_POWER", "SURVIVAL"}:
        score += 5
        advantage.append("ROBUST_FAMILY_IN_HIGH_RISK_SHAPE")

    score = max(0, min(100, score))

    return score, "|".join(advantage), "|".join(vulnerability)

def tier(score):
    if score >= 85:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 45:
        return "D"
    return "F"

def label_for(score):
    if score >= 85:
        return "PRIMARY_SECTIONAL_EDGE"
    if score >= 75:
        return "SECONDARY_SECTIONAL_EDGE"
    if score >= 60:
        return "MONITOR_POSITIVE_SHAPE"
    if score >= 45:
        return "NEUTRAL_OR_NO_EDGE"
    return "NEGATIVE_SHAPE_MATCH"

def action_for(score):
    if score >= 85:
        return "WATCHLIST_ONLY_PRIMARY"
    if score >= 75:
        return "WATCHLIST_ONLY_SECONDARY"
    if score >= 60:
        return "MONITOR_ONLY"
    if score >= 45:
        return "NO_ACTION"
    return "NEGATIVE_MARK"

def main():
    clusters = read_csv(IN_CLUSTERS)
    shapes = read_csv(IN_SHAPES)

    shape_lookup = {race_key(r): r for r in shapes}

    out = []

    for c in clusters:
        s = shape_lookup.get(race_key(c))
        if not s:
            continue

        score, adv, vuln = edge_score(c, s)

        out.append({
            "race_date": val(c, "race_date"),
            "track": val(c, "track"),
            "race_no": val(c, "race_no"),
            "horse": val(c, "horse"),
            "cluster_name": val(c, "cluster_name"),
            "cluster_family": val(c, "cluster_family"),
            "cluster_risk": val(c, "cluster_risk"),
            "race_shape_label": val(s, "race_shape_label"),
            "race_shape_risk": val(s, "race_shape_risk"),
            "best_suited_family": val(s, "best_suited_family"),
            "vulnerable_family": val(s, "vulnerable_family"),
            "sectional_fit_score": score,
            "shape_advantage": adv,
            "shape_vulnerability": vuln,
            "sectional_edge_label": label_for(score),
            "sectional_edge_tier": tier(score),
            "sectional_edge_action": action_for(score),
            "trusted_for_live_modelling": "NO",
            "trusted_for_live_execution": "NO",
            "notes": "Sandbox edge detection only. No pricing/execution impact.",
        })

    with OUT_EDGE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)

    labels = Counter(r["sectional_edge_label"] for r in out)
    tiers = Counter(r["sectional_edge_tier"] for r in out)
    actions = Counter(r["sectional_edge_action"] for r in out)

    summary = []
    summary.append({"metric": "edge_rows", "value": len(out)})
    summary.append({"metric": "live_modelling_yes", "value": 0})
    summary.append({"metric": "live_execution_yes", "value": 0})

    for k, v in labels.most_common():
        summary.append({"metric": f"edge_label::{k}", "value": v})
    for k, v in tiers.most_common():
        summary.append({"metric": f"edge_tier::{k}", "value": v})
    for k, v in actions.most_common():
        summary.append({"metric": f"action::{k}", "value": v})

    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("=" * 88)
    print("EDGEIQ SECTIONAL EDGE DETECTION ENGINE V1")
    print("=" * 88)
    print(f"edge rows built: {len(out)}")
    print(f"saved: {OUT_EDGE}")
    print(f"saved: {OUT_SUMMARY}")
    print("edge labels:")
    for k, v in labels.most_common():
        print(f"  {k}: {v}")
    print("tiers:")
    for k, v in tiers.most_common():
        print(f"  {k}: {v}")
    print("actions:")
    for k, v in actions.most_common():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
