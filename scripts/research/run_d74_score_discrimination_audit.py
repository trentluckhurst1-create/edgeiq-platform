from pathlib import Path
import pandas as pd,numpy as np
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_026\edgeiq_certified_flat_walk_forward_epi_026.csv")
print("D100_CONTRACT PERF026_NUMERIC_SEMANTIC_SANITY_AUDIT NO_MODEL NO_OUTCOME_SELECTION")
h=pd.read_csv(P,nrows=0);cols=list(h.columns);cand=[c for c in cols if any(k in c.lower() for k in ["finish","margin","field","barrier","weight","distance","time","position","rank","starts","wins","top3"])]
print("D100_CANDIDATES",cand)
use=["race_date"]+cand
d=pd.read_csv(P,usecols=use,low_memory=False);d["date"]=pd.to_datetime(d.race_date,errors="coerce")
for c in cand:
 v=pd.to_numeric(d[c],errors="coerce")
 if not v.notna().any():continue
 q=v.quantile([0,.01,.5,.99,1]).to_dict()
 print("D100_FIELD",c,"COV",float(v.notna().mean()),"Q",q,"NEG",int((v<0).sum()),"GT99",int((v>99).sum()))
print("D100_COMPLETE")
