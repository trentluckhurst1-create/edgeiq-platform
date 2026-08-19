import pandas as pd
import re

def class_score(x):
    if pd.isna(x): return 1.0
    s = str(x).upper()

    if "GROUP" in s or "G1" in s: return 1.25
    if "G2" in s or "G3" in s: return 1.15
    if "LISTED" in s: return 1.10
    if "BM" in s:
        try:
            num = int(re.findall(r"\d+", s)[0])
            return 0.8 + (num / 100)
        except:
            return 1.0
    if "MAIDEN" in s: return 0.85

    return 1.0

df = pd.read_csv("public/data/ratings_final_v2.csv", low_memory=False)

df["class_factor"] = df["race_class"].apply(class_score)

df["elite_today_rating"] = df["elite_today_rating"] * df["class_factor"]

# rebuild market
df["elite_prob"] = 0.0

for rk, g in df.groupby(["race_date","track","race_no"]):
    total = g["elite_today_rating"].sum()
    if total > 0:
        probs = g["elite_today_rating"] / total
        df.loc[g.index, "elite_prob"] = probs
        df.loc[g.index, "elite_rated_price"] = (1 / probs).round(3)

df.to_csv("public/data/ratings_final_v3.csv", index=False)

print("CLASS MODEL APPLIED")
print(df[["horse","race_class","elite_rated_price"]].head(20))
