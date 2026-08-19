from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_live_runner_dna_v6_2.csv"

OUT = DATA / "edgeiq_live_runner_dna_v6_3_medium_delta_research.csv"
SUMMARY = DATA / "edgeiq_runner_dna_v6_3_medium_delta_research_summary.csv"

built_at = datetime.now(timezone.utc).isoformat()

df = pd.read_csv(SRC, dtype=str).fillna("")

def num(x):
    try:
        s = str(x).replace("$","").replace("%","").strip()
        if s == "" or s.lower() == "nan":
            return np.nan
        return float(s)
    except Exception:
        return np.nan

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

BASE_SCORE_COL = "dna_v6_2_score"

FACTOR_MAP = {
    "rating_score": 0.15,
    "sectional_score": 0.15,
    "jockey_score": 0.15,
    "combo_score": 0.15,
}

df["v6_2_score_base"] = df[BASE_SCORE_COL].apply(num)

adjustment = pd.Series(0.0, index=df.index)

for col, delta_weight in FACTOR_MAP.items():
    if col not in df.columns:
        df[col] = ""
    vals = df[col].apply(num)
    centred = ((vals - 50.0) / 50.0).clip(-1, 1)
    adjustment += centred.fillna(0) * delta_weight * 2.0

df["v6_3_medium_delta_adjustment"] = adjustment.round(3)
df["dna_v6_3_medium_delta_score"] = (df["v6_2_score_base"] + adjustment).clip(0,100).round(1)
df["dna_v6_3_medium_delta_band"] = df["dna_v6_3_medium_delta_score"].apply(band)

df["runner_dna_v6_3_medium_delta_rank_in_race"] = (
    df.groupby(["track", "race_no"])["dna_v6_3_medium_delta_score"]
    .rank(method="first", ascending=False)
)

df["score_delta_vs_v6_2"] = (df["dna_v6_3_medium_delta_score"] - df["v6_2_score_base"]).round(3)
df["band_changed_vs_v6_2"] = np.where(df["dna_v6_2_band"] != df["dna_v6_3_medium_delta_band"], "YES", "NO")
df["rank_delta_vs_v6_2"] = df["runner_dna_v6_3_medium_delta_rank_in_race"] - pd.to_numeric(df["runner_dna_v6_2_rank_in_race"], errors="coerce")

df["research_only"] = "YES"
df["built_at_v6_3_medium_delta"] = built_at

df.to_csv(OUT, index=False)

summary = pd.DataFrame([
    ["status", "RUNNER_DNA_V6_3_MEDIUM_DELTA_RESEARCH_BUILT"],
    ["rows", len(df)],
    ["avg_score", round(float(df["dna_v6_3_medium_delta_score"].mean()), 2)],
    ["avg_abs_score_delta", round(float(df["score_delta_vs_v6_2"].abs().mean()), 3)],
    ["max_abs_score_delta", round(float(df["score_delta_vs_v6_2"].abs().max()), 3)],
    ["avg_abs_rank_delta", round(float(pd.to_numeric(df["rank_delta_vs_v6_2"], errors="coerce").abs().mean()), 3)],
    ["max_abs_rank_delta", round(float(pd.to_numeric(df["rank_delta_vs_v6_2"], errors="coerce").abs().max()), 3)],
    ["band_changed_rows", int((df["band_changed_vs_v6_2"] == "YES").sum())],
    ["elite", int((df["dna_v6_3_medium_delta_band"] == "ELITE").sum())],
    ["strong", int((df["dna_v6_3_medium_delta_band"] == "STRONG").sum())],
    ["positive", int((df["dna_v6_3_medium_delta_band"] == "POSITIVE").sum())],
    ["neutral", int((df["dna_v6_3_medium_delta_band"] == "NEUTRAL").sum())],
    ["negative", int((df["dna_v6_3_medium_delta_band"] == "NEGATIVE").sum())],
    ["poor", int((df["dna_v6_3_medium_delta_band"] == "POOR").sum())],
    ["research_only", "YES"],
    ["built_at", built_at],
], columns=["metric","value"])

summary.to_csv(SUMMARY, index=False)

print("[RUNNER_DNA_V6_3_MEDIUM_DELTA_RESEARCH] COMPLETE")
print(summary.to_string(index=False))
print(f"wrote={OUT}")
print(f"wrote={SUMMARY}")
