from pathlib import Path
import pandas as pd,numpy as np
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_026\edgeiq_certified_flat_walk_forward_epi_026.csv")
print("D97_CONTRACT FINISH_POSITION_SEMANTIC_AUDIT NO_MODEL")
d=pd.read_csv(P,usecols=["race_date","finish_position","field_size","canonical_race_id"],low_memory=False);d["date"]=pd.to_datetime(d.race_date);d["fp"]=pd.to_numeric(d.finish_position,errors="coerce");d["fs"]=pd.to_numeric(d.field_size,errors="coerce")
for y in [2020,2021,2022,2023,2024]:
 q=d[d.date.dt.year.eq(y)];v=q.fp.dropna();bad=q.fp>q.fs
 print("D97_YEAR",y,"ROWS",len(q),"FP_COV",float(q.fp.notna().mean()),"FP_Q",v.quantile([0,.25,.5,.75,.9,.99,1]).to_dict(),"FIELD_MED",float(q.fs.median()),"FP_GT_FIELD",int(bad.sum()),"RATE",float(bad.mean()))
 print("D97_TOP_FP",q.fp.value_counts().head(20).to_dict())
print("D97_COMPLETE")
