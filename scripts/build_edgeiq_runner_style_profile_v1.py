import pandas as pd
import numpy as np
import re
from pathlib import Path

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SOURCE_FILE = DATA / "edgeiq_historical_run_style_v1.csv"

OUT_FILE = DATA / "edgeiq_runner_style_profile_v1.csv"
SUMMARY_FILE = DATA / "edgeiq_runner_style_profile_v1_summary.csv"

def txt(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def num(x):
    try:
        return float(str(x).strip())
    except:
        return np.nan

def horse_key(v):
    s = txt(v).upper()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s

def confidence(starts):
    if starts >= 20:
        return "HIGH"
    if starts >= 10:
        return "MEDIUM"
    if starts >= 5:
        return "LOW"
    return "VERY_LOW"

def dominant_style(row):
    vals = {
        "LEADER": row["leader_pct"],
        "ON_PACE": row["onpace_pct"],
        "MIDFIELD": row["midfield_pct"],
        "BACKMARKER": row["backmarker_pct"]
    }
    return max(vals, key=vals.get)

def movement_profile(avg_gain):
    if pd.isna(avg_gain):
        return "UNKNOWN"
    if avg_gain >= 1:
        return "IMPROVER"
    if avg_gain <= -1:
        return "FADER"
    return "HOLDS_POSITION"

df = pd.read_csv(SOURCE_FILE, dtype=str).fillna("")

print(f"[READ] {SOURCE_FILE.name} rows={len(df)}")

df["horse_key"] = df["horse"].apply(horse_key)

for col in [
    "pos800",
    "pos400",
    "gain_800_400"
]:
    if col in df.columns:
        df[col] = df[col].apply(num)

grp = df.groupby("horse_key", dropna=False)

rows = []

for hk, g in grp:

    horse_name = (
        g["horse"]
        .mode()
        .iloc[0]
        if len(g["horse"].mode()) > 0
        else g["horse"].iloc[0]
    )

    starts = len(g)

    leader_runs = (g["run_style_v1"] == "LEADER").sum()
    onpace_runs = (g["run_style_v1"] == "ON_PACE").sum()
    midfield_runs = (g["run_style_v1"] == "MIDFIELD").sum()
    backmarker_runs = (g["run_style_v1"] == "BACKMARKER").sum()

    leader_pct = round(100 * leader_runs / starts, 2)
    onpace_pct = round(100 * onpace_runs / starts, 2)
    midfield_pct = round(100 * midfield_runs / starts, 2)
    backmarker_pct = round(100 * backmarker_runs / starts, 2)

    avg_pos800 = round(g["pos800"].mean(), 2)
    avg_pos400 = round(g["pos400"].mean(), 2)
    avg_gain = round(g["gain_800_400"].mean(), 2)

    improver_pct = round(
        100 * (g["movement_profile_v1"] == "IMPROVER").sum() / starts,
        2
    )

    fader_pct = round(
        100 * (g["movement_profile_v1"] == "FADER").sum() / starts,
        2
    )

    hold_pct = round(
        100 * (g["movement_profile_v1"] == "HOLDS_POSITION").sum() / starts,
        2
    )

    row = {
        "horse": horse_name,
        "horse_key": hk,
        "starts": starts,

        "leader_runs": leader_runs,
        "onpace_runs": onpace_runs,
        "midfield_runs": midfield_runs,
        "backmarker_runs": backmarker_runs,

        "leader_pct": leader_pct,
        "onpace_pct": onpace_pct,
        "midfield_pct": midfield_pct,
        "backmarker_pct": backmarker_pct,

        "avg_pos800": avg_pos800,
        "avg_pos400": avg_pos400,
        "avg_gain_800_400": avg_gain,

        "improver_pct": improver_pct,
        "fader_pct": fader_pct,
        "holds_position_pct": hold_pct
    }

    row["dominant_run_style"] = dominant_style(row)
    row["movement_profile"] = movement_profile(avg_gain)
    row["style_confidence"] = confidence(starts)

    rows.append(row)

out = pd.DataFrame(rows)

out = out.sort_values(
    ["starts", "horse"],
    ascending=[False, True]
)

out.to_csv(OUT_FILE, index=False)

summary = pd.DataFrame([
    {"metric":"status","value":"COMPLETE"},
    {"metric":"source","value":SOURCE_FILE.name},
    {"metric":"source_rows","value":len(df)},
    {"metric":"horses","value":len(out)},
    {"metric":"high_confidence","value":(out["style_confidence"]=="HIGH").sum()},
    {"metric":"medium_confidence","value":(out["style_confidence"]=="MEDIUM").sum()},
    {"metric":"low_confidence","value":(out["style_confidence"]=="LOW").sum()},
    {"metric":"very_low_confidence","value":(out["style_confidence"]=="VERY_LOW").sum()},
    {"metric":"leader_profiles","value":(out["dominant_run_style"]=="LEADER").sum()},
    {"metric":"onpace_profiles","value":(out["dominant_run_style"]=="ON_PACE").sum()},
    {"metric":"midfield_profiles","value":(out["dominant_run_style"]=="MIDFIELD").sum()},
    {"metric":"backmarker_profiles","value":(out["dominant_run_style"]=="BACKMARKER").sum()},
    {"metric":"output","value":OUT_FILE.name}
])

summary.to_csv(SUMMARY_FILE,index=False)

print("[RUNNER_STYLE_PROFILE_V1] COMPLETE")
print(f"source_rows={len(df)}")
print(f"horses={len(out)}")
print(f"wrote={OUT_FILE}")
