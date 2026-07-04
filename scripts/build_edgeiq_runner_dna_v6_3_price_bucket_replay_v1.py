import pandas as pd

print("[PRICE_BUCKET_REPLAY_V1] START")

df = pd.read_csv("public/data/edgeiq_historical_replay_settled_v1.csv")
df = df[df["sp_valid"] == "True"]

df["sp"] = pd.to_numeric(df["sp_num_settled"], errors="coerce")

def bucket(x):
    if x < 3: return "LT_3"
    if x < 5: return "3_TO_5"
    if x < 10: return "5_TO_10"
    if x < 20: return "10_TO_20"
    return "20_PLUS"

df["bucket"] = df["sp"].apply(bucket)

out = df.groupby("bucket").agg({
    "won":"mean",
    "sp":"count"
}).reset_index()

print(out)

out.to_csv("public/data/edgeiq_runner_dna_v6_3_price_bucket_replay_v1.csv", index=False)
