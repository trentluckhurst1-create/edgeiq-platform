from pathlib import Path
import pandas as pd
from pathlib import Path
import os,re
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research")
print("V2_STAGE022A_CONTRACT DENSE_UNTOUCHED_FAMILY_AUTHORITY_INVENTORY NO_MODEL NO_MARKET 2025_2026_SEALED")
terms=["age","sex","gender","class","prize","prizemoney","track_condition","going","surface"]
hits=[]
for p in ROOT.rglob("*.csv"):
 s=str(p).lower()
 if any(t in s for t in terms):
  try:
   cols=list(pd.read_csv(p,nrows=2).columns)
  except Exception:
   continue
  relevant=[c for c in cols if any(t in c.lower() for t in terms)]
  keys=[c for c in cols if c in ["canonical_race_id","canonical_horse_id","horse_id","race_date","race_id"]]
  if relevant and ("race_date" in cols) and any(c in cols for c in ["canonical_horse_id","horse_id"]):
   hits.append((str(p),len(cols),keys,relevant[:30]))
print("V2_STAGE022A_HITS",len(hits))
for p,n,k,r in hits[:150]:
 print("V2_STAGE022A_FILE",p,"NCOLS",n,"KEYS","|".join(k),"FIELDS","|".join(r))
print("V2_STAGE022A_COMPLETE")
