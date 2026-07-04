import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_probability_engine_v5_factor_overlay_research_audit_v1.csv"

OUT = DATA / "edgeiq_v5_overlay_race4_flip_audit_v1.csv"
SUMMARY = DATA / "edgeiq_v5_overlay_race4_flip_audit_v1_summary.csv"

df = pd.read_csv(SRC, low_memory=False)

def num(x):
    return pd.to_numeric(x, errors="coerce")

for c in [
    "fair_price",
    "research_fair_price_v5",
    "base_probability",
    "research_probability_v5_num",
    "factor_overlay_score",
    "factor_adjustment_pct",
    "positive_factor_count",
    "negative_factor_count",
    "base_rank",
    "v5_rank",
    "rank_delta",
    "form_score",
    "rating_score",
    "distance_fit_score",
    "condition_fit_score",
    "class_fit_score",
    "profile_score",
    "sectional_score",
    "track_score",
]:
    if c in df.columns:
        df[c] = num(df[c])

race = df[
    (df["track"].astype(str).str.upper().str.strip() == "CAULFIELD HEATH") &
    (df["race_no"].astype(str).str.strip() == "4")
].copy()

race["focus_runner"] = race["horse"].isin(["FOUR CANDLES", "OAK BEACH"])

cols = [
    "track",
    "race_no",
    "horse",
    "focus_runner",
    "fair_price",
    "research_fair_price_v5",
    "base_probability",
    "research_probability_v5_num",
    "base_rank",
    "v5_rank",
    "rank_delta",
    "factor_overlay_score",
    "factor_adjustment_pct",
    "positive_factor_count",
    "negative_factor_count",
    "form_score",
    "rating_score",
    "distance_fit_score",
    "condition_fit_score",
    "class_fit_score",
    "profile_score",
    "sectional_score",
    "track_score",
    "runner_dna_v6_1_score",
    "runner_dna_v6_1_band",
    "runner_dna_v6_1_rank_in_race",
    "strongest_factor_v6_1",
    "weakest_factor_v6_1",
]

keep = [c for c in cols if c in race.columns]

race = race[keep].sort_values(
    ["v5_rank", "base_rank"],
    ascending=[True, True]
)

race.to_csv(OUT, index=False)

focus = race[race["focus_runner"] == True].copy()

summary_rows = [
    {"metric": "status", "value": "V5_RACE4_FLIP_AUDIT_BUILT"},
    {"metric": "race_rows", "value": len(race)},
    {"metric": "focus_rows", "value": len(focus)},
]

if len(focus) > 0:
    for _, r in focus.iterrows():
        horse = str(r.get("horse", "")).upper().replace(" ", "_")
        summary_rows.extend([
            {"metric": f"{horse}_base_rank", "value": r.get("base_rank", "")},
            {"metric": f"{horse}_v5_rank", "value": r.get("v5_rank", "")},
            {"metric": f"{horse}_fair_price", "value": r.get("fair_price", "")},
            {"metric": f"{horse}_v5_fair_price", "value": r.get("research_fair_price_v5", "")},
            {"metric": f"{horse}_overlay_score", "value": r.get("factor_overlay_score", "")},
            {"metric": f"{horse}_adjustment_pct", "value": r.get("factor_adjustment_pct", "")},
            {"metric": f"{horse}_positive_factors", "value": r.get("positive_factor_count", "")},
            {"metric": f"{horse}_negative_factors", "value": r.get("negative_factor_count", "")},
        ])

pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)

print("[V5_RACE4_FLIP_AUDIT] COMPLETE")
print(pd.DataFrame(summary_rows).to_string(index=False))
print()
print(race.to_string(index=False))
