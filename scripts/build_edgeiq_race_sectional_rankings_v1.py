import csv
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_live_sectional_intelligence_v1.csv"
ABILITY = DATA / "edgeiq_sectional_ability_engine_v3.csv"
PACE = DATA / "edgeiq_pace_advantage_engine_v1.csv"

OUT = DATA / "edgeiq_race_sectional_rankings_v1.csv"
AUDIT = DATA / "edgeiq_race_sectional_rankings_v1_audit.csv"

def clean(v):
    return "" if v is None else str(v).strip()

def key(v):
    return clean(v).upper().replace("'", "").replace(".", "").replace("-", " ")

def to_float(v, default=0.0):
    try:
        if v is None or str(v).strip() == "":
            return default
        return float(v)
    except Exception:
        return default

def race_key(row):
    track = clean(row.get("track") or row.get("meeting") or row.get("venue"))
    race_no = clean(row.get("race_no") or row.get("race") or row.get("race_number"))
    return f"{track}|{race_no}"

def horse_key(row):
    return key(row.get("horse_name") or row.get("runner_name") or row.get("horse"))

def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

live_rows = read_csv(LIVE)
ability_rows = read_csv(ABILITY)
pace_rows = read_csv(PACE)

ability_by_horse = {}
for r in ability_rows:
    ability_by_horse[horse_key(r)] = r

pace_by_race_horse = {}
for r in pace_rows:
    rk = race_key(r)
    hk = horse_key(r)
    pace_by_race_horse[(rk, hk)] = r

race_groups = defaultdict(list)

for live in live_rows:
    rk = race_key(live)
    hk = horse_key(live)
    if not rk or not hk:
        continue

    ability = ability_by_horse.get(hk, {})
    pace = pace_by_race_horse.get((rk, hk), {})

    merged = {}
    merged.update(live)
    merged.update({f"ability_{k}": v for k, v in ability.items()})
    merged.update({f"pace_{k}": v for k, v in pace.items()})

    merged["_race_key"] = rk
    merged["_horse_key"] = hk
    merged["_track"] = clean(live.get("track") or live.get("meeting") or live.get("venue"))
    merged["_race_no"] = clean(live.get("race_no") or live.get("race") or live.get("race_number"))
    merged["_horse_name"] = clean(live.get("horse_name") or live.get("runner_name") or live.get("horse"))

    merged["_ability_score"] = to_float(ability.get("sectional_ability_score_v3"))
    merged["_confidence_score"] = to_float(ability.get("sectional_confidence_score_v3"))
    merged["_closing_score"] = to_float(ability.get("closing_speed_score"))
    merged["_sustained_score"] = to_float(ability.get("sustained_speed_score"))
    merged["_peak_score"] = to_float(ability.get("peak_speed_score"))
    merged["_reliability"] = clean(ability.get("sectional_reliability_rank_v3"))
    merged["_warning"] = clean(ability.get("sectional_sample_warning_v3"))
    merged["_ability_class"] = clean(ability.get("sectional_ability_class_v3"))
    merged["_pace_status"] = clean(
        pace.get("pace_advantage_status")
        or pace.get("advantage_status")
        or pace.get("status")
    )
    merged["_pace_signal"] = clean(
        pace.get("pace_advantage")
        or pace.get("pace_signal")
        or pace.get("advantage_type")
    )

    race_groups[rk].append(merged)

def rank_rows(rows, score_field):
    ordered = sorted(rows, key=lambda r: to_float(r.get(score_field)), reverse=True)
    return {r["_horse_key"]: idx + 1 for idx, r in enumerate(ordered)}

def dangerous_improver_score(r):
    ability = r["_ability_score"]
    conf = r["_confidence_score"]
    rel = r["_reliability"]

    # Strong talent signal + not fully proven yet.
    low_reliability_bonus = 0
    if rel == "D":
        low_reliability_bonus = 12
    elif rel == "C":
        low_reliability_bonus = 8
    elif rel == "B":
        low_reliability_bonus = 3

    confidence_gap = max(0, 75 - conf) * 0.25
    return ability + low_reliability_bonus + confidence_gap

def pace_combo_score(r):
    ability = r["_ability_score"]
    confidence = r["_confidence_score"]
    closing = r["_closing_score"]
    sustained = r["_sustained_score"]
    pace_status = r["_pace_status"].upper()
    pace_signal = r["_pace_signal"].upper()

    bonus = 0
    if "VERY_POSITIVE" in pace_status:
        bonus += 14
    elif "POSITIVE" in pace_status:
        bonus += 8
    elif "NEGATIVE" in pace_status:
        bonus -= 10

    if "PACE_COLLAPSE" in pace_signal:
        bonus += closing * 0.08
    if "SOFT_LEAD" in pace_signal:
        bonus += sustained * 0.06
    if "TURN_OF_FOOT" in pace_signal:
        bonus += closing * 0.06

    return (ability * 0.55) + (confidence * 0.15) + bonus

out_rows = []

for rk, rows in race_groups.items():
    ability_rank = rank_rows(rows, "_ability_score")
    confidence_rank = rank_rows(rows, "_confidence_score")
    closing_rank = rank_rows(rows, "_closing_score")
    sustained_rank = rank_rows(rows, "_sustained_score")

    dangerous_rank = {
        r["_horse_key"]: idx + 1
        for idx, r in enumerate(sorted(rows, key=dangerous_improver_score, reverse=True))
    }

    pace_rank = {
        r["_horse_key"]: idx + 1
        for idx, r in enumerate(sorted(rows, key=pace_combo_score, reverse=True))
    }

    for r in rows:
        hk = r["_horse_key"]

        top_flags = []
        if ability_rank.get(hk) == 1:
            top_flags.append("BEST_SECTIONAL_HORSE")
        if confidence_rank.get(hk) == 1:
            top_flags.append("HIGHEST_CONFIDENCE")
        if closing_rank.get(hk) == 1:
            top_flags.append("BEST_CLOSER")
        if sustained_rank.get(hk) == 1:
            top_flags.append("BEST_SUSTAINED")
        if dangerous_rank.get(hk) == 1:
            top_flags.append("DANGEROUS_IMPROVER")
        if pace_rank.get(hk) == 1:
            top_flags.append("BEST_PACE_FIT")

        if not top_flags:
            top_flags.append("NO_TOP_RANK")

        primary = top_flags[0]

        note_parts = []
        if "BEST_SECTIONAL_HORSE" in top_flags:
            note_parts.append("Top sectional ability in this race")
        if "BEST_CLOSER" in top_flags:
            note_parts.append("Best closing profile")
        if "BEST_SUSTAINED" in top_flags:
            note_parts.append("Best sustained-speed profile")
        if "DANGEROUS_IMPROVER" in top_flags:
            note_parts.append("High upside but not fully proven")
        if "BEST_PACE_FIT" in top_flags:
            note_parts.append("Best sectional plus pace-shape fit")
        if "HIGHEST_CONFIDENCE" in top_flags:
            note_parts.append("Most reliable sectional evidence")

        if not note_parts:
            note_parts.append("No dominant sectional edge")

        out_rows.append({
            "track": r["_track"],
            "race_no": r["_race_no"],
            "race_key": rk,
            "horse_name": r["_horse_name"],
            "sectional_ability_score": round(r["_ability_score"], 2),
            "sectional_ability_class": r["_ability_class"],
            "sectional_confidence_score": round(r["_confidence_score"], 2),
            "sectional_reliability_rank": r["_reliability"],
            "closing_speed_score": round(r["_closing_score"], 2),
            "sustained_speed_score": round(r["_sustained_score"], 2),
            "pace_advantage_status": r["_pace_status"],
            "pace_advantage_signal": r["_pace_signal"],
            "sectional_ability_rank": ability_rank.get(hk, ""),
            "sectional_confidence_rank": confidence_rank.get(hk, ""),
            "closing_rank": closing_rank.get(hk, ""),
            "sustained_rank": sustained_rank.get(hk, ""),
            "dangerous_improver_rank": dangerous_rank.get(hk, ""),
            "pace_fit_rank": pace_rank.get(hk, ""),
            "race_sectional_primary_flag": primary,
            "race_sectional_flags": "|".join(top_flags),
            "race_sectional_note": "; ".join(note_parts),
        })

fields = [
    "track",
    "race_no",
    "race_key",
    "horse_name",
    "sectional_ability_score",
    "sectional_ability_class",
    "sectional_confidence_score",
    "sectional_reliability_rank",
    "closing_speed_score",
    "sustained_speed_score",
    "pace_advantage_status",
    "pace_advantage_signal",
    "sectional_ability_rank",
    "sectional_confidence_rank",
    "closing_rank",
    "sustained_rank",
    "dangerous_improver_rank",
    "pace_fit_rank",
    "race_sectional_primary_flag",
    "race_sectional_flags",
    "race_sectional_note",
]

with OUT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(out_rows)

flag_counts = defaultdict(int)
race_count = len(race_groups)

for r in out_rows:
    for flag in clean(r.get("race_sectional_flags")).split("|"):
        if flag:
            flag_counts[flag] += 1

audit_row = {
    "live_rows_loaded": len(live_rows),
    "ability_rows_loaded": len(ability_rows),
    "pace_rows_loaded": len(pace_rows),
    "output_rows": len(out_rows),
    "race_count": race_count,
    "best_sectional_horse": flag_counts.get("BEST_SECTIONAL_HORSE", 0),
    "highest_confidence": flag_counts.get("HIGHEST_CONFIDENCE", 0),
    "best_closer": flag_counts.get("BEST_CLOSER", 0),
    "best_sustained": flag_counts.get("BEST_SUSTAINED", 0),
    "dangerous_improver": flag_counts.get("DANGEROUS_IMPROVER", 0),
    "best_pace_fit": flag_counts.get("BEST_PACE_FIT", 0),
    "final_status": "RACE_SECTIONAL_RANKINGS_BUILT",
}

with AUDIT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(audit_row.keys()))
    writer.writeheader()
    writer.writerow(audit_row)

print("EDGEiQ Race Sectional Rankings V1 built")
print(f"rows={len(out_rows)}")
print(f"races={race_count}")
print(f"saved={OUT}")
print(f"audit={AUDIT}")
print("final_status=RACE_SECTIONAL_RANKINGS_BUILT")
