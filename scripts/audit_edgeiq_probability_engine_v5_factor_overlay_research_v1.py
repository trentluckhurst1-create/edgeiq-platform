import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_probability_engine_v5_factor_overlay_research.csv"

OUT = DATA / "edgeiq_probability_engine_v5_factor_overlay_research_audit_v1.csv"
SUMMARY = DATA / "edgeiq_probability_engine_v5_factor_overlay_research_audit_v1_summary.csv"
BY_ADJ = DATA / "edgeiq_probability_engine_v5_factor_overlay_research_audit_v1_by_adjustment.csv"

df = pd.read_csv(SRC, low_memory=False)

def num(c):
    return pd.to_numeric(df[c], errors="coerce") if c in df.columns else pd.Series(np.nan, index=df.index)

df["fair_price_num"] = num("fair_price")
df["research_fair_price_v5_num"] = num("research_fair_price_v5")
df["factor_adjustment_pct_num"] = num("factor_adjustment_pct")
df["factor_overlay_score_num"] = num("factor_overlay_score")

df["fair_price_delta"] = df["research_fair_price_v5_num"] - df["fair_price_num"]
df["fair_price_delta_pct"] = np.where(
    df["fair_price_num"] > 0,
    ((df["research_fair_price_v5_num"] / df["fair_price_num"]) - 1) * 100,
    np.nan
)

df["base_probability"] = np.where(df["fair_price_num"] > 0, 1 / df["fair_price_num"], np.nan)
df["research_probability_v5_num"] = num("research_probability_v5")
df["probability_delta_pct"] = np.where(
    df["base_probability"] > 0,
    ((df["research_probability_v5_num"] / df["base_probability"]) - 1) * 100,
    np.nan
)

df["race_key"] = (
    df["race_date"].astype(str).str.strip() + "|" +
    df["track"].astype(str).str.upper().str.strip() + "|" +
    df["race_no"].astype(str).str.strip()
)

rank_rows = []

for race_key, g in df.groupby("race_key", dropna=False):
    priced = g[g["fair_price_num"].notna() & g["research_fair_price_v5_num"].notna()].copy()

    if priced.empty:
        continue

    priced["base_rank"] = priced["base_probability"].rank(method="first", ascending=False)
    priced["v5_rank"] = priced["research_probability_v5_num"].rank(method="first", ascending=False)
    priced["rank_delta"] = priced["base_rank"] - priced["v5_rank"]

    for _, r in priced.iterrows():
        rank_rows.append({
            "race_key": race_key,
            "horse": r["horse"],
            "base_rank": r["base_rank"],
            "v5_rank": r["v5_rank"],
            "rank_delta": r["rank_delta"],
        })

rank_df = pd.DataFrame(rank_rows)

if not rank_df.empty:
    df = df.merge(rank_df, on=["race_key", "horse"], how="left")
else:
    df["base_rank"] = np.nan
    df["v5_rank"] = np.nan
    df["rank_delta"] = np.nan

df.to_csv(OUT, index=False)

by_adj = df.groupby("factor_adjustment_pct", dropna=False).agg(
    runners=("horse", "count"),
    priced_runners=("fair_price_num", lambda s: int(s.notna().sum())),
    avg_overlay=("factor_overlay_score_num", "mean"),
    avg_fair_delta_pct=("fair_price_delta_pct", "mean"),
    avg_probability_delta_pct=("probability_delta_pct", "mean"),
    avg_rank_delta=("rank_delta", "mean"),
).reset_index()

for c in ["avg_overlay", "avg_fair_delta_pct", "avg_probability_delta_pct", "avg_rank_delta"]:
    by_adj[c] = pd.to_numeric(by_adj[c], errors="coerce").round(3)

by_adj.to_csv(BY_ADJ, index=False)

top_changed = 0
race_rows = []

for race_key, g in df.groupby("race_key", dropna=False):
    priced = g[g["fair_price_num"].notna() & g["research_fair_price_v5_num"].notna()].copy()

    if priced.empty:
        continue

    base_top = priced.sort_values("base_probability", ascending=False).iloc[0]
    v5_top = priced.sort_values("research_probability_v5_num", ascending=False).iloc[0]
    changed = str(base_top["horse"]) != str(v5_top["horse"])

    if changed:
        top_changed += 1

    race_rows.append({
        "race_key": race_key,
        "track": base_top.get("track", ""),
        "race_no": base_top.get("race_no", ""),
        "base_top": base_top["horse"],
        "v5_top": v5_top["horse"],
        "base_top_prob": base_top["base_probability"],
        "v5_top_prob": v5_top["research_probability_v5_num"],
        "top_changed": changed,
    })

race_audit = pd.DataFrame(race_rows)

summary = pd.DataFrame([
    {"metric": "status", "value": "V5_FACTOR_OVERLAY_RESEARCH_AUDIT_COMPLETE"},
    {"metric": "rows", "value": len(df)},
    {"metric": "priced_rows", "value": int(df["fair_price_num"].notna().sum())},
    {"metric": "races", "value": df["race_key"].nunique()},
    {"metric": "top_changed_races", "value": int(top_changed)},
    {"metric": "avg_adjustment_pct", "value": round(float(df["factor_adjustment_pct_num"].mean()), 3)},
    {"metric": "avg_abs_fair_delta_pct", "value": round(float(df["fair_price_delta_pct"].abs().mean()), 3)},
    {"metric": "max_abs_fair_delta_pct", "value": round(float(df["fair_price_delta_pct"].abs().max()), 3)},
    {"metric": "positive_factor_total", "value": int(pd.to_numeric(df["positive_factor_count"], errors="coerce").fillna(0).sum())},
    {"metric": "negative_factor_total", "value": int(pd.to_numeric(df["negative_factor_count"], errors="coerce").fillna(0).sum())},
    {"metric": "production_prices_changed", "value": "NO"},
    {"metric": "production_probability_changed", "value": "NO"},
    {"metric": "research_only", "value": "YES"},
    {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
])

summary.to_csv(SUMMARY, index=False)

print("[V5_FACTOR_OVERLAY_RESEARCH_AUDIT] COMPLETE")
print(summary.to_string(index=False))
print()
print("=== BY ADJUSTMENT ===")
print(by_adj.to_string(index=False))
print()
print("=== RACE TOPS ===")
print(race_audit.to_string(index=False))
