from pathlib import Path
import pandas as pd,numpy as np
from scipy.special import expit
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
P=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\d45\D45_FROZEN_PIT_FEATURE_MATRIX.csv")
d=pd.read_csv(P);d["date"]=pd.to_datetime(d.race_date);d["year_eval"]=d.date.dt.year
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone","year","year_eval"}
num=[c for c in d if c not in meta and pd.api.types.is_numeric_dtype(d[c])]
context={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"}
F=[c for c in num if c not in context]
print("D52_MARGIN_SOFTMAX_START FEATURES",len(F))
for yr in [2022,2023,2024]:
 tr=d.year_eval<yr;te=d.year_eval.eq(yr)
 for name,leaf in [("L5",5),("L7",7)]:
  m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=leaf,l2_regularization=1,random_state=42))
  m.fit(d.loc[tr,F],d.loc[tr,"y"])
  margin=m.decision_function(d.loc[te,F]);bp=expit(margin)
  base=d.loc[te,["_race","y"]].copy()
  for method,val in [("BIN_NORM",bp),("MARGIN_SM_T1",margin)]:
   q=base.copy();q["v"]=val
   if method=="BIN_NORM":q["p"]=q.v/q.groupby("_race").v.transform("sum")
   else:q["p"]=q.groupby("_race").v.transform(lambda x:np.exp(x-x.max())/np.exp(x-x.max()).sum())
   q["rank"]=q.groupby("_race").v.rank(ascending=False,method="first");w=q[q.y.eq(1)]
   print("RESULT",yr,name,method,"TOP1",float((w["rank"]<=1).mean()),"MRR",float((1/w["rank"]).mean()),"LL",float(-np.log(w.p.clip(1e-12,1)).mean()))
print("D52_MARGIN_SOFTMAX_COMPLETE")
