import pandas as pd
import re

ratings = pd.read_csv("public/data/ratings_final_v2.csv", low_memory=False)
odds = pd.read_csv("public/data/ladbrokes_affiliate_market_odds.csv", low_memory=False)

def clean(x):
    s = str(x).upper().strip()
    s = re.sub(r"\s*\([A-Z]+\)", "", s)
    s = s.replace("’","").replace("'","")
    s = re.sub(r"[^A-Z0-9 ]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

for df in [ratings, odds]:
    df["horse_clean"] = df["horse"].apply(clean)
    df["track_clean"] = df["track"].astype(str).str.upper().str.strip()
    df["race_no_clean"] = pd.to_numeric(df["race_no"], errors="coerce")
    df["date_clean"] = pd.to_datetime(df["race_date"], errors="coerce").dt.date

print("="*80)
print("MARKET JOIN DIAGNOSIS")
print("="*80)

print("\nRATINGS DATES:")
print(ratings["date_clean"].value_counts(dropna=False).head(20))

print("\nODDS DATES:")
print(odds["date_clean"].value_counts(dropna=False).head(20))

print("\nRATINGS TRACKS:")
print(sorted(ratings["track_clean"].dropna().unique())[:80])

print("\nODDS TRACKS:")
print(sorted(odds["track_clean"].dropna().unique())[:80])

print("\nOVERLAP TRACKS:")
print(sorted(set(ratings["track_clean"]) & set(odds["track_clean"])))

print("\nMATCH BY HORSE ONLY:")
print(len(set(ratings["horse_clean"]) & set(odds["horse_clean"])))

print("\nMATCH BY HORSE + TRACK:")
r1 = set(zip(ratings["horse_clean"], ratings["track_clean"]))
o1 = set(zip(odds["horse_clean"], odds["track_clean"]))
print(len(r1 & o1))

print("\nMATCH BY HORSE + TRACK + RACE:")
r2 = set(zip(ratings["horse_clean"], ratings["track_clean"], ratings["race_no_clean"]))
o2 = set(zip(odds["horse_clean"], odds["track_clean"], odds["race_no_clean"]))
print(len(r2 & o2))

print("\nMATCH BY HORSE + TRACK + RACE + DATE:")
r3 = set(zip(ratings["horse_clean"], ratings["track_clean"], ratings["race_no_clean"], ratings["date_clean"]))
o3 = set(zip(odds["horse_clean"], odds["track_clean"], odds["race_no_clean"], odds["date_clean"]))
print(len(r3 & o3))

print("\nSAMPLE RATINGS:")
print(ratings[["race_date","track","race_no","horse","horse_clean"]].head(30).to_string(index=False))

print("\nSAMPLE ODDS:")
print(odds[["race_date","track","race_no","horse","horse_clean","fixed_win","captured_at"]].head(30).to_string(index=False))
