from pathlib import Path
import pandas as pd
import numpy as np
import math

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_current_field_projection_V6_1_RESEARCH_replay.csv"

OUT = DATA / "edgeiq_probability_power_sensitivity_v1.csv"
SUMMARY = DATA / "edgeiq_probability_power_sensitivity_v1_summary.csv"

POWERS = [0.55, 0.75, 1.00, 1.25]

def price_bucket(price):
    if pd.isna(price):
        return "NO_PRICE"
    if price < 2:
        return "ODDS_ON"
    if price < 4:
        return "SHORT"
    if price < 8:
        return "MID"
    if price < 16:
        return "VALUE"
    if price < 50:
        return "LONG"
    return "VERY_LONG"

def main():
    df = pd.read_csv(SRC, dtype=str, keep_default_na=False, low_memory=False)
    df["gap_num"] = pd.to_numeric(df["projection_gap_V6_1_RESEARCH"], errors="coerce")

    rows = []
    group_cols = ["race_date", "track", "race_no"]

    for power in POWERS:
        for _, race in df.groupby(group_cols, dropna=False):
            race = race.copy()
            known = race["gap_num"].notna()
            if int(known.sum()) < 4:
                continue

            gaps = race.loc[known, "gap_num"]
            min_gap = gaps.min()
            score = (gaps - min_gap + 1.0).clip(lower=0.000001).pow(power)
            score_sum = score.sum()

            if not score_sum or math.isnan(score_sum):
                continue

            prob = score / score_sum
            fair = 1.0 / prob
            rank = prob.rank(method="first", ascending=False).astype(int)

            temp = race.loc[known].copy()
            temp["power"] = power
            temp["probability"] = prob.round(6)
            temp["fair_price"] = fair.round(2)
            temp["price_rank"] = rank
            temp["price_bucket"] = fair.apply(price_bucket)
            rows.append(temp)

    out = pd.concat(rows, ignore_index=True)
    out.to_csv(OUT, index=False)

    summary = (
        out.groupby(["power"], dropna=False)
        .agg(
            rows=("horse", "size"),
            avg_fair=("fair_price", "mean"),
            min_fair=("fair_price", "min"),
            max_fair=("fair_price", "max"),
            avg_top1_prob=("probability", "max"),
        )
        .reset_index()
    )
    summary.to_csv(SUMMARY, index=False)

    print("[PROBABILITY_POWER_SENSITIVITY] COMPLETE")
    print(f"out={OUT}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
