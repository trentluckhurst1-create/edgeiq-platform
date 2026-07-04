import csv
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_race_sectional_rankings_v2.csv"
OUT = DATA / "edgeiq_race_sectional_read_v1.csv"
AUDIT = DATA / "edgeiq_race_sectional_read_v1_audit.csv"

def clean(v):
    return "" if v is None else str(v).strip()

def to_float(v, default=0.0):
    try:
        if v is None or str(v).strip() == "":
            return default
        return float(v)
    except Exception:
        return default

def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

rows = read_csv(SRC)
groups = defaultdict(list)

for r in rows:
    rk = clean(r.get("race_key"))
    if rk:
        groups[rk].append(r)

def first_by_flag(rows, flag):
    for r in rows:
        flags = clean(r.get("race_sectional_flags")).split("|")
        if flag in flags:
            return r
    return None

def race_status(rows):
    if not rows:
        return "NO_DATA"

    meaningful = [
        r for r in rows
        if clean(r.get("race_sectional_primary_flag")) not in ("NO_MEANINGFUL_SECTIONAL_SIGNAL", "NO_TOP_RANK", "")
    ]

    if not meaningful:
        return "SECTIONAL_DATA_INSUFFICIENT"

    strong = [
        r for r in meaningful
        if to_float(r.get("sectional_ability_score")) >= 65
        or clean(r.get("sectional_reliability_rank")).upper() in ("A", "B")
    ]

    if len(strong) >= 2:
        return "STRONG_SECTIONAL_READ"

    return "PARTIAL_SECTIONAL_READ"

def horse_summary(row, score_field="sectional_ability_score"):
    if not row:
        return ""
    horse = clean(row.get("horse_name"))
    score = to_float(row.get(score_field))
    rel = clean(row.get("sectional_reliability_rank"))
    if score > 0 and rel:
        return f"{horse} ({score:.0f}, Rel {rel})"
    if score > 0:
        return f"{horse} ({score:.0f})"
    return horse

def summary_for(status, picks):
    if status == "SECTIONAL_DATA_INSUFFICIENT":
        return "Sectional data insufficient for this race; no runner clears minimum evidence thresholds."

    bits = []

    if picks["best_sectional"]:
        bits.append(f"Best sectional profile: {horse_summary(picks['best_sectional'])}.")
    if picks["best_pace_fit"]:
        bits.append(f"Best sectional + pace fit: {horse_summary(picks['best_pace_fit'])}.")
    if picks["dangerous_improver"]:
        bits.append(f"Dangerous improver: {horse_summary(picks['dangerous_improver'])}.")
    if picks["most_reliable"]:
        bits.append(f"Most reliable sectional profile: {horse_summary(picks['most_reliable'])}.")

    if not bits:
        return "Only partial sectional evidence is available; treat the race read cautiously."

    return " ".join(bits)

out_rows = []

for rk, rs in sorted(groups.items()):
    track = clean(rs[0].get("track"))
    race_no = clean(rs[0].get("race_no"))

    picks = {
        "best_sectional": first_by_flag(rs, "BEST_SECTIONAL_HORSE"),
        "most_reliable": first_by_flag(rs, "HIGHEST_CONFIDENCE"),
        "best_closer": first_by_flag(rs, "BEST_CLOSER"),
        "best_sustained": first_by_flag(rs, "BEST_SUSTAINED"),
        "dangerous_improver": first_by_flag(rs, "DANGEROUS_IMPROVER"),
        "best_pace_fit": first_by_flag(rs, "BEST_PACE_FIT"),
    }

    status = race_status(rs)

    out_rows.append({
        "track": track,
        "race_no": race_no,
        "race_key": rk,
        "sectional_read_status": status,

        "best_sectional_horse": clean(picks["best_sectional"].get("horse_name")) if picks["best_sectional"] else "",
        "best_sectional_score": round(to_float(picks["best_sectional"].get("sectional_ability_score")) if picks["best_sectional"] else 0, 2),
        "best_sectional_reliability": clean(picks["best_sectional"].get("sectional_reliability_rank")) if picks["best_sectional"] else "",

        "most_reliable_profile": clean(picks["most_reliable"].get("horse_name")) if picks["most_reliable"] else "",
        "most_reliable_confidence": round(to_float(picks["most_reliable"].get("sectional_confidence_score")) if picks["most_reliable"] else 0, 2),
        "most_reliable_rank": clean(picks["most_reliable"].get("sectional_reliability_rank")) if picks["most_reliable"] else "",

        "best_closer": clean(picks["best_closer"].get("horse_name")) if picks["best_closer"] else "",
        "best_closer_score": round(to_float(picks["best_closer"].get("closing_speed_score")) if picks["best_closer"] else 0, 2),

        "best_sustained": clean(picks["best_sustained"].get("horse_name")) if picks["best_sustained"] else "",
        "best_sustained_score": round(to_float(picks["best_sustained"].get("sustained_speed_score")) if picks["best_sustained"] else 0, 2),

        "dangerous_improver": clean(picks["dangerous_improver"].get("horse_name")) if picks["dangerous_improver"] else "",
        "dangerous_improver_score": round(to_float(picks["dangerous_improver"].get("sectional_ability_score")) if picks["dangerous_improver"] else 0, 2),
        "dangerous_improver_reliability": clean(picks["dangerous_improver"].get("sectional_reliability_rank")) if picks["dangerous_improver"] else "",

        "best_pace_fit": clean(picks["best_pace_fit"].get("horse_name")) if picks["best_pace_fit"] else "",
        "best_pace_fit_score": round(to_float(picks["best_pace_fit"].get("sectional_ability_score")) if picks["best_pace_fit"] else 0, 2),
        "best_pace_fit_reliability": clean(picks["best_pace_fit"].get("sectional_reliability_rank")) if picks["best_pace_fit"] else "",

        "sectional_race_summary": summary_for(status, picks),
    })

fields = [
    "track",
    "race_no",
    "race_key",
    "sectional_read_status",
    "best_sectional_horse",
    "best_sectional_score",
    "best_sectional_reliability",
    "most_reliable_profile",
    "most_reliable_confidence",
    "most_reliable_rank",
    "best_closer",
    "best_closer_score",
    "best_sustained",
    "best_sustained_score",
    "dangerous_improver",
    "dangerous_improver_score",
    "dangerous_improver_reliability",
    "best_pace_fit",
    "best_pace_fit_score",
    "best_pace_fit_reliability",
    "sectional_race_summary",
]

with OUT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(out_rows)

status_counts = defaultdict(int)
for r in out_rows:
    status_counts[r["sectional_read_status"]] += 1

audit_row = {
    "source_rows": len(rows),
    "output_races": len(out_rows),
    "strong_sectional_read": status_counts.get("STRONG_SECTIONAL_READ", 0),
    "partial_sectional_read": status_counts.get("PARTIAL_SECTIONAL_READ", 0),
    "sectional_data_insufficient": status_counts.get("SECTIONAL_DATA_INSUFFICIENT", 0),
    "final_status": "RACE_SECTIONAL_READ_BUILT",
}

with AUDIT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(audit_row.keys()))
    writer.writeheader()
    writer.writerow(audit_row)

print("EDGEiQ Race Sectional Read V1 built")
print(f"source_rows={len(rows)}")
print(f"output_races={len(out_rows)}")
print(f"saved={OUT}")
print(f"audit={AUDIT}")
print("final_status=RACE_SECTIONAL_READ_BUILT")
