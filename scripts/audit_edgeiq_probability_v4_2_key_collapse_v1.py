from pathlib import Path
import pandas as pd
import re

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

PROB = DATA / "edgeiq_probability_engine_v4_2_candidate_replay.csv"
SPINE = DATA / "edgeiq_historical_replay_settled_v1.csv"

OUT = DATA / "edgeiq_probability_v4_2_key_collapse_audit_v1.csv"
SUMMARY = DATA / "edgeiq_probability_v4_2_key_collapse_summary_v1.csv"

def norm_text(x):
    if pd.isna(x):
        return ""
    return re.sub(r"\s+", " ", str(x).strip().upper())

def norm_horse(x):
    x = norm_text(x)
    x = re.sub(r"[^A-Z0-9 ]+", "", x)
    return re.sub(r"\s+", " ", x).strip()

def date_str(s):
    return pd.to_datetime(s, errors="coerce").dt.date.astype("string")

def num(s):
    return pd.to_numeric(s, errors="coerce")

print("[V4_2_KEY_COLLAPSE_AUDIT] START")

prob = pd.read_csv(PROB, low_memory=False)
spine = pd.read_csv(SPINE, low_memory=False)

p = pd.DataFrame()
p["race_date"] = date_str(prob["race_date"])
p["track"] = prob["track"].astype("string")
p["track_norm"] = prob["track"].map(norm_text)
p["race_no"] = num(prob["race_no"]).astype("Int64").astype("string")
p["horse"] = prob["horse"].astype("string")
p["horse_norm"] = prob["horse"].map(norm_horse)
p["race_key_source"] = prob.get("race_key", "").astype("string") if "race_key" in prob.columns else ""
p["horse_key_source"] = prob.get("horse_key", "").astype("string") if "horse_key" in prob.columns else ""
p["probability"] = num(prob["candidate_probability_v1"])
p["fair_price"] = num(prob["candidate_fair_price_v1"])
p["rating"] = num(prob["rating"])

p["rebuilt_race_key"] = (
    p["race_date"].fillna("").astype(str) + "|" +
    p["track_norm"].fillna("").astype(str) + "|" +
    p["race_no"].fillna("").astype(str)
)
p["rebuilt_runner_key"] = (
    p["rebuilt_race_key"].fillna("").astype(str) + "|" +
    p["horse_norm"].fillna("").astype(str)
)

s = pd.DataFrame()
s["race_date"] = date_str(spine["meeting_date"])
s["track_norm"] = spine["track"].map(norm_text)
s["race_no"] = num(spine["race_no"]).astype("Int64").astype("string")
s["horse_norm"] = spine["horse"].map(norm_horse)
s["rebuilt_runner_key"] = (
    s["race_date"].fillna("").astype(str) + "|" +
    s["track_norm"].fillna("").astype(str) + "|" +
    s["race_no"].fillna("").astype(str) + "|" +
    s["horse_norm"].fillna("").astype(str)
)

spine_keys = set(s["rebuilt_runner_key"])

p["matches_spine"] = p["rebuilt_runner_key"].isin(spine_keys)

dup = (
    p.groupby("rebuilt_runner_key", dropna=False)
    .agg(
        rows=("rebuilt_runner_key", "size"),
        race_date=("race_date", "first"),
        track=("track", "first"),
        race_no=("race_no", "first"),
        horse=("horse", "first"),
        probability_min=("probability", "min"),
        probability_max=("probability", "max"),
        rating_min=("rating", "min"),
        rating_max=("rating", "max"),
        source_race_keys=("race_key_source", "nunique"),
        source_horse_keys=("horse_key_source", "nunique"),
        matches_spine=("matches_spine", "max"),
    )
    .reset_index()
    .sort_values("rows", ascending=False)
)

dup.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "prob_rows": len(p),
    "rebuilt_unique_runner_keys": p["rebuilt_runner_key"].nunique(),
    "source_race_keys": p["race_key_source"].nunique(),
    "source_horse_keys": p["horse_key_source"].nunique(),
    "date_min": p["race_date"].min(),
    "date_max": p["race_date"].max(),
    "unique_dates": p["race_date"].nunique(),
    "unique_tracks": p["track_norm"].nunique(),
    "unique_races_rebuilt": p["rebuilt_race_key"].nunique(),
    "rows_matching_spine": int(p["matches_spine"].sum()),
    "unique_runner_keys_matching_spine": p.loc[p["matches_spine"], "rebuilt_runner_key"].nunique(),
    "duplicate_rows_above_1": int((dup["rows"] > 1).sum()),
    "max_duplicate_rows_one_runner": int(dup["rows"].max()) if len(dup) else 0,
    "verdict": "KEY_COLLAPSE_REQUIRES_SOURCE_KEY_AUDIT"
}])

summary.to_csv(SUMMARY, index=False)

print("[V4_2_KEY_COLLAPSE_AUDIT] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(summary.to_string(index=False))
print("")
print("[TOP_DUPLICATES]")
print(dup.head(30).to_string(index=False))
