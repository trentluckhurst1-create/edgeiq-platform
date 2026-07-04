import pandas as pd
from pathlib import Path

DATA = Path("./public/data")

INPUT = DATA / "edgeiq_live_runner_dna_v6_2.csv"
OUT = DATA / "edgeiq_runner_dna_explainability_feed_v2.csv"
SUMMARY = DATA / "edgeiq_runner_dna_explainability_feed_v2_summary.csv"

df = pd.read_csv(INPUT)

def num(col):
    if col not in df.columns:
        return pd.Series([0.0] * len(df))
    return pd.to_numeric(df[col], errors="coerce").fillna(0)

out = pd.DataFrame()

for c in ["race_date","track","race_no","horse","horse_key","trainer","jockey"]:
    out[c] = df[c] if c in df.columns else ""

out["dna_v6_2_score"] = num("dna_v6_2_score")
out["dna_v6_2_band"] = df["dna_v6_2_band"] if "dna_v6_2_band" in df.columns else ""

factor_map = {
    "rating_contribution": "rating_score",
    "sectional_contribution": "sectional_score",
    "jockey_contribution": "jockey_score",
    "trainer_contribution": "trainer_score",
    "connection_contribution": "tj_blend_score",
    "distance_contribution": "distance_fit_score",
    "condition_contribution": "condition_fit_score",
    "pace_contribution": "pace_score",
    "late_power_contribution": "late_power_score",
    "profile_contribution": "profile_score",
}

for new_col, source_col in factor_map.items():
    out[new_col] = num(source_col)

factor_cols = list(factor_map.keys())

out["largest_positive_factor"] = out[factor_cols].idxmax(axis=1).str.replace("_contribution","", regex=False).str.upper()
out["largest_negative_factor"] = out[factor_cols].idxmin(axis=1).str.replace("_contribution","", regex=False).str.upper()

out["positive_factor_score"] = out[factor_cols].max(axis=1)
out["negative_factor_score"] = out[factor_cols].min(axis=1)

out["explainability_summary"] = (
    "DNA " + out["dna_v6_2_score"].round(1).astype(str) +
    " " + out["dna_v6_2_band"].astype(str) +
    " | Strongest: " + out["largest_positive_factor"] +
    " " + out["positive_factor_score"].round(1).astype(str) +
    " | Weakest: " + out["largest_negative_factor"] +
    " " + out["negative_factor_score"].round(1).astype(str)
)

out.to_csv(OUT, index=False)

summary = pd.DataFrame([
    {"metric":"status","value":"RUNNER_DNA_EXPLAINABILITY_FEED_V2_BUILT"},
    {"metric":"rows","value":len(out)},
    {"metric":"source","value":str(INPUT)},
    {"metric":"output","value":str(OUT)},
])
summary.to_csv(SUMMARY, index=False)

print("[RUNNER_DNA_EXPLAINABILITY_FEED_V2] COMPLETE")
print(f"rows={len(out)}")
print(out[["horse","dna_v6_2_score","dna_v6_2_band","largest_positive_factor","positive_factor_score","largest_negative_factor","negative_factor_score"]].head(25).to_string(index=False))
