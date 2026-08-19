from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PROJECTION = DATA / "edgeiq_current_field_projection_v5_2.csv"
SECTIONAL = DATA / "edgeiq_sectional_strength_v2.csv"
GENOME = DATA / "edgeiq_horse_genome_v3.csv"
PREDICTABILITY = DATA / "edgeiq_predictability_v1.csv"

OUTPUT = DATA / "edgeiq_strength_adjusted_ratings_v1.csv"
AUDIT = DATA / "edgeiq_strength_adjusted_ratings_v1_audit.csv"

def clean_key(v):
    if pd.isna(v):
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(v).upper())

def num(v):
    try:
        if pd.isna(v):
            return np.nan
        return float(v)
    except:
        return np.nan

def normalise(series):
    s = pd.to_numeric(series, errors="coerce")

    mn = s.min()
    mx = s.max()

    if pd.isna(mn) or pd.isna(mx) or mx <= mn:
        return pd.Series([50] * len(series), index=series.index)

    return ((s - mn) / (mx - mn) * 100).clip(0,100)

def band(v):
    if v >= 90:
        return "ELITE"
    if v >= 80:
        return "STRONG"
    if v >= 70:
        return "POSITIVE"
    if v >= 60:
        return "NEUTRAL"
    return "POOR"

def main():

    proj = pd.read_csv(PROJECTION)
    sec = pd.read_csv(SECTIONAL)
    gen = pd.read_csv(GENOME)
    pred = pd.read_csv(PREDICTABILITY)

    proj["horse_key_join"] = proj["horse_key"].apply(clean_key)
    sec["horse_key_join"] = sec["horse_key_join"].apply(clean_key)
    gen["horse_key_join"] = gen["horse_key"].apply(clean_key)
    pred["horse_key_join"] = pred["horse_key"].apply(clean_key)

    out = proj.copy()

    out = out.merge(
        sec[[
            "horse_key_join",
            "sectional_strength_rating",
            "sectional_strength_band"
        ]],
        on="horse_key_join",
        how="left"
    )

    out = out.merge(
        gen[[
            "horse_key_join",
            "horse_genome_score_v3",
            "horse_genome_band_v3"
        ]],
        on="horse_key_join",
        how="left"
    )

    out = out.merge(
        pred[[
            "horse_key_join",
            "predictability_score_v1",
            "predictability_band_v1"
        ]],
        on="horse_key_join",
        how="left"
    )

    projection_col = "projected_rating_v5_2"

    out["projection_norm"] = normalise(out[projection_col])

    out["sectional_norm"] = (
        out["sectional_strength_rating"]
        .fillna(50)
    )

    out["genome_norm"] = (
        out["horse_genome_score_v3"]
        .fillna(50)
    )

    out["predictability_norm"] = (
        out["predictability_score_v1"]
        .fillna(25)
    )

    out["strength_adjusted_rating_v1"] = (
        out["projection_norm"] * 0.40
        +
        out["sectional_norm"] * 0.25
        +
        out["genome_norm"] * 0.15
        +
        out["predictability_norm"] * 0.10
        +
        out["projection_norm"] * 0.10
    ).round(3)

    out["strength_adjusted_band_v1"] = (
        out["strength_adjusted_rating_v1"]
        .apply(band)
    )

    out["strength_adjusted_engine"] = "STRENGTH_ADJUSTED_V1"

    out.to_csv(OUTPUT,index=False)

    audit = pd.DataFrame([{
        "rows": len(out),
        "elite": int((out["strength_adjusted_band_v1"]=="ELITE").sum()),
        "strong": int((out["strength_adjusted_band_v1"]=="STRONG").sum()),
        "positive": int((out["strength_adjusted_band_v1"]=="POSITIVE").sum()),
        "neutral": int((out["strength_adjusted_band_v1"]=="NEUTRAL").sum()),
        "poor": int((out["strength_adjusted_band_v1"]=="POOR").sum()),
        "avg_rating": round(float(out["strength_adjusted_rating_v1"].mean()),3),
        "output": str(OUTPUT)
    }])

    audit.to_csv(AUDIT,index=False)

    print("[STRENGTH_ADJUSTED_V1] COMPLETE")
    print(f"rows={len(out)}")
    print(f"output={OUTPUT}")
    print(out["strength_adjusted_band_v1"].value_counts().to_string())

if __name__ == "__main__":
    main()
