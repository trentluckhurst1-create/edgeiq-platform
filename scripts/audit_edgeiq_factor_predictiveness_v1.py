from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_historical_replay_settled_v1.csv"

OUT = DATA / "edgeiq_factor_predictiveness_audit_v1.csv"
BY_FACTOR = DATA / "edgeiq_factor_predictiveness_by_factor_v1.csv"
SUMMARY = DATA / "edgeiq_factor_predictiveness_summary_v1.csv"

FACTOR_COLS = {
    "RUNNER_SCORE": "runner_score",
    "PROJECTED_RATING": "projected_rating_v5_2",
    "GOVERNED_PROJECTION": "governed_projection_rating_v6",
    "PROJECTION_GAP": "projection_gap_v5_2",
    "SECTIONALS": "sectional_strength_rating",
    "LIVE_STRENGTH": "live_race_strength_score_v3",
    "STRENGTH_ADJUSTED": "strength_adjusted_rating_v6",
    "CONFIDENCE": "confidence_score_v1",
    "CONFIDENCE_ADJUSTED": "confidence_adjusted_rating_v6",
    "CONNECTION": "connection_score",
    "TRAINER": "trainer_score",
    "JOCKEY": "jockey_score",
    "MARKET": "market_score",
}

def num(x):
    try:
        s = str(x).replace("$", "").replace("%", "").strip()
        if s == "" or s.lower() == "nan":
            return np.nan
        return float(s)
    except Exception:
        return np.nan

def bucket(v):
    if pd.isna(v):
        return "NO_SCORE"
    if v < 20:
        return "00_20"
    if v < 40:
        return "20_40"
    if v < 60:
        return "40_60"
    if v < 80:
        return "60_80"
    return "80_100"

df = pd.read_csv(SRC, dtype=str).fillna("")
built_at = datetime.now(timezone.utc).isoformat()

df["won_num"] = df["won"].apply(num).fillna(0)
df["finish_num"] = df["finish_position"].apply(num)
df["placed_num"] = np.where(df["finish_num"].between(1,3), 1, 0)
df["sp_num"] = df["sp_num_settled"].apply(num)
df["profit_num"] = df["profit_1u"].apply(num)

base_runners = len(df)
base_wins = int(df["won_num"].sum())
base_places = int(df["placed_num"].sum())
base_win_pct = base_wins / base_runners * 100 if base_runners else 0
base_place_pct = base_places / base_runners * 100 if base_runners else 0

rows = []

for factor, col in FACTOR_COLS.items():
    if col not in df.columns:
        continue

    temp = df.copy()
    temp["factor"] = factor
    temp["factor_col"] = col
    temp["factor_score"] = temp[col].apply(num)
    temp["bucket"] = temp["factor_score"].apply(bucket)

    for band, g in temp.groupby("bucket", dropna=False):
        runners = len(g)
        wins = int(g["won_num"].sum())
        places = int(g["placed_num"].sum())

        profit = g["profit_num"].dropna()
        total_profit = profit.sum() if len(profit) else np.nan
        roi_pct = (total_profit / len(profit) * 100) if len(profit) else np.nan

        win_pct = wins / runners * 100 if runners else 0
        place_pct = places / runners * 100 if runners else 0

        rows.append({
            "factor": factor,
            "factor_col": col,
            "bucket": band,
            "runners": runners,
            "wins": wins,
            "places": places,
            "win_pct": round(win_pct, 3),
            "place_pct": round(place_pct, 3),
            "base_win_pct": round(base_win_pct, 3),
            "base_place_pct": round(base_place_pct, 3),
            "win_lift_pct": round(win_pct - base_win_pct, 3),
            "place_lift_pct": round(place_pct - base_place_pct, 3),
            "avg_sp": round(g["sp_num"].dropna().mean(), 3) if g["sp_num"].notna().any() else "",
            "roi_pct": "" if pd.isna(roi_pct) else round(roi_pct, 3),
            "built_at": built_at,
        })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

factor_rows = []
for factor, g in out[out["bucket"] != "NO_SCORE"].groupby("factor"):
    hi = g[g["bucket"] == "80_100"]
    mid = g[g["bucket"] == "40_60"]
    low = g[g["bucket"] == "00_20"]

    hi_lift = float(hi["win_lift_pct"].iloc[0]) if len(hi) else np.nan
    mid_lift = float(mid["win_lift_pct"].iloc[0]) if len(mid) else np.nan
    low_lift = float(low["win_lift_pct"].iloc[0]) if len(low) else np.nan

    spread = hi_lift - low_lift if not pd.isna(hi_lift) and not pd.isna(low_lift) else np.nan

    factor_rows.append({
        "factor": factor,
        "predictive_spread_80_100_vs_00_20": "" if pd.isna(spread) else round(spread, 3),
        "high_bucket_win_lift": "" if pd.isna(hi_lift) else round(hi_lift, 3),
        "mid_bucket_win_lift": "" if pd.isna(mid_lift) else round(mid_lift, 3),
        "low_bucket_win_lift": "" if pd.isna(low_lift) else round(low_lift, 3),
        "total_runners": int(g["runners"].sum()),
    })

by_factor = pd.DataFrame(factor_rows)
by_factor["_sort_predictive_spread"] = pd.to_numeric(by_factor["predictive_spread_80_100_vs_00_20"], errors="coerce")
by_factor = by_factor.sort_values("_sort_predictive_spread", ascending=False, na_position="last").drop(columns=["_sort_predictive_spread"])
by_factor.to_csv(BY_FACTOR, index=False)

summary = pd.DataFrame([
    ["status", "FACTOR_PREDICTIVENESS_AUDIT_V1_BUILT"],
    ["source", SRC.name],
    ["rows", len(df)],
    ["base_wins", base_wins],
    ["base_win_pct", round(base_win_pct, 3)],
    ["base_places", base_places],
    ["base_place_pct", round(base_place_pct, 3)],
    ["factors_tested", len(by_factor)],
    ["built_at", built_at],
], columns=["metric", "value"])

summary.to_csv(SUMMARY, index=False)

print("[FACTOR_PREDICTIVENESS_AUDIT_V1] COMPLETE")
print(summary.to_string(index=False))
print("\nBY FACTOR")
print(by_factor.to_string(index=False))
print(f"wrote={OUT}")
print(f"wrote={BY_FACTOR}")
print(f"wrote={SUMMARY}")

