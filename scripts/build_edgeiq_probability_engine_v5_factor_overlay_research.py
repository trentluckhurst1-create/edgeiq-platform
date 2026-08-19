import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]

dna_file = ROOT / "public/data/edgeiq_runner_dna_ui_feed_v1.csv"

out_file = ROOT / "public/data/edgeiq_probability_engine_v5_factor_overlay_research.csv"
summary_file = ROOT / "public/data/edgeiq_probability_engine_v5_factor_overlay_research_summary.csv"
factor_file = ROOT / "public/data/edgeiq_probability_engine_v5_factor_overlay_research_by_factor.csv"
race_file = ROOT / "public/data/edgeiq_probability_engine_v5_factor_overlay_research_by_race.csv"

df = pd.read_csv(dna_file, dtype=str).fillna("")

def num(v):
    try:
        return float(v)
    except:
        return 0.0

score_fields = {
    "FORM":"form_score",
    "RATING":"rating_score",
    "DISTANCE":"distance_fit_score",
    "CONDITION":"condition_fit_score",
    "CLASS":"class_fit_score",
    "PROFILE":"profile_score",
    "SECTIONAL":"sectional_score",
    "TRACK":"track_score",
    "TRAINER":"trainer_score",
    "JOCKEY":"jockey_score",
    "COMBO":"combo_score"
}

factor_rows = []

positive_counts = []
negative_counts = []
overlay_scores = []

for _, row in df.iterrows():

    pos = 0
    neg = 0

    for factor, field in score_fields.items():

        score = num(row.get(field, ""))

        positive_hit = False
        negative_hit = False

        if score >= 75:
            pos += 1
            positive_hit = True

        if score > 0 and score <= 40:
            neg += 1
            negative_hit = True

        factor_rows.append({
            "horse": row.get("horse",""),
            "factor": factor,
            "score": round(score,2),
            "positive": positive_hit,
            "negative": negative_hit
        })

    positive_counts.append(pos)
    negative_counts.append(neg)

    overlay = (pos * 2.0) - (neg * 3.0)
    overlay_scores.append(overlay)

df["positive_factor_count"] = positive_counts
df["negative_factor_count"] = negative_counts
df["factor_overlay_score"] = overlay_scores

adjustments = []

for overlay in overlay_scores:

    if overlay >= 10:
        adj = 8

    elif overlay >= 6:
        adj = 6

    elif overlay >= 2:
        adj = 4

    elif overlay <= -10:
        adj = -8

    elif overlay <= -6:
        adj = -6

    elif overlay <= -2:
        adj = -4

    else:
        adj = 0

    adjustments.append(adj)

df["factor_adjustment_pct"] = adjustments

research_probabilities = []
research_prices = []

for _, row in df.iterrows():

    fair_price = num(row.get("fair_price"))

    adj = num(row.get("factor_adjustment_pct"))

    if fair_price <= 0:
        research_probabilities.append("")
        research_prices.append("")
        continue

    base_prob = 1 / fair_price

    adjusted_prob = base_prob * (1 + (adj / 100))

    research_probabilities.append(round(adjusted_prob, 6))

    if adjusted_prob > 0:
        research_prices.append(round(1 / adjusted_prob, 4))
    else:
        research_prices.append("")

df["research_probability_v5"] = research_probabilities
df["research_fair_price_v5"] = research_prices

df.to_csv(out_file, index=False)

factor_summary = (
    pd.DataFrame(factor_rows)
    .groupby("factor")
    .agg(
        positive_hits=("positive","sum"),
        negative_hits=("negative","sum"),
        avg_score=("score","mean")
    )
    .reset_index()
)

factor_summary.to_csv(factor_file, index=False)

race_summary = (
    df.groupby(["track","race_no"])
      .agg(
          runners=("horse","count"),
          avg_overlay=("factor_overlay_score","mean"),
          avg_adjustment=("factor_adjustment_pct","mean")
      )
      .reset_index()
)

race_summary.to_csv(race_file, index=False)

summary = pd.DataFrame([
    {
        "metric":"status",
        "value":"PROBABILITY_ENGINE_V5_FACTOR_OVERLAY_RESEARCH_BUILT"
    },
    {
        "metric":"rows",
        "value":len(df)
    },
    {
        "metric":"positive_factor_total",
        "value":int(df["positive_factor_count"].sum())
    },
    {
        "metric":"negative_factor_total",
        "value":int(df["negative_factor_count"].sum())
    },
    {
        "metric":"avg_overlay_score",
        "value":round(df["factor_overlay_score"].mean(),2)
    },
    {
        "metric":"avg_adjustment_pct",
        "value":round(df["factor_adjustment_pct"].mean(),2)
    },
    {
        "metric":"built_at",
        "value":datetime.now(timezone.utc).isoformat()
    }
])

summary.to_csv(summary_file, index=False)

print("[PROBABILITY_ENGINE_V5_FACTOR_OVERLAY_RESEARCH] COMPLETE")
print(summary)
