import csv
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "public" / "data"

INPUTS = [
    PUB / "edgeiq_canonical_split_schema_v1.csv",
    PUB / "edgeiq_sectional_payload_reconstruction_v1.csv",
    PUB / "edgeiq_sectional_physics_validation_v1.csv",
    PUB / "edgeiq_trusted_sectional_universe_v2.csv",
]

OUT_FEATURES = PUB / "edgeiq_real_sectional_physics_features_v1.csv"
OUT_SUMMARY = PUB / "edgeiq_real_sectional_physics_features_summary_v1.csv"

FIELDS = [
    "source_file","race_date","track","race_no","horse",
    "split_count","usable_numeric_count",
    "early_phase_value","mid_phase_value","late_phase_value",
    "acceleration_delta","late_retention_delta",
    "energy_decay_index","sectional_volatility",
    "measured_physics_grade","measured_physics_label",
    "feature_status","trusted_for_live_modelling",
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

def to_float(x):
    try:
        s = str(x or "").strip().replace("$", "").replace(",", "")
        if not s or s in {"-", "nan", "None"}:
            return None
        return float(s)
    except Exception:
        return None

def looks_split_col(name):
    n = name.lower()
    return any(k in n for k in [
        "split", "sectional", "600", "400", "200", "800",
        "time", "velocity", "speed", "last", "final"
    ])

def extract_numeric_payload(row):
    vals = []
    for k, v in row.items():
        if not looks_split_col(k):
            continue
        f = to_float(v)
        if f is not None and f > 0:
            vals.append((k, f))
    return vals

def phase_features(nums):
    values = [v for _, v in nums]
    if not values:
        return None

    values = values[:12]
    n = len(values)

    early = sum(values[:max(1, n//3)]) / max(1, len(values[:max(1, n//3)]))
    mid_slice = values[max(1, n//3):max(2, (2*n)//3)]
    late_slice = values[max(2, (2*n)//3):]

    mid = sum(mid_slice) / len(mid_slice) if mid_slice else early
    late = sum(late_slice) / len(late_slice) if late_slice else mid

    accel = late - early
    retention = late - mid
    decay = early - late
    mean = sum(values) / len(values)
    volatility = sum(abs(v - mean) for v in values) / len(values)

    return early, mid, late, accel, retention, decay, volatility

def grade_features(split_count, usable_count, accel, retention, decay, volatility):
    if usable_count < 3:
        return "F", "INSUFFICIENT_REAL_SPLITS", "BLOCKED_INSUFFICIENT_PAYLOAD"
    if volatility <= 0:
        return "D", "LOW_VARIANCE_OR_SCHEMA_RISK", "REVIEW_SCHEMA"
    if retention > 0 and decay < 0:
        return "A", "MEASURED_LATE_IMPROVER", "REAL_PHYSICS_SANDBOX"
    if retention >= -0.15 and decay <= 0.25:
        return "B", "MEASURED_ENERGY_HOLDER", "REAL_PHYSICS_SANDBOX"
    if decay > 0.75:
        return "F", "MEASURED_ENERGY_DECAY_RISK", "REAL_PHYSICS_NEGATIVE"
    return "C", "MEASURED_NEUTRAL_SECTIONAL_PROFILE", "REAL_PHYSICS_MONITOR"

def main():
    out = []

    for path in INPUTS:
        rows = read_csv(path)
        for r in rows:
            nums = extract_numeric_payload(r)
            features = phase_features(nums)

            if not features:
                continue

            early, mid, late, accel, retention, decay, volatility = features
            grade, label, status = grade_features(len(nums), len(nums), accel, retention, decay, volatility)

            out.append({
                "source_file": path.name,
                "race_date": val(r, "race_date", "date", "meeting_date"),
                "track": val(r, "track", "track_name", "meeting"),
                "race_no": val(r, "race_no", "race_number"),
                "horse": val(r, "horse", "horse_name", "runner_name", "sectional_runner"),
                "split_count": len(nums),
                "usable_numeric_count": len(nums),
                "early_phase_value": round(early, 4),
                "mid_phase_value": round(mid, 4),
                "late_phase_value": round(late, 4),
                "acceleration_delta": round(accel, 4),
                "late_retention_delta": round(retention, 4),
                "energy_decay_index": round(decay, 4),
                "sectional_volatility": round(volatility, 4),
                "measured_physics_grade": grade,
                "measured_physics_label": label,
                "feature_status": status,
                "trusted_for_live_modelling": "NO",
                "trusted_for_live_execution": "NO",
                "notes": "Measured real sectional physics sandbox only. No live pricing/execution impact.",
            })

    with OUT_FEATURES.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)

    grades = Counter(r["measured_physics_grade"] for r in out)
    labels = Counter(r["measured_physics_label"] for r in out)
    sources = Counter(r["source_file"] for r in out)

    summary = []
    summary.append({"metric": "real_physics_feature_rows", "value": len(out)})
    summary.append({"metric": "live_modelling_yes", "value": 0})
    summary.append({"metric": "live_execution_yes", "value": 0})

    for k, v in grades.most_common():
        summary.append({"metric": f"grade::{k}", "value": v})
    for k, v in labels.most_common():
        summary.append({"metric": f"label::{k}", "value": v})
    for k, v in sources.most_common():
        summary.append({"metric": f"source::{k}", "value": v})

    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("=" * 88)
    print("EDGEIQ REAL SECTIONAL PHYSICS FEATURE ENGINE V1")
    print("=" * 88)
    print(f"real physics feature rows built: {len(out)}")
    print(f"saved: {OUT_FEATURES}")
    print(f"saved: {OUT_SUMMARY}")
    print("grades:")
    for k, v in grades.most_common():
        print(f"  {k}: {v}")
    print("sources:")
    for k, v in sources.most_common():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
