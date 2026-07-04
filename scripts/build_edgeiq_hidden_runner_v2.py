from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "edgeiq_market_rank_v1.csv"

OUTPUT = DATA / "edgeiq_hidden_runner_v2.csv"
AUDIT = DATA / "edgeiq_hidden_runner_v2_audit.csv"

def num(v):
    try:
        return float(v)
    except:
        return 0.0

def hidden_band(v):
    if v >= 90:
        return "ELITE_HIDDEN"
    if v >= 80:
        return "STRONG_HIDDEN"
    if v >= 70:
        return "HIDDEN"
    if v >= 60:
        return "WATCH"
    return "NONE"

def edge_score(edge):

    edge = num(edge)

    if edge >= 16:
        return 100

    if edge >= 12:
        return 90

    if edge >= 8:
        return 80

    if edge >= 5:
        return 70

    if edge >= 3:
        return 60

    if edge >= 0:
        return 50

    if edge >= -3:
        return 30

    if edge >= -5:
        return 20

    return 0

def build_reason(r):

    bits = []

    edge = num(r["shape_edge_v1"])
    fit = num(r["race_shape_fit_score_v1"])

    if edge >= 12:
        bits.append("massive market mismatch")

    elif edge >= 8:
        bits.append("strong market mismatch")

    elif edge >= 5:
        bits.append("positive market mismatch")

    if fit >= 85:
        bits.append("elite shape fit")

    elif fit >= 75:
        bits.append("strong shape fit")

    if str(r.get("ability_dna_v3","")).startswith("POWER"):
        bits.append("power profile")

    if str(r.get("sectional_strength_band","")) in ["ELITE","STRONG"]:
        bits.append("strong sectionals")

    return "; ".join(bits)

def main():

    df = pd.read_csv(INPUT)

    df["fit"] = pd.to_numeric(
        df["race_shape_fit_score_v1"],
        errors="coerce"
    ).fillna(0)

    df["power"] = pd.to_numeric(
        df["dna_power_rating_v3"],
        errors="coerce"
    ).fillna(0)

    df["sectional"] = pd.to_numeric(
        df["sectional_strength_rating"],
        errors="coerce"
    ).fillna(0)

    df["shape_edge_score_v1"] = (
        df["shape_edge_v1"]
        .apply(edge_score)
    )

    df["hidden_runner_score_v2"] = (
        df["fit"] * 0.35 +
        df["shape_edge_score_v1"] * 0.35 +
        df["power"] * 0.20 +
        df["sectional"] * 0.10
    ).round(3)

    df["hidden_runner_band_v2"] = (
        df["hidden_runner_score_v2"]
        .apply(hidden_band)
    )

    df["hidden_runner_reason_v2"] = (
        df.apply(build_reason, axis=1)
    )

    df.to_csv(OUTPUT, index=False)

    audit = pd.DataFrame([{
        "rows": len(df),
        "elite_hidden": int((df["hidden_runner_band_v2"]=="ELITE_HIDDEN").sum()),
        "strong_hidden": int((df["hidden_runner_band_v2"]=="STRONG_HIDDEN").sum()),
        "hidden": int((df["hidden_runner_band_v2"]=="HIDDEN").sum()),
        "watch": int((df["hidden_runner_band_v2"]=="WATCH").sum()),
        "none": int((df["hidden_runner_band_v2"]=="NONE").sum()),
        "avg_score": round(
            float(df["hidden_runner_score_v2"].mean()),
            3
        ),
        "output": str(OUTPUT)
    }])

    audit.to_csv(AUDIT, index=False)

    print("[HIDDEN_RUNNER_V2] COMPLETE")
    print(f"rows={len(df)}")
    print(df["hidden_runner_band_v2"].value_counts().to_string())

if __name__ == "__main__":
    main()
