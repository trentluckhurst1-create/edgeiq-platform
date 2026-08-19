from pathlib import Path
import pandas as pd
import numpy as np
import re

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "dashboard" / "racing-dashboard"
PUBLIC = DASH / "public" / "data"

INFILE = PUBLIC / "all_horse_runs_rated.csv"
OUT = PUBLIC / "edgeiq_positional_dna_engine_v2.csv"
DIAG = PUBLIC / "edgeiq_positional_dna_engine_v2_diagnostics.csv"
OBS = PUBLIC / "edgeiq_positional_dna_observations_v2.csv"

def clean(x):
    return re.sub(r"\s+", " ", str(x or "").upper().strip())

def num(x, default=np.nan):
    try:
        s = str(x).strip()
        if not s:
            return default
        return float(re.sub(r"[^\d\.\-]", "", s))
    except Exception:
        return default

def parse_ordinal_position(raw, marker):
    s = str(raw or "")
    m = re.search(r"(\d+)(?:st|nd|rd|th)?\s*@" + str(marker) + r"m", s, re.I)
    return float(m.group(1)) if m else np.nan

def pct(mask):
    return round(float(mask.mean() * 100), 1) if len(mask) else 0.0

def style_from_avg(pos):
    if pd.isna(pos):
        return "UNKNOWN"
    if pos <= 3:
        return "LEADER"
    if pos <= 6:
        return "ON PACE"
    if pos <= 10:
        return "MIDFIELD"
    return "BACKMARKER"

if not INFILE.exists():
    raise SystemExit(f"MISSING INPUT: {INFILE}")

print("=" * 100)
print("EDGEIQ POSITIONAL DNA ENGINE V2")
print("=" * 100)
print(f"READING: {INFILE}")

df = pd.read_csv(INFILE, dtype=str, low_memory=False)

horse_col = "horse_name" if "horse_name" in df.columns else "horse"
raw_col = "in_run_positions_raw" if "in_run_positions_raw" in df.columns else "in_run"

rows = []

for _, r in df.iterrows():
    horse = clean(r.get(horse_col))
    if not horse:
        continue

    raw = r.get(raw_col, "")

    pos800 = parse_ordinal_position(raw, 800)
    pos400 = parse_ordinal_position(raw, 400)

    if pd.isna(pos800) and pd.isna(pos400):
        continue

    field_size = num(r.get("field_size_num") or r.get("field_size"))
    finish_pos = num(r.get("finish_pos_num") or r.get("finish_pos"))
    margin = num(r.get("margin_num") or r.get("margin"))
    last600 = num(r.get("sectional_600_seconds") or r.get("sectional_600"))
    sectional_fig = num(r.get("sectional_figure"))
    speed_fig = num(r.get("speed_figure"))
    distance = num(r.get("distance"))
    barrier = num(r.get("barrier_num") or r.get("barrier"))

    avg_early = np.nanmean([x for x in [pos800] if not pd.isna(x)]) if not pd.isna(pos800) else np.nan
    avg_turn = np.nanmean([x for x in [pos400] if not pd.isna(x)]) if not pd.isna(pos400) else np.nan

    gain_800_400 = np.nan
    if not pd.isna(pos800) and not pd.isna(pos400):
        gain_800_400 = pos800 - pos400

    early_bucket = style_from_avg(pos800)
    turn_bucket = style_from_avg(pos400)

    rows.append({
        "horse": horse,
        "horse_key": clean(r.get("horse_key_norm") or r.get("horse_key")),
        "run_date": r.get("run_date", ""),
        "track": r.get("track", ""),
        "distance": distance,
        "barrier": barrier,
        "field_size": field_size,
        "finish_pos": finish_pos,
        "margin": margin,
        "last600": last600,
        "sectional_figure": sectional_fig,
        "speed_figure": speed_fig,
        "raw_in_run": raw,
        "pos800": pos800,
        "pos400": pos400,
        "gain_800_400": gain_800_400,
        "early_bucket": early_bucket,
        "turn_bucket": turn_bucket,
    })

obs = pd.DataFrame(rows)

if obs.empty:
    raise SystemExit("NO VALID IN-RUN POSITIONAL OBSERVATIONS BUILT")

obs.to_csv(OBS, index=False)

summary_rows = []

for horse, g in obs.groupby("horse"):
    samples = len(g)

    avg800 = round(g["pos800"].mean(), 2) if g["pos800"].notna().any() else np.nan
    avg400 = round(g["pos400"].mean(), 2) if g["pos400"].notna().any() else np.nan
    avg_gain = round(g["gain_800_400"].mean(), 2) if g["gain_800_400"].notna().any() else np.nan

    leader_pct = pct(g["pos800"] <= 3)
    onpace_pct = pct((g["pos800"] > 3) & (g["pos800"] <= 6))
    midfield_pct = pct((g["pos800"] > 6) & (g["pos800"] <= 10))
    backmarker_pct = pct(g["pos800"] > 10)

    turn_leader_pct = pct(g["pos400"] <= 3)
    turn_onpace_pct = pct((g["pos400"] > 3) & (g["pos400"] <= 6))
    turn_midfield_pct = pct((g["pos400"] > 6) & (g["pos400"] <= 10))
    turn_backmarker_pct = pct(g["pos400"] > 10)

    early_speed_rating = 50
    if not pd.isna(avg800):
        early_speed_rating = round(max(1, min(100, 108 - (avg800 * 7.5))), 1)

    if leader_pct >= 45:
        archetype = "NATURAL LEADER"
    elif leader_pct + onpace_pct >= 60:
        archetype = "FORWARD / ON PACE"
    elif backmarker_pct >= 45:
        archetype = "BACKMARKER / CLOSER"
    elif midfield_pct >= 55:
        archetype = "MIDFIELD STALKER"
    else:
        archetype = "TACTICALLY FLEXIBLE"

    if not pd.isna(avg_gain):
        if avg_gain >= 3:
            movement = "SURGES MIDRACE"
        elif avg_gain >= 1:
            movement = "IMPROVES POSITION"
        elif avg_gain <= -3:
            movement = "LOSES POSITION"
        elif avg_gain <= -1:
            movement = "DRIFTS BACK"
        else:
            movement = "HOLDS POSITION"
    else:
        movement = "UNKNOWN"

    avg_last600 = round(g["last600"].mean(), 2) if g["last600"].notna().any() else np.nan
    avg_sectional_fig = round(g["sectional_figure"].mean(), 2) if g["sectional_figure"].notna().any() else np.nan
    avg_speed_fig = round(g["speed_figure"].mean(), 2) if g["speed_figure"].notna().any() else np.nan

    if samples >= 8:
        confidence = "HIGH"
    elif samples >= 3:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    summary_rows.append({
        "horse": horse,
        "samples": samples,
        "avg_800m_position": avg800,
        "avg_400m_position": avg400,
        "avg_800_to_400_gain": avg_gain,
        "leader_pct": leader_pct,
        "onpace_pct": onpace_pct,
        "midfield_pct": midfield_pct,
        "backmarker_pct": backmarker_pct,
        "turn_leader_pct": turn_leader_pct,
        "turn_onpace_pct": turn_onpace_pct,
        "turn_midfield_pct": turn_midfield_pct,
        "turn_backmarker_pct": turn_backmarker_pct,
        "early_speed_rating": early_speed_rating,
        "run_style_archetype": archetype,
        "positional_movement_profile": movement,
        "avg_last600": avg_last600,
        "avg_sectional_figure": avg_sectional_fig,
        "avg_speed_figure": avg_speed_fig,
        "positional_confidence": confidence,
    })

summary = pd.DataFrame(summary_rows)

confidence_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
summary["_confidence_rank"] = summary["positional_confidence"].map(confidence_rank).fillna(9)
summary = summary.sort_values(
    ["_confidence_rank", "early_speed_rating", "samples"],
    ascending=[True, False, False]
).drop(columns=["_confidence_rank"])

summary.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "horses": len(summary),
    "observations": len(obs),
    "high_confidence": int((summary["positional_confidence"] == "HIGH").sum()),
    "medium_confidence": int((summary["positional_confidence"] == "MEDIUM").sum()),
    "low_confidence": int((summary["positional_confidence"] == "LOW").sum()),
    "leaders": int((summary["run_style_archetype"] == "NATURAL LEADER").sum()),
    "forward_onpace": int((summary["run_style_archetype"] == "FORWARD / ON PACE").sum()),
    "backmarkers": int((summary["run_style_archetype"] == "BACKMARKER / CLOSER").sum()),
    "output": str(OUT),
    "observations_output": str(OBS),
}])

diag.to_csv(DIAG, index=False)

print("=" * 100)
print("POSITIONAL DNA V2 BUILT")
print("=" * 100)
print(diag.to_string(index=False))
print()
print(summary.head(40).to_string(index=False))
