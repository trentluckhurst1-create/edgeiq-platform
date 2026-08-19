from pathlib import Path
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent

INPUT_PATH = BASE_DIR / "outputs" / "forecasts" / "race_card_report.csv"
OUTPUT_PATH = BASE_DIR / "outputs" / "forecasts" / "race_card_report_calibrated.csv"


def classify_confidence(starts):
    if pd.isna(starts):
        return 0.6
    if starts >= 6:
        return 1.0
    if starts >= 4:
        return 0.92
    if starts >= 2:
        return 0.82
    if starts >= 1:
        return 0.7
    return 0.6


def softmax(x, temp):
    x = x - np.max(x)
    exps = np.exp(x / temp)
    return exps / np.sum(exps)


def calibrate_race(df):

    df = df.copy()

    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["starts"] = pd.to_numeric(df.get("career_starts", 0), errors="coerce")

    df["rating"] = df["rating"].fillna(df["rating"].median())

    field_mean = df["rating"].mean()

    # detect race type
    race_class = str(df.get("race_class", "").iloc[0]).lower()

    if "maiden" in race_class:
        shrink = 0.72
        temp = 11.5
    elif "group" in race_class:
        shrink = 0.95
        temp = 7.5
    else:
        shrink = 0.85
        temp = 9.5

    df["confidence"] = df["starts"].apply(classify_confidence)

    # maiden adjustment
    if "maiden" in race_class:
        df["rating"] = field_mean + (df["rating"] - field_mean) * 0.7

    df["adj_rating"] = field_mean + (df["rating"] - field_mean) * shrink * df["confidence"]

    probs = softmax(df["adj_rating"].values, temp)

    probs = np.clip(probs, 0.015, 0.6)
    probs = probs / probs.sum()

    df["win_prob_cal"] = probs
    df["rated_price_cal"] = 1 / probs

    if "market" in df.columns:
        df["market"] = pd.to_numeric(df["market"], errors="coerce")
        df["edge_cal"] = (df["market"] / df["rated_price_cal"] - 1) * 100

    return df


def main():
    print("=== CALIBRATION RUNNING ===")

    if not INPUT_PATH.exists():
        print("❌ Missing input file:", INPUT_PATH)
        return

    df = pd.read_csv(INPUT_PATH)

    print("Loaded rows:", len(df))

    grouped = []
    for (d, t, r), g in df.groupby(["race_date", "track", "race_no"]):
        print(f"Calibrating: {t} R{r}")
        grouped.append(calibrate_race(g))

    out = pd.concat(grouped)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_PATH, index=False)

    print("✅ DONE")
    print("Saved to:", OUTPUT_PATH)


if __name__ == "__main__":
    main()