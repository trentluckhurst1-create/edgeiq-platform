from pathlib import Path
import pandas as pd
import numpy as np
import math

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_current_fair_prices_v5_2_research_replay.csv"

OUT = DATA / "edgeiq_gap_probability_curve_audit_v1.csv"
SUMMARY = DATA / "edgeiq_gap_probability_curve_audit_v1_summary.csv"

def bucket_gap(x):
    try:
        g = float(x)
    except:
        return "NO_GAP"

    if g >= 10:
        return "10_PLUS"
    if g >= 6:
        return "6_TO_10"
    if g >= 2:
        return "2_TO_6"
    if g >= -2:
        return "-2_TO_2"
    if g >= -6:
        return "-6_TO_-2"
    if g >= -10:
        return "-10_TO_-6"
    return "LT_-10"

def main():
    df = pd.read_csv(SRC, dtype=str, keep_default_na=False, low_memory=False)

    df["gap_num"] = pd.to_numeric(df["projection_gap_research"], errors="coerce")
    df["prob_num"] = pd.to_numeric(df["research_probability"], errors="coerce")
    df["price_num"] = pd.to_numeric(df["research_fair_price"], errors="coerce")

    df["gap_bucket"] = df["projection_gap_research"].apply(bucket_gap)

    out = df[
        [
            "race_date",
            "track",
            "race_no",
            "horse",
            "projection_gap_research",
            "projection_band_research",
            "research_probability",
            "research_fair_price",
            "research_price_rank",
            "research_price_status",
            "research_pricing_guardrail",
            "research_pricing_power_used",
            "gap_bucket",
        ]
    ].copy()

    out.to_csv(OUT, index=False)

    rows = []

    rated = df[df["research_price_status"].eq("RESEARCH_RATED")].copy()

    for b, g in rated.groupby("gap_bucket", dropna=False):
        probs = g["prob_num"].dropna()
        prices = g["price_num"].dropna()

        rows.append({
            "gap_bucket": b,
            "count": len(g),
            "avg_gap": round(float(g["gap_num"].mean()), 4),
            "avg_probability": round(float(probs.mean()), 6) if len(probs) else "",
            "median_probability": round(float(probs.median()), 6) if len(probs) else "",
            "avg_fair_price": round(float(prices.mean()), 4) if len(prices) else "",
            "median_fair_price": round(float(prices.median()), 4) if len(prices) else "",
            "min_fair_price": round(float(prices.min()), 4) if len(prices) else "",
            "max_fair_price": round(float(prices.max()), 4) if len(prices) else "",
        })

    summary = pd.DataFrame(rows).sort_values("avg_gap", ascending=False)
    summary.to_csv(SUMMARY, index=False)

    print("[GAP_PROBABILITY_CURVE_AUDIT_V1] COMPLETE")
    print(f"rows={len(out)}")
    print(f"rated_rows={len(rated)}")
    print(f"out={OUT}")
    print(f"summary={SUMMARY}")
    print(summary.to_string(index=False))

if __name__ == "__main__":
    main()
