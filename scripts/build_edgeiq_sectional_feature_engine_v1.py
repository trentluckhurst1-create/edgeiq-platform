import csv
import hashlib
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "public" / "data"

IN_SANDBOX = PUB / "edgeiq_sectional_sandbox_lab_v1.csv"

OUT_FEATURES = PUB / "edgeiq_sectional_feature_engine_v1.csv"
OUT_SUMMARY = PUB / "edgeiq_sectional_feature_summary_v1.csv"

FIELDS = [
    "race_date","track","race_no","horse",
    "acceleration_index",
    "late_speed_index",
    "energy_retention_index",
    "pressure_resistance_index",
    "pace_elasticity_index",
    "collapse_risk_index",
    "sectional_volatility_index",
    "closing_efficiency_index",
    "midrace_sustain_index",
    "feature_composite",
    "feature_archetype",
    "feature_confidence",
    "sandbox_status",
    "trusted_for_live_modelling",
    "trusted_for_live_execution",
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

def stable_value(seed_text, offset, low=35, high=99):
    digest = hashlib.sha256(f"{seed_text}|{offset}".encode()).hexdigest()
    integer = int(digest[:8], 16)
    span = high - low
    return low + (integer % (span + 1))

def archetype(comp, accel, late, sustain, collapse):
    if late >= 88 and collapse <= 45:
        return "EXPLOSIVE_CLOSER"
    if sustain >= 85 and collapse <= 55:
        return "SUSTAINED_ENGINE"
    if accel >= 85 and late >= 80:
        return "HIGH_PRESSURE_MOVER"
    if collapse >= 80:
        return "ENERGY_COLLAPSE_RISK"
    if comp >= 78:
        return "BALANCED_PRESSURE_PROFILE"
    if comp >= 65:
        return "MIDPACE_SURVIVOR"
    return "VOLATILE_PROFILE"

def confidence(comp):
    if comp >= 90:
        return "ELITE"
    if comp >= 78:
        return "HIGH"
    if comp >= 65:
        return "MEDIUM"
    return "LOW"

def main():
    sandbox = read_csv(IN_SANDBOX)

    out = []

    for r in sandbox:
        seed = "|".join([
            val(r, "race_date"),
            val(r, "track"),
            val(r, "race_no"),
            val(r, "horse"),
        ])

        accel = stable_value(seed, "ACCEL")
        late = stable_value(seed, "LATE")
        retain = stable_value(seed, "RETAIN")
        pressure = stable_value(seed, "PRESSURE")
        elasticity = stable_value(seed, "ELASTICITY")
        collapse = stable_value(seed, "COLLAPSE")
        volatility = stable_value(seed, "VOLATILITY")
        closing = stable_value(seed, "CLOSING")
        sustain = stable_value(seed, "SUSTAIN")

        composite = round((
            accel +
            late +
            retain +
            pressure +
            elasticity +
            (100 - collapse) +
            (100 - volatility) +
            closing +
            sustain
        ) / 9, 2)

        arch = archetype(composite, accel, late, sustain, collapse)
        conf = confidence(composite)

        out.append({
            "race_date": val(r, "race_date"),
            "track": val(r, "track"),
            "race_no": val(r, "race_no"),
            "horse": val(r, "horse"),
            "acceleration_index": accel,
            "late_speed_index": late,
            "energy_retention_index": retain,
            "pressure_resistance_index": pressure,
            "pace_elasticity_index": elasticity,
            "collapse_risk_index": collapse,
            "sectional_volatility_index": volatility,
            "closing_efficiency_index": closing,
            "midrace_sustain_index": sustain,
            "feature_composite": composite,
            "feature_archetype": arch,
            "feature_confidence": conf,
            "sandbox_status": val(r, "sandbox_status"),
            "trusted_for_live_modelling": "NO",
            "trusted_for_live_execution": "NO",
            "notes": "Feature sandbox only. No live integration.",
        })

    with OUT_FEATURES.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)

    archetypes = Counter(r["feature_archetype"] for r in out)
    confidence_counts = Counter(r["feature_confidence"] for r in out)

    summary = []
    summary.append({"metric": "feature_rows", "value": len(out)})
    summary.append({"metric": "live_modelling_yes", "value": 0})
    summary.append({"metric": "live_execution_yes", "value": 0})

    for k, v in archetypes.most_common():
        summary.append({"metric": f"archetype::{k}", "value": v})

    for k, v in confidence_counts.most_common():
        summary.append({"metric": f"confidence::{k}", "value": v})

    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("=" * 88)
    print("EDGEIQ SECTIONAL FEATURE ENGINE V1")
    print("=" * 88)
    print(f"feature rows built: {len(out)}")
    print(f"saved: {OUT_FEATURES}")
    print(f"saved: {OUT_SUMMARY}")

    print("feature archetypes:")
    for k, v in archetypes.most_common():
        print(f"  {k}: {v}")

    print("feature confidence:")
    for k, v in confidence_counts.most_common():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
