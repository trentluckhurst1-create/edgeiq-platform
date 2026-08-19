import csv
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "public" / "data"

IN_CLUSTERS = PUB / "edgeiq_sectional_archetype_cluster_v1.csv"

OUT_RESPONSE = PUB / "edgeiq_race_shape_response_v1.csv"
OUT_SUMMARY = PUB / "edgeiq_race_shape_response_summary_v1.csv"

FIELDS = [
    "race_date","track","race_no",
    "field_size","volatility_count","collapse_count",
    "pressure_attack_count","energy_sustain_count",
    "survival_count","closing_power_count",
    "pace_pressure_index","collapse_pressure_index",
    "late_opportunity_index","shape_instability_index",
    "race_shape_label","race_shape_risk",
    "best_suited_family","vulnerable_family",
    "shape_modelling_status",
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

def main():
    rows = read_csv(IN_CLUSTERS)

    grouped = defaultdict(list)
    for r in rows:
        grouped[race_key(r)].append(r)

    out = []

    for (race_date, track, race_no), rs in grouped.items():
        field_size = len(rs)
        fam = Counter(val(r, "cluster_family") for r in rs)

        volatility = fam.get("VOLATILITY", 0)
        collapse = fam.get("COLLAPSE", 0)
        pressure = fam.get("PRESSURE_ATTACK", 0)
        sustain = fam.get("ENERGY_SUSTAIN", 0)
        survival = fam.get("SURVIVAL", 0)
        closing = fam.get("CLOSING_POWER", 0)

        if field_size <= 0:
            continue

        pace_pressure = round(((pressure * 18) + (volatility * 5) + (collapse * 4)) / field_size, 2)
        collapse_pressure = round(((collapse * 18) + (volatility * 9) + (pressure * 5)) / field_size, 2)
        late_opportunity = round(((collapse * 12) + (pressure * 8) + (closing * 18) + (sustain * 6)) / field_size, 2)
        instability = round(((volatility * 16) + (collapse * 12) + (pressure * 7)) / field_size, 2)

        if pressure >= 2 and collapse >= 3 and closing >= 1:
            label = "PACE_COLLAPSE_WITH_CLOSER_OPPORTUNITY"
            risk = "HIGH"
            best = "CLOSING_POWER"
            vulnerable = "COLLAPSE"
        elif pressure >= 2 and sustain >= 2:
            label = "PRESSURE_SUSTAIN_BATTLE"
            risk = "MEDIUM_HIGH"
            best = "ENERGY_SUSTAIN"
            vulnerable = "VOLATILITY"
        elif collapse >= max(3, field_size // 3):
            label = "FRAGILE_FIELD_COLLAPSE_RISK"
            risk = "HIGH"
            best = "SURVIVAL"
            vulnerable = "COLLAPSE"
        elif closing >= 2 and pressure <= 1:
            label = "LOW_PRESSURE_LATE_SPEED_RACE"
            risk = "MEDIUM"
            best = "CLOSING_POWER"
            vulnerable = "VOLATILITY"
        elif volatility >= max(3, field_size // 3):
            label = "UNSTABLE_VOLATILE_FIELD"
            risk = "HIGH"
            best = "BALANCED"
            vulnerable = "VOLATILITY"
        elif sustain + survival >= max(3, field_size // 2):
            label = "EVEN_TEMPO_SURVIVAL_RACE"
            risk = "LOW_MEDIUM"
            best = "ENERGY_SUSTAIN"
            vulnerable = "COLLAPSE"
        else:
            label = "MIXED_SHAPE_UNCLEAR"
            risk = "MEDIUM"
            best = "BALANCED"
            vulnerable = "UNKNOWN"

        out.append({
            "race_date": race_date,
            "track": track,
            "race_no": race_no,
            "field_size": field_size,
            "volatility_count": volatility,
            "collapse_count": collapse,
            "pressure_attack_count": pressure,
            "energy_sustain_count": sustain,
            "survival_count": survival,
            "closing_power_count": closing,
            "pace_pressure_index": pace_pressure,
            "collapse_pressure_index": collapse_pressure,
            "late_opportunity_index": late_opportunity,
            "shape_instability_index": instability,
            "race_shape_label": label,
            "race_shape_risk": risk,
            "best_suited_family": best,
            "vulnerable_family": vulnerable,
            "shape_modelling_status": "SANDBOX_ONLY",
            "trusted_for_live_modelling": "NO",
            "trusted_for_live_execution": "NO",
            "notes": "Race shape response sandbox only. No live pricing/execution impact.",
        })

    with OUT_RESPONSE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)

    labels = Counter(r["race_shape_label"] for r in out)
    risks = Counter(r["race_shape_risk"] for r in out)
    bests = Counter(r["best_suited_family"] for r in out)

    summary = []
    summary.append({"metric": "race_shape_rows", "value": len(out)})
    summary.append({"metric": "live_modelling_yes", "value": 0})
    summary.append({"metric": "live_execution_yes", "value": 0})

    for k, v in labels.most_common():
        summary.append({"metric": f"shape::{k}", "value": v})
    for k, v in risks.most_common():
        summary.append({"metric": f"risk::{k}", "value": v})
    for k, v in bests.most_common():
        summary.append({"metric": f"best_suited_family::{k}", "value": v})

    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("=" * 88)
    print("EDGEIQ RACE SHAPE RESPONSE ENGINE V1")
    print("=" * 88)
    print(f"race shape rows built: {len(out)}")
    print(f"saved: {OUT_RESPONSE}")
    print(f"saved: {OUT_SUMMARY}")
    print("race shapes:")
    for k, v in labels.most_common():
        print(f"  {k}: {v}")
    print("risk:")
    for k, v in risks.most_common():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
