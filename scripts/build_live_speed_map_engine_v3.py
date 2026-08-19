from pathlib import Path
import pandas as pd
import re

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"

OUT = PUBLIC / "live_speed_map_v3.csv"
DIAG = PUBLIC / "live_speed_map_v3_diagnostics.csv"

def read_csv(name):
    p = PUBLIC / name
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, dtype=str, keep_default_na=False)

def key(x):
    return re.sub(r"[^A-Z0-9]", "", str(x or "").upper())

def num(x, default=None):
    try:
        s = str(x).strip()
        if s == "":
            return default
        return float(s)
    except Exception:
        return default

def pick(row, cols, default=""):
    for c in cols:
        if c in row and str(row[c]).strip():
            return row[c]
    return default

fields = read_csv("race_fields.csv")
race_card = read_csv("race_card_report.csv")
historic_speed = read_csv("speed_map_report.csv")
memory = read_csv("edgeiq_universal_sectional_memory_v1.csv")

if fields.empty:
    raise SystemExit("race_fields.csv is empty/missing")

memory_lookup = {}
if not memory.empty:
    for _, r in memory.iterrows():
        hk = key(pick(r, ["horse_key", "horse"]))
        hn = key(pick(r, ["horse"]))
        if hk:
            memory_lookup[hk] = r
        if hn:
            memory_lookup[hn] = r

historic_lookup = {}
if not historic_speed.empty:
    for _, r in historic_speed.iterrows():
        hk = key(pick(r, ["horse_key", "horse"]))
        hn = key(pick(r, ["horse"]))
        if hk:
            historic_lookup[hk] = r
        if hn:
            historic_lookup[hn] = r

race_lookup = {}
if not race_card.empty:
    for _, r in race_card.iterrows():
        race_date = pick(r, ["race_date", "date"])
        track = pick(r, ["track", "meeting"])
        race_no = str(int(num(pick(r, ["race_no", "race_number"]), 0) or 0))
        race_lookup[(race_date, key(track), race_no)] = r

rows = []

for _, f in fields.iterrows():
    horse = pick(f, ["horse", "horse_name", "runner", "runner_name"])
    if not horse:
        continue

    horse_key = key(pick(f, ["horse_key", "runner_key"], horse))
    race_date = pick(f, ["race_date", "date"])
    track = pick(f, ["track", "meeting"])
    race_no = str(int(num(pick(f, ["race_no", "race_number", "race"]), 0) or 0))

    hist = historic_lookup.get(horse_key)
    if hist is None:
        hist = historic_lookup.get(key(horse))

    mem = memory_lookup.get(horse_key)
    if mem is None:
        mem = memory_lookup.get(key(horse))

    race = race_lookup.get((race_date, key(track), race_no), {})

    hist_bucket = pick(hist, ["speed_map_bucket", "map_style", "run_style"], "") if hist is not None else ""
    mem_style = pick(mem, ["projected_map_style"], "") if mem is not None else ""

    raw_style = hist_bucket or mem_style or "UNKNOWN"

    s = str(raw_style).upper()
    if "LEAD" in s:
        bucket = "LEADER"
    elif "ON PACE" in s or "PACE" in s:
        bucket = "ON PACE"
    elif "BACK" in s or "CLOS" in s or "LATE" in s:
        bucket = "BACKMARKER"
    elif "FIRST" in s:
        bucket = "FIRST START"
    elif "MID" in s:
        bucket = "MIDFIELD"
    else:
        bucket = "MIDFIELD"

    confidence = "LOW"
    if hist is not None and pick(hist, ["confidence"]):
        confidence = pick(hist, ["confidence"])
    elif mem is not None:
        confidence = pick(mem, ["coverage_grade"], "LOW")

    rows.append({
        "race_date": race_date,
        "track": track,
        "race_no": race_no,
        "race_time": pick(race, ["race_time", "time"]),
        "distance": pick(race, ["distance", "dist"]),
        "race_class": pick(race, ["race_class", "class"]),
        "track_condition": pick(race, ["track_condition", "condition"]),

        "horse_no": pick(f, ["horse_no", "saddlecloth", "number", "tab_no", "runner_number"]),
        "horse": horse,
        "horse_key": horse_key,
        "barrier": pick(f, ["barrier", "gate", "bar"]),

        "speed_map_bucket": bucket,
        "map_style": bucket,
        "confidence": confidence,

        "historic_speed_bucket": hist_bucket,
        "memory_projected_map_style": mem_style,
        "memory_coverage_grade": pick(mem, ["coverage_grade"], "") if mem is not None else "",
        "memory_note": pick(mem, ["memory_note"], "") if mem is not None else "",

        "sectional_profile": pick(mem, ["sectional_profile"], "") if mem is not None else "",
        "run_style_cluster": pick(mem, ["run_style_cluster"], "") if mem is not None else "",
        "projected_tempo_shape": pick(mem, ["best_tempo_setup"], "") if mem is not None else "",
        "pace_collapse_risk": "HIGH" if mem is not None and pick(mem, ["best_tempo_setup"]) == "HOT_TEMPO_COLLAPSE" else "",
        "tempo_fit": pick(mem, ["best_tempo_setup"], "") if mem is not None else "",
        "sectional_weapon_score": pick(mem, ["sectional_weapon_score"], "") if mem is not None else "",
        "late_power_index": pick(mem, ["late_power_index"], "") if mem is not None else "",
        "burst_index": pick(mem, ["burst_index"], "") if mem is not None else "",
        "sustain_index": pick(mem, ["sustain_index"], "") if mem is not None else "",
        "fatigue_risk_index": pick(mem, ["fatigue_risk_index"], "") if mem is not None else "",

        "source": "LIVE_FIELDS_PLUS_HISTORIC_SPEED_PLUS_UNIVERSAL_SECTIONAL_MEMORY",
    })

out = pd.DataFrame(rows)

if out.empty:
    raise SystemExit("No live speed map v3 rows built")

out.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "rows": len(out),
    "unique_races": out[["race_date", "track", "race_no"]].drop_duplicates().shape[0],
    "unique_tracks": out["track"].nunique(),
    "with_barrier": int((out["barrier"].astype(str).str.strip() != "").sum()),
    "with_sectional_weapon": int((out["sectional_weapon_score"].astype(str).str.strip() != "").sum()),
    "with_memory_match": int((out["memory_coverage_grade"].astype(str).str.strip() != "").sum()),
    "with_historic_speed": int((out["historic_speed_bucket"].astype(str).str.strip() != "").sum()),
    "output": str(OUT),
}])

diag.to_csv(DIAG, index=False)

print("=" * 100)
print("EDGEIQ LIVE SPEED MAP V3 BUILT")
print("=" * 100)
print(diag.to_string(index=False))
print()
print(out.head(30).to_string(index=False))
