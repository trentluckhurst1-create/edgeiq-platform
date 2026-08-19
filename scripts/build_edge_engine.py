import pandas as pd

print("="*80)
print("EDGE ENGINE - FIXED SOURCE")
print("="*80)

df = pd.read_csv("public/data/ratings_final_v2.csv")

# load market
try:
    market = pd.read_csv("public/data/market_odds.csv")
    df = df.merge(market, on=["horse","race_date","track","race_no"], how="left")
except:
    df["market_price_clean"] = None

df["edge_pct"] = ((df["market_price_clean"] / df["elite_rated_price"]) - 1) * 100

df["edge_grade"] = "FAIR"
df.loc[df["edge_pct"] > 20, "edge_grade"] = "A+ OVERLAY"
df.loc[df["edge_pct"] > 10, "edge_grade"] = "A OVERLAY"
df.loc[df["edge_pct"] < -10, "edge_grade"] = "UNDER"

out = "public/data/edgeiq_live_bets.csv"
df.to_csv(out, index=False)

print("SAVED:", out)

print("\nSAMPLE:")
print(df[["horse","form_rating","elite_rated_price","market_price_clean","edge_pct","edge_grade"]].head(40).to_string(index=False))
