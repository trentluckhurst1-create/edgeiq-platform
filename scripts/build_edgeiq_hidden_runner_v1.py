from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "edgeiq_race_shape_fit_v1.csv"

OUTPUT = DATA / "edgeiq_hidden_runner_v1.csv"
AUDIT = DATA / "edgeiq_hidden_runner_v1_audit.csv"

def num(v):
    try:
        return float(v)
    except:
        return 0.0

def confidence_score(v):
    v = str(v).upper().strip()

    if v == "VERY_HIGH":
        return 100

    if v == "HIGH":
        return 85

    if v == "MEDIUM":
        return 65

    return 40

def hidden_band(score):
    if score >= 85:
        return "ELITE_HIDDEN"

    if score >= 75:
        return "STRONG_HIDDEN"

    if score >= 65:
        return "HIDDEN"

    if score >= 55:
        return "WATCH"

    return "NONE"

def main():

    df = pd.read_csv(INPUT)

    df["shape_fit"] = pd.to_numeric(
        df["race_shape_fit_score_v1"],
        errors="coerce"
    ).fillna(0)

    df["percentile"] = pd.to_numeric(
        df["shape_fit_percentile_in_race"],
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

    df["confidence_component"] = (
        df["shape_fit_confidence_v1"]
        .apply(confidence_score)
    )

    df["hidden_runner_score_v1"] = (
        df["shape_fit"] * 0.40 +
        df["percentile"] * 0.25 +
        df["power"] * 0.20 +
        df["sectional"] * 0.10 +
        df["confidence_component"] * 0.05
    ).round(3)

    df["hidden_runner_band_v1"] = (
        df["hidden_runner_score_v1"]
        .apply(hidden_band)
    )

    def build_reason(r):

        bits = []

        if num(r["shape_fit"]) >= 80:
            bits.append("elite shape fit")

        elif num(r["shape_fit"]) >= 70:
            bits.append("strong shape fit")

        if num(r["percentile"]) >= 90:
            bits.append("top race percentile")

        elif num(r["percentile"]) >= 75:
            bits.append("high race percentile")

        if num(r["power"]) >= 72:
            bits.append("elite DNA power")

        elif num(r["power"]) >= 68:
            bits.append("strong DNA power")

        if num(r["sectional"]) >= 73:
            bits.append("elite sectional strength")

        elif num(r["sectional"]) >= 70:
            bits.append("strong sectional strength")

        return "; ".join(bits)

    df["hidden_runner_reason_v1"] = (
        df.apply(build_reason, axis=1)
    )

    df.to_csv(OUTPUT, index=False)

    audit = pd.DataFrame([{
        "rows": len(df),
        "elite_hidden": int((df["hidden_runner_band_v1"]=="ELITE_HIDDEN").sum()),
        "strong_hidden": int((df["hidden_runner_band_v1"]=="STRONG_HIDDEN").sum()),
        "hidden": int((df["hidden_runner_band_v1"]=="HIDDEN").sum()),
        "watch": int((df["hidden_runner_band_v1"]=="WATCH").sum()),
        "none": int((df["hidden_runner_band_v1"]=="NONE").sum()),
        "avg_hidden_score": round(
            float(df["hidden_runner_score_v1"].mean()),
            3
        ),
        "output": str(OUTPUT)
    }])

    audit.to_csv(AUDIT, index=False)

    print("[HIDDEN_RUNNER_V1] COMPLETE")
    print(f"rows={len(df)}")
    print(f"output={OUTPUT}")
    print(df["hidden_runner_band_v1"].value_counts().to_string())

if __name__ == "__main__":
    main()

