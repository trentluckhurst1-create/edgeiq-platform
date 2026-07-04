from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_current_field_projection_V6_1_RESEARCH_BACKFILLED_GOVERNED_CANDIDATE_20260617.csv"

OUT = DATA / "edgeiq_current_fair_prices_V6_1_RESEARCH_BACKFILLED_GOVERNED_CANDIDATE_20260617.csv"
SUMMARY = DATA / "edgeiq_current_fair_prices_V6_1_RESEARCH_BACKFILLED_GOVERNED_CANDIDATE_20260617_summary.csv"

POWER = 0.55

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
    if not SRC.exists():
        raise FileNotFoundError(f"Missing governed projection candidate: {SRC}")

    df = pd.read_csv(SRC, dtype=str, keep_default_na=False, low_memory=False)
    df["projection_gap_V6_1_RESEARCH_num"] = pd.to_numeric(df["projection_gap_V6_1_RESEARCH"], errors="coerce")

    rows = []
    group_cols = ["race_date", "track", "race_no"]

    for _, race_group in df.groupby(group_cols, dropna=False):
        race = race_group.copy()
        known = race["projection_gap_V6_1_RESEARCH_num"].notna()

        race["V6_1_RESEARCH_probability"] = np.nan
        race["V6_1_RESEARCH_fair_price"] = np.nan
        race["V6_1_RESEARCH_price_rank"] = pd.NA
        race["V6_1_RESEARCH_price_bucket"] = "NO_PRICE"
        race["V6_1_RESEARCH_price_status"] = "NO_PRICE"
        race["V6_1_RESEARCH_pricing_power_used"] = ""
        race["V6_1_RESEARCH_pricing_guardrail"] = ""

        known_count = int(known.sum())
        top_gap = race.loc[known, "projection_gap_V6_1_RESEARCH_num"].max() if known_count > 0 else np.nan

        if known_count < 4:
            race.loc[known, "V6_1_RESEARCH_price_status"] = "NO_PRICE_LOW_COVERAGE"
            race.loc[known, "V6_1_RESEARCH_pricing_guardrail"] = "known_count_lt_4"
        elif known_count > 0:
            power_used = 0.35 if top_gap < 2.0 else POWER
            min_gap = race.loc[known, "projection_gap_V6_1_RESEARCH_num"].min()
            race.loc[known, "research_score"] = (
                race.loc[known, "projection_gap_V6_1_RESEARCH_num"] - min_gap + 1.0
            ).clip(lower=0.000001).pow(power_used)

            score_sum = race.loc[known, "research_score"].sum()
            if score_sum and not math.isnan(score_sum):
                raw_prob = race.loc[known, "research_score"] / score_sum
                capped_prob = raw_prob.clip(upper=0.35)
                race.loc[known, "V6_1_RESEARCH_probability"] = capped_prob
                race.loc[known, "V6_1_RESEARCH_fair_price"] = 1.0 / race.loc[known, "V6_1_RESEARCH_probability"]
                race.loc[known, "V6_1_RESEARCH_price_status"] = "RESEARCH_RATED"
                race.loc[known, "V6_1_RESEARCH_pricing_power_used"] = str(power_used)
                race.loc[known, "V6_1_RESEARCH_pricing_guardrail"] = (
                    "weak_race_damped" if top_gap < 2.0 else "standard_power"
                )
                race.loc[known, "V6_1_RESEARCH_price_rank"] = (
                    race.loc[known, "V6_1_RESEARCH_probability"]
                    .rank(method="first", ascending=False)
                    .astype("Int64")
                )
                race["V6_1_RESEARCH_price_bucket"] = race["V6_1_RESEARCH_fair_price"].apply(price_bucket)

        rows.append(race)

    out = pd.concat(rows, ignore_index=True)
    out["V6_1_RESEARCH_probability"] = pd.to_numeric(out["V6_1_RESEARCH_probability"], errors="coerce").round(6)
    out["V6_1_RESEARCH_fair_price"] = pd.to_numeric(out["V6_1_RESEARCH_fair_price"], errors="coerce").round(2)
    out.to_csv(OUT, index=False)

    fallback = out["V6_1_governance_action"].astype(str).eq("FALLBACK_TO_V5_2") if "V6_1_governance_action" in out.columns else pd.Series(False, index=out.index)

    summary_rows = [
        {"section": "overall", "metric": "rows", "value": len(out)},
        {"section": "overall", "metric": "races", "value": out[group_cols].drop_duplicates().shape[0]},
        {"section": "overall", "metric": "priced_rows", "value": int(out["V6_1_RESEARCH_price_status"].eq("RESEARCH_RATED").sum())},
        {"section": "overall", "metric": "fallback_to_v5_2_rows", "value": int(fallback.sum())},
        {"section": "overall", "metric": "fallback_horses", "value": ", ".join(out.loc[fallback, "horse"].astype(str).tolist())},
        {"section": "overall", "metric": "source_projection_file", "value": SRC.name},
        {"section": "meta", "metric": "built_at_utc", "value": datetime.now(timezone.utc).isoformat(timespec="seconds")},
    ]

    pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)

    print("[FAIR_PRICE_BACKFILLED_GOVERNED_CANDIDATE] COMPLETE")
    print(f"source={SRC}")
    print(f"rows={len(out)}")
    print(f"out={OUT}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
