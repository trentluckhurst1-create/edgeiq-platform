from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_historical_replay_settled_v1.csv"

DETAIL = DATA / "edgeiq_gap_to_winrate_curve_v1_detail.csv"
WIN_CURVE = DATA / "edgeiq_gap_to_winrate_curve_v1.csv"
PLACE_CURVE = DATA / "edgeiq_gap_to_place_curve_v1.csv"
PRICE_CURVE = DATA / "edgeiq_gap_to_price_curve_v1.csv"
SUMMARY = DATA / "edgeiq_gap_to_winrate_curve_summary_v1.csv"

GAP_BUCKETS = [
    (-999, -15, "LT_NEG_15"),
    (-15, -10, "NEG_15_TO_NEG_10"),
    (-10, -8, "NEG_10_TO_NEG_8"),
    (-8, -6, "NEG_8_TO_NEG_6"),
    (-6, -4, "NEG_6_TO_NEG_4"),
    (-4, -2, "NEG_4_TO_NEG_2"),
    (-2, 0, "NEG_2_TO_0"),
    (0, 2, "0_TO_2"),
    (2, 4, "2_TO_4"),
    (4, 6, "4_TO_6"),
    (6, 8, "6_TO_8"),
    (8, 10, "8_TO_10"),
    (10, 15, "10_TO_15"),
    (15, 999, "GT_15"),
]

def first_existing(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

def bucket_gap(g):
    if pd.isna(g):
        return "UNKNOWN"
    for lo, hi, label in GAP_BUCKETS:
        if g >= lo and g < hi:
            return label
    return "UNKNOWN"

def bucket_mid(label):
    mids = {
        "LT_NEG_15": -17.5,
        "NEG_15_TO_NEG_10": -12.5,
        "NEG_10_TO_NEG_8": -9,
        "NEG_8_TO_NEG_6": -7,
        "NEG_6_TO_NEG_4": -5,
        "NEG_4_TO_NEG_2": -3,
        "NEG_2_TO_0": -1,
        "0_TO_2": 1,
        "2_TO_4": 3,
        "4_TO_6": 5,
        "6_TO_8": 7,
        "8_TO_10": 9,
        "10_TO_15": 12.5,
        "GT_15": 17.5,
    }
    return mids.get(label, np.nan)

def safe_pct(n, d):
    return round((n / d) * 100, 3) if d else ""

def safe_price(pct):
    try:
        p = float(pct)
        if p <= 0:
            return ""
        return round(100 / p, 2)
    except Exception:
        return ""

df = pd.read_csv(SRC, dtype=str).fillna("")

gap_col = first_existing(df, [
    "projection_gap_V6_1_RESEARCH",
    "projection_gap_v6_1_research",
    "projection_gap_v5_2",
    "projection_gap",
])

win_col = first_existing(df, ["won", "win_flag", "winner", "won_num"])
place_col = first_existing(df, ["placed", "place_flag", "placed_num"])
finish_col = first_existing(df, ["finish_position", "finish_pos", "finishing_position"])

race_col = first_existing(df, ["race_key", "race_context_key", "race_id"])
horse_col = first_existing(df, ["horse", "runner", "horse_name"])
track_col = first_existing(df, ["track"])
race_no_col = first_existing(df, ["race_no"])
date_col = first_existing(df, ["meeting_date", "race_date", "date"])

missing = []
for name, col in [("gap", gap_col), ("win", win_col), ("race", race_col), ("horse", horse_col)]:
    if col is None:
        missing.append(name)

if place_col is None and finish_col is None:
    missing.append("place_or_finish_position")

if missing:
    raise RuntimeError(f"Missing required columns: {missing}. Available columns: {list(df.columns)}")

out = pd.DataFrame()
out["race_key"] = df[race_col]
out["meeting_date"] = df[date_col] if date_col else ""
out["track"] = df[track_col] if track_col else ""
out["race_no"] = df[race_no_col] if race_no_col else ""
out["horse"] = df[horse_col]
out["projection_gap"] = pd.to_numeric(df[gap_col], errors="coerce")
out["gap_bucket"] = out["projection_gap"].apply(bucket_gap)
out["gap_bucket_mid"] = out["gap_bucket"].apply(bucket_mid)
out["won"] = pd.to_numeric(df[win_col], errors="coerce").fillna(0).astype(int)

if place_col:
    out["placed"] = pd.to_numeric(df[place_col], errors="coerce").fillna(0).astype(int)
else:
    finish = pd.to_numeric(df[finish_col], errors="coerce")
    out["placed"] = ((finish >= 1) & (finish <= 3)).astype(int)

out = out[out["projection_gap"].notna()].copy()
built_at = datetime.now(timezone.utc).isoformat()
out["built_at"] = built_at
out.to_csv(DETAIL, index=False)

curve = (
    out.groupby(["gap_bucket", "gap_bucket_mid"], dropna=False)
    .agg(
        runners=("horse", "count"),
        races=("race_key", "nunique"),
        winners=("won", "sum"),
        placers=("placed", "sum"),
        avg_gap=("projection_gap", "mean"),
        min_gap=("projection_gap", "min"),
        max_gap=("projection_gap", "max"),
    )
    .reset_index()
)

curve["win_pct"] = curve.apply(lambda r: safe_pct(r["winners"], r["runners"]), axis=1)
curve["place_pct"] = curve.apply(lambda r: safe_pct(r["placers"], r["runners"]), axis=1)
curve["empirical_fair_price"] = curve["win_pct"].apply(safe_price)
curve["empirical_place_price"] = curve["place_pct"].apply(safe_price)

curve["avg_gap"] = curve["avg_gap"].round(3)
curve["min_gap"] = curve["min_gap"].round(3)
curve["max_gap"] = curve["max_gap"].round(3)

curve = curve.sort_values("gap_bucket_mid")

win_curve = curve[[
    "gap_bucket",
    "gap_bucket_mid",
    "runners",
    "races",
    "winners",
    "win_pct",
    "empirical_fair_price",
    "avg_gap",
    "min_gap",
    "max_gap",
]].copy()

place_curve = curve[[
    "gap_bucket",
    "gap_bucket_mid",
    "runners",
    "races",
    "placers",
    "place_pct",
    "empirical_place_price",
    "avg_gap",
    "min_gap",
    "max_gap",
]].copy()

price_curve = curve[[
    "gap_bucket",
    "gap_bucket_mid",
    "runners",
    "win_pct",
    "empirical_fair_price",
    "place_pct",
    "empirical_place_price",
]].copy()

win_curve.to_csv(WIN_CURVE, index=False)
place_curve.to_csv(PLACE_CURVE, index=False)
price_curve.to_csv(PRICE_CURVE, index=False)

ate_bucket = bucket_gap(-5.66)
tri_bucket = bucket_gap(8.92)

ate_row = curve[curve["gap_bucket"] == ate_bucket]
tri_row = curve[curve["gap_bucket"] == tri_bucket]

summary_rows = [
    {"metric": "status", "value": "GAP_TO_WINRATE_CURVE_V1_BUILT"},
    {"metric": "source", "value": SRC.name},
    {"metric": "detail", "value": DETAIL.name},
    {"metric": "win_curve", "value": WIN_CURVE.name},
    {"metric": "place_curve", "value": PLACE_CURVE.name},
    {"metric": "price_curve", "value": PRICE_CURVE.name},
    {"metric": "rows_used", "value": len(out)},
    {"metric": "races_used", "value": out["race_key"].nunique()},
    {"metric": "ate_iron_gap_test", "value": -5.66},
    {"metric": "ate_iron_bucket", "value": ate_bucket},
    {"metric": "ate_iron_bucket_win_pct", "value": ate_row["win_pct"].iloc[0] if len(ate_row) else ""},
    {"metric": "ate_iron_bucket_empirical_fair", "value": ate_row["empirical_fair_price"].iloc[0] if len(ate_row) else ""},
    {"metric": "triumvirate_gap_test", "value": 8.92},
    {"metric": "triumvirate_bucket", "value": tri_bucket},
    {"metric": "triumvirate_bucket_win_pct", "value": tri_row["win_pct"].iloc[0] if len(tri_row) else ""},
    {"metric": "triumvirate_bucket_empirical_fair", "value": tri_row["empirical_fair_price"].iloc[0] if len(tri_row) else ""},
    {"metric": "built_at", "value": built_at},
]

summary = pd.DataFrame(summary_rows)
summary.to_csv(SUMMARY, index=False)

print("[GAP_TO_WINRATE_CURVE_V1] COMPLETE")
print(summary.to_string(index=False))
print("")
print(win_curve.to_string(index=False))
