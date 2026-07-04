import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime

BASE = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = BASE / "public" / "data"

SRC = DATA / "edgeiq_trainer_jockey_runner_history_canonical_v1.csv"

OUT = DATA / "edgeiq_trainer_context_research_v2.csv"
SUMMARY = DATA / "edgeiq_trainer_context_research_v2_summary.csv"

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

def class_bucket(v):
    s = clean(v).upper()
    if "GROUP" in s or "LISTED" in s: return "BLACK_TYPE"
    if "MAIDEN" in s: return "MAIDEN"
    if "BM" in s: return "BENCHMARK"
    if "HANDICAP" in s: return "HANDICAP"
    return "OTHER" if s else "UNKNOWN"

def barrier_bucket(v):
    n = fnum(v)
    if n is None or n <= 0: return "UNKNOWN"
    if n <= 4: return "INSIDE"
    if n <= 8: return "MIDDLE"
    return "WIDE"

def sp_bucket(v):
    n = fnum(v)
    if n is None or n <= 0: return "UNKNOWN"
    if n <= 2.50: return "FAVOURITE"
    if n <= 5.00: return "WELL_FOUND"
    if n <= 10.00: return "MID_MARKET"
    return "OUTSIDER"

def track_family(v):
    s = clean(v).upper()

    if "FLEMINGTON" in s: return "FLEMINGTON"
    if "CAULFIELD" in s: return "CAULFIELD"
    if "VALLEY" in s or "MOONEE" in s: return "THE_VALLEY"
    if "SANDOWN" in s or "HILLSIDE" in s or "LAKESIDE" in s: return "SANDOWN"
    if "SYN" in s or "SYNTHETIC" in s: return "SYNTHETIC"
    if "PAKENHAM" in s: return "PAKENHAM"
    if "CRANBOURNE" in s: return "CRANBOURNE"
    if "GEELONG" in s: return "GEELONG"
    if "BALLARAT" in s: return "BALLARAT"
    if "BENDIGO" in s: return "BENDIGO"
    if "SALE" in s: return "SALE"
    if "WARRNAMBOOL" in s: return "WARRNAMBOOL"
    return "COUNTRY_OTHER"

rows = []
with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

trainer_base = defaultdict(lambda: {"starts":0,"wins":0,"places":0})
groups = defaultdict(lambda: {"starts":0,"wins":0,"places":0})

for r in rows:
    trainer = clean(r.get("trainer_canonical"))
    if not trainer:
        continue

    won = 1 if clean(r.get("won_v1")) == "1" else 0
    placed = 1 if clean(r.get("placed_v1")) == "1" else 0

    trainer_base[trainer]["starts"] += 1
    trainer_base[trainer]["wins"] += won
    trainer_base[trainer]["places"] += placed

    contexts = [
        ("TRACK", clean(r.get("track"))),
        ("TRACK_FAMILY", track_family(r.get("track"))),
        ("DISTANCE", distance_bucket(r.get("distance"))),
        ("CONDITION", condition_bucket(r.get("track_condition"))),
        ("CLASS", class_bucket(r.get("race_class"))),
        ("BARRIER", barrier_bucket(r.get("barrier"))),
        ("SP", sp_bucket(r.get("sp"))),
    ]

    for ctype, cvalue in contexts:
        if not cvalue or cvalue == "UNKNOWN":
            continue

        k = (trainer, ctype, cvalue)

        groups[k]["starts"] += 1
        groups[k]["wins"] += won
        groups[k]["places"] += placed

out_rows = []

for (trainer, ctype, cvalue), g in groups.items():

    starts = g["starts"]
    base = trainer_base[trainer]
    base_starts = base["starts"]

    if starts < 25 or base_starts < 75:
        continue

    win_pct = g["wins"] / starts
    place_pct = g["places"] / starts

    base_win = base["wins"] / base_starts
    base_place = base["places"] / base_starts

    win_lift = win_pct - base_win
    place_lift = place_pct - base_place

    if starts >= 75 and win_lift >= 0.04 and place_lift >= 0.06:
        signal = "CONTEXT_EDGE"
    elif starts >= 40 and win_lift >= 0.025 and place_lift >= 0.04:
        signal = "MILD_CONTEXT_EDGE"
    elif starts >= 75 and win_lift <= -0.035 and place_lift <= -0.05:
        signal = "CONTEXT_RISK"
    else:
        signal = "NEUTRAL"

    if starts >= 150:
        evidence_band = "STRONG_EVIDENCE"
    elif starts >= 75:
        evidence_band = "PROMISING_EVIDENCE"
    elif starts >= 40:
        evidence_band = "MILD_EVIDENCE"
    else:
        evidence_band = "LIGHT_EVIDENCE"

    if signal == "CONTEXT_EDGE":
        insight = f"{trainer} has historically performed above baseline in {ctype.lower()} context: {cvalue}."
    elif signal == "MILD_CONTEXT_EDGE":
        insight = f"{trainer} has shown a mild positive profile in {ctype.lower()} context: {cvalue}."
    elif signal == "CONTEXT_RISK":
        insight = f"{trainer} has historically performed below baseline in {ctype.lower()} context: {cvalue}."
    else:
        insight = f"{trainer} has a neutral profile in {ctype.lower()} context: {cvalue}."

    out_rows.append({
        "entity_type": "TRAINER",
        "trainer": trainer,
        "context_type": ctype,
        "context_value": cvalue,
        "starts": starts,
        "wins": g["wins"],
        "places": g["places"],
        "win_pct": round(win_pct * 100, 2),
        "place_pct": round(place_pct * 100, 2),
        "trainer_base_starts": base_starts,
        "trainer_base_win_pct": round(base_win * 100, 2),
        "trainer_base_place_pct": round(base_place * 100, 2),
        "within_trainer_win_lift_pct": round(win_lift * 100, 2),
        "within_trainer_place_lift_pct": round(place_lift * 100, 2),
        "signal": signal,
        "evidence_band": evidence_band,
        "insight": insight,
    })

signal_order = {
    "CONTEXT_EDGE":0,
    "MILD_CONTEXT_EDGE":1,
    "CONTEXT_RISK":2,
    "NEUTRAL":3,
}

evidence_order = {
    "STRONG_EVIDENCE":0,
    "PROMISING_EVIDENCE":1,
    "MILD_EVIDENCE":2,
    "LIGHT_EVIDENCE":3,
}

out_rows.sort(
    key=lambda r: (
        signal_order.get(r["signal"],9),
        evidence_order.get(r["evidence_band"],9),
        -int(r["starts"]),
        r["trainer"]
    )
)

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
    writer.writeheader()
    writer.writerows(out_rows)

summary = [
    {"metric":"status","value":"COMPLETE"},
    {"metric":"source_rows","value":len(rows)},
    {"metric":"unique_trainers","value":len(trainer_base)},
    {"metric":"context_rows","value":len(out_rows)},
    {"metric":"context_edge","value":sum(1 for r in out_rows if r["signal"]=="CONTEXT_EDGE")},
    {"metric":"mild_context_edge","value":sum(1 for r in out_rows if r["signal"]=="MILD_CONTEXT_EDGE")},
    {"metric":"context_risk","value":sum(1 for r in out_rows if r["signal"]=="CONTEXT_RISK")},
    {"metric":"strong_evidence_rows","value":sum(1 for r in out_rows if r["evidence_band"]=="STRONG_EVIDENCE")},
    {"metric":"promising_evidence_rows","value":sum(1 for r in out_rows if r["evidence_band"]=="PROMISING_EVIDENCE")},
    {"metric":"built_at","value":datetime.now().isoformat()},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric","value"])
    writer.writeheader()
    writer.writerows(summary)

print("[EDGEIQ_TRAINER_CONTEXT_RESEARCH_V2] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
