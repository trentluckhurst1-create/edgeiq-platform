import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime

BASE = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = BASE / "public" / "data"

SRC = DATA / "edgeiq_trainer_jockey_runner_history_canonical_v1.csv"
OUT = DATA / "edgeiq_jockey_context_research_v1.csv"
SUMMARY = DATA / "edgeiq_jockey_context_research_v1_summary.csv"

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
    if "SYNTH" in s: return "SYNTHETIC"
    return "UNKNOWN"

def barrier_bucket(v):
    n = fnum(v)
    if n is None or n <= 0: return "UNKNOWN"
    if n <= 4: return "INSIDE"
    if n <= 8: return "MIDDLE"
    return "WIDE"

def class_bucket(v):
    s = clean(v).upper()
    if "MAIDEN" in s or s == "MDN": return "MAIDEN"
    if "GROUP" in s or "LISTED" in s: return "BLACK_TYPE"
    if "BM" in s: return "BENCHMARK"
    if "HANDICAP" in s: return "HANDICAP"
    return "OTHER" if s else "UNKNOWN"

rows = []
with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

global_starts = 0
global_wins = 0
global_places = 0

groups = defaultdict(lambda: {"starts":0,"wins":0,"places":0})

for r in rows:
    jockey = clean(r.get("jockey_canonical"))
    if not jockey:
        continue

    won = 1 if clean(r.get("won_v1")) == "1" else 0
    placed = 1 if clean(r.get("placed_v1")) == "1" else 0

    global_starts += 1
    global_wins += won
    global_places += placed

    contexts = [
        ("TRACK", clean(r.get("track"))),
        ("DISTANCE", distance_bucket(r.get("distance"))),
        ("CONDITION", condition_bucket(r.get("track_condition"))),
        ("BARRIER", barrier_bucket(r.get("barrier"))),
        ("CLASS", class_bucket(r.get("race_class"))),
    ]

    for ctype, cval in contexts:
        if not cval or cval == "UNKNOWN":
            continue
        key = (jockey, ctype, cval)
        groups[key]["starts"] += 1
        groups[key]["wins"] += won
        groups[key]["places"] += placed

global_win = global_wins / global_starts if global_starts else 0
global_place = global_places / global_starts if global_starts else 0

out_rows = []
for (jockey, ctype, cval), g in groups.items():
    starts = g["starts"]
    if starts < 20:
        continue

    win_pct = g["wins"] / starts
    place_pct = g["places"] / starts
    win_lift = win_pct - global_win
    place_lift = place_pct - global_place

    if starts >= 50 and win_lift >= 0.06 and place_lift >= 0.08:
        signal = "STRONG_POSITIVE"
    elif starts >= 30 and win_lift >= 0.03 and place_lift >= 0.04:
        signal = "POSITIVE"
    elif starts >= 50 and win_lift <= -0.05 and place_lift <= -0.07:
        signal = "NEGATIVE"
    else:
        signal = "NEUTRAL"

    out_rows.append({
        "jockey": jockey,
        "context_type": ctype,
        "context_value": cval,
        "starts": starts,
        "wins": g["wins"],
        "places": g["places"],
        "win_pct": round(win_pct * 100, 2),
        "place_pct": round(place_pct * 100, 2),
        "global_win_pct": round(global_win * 100, 2),
        "global_place_pct": round(global_place * 100, 2),
        "win_lift_pct": round(win_lift * 100, 2),
        "place_lift_pct": round(place_lift * 100, 2),
        "signal": signal,
        "insight": f"{jockey} has a {signal.lower().replace('_',' ')} profile for {ctype.lower()} {cval}.",
    })

out_rows.sort(key=lambda r: (r["signal"] != "STRONG_POSITIVE", r["signal"] != "POSITIVE", -int(r["starts"])))

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
    writer.writeheader()
    writer.writerows(out_rows)

summary = [
    {"metric":"status","value":"COMPLETE"},
    {"metric":"source_rows","value":len(rows)},
    {"metric":"global_starts","value":global_starts},
    {"metric":"global_win_pct","value":round(global_win*100,2)},
    {"metric":"global_place_pct","value":round(global_place*100,2)},
    {"metric":"context_rows","value":len(out_rows)},
    {"metric":"strong_positive","value":sum(1 for r in out_rows if r["signal"]=="STRONG_POSITIVE")},
    {"metric":"positive","value":sum(1 for r in out_rows if r["signal"]=="POSITIVE")},
    {"metric":"negative","value":sum(1 for r in out_rows if r["signal"]=="NEGATIVE")},
    {"metric":"built_at","value":datetime.now().isoformat()},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric","value"])
    writer.writeheader()
    writer.writerows(summary)

print("[EDGEIQ_JOCKEY_CONTEXT_RESEARCH_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
