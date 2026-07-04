from pathlib import Path
import pandas as pd
import re
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_historical_probability_archive_v1.csv"
SUMMARY = DATA / "edgeiq_historical_probability_archive_v1_summary.csv"
AUDIT = DATA / "edgeiq_historical_probability_archive_v1_audit.csv"

def norm_text(x):
    if pd.isna(x):
        return ""
    return re.sub(r"\s+", " ", str(x).strip().upper())

def norm_track(x):
    return norm_text(x)

def norm_horse(x):
    x = norm_text(x)
    x = re.sub(r"[^A-Z0-9 ]+", "", x)
    return re.sub(r"\s+", " ", x).strip()

def to_date(x):
    return pd.to_datetime(x, errors="coerce").dt.date.astype("string")

def num(s):
    return pd.to_numeric(s, errors="coerce")

def first_col(df, names):
    lower = {c.lower(): c for c in df.columns}
    for n in names:
        if n.lower() in lower:
            return lower[n.lower()]
    return None

def make_race_key(df):
    return (
        df["race_date"].fillna("").astype(str) + "|" +
        df["track_norm"].fillna("").astype(str) + "|" +
        df["race_no"].fillna("").astype(str)
    )

def make_runner_key(df):
    return (
        df["race_key"].fillna("").astype(str) + "|" +
        df["horse_norm"].fillna("").astype(str)
    )

def standardise(path, source_name, priority, prob_cols, fair_cols, rating_cols, date_cols, track_cols, race_cols, horse_cols):
    if not path.exists():
        return pd.DataFrame(), {
            "source": source_name,
            "status": "MISSING",
            "rows_in": 0,
            "rows_out": 0
        }

    df = pd.read_csv(path, low_memory=False)
    rows_in = len(df)

    date_col = first_col(df, date_cols)
    track_col = first_col(df, track_cols)
    race_col = first_col(df, race_cols)
    horse_col = first_col(df, horse_cols)
    prob_col = first_col(df, prob_cols)
    fair_col = first_col(df, fair_cols)
    rating_col = first_col(df, rating_cols)

    out = pd.DataFrame()
    out["source_file"] = path.name
    out["source_name"] = source_name
    out["source_priority"] = priority

    out["race_date"] = to_date(df[date_col]) if date_col else pd.Series([""] * rows_in)
    out["track"] = df[track_col].astype("string") if track_col else ""
    out["track_norm"] = out["track"].map(norm_track)
    out["race_no"] = num(df[race_col]).astype("Int64").astype("string") if race_col else ""
    out["horse"] = df[horse_col].astype("string") if horse_col else ""
    out["horse_norm"] = out["horse"].map(norm_horse)

    out["probability"] = num(df[prob_col]) if prob_col else pd.NA
    out["fair_price"] = num(df[fair_col]) if fair_col else pd.NA
    out["rating"] = num(df[rating_col]) if rating_col else pd.NA

    out["probability_col"] = prob_col or ""
    out["fair_price_col"] = fair_col or ""
    out["rating_col"] = rating_col or ""

    out["race_key"] = make_race_key(out)
    out["runner_key"] = make_runner_key(out)

    out["has_identity"] = (
        out["race_date"].fillna("").ne("") &
        out["track_norm"].fillna("").ne("") &
        out["race_no"].fillna("").ne("") &
        out["horse_norm"].fillna("").ne("")
    )

    out["has_probability"] = out["probability"].notna() & (out["probability"] > 0)
    out["has_fair_price"] = out["fair_price"].notna() & (out["fair_price"] > 0)
    out["has_rating"] = out["rating"].notna()

    out = out[
        out["has_identity"] &
        (out["has_probability"] | out["has_fair_price"] | out["has_rating"])
    ].copy()

    audit = {
        "source": source_name,
        "status": "READ",
        "rows_in": rows_in,
        "rows_out": len(out),
        "date_col": date_col or "",
        "track_col": track_col or "",
        "race_col": race_col or "",
        "horse_col": horse_col or "",
        "probability_col": prob_col or "",
        "fair_price_col": fair_col or "",
        "rating_col": rating_col or "",
        "prob_rows": int(out["has_probability"].sum()) if len(out) else 0,
        "fair_price_rows": int(out["has_fair_price"].sum()) if len(out) else 0,
        "rating_rows": int(out["has_rating"].sum()) if len(out) else 0,
    }

    return out, audit

sources = [
    {
        "file": "edgeiq_probability_engine_v4_2_candidate_replay.csv",
        "name": "V4_2_CANDIDATE_REPLAY",
        "priority": 10,
        "prob": ["candidate_probability_v1", "hybrid_probability_v1", "current_v6_1_probability_v1"],
        "fair": ["candidate_fair_price_v1", "hybrid_fair_price_v1", "current_v6_1_fair_price_v1"],
        "rating": ["rating", "rating_gap"],
        "date": ["race_date", "meeting_date"],
        "track": ["track"],
        "race": ["race_no"],
        "horse": ["horse"],
    },
    {
        "file": "edgeiq_historical_replay_settled_v1.csv",
        "name": "HISTORICAL_REPLAY_SETTLED",
        "priority": 8,
        "prob": [],
        "fair": [],
        "rating": ["governed_projection_rating_v6", "confidence_adjusted_rating_v6", "projected_rating_v5_2"],
        "date": ["meeting_date", "race_date"],
        "track": ["track"],
        "race": ["race_no"],
        "horse": ["horse"],
    },
    {
        "file": "edgeiq_historical_performance_rating_v6_1_research.csv",
        "name": "HISTORICAL_PERFORMANCE_RATING_V6_1",
        "priority": 7,
        "prob": [],
        "fair": [],
        "rating": ["performance_rating_v6_1_research", "performance_rating_v5_1", "performance_rating_v3"],
        "date": ["race_date", "meeting_date"],
        "track": ["track"],
        "race": ["race_no"],
        "horse": ["horse"],
    },
    {
        "file": "edgeiq_probability_research_v6_candidate.csv",
        "name": "CURRENT_V6_RESEARCH_CANDIDATE",
        "priority": 5,
        "prob": ["v6_probability", "v5_2_probability", "production_probability"],
        "fair": ["v6_fair_price", "v5_2_fair_price", "production_fair_price"],
        "rating": ["rating", "rating_gap_to_top"],
        "date": ["race_date", "meeting_date"],
        "track": ["track"],
        "race": ["race_no"],
        "horse": ["horse"],
    },
    {
        "file": "edgeiq_probability_research_v5_compression_fix.csv",
        "name": "CURRENT_V5_COMPRESSION_RESEARCH",
        "priority": 4,
        "prob": ["candidate_probability_v5", "production_probability"],
        "fair": ["candidate_fair_price_v5", "production_fair_price"],
        "rating": ["rating", "rating_gap_to_top"],
        "date": ["race_date", "meeting_date"],
        "track": ["track"],
        "race": ["race_no"],
        "horse": ["horse"],
    },
]

frames = []
audits = []

print("[HISTORICAL_PROBABILITY_ARCHIVE_V1] START")

for s in sources:
    frame, audit = standardise(
        DATA / s["file"],
        s["name"],
        s["priority"],
        s["prob"],
        s["fair"],
        s["rating"],
        s["date"],
        s["track"],
        s["race"],
        s["horse"],
    )
    frames.append(frame)
    audits.append(audit)

raw = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

if len(raw):
    raw = raw.sort_values(
        ["runner_key", "has_probability", "source_priority"],
        ascending=[True, False, False]
    )

    archive = raw.drop_duplicates("runner_key", keep="first").copy()
else:
    archive = raw.copy()

archive["built_at"] = datetime.now(timezone.utc).isoformat()

archive.to_csv(OUT, index=False)

audit_df = pd.DataFrame(audits)
audit_df.to_csv(AUDIT, index=False)

summary_rows = [{
    "built_at": datetime.now(timezone.utc).isoformat(),
    "raw_rows": len(raw),
    "archive_rows": len(archive),
    "unique_races": archive["race_key"].nunique() if len(archive) else 0,
    "probability_rows": int(archive["has_probability"].sum()) if len(archive) else 0,
    "fair_price_rows": int(archive["has_fair_price"].sum()) if len(archive) else 0,
    "rating_rows": int(archive["has_rating"].sum()) if len(archive) else 0,
    "status": "ARCHIVE_BUILT_RESEARCH_ONLY"
}]

summary = pd.DataFrame(summary_rows)
summary.to_csv(SUMMARY, index=False)

print("[HISTORICAL_PROBABILITY_ARCHIVE_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(f"audit={AUDIT}")
print(summary.to_string(index=False))
print("")
print("[SOURCE_AUDIT]")
print(audit_df.to_string(index=False))
