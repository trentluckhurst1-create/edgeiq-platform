import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_price_enrichment_research_v1.csv"

OUT = DATA / "edgeiq_probability_engine_v4_dna_overlay_research_v1.csv"
SUMMARY = DATA / "edgeiq_probability_engine_v4_dna_overlay_research_v1_summary.csv"
BY_RACE = DATA / "edgeiq_probability_engine_v4_dna_overlay_research_v1_by_race.csv"
BY_BAND = DATA / "edgeiq_probability_engine_v4_dna_overlay_research_v1_by_band.csv"
JSON_OUT = DATA / "edgeiq_probability_engine_v4_dna_overlay_research_v1_summary.json"

def num(x):
    return pd.to_numeric(x, errors="coerce")

df = pd.read_csv(SRC, low_memory=False)

for c in [
    "fair_price",
    "live_price",
    "edge_pct",
    "runner_dna_score",
    "dna_adjustment_pct",
    "form_score",
    "rating_score",
    "distance_score",
    "condition_score",
    "class_score",
    "sectional_score",
    "profile_score",
]:
    if c in df.columns:
        df[c] = num(df[c])

df["race_key"] = (
    df["race_date"].astype(str).str.strip() + "|" +
    df["track"].astype(str).str.upper().str.strip() + "|" +
    df["race_no"].astype(str).str.strip()
)

df["base_probability"] = np.where(df["fair_price"] > 0, 1 / df["fair_price"], np.nan)

df["dna_multiplier"] = 1 + (df["dna_adjustment_pct"].fillna(0) / 100)

df["dna_raw_probability"] = np.where(
    df["base_probability"].notna(),
    df["base_probability"] * df["dna_multiplier"],
    np.nan
)

race_sums = df.groupby("race_key", dropna=False).agg(
    base_probability_sum=("base_probability", "sum"),
    dna_raw_probability_sum=("dna_raw_probability", "sum"),
    runners=("horse", "count"),
    priced_runners=("base_probability", lambda s: int(s.notna().sum())),
).reset_index()

df = df.merge(race_sums, on="race_key", how="left")

df["dna_adjusted_probability"] = np.where(
    (df["dna_raw_probability"].notna()) & (df["dna_raw_probability_sum"] > 0),
    df["dna_raw_probability"] / df["dna_raw_probability_sum"],
    np.nan
)

df["dna_adjusted_fair_price"] = np.where(
    df["dna_adjusted_probability"] > 0,
    1 / df["dna_adjusted_probability"],
    np.nan
)

df["fair_price_delta"] = df["dna_adjusted_fair_price"] - df["fair_price"]
df["fair_price_delta_pct"] = np.where(
    df["fair_price"] > 0,
    (df["dna_adjusted_fair_price"] / df["fair_price"] - 1) * 100,
    np.nan
)

df["probability_delta"] = df["dna_adjusted_probability"] - df["base_probability"]
df["probability_delta_pct"] = np.where(
    df["base_probability"] > 0,
    (df["dna_adjusted_probability"] / df["base_probability"] - 1) * 100,
    np.nan
)

df["v4_price_rank"] = df.groupby("race_key")["dna_adjusted_probability"].rank(method="first", ascending=False)
df["base_price_rank"] = df.groupby("race_key")["base_probability"].rank(method="first", ascending=False)

df["rank_delta"] = df["base_price_rank"] - df["v4_price_rank"]

df["v4_edge_pct"] = np.where(
    (df["live_price"] > 0) & (df["dna_adjusted_fair_price"] > 0),
    ((df["live_price"] / df["dna_adjusted_fair_price"]) - 1) * 100,
    np.nan
)

df["v4_decision_research"] = np.select(
    [
        df["v4_edge_pct"] >= 18,
        df["v4_edge_pct"] >= 10,
        df["v4_edge_pct"] >= 6,
    ],
    [
        "EXECUTE_RESEARCH",
        "STRONG_WATCH_RESEARCH",
        "WATCH_RESEARCH",
    ],
    default="PASS_RESEARCH"
)

df.to_csv(OUT, index=False)

by_race = df.groupby("race_key", dropna=False).agg(
    race_date=("race_date", "first"),
    track=("track", "first"),
    race_no=("race_no", "first"),
    runners=("horse", "count"),
    priced_runners=("base_probability", lambda s: int(s.notna().sum())),
    base_probability_sum=("base_probability", "sum"),
    dna_adjusted_probability_sum=("dna_adjusted_probability", "sum"),
    base_top=("horse", lambda s: ""),
).reset_index()

tops = []
for race_key, g in df.groupby("race_key", dropna=False):
    g1 = g.sort_values("base_probability", ascending=False)
    g2 = g.sort_values("dna_adjusted_probability", ascending=False)
    tops.append({
        "race_key": race_key,
        "base_top": g1.iloc[0]["horse"] if len(g1) else "",
        "v4_top": g2.iloc[0]["horse"] if len(g2) else "",
        "base_top_prob": g1.iloc[0]["base_probability"] if len(g1) else np.nan,
        "v4_top_prob": g2.iloc[0]["dna_adjusted_probability"] if len(g2) else np.nan,
        "top_changed": (g1.iloc[0]["horse"] != g2.iloc[0]["horse"]) if len(g1) and len(g2) else False,
    })

tops = pd.DataFrame(tops)
by_race = by_race.drop(columns=["base_top"], errors="ignore").merge(tops, on="race_key", how="left")
by_race.to_csv(BY_RACE, index=False)

by_band = df.groupby("runner_dna_band", dropna=False).agg(
    runners=("horse", "count"),
    priced_runners=("base_probability", lambda s: int(s.notna().sum())),
    avg_dna_score=("runner_dna_score", "mean"),
    avg_base_fair=("fair_price", "mean"),
    avg_v4_fair=("dna_adjusted_fair_price", "mean"),
    avg_fair_delta_pct=("fair_price_delta_pct", "mean"),
    avg_probability_delta_pct=("probability_delta_pct", "mean"),
).reset_index()

for c in ["avg_dna_score","avg_base_fair","avg_v4_fair","avg_fair_delta_pct","avg_probability_delta_pct"]:
    by_band[c] = pd.to_numeric(by_band[c], errors="coerce").round(3)

by_band.to_csv(BY_BAND, index=False)

summary_rows = [
    {"metric": "status", "value": "PROBABILITY_ENGINE_V4_DNA_OVERLAY_RESEARCH_BUILT"},
    {"metric": "rows", "value": len(df)},
    {"metric": "races", "value": df["race_key"].nunique()},
    {"metric": "priced_rows", "value": int(df["base_probability"].notna().sum())},
    {"metric": "unpriced_rows", "value": int(df["base_probability"].isna().sum())},
    {"metric": "top_changed_races", "value": int(by_race["top_changed"].sum())},
    {"metric": "execute_research", "value": int((df["v4_decision_research"] == "EXECUTE_RESEARCH").sum())},
    {"metric": "strong_watch_research", "value": int((df["v4_decision_research"] == "STRONG_WATCH_RESEARCH").sum())},
    {"metric": "watch_research", "value": int((df["v4_decision_research"] == "WATCH_RESEARCH").sum())},
    {"metric": "pass_research", "value": int((df["v4_decision_research"] == "PASS_RESEARCH").sum())},
    {"metric": "avg_abs_fair_delta_pct", "value": round(float(df["fair_price_delta_pct"].abs().mean()), 3)},
    {"metric": "max_abs_fair_delta_pct", "value": round(float(df["fair_price_delta_pct"].abs().max()), 3)},
    {"metric": "production_prices_changed", "value": "NO"},
    {"metric": "production_probability_changed", "value": "NO"},
    {"metric": "research_only", "value": "YES"},
    {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
]

summary = pd.DataFrame(summary_rows)
summary.to_csv(SUMMARY, index=False)

JSON_OUT.write_text(
    json.dumps({r["metric"]: r["value"] for r in summary_rows}, indent=2),
    encoding="utf-8"
)

print("[PROBABILITY_ENGINE_V4_DNA_OVERLAY_RESEARCH] COMPLETE")
print(summary.to_string(index=False))
print()
print("=== BY BAND ===")
print(by_band.to_string(index=False))
print()
print("=== TOP CHANGED RACES ===")
print(by_race[by_race["top_changed"] == True].to_string(index=False))
