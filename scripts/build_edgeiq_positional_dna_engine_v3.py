from pathlib import Path
import pandas as pd
import numpy as np
import re

PUBLIC = Path(r"public/data")

LIVE = PUBLIC / "live_speed_map_v3.csv"
OBS = PUBLIC / "edgeiq_positional_dna_observations_v2.csv"
OUT = PUBLIC / "edgeiq_positional_dna_engine_v3.csv"
DIAG = PUBLIC / "edgeiq_positional_dna_engine_v3_diagnostics.csv"

def clean(x):
    return re.sub(r"\s+", " ", str(x or "").upper().strip())

def strip_suffix(x):
    s = clean(x)
    s = re.sub(r"\s*\((NZ|GB|IRE|FR|USA|JPN|SAF|GER|ARG|BRZ|CAN|AUS)\)\s*$", "", s)
    return clean(s)

def compact(x):
    return re.sub(r"[^A-Z0-9]", "", strip_suffix(x))

def pct(mask):
    return round(float(mask.mean() * 100), 1) if len(mask) else 0.0

def archetype(row):
    if row["leader_pct"] >= 45:
        return "NATURAL LEADER"
    if row["leader_pct"] + row["onpace_pct"] >= 60:
        return "FORWARD / ON PACE"
    if row["backmarker_pct"] >= 45:
        return "BACKMARKER / CLOSER"
    if row["midfield_pct"] >= 55:
        return "MIDFIELD STALKER"
    return "TACTICALLY FLEXIBLE"

def confidence(samples):
    if samples >= 8:
        return "HIGH"
    if samples >= 3:
        return "MEDIUM"
    return "LOW"

obs = pd.read_csv(OBS, dtype=str, low_memory=False).fillna("")
live = pd.read_csv(LIVE, dtype=str, low_memory=False).fillna("")

obs["canonical_horse"] = obs["horse"].map(strip_suffix)
obs["canonical_key"] = obs["horse"].map(compact)
live["canonical_key"] = live["horse"].map(compact)

summary_rows = []

for canonical_key, g in obs.groupby("canonical_key"):
    if not canonical_key:
        continue

    horse = g["canonical_horse"].mode().iloc[0] if len(g["canonical_horse"].mode()) else g["canonical_horse"].iloc[0]

    g2 = g.copy()
    for c in ["pos800", "pos400", "gain_800_400", "last600", "sectional_figure", "speed_figure"]:
        g2[c] = pd.to_numeric(g2[c], errors="coerce")

    samples = len(g2)

    leader_pct = pct(g2["pos800"] <= 3)
    onpace_pct = pct((g2["pos800"] > 3) & (g2["pos800"] <= 6))
    midfield_pct = pct((g2["pos800"] > 6) & (g2["pos800"] <= 10))
    backmarker_pct = pct(g2["pos800"] > 10)

    avg800 = round(g2["pos800"].mean(), 2)
    avg400 = round(g2["pos400"].mean(), 2)
    gain = round(g2["gain_800_400"].mean(), 2)

    early_speed = round(max(1, min(100, 108 - (avg800 * 7.5))), 1) if pd.notna(avg800) else 50

    movement = "UNKNOWN"
    if pd.notna(gain):
        if gain >= 3:
            movement = "SURGES MIDRACE"
        elif gain >= 1:
            movement = "IMPROVES POSITION"
        elif gain <= -3:
            movement = "LOSES POSITION"
        elif gain <= -1:
            movement = "DRIFTS BACK"
        else:
            movement = "HOLDS POSITION"

    row = {
        "horse": horse,
        "canonical_key": canonical_key,
        "samples": samples,
        "avg_800m_position": avg800,
        "avg_400m_position": avg400,
        "avg_800_to_400_gain": gain,
        "leader_pct": leader_pct,
        "onpace_pct": onpace_pct,
        "midfield_pct": midfield_pct,
        "backmarker_pct": backmarker_pct,
        "early_speed_rating": early_speed,
        "positional_movement_profile": movement,
        "avg_last600": round(g2["last600"].mean(), 2),
        "avg_sectional_figure": round(g2["sectional_figure"].mean(), 2),
        "avg_speed_figure": round(g2["speed_figure"].mean(), 2),
        "positional_confidence": confidence(samples),
    }

    row["run_style_archetype"] = archetype(row)
    summary_rows.append(row)

out = pd.DataFrame(summary_rows)

out = out.sort_values(
    ["positional_confidence", "early_speed_rating", "samples"],
    ascending=[True, False, False]
)

out.to_csv(OUT, index=False)

live_keys = set(live["canonical_key"])
dna_keys = set(out["canonical_key"])
matched = live_keys & dna_keys

diag = pd.DataFrame([{
    "horses": len(out),
    "live_unique": len(live_keys),
    "matched_live": len(matched),
    "match_rate_pct": round(len(matched) / max(len(live_keys), 1) * 100, 2),
    "high_confidence": int((out["positional_confidence"] == "HIGH").sum()),
    "medium_confidence": int((out["positional_confidence"] == "MEDIUM").sum()),
    "low_confidence": int((out["positional_confidence"] == "LOW").sum()),
    "output": str(OUT),
}])

diag.to_csv(DIAG, index=False)

print("=" * 100)
print("EDGEIQ POSITIONAL DNA V3 BUILT - CANONICAL IDENTITY")
print("=" * 100)
print(diag.to_string(index=False))
print()
print(out.head(40).to_string(index=False))
