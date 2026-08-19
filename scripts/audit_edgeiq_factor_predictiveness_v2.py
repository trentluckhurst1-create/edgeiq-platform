from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import math

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_historical_replay_settled_v1.csv"

OUT = DATA / "edgeiq_factor_predictiveness_audit_v2.csv"
RANKINGS = DATA / "edgeiq_factor_predictiveness_factor_rankings_v2.csv"
SUMMARY = DATA / "edgeiq_factor_predictiveness_summary_v2.csv"

MIN_BUCKET_RUNNERS = 500

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
df["placed_num"] = np.where(df["finish_num"].between(1, 3), 1, 0)
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
    temp["factor_score"] = temp[col].apply(num)
    temp["bucket"] = temp["factor_score"].apply(bucket)

    for band, g in temp.groupby("bucket", dropna=False):
        runners = len(g)
        wins = int(g["won_num"].sum())
        places = int(g["placed_num"].sum())

        win_pct = wins / runners * 100 if runners else 0
        place_pct = places / runners * 100 if runners else 0

        profit = g["profit_num"].dropna()
        total_profit = profit.sum() if len(profit) else np.nan
        roi_pct = total_profit / len(profit) * 100 if len(profit) else np.nan

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
            "sample_ok": "YES" if runners >= MIN_BUCKET_RUNNERS else "NO",
            "min_bucket_runners": MIN_BUCKET_RUNNERS,
            "built_at": built_at,
        })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

rank_rows = []

for factor, g in out[out["bucket"] != "NO_SCORE"].groupby("factor"):
    usable = g[g["runners"] >= MIN_BUCKET_RUNNERS].copy()

    if usable.empty:
        rank_rows.append({
            "factor": factor,
            "usable_buckets": 0,
            "total_buckets": len(g),
            "best_bucket": "",
            "best_bucket_runners": "",
            "best_bucket_win_lift": "",
            "worst_bucket": "",
            "worst_bucket_runners": "",
            "worst_bucket_win_lift": "",
            "predictive_spread": "",
            "sample_adjusted_score": "",
            "verdict": "INSUFFICIENT_SAMPLE",
        })
        continue

    usable["win_lift_num"] = pd.to_numeric(usable["win_lift_pct"], errors="coerce")

    best = usable.sort_values("win_lift_num", ascending=False).iloc[0]
    worst = usable.sort_values("win_lift_num", ascending=True).iloc[0]

    spread = float(best["win_lift_num"]) - float(worst["win_lift_num"])
    sample_scale = math.log10(max(10, int(best["runners"])))
    sample_adjusted = spread * sample_scale

    verdict = "STRONG" if sample_adjusted >= 40 else "POSITIVE" if sample_adjusted >= 20 else "WEAK" if sample_adjusted >= 8 else "NO_EDGE"

    rank_rows.append({
        "factor": factor,
        "usable_buckets": len(usable),
        "total_buckets": len(g),
        "best_bucket": best["bucket"],
        "best_bucket_runners": int(best["runners"]),
        "best_bucket_win_lift": round(float(best["win_lift_num"]), 3),
        "worst_bucket": worst["bucket"],
        "worst_bucket_runners": int(worst["runners"]),
        "worst_bucket_win_lift": round(float(worst["win_lift_num"]), 3),
        "predictive_spread": round(spread, 3),
        "sample_adjusted_score": round(sample_adjusted, 3),
        "verdict": verdict,
    })

rankings = pd.DataFrame(rank_rows)
rankings["_sort"] = pd.to_numeric(rankings["sample_adjusted_score"], errors="coerce")
rankings = rankings.sort_values("_sort", ascending=False, na_position="last").drop(columns=["_sort"])
rankings.to_csv(RANKINGS, index=False)

summary = pd.DataFrame([
    ["status", "FACTOR_PREDICTIVENESS_AUDIT_V2_BUILT"],
    ["source", SRC.name],
    ["rows", len(df)],
    ["base_wins", base_wins],
    ["base_win_pct", round(base_win_pct, 3)],
    ["base_places", base_places],
    ["base_place_pct", round(base_place_pct, 3)],
    ["factors_tested", len(rankings)],
    ["min_bucket_runners", MIN_BUCKET_RUNNERS],
    ["built_at", built_at],
], columns=["metric", "value"])

summary.to_csv(SUMMARY, index=False)

print("[FACTOR_PREDICTIVENESS_AUDIT_V2] COMPLETE")
print(summary.to_string(index=False))
print("\nRANKINGS")
print(rankings.to_string(index=False))
print(f"wrote={OUT}")
print(f"wrote={RANKINGS}")
print(f"wrote={SUMMARY}")
