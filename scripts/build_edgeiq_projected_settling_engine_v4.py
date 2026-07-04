from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[1]

LIVE_PATH = ROOT / "public" / "data" / "live_speed_map_v3.csv"
DNA_PATH = ROOT / "public" / "data" / "edgeiq_master_positional_dna_v1.csv"

OUT_PATH = ROOT / "public" / "data" / "edgeiq_projected_settling_engine_v4.csv"
DIAG_PATH = ROOT / "public" / "data" / "edgeiq_projected_settling_engine_v4_diagnostics.csv"

SUFFIXES = [
    " NZ",
    " GB",
    " IRE",
    " FR",
    " USA",
    " SAF",
    " GER",
    " JAP",
]

def canon(x):
    if pd.isna(x):
        return ""

    x = str(x).upper().strip()

    x = re.sub(r"\(.*?\)", "", x)

    for s in SUFFIXES:
        if x.endswith(s):
            x = x[:-len(s)]

    x = re.sub(r"[^A-Z0-9]", "", x)

    return x.strip()

def safe_float(x, default=np.nan):
    try:
        return float(x)
    except:
        return default

print("=" * 80)
print("EDGEIQ PROJECTED SETTLING ENGINE V4 PATCH")
print("=" * 80)

live = pd.read_csv(LIVE_PATH)
dna = pd.read_csv(DNA_PATH)

live.columns = [c.strip() for c in live.columns]
dna.columns = [c.strip() for c in dna.columns]

live_horse_col = None
dna_horse_col = None

for c in live.columns:
    if c.lower() in ["horse", "horse_name", "runner_name"]:
        live_horse_col = c
        break

for c in dna.columns:
    if c.lower() in ["horse", "horse_name", "runner_name"]:
        dna_horse_col = c
        break

live["canonical_horse"] = live[live_horse_col].apply(canon)
dna["canonical_horse"] = dna[dna_horse_col].apply(canon)

merged = live.merge(
    dna,
    on="canonical_horse",
    how="left",
    suffixes=("", "_dna")
)

confidence_col = None

for c in merged.columns:
    cl = c.lower()

    if "confidence" in cl and "tier" in cl:
        confidence_col = c
        break

rows = []

for _, r in merged.iterrows():

    horse = r.get(live_horse_col, "")

    barrier = safe_float(
        r.get("barrier", r.get("barrier_num", 8)),
        8
    )

    field_size = safe_float(
        r.get("field_size", 12),
        12
    )

    distance = safe_float(
        r.get("distance", 1400),
        1400
    )

    avg_800m_position = safe_float(
        r.get("avg_800m_position"),
        np.nan
    )

    early_speed_rating = safe_float(
        r.get("early_speed_rating"),
        np.nan
    )

    leader_pct = safe_float(r.get("leader_pct"), 0)
    onpace_pct = safe_float(r.get("onpace_pct"), 0)
    midfield_pct = safe_float(r.get("midfield_pct"), 0)
    backmarker_pct = safe_float(r.get("backmarker_pct"), 0)

    has_dna = not pd.isna(avg_800m_position)

    if has_dna:
        projected_spd = avg_800m_position
    else:
        projected_spd = field_size * 0.55

    if has_dna:

        if barrier <= 4:
            projected_spd -= 0.4

        elif barrier >= 12:
            projected_spd += 0.5

        if distance >= 1800:
            projected_spd += 0.4

        if early_speed_rating >= 85:
            projected_spd -= 1.0

        elif early_speed_rating >= 75:
            projected_spd -= 0.5

        if leader_pct >= 0.50:
            projected_spd -= 1.2

        elif leader_pct >= 0.30:
            projected_spd -= 0.6

        if backmarker_pct >= 0.50:
            projected_spd += 1.5

    projected_spd = round(
        max(1, min(projected_spd, field_size)),
        1
    )

    if projected_spd <= 2:
        settling_band = "LEADER"

    elif projected_spd <= 5:
        settling_band = "ON PACE"

    elif projected_spd <= 9:
        settling_band = "MIDFIELD"

    else:
        settling_band = "BACKMARKER"

    if has_dna:
        confidence = str(
            r.get(confidence_col, "MEDIUM")
        ).upper()
    else:
        confidence = "NO DNA"

    archetype = str(
        r.get("run_style_archetype", "")
    ).upper()

    note = (
        f"{settling_band} | "
        f"SPD {projected_spd} | "
        f"{confidence}"
    )

    rows.append({
        "horse": horse,
        "track": r.get("track", ""),
        "race_no": r.get("race_no", ""),
        "barrier": barrier,
        "distance": distance,
        "field_size": field_size,
        "avg_800m_position": avg_800m_position,
        "early_speed_rating": early_speed_rating,
        "leader_pct": leader_pct,
        "onpace_pct": onpace_pct,
        "midfield_pct": midfield_pct,
        "backmarker_pct": backmarker_pct,
        "projected_spd": projected_spd,
        "settling_band": settling_band,
        "confidence": confidence,
        "archetype": archetype,
        "settling_note": note,
    })

out = pd.DataFrame(rows)

out["race_key"] = (
    out["track"].astype(str)
    + "_R"
    + out["race_no"].astype(str)
)

out["settling_rank"] = (
    out.groupby("race_key")["projected_spd"]
    .rank(method="first")
)

out = out.sort_values(
    by=["track", "race_no", "projected_spd"],
    ascending=[True, True, True]
)

diag = pd.DataFrame([{
    "rows": len(out),
    "leaders": int((out["settling_band"] == "LEADER").sum()),
    "on_pace": int((out["settling_band"] == "ON PACE").sum()),
    "midfield": int((out["settling_band"] == "MIDFIELD").sum()),
    "backmarker": int((out["settling_band"] == "BACKMARKER").sum()),
    "high_confidence": int((out["confidence"] == "HIGH").sum()),
    "medium_confidence": int((out["confidence"] == "MEDIUM").sum()),
    "low_confidence": int((out["confidence"] == "LOW").sum()),
    "no_dna": int((out["confidence"] == "NO DNA").sum()),
}])

out.to_csv(OUT_PATH, index=False)
diag.to_csv(DIAG_PATH, index=False)

print()
print("=" * 80)
print("PATCH COMPLETE")
print("=" * 80)

print(out.head(40).to_string())

print()
print("=" * 80)
print("FILES WRITTEN")
print("=" * 80)

print(OUT_PATH)
print(DIAG_PATH)
