import csv
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

BASE = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = BASE / "public" / "data"

LIVE_CANDIDATES = [
    DATA / "edgeiq_live_runner_board_governed_v1.csv",
    DATA / "edgeiq_live_runner_board_v1.csv",
    DATA / "edgeiq_live_terminal_feed_v1.csv",
    DATA / "edgeiq_horse_intelligence_drawer_v1.csv",
    DATA / "edgeiq_trainer_jockey_runner_history_canonical_v1.csv",
]

CONTEXT = DATA / "edgeiq_context_warehouse_v1.csv"

OUT = DATA / "edgeiq_factor_selection_engine_v1.csv"
SUMMARY = DATA / "edgeiq_factor_selection_engine_v1_summary.csv"

def clean(v):
    return (v or "").strip()

def key(v):
    return re.sub(r"[^A-Z0-9]", "", clean(v).upper())

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
    if "MAIDEN" in s or s == "MDN": return "MAIDEN"
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

def pick_source():
    for p in LIVE_CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError("No live/source runner file found")

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def positive_signal(sig):
    return sig in {
        "POSITIVE_PROFILE",
        "STRONG_POSITIVE",
        "POSITIVE",
        "CONTEXT_EDGE",
        "MILD_CONTEXT_EDGE",
        "CONNECTION_EDGE",
        "MILD_CONNECTION_EDGE",
    }

def caution_signal(sig):
    return sig in {
        "CAUTION_PROFILE",
        "NEGATIVE",
        "CONTEXT_RISK",
        "CONNECTION_RISK",
    }

source = pick_source()
live_rows = read_csv(source)
context_rows = read_csv(CONTEXT)

ctx = defaultdict(list)

for r in context_rows:
    et = clean(r.get("entity_type")).upper()
    en = key(r.get("entity_name"))
    ct = clean(r.get("context_type")).upper()
    cv = clean(r.get("context_value")).upper()
    sig = clean(r.get("signal")).upper()

    if not et or not en or not ct or not cv:
        continue

    ctx[(et, en, ct, cv)].append(r)

def first_value(row, names):
    for n in names:
        v = clean(row.get(n))
        if v:
            return v
    return ""

out_rows = []

for r in live_rows:

    horse = first_value(r, ["horse_key","horse_canon","horse","runner","runner_name"])
    trainer = first_value(r, ["trainer_canonical","trainer","trainer_name"])
    jockey = first_value(r, ["jockey_canonical","jockey","jockey_name"])
    track = first_value(r, ["track","venue","meeting_track"])
    race_no = first_value(r, ["race_no","race_number"])
    distance = first_value(r, ["distance","race_distance"])
    condition = first_value(r, ["track_condition","condition","track_rating"])
    race_class = first_value(r, ["race_class","class","race_class_clean"])
    barrier = first_value(r, ["barrier","barrier_number","live_barrier"])
    sp = first_value(r, ["sp","starting_price","live_price","market_price","fixed_win","sportsbet_price"])

    horse_k = key(horse)
    trainer_k = key(trainer)
    jockey_k = key(jockey)
    connection_k = f"{trainer_k}{jockey_k}"

    derived_contexts = [
        ("TRACK", clean(track).upper()),
        ("DISTANCE", distance_bucket(distance)),
        ("CONDITION", condition_bucket(condition)),
        ("CLASS", class_bucket(race_class)),
        ("BARRIER", barrier_bucket(barrier)),
        ("SP", sp_bucket(sp)),
    ]

    positive = []
    caution = []

    entities = [
        ("HORSE", horse_k),
        ("TRAINER", trainer_k),
        ("JOCKEY", jockey_k),
    ]

    for et, en in entities:
        if not en:
            continue

        for ctype, cvalue in derived_contexts:
            if not cvalue or cvalue == "UNKNOWN":
                continue

            matches = ctx.get((et, en, ctype, cvalue), [])
            for m in matches:
                sig = clean(m.get("signal")).upper()
                label = f"{et.title()} {ctype.title()} Context"
                insight = clean(m.get("insight")) or f"{label}: {cvalue}"

                item = f"{label} — {insight}"

                if positive_signal(sig):
                    positive.append(item)
                elif caution_signal(sig):
                    caution.append(item)

    if trainer_k and jockey_k:
        for (et, en, ctype, cvalue), matches in ctx.items():
            if et != "CONNECTION":
                continue
            if trainer_k in en and jockey_k in en:
                for m in matches:
                    sig = clean(m.get("signal")).upper()
                    insight = clean(m.get("insight")) or "Trainer/Jockey connection context detected."
                    item = f"Connection Context — {insight}"
                    if positive_signal(sig):
                        positive.append(item)
                    elif caution_signal(sig):
                        caution.append(item)

    positive = list(dict.fromkeys(positive))
    caution = list(dict.fromkeys(caution))

    if len(positive) >= 3 and len(caution) == 0:
        assessment = "Multiple positive contexts align."
    elif len(positive) >= 2 and len(caution) >= 1:
        assessment = "Mixed context profile with positive and caution signals."
    elif len(positive) >= 1 and len(caution) == 0:
        assessment = "Positive context support detected."
    elif len(caution) >= 1 and len(positive) == 0:
        assessment = "Caution context detected."
    else:
        assessment = "No strong historical context signal detected."

    out_rows.append({
        "source_file": source.name,
        "race_date": first_value(r, ["race_date","meeting_date","date"]),
        "track": track,
        "race_no": race_no,
        "horse": horse,
        "trainer": trainer,
        "jockey": jockey,
        "distance": distance,
        "track_condition": condition,
        "race_class": race_class,
        "barrier": barrier,
        "sp_or_price": sp,
        "positive_factor_count": len(positive),
        "caution_factor_count": len(caution),
        "positive_factor_1": positive[0] if len(positive) > 0 else "",
        "positive_factor_2": positive[1] if len(positive) > 1 else "",
        "positive_factor_3": positive[2] if len(positive) > 2 else "",
        "caution_factor_1": caution[0] if len(caution) > 0 else "",
        "caution_factor_2": caution[1] if len(caution) > 1 else "",
        "edgeiq_assessment": assessment,
        "built_at": datetime.now().isoformat(),
    })

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
    writer.writeheader()
    writer.writerows(out_rows)

summary = [
    {"metric":"status","value":"COMPLETE"},
    {"metric":"source_file","value":source.name},
    {"metric":"source_rows","value":len(live_rows)},
    {"metric":"context_rows","value":len(context_rows)},
    {"metric":"output_rows","value":len(out_rows)},
    {"metric":"rows_with_positive_factors","value":sum(1 for r in out_rows if int(r["positive_factor_count"]) > 0)},
    {"metric":"rows_with_caution_factors","value":sum(1 for r in out_rows if int(r["caution_factor_count"]) > 0)},
    {"metric":"built_at","value":datetime.now().isoformat()},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric","value"])
    writer.writeheader()
    writer.writerows(summary)

print("[EDGEIQ_FACTOR_SELECTION_ENGINE_V1] COMPLETE")
print(f"source={source}")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
