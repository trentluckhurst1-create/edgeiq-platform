import pandas as pd

df = pd.read_csv("public/data/ratings_final_v1.csv", low_memory=False)

# compress ratings toward mean
mean = df["elite_today_rating"].mean()

df["elite_today_rating"] = (
    (df["elite_today_rating"] - mean) * 0.6 + mean
)

# rebuild market
df["elite_prob"] = 0.0
df["elite_rated_price"] = None

for rk, g in df.groupby(["race_date","track","race_no"]):
    total = g["elite_today_rating"].sum()
    if total > 0:
        probs = g["elite_today_rating"] / total
        df.loc[g.index, "elite_prob"] = probs
        df.loc[g.index, "elite_rated_price"] = (1 / probs).round(3)

df.to_csv("public/data/ratings_final_v2.csv", index=False)

print("RATINGS COMPRESSED")
print(df[["horse","elite_rated_price"]].head(20))
