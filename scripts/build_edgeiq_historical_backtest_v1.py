import re
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RESULTS = DATA / "edgeiq_racingcom_results_warehouse_full_v1.csv"

OUT_RUNNERS = DATA / "edgeiq_historical_backtest_v1_runner_rows.csv"
OUT_RANK = DATA / "edgeiq_historical_backtest_v1_by_market_rank.csv"
OUT_PRICE = DATA / "edgeiq_historical_backtest_v1_by_sp_band.csv"
OUT_SUMMARY = DATA / "edgeiq_historical_backtest_v1_summary.csv"

def price_num(x):
    s = "" if pd.isna(x) else str(x).strip()
    s = s.replace("$", "").replace(",", "")
    try:
        return float(s)
    except Exception:
        return np.nan

def pos_num(x):
    s = "" if pd.isna(x) else str(x).strip().upper()
    if s in ["", "SCR", "SCRATCHED", "NAN", "NONE"]:
        return np.nan
    m = re.search(r"\d+", s)
    return float(m.group(0)) if m else np.nan

def sp_band(x):
    if pd.isna(x):
        return "NO_SP"
    if x < 2:
        return "01_<2"
    if x < 3:
        return "02_2-2.99"
    if x < 5:
        return "03_3-4.99"
    if x < 8:
        return "04_5-7.99"
    if x < 12:
        return "05_8-11.99"
    if x < 20:
        return "06_12-19.99"
    if x < 50:
        return "07_20-49.99"
    return "08_50+"

def metrics(df, group_col):
    g = df.groupby(group_col, dropna=False).agg(
        runners=("horseName", "count"),
        races=("race_key", "nunique"),
        wins=("won", "sum"),
        places=("placed", "sum"),
        profit_1u=("profit_1u", "sum"),
        avg_sp=("sp_num", "mean"),
        median_sp=("sp_num", "median"),
    ).reset_index()

    g["strike_rate"] = (g["wins"] / g["runners"]).round(4)
    g["place_rate"] = (g["places"] / g["runners"]).round(4)
    g["roi_1u"] = (g["profit_1u"] / g["runners"]).round(4)
    g["profit_1u"] = g["profit_1u"].round(2)
    g["avg_sp"] = g["avg_sp"].round(2)
    g["median_sp"] = g["median_sp"].round(2)
    return g

def main():
    if not RESULTS.exists():
        raise FileNotFoundError(f"Missing full results warehouse: {RESULTS}")

    df = pd.read_csv(RESULTS)

    required = ["meeting_date", "track", "race_no", "horseName", "finishPosition", "sp"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required result columns: {missing}")

    df["sp_num"] = df["sp"].apply(price_num)
    df["finish_num"] = df["finishPosition"].apply(pos_num)

    df = df[df["finish_num"].notna()].copy()
    df = df[df["sp_num"].notna()].copy()
    df = df[df["sp_num"] > 1.0].copy()

    df["race_key"] = (
        df["meeting_date"].astype(str) + "|" +
        df["track"].astype(str) + "|" +
        df["race_no"].astype(str)
    )

    df["won"] = df["finish_num"].eq(1).astype(int)
    df["placed"] = df["finish_num"].le(3).astype(int)
    df["profit_1u"] = np.where(df["won"].eq(1), df["sp_num"] - 1.0, -1.0)

    df["market_rank"] = df.groupby("race_key")["sp_num"].rank(method="first", ascending=True)
    df["market_rank_bucket"] = np.where(df["market_rank"] <= 10, df["market_rank"].astype(int).astype(str), "11+")
    df["sp_band"] = df["sp_num"].apply(sp_band)

    df.to_csv(OUT_RUNNERS, index=False)

    by_rank = metrics(df, "market_rank_bucket").sort_values(
        "market_rank_bucket",
        key=lambda s: s.map(lambda x: int(x.replace("+", "")) if str(x).replace("+", "").isdigit() else 99)
    )
    by_rank.to_csv(OUT_RANK, index=False)

    by_price = metrics(df, "sp_band").sort_values("sp_band")
    by_price.to_csv(OUT_PRICE, index=False)

    total_runners = len(df)
    total_races = df["race_key"].nunique()
    total_wins = int(df["won"].sum())
    total_places = int(df["placed"].sum())
    total_profit = float(df["profit_1u"].sum())

    summary = pd.DataFrame([
        {"metric": "usable_runners", "value": total_runners},
        {"metric": "usable_races", "value": total_races},
        {"metric": "date_min", "value": df["meeting_date"].min()},
        {"metric": "date_max", "value": df["meeting_date"].max()},
        {"metric": "wins", "value": total_wins},
        {"metric": "places", "value": total_places},
        {"metric": "all_runner_profit_1u", "value": round(total_profit, 2)},
        {"metric": "all_runner_roi_1u", "value": round(total_profit / total_runners, 4) if total_runners else 0},
        {"metric": "market_fav_bets", "value": int((df["market_rank"] == 1).sum())},
        {"metric": "market_fav_profit_1u", "value": round(df[df["market_rank"] == 1]["profit_1u"].sum(), 2)},
        {"metric": "market_fav_roi_1u", "value": round(df[df["market_rank"] == 1]["profit_1u"].sum() / max(1, int((df["market_rank"] == 1).sum())), 4)},
    ])
    summary.to_csv(OUT_SUMMARY, index=False)

    print("[HISTORICAL_BACKTEST_V1] COMPLETE")
    print(f"usable_runners={total_runners}")
    print(f"usable_races={total_races}")
    print(f"date_range={df['meeting_date'].min()} to {df['meeting_date'].max()}")
    print(f"market_fav_roi={summary.loc[summary['metric'].eq('market_fav_roi_1u'), 'value'].iloc[0]}")
    print(f"wrote={OUT_RUNNERS}")
    print(f"rank={OUT_RANK}")
    print(f"price={OUT_PRICE}")
    print(f"summary={OUT_SUMMARY}")

if __name__ == "__main__":
    main()
