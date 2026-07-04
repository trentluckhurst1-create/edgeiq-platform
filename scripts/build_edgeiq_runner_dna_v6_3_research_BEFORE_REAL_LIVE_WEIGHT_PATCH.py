import pandas as pd
import numpy as np
import re
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

BASE_DNA = DATA / "edgeiq_runner_dna_current.csv"
DIST = DATA / "edgeiq_live_distance_dna_v1.csv"
COND = DATA / "edgeiq_live_condition_dna_v1.csv"
CLASS = DATA / "edgeiq_live_class_dna_v3.csv"
TJ = DATA / "edgeiq_live_trainer_jockey_factor_feed_v3.csv"

OUT = DATA / "edgeiq_live_runner_dna_v6_3_research.csv"
SUMMARY = DATA / "edgeiq_runner_dna_v6_3_research_summary.csv"
JSON_OUT = DATA / "edgeiq_runner_dna_v6_2_summary.json"

def canon_horse(x):
    if pd.isna(x):
        return ""
    s = str(x).upper().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def band(score):
    if pd.isna(score):
        return "NO_PROFILE"
    if score >= 85:
        return "ELITE"
    if score >= 72:
        return "STRONG"
    if score >= 58:
        return "POSITIVE"
    if score >= 45:
        return "NEUTRAL"
    if score >= 30:
        return "NEGATIVE"
    return "POOR"

def tj_score_to_100(x):
    n = pd.to_numeric(x, errors="coerce")
    if pd.isna(n):
        return np.nan
    return max(0, min(100, 50 + (float(n) * 25)))

base = pd.read_csv(BASE_DNA, low_memory=False)
dist = pd.read_csv(DIST, low_memory=False)
cond = pd.read_csv(COND, low_memory=False)
cls = pd.read_csv(CLASS, low_memory=False)
tj = pd.read_csv(TJ, low_memory=False)

for df in [base, dist, cond, cls, tj]:
    df["horse_join"] = df["horse"].apply(canon_horse)
    df["track_join"] = df["track"].astype(str).str.upper().str.strip()
    df["race_join"] = pd.to_numeric(df["race_no"], errors="coerce").fillna(-1).astype(int)

join_cols = ["track_join", "race_join", "horse_join"]

dna = base.copy()

dna = dna.merge(
    dist[join_cols + ["distance_fit_score", "distance_fit_band"]],
    on=join_cols,
    how="left",
    suffixes=("", "_distance")
)

dna = dna.merge(
    cond[join_cols + ["condition_fit_score", "condition_fit_band"]],
    on=join_cols,
    how="left",
    suffixes=("", "_condition")
)

dna = dna.merge(
    cls[join_cols + ["class_fit_score", "class_fit_band", "class_movement"]],
    on=join_cols,
    how="left",
    suffixes=("", "_class")
)

tj_keep = tj[
    join_cols + [
        "trainer_factor_score_v1",
        "jockey_factor_score_v1",
        "combo_factor_score_v1",
        "trainer_jockey_blend_score_v3",
        "trainer_factor_band_v1",
        "jockey_factor_band_v1",
        "combo_factor_band_v1",
        "trainer_jockey_blend_band_v3",
        "trainer_factor_matched_v3",
        "jockey_factor_matched_v3",
        "combo_factor_matched_v3",
        "tj_factor_verdict_v3",
        "trainer",
        "jockey",
    ]
].copy()

tj_keep = tj_keep.drop_duplicates(subset=join_cols, keep="first")

dna = dna.merge(
    tj_keep,
    on=join_cols,
    how="left",
    suffixes=("", "_tj")
)

for src in [
    "trainer_factor_score_v1",
    "jockey_factor_score_v1",
    "combo_factor_score_v1",
    "trainer_jockey_blend_score_v3",
]:
    tj_col = src + "_tj"
    if src not in dna.columns and tj_col in dna.columns:
        dna[src] = dna[tj_col]
    elif src in dna.columns and tj_col in dna.columns:
        dna[src] = dna[src].where(dna[src].notna(), dna[tj_col])

dna["trainer_score"] = dna["trainer_factor_score_v1"].apply(tj_score_to_100)
dna["jockey_score"] = dna["jockey_factor_score_v1"].apply(tj_score_to_100)
dna["combo_score"] = dna["combo_factor_score_v1"].apply(tj_score_to_100)
dna["tj_blend_score"] = dna["trainer_jockey_blend_score_v3"].apply(tj_score_to_100)

for c in [
    "distance_fit_score",
    "condition_fit_score",
    "class_fit_score",
    "trainer_score",
    "jockey_score",
    "combo_score",
    "tj_blend_score",
]:
    dna[c] = pd.to_numeric(dna[c], errors="coerce")

score_candidates = [
    "distance_fit_score",
    "condition_fit_score",
    "class_fit_score",
    "trainer_score",
    "jockey_score",
    "combo_score",
]

dna["dna_v6_2_component_count"] = dna[score_candidates].notna().sum(axis=1)

weights = {
    "distance_fit_score": 1.00,
    "condition_fit_score": 1.00,
    "class_fit_score": 1.00,
    "trainer_score": 0.30,
    "jockey_score": 0.30,
    "combo_score": 0.40,
}

weighted_sum = pd.Series(0.0, index=dna.index)
weight_sum = pd.Series(0.0, index=dna.index)

for col, w in weights.items():
    valid = dna[col].notna()
    weighted_sum.loc[valid] += dna.loc[valid, col] * w
    weight_sum.loc[valid] += w

dna["dna_v6_2_score"] = np.where(
    weight_sum > 0,
    (weighted_sum / weight_sum).round(1),
    np.nan
)

dna["dna_v6_2_band"] = dna["dna_v6_2_score"].apply(band)

def strongest_factor(row):
    vals = {
        "DISTANCE": row.get("distance_fit_score"),
        "CONDITION": row.get("condition_fit_score"),
        "CLASS": row.get("class_fit_score"),
        "TRAINER": row.get("trainer_score"),
        "JOCKEY": row.get("jockey_score"),
        "COMBO": row.get("combo_score"),
    }
    vals = {k: float(v) for k, v in vals.items() if pd.notna(v)}
    if len(vals) == 0:
        return pd.Series(["UNKNOWN", 0])
    best = max(vals, key=vals.get)
    return pd.Series([best, round(vals[best], 1)])

def weakest_factor(row):
    vals = {
        "DISTANCE": row.get("distance_fit_score"),
        "CONDITION": row.get("condition_fit_score"),
        "CLASS": row.get("class_fit_score"),
        "TRAINER": row.get("trainer_score"),
        "JOCKEY": row.get("jockey_score"),
        "COMBO": row.get("combo_score"),
    }
    vals = {k: float(v) for k, v in vals.items() if pd.notna(v)}
    if len(vals) == 0:
        return pd.Series(["UNKNOWN", 0])
    worst = min(vals, key=vals.get)
    return pd.Series([worst, round(vals[worst], 1)])

dna[["strongest_factor_v6_2", "strongest_factor_score_v6_2"]] = dna.apply(strongest_factor, axis=1)
dna[["weakest_factor_v6_2", "weakest_factor_score_v6_2"]] = dna.apply(weakest_factor, axis=1)

def build_narrative(row):
    bullets = []

    if row.get("distance_fit_band") == "ELITE":
        bullets.append("Elite distance profile")
    elif row.get("distance_fit_band") == "STRONG":
        bullets.append("Strong distance profile")

    if row.get("condition_fit_band") == "ELITE":
        bullets.append("Outstanding condition profile")
    elif row.get("condition_fit_band") == "STRONG":
        bullets.append("Condition positive")

    if row.get("class_movement") == "CLASS_RISE":
        bullets.append("Rising in grade")
    elif row.get("class_movement") == "CLASS_DROP":
        bullets.append("Class drop positive")

    if row.get("class_fit_band") == "ELITE":
        bullets.append("Elite class performance")
    elif row.get("class_fit_band") == "STRONG":
        bullets.append("Strong class performance")

    tj_band = str(row.get("trainer_jockey_blend_band_v3", "")).upper()
    if tj_band == "ELITE":
        bullets.append("Elite trainer-jockey edge")
    elif tj_band == "POSITIVE":
        bullets.append("Trainer-jockey edge positive")
    elif tj_band in ["NEGATIVE", "POOR"]:
        bullets.append("Trainer-jockey edge risk")

    if len(bullets) == 0:
        bullets.append("Limited DNA evidence available")

    return ". ".join(bullets) + "."

dna["runner_dna_v6_2_narrative"] = dna.apply(build_narrative, axis=1)

dna["runner_dna_v6_2_rank_in_race"] = (
    dna.groupby(["track_join", "race_join"])["dna_v6_2_score"]
    .rank(method="first", ascending=False)
)

dna.to_csv(OUT, index=False)

summary_rows = [
    {"metric": "status", "value": "RUNNER_DNA_V6_3_RESEARCH_BUILT"},
    {"metric": "rows", "value": len(dna)},
    {"metric": "avg_score", "value": round(float(dna["dna_v6_2_score"].mean()), 2)},
    {"metric": "tj_rows_matched", "value": int(dna["trainer_jockey_blend_score_v3"].notna().sum())},
    {"metric": "trainer_nonblank", "value": int(dna["trainer_score"].notna().sum())},
    {"metric": "jockey_nonblank", "value": int(dna["jockey_score"].notna().sum())},
    {"metric": "combo_nonblank", "value": int(dna["combo_score"].notna().sum())},
    {"metric": "elite", "value": int((dna["dna_v6_2_band"] == "ELITE").sum())},
    {"metric": "strong", "value": int((dna["dna_v6_2_band"] == "STRONG").sum())},
    {"metric": "positive", "value": int((dna["dna_v6_2_band"] == "POSITIVE").sum())},
    {"metric": "neutral", "value": int((dna["dna_v6_2_band"] == "NEUTRAL").sum())},
    {"metric": "negative", "value": int((dna["dna_v6_2_band"] == "NEGATIVE").sum())},
    {"metric": "poor", "value": int((dna["dna_v6_2_band"] == "POOR").sum())},
    {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
]

summary = pd.DataFrame(summary_rows)
summary.to_csv(SUMMARY, index=False)

JSON_OUT.write_text(
    json.dumps({r["metric"]: r["value"] for r in summary_rows}, indent=2),
    encoding="utf-8"
)

print("[RUNNER_DNA_V6_3_RESEARCH] COMPLETE")
print(summary.to_string(index=False))
print()
print(dna.sort_values("dna_v6_2_score", ascending=False)[[
    "track",
    "race_no",
    "horse",
    "dna_v6_2_score",
    "dna_v6_2_band",
    "trainer_score",
    "jockey_score",
    "combo_score",
    "trainer_jockey_blend_band_v3",
    "strongest_factor_v6_2",
    "weakest_factor_v6_2",
]].head(30).to_string(index=False))

