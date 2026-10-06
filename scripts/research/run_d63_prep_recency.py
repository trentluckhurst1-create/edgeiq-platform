from pathlib import Path
import pandas as pd,numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
D=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\d45\D45_FROZEN_PIT_FEATURE_MATRIX.csv")
B=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv")
d=pd.read_csv(D);b=pd.read_csv(B)
bridge_prep=["last_distance","last_finish","last_won","last_top3"]
z=d.merge(b[["_race","_horse"]+bridge_prep],on=["_race","_horse"],how="left",validate="one_to_one")
z["distance_change"]=z["current_distance"]-z["last_distance"]
z["abs_distance_change"]=z["distance_change"].abs()
prep=["days_since_last","distance_change","abs_distance_change","last_finish","last_won","last_top3"]
z["date"]=pd.to_datetime(z.race_date);z["year_eval"]=z.date.dt.year
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone","year","year_eval"}
num=[c for c in d.columns if c not in meta and pd.api.types.is_numeric_dtype(d[c])]
context={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"}
base=[c for c in num if c not in context]
print("D63_CONTRACT PREP_RECENCY_ONLY_NAMESPACE_FIXED BASE",len(base),"PLUS",len(base)+len(prep))
print("D63_COVERAGE",{c:float(z[c].notna().mean()) for c in prep})
for yr in [2022,2023,2024]:
 tr=z.year_eval<yr;te=z.year_eval.eq(yr)
 for name,F in [("BASE",base),("PREP",base+prep)]:
  m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42))
  m.fit(z.loc[tr,F],z.loc[tr,"y"]);sc=m.decision_function(z.loc[te,F])
  q=z.loc[te,["_race","y"]].copy();q["s"]=sc
  q["p"]=q.groupby("_race").s.transform(lambda x:np.exp(x-x.max())/np.exp(x-x.max()).sum())
  q["rank"]=q.groupby("_race").s.rank(ascending=False,method="first");w=q[q.y.eq(1)]
  print("D63_RESULT",yr,name,"RACES",len(w),"TOP1",float((w["rank"]==1).mean()),"TOP2",float((w["rank"]<=2).mean()),"TOP3",float((w["rank"]<=3).mean()),"MRR",float((1/w["rank"]).mean()),"LL",float(-np.log(w.p.clip(1e-12,1)).mean()))
print("D63_COMPLETE")
print("D63_CONTRACT_VERSION PREP_RECENCY_V1_NAMESPACE_FIX_MERGE_FIX")
