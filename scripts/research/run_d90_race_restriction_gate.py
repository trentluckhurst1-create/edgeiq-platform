from pathlib import Path
import pandas as pd
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM");D=R/"outputs"/"research"/"profitability_program"/"d45"/"D45_FROZEN_PIT_FEATURE_MATRIX.csv";P=ROOT/"public"/"data"/"edgeiq_historical_performance_rating_v6_1_research.csv"
d=pd.read_csv(D,usecols=["_race","_horse","race_date"]);d["date"]=pd.to_datetime(d.race_date)
h=pd.read_csv(P,usecols=["race_date","canonical_horse_id","race_type_recovered","age_restriction_recovered","sex_restriction_recovered","race_name","race_class_clean"]);h["date"]=pd.to_datetime(h.race_date)
print("D90_CONTRACT RACE_RESTRICTION_OVERLAP_GATE NO_MODEL")
for y in [2022,2023,2024]:
 a=d[d.date.dt.year.eq(y)];b=h[h.date.dt.year.eq(y)]
 m=a.merge(b,left_on=["date","_horse"],right_on=["date","canonical_horse_id"],how="left")
 print("D90_YEAR",y,"RUNNERS",len(a),"MATCH",int(m.canonical_horse_id.notna().sum()))
 for c in ["race_type_recovered","age_restriction_recovered","sex_restriction_recovered"]:
  print("D90_FIELD",y,c,"COV",float(m[c].notna().mean()),"UNIQUE",int(m[c].nunique(dropna=True)),"TOP",m[c].value_counts(dropna=False).head(12).to_dict())
print("D90_COMPLETE")
