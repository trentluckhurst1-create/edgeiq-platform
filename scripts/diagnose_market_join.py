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

fields["k"] = fields["horse"].apply(clean)
odds["k"] = odds["horse"].apply(clean)

fields["track_norm"] = fields["track"].astype(str).str.upper().str.strip()
odds["track_norm"] = odds["track"].astype(str).str.upper().str.strip()

fields["race_no_norm"] = pd.to_numeric(fields["race_no"], errors="coerce").astype("Int64")
odds["race_no_norm"] = pd.to_numeric(odds["race_no"], errors="coerce").astype("Int64")

print("FIELDS DATES:")
print(fields["race_date"].value_counts().head(20))
print()
print("ODDS DATES:")
print(odds["race_date"].value_counts().head(20))
print()
print("OVERLAP TRACKS:")
print(sorted(set(fields["track_norm"]) & set(odds["track_norm"])))
print()
print("MATCH BY HORSE ONLY:", fields["k"].isin(set(odds["k"])).sum())
print("MATCH BY HORSE+TRACK:", fields.set_index(["k","track_norm"]).index.isin(odds.set_index(["k","track_norm"]).index).sum())
print("MATCH BY HORSE+TRACK+RACE:", fields.set_index(["k","track_norm","race_no_norm"]).index.isin(odds.set_index(["k","track_norm","race_no_norm"]).index).sum())
print("MATCH BY HORSE+TRACK+RACE+DATE:", fields.set_index(["k","track_norm","race_no_norm","race_date"]).index.isin(odds.set_index(["k","track_norm","race_no_norm","race_date"]).index).sum())
