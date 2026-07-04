import pandas as pd

INPUT_PROJECTION = ".\public\data\edgeiq_current_field_projection_v5_2_recovered_overlay_v1.csv"
OUTPUT_FILE = ".\public\data\edgeiq_first_starter_scores_v1.csv"

# Load data
df = pd.read_csv(INPUT_PROJECTION)

# Only target first starters
df_fs = df[df["starts_found_governed_v1"] == 0].copy()

# Build scores from component factors
def compute_first_starter_score(row):
    t_score = float(row.get("trainer_edge_score", 0)) * 0.3
    j_score = float(row.get("jockey_edge_score", 0)) * 0.25
    combo_score = float(row.get("trainer_jockey_edge_score", 0)) * 0.2
    barrier_score = float(row.get("barrier_fit_score", 0)) * 0.1
    track_fit_score = float(row.get("track_dna_score", 0)) * 0.1
    market_support = float(row.get("market_support_pct", 0)) * 0.05
    total_score = t_score + j_score + combo_score + barrier_score + track_fit_score + market_support
    return round(total_score, 2)

df_fs["first_starter_score"] = df_fs.apply(compute_first_starter_score, axis=1)

# Convert to bands for display
def score_to_band(score):
    if score >= 75:
        return "ELITE"
    elif score >= 60:
        return "STRONG"
    elif score >= 40:
        return "POSITIVE"
    elif score >= 25:
        return "NEUTRAL"
    else:
        return "LOW"

df_fs["first_starter_band"] = df_fs["first_starter_score"].apply(score_to_band)

# Save
df_fs.to_csv(OUTPUT_FILE, index=False)
print(f"[FIRST_STARTER_SCORES_V1] COMPLETE rows={len(df_fs)}")
