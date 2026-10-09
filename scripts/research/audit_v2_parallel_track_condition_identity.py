"""Read-only exact-key audit for PL001/PL002 track-condition authorities. No fit/outcomes/prices."""
from pathlib import Path
import pandas as pd
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research")
U=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage004\V2_CERTIFIED_SINGLE_WINNER_UNIVERSE.csv")
SOURCES=[ROOT/"parallel_lane_001"/"PL001_ENRICHED_LOCAL_UNIVERSE_2021_2024.csv",ROOT/"parallel_lane_002"/"PL002_ENRICHED_LOCAL_UNIVERSE_2021_2024.csv"]
KEY=["canonical_race_id","canonical_horse_id"]
print("CONTRACT PL_TRACK_IDENTITY_AUDIT READ_ONLY NO_MODEL NO_MARKET SEALED_2025_2026")
u=pd.read_csv(U,usecols=lambda c:c in set(KEY+["_race","_horse","race_date"]),low_memory=False)
for canonical,alias in zip(KEY,["_race","_horse"]):
 if canonical not in u and alias in u:u[canonical]=u[alias]
if not set(KEY+["race_date"]).issubset(u):raise SystemExit("STOP missing V2 keys/date")
u=u[u.race_date.astype(str).str[:4].isin(["2021","2022","2023","2024"])].copy()
for k in KEY:u[k]=u[k].astype("string").str.strip()
u["race_date"]=pd.to_datetime(u.race_date,errors="coerce").dt.strftime("%Y-%m-%d")
print("V2_N",len(u),"V2_DUP",int(u.duplicated(KEY).sum()))
if u.duplicated(KEY).any():raise SystemExit("STOP V2 duplicate race/horse keys")
for p in SOURCES:
 print("SOURCE",p)
 if not p.is_file():print("STOP SOURCE_MISSING");continue
 cols=pd.read_csv(p,nrows=0).columns.tolist()
 print("COLUMNS",",".join(cols))
 if not set(KEY+["track_condition"]).issubset(cols):
  print("STOP REQUIRED_COLUMNS_MISSING");continue
 use=KEY+["track_condition"]+(["race_date"] if "race_date" in cols else [])
 a=pd.read_csv(p,usecols=use,low_memory=False)
 for k in KEY:a[k]=a[k].astype("string").str.strip()
 print("SOURCE_N",len(a),"DUP_EXACT_KEY",int(a.duplicated(KEY).sum()))
 if a.duplicated(KEY).any():
  print("STOP AMBIGUOUS_SOURCE_IDENTITY");continue
 a["track_condition"]=a.track_condition.astype("string").str.strip()
 a.loc[a.track_condition.eq(""),"track_condition"]=pd.NA
 m=u.merge(a,on=KEY,how="left",indicator=True,validate="one_to_one",suffixes=("","_source"))
 matched=m["_merge"].eq("both")
 covered=matched & m.track_condition.notna()
 if "race_date_source" in m:
  source_date=pd.to_datetime(m.race_date_source,errors="coerce").dt.strftime("%Y-%m-%d")
  mismatched=matched & source_date.ne(m.race_date).fillna(True)
  print("MATCHED_DATE_MISMATCH",int(mismatched.sum()))
  if mismatched.any():print("STOP DATE_MISMATCH");continue
 print("EXACT_MATCH",int(matched.sum()),"N",len(m),"RATE",round(float(matched.mean()),6))
 print("TRACK_CONDITION_NON_NULL",int(covered.sum()),"RATE",round(float(covered.mean()),6))
 for year,g in m.groupby(m.race_date.str[:4],sort=True):
  hit=g["_merge"].eq("both");cov=hit & g.track_condition.notna()
  print("YEAR",year,"N",len(g),"EXACT_MATCH",int(hit.sum()),"TRACK_NON_NULL",int(cov.sum()),"COVERAGE",round(float(cov.mean()),6))
 print("COVERAGE_GATE", "PASS_90_PERCENT" if covered.mean()>=.90 else "FAIL_BELOW_90_PERCENT")
 print("PIT_GATE NOT_CERTIFIED — pre-race authority timestamps not established")
print("AUDIT_COMPLETE NO_TRAINING_AUTHORISED")
