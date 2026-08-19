from pathlib import Path
import pandas as pd
import numpy as np
import re

PUBLIC = Path(r"public/data")

LIVE = PUBLIC / "live_speed_map_v3.csv"
DNA = PUBLIC / "edgeiq_positional_dna_engine_v2.csv"
OUT = PUBLIC / "edgeiq_projected_settling_engine_v3.csv"
DIAG = PUBLIC / "edgeiq_projected_settling_engine_v3_diagnostics.csv"

def clean(x):
    return re.sub(r"\s+", " ", str(x or "").upper().strip())

def key(x):
    return re.sub(r"[^A-Z0-9]", "", clean(x))

def num(x, default=np.nan):
    try:
        s = str(x).strip()
        if not s:
            return default
        return float(re.sub(r"[^\d\.\-]", "", s))
    except:
        return default

def read(path):
    if not path.exists():
        raise SystemExit(f"MISSING INPUT: {path}")
    return pd.read_csv(path, dtype=str, low_memory=False).fillna("")

print("=" * 100)
print("EDGEIQ PROJECTED SETTLING ENGINE V3")
print("=" * 100)

live = read(LIVE)
dna = read(DNA)

dna["_key"] = dna["horse"].map(key)
dna_map = {r["_key"]: r for _, r in dna.iterrows()}

rows = []

for (race_date, track, race_no), g in live.groupby(["race_date", "track", "race_no"], dropna=False):
    field_size = len(g)

    for _, r in g.iterrows():
        horse = r.get("horse", "")
        k = key(horse)
        d = dna_map.get(k)

        barrier = num(r.get("barrier"), 0)
        distance = num(r.get("distance"), 0)

        if d is not None:
            avg800 = num(d.get("avg_800m_position"), np.nan)
            avg400 = num(d.get("avg_400m_position"), np.nan)
            early_speed = num(d.get("early_speed_rating"), 50)
            leader_pct = num(d.get("leader_pct"), 0)
            onpace_pct = num(d.get("onpace_pct"), 0)
            midfield_pct = num(d.get("midfield_pct"), 0)
            backmarker_pct = num(d.get("backmarker_pct"), 0)
            archetype = d.get("run_style_archetype", "UNKNOWN")
            movement = d.get("positional_movement_profile", "UNKNOWN")
            confidence = d.get("positional_confidence", "LOW")
            samples = num(d.get("samples"), 0)
        else:
            avg800 = np.nan
            avg400 = np.nan
            early_speed = 50
            leader_pct = 0
            onpace_pct = 0
            midfield_pct = 100
            backmarker_pct = 0
            archetype = "UNKNOWN"
            movement = "UNKNOWN"
            confidence = "NO DNA"
            samples = 0

        # Lower projected_spd = more forward. Higher = further back.
        if not np.isnan(avg800):
            projected_spd = round(min(100, max(1, avg800 * 8.6)), 1)
        else:
            projected_spd = 58.0

        # Barrier influence: wide draws push forward horses slightly back; inside draws help.
        if barrier > 0 and field_size > 0:
            barrier_pct = barrier / max(field_size, 1)
            if leader_pct + onpace_pct >= 50:
                projected_spd += round((barrier_pct - 0.5) * 12, 1)
            elif backmarker_pct >= 40:
                projected_spd += round((barrier_pct - 0.5) * 4, 1)
            else:
                projected_spd += round((barrier_pct - 0.5) * 7, 1)

        # Distance influence: sprints reward early speed; staying races allow settling deeper.
        if distance and distance <= 1200:
            projected_spd -= 4
        elif distance and distance >= 2000:
            projected_spd += 4

        projected_spd = round(min(100, max(1, projected_spd)), 1)

        if projected_spd <= 28:
            settling_band = "LEADER"
        elif projected_spd <= 45:
            settling_band = "ON PACE"
        elif projected_spd <= 72:
            settling_band = "MIDFIELD"
        else:
            settling_band = "BACKMARKER"

        rows.append({
            "race_date": race_date,
            "track": track,
            "race_no": race_no,
            "horse": horse,
            "horse_key": r.get("horse_key", ""),
            "saddlecloth": r.get("horse_no", ""),
            "barrier": r.get("barrier", ""),
            "distance": r.get("distance", ""),
            "projected_spd": projected_spd,
            "settling_band": settling_band,
            "avg_800m_position": "" if np.isnan(avg800) else round(avg800, 2),
            "avg_400m_position": "" if np.isnan(avg400) else round(avg400, 2),
            "leader_pct": leader_pct,
            "onpace_pct": onpace_pct,
            "midfield_pct": midfield_pct,
            "backmarker_pct": backmarker_pct,
            "early_speed_rating": early_speed,
            "run_style_archetype": archetype,
            "positional_movement_profile": movement,
            "positional_confidence": confidence,
            "dna_samples": samples,
            "settling_note": f"{settling_band} | SPD {projected_spd} | {archetype} | {confidence}",
        })

out = pd.DataFrame(rows).sort_values(["race_date", "track", "race_no", "projected_spd"])

out.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "rows": len(out),
    "races": out[["race_date","track","race_no"]].drop_duplicates().shape[0],
    "with_dna": int((out["positional_confidence"] != "NO DNA").sum()),
    "leaders": int((out["settling_band"] == "LEADER").sum()),
    "onpace": int((out["settling_band"] == "ON PACE").sum()),
    "midfield": int((out["settling_band"] == "MIDFIELD").sum()),
    "backmarkers": int((out["settling_band"] == "BACKMARKER").sum()),
    "output": str(OUT),
}])

diag.to_csv(DIAG, index=False)

print(diag.to_string(index=False))
print()
print(out.head(50).to_string(index=False))
