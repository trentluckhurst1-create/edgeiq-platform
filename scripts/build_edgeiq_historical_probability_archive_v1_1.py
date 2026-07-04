from pathlib import Path
import pandas as pd
import re
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SPINE = DATA / "edgeiq_historical_replay_settled_v1.csv"
PROB = DATA / "edgeiq_probability_engine_v4_2_candidate_replay.csv"

OUT = DATA / "edgeiq_historical_probability_archive_v1_1.csv"
SUMMARY = DATA / "edgeiq_historical_probability_archive_v1_1_summary.csv"
AUDIT = DATA / "edgeiq_historical_probability_archive_v1_1_audit.csv"

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

print("[HISTORICAL_PROBABILITY_ARCHIVE_V1_1] START")

spine = pd.read_csv(SPINE, low_memory=False)
prob = pd.read_csv(PROB, low_memory=False)

spine_out = pd.DataFrame()
spine_out["race_date"] = date_str(spine["meeting_date"])
spine_out["track"] = spine["track"].astype("string")
spine_out["track_norm"] = spine_out["track"].map(norm_text)
spine_out["race_no"] = num(spine["race_no"]).astype("Int64").astype("string")
spine_out["horse"] = spine["horse"].astype("string")
spine_out["horse_norm"] = spine_out["horse"].map(norm_horse)
spine_out["rating"] = num(spine["governed_projection_rating_v6"])
spine_out["rating_source"] = "edgeiq_historical_replay_settled_v1.csv"
spine_out["race_key"] = (
    spine_out["race_date"].fillna("").astype(str) + "|" +
    spine_out["track_norm"].fillna("").astype(str) + "|" +
    spine_out["race_no"].fillna("").astype(str)
)
spine_out["runner_key"] = (
    spine_out["race_key"].fillna("").astype(str) + "|" +
    spine_out["horse_norm"].fillna("").astype(str)
)

prob_out = pd.DataFrame()
prob_out["race_date"] = date_str(prob["race_date"])
prob_out["track_norm"] = prob["track"].map(norm_text)
prob_out["race_no"] = num(prob["race_no"]).astype("Int64").astype("string")
prob_out["horse_norm"] = prob["horse"].map(norm_horse)
prob_out["runner_key"] = (
    prob_out["race_date"].fillna("").astype(str) + "|" +
    prob_out["track_norm"].fillna("").astype(str) + "|" +
    prob_out["race_no"].fillna("").astype(str) + "|" +
    prob_out["horse_norm"].fillna("").astype(str)
)

prob_out["archive_probability"] = num(prob["candidate_probability_v1"])
prob_out["archive_fair_price"] = num(prob["candidate_fair_price_v1"])
prob_out["archive_rating"] = num(prob["rating"])
prob_out["archive_rating_gap"] = num(prob["rating_gap"])
prob_out["probability_source"] = "edgeiq_probability_engine_v4_2_candidate_replay.csv"

prob_out = prob_out[
    prob_out["runner_key"].notna() &
    prob_out["archive_probability"].notna() &
    (prob_out["archive_probability"] > 0)
].copy()

prob_out = (
    prob_out
    .sort_values(["runner_key", "archive_probability"], ascending=[True, False])
    .drop_duplicates("runner_key", keep="first")
)

archive = spine_out.merge(
    prob_out[
        [
            "runner_key",
            "archive_probability",
            "archive_fair_price",
            "archive_rating",
            "archive_rating_gap",
            "probability_source"
        ]
    ],
    on="runner_key",
    how="left"
)

archive["final_probability"] = archive["archive_probability"]
archive["final_fair_price"] = archive["archive_fair_price"]
archive["final_rating"] = archive["archive_rating"].where(
    archive["archive_rating"].notna(),
    archive["rating"]
)

archive["has_probability"] = archive["final_probability"].notna() & (archive["final_probability"] > 0)
archive["has_fair_price"] = archive["final_fair_price"].notna() & (archive["final_fair_price"] > 0)
archive["has_rating"] = archive["final_rating"].notna()

archive["archive_status"] = archive.apply(
    lambda r: "PROBABILITY_AND_RATING" if r["has_probability"] and r["has_rating"]
    else "RATING_ONLY" if r["has_rating"]
    else "NO_MODEL_STATE",
    axis=1
)

archive["built_at"] = datetime.now(timezone.utc).isoformat()

archive.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "built_at": datetime.now(timezone.utc).isoformat(),
    "spine_rows": len(spine_out),
    "prob_source_rows": len(prob),
    "prob_source_unique_runner_keys": prob_out["runner_key"].nunique(),
    "archive_rows": len(archive),
    "unique_races": archive["race_key"].nunique(),
    "probability_rows": int(archive["has_probability"].sum()),
    "fair_price_rows": int(archive["has_fair_price"].sum()),
    "rating_rows": int(archive["has_rating"].sum()),
    "probability_coverage_pct": round(float(archive["has_probability"].mean() * 100), 2),
    "rating_coverage_pct": round(float(archive["has_rating"].mean() * 100), 2),
    "status": "ARCHIVE_V1_1_BUILT_RESEARCH_ONLY"
}])

summary.to_csv(SUMMARY, index=False)

audit = (
    archive
    .groupby("archive_status")
    .size()
    .reset_index(name="rows")
    .sort_values("rows", ascending=False)
)

audit.to_csv(AUDIT, index=False)

print("[HISTORICAL_PROBABILITY_ARCHIVE_V1_1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(f"audit={AUDIT}")
print(summary.to_string(index=False))
print("")
print(audit.to_string(index=False))
