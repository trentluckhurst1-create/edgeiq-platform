import pandas as pd
import re

def clean(x):
    if pd.isna(x):
        return ""
    x = str(x).upper()
    x = re.sub(r"\([^)]*\)", "", x)
    x = x.replace("’", "").replace("'", "")
    x = re.sub(r"[^A-Z0-9]", "", x)
    return x

ratings = pd.read_csv("public/data/ratings_audit_elite_v2.csv", low_memory=False)
speed = pd.read_csv("public/data/speed_map_report.csv", low_memory=False)

ratings["horse_key_norm"] = ratings["horse"].apply(clean)
speed["horse_key_norm"] = speed["horse"].apply(clean)

ratings["race_key"] = (
    ratings["race_date"].astype(str) + "|" +
    ratings["track"].astype(str).str.upper().str.strip() + "|" +
    ratings["race_no"].astype(str)
)

speed["race_key"] = (
    speed["race_date"].astype(str) + "|" +
    speed["track"].astype(str).str.upper().str.strip() + "|" +
    speed["race_no"].astype(str)
)

merged = ratings.merge(
    speed[["race_key", "horse_key_norm", "speed_map_bucket", "map_style"]],
    on=["race_key", "horse_key_norm"],
    how="left",
    suffixes=("", "_speed")
)

bucket_col = "speed_map_bucket"
style_col = "map_style"

if bucket_col not in merged.columns and "speed_map_bucket_speed" in merged.columns:
    bucket_col = "speed_map_bucket_speed"

if style_col not in merged.columns and "map_style_speed" in merged.columns:
    style_col = "map_style_speed"

merged["runner_style"] = merged[bucket_col].fillna(merged[style_col])

merged.to_csv("public/data/ratings_audit_elite_v2.csv", index=False)

print("FIXED RUNNER STYLE JOIN")
print(merged["runner_style"].value_counts(dropna=False))
