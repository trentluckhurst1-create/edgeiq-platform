"""Read-only source coverage inventory for original jockey/trainer, prep and running-style authorities.
No fitting, outcome columns, prices or 2025-26 data. Prints exact join coverage and feature non-null counts.
"""
from pathlib import Path
import csv,re
import pandas as pd
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research")
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research")
U=R/"model_v2"/"stage004"/"V2_CERTIFIED_SINGLE_WINNER_UNIVERSE.csv"
KEY=["canonical_race_id","canonical_horse_id","race_date"]
FAMILY=re.compile(r"jockey|trainer|(^|_)(prep|spell|run.style|settle|pace|leader|onpace|backmarker|first.up|second.up|third.up|runs.last|days.since|gear)(_|$)",re.I)
EXCLUDE=re.compile(r"market|odds|price|bsp|starting.price|result|outcome|epi|prediction|scored|holdout|2025|2026",re.I)
def schema(p):
 try:
  with p.open(encoding="utf-8-sig",newline="") as f:return next(csv.reader(f))
 except (OSError,UnicodeError,StopIteration,csv.Error):return []
print("CONTRACT ORIGINAL_AUTHORITY_COVERAGE READ_ONLY NO_FIT NO_MARKET SEALED_2025_2026")
u=pd.read_csv(U,usecols=lambda c:c in KEY+["_race","_horse"],low_memory=False)
for k,alias in zip(KEY[:2],["_race","_horse"]):
 if k not in u:u[k]=u[alias]
u["race_date"]=pd.to_datetime(u.race_date,errors="coerce").dt.strftime("%Y-%m-%d")
u=u[u.race_date.str[:4].isin(["2021","2022","2023","2024"])][KEY].copy()
for k in KEY[:2]:u[k]=u[k].astype("string").str.strip()
print("V2_ROWS",len(u),"DUP_KEYS",int(u.duplicated(KEY).sum()))
if u.duplicated(KEY).any():raise SystemExit("STOP V2 DUPLICATES")
candidates=[]
for root in [R,P]:
 if not root.exists():continue
 for p in root.rglob("*.csv"):
  if EXCLUDE.search(str(p)):continue
  cols=schema(p)
  fs=[c for c in cols if FAMILY.search(c) and not EXCLUDE.search(c) and c not in KEY]
  if not fs:continue
  hid="canonical_horse_id" if "canonical_horse_id" in cols else ("horse_id" if "horse_id" in cols else None)
  rid="canonical_race_id" if "canonical_race_id" in cols else ("_race" if "_race" in cols else None)
  if hid and rid and "race_date" in cols:
   candidates.append((p,rid,hid,fs))
print("CANDIDATES",len(candidates))
# Do not read every giant source: only known authorities and first 30 source paths by alphabetical order.
priority=[t for t in candidates if any(x in str(t[0]).lower() for x in ["model_lab_037","model_lab_089","model_lab_031","model_lab_080","parallel_lane_"])]
others=[t for t in candidates if t not in priority]
chosen=(priority+others)[:40]
print("AUDITED",len(chosen),"PRIORITY",len(priority))
for p,rid,hid,fs in chosen:
 print("SOURCE",p,"FEATURES",",".join(fs[:15]))
 try:
  use=list(dict.fromkeys([rid,hid,"race_date"]+fs[:15]))
  a=pd.read_csv(p,usecols=use,low_memory=False).rename(columns={rid:KEY[0],hid:KEY[1]})
  a["race_date"]=pd.to_datetime(a.race_date,errors="coerce").dt.strftime("%Y-%m-%d")
  a=a[a.race_date.str[:4].isin(["2021","2022","2023","2024"])]
  for k in KEY[:2]:a[k]=a[k].astype("string").str.strip()
  dup=int(a.duplicated(KEY).sum())
  print("AUTH_ROWS",len(a),"DUP_KEYS",dup)
  if dup:print("GATE STOP_DUPLICATE_IDENTITY");continue
  m=u.merge(a,on=KEY,how="left",indicator=True,validate="one_to_one")
  match=m["_merge"].eq("both")
  print("MATCH",int(match.sum()),"N",len(m),"RATE",round(float(match.mean()),6))
  for f in fs[:15]:
   cov=m[f].notna()
   print("FEATURE",f,"NONNULL",int(cov.sum()),"RATE",round(float(cov.mean()),6))
  print("IDENTITY_GATE","PASS_90" if match.mean()>=.90 else "FAIL_90")
 except Exception as e:print("SOURCE_ERROR",type(e).__name__,str(e)[:220])
print("PIT_STATUS NOT_CERTIFIED; PREVIOUSLY_FITTED_STATUS NOT_CERTIFIED")
print("COMPLETE NO_TRAINING_AUTHORISED")
