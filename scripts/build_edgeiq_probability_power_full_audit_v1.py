from pathlib import Path
from datetime import datetime, timezone
import math
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_historical_replay_settled_v1.csv"

DETAIL = DATA / "edgeiq_probability_power_full_audit_v1_detail.csv"
SUMMARY = DATA / "edgeiq_probability_power_full_audit_v1_summary.csv"
CALIBRATION = DATA / "edgeiq_probability_power_full_audit_v1_calibration.csv"
BY_RACE = DATA / "edgeiq_probability_power_full_audit_v1_by_race.csv"
RECOMMENDATION = DATA / "edgeiq_probability_power_full_audit_v1_recommendation.csv"

POWERS = [0.55, 0.75, 1.00, 1.25]

PROB_BUCKETS = [
    (0.00, 0.05, "00_05"),
    (0.05, 0.10, "05_10"),
    (0.10, 0.15, "10_15"),
    (0.15, 0.20, "15_20"),
    (0.20, 0.25, "20_25"),
    (0.25, 0.30, "25_30"),
    (0.30, 0.40, "30_40"),
    (0.40, 1.01, "40_PLUS"),
]

def first_existing(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

def probability_bucket(p):
    if pd.isna(p):
        return "UNKNOWN"
    for lo, hi, label in PROB_BUCKETS:
        if p >= lo and p < hi:
            return label
    return "UNKNOWN"

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

def safe_div(a, b):
    return np.nan if not b else a / b

def rmse(values):
    arr = pd.to_numeric(values, errors="coerce").dropna()
    if not len(arr):
        return np.nan
    return math.sqrt(float((arr ** 2).mean()))

def mae(values):
    arr = pd.to_numeric(values, errors="coerce").dropna()
    if not len(arr):
        return np.nan
    return float(arr.abs().mean())

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
sp_col = first_existing(df, ["sp_num_settled", "sp_settled", "sp"])

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

if sp_col:
    df["_sp"] = pd.to_numeric(df[sp_col], errors="coerce")
else:
    df["_sp"] = np.nan

built_at = datetime.now(timezone.utc).isoformat()

detail_rows = []
race_rows = []

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

        probability = score / score_sum
        fair_price = 1.0 / probability
        price_rank = probability.rank(method="first", ascending=False).astype(int)

        temp = race.loc[known].copy()
        temp["_probability"] = probability
        temp["_fair_price"] = fair_price
        temp["_price_rank"] = price_rank
        temp["_prob_bucket"] = temp["_probability"].apply(probability_bucket)
        temp["_price_bucket"] = temp["_fair_price"].apply(price_bucket)

        top = temp.sort_values("_price_rank").iloc[0]
        top_prob = float(top["_probability"])
        top_fair = float(top["_fair_price"])

        race_rows.append({
            "power": power,
            "race_key": race_key,
            "meeting_date": top.get(date_col, "") if date_col else "",
            "track": top.get(track_col, "") if track_col else "",
            "race_no": top.get(race_no_col, "") if race_no_col else "",
            "known_count": known_count,
            "top_horse": top.get(horse_col, ""),
            "top_gap": round(float(top["_gap"]), 4),
            "top_probability": round(top_prob, 6),
            "top_fair_price": round(top_fair, 2),
            "top_won": int(top["_won"]),
            "top_placed": int(top["_placed"]),
            "built_at": built_at,
        })

        for _, r in temp.iterrows():
            p = float(r["_probability"])
            won = int(r["_won"])
            error = won - p
            brier = (p - won) ** 2

            sp = r["_sp"]
            overlay_pct = np.nan
            if pd.notna(sp) and sp > 0 and pd.notna(r["_fair_price"]) and r["_fair_price"] > 0:
                overlay_pct = ((sp / r["_fair_price"]) - 1.0) * 100

            detail_rows.append({
                "power": power,
                "race_key": race_key,
                "meeting_date": r.get(date_col, "") if date_col else "",
                "track": r.get(track_col, "") if track_col else "",
                "race_no": r.get(race_no_col, "") if race_no_col else "",
                "horse": r.get(horse_col, ""),
                "projection_gap": round(float(r["_gap"]), 4),
                "probability": round(p, 6),
                "fair_price": round(float(r["_fair_price"]), 2),
                "price_rank": int(r["_price_rank"]),
                "probability_bucket": r["_prob_bucket"],
                "price_bucket": r["_price_bucket"],
                "won": won,
                "placed": int(r["_placed"]),
                "calibration_error": round(error, 6),
                "abs_calibration_error": round(abs(error), 6),
                "brier_component": round(brier, 8),
                "sp": round(float(sp), 2) if pd.notna(sp) else "",
                "overlay_pct_vs_sp": round(float(overlay_pct), 2) if pd.notna(overlay_pct) else "",
                "known_count": known_count,
                "built_at": built_at,
            })

detail = pd.DataFrame(detail_rows)
by_race = pd.DataFrame(race_rows)

detail.to_csv(DETAIL, index=False)
by_race.to_csv(BY_RACE, index=False)

calibration_rows = []

for (power, bucket), g in detail.groupby(["power", "probability_bucket"], dropna=False):
    n = len(g)
    expected_wins = pd.to_numeric(g["probability"], errors="coerce").sum()
    actual_wins = pd.to_numeric(g["won"], errors="coerce").sum()
    avg_probability = pd.to_numeric(g["probability"], errors="coerce").mean()
    actual_win_pct = safe_div(actual_wins, n)
    expected_win_pct = safe_div(expected_wins, n)

    calibration_rows.append({
        "power": power,
        "probability_bucket": bucket,
        "rows": n,
        "expected_wins": round(expected_wins, 3),
        "actual_wins": int(actual_wins),
        "expected_win_pct": round(expected_win_pct * 100, 3) if pd.notna(expected_win_pct) else "",
        "actual_win_pct": round(actual_win_pct * 100, 3) if pd.notna(actual_win_pct) else "",
        "calibration_delta_pct": round((actual_win_pct - expected_win_pct) * 100, 3) if pd.notna(actual_win_pct) and pd.notna(expected_win_pct) else "",
        "avg_probability": round(avg_probability, 6),
        "avg_fair_price": round(pd.to_numeric(g["fair_price"], errors="coerce").mean(), 3),
        "brier_score": round(pd.to_numeric(g["brier_component"], errors="coerce").mean(), 8),
        "built_at": built_at,
    })

calibration = pd.DataFrame(calibration_rows)
calibration.to_csv(CALIBRATION, index=False)

summary_rows = []

for power, g in detail.groupby("power"):
    races = g["race_key"].nunique()
    top = g[g["price_rank"] == 1].copy()

    expected_total = pd.to_numeric(g["probability"], errors="coerce").sum()
    actual_total = pd.to_numeric(g["won"], errors="coerce").sum()

    cal = calibration[calibration["power"].astype(str) == str(power)].copy()
    cal["rows_num"] = pd.to_numeric(cal["rows"], errors="coerce")
    cal["delta_num"] = pd.to_numeric(cal["calibration_delta_pct"], errors="coerce")
    weighted_abs_cal_delta = (
        (cal["delta_num"].abs() * cal["rows_num"]).sum() / cal["rows_num"].sum()
        if cal["rows_num"].sum() else np.nan
    )

    longshots = g[pd.to_numeric(g["fair_price"], errors="coerce") >= 20]
    outsiders = g[pd.to_numeric(g["fair_price"], errors="coerce") >= 15]
    short = g[pd.to_numeric(g["fair_price"], errors="coerce") < 4]

    top_prob = pd.to_numeric(top["probability"], errors="coerce")
    top_fair = pd.to_numeric(top["fair_price"], errors="coerce")

    brier = pd.to_numeric(g["brier_component"], errors="coerce").mean()

    summary_rows.append({
        "power": power,
        "races": races,
        "runner_rows": len(g),
        "rank1_wins": int(top["won"].sum()),
        "rank1_places": int(top["placed"].sum()),
        "rank1_win_pct": round(top["won"].sum() / races * 100, 3) if races else "",
        "rank1_place_pct": round(top["placed"].sum() / races * 100, 3) if races else "",
        "expected_total_wins": round(expected_total, 3),
        "actual_total_wins": int(actual_total),
        "total_expected_vs_actual_delta": round(actual_total - expected_total, 3),
        "brier_score": round(brier, 8),
        "weighted_abs_calibration_delta_pct": round(weighted_abs_cal_delta, 3),
        "avg_top1_probability": round(top_prob.mean(), 6),
        "avg_top1_fair_price": round(top_fair.mean(), 3),
        "median_top1_fair_price": round(top_fair.median(), 3),
        "short_price_rows_under_4": len(short),
        "short_price_win_pct_under_4": round(short["won"].sum() / len(short) * 100, 3) if len(short) else "",
        "outsider_rows_15_plus": len(outsiders),
        "outsider_win_pct_15_plus": round(outsiders["won"].sum() / len(outsiders) * 100, 3) if len(outsiders) else "",
        "longshot_rows_20_plus": len(longshots),
        "longshot_win_pct_20_plus": round(longshots["won"].sum() / len(longshots) * 100, 3) if len(longshots) else "",
        "avg_runner_fair_price": round(pd.to_numeric(g["fair_price"], errors="coerce").mean(), 3),
        "median_runner_fair_price": round(pd.to_numeric(g["fair_price"], errors="coerce").median(), 3),
        "built_at": built_at,
    })

summary = pd.DataFrame(summary_rows)

# Recommendation scoring:
# lower brier is better, lower weighted calibration error is better.
# add realism penalty if avg top1 prob is very low or very high.
summary["_brier_rank"] = pd.to_numeric(summary["brier_score"], errors="coerce").rank(method="min", ascending=True)
summary["_cal_rank"] = pd.to_numeric(summary["weighted_abs_calibration_delta_pct"], errors="coerce").rank(method="min", ascending=True)

def realism_penalty(p):
    try:
        p = float(p)
    except Exception:
        return 10
    # expected top rank empirical win pct is about 21.6 in this replay source.
    # Do not let model favourites average absurdly low or absurdly high.
    if p < 0.20:
        return 2
    if p > 0.30:
        return 2
    return 0

summary["_realism_penalty"] = summary["avg_top1_probability"].apply(realism_penalty)
summary["_recommendation_score"] = summary["_brier_rank"] + summary["_cal_rank"] + summary["_realism_penalty"]
summary["recommendation_rank"] = summary["_recommendation_score"].rank(method="first", ascending=True).astype(int)

summary_out = summary.drop(columns=["_brier_rank", "_cal_rank", "_realism_penalty", "_recommendation_score"])
summary_out.to_csv(SUMMARY, index=False)

best = summary.sort_values(["_recommendation_score", "power"]).iloc[0]

recommendation = pd.DataFrame([
    {"metric": "status", "value": "PROBABILITY_POWER_FULL_AUDIT_V1_COMPLETE"},
    {"metric": "recommended_power", "value": best["power"]},
    {"metric": "recommended_reason", "value": "Lowest combined calibration/Brier score with realism guardrail"},
    {"metric": "current_power", "value": 0.55},
    {"metric": "current_power_status", "value": "AUDIT_ONLY_DO_NOT_PROMOTE_AUTOMATICALLY"},
    {"metric": "detail", "value": DETAIL.name},
    {"metric": "summary", "value": SUMMARY.name},
    {"metric": "calibration", "value": CALIBRATION.name},
    {"metric": "by_race", "value": BY_RACE.name},
    {"metric": "built_at", "value": built_at},
])
recommendation.to_csv(RECOMMENDATION, index=False)

print("[PROBABILITY_POWER_FULL_AUDIT_V1] COMPLETE")
print(f"detail={DETAIL}")
print(f"summary={SUMMARY}")
print(f"calibration={CALIBRATION}")
print(f"by_race={BY_RACE}")
print(f"recommendation={RECOMMENDATION}")
print(summary_out.to_string(index=False))
print("")
print(recommendation.to_string(index=False))
