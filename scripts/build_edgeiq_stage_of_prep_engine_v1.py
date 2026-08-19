import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta

BASE = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = BASE / "public" / "data"

SRC = DATA / "edgeiq_trainer_jockey_runner_history_canonical_v1.csv"

OUT_HORSE = DATA / "edgeiq_horse_stage_of_prep_engine_v1.csv"
OUT_TRAINER = DATA / "edgeiq_trainer_stage_of_prep_engine_v1.csv"
SUMMARY = DATA / "edgeiq_stage_of_prep_engine_v1_summary.csv"

def clean(v):
    return (v or "").strip()

def parse_date(v):
    try:
        return datetime.strptime(clean(v), "%Y-%m-%d").date()
    except Exception:
        return None

def prep_stage(n):
    if n <= 1:
        return "FIRST_UP"
    if n == 2:
        return "SECOND_UP"
    if n == 3:
        return "THIRD_UP"
    return "FOURTH_UP_PLUS"

rows = []
with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

horse_runs = defaultdict(list)

for r in rows:
    horse = clean(r.get("horse_key")) or clean(r.get("horse"))
    d = parse_date(r.get("meeting_date"))
    if not horse or not d:
        continue
    horse_runs[horse].append((d, r))

annotated = []

for horse, runs in horse_runs.items():
    runs.sort(key=lambda x: x[0])
    campaign_start_count = 0
    last_date = None

    for d, r in runs:
        if last_date is None or (d - last_date).days >= 60:
            campaign_start_count = 1
        else:
            campaign_start_count += 1

        stage = prep_stage(campaign_start_count)

        rr = dict(r)
        rr["prep_run_number_v1"] = campaign_start_count
        rr["prep_stage_v1"] = stage
        annotated.append(rr)

        last_date = d

horse_base = defaultdict(lambda: {"starts":0,"wins":0,"places":0})
horse_stage = defaultdict(lambda: {"starts":0,"wins":0,"places":0})

trainer_base = defaultdict(lambda: {"starts":0,"wins":0,"places":0})
trainer_stage = defaultdict(lambda: {"starts":0,"wins":0,"places":0})

for r in annotated:
    horse = clean(r.get("horse_key")) or clean(r.get("horse"))
    trainer = clean(r.get("trainer_canonical")) or clean(r.get("trainer"))
    stage = clean(r.get("prep_stage_v1"))

    won = 1 if clean(r.get("won_v1")) == "1" else 0
    placed = 1 if clean(r.get("placed_v1")) == "1" else 0

    if horse:
        horse_base[horse]["starts"] += 1
        horse_base[horse]["wins"] += won
        horse_base[horse]["places"] += placed

        horse_stage[(horse, stage)]["starts"] += 1
        horse_stage[(horse, stage)]["wins"] += won
        horse_stage[(horse, stage)]["places"] += placed

    if trainer:
        trainer_base[trainer]["starts"] += 1
        trainer_base[trainer]["wins"] += won
        trainer_base[trainer]["places"] += placed

        trainer_stage[(trainer, stage)]["starts"] += 1
        trainer_stage[(trainer, stage)]["wins"] += won
        trainer_stage[(trainer, stage)]["places"] += placed

horse_out = []

for (horse, stage), g in horse_stage.items():
    hb = horse_base[horse]

    if hb["starts"] < 10 or g["starts"] < 3:
        continue

    win_pct = g["wins"] / g["starts"]
    place_pct = g["places"] / g["starts"]

    base_win = hb["wins"] / hb["starts"]
    base_place = hb["places"] / hb["starts"]

    win_lift = win_pct - base_win
    place_lift = place_pct - base_place

    if g["starts"] >= 4 and win_lift >= 0.12:
        signal = "POSITIVE_PREP_PROFILE"
    elif g["starts"] >= 4 and win_lift <= -0.12:
        signal = "CAUTION_PREP_PROFILE"
    else:
        signal = "NEUTRAL"

    horse_out.append({
        "entity_type": "HORSE",
        "horse": horse,
        "prep_stage": stage,
        "starts": g["starts"],
        "wins": g["wins"],
        "places": g["places"],
        "win_pct": round(win_pct * 100, 2),
        "place_pct": round(place_pct * 100, 2),
        "horse_base_starts": hb["starts"],
        "horse_base_win_pct": round(base_win * 100, 2),
        "horse_base_place_pct": round(base_place * 100, 2),
        "win_lift_pct": round(win_lift * 100, 2),
        "place_lift_pct": round(place_lift * 100, 2),
        "signal": signal,
        "insight": f"{horse} has a {signal.lower().replace('_',' ')} at {stage.replace('_',' ').title()}.",
    })

trainer_out = []

for (trainer, stage), g in trainer_stage.items():
    tb = trainer_base[trainer]

    if tb["starts"] < 75 or g["starts"] < 25:
        continue

    win_pct = g["wins"] / g["starts"]
    place_pct = g["places"] / g["starts"]

    base_win = tb["wins"] / tb["starts"]
    base_place = tb["places"] / tb["starts"]

    win_lift = win_pct - base_win
    place_lift = place_pct - base_place

    if g["starts"] >= 75 and win_lift >= 0.035 and place_lift >= 0.05:
        signal = "PREP_CONTEXT_EDGE"
    elif g["starts"] >= 40 and win_lift >= 0.02 and place_lift >= 0.035:
        signal = "MILD_PREP_CONTEXT_EDGE"
    elif g["starts"] >= 75 and win_lift <= -0.03 and place_lift <= -0.045:
        signal = "PREP_CONTEXT_RISK"
    else:
        signal = "NEUTRAL"

    if g["starts"] >= 150:
        evidence_band = "STRONG_EVIDENCE"
    elif g["starts"] >= 75:
        evidence_band = "PROMISING_EVIDENCE"
    elif g["starts"] >= 40:
        evidence_band = "MILD_EVIDENCE"
    else:
        evidence_band = "LIGHT_EVIDENCE"

    trainer_out.append({
        "entity_type": "TRAINER",
        "trainer": trainer,
        "prep_stage": stage,
        "starts": g["starts"],
        "wins": g["wins"],
        "places": g["places"],
        "win_pct": round(win_pct * 100, 2),
        "place_pct": round(place_pct * 100, 2),
        "trainer_base_starts": tb["starts"],
        "trainer_base_win_pct": round(base_win * 100, 2),
        "trainer_base_place_pct": round(base_place * 100, 2),
        "win_lift_pct": round(win_lift * 100, 2),
        "place_lift_pct": round(place_lift * 100, 2),
        "signal": signal,
        "evidence_band": evidence_band,
        "insight": f"{trainer} has historically performed {signal.lower().replace('_',' ')} at {stage.replace('_',' ').title()} stage.",
    })

horse_out.sort(key=lambda r: (r["signal"], -int(r["starts"]), r["horse"]))
trainer_out.sort(key=lambda r: (r["signal"], -int(r["starts"]), r["trainer"]))

with OUT_HORSE.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(horse_out[0].keys()))
    writer.writeheader()
    writer.writerows(horse_out)

with OUT_TRAINER.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(trainer_out[0].keys()))
    writer.writeheader()
    writer.writerows(trainer_out)

summary = [
    {"metric":"status","value":"COMPLETE"},
    {"metric":"source_rows","value":len(rows)},
    {"metric":"annotated_rows","value":len(annotated)},
    {"metric":"horse_stage_rows","value":len(horse_out)},
    {"metric":"trainer_stage_rows","value":len(trainer_out)},
    {"metric":"horse_positive_prep_profiles","value":sum(1 for r in horse_out if r["signal"]=="POSITIVE_PREP_PROFILE")},
    {"metric":"horse_caution_prep_profiles","value":sum(1 for r in horse_out if r["signal"]=="CAUTION_PREP_PROFILE")},
    {"metric":"trainer_prep_edges","value":sum(1 for r in trainer_out if r["signal"]=="PREP_CONTEXT_EDGE")},
    {"metric":"trainer_mild_prep_edges","value":sum(1 for r in trainer_out if r["signal"]=="MILD_PREP_CONTEXT_EDGE")},
    {"metric":"trainer_prep_risks","value":sum(1 for r in trainer_out if r["signal"]=="PREP_CONTEXT_RISK")},
    {"metric":"built_at","value":datetime.now().isoformat()},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric","value"])
    writer.writeheader()
    writer.writerows(summary)

print("[EDGEIQ_STAGE_OF_PREP_ENGINE_V1] COMPLETE")
print(f"horse_out={OUT_HORSE}")
print(f"trainer_out={OUT_TRAINER}")
print(f"summary={SUMMARY}")
