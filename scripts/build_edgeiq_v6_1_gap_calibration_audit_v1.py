from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUT_SOURCE_SCAN = DATA / "edgeiq_v6_1_gap_calibration_source_scan_v1.csv"
DETAIL = DATA / "edgeiq_v6_1_gap_calibration_audit_v1_detail.csv"
BUCKETS = DATA / "edgeiq_v6_1_gap_calibration_audit_v1_buckets.csv"
SUMMARY = DATA / "edgeiq_v6_1_gap_calibration_audit_v1_summary.csv"

PREFERRED_SOURCES = [
    DATA / "edgeiq_runner_dna_v6_3_historical_replay_v1.csv",
    DATA / "edgeiq_historical_replay_settled_v1.csv",
    DATA / "edgeiq_projection_v6_1_research_prior_rating_backtest.csv",
    DATA / "edgeiq_projection_v6_1_research_replay_backtest.csv",
]

GAP_BUCKETS = [
    (-999, -20, "LT_NEG_20"),
    (-20, -15, "NEG_20_TO_NEG_15"),
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
    (15, 20, "15_TO_20"),
    (20, 999, "GT_20"),
]

BAD_FILE_TOKENS = [
    "sensitivity",
    "summary",
    "calibration",
    "bucket",
    "recommendation",
    "audit_v1_detail",
    "scenario",
    "power_full",
    "power_replay",
    "gap_to_winrate",
]

def first_existing(cols, candidates):
    for c in candidates:
        if c in cols:
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
    mapping = {
        "LT_NEG_20": -25,
        "NEG_20_TO_NEG_15": -17.5,
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
        "15_TO_20": 17.5,
        "GT_20": 25,
    }
    return mapping.get(label, np.nan)

def safe_pct(n, d):
    return round((n / d) * 100, 3) if d else ""

def safe_price(win_pct):
    try:
        p = float(win_pct)
        if p <= 0:
            return ""
        return round(100 / p, 2)
    except Exception:
        return ""

def inspect_file(path: Path):
    lower_name = path.name.lower()
    if any(tok in lower_name for tok in BAD_FILE_TOKENS):
        return None

    try:
        sample = pd.read_csv(path, dtype=str, nrows=5000).fillna("")
    except Exception:
        return None

    cols = list(sample.columns)

    gap_col = first_existing(cols, [
        "projection_gap_V6_1_RESEARCH",
        "projection_gap_v6_1_research",
        "projection_gap_research",
        "projection_gap_v5_2",
    ])

    prob_col = first_existing(cols, [
        "V6_1_RESEARCH_probability",
        "rated_probability_V6_1_RESEARCH",
        "win_probability",
        "probability",
    ])

    fair_col = first_existing(cols, [
        "V6_1_RESEARCH_fair_price",
        "fair_price",
        "rated_price",
    ])

    win_col = first_existing(cols, ["won", "win_flag", "winner", "won_num"])
    place_col = first_existing(cols, ["placed", "place_flag", "placed_num"])
    finish_col = first_existing(cols, ["finish_position", "finish_pos", "finishing_position"])
    race_col = first_existing(cols, ["race_key", "race_context_key_v5_2", "race_context_key", "race_id"])
    horse_col = first_existing(cols, ["horse", "runner", "horse_name"])

    has_outcome = bool(win_col or finish_col)
    if not gap_col or not has_outcome or not horse_col:
        return None

    gap = pd.to_numeric(sample[gap_col], errors="coerce")
    positive_gap_rows = int((gap > 0).sum())

    useful_score = 0
    useful_score += 5000 if "v6_1" in gap_col.lower() else 0
    useful_score += 2000 if "settled" in lower_name or "replay" in lower_name or "backtest" in lower_name else 0
    useful_score += 1000 if has_outcome else 0
    useful_score += 500 if prob_col else 0
    useful_score += 300 if fair_col else 0
    useful_score += 200 if race_col else 0
    useful_score += min(positive_gap_rows, 500)

    return {
        "file": path.name,
        "path": str(path),
        "sample_rows": len(sample),
        "columns": len(cols),
        "gap_col": gap_col,
        "prob_col": prob_col or "",
        "fair_col": fair_col or "",
        "win_col": win_col or "",
        "place_col": place_col or "",
        "finish_col": finish_col or "",
        "race_col": race_col or "",
        "horse_col": horse_col or "",
        "positive_gap_rows_sample": positive_gap_rows,
        "min_gap_sample": round(gap.min(), 4) if gap.notna().any() else "",
        "max_gap_sample": round(gap.max(), 4) if gap.notna().any() else "",
        "useful_score": useful_score,
    }

scan_rows = []

for preferred in PREFERRED_SOURCES:
    if preferred.exists():
        info = inspect_file(preferred)
        if info:
            info["preferred_source"] = "YES"
            info["useful_score"] += 10000
            scan_rows.append(info)

for path in DATA.glob("*.csv"):
    info = inspect_file(path)
    if info:
        info["preferred_source"] = info.get("preferred_source", "NO")
        scan_rows.append(info)

scan = pd.DataFrame(scan_rows)

if scan.empty:
    raise RuntimeError("No valid source found with gap + outcome columns.")

scan = scan.drop_duplicates(subset=["path"]).sort_values(
    ["useful_score", "positive_gap_rows_sample"],
    ascending=[False, False]
)

scan.to_csv(OUT_SOURCE_SCAN, index=False)

source_row = scan.iloc[0]
SRC = Path(source_row["path"])

df = pd.read_csv(SRC, dtype=str).fillna("")
cols = list(df.columns)

gap_col = source_row["gap_col"]
prob_col = source_row["prob_col"] if str(source_row["prob_col"]).strip() else None
fair_col = source_row["fair_col"] if str(source_row["fair_col"]).strip() else None
win_col = source_row["win_col"] if str(source_row["win_col"]).strip() else None
place_col = source_row["place_col"] if str(source_row["place_col"]).strip() else None
finish_col = source_row["finish_col"] if str(source_row["finish_col"]).strip() else None
race_col = source_row["race_col"] if str(source_row["race_col"]).strip() else None
horse_col = source_row["horse_col"] if str(source_row["horse_col"]).strip() else None

track_col = first_existing(cols, ["track"])
race_no_col = first_existing(cols, ["race_no"])
date_col = first_existing(cols, ["meeting_date", "race_date", "date"])

if not race_col:
    df["_race_key_fallback"] = (
        df.get(date_col, "").astype(str) + "|" +
        df.get(track_col, "").astype(str) + "|R" +
        df.get(race_no_col, "").astype(str)
    )
    race_col = "_race_key_fallback"

out = pd.DataFrame()
out["race_key"] = df[race_col]
out["meeting_date"] = df[date_col] if date_col else ""
out["track"] = df[track_col] if track_col else ""
out["race_no"] = df[race_no_col] if race_no_col else ""
out["horse"] = df[horse_col]
out["projection_gap_used"] = pd.to_numeric(df[gap_col], errors="coerce")
out["gap_bucket"] = out["projection_gap_used"].apply(bucket_gap)
out["gap_bucket_mid"] = out["gap_bucket"].apply(bucket_mid)

if prob_col:
    out["model_probability"] = pd.to_numeric(df[prob_col], errors="coerce")
else:
    out["model_probability"] = np.nan

if fair_col:
    out["model_fair_price"] = pd.to_numeric(df[fair_col], errors="coerce")
else:
    out["model_fair_price"] = np.nan

if win_col:
    out["won"] = pd.to_numeric(df[win_col], errors="coerce").fillna(0).astype(int)
elif finish_col:
    finish = pd.to_numeric(df[finish_col], errors="coerce")
    out["won"] = (finish == 1).astype(int)

if place_col:
    out["placed"] = pd.to_numeric(df[place_col], errors="coerce").fillna(0).astype(int)
elif finish_col:
    finish = pd.to_numeric(df[finish_col], errors="coerce")
    out["placed"] = ((finish >= 1) & (finish <= 3)).astype(int)
else:
    out["placed"] = np.nan

out = out[out["projection_gap_used"].notna()].copy()

built_at = datetime.now(timezone.utc).isoformat()
out["source_file"] = SRC.name
out["gap_col_used"] = gap_col
out["prob_col_used"] = prob_col or ""
out["fair_col_used"] = fair_col or ""
out["built_at"] = built_at

out.to_csv(DETAIL, index=False)

bucket = (
    out.groupby(["gap_bucket", "gap_bucket_mid"], dropna=False)
    .agg(
        runners=("horse", "count"),
        races=("race_key", "nunique"),
        winners=("won", "sum"),
        placers=("placed", "sum"),
        avg_gap=("projection_gap_used", "mean"),
        min_gap=("projection_gap_used", "min"),
        max_gap=("projection_gap_used", "max"),
        avg_model_probability=("model_probability", "mean"),
        avg_model_fair_price=("model_fair_price", "mean"),
    )
    .reset_index()
    .sort_values("gap_bucket_mid")
)

bucket["actual_win_pct"] = bucket.apply(lambda r: safe_pct(r["winners"], r["runners"]), axis=1)
bucket["actual_place_pct"] = bucket.apply(lambda r: safe_pct(r["placers"], r["runners"]), axis=1)
bucket["empirical_fair_price"] = bucket["actual_win_pct"].apply(safe_price)
bucket["empirical_place_price"] = bucket["actual_place_pct"].apply(safe_price)
bucket["avg_model_probability_pct"] = (bucket["avg_model_probability"] * 100).round(3)
bucket["model_vs_actual_delta_pct"] = bucket["avg_model_probability_pct"] - pd.to_numeric(bucket["actual_win_pct"], errors="coerce")

for c in ["avg_gap", "min_gap", "max_gap", "avg_model_probability", "avg_model_fair_price", "model_vs_actual_delta_pct"]:
    bucket[c] = pd.to_numeric(bucket[c], errors="coerce").round(4)

bucket.to_csv(BUCKETS, index=False)

ate_gap = -5.66
tri_gap = 8.92
ate_bucket = bucket_gap(ate_gap)
tri_bucket = bucket_gap(tri_gap)

ate_row = bucket[bucket["gap_bucket"] == ate_bucket]
tri_row = bucket[bucket["gap_bucket"] == tri_bucket]

summary = pd.DataFrame([
    {"metric": "status", "value": "V6_1_GAP_CALIBRATION_AUDIT_V1_BUILT"},
    {"metric": "source_file", "value": SRC.name},
    {"metric": "source_scan", "value": OUT_SOURCE_SCAN.name},
    {"metric": "detail", "value": DETAIL.name},
    {"metric": "buckets", "value": BUCKETS.name},
    {"metric": "rows_used", "value": len(out)},
    {"metric": "races_used", "value": out["race_key"].nunique()},
    {"metric": "gap_col_used", "value": gap_col},
    {"metric": "prob_col_used", "value": prob_col or ""},
    {"metric": "fair_col_used", "value": fair_col or ""},
    {"metric": "ate_iron_gap_test", "value": ate_gap},
    {"metric": "ate_iron_bucket", "value": ate_bucket},
    {"metric": "ate_iron_bucket_rows", "value": int(ate_row["runners"].iloc[0]) if len(ate_row) else ""},
    {"metric": "ate_iron_actual_win_pct", "value": ate_row["actual_win_pct"].iloc[0] if len(ate_row) else ""},
    {"metric": "ate_iron_empirical_fair", "value": ate_row["empirical_fair_price"].iloc[0] if len(ate_row) else ""},
    {"metric": "ate_iron_avg_model_prob_pct", "value": ate_row["avg_model_probability_pct"].iloc[0] if len(ate_row) else ""},
    {"metric": "triumvirate_gap_test", "value": tri_gap},
    {"metric": "triumvirate_bucket", "value": tri_bucket},
    {"metric": "triumvirate_bucket_rows", "value": int(tri_row["runners"].iloc[0]) if len(tri_row) else ""},
    {"metric": "triumvirate_actual_win_pct", "value": tri_row["actual_win_pct"].iloc[0] if len(tri_row) else ""},
    {"metric": "triumvirate_empirical_fair", "value": tri_row["empirical_fair_price"].iloc[0] if len(tri_row) else ""},
    {"metric": "triumvirate_avg_model_prob_pct", "value": tri_row["avg_model_probability_pct"].iloc[0] if len(tri_row) else ""},
    {"metric": "built_at", "value": built_at},
])
summary.to_csv(SUMMARY, index=False)

print("[V6_1_GAP_CALIBRATION_AUDIT_V1] COMPLETE")
print("")
print("SOURCE SELECTED")
print(source_row.to_string())
print("")
print("SUMMARY")
print(summary.to_string(index=False))
print("")
print("BUCKETS")
print(bucket.to_string(index=False))
