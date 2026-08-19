from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "edgeiq_horse_genome_v3.csv"

OUTPUT = DATA / "edgeiq_predictability_v1.csv"
AUDIT = DATA / "edgeiq_predictability_v1_audit.csv"

def num(v):
    try:
        if pd.isna(v):
            return np.nan
        return float(v)
    except:
        return np.nan

def confidence(starts):
    starts = int(starts)

    if starts >= 30:
        return "HIGH"

    if starts >= 15:
        return "MEDIUM"

    if starts >= 5:
        return "LOW"

    return "VERY_LOW"

def reliability(starts):
    starts = int(starts)

    if starts >= 50:
        return 1.00

    if starts >= 30:
        return 0.95

    if starts >= 20:
        return 0.90

    if starts >= 10:
        return 0.80

    if starts >= 5:
        return 0.65

    if starts >= 3:
        return 0.50

    return 0.25

def band(score):
    if score >= 55:
        return "VERY_PREDICTABLE"
    if score >= 45:
        return "PREDICTABLE"
    if score >= 35:
        return "NORMAL"
    if score >= 25:
        return "VOLATILE"
    return "CHAOTIC"

def main():

    if not INPUT.exists():
        raise FileNotFoundError(INPUT)

    df = pd.read_csv(INPUT)

    df["starts_v2"] = pd.to_numeric(df["starts_v2"], errors="coerce").fillna(0)
    df["finish_std_v3"] = pd.to_numeric(df["finish_std_v3"], errors="coerce").fillna(999)
    df["place_pct_v2"] = pd.to_numeric(df["place_pct_v2"], errors="coerce").fillna(0)
    df["win_pct_v2"] = pd.to_numeric(df["win_pct_v2"], errors="coerce").fillna(0)

    max_std = df["finish_std_v3"].replace(0,np.nan).quantile(0.95)

    if pd.isna(max_std):
        max_std = 10

    df["variance_component"] = (
        100 -
        (
            (df["finish_std_v3"] / max_std)
            * 100
        )
    ).clip(0,100)

    df["place_component"] = (
        df["place_pct_v2"] * 100
    ).clip(0,100)

    df["win_component"] = (
        df["win_pct_v2"] * 100
    ).clip(0,100)

    df["reliability_factor"] = (
        df["starts_v2"]
        .astype(int)
        .apply(reliability)
    )

    df["raw_predictability_score_v1"] = (
        df["variance_component"] * 0.50
        +
        df["place_component"] * 0.30
        +
        df["win_component"] * 0.20
    )

    df["predictability_score_v1"] = (
        df["raw_predictability_score_v1"]
        *
        df["reliability_factor"]
    ).round(3)

    df["predictability_band_v1"] = (
        df["predictability_score_v1"]
        .apply(band)
    )

    df["predictability_confidence_v1"] = (
        df["starts_v2"]
        .astype(int)
        .apply(confidence)
    )

    df["predictability_engine"] = "PREDICTABILITY_V1"

    df = df.sort_values(
        "predictability_score_v1",
        ascending=False
    )

    df.to_csv(OUTPUT,index=False)

    audit = pd.DataFrame([{
        "horses": len(df),
        "very_predictable": int((df["predictability_band_v1"]=="VERY_PREDICTABLE").sum()),
        "predictable": int((df["predictability_band_v1"]=="PREDICTABLE").sum()),
        "normal": int((df["predictability_band_v1"]=="NORMAL").sum()),
        "volatile": int((df["predictability_band_v1"]=="VOLATILE").sum()),
        "chaotic": int((df["predictability_band_v1"]=="CHAOTIC").sum()),
        "avg_score": round(float(df["predictability_score_v1"].mean()),3),
        "output": str(OUTPUT)
    }])

    audit.to_csv(AUDIT,index=False)

    print("[PREDICTABILITY_V1] COMPLETE")
    print(f"horses={len(df)}")
    print(f"output={OUTPUT}")
    print(df["predictability_band_v1"].value_counts().to_string())

if __name__ == "__main__":
    main()

