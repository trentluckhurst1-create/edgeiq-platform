import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "edgeiq_runner_score_v3_1.csv"
OUT = DATA / "edgeiq_fair_price_v7_2.csv"
AUDIT = DATA / "edgeiq_fair_price_v7_2_audit.csv"

GOVERNANCE_INFLATION = {
    "PROVEN": 1.00,
    "LIMITED_DATA_3_4_STARTS": 1.05,
    "LIMITED_DATA_2_STARTS": 1.10,
    "LIMITED_DATA_1_START": 1.20,
    "IMPORT_UNKNOWN": 1.30,
    "FIRST_STARTER_OR_UNKNOWN": 1.40,
}

SCORE_CANDIDATES = [
    "runner_score_v3_1",
    "edgeiq_runner_score_v3_1",
    "runner_score",
    "score_v3_1",
    "edgeiq_score_v3_1",
    "final_runner_score_v3_1",
    "runner_score_v3",
    "edgeiq_runner_score_v3",
]

def pick_col(df, names):
    lower_map = {c.lower().strip(): c for c in df.columns}
    for n in names:
        key = n.lower().strip()
        if key in lower_map:
            return lower_map[key]
    return None

def classify_overlay(edge):
    if pd.isna(edge):
        return "NO_LIVE_PRICE"
    if edge >= 25:
        return "EXECUTE_CANDIDATE"
    if edge >= 15:
        return "STRONG_WATCH"
    if edge >= 8:
        return "WATCH"
    if edge >= 0:
        return "FAIR"
    return "UNDERLAY"

def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing input: {INPUT}")

    df = pd.read_csv(INPUT)

    score_col = pick_col(df, SCORE_CANDIDATES)

    if score_col is None:
        print("[FAIR_PRICE_V7_2] ERROR: could not find runner score column.")
        print("Available columns:")
        for c in df.columns:
            print(f" - {c}")
        raise ValueError("Missing runner score column. See printed available columns above.")

    race_col = pick_col(df, ["race_id", "race_key", "meeting_race_key", "track_race_key"])

    if race_col is None:
        if all(c in df.columns for c in ["race_date", "track", "race_no"]):
            df["edgeiq_race_key_v7_2"] = (
                df["race_date"].astype(str).str.strip() + "|" +
                df["track"].astype(str).str.upper().str.strip() + "|" +
                df["race_no"].astype(str).str.strip()
            )
            race_col = "edgeiq_race_key_v7_2"
        else:
            raise ValueError("No race key found. Need race key or race_date + track + race_no.")

    horse_col = pick_col(df, ["horse", "horse_name", "runner", "runner_name"])

    live_col = pick_col(df, [
        "live_price",
        "live_price_used",
        "tab_fixed_win",
        "sportsbet_price",
        "market_price",
        "fixed_win",
        "ui_price",
    ])

    gov_col = pick_col(df, [
        "projection_governance_v6",
        "governance_band_v6",
        "data_governance_band",
        "runner_governance_band",
        "projection_status_v6",
        "governance_band",
    ])

    df["runner_score_v3_1"] = pd.to_numeric(df[score_col], errors="coerce").fillna(0)

    if gov_col:
        df["governance_band_v7_2"] = df[gov_col].astype(str).str.upper().str.strip()
    else:
        df["governance_band_v7_2"] = "PROVEN"

    df["pricing_weight_v7_2"] = np.exp(df["runner_score_v3_1"] / 55.0)

    df["raw_probability_v7_2"] = (
        df["pricing_weight_v7_2"] /
        df.groupby(race_col)["pricing_weight_v7_2"].transform("sum")
    )

    df["governance_inflation_v7_2"] = (
        df["governance_band_v7_2"]
        .map(GOVERNANCE_INFLATION)
        .fillna(1.15)
    )

    df["fair_price_v7_2"] = (1.0 / df["raw_probability_v7_2"]) * df["governance_inflation_v7_2"]
    df["fair_price_v7_2"] = df["fair_price_v7_2"].replace([np.inf, -np.inf], np.nan).round(2)
    df["fair_probability_v7_2"] = (1.0 / df["fair_price_v7_2"]).replace([np.inf, -np.inf], np.nan)

    if live_col:
        df["live_price_used_v7_2"] = pd.to_numeric(df[live_col], errors="coerce")
    else:
        df["live_price_used_v7_2"] = np.nan

    df["overlay_pct_v7_2"] = ((df["live_price_used_v7_2"] / df["fair_price_v7_2"]) - 1.0) * 100.0
    df["overlay_pct_v7_2"] = df["overlay_pct_v7_2"].round(1)
    df["overlay_decision_v7_2"] = df["overlay_pct_v7_2"].apply(classify_overlay)

    df["race_probability_sum_v7_2"] = df.groupby(race_col)["fair_probability_v7_2"].transform("sum").round(4)
    df["runner_rank_v7_2"] = df.groupby(race_col)["runner_score_v3_1"].rank(method="first", ascending=False).astype(int)

    df = df.sort_values([race_col, "runner_rank_v7_2"])

    df.to_csv(OUT, index=False)

    favs = df.sort_values([race_col, "fair_price_v7_2"]).groupby(race_col).head(1)

    audit = pd.DataFrame([
        {"metric": "input_score_column_used", "value": score_col},
        {"metric": "race_column_used", "value": race_col},
        {"metric": "live_price_column_used", "value": live_col or "NONE"},
        {"metric": "governance_column_used", "value": gov_col or "NONE"},
        {"metric": "rows", "value": len(df)},
        {"metric": "races", "value": df[race_col].nunique()},
        {"metric": "min_favourite_price", "value": round(favs["fair_price_v7_2"].min(), 2)},
        {"metric": "avg_favourite_price", "value": round(favs["fair_price_v7_2"].mean(), 2)},
        {"metric": "max_favourite_price", "value": round(favs["fair_price_v7_2"].max(), 2)},
        {"metric": "min_race_probability_sum", "value": round(df.groupby(race_col)["fair_probability_v7_2"].sum().min(), 4)},
        {"metric": "avg_race_probability_sum", "value": round(df.groupby(race_col)["fair_probability_v7_2"].sum().mean(), 4)},
        {"metric": "max_race_probability_sum", "value": round(df.groupby(race_col)["fair_probability_v7_2"].sum().max(), 4)},
    ])

    audit.to_csv(AUDIT, index=False)

    print("[FAIR_PRICE_V7_2] COMPLETE")
    print(f"score_col={score_col}")
    print(f"rows={len(df)}")
    print(f"races={df[race_col].nunique()}")
    print(f"wrote={OUT}")
    print(f"audit={AUDIT}")

if __name__ == "__main__":
    main()
