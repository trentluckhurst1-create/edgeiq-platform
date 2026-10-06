from pathlib import Path
import pandas as pd
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research")
files=[
 ROOT/"model_lab_123"/"LAB123_RULE2_TIMESTAMPED_PRICES.csv",
 ROOT/"model_lab_123"/"LAB123_PRICE_SOURCE_INVENTORY.csv",
 ROOT/"model_lab_080"/"LAB080S3F_ACTUAL_STARTER_EXECUTABLE_MARKET_GATE.csv",
 ROOT/"model_lab_080"/"LAB081F_CERTIFIED_PREJUMP_MARKET_RUNNERS.csv"]
for p in files:
 print("\nFILE",p)
 if not p.exists():print("MISSING");continue
 d=pd.read_csv(p)
 print("ROWS",len(d),"COLS",list(d.columns))
 for dc in ["race_date","race_date_model"]:
  if dc in d:
   x=pd.to_datetime(d[dc],errors="coerce");print("DATES",dc,x.min(),x.max())
   yy=x.dt.year
   for y in [2021,2022,2023,2024]:
    z=d[yy.eq(y)]
    if len(z):
     races=z["canonical_race_id"].nunique() if "canonical_race_id" in z else (z["_race"].nunique() if "_race" in z else None)
     horses=z["canonical_horse_id"].nunique() if "canonical_horse_id" in z else None
     print("YEAR",y,"ROWS",len(z),"RACES",races,"HORSES",horses)
 if "available" in d:print("AVAILABLE",d.available.value_counts(dropna=False).head(10).to_dict())
 for c in ["provider","price_type","decision_timepoint","price_age_bucket","bookmaker","potentially_executable","commission_known","historical_snapshot","provenance_level"]:
  if c in d:print("VALUES",c,d[c].value_counts(dropna=False).head(20).to_dict())
 for c in ["decimal_price","latest_safe_price","price_10m","price_30m","price_60m"]:
  if c in d:print("PRICE_COVERAGE",c,float(pd.to_numeric(d[c],errors="coerce").notna().mean()))
print("D57_EXECUTABLE_PRICE_AUDIT_COMPLETE")
