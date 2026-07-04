from pathlib import Path
from datetime import datetime, timezone
import math
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_historical_replay_settled_v1.csv"

OUT = DATA / "edgeiq_probability_power_replay_v1.csv"
SUMMARY = DATA / "edgeiq_probability_power_replay_v1_summary.csv"
BY_RACE = DATA / "edgeiq_probability_power_replay_v1_by_race.csv"

POWERS = [0.55, 0.75, 1.00, 1.25]

def first_existing(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

def price_bucket(price):
    if pd.isna(price):
        return "NO_PRICE"
    if price < 2:
        return "ODDS_ON"
    if price < 4:
        return "SHORT"
    if price < 8:
        return "MID"
    if price < 15:
        return "VALUE"
    if price < 31:
        return "OUTSIDER"
    return "LONGSHOT"

df = pd.read_csv(SRC, dtype=str).fillna("")

race_col = first_existing(df, ["race_key", "race_context_key", "race_id"])
horse_col = first_existing(df, ["horse", "runner", "horse_name"])
track_col = first_existing(df, ["track"])
race_no_col = first_existing(df, ["race_no"])
date_col = first_existing(df, ["meeting_date", "race_date", "date"])

gap_col = first_existing(df, [
    "projection_gap_V6_1_RESEARCH",
    "projection_gap_v6_1_research",
    "projection_gap_v5_2",
    "projection_gap",
])

win_col = first_existing(df, ["won", "win_flag", "winner", "won_num"])
place_col = first_existing(df, ["placed", "place_flag", "placed_num"])
finish_col = first_existing(df, ["finish_position", "finish_pos", "finishing_position"])

missing = []
for name, col in [
    ("race", race_col),
    ("horse", horse_col),
    ("gap", gap_col),
    ("win", win_col),
]:
    if col is None:
        missing.append(name)

if place_col is None and finish_col is None:
    missing.append("place_or_finish_position")

if missing:
    raise RuntimeError(f"Missing required source columns: {missing}. Available columns: {list(df.columns)}")

df["_gap"] = pd.to_numeric(df[gap_col], errors="coerce")
df["_won"] = pd.to_numeric(df[win_col], errors="coerce").fillna(0).astype(int)

if place_col:
    df["_placed"] = pd.to_numeric(df[place_col], errors="coerce").fillna(0).astype(int)
else:
    finish = pd.to_numeric(df[finish_col], errors="coerce")
    df["_placed"] = ((finish >= 1) & (finish <= 3)).astype(int)

rows = []
race_rows = []
built_at = datetime.now(timezone.utc).isoformat()

for power in POWERS:
    for race_key, race in df.groupby(race_col, dropna=False):
        race = race.copy()
        known = race["_gap"].notna()
        known_count = int(known.sum())

        if known_count < 4:
            continue

        gaps = race.loc[known, "_gap"]
        min_gap = gaps.min()

        score = (gaps - min_gap + 1.0).clip(lower=0.000001).pow(power)
        score_sum = score.sum()

        if not score_sum or math.isnan(score_sum):
            continue

        prob = score / score_sum
        fair = 1.0 / prob
        rank = prob.rank(method="first", ascending=False).astype(int)

        temp = race.loc[known].copy()
        temp["_probability"] = prob
        temp["_fair_price"] = fair
        temp["_price_rank"] = rank
        temp["_price_bucket"] = fair.apply(price_bucket)

        top = temp.sort_values("_price_rank").iloc[0]

        race_rows.append({
            "power": power,
            "race_key": race_key,
            "meeting_date": top.get(date_col, "") if date_col else "",
            "track": top.get(track_col, "") if track_col else "",
            "race_no": top.get(race_no_col, "") if race_no_col else "",
            "known_count": known_count,
            "top_horse": top.get(horse_col, ""),
            "top_probability": round(float(top["_probability"]), 6),
            "top_fair_price": round(float(top["_fair_price"]), 2),
            "top_gap": round(float(top["_gap"]), 4),
            "top_won": int(top["_won"]),
            "top_placed": int(top["_placed"]),
            "built_at": built_at,
        })

        for _, r in temp.iterrows():
            rows.append({
                "power": power,
                "race_key": race_key,
                "meeting_date": r.get(date_col, "") if date_col else "",
                "track": r.get(track_col, "") if track_col else "",
                "race_no": r.get(race_no_col, "") if race_no_col else "",
                "horse": r.get(horse_col, ""),
                "projection_gap": round(float(r["_gap"]), 4),
                "probability": round(float(r["_probability"]), 6),
                "fair_price": round(float(r["_fair_price"]), 2),
                "price_rank": int(r["_price_rank"]),
                "price_bucket": r["_price_bucket"],
                "won": int(r["_won"]),
                "placed": int(r["_placed"]),
                "known_count": known_count,
                "built_at": built_at,
            })

out = pd.DataFrame(rows)
by_race = pd.DataFrame(race_rows)

out.to_csv(OUT, index=False)
by_race.to_csv(BY_RACE, index=False)

summary_rows = []

for power, g in out.groupby("power"):
    races = g["race_key"].nunique()
    top = g[g["price_rank"] == 1].copy()

    longshots = g[pd.to_numeric(g["fair_price"], errors="coerce") >= 20]
    outsiders = g[pd.to_numeric(g["fair_price"], errors="coerce") >= 15]

    fav_prob = pd.to_numeric(top["probability"], errors="coerce")
    fav_price = pd.to_numeric(top["fair_price"], errors="coerce")

    summary_rows.append({
        "power": power,
        "races": races,
        "runner_rows": len(g),
        "rank1_wins": int(top["won"].sum()),
        "rank1_places": int(top["placed"].sum()),
        "rank1_win_pct": round(top["won"].sum() / races * 100, 3) if races else "",
        "rank1_place_pct": round(top["placed"].sum() / races * 100, 3) if races else "",
        "avg_top1_probability": round(fav_prob.mean(), 6),
        "avg_top1_fair_price": round(fav_price.mean(), 3),
        "median_top1_fair_price": round(fav_price.median(), 3),
        "avg_runner_fair_price": round(pd.to_numeric(g["fair_price"], errors="coerce").mean(), 3),
        "median_runner_fair_price": round(pd.to_numeric(g["fair_price"], errors="coerce").median(), 3),
        "longshot_rows_20_plus": len(longshots),
        "longshot_win_pct_20_plus": round(longshots["won"].sum() / len(longshots) * 100, 3) if len(longshots) else "",
        "outsider_rows_15_plus": len(outsiders),
        "outsider_win_pct_15_plus": round(outsiders["won"].sum() / len(outsiders) * 100, 3) if len(outsiders) else "",
        "built_at": built_at,
    })

summary = pd.DataFrame(summary_rows)
summary.to_csv(SUMMARY, index=False)

print("[PROBABILITY_POWER_REPLAY_V1] COMPLETE")
print(summary.to_string(index=False))
