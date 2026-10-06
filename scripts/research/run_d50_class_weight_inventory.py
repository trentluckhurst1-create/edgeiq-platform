from pathlib import Path
import pandas as pd,numpy as np
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
P=ROOT/"outputs"/"research"/"model_lab_026"/"edgeiq_certified_flat_walk_forward_epi_026.csv"
cols=pd.read_csv(P,nrows=0).columns.tolist()
keys=["weight","class","rating","prize","benchmark","grade","age","sex"]
cand=[c for c in cols if any(k in c.lower() for k in keys)]
print("D50_CLASS_WEIGHT_COLUMNS",cand)
use=list(dict.fromkeys(["race_date","canonical_race_id","canonical_horse_id"]+cand))
d=pd.read_csv(P,usecols=[c for c in use if c in cols]);d["year"]=pd.to_datetime(d.race_date,errors="coerce").dt.year
for c in cand:
 v=d[c];cov=v.notna()
 print("FEATURE",c,"COVERAGE",float(cov.mean()),"NUNIQUE",int(v.nunique(dropna=True)))
 for y in [2020,2021,2022,2023,2024]:
  z=d.year.eq(y);print("YEARCOV",c,y,int(z.sum()),float(v[z].notna().mean()) if z.any() else 0)
print("D50_CLASS_WEIGHT_COMPLETE")
