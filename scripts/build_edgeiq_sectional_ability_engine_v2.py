import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_sectional_ability_engine_v1.csv"
OUT = DATA / "edgeiq_sectional_ability_engine_v2.csv"
AUDIT = DATA / "edgeiq_sectional_ability_engine_v2_audit.csv"

def f(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default

def i(v, default=0):
    try:
        return int(float(v))
    except Exception:
        return default

def evidence_score(runs):
    if runs <= 0: return 0
    if runs == 1: return 20
    if runs == 2: return 35
    if runs == 3: return 50
    if runs == 4: return 60
    if runs == 5: return 70
    if runs == 6: return 78
    if runs == 7: return 84
    if runs == 8: return 89
    if runs == 9: return 93
    return 100

def confidence_status(runs):
    if runs >= 10:
        return "HIGH_CONFIDENCE"
    if runs >= 6:
        return "MEDIUM_CONFIDENCE"
    if runs >= 3:
        return "EARLY_CONFIDENCE"
    return "LOW_CONFIDENCE"

def adjusted_class(score, conf):
    if conf < 50 and score >= 80:
        return "UNPROVEN_HIGH_UPSIDE"
    if score >= 90:
        return "WORLD_CLASS"
    if score >= 85:
        return "ELITE"
    if score >= 78:
        return "VERY_STRONG"
    if score >= 68:
        return "ABOVE_AVERAGE"
    if score >= 58:
        return "COMPETITIVE"
    if score >= 45:
        return "AVERAGE"
    return "LIMITED"

rows = []
with SRC.open("r", encoding="utf-8-sig", newline="") as f_in:
    reader = csv.DictReader(f_in)
    base_fields = reader.fieldnames or []

    for r in reader:
        runs = i(r.get("runs_with_sectionals"))
        raw = f(r.get("sectional_ability_score"))
        peak = f(r.get("peak_speed_score"))
        closing = f(r.get("closing_speed_score"))
        sustained = f(r.get("sustained_speed_score"))

        ev = evidence_score(runs)

        # Confidence is evidence-led, but still rewards balanced sectional data.
        balance = 100 - (max(peak, closing, sustained) - min(peak, closing, sustained))
        balance = max(0, min(100, balance))

        conf = round((ev * 0.75) + (balance * 0.25), 2)

        # Ability remains mostly talent, but confidence prevents tiny samples from dominating.
        adjusted = round((raw * 0.78) + (conf * 0.22), 2)

        r["raw_sectional_ability_score"] = round(raw, 2)
        r["sectional_evidence_score"] = round(ev, 2)
        r["sectional_confidence_score"] = conf
        r["adjusted_sectional_ability_score"] = adjusted
        r["sectional_class_v2"] = adjusted_class(adjusted, conf)
        r["confidence_status_v2"] = confidence_status(runs)

        rows.append(r)

extra_fields = [
    "raw_sectional_ability_score",
    "sectional_evidence_score",
    "sectional_confidence_score",
    "adjusted_sectional_ability_score",
    "sectional_class_v2",
    "confidence_status_v2",
]

fields = list(base_fields)
for x in extra_fields:
    if x not in fields:
        fields.append(x)

with OUT.open("w", encoding="utf-8", newline="") as f_out:
    writer = csv.DictWriter(f_out, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

classes = {}
conf_status = {}
for r in rows:
    classes[r["sectional_class_v2"]] = classes.get(r["sectional_class_v2"], 0) + 1
    conf_status[r["confidence_status_v2"]] = conf_status.get(r["confidence_status_v2"], 0) + 1

audit_row = {
    "source_rows": len(rows),
    "world_class": classes.get("WORLD_CLASS", 0),
    "elite": classes.get("ELITE", 0),
    "very_strong": classes.get("VERY_STRONG", 0),
    "above_average": classes.get("ABOVE_AVERAGE", 0),
    "competitive": classes.get("COMPETITIVE", 0),
    "average": classes.get("AVERAGE", 0),
    "limited": classes.get("LIMITED", 0),
    "unproven_high_upside": classes.get("UNPROVEN_HIGH_UPSIDE", 0),
    "high_confidence": conf_status.get("HIGH_CONFIDENCE", 0),
    "medium_confidence": conf_status.get("MEDIUM_CONFIDENCE", 0),
    "early_confidence": conf_status.get("EARLY_CONFIDENCE", 0),
    "low_confidence": conf_status.get("LOW_CONFIDENCE", 0),
    "final_status": "SECTIONAL_ABILITY_ENGINE_V2_BUILT",
}

with AUDIT.open("w", encoding="utf-8", newline="") as f_audit:
    writer = csv.DictWriter(f_audit, fieldnames=list(audit_row.keys()))
    writer.writeheader()
    writer.writerow(audit_row)

print("EDGEiQ Sectional Ability Engine V2 built")
print(f"rows={len(rows)}")
print(f"saved={OUT}")
print(f"audit={AUDIT}")
print("final_status=SECTIONAL_ABILITY_ENGINE_V2_BUILT")
