from pathlib import Path
import pandas as pd
import re

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"

OUT = PUBLIC / "live_speed_map_v2.csv"
DIAG = PUBLIC / "live_speed_map_v2_diagnostics.csv"

def read_csv(name):
    p = PUBLIC / name
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, dtype=str, keep_default_na=False)

def key(x):
    return re.sub(r"[^A-Z0-9]", "", str(x or "").upper())

def num(x, default=None):
    try:
        if str(x).strip() == "":
            return default
        return float(x)
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
sectional = read_csv("edgeiq_sectional_tempo_engine_v1.csv")

if fields.empty:
    raise SystemExit("race_fields.csv is empty/missing")

# Build sectional lookup by horse key and horse name
sectional_lookup = {}
if not sectional.empty:
    for _, r in sectional.iterrows():
        hk = key(pick(r, ["horse_key", "horse", "horse_sectional"]))
        hn = key(pick(r, ["horse", "horse_sectional"]))
        if hk:
            sectional_lookup[hk] = r
        if hn:
            sectional_lookup[hn] = r

# Build historic speed lookup by horse key and horse name
historic_lookup = {}
if not historic_speed.empty:
    for _, r in historic_speed.iterrows():
        hk = key(pick(r, ["horse_key", "horse"]))
        hn = key(pick(r, ["horse"]))
        if hk:
            historic_lookup[hk] = r
        if hn:
            historic_lookup[hn] = r

# Race card lookup for time/dist/class/condition
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

    barrier = pick(f, ["barrier", "gate", "bar"])
    horse_no = pick(f, ["horse_no", "saddlecloth", "number", "tab_no", "runner_number"])

    hist = historic_lookup.get(horse_key)
    if hist is None:
        hist = historic_lookup.get(key(horse))
    sec = sectional_lookup.get(horse_key)
    if sec is None:
        sec = sectional_lookup.get(key(horse))
    race = race_lookup.get((race_date, key(track), race_no), {})

    hist_bucket = pick(hist, ["speed_map_bucket", "map_style", "run_style"], "") if hist is not None else ""
    sec_cluster = pick(sec, ["run_style_cluster", "sectional_profile"], "") if sec is not None else ""
    tempo_role = pick(sec, ["tempo_role"], "") if sec is not None else ""

    # Basic projected style hierarchy
    raw_style = hist_bucket or tempo_role or sec_cluster or "UNKNOWN"

    s = str(raw_style).upper()
    if "LEAD" in s:
        bucket = "LEADER"
    elif "PACE" in s or "ON" in s:
        bucket = "ON PACE"
    elif "BACK" in s or "CLOS" in s or "LATE" in s or "SUSTAIN" in s:
        bucket = "BACKMARKER"
    elif "MID" in s:
        bucket = "MIDFIELD"
    elif "FIRST" in s:
        bucket = "FIRST START"
    else:
        bucket = "MIDFIELD"

    confidence = "LOW"
    if hist is not None and pick(hist, ["confidence"]):
        confidence = pick(hist, ["confidence"])
    elif sec is not None and pick(sec, ["tempo_edge_grade", "sectional_confidence"]):
        confidence = pick(sec, ["tempo_edge_grade", "sectional_confidence"])

    rows.append({
        "race_date": race_date,
        "track": track,
        "race_no": race_no,
        "race_time": pick(race, ["race_time", "time"]),
        "distance": pick(race, ["distance", "dist"]),
        "race_class": pick(race, ["race_class", "class"]),
        "track_condition": pick(race, ["track_condition", "condition"]),

        "horse_no": horse_no,
        "horse": horse,
        "horse_key": horse_key,
        "barrier": barrier,

        "speed_map_bucket": bucket,
        "map_style": bucket,
        "confidence": confidence,

        "historic_speed_bucket": hist_bucket,
        "sectional_profile": pick(sec, ["sectional_profile"], "") if sec is not None else "",
        "run_style_cluster": sec_cluster,
        "tempo_role": tempo_role,
        "projected_tempo_shape": pick(sec, ["projected_tempo_shape"], "") if sec is not None else "",
        "pace_collapse_risk": pick(sec, ["pace_collapse_risk"], "") if sec is not None else "",
        "tempo_fit": pick(sec, ["tempo_fit"], "") if sec is not None else "",
        "sectional_weapon_score": pick(sec, ["sectional_weapon_score"], "") if sec is not None else "",
        "late_power_index": pick(sec, ["late_power_index"], "") if sec is not None else "",
        "burst_index": pick(sec, ["burst_index"], "") if sec is not None else "",
        "sustain_index": pick(sec, ["sustain_index"], "") if sec is not None else "",
        "fatigue_risk_index": pick(sec, ["fatigue_risk_index"], "") if sec is not None else "",

        "source": "LIVE_FIELDS_PLUS_HISTORIC_SPEED_PLUS_SECTIONAL_TEMPO",
    })

out = pd.DataFrame(rows)

if out.empty:
    raise SystemExit("No live speed map rows built")

out.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "rows": len(out),
    "unique_races": out[["race_date", "track", "race_no"]].drop_duplicates().shape[0],
    "unique_tracks": out["track"].nunique(),
    "with_barrier": int((out["barrier"].astype(str).str.strip() != "").sum()),
    "with_sectional_weapon": int((out["sectional_weapon_score"].astype(str).str.strip() != "").sum()),
    "with_historic_speed": int((out["historic_speed_bucket"].astype(str).str.strip() != "").sum()),
    "output": str(OUT),
}])
diag.to_csv(DIAG, index=False)

print("=" * 90)
print("EDGEIQ LIVE SPEED MAP V2 BUILT")
print("=" * 90)
print(diag.to_string(index=False))
print()
print(out.head(20).to_string(index=False))
