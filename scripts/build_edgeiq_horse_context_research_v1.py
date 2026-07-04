import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime

BASE = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = BASE / "public" / "data"

SRC = DATA / "edgeiq_trainer_jockey_runner_history_canonical_v1.csv"

OUT = DATA / "edgeiq_horse_context_research_v1.csv"
SUMMARY = DATA / "edgeiq_horse_context_research_v1_summary.csv"

def clean(v):
    return (v or "").strip()

def fnum(v):
    s = clean(v).replace("$","").replace(",","").replace("kg","").replace("m","")
    try:
        return float(s)
    except:
        return None

def distance_bucket(v):
    n = fnum(v)
    if n is None: return "UNKNOWN"
    if n < 1200: return "SPRINT_SHORT"
    if n < 1400: return "SPRINT"
    if n < 1600: return "SPRINT_MILE"
    if n < 2000: return "MILE_MIDDLE"
    if n < 2400: return "STAYING"
    return "LONG_STAYING"

def condition_bucket(v):
    s = clean(v).upper()
    if "HEAVY" in s: return "HEAVY"
    if "SOFT" in s: return "SOFT"
    if "GOOD" in s: return "GOOD"
    return "UNKNOWN"

def class_bucket(v):
    s = clean(v).upper()
    if "GROUP" in s or "LISTED" in s:
        return "BLACK_TYPE"
    if "MAIDEN" in s:
        return "MAIDEN"
    if "BM" in s:
        return "BENCHMARK"
    if "HANDICAP" in s:
        return "HANDICAP"
    return "OTHER"

def sp_bucket(v):
    s = clean(v).replace("$","")
    try:
        n = float(s)
    except:
        return "UNKNOWN"

    if n <= 2.50: return "FAVOURITE"
    if n <= 5.00: return "WELL_FOUND"
    if n <= 10.00: return "MID_MARKET"
    return "OUTSIDER"

rows = []
with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

horse_base = defaultdict(lambda:{
    "starts":0,
    "wins":0,
    "places":0
})

contexts = defaultdict(lambda:{
    "starts":0,
    "wins":0,
    "places":0
})

for r in rows:

    horse = clean(r.get("horse_key"))
    if not horse:
        continue

    won = 1 if clean(r.get("won_v1")) == "1" else 0
    placed = 1 if clean(r.get("placed_v1")) == "1" else 0

    horse_base[horse]["starts"] += 1
    horse_base[horse]["wins"] += won
    horse_base[horse]["places"] += placed

    context_list = [
        ("TRACK", clean(r.get("track"))),
        ("DISTANCE", distance_bucket(r.get("distance"))),
        ("CONDITION", condition_bucket(r.get("track_condition"))),
        ("CLASS", class_bucket(r.get("race_class"))),
        ("SP", sp_bucket(r.get("sp"))),
    ]

    for ctype, cvalue in context_list:

        if not cvalue or cvalue == "UNKNOWN":
            continue

        k = (horse, ctype, cvalue)

        contexts[k]["starts"] += 1
        contexts[k]["wins"] += won
        contexts[k]["places"] += placed

out_rows = []

for (horse, ctype, cvalue), g in contexts.items():

    starts = g["starts"]

    if starts < 5:
        continue

    hb = horse_base[horse]

    if hb["starts"] < 12:
        continue

    win_pct = g["wins"] / starts
    place_pct = g["places"] / starts

    base_win = hb["wins"] / hb["starts"]
    base_place = hb["places"] / hb["starts"]

    win_lift = win_pct - base_win
    place_lift = place_pct - base_place

    if starts >= 8 and win_lift >= 0.15:
        signal = "POSITIVE_PROFILE"
    elif starts >= 8 and win_lift <= -0.15:
        signal = "CAUTION_PROFILE"
    else:
        signal = "NEUTRAL"

    if signal == "POSITIVE_PROFILE":
        insight = f"Historically performs above baseline in {ctype.lower()} context: {cvalue}"
    elif signal == "CAUTION_PROFILE":
        insight = f"Historically performs below baseline in {ctype.lower()} context: {cvalue}"
    else:
        insight = f"Neutral profile in {ctype.lower()} context: {cvalue}"

    out_rows.append({
        "horse_key": horse,
        "context_type": ctype,
        "context_value": cvalue,
        "starts": starts,
        "wins": g["wins"],
        "places": g["places"],
        "horse_starts": hb["starts"],
        "win_pct": round(win_pct * 100,2),
        "place_pct": round(place_pct * 100,2),
        "horse_base_win_pct": round(base_win * 100,2),
        "horse_base_place_pct": round(base_place * 100,2),
        "win_lift_pct": round(win_lift * 100,2),
        "place_lift_pct": round(place_lift * 100,2),
        "signal": signal,
        "insight": insight
    })

signal_order = {
    "POSITIVE_PROFILE":0,
    "CAUTION_PROFILE":1,
    "NEUTRAL":2
}

out_rows.sort(
    key=lambda r: (
        signal_order.get(r["signal"],9),
        -int(r["starts"])
    )
)

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
    writer.writeheader()
    writer.writerows(out_rows)

summary = [
    {"metric":"status","value":"COMPLETE"},
    {"metric":"source_rows","value":len(rows)},
    {"metric":"unique_horses","value":len(horse_base)},
    {"metric":"context_rows","value":len(out_rows)},
    {"metric":"positive_profiles","value":sum(1 for r in out_rows if r["signal"]=="POSITIVE_PROFILE")},
    {"metric":"caution_profiles","value":sum(1 for r in out_rows if r["signal"]=="CAUTION_PROFILE")},
    {"metric":"built_at","value":datetime.now().isoformat()}
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric","value"])
    writer.writeheader()
    writer.writerows(summary)

print("[EDGEIQ_HORSE_CONTEXT_RESEARCH_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
