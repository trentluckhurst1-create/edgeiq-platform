from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "edgeiq_horse_genome_v2.csv"
HISTORY = DATA / "edgeiq_historical_race_shape_archive_v1.csv"

OUTPUT = DATA / "edgeiq_horse_genome_v3.csv"
AUDIT = DATA / "edgeiq_horse_genome_v3_audit.csv"

def num(v):
    try:
        if pd.isna(v):
            return np.nan
        return float(v)
    except Exception:
        return np.nan

def reliability_factor(starts):
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
    if starts >= 2:
        return 0.35
    return 0.20

def confidence(starts):
    starts = int(starts)
    if starts >= 30:
        return "HIGH"
    if starts >= 15:
        return "MEDIUM"
    if starts >= 5:
        return "LOW"
    return "VERY_LOW"

def band_by_rank(pct):
    if pct >= 98:
        return "ELITE"
    if pct >= 90:
        return "STRONG"
    if pct >= 70:
        return "SOLID"
    if pct >= 40:
        return "NEUTRAL"
    return "WEAK"

def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing input: {INPUT}")

    if not HISTORY.exists():
        raise FileNotFoundError(f"Missing input: {HISTORY}")

    base = pd.read_csv(INPUT)
    hist = pd.read_csv(HISTORY)

    hist = hist[hist["is_scratched"].astype(str) == "0"].copy()
    hist["finish_position_num"] = pd.to_numeric(hist["finish_position_num"], errors="coerce")

    finish_var = (
        hist
        .dropna(subset=["finish_position_num"])
        .groupby("horse_key_join")
        .agg(
            finish_std_v3=("finish_position_num", "std"),
            best_finish_v3=("finish_position_num", "min"),
            worst_finish_v3=("finish_position_num", "max"),
        )
        .reset_index()
    )

    df = base.merge(
        finish_var,
        left_on="horse_key",
        right_on="horse_key_join",
        how="left"
    )

    for c in [
        "starts_v2",
        "win_pct_v2",
        "place_pct_v2",
        "avg_finish_v2",
        "avg_race_strength_v2",
        "avg_sectional_strength_v2",
    ]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    max_finish = df["avg_finish_v2"].quantile(0.95)
    if pd.isna(max_finish) or max_finish <= 1:
        max_finish = 12

    df["win_component_v3"] = (df["win_pct_v2"].fillna(0) * 100).clip(0, 100)
    df["place_component_v3"] = (df["place_pct_v2"].fillna(0) * 100).clip(0, 100)

    df["finish_component_v3"] = (
        100 - (
            ((df["avg_finish_v2"].fillna(max_finish) - 1) / max(max_finish - 1, 1)) * 100
        )
    ).clip(0, 100)

    df["sectional_component_v3"] = df["avg_sectional_strength_v2"].fillna(50).clip(0, 100)
    df["race_strength_component_v3"] = df["avg_race_strength_v2"].fillna(50).clip(0, 100)

    df["raw_horse_genome_score_v3"] = (
        df["win_component_v3"] * 0.40
        + df["place_component_v3"] * 0.30
        + df["finish_component_v3"] * 0.10
        + df["sectional_component_v3"] * 0.10
        + df["race_strength_component_v3"] * 0.10
    ).round(3)

    df["genome_reliability_factor_v3"] = df["starts_v2"].fillna(0).astype(int).apply(reliability_factor)

    df["horse_genome_score_v3"] = (
        df["raw_horse_genome_score_v3"]
        * df["genome_reliability_factor_v3"]
    ).round(3)

    df["horse_genome_percentile_v3"] = (
        df["horse_genome_score_v3"]
        .rank(pct=True)
        * 100
    ).round(3)

    df["horse_genome_band_v3"] = df["horse_genome_percentile_v3"].apply(band_by_rank)
    df["genome_confidence_v3"] = df["starts_v2"].fillna(0).astype(int).apply(confidence)

    df["finish_std_v3"] = df["finish_std_v3"].fillna(0).round(3)
    df["best_finish_v3"] = df["best_finish_v3"].fillna("").astype(str)
    df["worst_finish_v3"] = df["worst_finish_v3"].fillna("").astype(str)

    df["horse_genome_engine"] = "HORSE_GENOME_V3"
    df["horse_genome_input"] = INPUT.name
    df["horse_genome_history_input"] = HISTORY.name

    preferred = [
        "horse_key",
        "horse_name",
        "starts_v2",
        "wins_v2",
        "places_v2",
        "win_pct_v2",
        "place_pct_v2",
        "avg_finish_v2",
        "finish_std_v3",
        "best_finish_v3",
        "worst_finish_v3",
        "avg_race_strength_v2",
        "avg_sectional_strength_v2",
        "preferred_position_style_v2",
        "raw_horse_genome_score_v3",
        "genome_reliability_factor_v3",
        "horse_genome_score_v3",
        "horse_genome_percentile_v3",
        "horse_genome_band_v3",
        "genome_confidence_v3",
        "win_component_v3",
        "place_component_v3",
        "finish_component_v3",
        "sectional_component_v3",
        "race_strength_component_v3",
    ]

    preferred = [c for c in preferred if c in df.columns]
    remaining = [c for c in df.columns if c not in preferred]
    df = df[preferred + remaining]

    df = df.sort_values(
        ["horse_genome_score_v3", "starts_v2"],
        ascending=[False, False]
    )

    df.to_csv(OUTPUT, index=False)

    audit = pd.DataFrame([{
        "input_horses": len(base),
        "output_horses": len(df),
        "elite": int((df["horse_genome_band_v3"] == "ELITE").sum()),
        "strong": int((df["horse_genome_band_v3"] == "STRONG").sum()),
        "solid": int((df["horse_genome_band_v3"] == "SOLID").sum()),
        "neutral": int((df["horse_genome_band_v3"] == "NEUTRAL").sum()),
        "weak": int((df["horse_genome_band_v3"] == "WEAK").sum()),
        "high_confidence": int((df["genome_confidence_v3"] == "HIGH").sum()),
        "medium_confidence": int((df["genome_confidence_v3"] == "MEDIUM").sum()),
        "low_confidence": int((df["genome_confidence_v3"] == "LOW").sum()),
        "very_low_confidence": int((df["genome_confidence_v3"] == "VERY_LOW").sum()),
        "avg_score": round(float(df["horse_genome_score_v3"].mean()), 3),
        "output": str(OUTPUT),
    }])

    audit.to_csv(AUDIT, index=False)

    print("[HORSE_GENOME_V3] COMPLETE")
    print(f"input_horses={len(base)}")
    print(f"output_horses={len(df)}")
    print(f"wrote={OUTPUT}")
    print(f"audit={AUDIT}")
    print(df["horse_genome_band_v3"].value_counts(dropna=False).to_string())

if __name__ == "__main__":
    main()
