from pathlib import Path
import pandas as pd
import numpy as np
import math
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_current_field_projection_v5_2_research_replay.csv"

OUT = DATA / "edgeiq_current_fair_prices_v5_2_research_replay.csv"
SUMMARY = DATA / "edgeiq_current_fair_prices_v5_2_research_replay_summary.csv"

POWER = 0.85

def num(x):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return np.nan
        return float(str(x).replace(",", "").strip())
    except Exception:
        return np.nan

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

    df["projection_gap_research_num"] = pd.to_numeric(df["projection_gap_research"], errors="coerce")

    rows = []
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    group_cols = ["race_date", "track", "race_no"]

    for _, g in df.groupby(group_cols, dropna=False):
        race = g.copy()
        known = race["projection_gap_research_num"].notna()

        race["research_probability"] = np.nan
        race["research_fair_price"] = np.nan
        race["research_price_rank"] = pd.NA
        race["research_price_bucket"] = "NO_PRICE"
        race["research_price_status"] = "NO_PRICE"

        known_count = int(known.sum())
        top_gap = race.loc[known, "projection_gap_research_num"].max() if known_count > 0 else np.nan

        race["research_pricing_power_used"] = ""
        race["research_pricing_guardrail"] = ""

        if known_count < 3:
            race.loc[known, "research_price_status"] = "NO_PRICE_LOW_COVERAGE"
            race.loc[known, "research_pricing_guardrail"] = "known_count_lt_3"
        elif known_count > 0:
            power_used = 0.35 if top_gap < 2.0 else POWER

            min_gap = race.loc[known, "projection_gap_research_num"].min()
            race.loc[known, "research_score"] = (
                race.loc[known, "projection_gap_research_num"] - min_gap + 1.0
            ).clip(lower=0.000001).pow(power_used)

            score_sum = race.loc[known, "research_score"].sum()

            race.loc[known, "research_probability"] = race.loc[known, "research_score"] / score_sum
            race.loc[known, "research_fair_price"] = 1.0 / race.loc[known, "research_probability"]
            race.loc[known, "research_price_status"] = "RESEARCH_RATED"
            race.loc[known, "research_pricing_power_used"] = str(power_used)
            race.loc[known, "research_pricing_guardrail"] = "weak_race_damped" if top_gap < 2.0 else "standard_power"

            race.loc[known, "research_price_rank"] = (
                race.loc[known, "research_probability"]
                .rank(method="first", ascending=False)
                .astype("Int64")
            )

            race["research_price_bucket"] = race["research_fair_price"].apply(price_bucket)

        rows.append(race)

    out = pd.concat(rows, ignore_index=True)

    out["research_probability"] = pd.to_numeric(out["research_probability"], errors="coerce").round(6)
    out["research_fair_price"] = pd.to_numeric(out["research_fair_price"], errors="coerce").round(2)

    out.to_csv(OUT, index=False)

    summary_rows = []

    summary_rows.append({
        "section": "overall",
        "metric": "rows",
        "value": len(out)
    })
    summary_rows.append({
        "section": "overall",
        "metric": "races",
        "value": out[group_cols].drop_duplicates().shape[0]
    })
    summary_rows.append({
        "section": "overall",
        "metric": "priced_rows",
        "value": int(out["research_price_status"].eq("RESEARCH_RATED").sum())
    })
    summary_rows.append({
        "section": "overall",
        "metric": "no_price_rows",
        "value": int(out["research_price_status"].eq("NO_PRICE").sum())
    })

    for bucket, count in out["research_price_bucket"].value_counts(dropna=False).sort_index().items():
        summary_rows.append({
            "section": "price_bucket",
            "metric": bucket,
            "count": int(count)
        })

    prob_sums = out.groupby(group_cols, dropna=False)["research_probability"].sum(min_count=1)

    summary_rows.extend([
        {"section": "probability_integrity", "metric": "sum_min", "value": round(float(prob_sums.min()), 6)},
        {"section": "probability_integrity", "metric": "sum_max", "value": round(float(prob_sums.max()), 6)},
        {"section": "probability_integrity", "metric": "sum_avg", "value": round(float(prob_sums.mean()), 6)},
    ])

    pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)

    print("[FAIR_PRICE_RESEARCH_REPLAY] COMPLETE")
    print(f"rows={len(out)}")
    print(f"out={OUT}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()



