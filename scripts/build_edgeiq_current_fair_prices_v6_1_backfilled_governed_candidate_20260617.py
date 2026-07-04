from pathlib import Path
import pandas as pd
import numpy as np
import math

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_current_field_projection_V6_1_RESEARCH_BACKFILLED_GOVERNED_CANDIDATE_20260617.csv"

OUT = DATA / "edgeiq_current_fair_prices_v6_1_BACKFILLED_GOVERNED_CANDIDATE_20260617.csv"
SUMMARY = DATA / "edgeiq_current_fair_prices_v6_1_BACKFILLED_GOVERNED_CANDIDATE_20260617_summary.csv"

def num(x, default=np.nan):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return default
        return float(str(x).strip())
    except Exception:
        return default

def build_race_prices(race):
    race = race.copy()

    race["projection_gap_V6_1_RESEARCH_num"] = pd.to_numeric(
        race["projection_gap_V6_1_RESEARCH"], errors="coerce"
    )

    known = race["projection_gap_V6_1_RESEARCH_num"].notna()
    known_count = int(known.sum())

    race["fair_price"] = pd.NA
    race["win_pct"] = pd.NA
    race["V6_1_RESEARCH_price_rank"] = pd.NA
    race["V6_1_RESEARCH_price_status"] = "NO_PRICE"

    if known_count <= 0:
        return race

    gaps = race.loc[known, "projection_gap_V6_1_RESEARCH_num"]

    min_gap = gaps.min()
    raw = gaps - min_gap + 1.0

    # Existing-style compression to avoid runaway short prices.
    raw = np.power(raw, 1.12)

    total = raw.sum()
    if total <= 0 or pd.isna(total):
        return race

    probs = raw / total

    race.loc[known, "win_pct"] = (probs * 100).round(2)
    race.loc[known, "fair_price"] = (1 / probs).round(2)
    race.loc[known, "V6_1_RESEARCH_price_rank"] = (
        race.loc[known, "win_pct"]
        .astype(float)
        .rank(method="first", ascending=False)
        .astype(int)
    )
    race.loc[known, "V6_1_RESEARCH_price_status"] = "RESEARCH_RATED"

    return race

def main():
    if not SRC.exists():
        raise FileNotFoundError(f"Missing input: {SRC}")

    df = pd.read_csv(SRC, dtype=str, keep_default_na=False, low_memory=False)

    group_cols = []
    for c in ["race_date", "track", "race_no"]:
        if c in df.columns:
            group_cols.append(c)

    if not group_cols:
        raise RuntimeError("No race grouping columns found")

    out = (
        df.groupby(group_cols, dropna=False, group_keys=False)
        .apply(build_race_prices)
        .reset_index(drop=True)
    )

    out.to_csv(OUT, index=False)

    fallback = out["V6_1_governance_action"].astype(str).eq("FALLBACK_TO_V5_2") if "V6_1_governance_action" in out.columns else pd.Series(False, index=out.index)

    summary_rows = [
        {"metric": "status", "value": "BACKFILLED_GOVERNED_FAIR_PRICE_CANDIDATE_BUILT"},
        {"metric": "rows", "value": len(out)},
        {"metric": "rated_rows", "value": int(out["V6_1_RESEARCH_price_status"].astype(str).eq("RESEARCH_RATED").sum())},
        {"metric": "fallback_to_v5_2_rows", "value": int(fallback.sum())},
        {"metric": "fallback_horses", "value": ", ".join(out.loc[fallback, "horse"].astype(str).tolist())},
    ]

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(SUMMARY, index=False)

    print("[BACKFILLED_GOVERNED_FAIR_PRICE_CANDIDATE] COMPLETE")
    print(summary.to_string(index=False))
    print(f"out={OUT}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
