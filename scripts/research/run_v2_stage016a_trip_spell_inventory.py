from pathlib import Path
import pandas as pd,re
W=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage006\V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv")
print("V2_STAGE016A_CONTRACT TRIP_SPELL_CLASS_WEIGHT_INVENTORY NO_MODEL NO_MARKET 2025_2026_SEALED")
d=pd.read_csv(W,nrows=5)
pat=re.compile(r"(distance|days_since|spell|weight|class|grade|benchmark|rating|handicap|carried)",re.I)
for c in d.columns:
 if pat.search(c): print("V2_STAGE016A_WAREHOUSE_FIELD",c)
# Search small schemas/files in production for candidate exact authorities.
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
hits=[]
for base in [ROOT/"outputs"/"research",ROOT/"docs"/"performance-intelligence"]:
 if not base.exists(): continue
 for p in base.rglob("*.csv"):
  try:
   if p.stat().st_size>250_000_000: continue
   cols=list(pd.read_csv(p,nrows=0).columns)
  except: continue
  cand=[c for c in cols if pat.search(c)]
  keys=[c for c in cols if c.lower() in {"canonical_race_id","canonical_horse_id","race_date","race_date_model","_race","_horse"}]
  if cand and len(keys)>=2:
   hits.append((str(p),keys,cand))
for p,k,c in hits[:80]:
 print("V2_STAGE016A_AUTH",p,"KEYS","|".join(k),"FIELDS","|".join(c[:30]))
print("V2_STAGE016A_AUTHORITIES",len(hits))
print("V2_STAGE016A_COMPLETE")
