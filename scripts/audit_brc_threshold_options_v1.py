import pandas as pd
import numpy as np

brc = pd.read_csv(r"public\data\edgeiq_barrier_rail_condition_bias_replay_v1.csv", low_memory=False)

def band(lift, starts, pos_min, strong_min):
    if pd.isna(lift):
        return "UNKNOWN"
    lift = float(lift)
    starts = float(starts)

    if starts >= strong_min and lift >= 4:
        return "STRONG_POSITIVE"
    if starts >= pos_min and lift >= 2:
        return "POSITIVE"
    if starts >= strong_min and lift <= -4:
        return "STRONG_NEGATIVE"
    if starts >= pos_min and lift <= -2:
        return "NEGATIVE"
    return "NEUTRAL"

for pos_min, strong_min in [(20,40),(25,50),(30,60),(40,80),(50,80)]:
    col = f"band_{pos_min}_{strong_min}"
    brc[col] = brc.apply(
        lambda r: band(r["barrier_rail_condition_lift_pts"], r["bucket_starts_v1"], pos_min, strong_min),
        axis=1
    )

    print()
    print(f"=== THRESHOLDS POS>={pos_min} STRONG>={strong_min} ===")
    print(brc[col].value_counts(dropna=False).to_string())

    sandown = brc[brc["track"].astype(str).str.upper().eq("SPORTSBET SANDOWN HILLSIDE")]
    print()
    print("SANDOWN HILLSIDE")
    print(sandown[col].value_counts(dropna=False).to_string())
