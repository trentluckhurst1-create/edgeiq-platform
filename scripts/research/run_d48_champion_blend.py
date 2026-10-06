from pathlib import Path
import pandas as pd,numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
P=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\d45\D45_FROZEN_PIT_FEATURE_MATRIX.csv")
d=pd.read_csv(P);d["date"]=pd.to_datetime(d.race_date);d["year"]=d.date.dt.year
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone"}
num=[c for c in d if c not in meta and pd.api.types.is_numeric_dtype(d[c])]
context={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"}
F=[c for c in num if c not in context]
cfg={"L5":(5,1,.05,200),"L7":(7,1,.05,200),"L5SLOW":(5,5,.03,350)}
print("D48_BLEND_START")
for yr in [2022,2023,2024]:
 tr=d.year<yr;te=d.year.eq(yr);pred={}
 for n,(leaf,reg,lr,it) in cfg.items():
  m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=it,learning_rate=lr,max_leaf_nodes=leaf,l2_regularization=reg,random_state=42));m.fit(d.loc[tr,F],d.loc[tr,"y"]);pred[n]=m.predict_proba(d.loc[te,F])[:,1]
 variants={"L5":pred["L5"],"L7":pred["L7"],"BLEND50":.5*pred["L5"]+.5*pred["L7"],"BLEND67_L5":.67*pred["L5"]+.33*pred["L7"],"BLEND3":(.4*pred["L5"]+.4*pred["L7"]+.2*pred["L5SLOW"])}
 for n,p in variants.items():
  q=d.loc[te,["_race","y"]].copy();q["p"]=p;q["rp"]=q.p/q.groupby("_race").p.transform("sum");q["rank"]=q.groupby("_race").p.rank(ascending=False,method="first");w=q[q.y.eq(1)]
  print("RESULT",yr,n,"TOP1",float((w["rank"]<=1).mean()),"TOP2",float((w["rank"]<=2).mean()),"TOP3",float((w["rank"]<=3).mean()),"MRR",float((1/w["rank"]).mean()),"LL",float(-np.log(w["rp"].clip(1e-12,1)).mean()))
print("D48_BLEND_COMPLETE")
