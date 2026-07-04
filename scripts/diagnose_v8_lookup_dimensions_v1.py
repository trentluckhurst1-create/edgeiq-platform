import pandas as pd

live=pd.read_csv(r"public\data\edgeiq_live_fair_price_v8_interaction_candidate_feed.csv",low_memory=False)
brc=pd.read_csv(r"public\data\edgeiq_barrier_rail_condition_bias_replay_v1.csv",low_memory=False)

print()
print("=== LIVE VALUES ===")

for c in [
    "track_norm_v8",
    "distance_bucket_v8",
    "condition_group_v8",
    "rail_bucket_v8",
    "barrier_bucket_v8"
]:
    print()
    print(c)
    print(sorted(live[c].dropna().astype(str).unique()))

print()
print("=== BRC VALUES ===")

for c in [
    "track_norm",
    "distance_bucket",
    "condition_group",
    "rail_bucket",
    "barrier_bucket"
]:
    print()
    print(c)
    print(sorted(brc[c].dropna().astype(str).unique())[:50])
