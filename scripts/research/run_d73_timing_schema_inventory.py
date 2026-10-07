from pathlib import Path
import pandas as pd
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_026\edgeiq_certified_flat_walk_forward_epi_026.csv")
cols=list(pd.read_csv(P,nrows=0).columns)
keys=("section","split","speed","time","pace","position","benchmark","rating","last600","last400","last200","early","late")
cand=[c for c in cols if any(k in c.lower().replace("_","") for k in keys)]
print("D73_TIMING_SCHEMA_INVENTORY")
print("TOTAL_COLUMNS",len(cols))
print("CANDIDATE_COLUMNS",cand)
if cand:
 d=pd.read_csv(P,usecols=cand,low_memory=False)
 for c in cand:
  s=d[c]
  print("D73_FIELD",c,"NON_NULL",float(s.notna().mean()),"NUNIQUE",int(s.nunique(dropna=True)),"SAMPLE",s.dropna().astype(str).head(5).tolist())
print("D73_COMPLETE NO_MODEL_RUN")
