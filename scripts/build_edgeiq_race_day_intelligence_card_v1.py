from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

runner_file = DATA / "edgeiq_live_runner_board_v1.csv"
race_shape_file = DATA / "edgeiq_race_shape_story_v1.csv"
track_file = DATA / "edgeiq_track_intelligence_card_v1.csv"

out_file = DATA / "edgeiq_race_day_intelligence_card_v1.csv"
summary_file = DATA / "edgeiq_race_day_intelligence_card_v1_summary.csv"

def read_csv(path):
    if path.exists():
        return pd.read_csv(path, dtype=str).fillna("")
    return pd.DataFrame()

def first(row, cols, default=""):
    for c in cols:
        if c in row and str(row[c]).strip():
            return str(row[c]).strip()
    return default

def norm_key(*parts):
    return "_".join(str(p).strip().upper() for p in parts if str(p).strip())

runner = read_csv(runner_file)
shape = read_csv(race_shape_file)
track = read_csv(track_file)

if runner.empty:
    raise SystemExit(f"Missing or empty runner board: {runner_file}")

race_rows = []

group_cols = ["race_date", "track", "race_no", "race_key"]
available_group_cols = [c for c in group_cols if c in runner.columns]

if "race_key" in runner.columns:
    groups = runner.groupby("race_key", dropna=False)
else:
    groups = runner.groupby(["track", "race_no"], dropna=False)

shape_lookup = {}
if not shape.empty:
    for _, r in shape.iterrows():
        key = first(r, ["race_key"], "")
        if not key:
            key = norm_key(first(r, ["track"]), first(r, ["race_no"]))
        shape_lookup[key] = r

track_lookup = {}
if not track.empty:
    for _, r in track.iterrows():
        key = norm_key(first(r, ["track"]))
        track_lookup[key] = r

for key, g in groups:
    base = g.iloc[0].to_dict()

    race_key = first(base, ["race_key"], str(key))
    track_name = first(base, ["track"], "")
    race_no = first(base, ["race_no"], "")

    shape_row = shape_lookup.get(race_key)
    if shape_row is None:
        shape_row = shape_lookup.get(norm_key(track_name, race_no), {})

    track_row = track_lookup.get(norm_key(track_name), {})

    condition = first(base, ["track_condition", "condition", "track_condition_clean"], "")
    rail = first(base, ["rail", "rail_position", "rail_position_clean"], "")

    distance = first(base, ["distance", "race_distance", "distance_m"], "")
    race_class = first(base, ["race_class", "class", "race_class_clean"], "")

    tempo = first(shape_row, ["expected_tempo", "tempo", "race_tempo"], "")
    if not tempo:
        tempo = first(base, ["expected_tempo", "tempo"], "Not assessed")

    race_shape = first(shape_row, ["race_shape_story", "race_shape_narrative", "shape_story", "summary"], "")
    if not race_shape:
        race_shape = "Race shape is still forming from available runner and pace data."

    track_profile = first(track_row, ["track_dna_style", "track_profile", "track_style"], "")
    track_confidence = first(track_row, ["track_dna_confidence", "confidence", "track_confidence"], "")

    if not track_profile:
        track_profile = "No strong track pattern flagged"
    if not track_confidence:
        track_confidence = "LOW"

    active = g[g.get("runner_status", "").astype(str).str.upper().ne("SCRATCHED")] if "runner_status" in g.columns else g
    active_count = len(active)

    early = 0
    midfield = 0
    back = 0

    for _, rr in active.iterrows():
        style = first(rr, ["run_style", "settling_band", "map_position", "pace_profile"], "").upper()
        if any(x in style for x in ["LEAD", "ON PACE", "ON-PACE", "FRONT"]):
            early += 1
        elif any(x in style for x in ["MID", "MIDDLE"]):
            midfield += 1
        elif any(x in style for x in ["BACK", "REAR", "CLOSER"]):
            back += 1

    if early >= 4:
        pressure = "Genuine pressure expected"
    elif early >= 2:
        pressure = "Moderate early pressure"
    elif early == 1:
        pressure = "Single-leader scenario possible"
    else:
        pressure = "Tempo unclear from available map data"

    race_read = race_shape
    if track_profile and track_profile != "No strong track pattern flagged":
        race_read = f"{race_read} Track profile: {track_profile}."

    race_rows.append({
        "race_date": first(base, ["race_date"], ""),
        "day_bucket": first(base, ["day_bucket"], ""),
        "track": track_name,
        "race_no": race_no,
        "race_key": race_key,
        "distance": distance,
        "race_class": race_class,
        "track_condition": condition,
        "rail": rail,
        "expected_tempo": tempo,
        "map_pressure": pressure,
        "track_profile": track_profile,
        "track_confidence": track_confidence,
        "active_runners": active_count,
        "early_speed_count": early,
        "midfield_count": midfield,
        "backmarker_count": back,
        "race_day_read": race_read,
        "customer_summary": f"{condition or 'Track condition not listed'} | {rail or 'Rail not listed'} | {tempo} | {pressure}",
        "built_at": datetime.now(timezone.utc).isoformat(),
    })

out = pd.DataFrame(race_rows)
out.to_csv(out_file, index=False)

summary = pd.DataFrame([{
    "status": "EDGEIQ_RACE_DAY_INTELLIGENCE_CARD_V1_BUILT",
    "rows": len(out),
    "with_track_condition": int((out["track_condition"].astype(str).str.len() > 0).sum()) if len(out) else 0,
    "with_rail": int((out["rail"].astype(str).str.len() > 0).sum()) if len(out) else 0,
    "with_race_day_read": int((out["race_day_read"].astype(str).str.len() > 0).sum()) if len(out) else 0,
    "built_at": datetime.now(timezone.utc).isoformat(),
}])
summary.to_csv(summary_file, index=False)

print("[EDGEIQ_RACE_DAY_INTELLIGENCE_CARD_V1] COMPLETE")
print(f"out={out_file}")
print(f"summary={summary_file}")
