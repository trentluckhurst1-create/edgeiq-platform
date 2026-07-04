import csv
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "public" / "data"

IN_FEATURES = PUB / "edgeiq_sectional_feature_engine_v1.csv"

OUT_CLUSTERS = PUB / "edgeiq_sectional_archetype_cluster_v1.csv"
OUT_SUMMARY = PUB / "edgeiq_sectional_archetype_cluster_summary_v1.csv"

FIELDS = [
    "race_date","track","race_no","horse",
    "feature_archetype","feature_confidence",
    "cluster_id","cluster_name","cluster_family",
    "cluster_strength","cluster_risk","cluster_style",
    "pace_response","late_response","pressure_response",
    "cluster_modelling_status","trusted_for_live_modelling",
    "trusted_for_live_execution","notes"
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
        return float(val(row, name))
    except Exception:
        return 0.0

def cluster_for(row):
    arch = val(row, "feature_archetype")
    accel = num(row, "acceleration_index")
    late = num(row, "late_speed_index")
    retain = num(row, "energy_retention_index")
    pressure = num(row, "pressure_resistance_index")
    elasticity = num(row, "pace_elasticity_index")
    collapse = num(row, "collapse_risk_index")
    volatility = num(row, "sectional_volatility_index")
    closing = num(row, "closing_efficiency_index")
    sustain = num(row, "midrace_sustain_index")
    comp = num(row, "feature_composite")

    if arch == "EXPLOSIVE_CLOSER":
        return ("C01", "Explosive Late Closer", "CLOSING_POWER", "HIGH", "LOW", "LATE_SURGE", "NEEDS_PACE_ON", "EXPLOSIVE", "ABSORBS")
    if arch == "SUSTAINED_ENGINE":
        return ("C02", "Sustained Engine", "ENERGY_SUSTAIN", "HIGH", "LOW_MEDIUM", "GRINDER", "VERSATILE", "SUSTAINED", "ABSORBS")
    if arch == "HIGH_PRESSURE_MOVER":
        return ("C03", "High Pressure Mover", "PRESSURE_ATTACK", "MEDIUM_HIGH", "MEDIUM", "FORWARD_PRESS", "PRESSURE_POSITIVE", "STRONG", "APPLIES")
    if arch == "ENERGY_COLLAPSE_RISK":
        if collapse >= 90 or volatility >= 85:
            return ("C04A", "Severe Collapse Risk", "COLLAPSE", "LOW", "EXTREME", "FRAGILE", "PACE_NEGATIVE", "WEAK", "FAILS")
        return ("C04B", "Moderate Collapse Risk", "COLLAPSE", "LOW_MEDIUM", "HIGH", "FRAGILE", "PACE_NEGATIVE", "LIMITED", "FAILS")
    if arch == "MIDPACE_SURVIVOR":
        return ("C05", "Midrace Survivor", "SURVIVAL", "MEDIUM", "MEDIUM", "SURVIVOR", "NEEDS_EVEN_TEMPO", "STEADY", "SURVIVES")
    if arch == "BALANCED_PRESSURE_PROFILE":
        return ("C06", "Balanced Pressure Profile", "BALANCED", "MEDIUM_HIGH", "MEDIUM_LOW", "BALANCED", "VERSATILE", "BALANCED", "HOLDS")
    if comp >= 70 and collapse <= 55 and sustain >= 70:
        return ("C07", "Hidden Sustainer", "ENERGY_SUSTAIN", "MEDIUM", "MEDIUM", "GRINDER", "VERSATILE", "STEADY", "HOLDS")
    if late >= 75 and closing >= 75 and collapse <= 65:
        return ("C08", "Late Efficiency Type", "CLOSING_POWER", "MEDIUM", "MEDIUM", "LATE_EFFICIENT", "NEEDS_COVER", "GOOD", "HOLDS")
    return ("C09", "Unstable Volatile Type", "VOLATILITY", "LOW", "HIGH", "UNSTABLE", "PACE_UNCLEAR", "UNKNOWN", "UNKNOWN")

def main():
    rows = read_csv(IN_FEATURES)
    out = []

    for r in rows:
        cid, cname, family, strength, risk, style, pace, late, pressure = cluster_for(r)

        out.append({
            "race_date": val(r, "race_date"),
            "track": val(r, "track"),
            "race_no": val(r, "race_no"),
            "horse": val(r, "horse"),
            "feature_archetype": val(r, "feature_archetype"),
            "feature_confidence": val(r, "feature_confidence"),
            "cluster_id": cid,
            "cluster_name": cname,
            "cluster_family": family,
            "cluster_strength": strength,
            "cluster_risk": risk,
            "cluster_style": style,
            "pace_response": pace,
            "late_response": late,
            "pressure_response": pressure,
            "cluster_modelling_status": "SANDBOX_ONLY",
            "trusted_for_live_modelling": "NO",
            "trusted_for_live_execution": "NO",
            "notes": "Cluster sandbox only. No live pricing/execution impact.",
        })

    with OUT_CLUSTERS.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)

    clusters = Counter(r["cluster_name"] for r in out)
    families = Counter(r["cluster_family"] for r in out)
    risks = Counter(r["cluster_risk"] for r in out)

    summary = []
    summary.append({"metric": "cluster_rows", "value": len(out)})
    summary.append({"metric": "live_modelling_yes", "value": 0})
    summary.append({"metric": "live_execution_yes", "value": 0})

    for k, v in clusters.most_common():
        summary.append({"metric": f"cluster::{k}", "value": v})
    for k, v in families.most_common():
        summary.append({"metric": f"family::{k}", "value": v})
    for k, v in risks.most_common():
        summary.append({"metric": f"risk::{k}", "value": v})

    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("=" * 88)
    print("EDGEIQ SECTIONAL ARCHETYPE CLUSTER ENGINE V1")
    print("=" * 88)
    print(f"cluster rows built: {len(out)}")
    print(f"saved: {OUT_CLUSTERS}")
    print(f"saved: {OUT_SUMMARY}")
    print("clusters:")
    for k, v in clusters.most_common():
        print(f"  {k}: {v}")
    print("families:")
    for k, v in families.most_common():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
