import pandas as pd
from pathlib import Path
import math

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_projection_v6_1_research_prior_rating_backtest.csv"

OUT = DATA / "edgeiq_v6_1_overlay_replay_v1.csv"
SUMMARY = DATA / "edgeiq_v6_1_overlay_replay_v1_summary.csv"
BY_MODEL = DATA / "edgeiq_v6_1_overlay_replay_v1_by_model.csv"
BY_BAND = DATA / "edgeiq_v6_1_overlay_replay_v1_by_band.csv"
BY_FAIR_BUCKET = DATA / "edgeiq_v6_1_overlay_replay_v1_by_fair_bucket.csv"

def n(x):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return math.nan
        return float(x)
    except Exception:
        return math.nan

def fair_bucket(x):
    x = n(x)
    if math.isnan(x):
        return "NO_FAIR"
    if x < 2:
        return "UNDER_2"
    if x < 3:
        return "2_TO_3"
    if x < 5:
        return "3_TO_5"
    if x < 8:
        return "5_TO_8"
    if x < 12:
        return "8_TO_12"
    if x < 20:
        return "12_TO_20"
    return "20_PLUS"

def band_order(b):
    return {
        "ELITE": 6,
        "STRONG": 5,
        "POSITIVE": 4,
        "NEUTRAL": 3,
        "NEGATIVE": 2,
        "POOR": 1,
    }.get(str(b).upper(), 0)

def summarise(df, group_cols):
    rows = []
    for key, g in df.groupby(group_cols, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        d = dict(zip(group_cols, key))
        bets = len(g)
        wins = int(pd.to_numeric(g["won"], errors="coerce").fillna(0).sum())
        places = int(pd.to_numeric(g["placed"], errors="coerce").fillna(0).sum())
        d.update({
            "bets": bets,
            "wins": wins,
            "places": places,
            "win_pct": round((wins / bets) * 100, 2) if bets else 0,
            "place_pct": round((places / bets) * 100, 2) if bets else 0,
            "avg_fair_price": round(pd.to_numeric(g["fair_price"], errors="coerce").mean(), 4),
            "avg_gap": round(pd.to_numeric(g["rating_gap"], errors="coerce").mean(), 4),
            "avg_rank": round(pd.to_numeric(g["rank"], errors="coerce").mean(), 4),
        })
        rows.append(d)
    return pd.DataFrame(rows)

df = pd.read_csv(SRC, dtype=str, keep_default_na=False, low_memory=False)

df["fair_price_num"] = pd.to_numeric(df["fair_price"], errors="coerce")
df["rating_gap_num"] = pd.to_numeric(df["rating_gap"], errors="coerce")
df["rank_num"] = pd.to_numeric(df["rank"], errors="coerce")
df["won_num"] = pd.to_numeric(df["won"], errors="coerce").fillna(0)
df["placed_num"] = pd.to_numeric(df["placed"], errors="coerce").fillna(0)
df["fair_bucket"] = df["fair_price"].apply(fair_bucket)
df["band_score"] = df["projection_band"].apply(band_order)

# Candidate definition: not a real betting ROI replay.
# This is strength-only validation using model fair price / band / rank.
df["candidate_rule"] = "NO_BET"
df.loc[
    (df["rank_num"] <= 1) &
    (df["band_score"] >= 4) &
    (df["fair_price_num"] <= 8),
    "candidate_rule"
] = "RANK1_POSITIVE_PLUS_FAIR_LE_8"

df.loc[
    (df["rank_num"] <= 2) &
    (df["band_score"] >= 5) &
    (df["fair_price_num"] <= 10),
    "candidate_rule"
] = "TOP2_STRONG_PLUS_FAIR_LE_10"

df.loc[
    (df["rank_num"] <= 3) &
    (df["band_score"] >= 6) &
    (df["fair_price_num"] <= 12),
    "candidate_rule"
] = "TOP3_ELITE_FAIR_LE_12"

candidates = df[df["candidate_rule"] != "NO_BET"].copy()

candidates.to_csv(OUT, index=False)

summary_rows = [
    {"metric": "source_rows", "value": len(df)},
    {"metric": "candidate_rows", "value": len(candidates)},
    {"metric": "models", "value": ",".join(sorted(df["model"].dropna().unique()))},
    {"metric": "note", "value": "NO_SP_OR_MARKET_PRICE_IN_SOURCE_SO_THIS_IS_NOT_ROI"},
]

pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)

summarise(candidates, ["model", "candidate_rule"]).to_csv(BY_MODEL, index=False)
summarise(candidates, ["model", "projection_band"]).to_csv(BY_BAND, index=False)
summarise(candidates, ["model", "fair_bucket"]).to_csv(BY_FAIR_BUCKET, index=False)

print("[V6_1_OVERLAY_REPLAY_V1] COMPLETE")
print("NOTE: no SP/market odds in source, so this is NOT ROI.")
print("out=", OUT)
print("summary=", SUMMARY)
print("by_model=", BY_MODEL)
print("by_band=", BY_BAND)
print("by_fair_bucket=", BY_FAIR_BUCKET)
print(summarise(candidates, ["model", "candidate_rule"]).to_string(index=False))
