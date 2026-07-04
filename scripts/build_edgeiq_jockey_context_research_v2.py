import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime

BASE = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = BASE / "public" / "data"

SRC = DATA / "edgeiq_trainer_jockey_runner_history_canonical_v1.csv"
OUT = DATA / "edgeiq_jockey_context_research_v2.csv"
SUMMARY = DATA / "edgeiq_jockey_context_research_v2_summary.csv"

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

jockey_base = defaultdict(lambda: {"starts":0,"wins":0,"places":0})
groups = defaultdict(lambda: {"starts":0,"wins":0,"places":0})

for r in rows:
    jockey = clean(r.get("jockey_canonical"))
    if not jockey:
        continue

    won = 1 if clean(r.get("won_v1")) == "1" else 0
    placed = 1 if clean(r.get("placed_v1")) == "1" else 0

    jockey_base[jockey]["starts"] += 1
    jockey_base[jockey]["wins"] += won
    jockey_base[jockey]["places"] += placed

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

out_rows = []

for (jockey, ctype, cval), g in groups.items():
    starts = g["starts"]
    base = jockey_base[jockey]
    base_starts = base["starts"]

    if starts < 25 or base_starts < 75:
        continue

    win_pct = g["wins"] / starts
    place_pct = g["places"] / starts
    base_win = base["wins"] / base_starts
    base_place = base["places"] / base_starts

    win_lift = win_pct - base_win
    place_lift = place_pct - base_place

    if starts >= 50 and win_lift >= 0.04 and place_lift >= 0.06:
        signal = "CONTEXT_EDGE"
    elif starts >= 35 and win_lift >= 0.025 and place_lift >= 0.04:
        signal = "MILD_CONTEXT_EDGE"
    elif starts >= 50 and win_lift <= -0.035 and place_lift <= -0.05:
        signal = "CONTEXT_RISK"
    else:
        signal = "NEUTRAL"

    if signal == "CONTEXT_EDGE":
        phrase = f"{jockey} has historically performed above their own baseline for {ctype.lower()} {cval}."
    elif signal == "MILD_CONTEXT_EDGE":
        phrase = f"{jockey} has shown a mild positive context profile for {ctype.lower()} {cval}."
    elif signal == "CONTEXT_RISK":
        phrase = f"{jockey} has historically performed below their own baseline for {ctype.lower()} {cval}."
    else:
        phrase = f"{jockey} has a neutral context profile for {ctype.lower()} {cval}."

    out_rows.append({
        "jockey": jockey,
        "context_type": ctype,
        "context_value": cval,
        "starts": starts,
        "wins": g["wins"],
        "places": g["places"],
        "win_pct": round(win_pct * 100, 2),
        "place_pct": round(place_pct * 100, 2),
        "jockey_base_starts": base_starts,
        "jockey_base_win_pct": round(base_win * 100, 2),
        "jockey_base_place_pct": round(base_place * 100, 2),
        "within_jockey_win_lift_pct": round(win_lift * 100, 2),
        "within_jockey_place_lift_pct": round(place_lift * 100, 2),
        "signal": signal,
        "insight": phrase,
    })

signal_order = {"CONTEXT_EDGE":0, "MILD_CONTEXT_EDGE":1, "CONTEXT_RISK":2, "NEUTRAL":3}
out_rows.sort(key=lambda r: (signal_order.get(r["signal"],9), -int(r["starts"]), r["jockey"]))

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
    writer.writeheader()
    writer.writerows(out_rows)

summary = [
    {"metric":"status","value":"COMPLETE"},
    {"metric":"source_rows","value":len(rows)},
    {"metric":"unique_jockeys","value":len(jockey_base)},
    {"metric":"context_rows","value":len(out_rows)},
    {"metric":"context_edge","value":sum(1 for r in out_rows if r["signal"]=="CONTEXT_EDGE")},
    {"metric":"mild_context_edge","value":sum(1 for r in out_rows if r["signal"]=="MILD_CONTEXT_EDGE")},
    {"metric":"context_risk","value":sum(1 for r in out_rows if r["signal"]=="CONTEXT_RISK")},
    {"metric":"built_at","value":datetime.now().isoformat()},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric","value"])
    writer.writeheader()
    writer.writerows(summary)

print("[EDGEIQ_JOCKEY_CONTEXT_RESEARCH_V2] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
