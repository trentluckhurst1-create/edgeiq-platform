from pathlib import Path
import pandas as pd,numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
P=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\d45\D45_FROZEN_PIT_FEATURE_MATRIX.csv")
d=pd.read_csv(P);d["date"]=pd.to_datetime(d["race_date"]);d["year"]=d.date.dt.year
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone"}
num=[c for c in d.columns if c not in meta and pd.api.types.is_numeric_dtype(d[c])]
context={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"}
F=[c for c in num if c not in context]
grid=[
("L5_R1_LR05_I200",5,1,.05,200),("L7_R1_LR05_I200",7,1,.05,200),("L7_R2_LR04_I250",7,2,.04,250),
("L7_R5_LR04_I250",7,5,.04,250),("L7_R10_LR04_I250",7,10,.04,250),("L9_R2_LR04_I250",9,2,.04,250),
("L11_R2_LR04_I250",11,2,.04,250),("L7_R2_LR03_I350",7,2,.03,350),("L7_R5_LR03_I350",7,5,.03,350),
("L5_R5_LR03_I350",5,5,.03,350),("L9_R5_LR03_I350",9,5,.03,350),("L7_R10_LR03_I350",7,10,.03,350)]
print("D47_TARGETED_HGB_START","FEATURES",len(F),"CONFIGS",len(grid))
for yr in [2022,2023,2024]:
 tr=d.year<yr;te=d.year.eq(yr)
 for name,leaf,reg,lr,it in grid:
  m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=it,learning_rate=lr,max_leaf_nodes=leaf,l2_regularization=reg,random_state=42))
  m.fit(d.loc[tr,F],d.loc[tr,"y"]);p=m.predict_proba(d.loc[te,F])[:,1]
  q=d.loc[te,["_race","y"]].copy();q["p"]=p;q["rp"]=q.p/q.groupby("_race").p.transform("sum");q["rank"]=q.groupby("_race").p.rank(ascending=False,method="first");w=q[q.y.eq(1)]
  print("RESULT",yr,name,"RACES",len(w),"TOP1",float((w["rank"]<=1).mean()),"TOP2",float((w["rank"]<=2).mean()),"TOP3",float((w["rank"]<=3).mean()),"MRR",float((1/w["rank"]).mean()),"LL",float(-np.log(w["rp"].clip(1e-12,1)).mean()))
print("D47_TARGETED_HGB_COMPLETE")
