import pandas as pd
import re

def clean(x):
    if pd.isna(x): return ""
    s = str(x).upper()
    s = re.sub(r"\([^)]*\)", "", s)
    s = s.replace("’","").replace("'","")
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s

fields = pd.read_csv("public/data/race_fields.csv", low_memory=False)
odds = pd.read_csv("../../outputs/markets/ladbrokes_affiliate_market_odds.csv", low_memory=False)

for c in ["market_price", "market_price_x", "market_price_y"]:
    if c in fields.columns:
        fields = fields.drop(columns=[c])

fields["k"] = fields["horse"].apply(clean)
odds["k"] = odds["horse"].apply(clean)

fields["track_norm"] = fields["track"].astype(str).str.upper().str.strip()
odds["track_norm"] = odds["track"].astype(str).str.upper().str.strip()

fields["race_no_norm"] = pd.to_numeric(fields["race_no"], errors="coerce").astype("Int64")
odds["race_no_norm"] = pd.to_numeric(odds["race_no"], errors="coerce").astype("Int64")

odds["market_price"] = pd.to_numeric(odds["fixed_win"], errors="coerce")

odds_small = (
    odds[["k", "track_norm", "race_no_norm", "market_price"]]
    .dropna(subset=["market_price"])
    .drop_duplicates(subset=["k", "track_norm", "race_no_norm"], keep="last")
)

df = fields.merge(
    odds_small,
    on=["k", "track_norm", "race_no_norm"],
    how="left"
)

df.to_csv("public/data/race_fields.csv", index=False)

print("MARKET MERGED BY HORSE + TRACK + RACE")
print("NON-NULL MARKET COUNT:", df["market_price"].notna().sum())
print()
print(df[df["market_price"].notna()][["race_date","track","race_no","horse","market_price"]].head(60).to_string(index=False))
