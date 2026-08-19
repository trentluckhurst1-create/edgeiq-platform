from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PRICE = DATA / "edgeiq_current_fair_prices_v5_2_research_replay.csv"

OUT = DATA / "edgeiq_probability_driver_audit_v1.csv"
SUMMARY = DATA / "edgeiq_probability_driver_audit_v1_summary.csv"

def corr(df, a, b):
    if a not in df.columns or b not in df.columns:
        return ""
    x = pd.to_numeric(df[a], errors="coerce")
    y = pd.to_numeric(df[b], errors="coerce")
    ok = x.notna() & y.notna()
    if ok.sum() < 3:
        return ""
    return round(float(x[ok].corr(y[ok])), 6)

def main():
    df = pd.read_csv(PRICE, dtype=str, keep_default_na=False, low_memory=False)

    rated = df[df["research_price_status"].eq("RESEARCH_RATED")].copy()

    for c in [
        "projected_rating_v5_2",
        "projected_rating_research",
        "race_target_rating_v5_2",
        "projection_gap_v5_2",
        "projection_gap_research",
        "research_probability",
        "research_fair_price",
    ]:
        if c in rated.columns:
            rated[c + "_num"] = pd.to_numeric(rated[c], errors="coerce")

    rated.to_csv(OUT, index=False)

    rows = [
        {"metric": "rows", "value": len(rated)},
        {"metric": "corr_old_projected_rating_probability", "value": corr(rated, "projected_rating_v5_2", "research_probability")},
        {"metric": "corr_research_projected_rating_probability", "value": corr(rated, "projected_rating_research", "research_probability")},
        {"metric": "corr_target_probability", "value": corr(rated, "race_target_rating_v5_2", "research_probability")},
        {"metric": "corr_old_gap_probability", "value": corr(rated, "projection_gap_v5_2", "research_probability")},
        {"metric": "corr_research_gap_probability", "value": corr(rated, "projection_gap_research", "research_probability")},
    ]

    pd.DataFrame(rows).to_csv(SUMMARY, index=False)

    print("[PROBABILITY_DRIVER_AUDIT_V1] COMPLETE")
    print(f"rows={len(rated)}")
    print(f"out={OUT}")
    print(f"summary={SUMMARY}")
    print(pd.DataFrame(rows).to_string(index=False))

if __name__ == "__main__":
    main()
