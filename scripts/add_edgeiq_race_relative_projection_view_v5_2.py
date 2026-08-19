from pathlib import Path
import pandas as pd
import numpy as np

path = Path(r".\public\data\edgeiq_current_field_projection_v5_2.csv")
backup = Path(r".\public\data\edgeiq_current_field_projection_v5_2_PRE_RACE_RELATIVE_VIEW.csv")

df = pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)
df.to_csv(backup, index=False)

for col in ["projected_rating_v5_2", "race_target_rating_v5_2", "projection_gap_v5_2"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

race_key = (
    df["race_date"].astype(str) + "|" +
    df["track"].astype(str) + "|R" +
    df["race_no"].astype(str)
)

df["_race_key_tmp"] = race_key

df["race_projected_rank_v5_2"] = ""
df["race_projected_gap_to_top_v5_2"] = ""
df["race_relative_band_v5_2"] = ""

for key, g in df.groupby("_race_key_tmp", dropna=False):
    idx = g.index
    rated = g[g["projected_rating_v5_2"].notna()].copy()

    if rated.empty:
        df.loc[idx, "race_relative_band_v5_2"] = "NO_PROJECTION"
        continue

    top_rating = rated["projected_rating_v5_2"].max()
    ranks = rated["projected_rating_v5_2"].rank(method="dense", ascending=False).astype(int)

    for i, rnk in ranks.items():
        gap_to_top = float(df.at[i, "projected_rating_v5_2"] - top_rating)

        df.at[i, "race_projected_rank_v5_2"] = str(rnk)
        df.at[i, "race_projected_gap_to_top_v5_2"] = f"{gap_to_top:.2f}"

        if rnk == 1:
            band = "TOP_RATED"
        elif gap_to_top >= -2:
            band = "CONTENDER"
        elif gap_to_top >= -5:
            band = "MIXED"
        elif gap_to_top >= -10:
            band = "WEAK"
        else:
            band = "LOW_RATED"

        df.at[i, "race_relative_band_v5_2"] = band

    unrated_idx = g[g["projected_rating_v5_2"].isna()].index
    df.loc[unrated_idx, "race_relative_band_v5_2"] = "NO_PROJECTION"

df = df.drop(columns=["_race_key_tmp"])
df.to_csv(path, index=False)

print("WROTE:", path)
print("BACKUP:", backup)
