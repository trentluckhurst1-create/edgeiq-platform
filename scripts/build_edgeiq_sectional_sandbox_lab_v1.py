import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "public" / "data"

IN_SHADOW = PUB / "edgeiq_shadow_validation_engine_v1.csv"
IN_TRUSTED = PUB / "edgeiq_trusted_sectional_universe_v2.csv"

OUT_SANDBOX = PUB / "edgeiq_sectional_sandbox_lab_v1.csv"
OUT_SUMMARY = PUB / "edgeiq_sectional_sandbox_summary_v1.csv"

FIELDS = [
    "race_date","track","race_no","horse",
    "validation_grade","trust_level",
    "acceleration_signature",
    "late_speed_profile",
    "energy_retention_profile",
    "tempo_survivability",
    "finish_pressure_profile",
    "pace_compression_profile",
    "sectional_archetype",
    "sandbox_confidence",
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

def classify_archetype(score):
    if score >= 90:
        return "ELITE_CLOSER"
    if score >= 80:
        return "SUSTAINED_FINISHER"
    if score >= 70:
        return "PRESSURE_RESISTANT"
    if score >= 60:
        return "MIDPACE_SURVIVOR"
    return "UNCLASSIFIED"

def main():
    shadow = read_csv(IN_SHADOW)
    trusted = read_csv(IN_TRUSTED)

    trusted_lookup = {
        (
            val(r, "race_date"),
            val(r, "track"),
            val(r, "race_no"),
            val(r, "horse"),
        ): r
        for r in trusted
    }

    out = []

    for r in shadow:
        if val(r, "validation_grade") != "ELITE_STABLE":
            continue

        key = (
            val(r, "race_date"),
            val(r, "track"),
            val(r, "race_no"),
            val(r, "horse"),
        )

        trusted_row = trusted_lookup.get(key)
        if not trusted_row:
            continue

        validation_score = float(val(r, "validation_score") or 0)

        acceleration = min(100, validation_score + 5)
        late_speed = min(100, validation_score + 3)
        energy_retention = min(100, validation_score + 1)
        survivability = min(100, validation_score)
        pressure = min(100, validation_score - 2)
        compression = min(100, validation_score - 4)

        composite = (
            acceleration +
            late_speed +
            energy_retention +
            survivability +
            pressure +
            compression
        ) / 6

        archetype = classify_archetype(composite)

        if composite >= 90:
            confidence = "ELITE"
            status = "SANDBOX_STABLE"
        elif composite >= 75:
            confidence = "HIGH"
            status = "SANDBOX_STABLE"
        else:
            confidence = "MONITOR"
            status = "SANDBOX_REVIEW"

        out.append({
            "race_date": val(r, "race_date"),
            "track": val(r, "track"),
            "race_no": val(r, "race_no"),
            "horse": val(r, "horse"),
            "validation_grade": val(r, "validation_grade"),
            "trust_level": val(trusted_row, "trust_level"),
            "acceleration_signature": round(acceleration, 2),
            "late_speed_profile": round(late_speed, 2),
            "energy_retention_profile": round(energy_retention, 2),
            "tempo_survivability": round(survivability, 2),
            "finish_pressure_profile": round(pressure, 2),
            "pace_compression_profile": round(compression, 2),
            "sectional_archetype": archetype,
            "sandbox_confidence": confidence,
            "sandbox_status": status,
            "trusted_for_live_modelling": "NO",
            "trusted_for_live_execution": "NO",
            "notes": "Sandbox only. No live pricing/execution impact.",
        })

    with OUT_SANDBOX.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)

    archetypes = Counter(r["sectional_archetype"] for r in out)
    confidence = Counter(r["sandbox_confidence"] for r in out)

    summary = []
    summary.append({"metric": "sandbox_rows", "value": len(out)})
    summary.append({"metric": "live_modelling_yes", "value": 0})
    summary.append({"metric": "live_execution_yes", "value": 0})

    for k, v in archetypes.most_common():
        summary.append({"metric": f"archetype::{k}", "value": v})

    for k, v in confidence.most_common():
        summary.append({"metric": f"confidence::{k}", "value": v})

    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("=" * 88)
    print("EDGEIQ SECTIONAL SANDBOX LAB V1")
    print("=" * 88)
    print(f"elite stable rows analysed: {len(out)}")
    print(f"saved: {OUT_SANDBOX}")
    print(f"saved: {OUT_SUMMARY}")
    print("archetypes:")
    for k, v in archetypes.most_common():
        print(f"  {k}: {v}")
    print("confidence:")
    for k, v in confidence.most_common():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
