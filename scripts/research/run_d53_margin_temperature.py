from pathlib import Path
import pandas as pd,numpy as np
from scipy.special import expit
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
P=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\d45\D45_FROZEN_PIT_FEATURE_MATRIX.csv")
d=pd.read_csv(P);d["date"]=pd.to_datetime(d.race_date);d["eval_year"]=d.date.dt.year
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone","year","eval_year"}
num=[c for c in d if c not in meta and pd.api.types.is_numeric_dtype(d[c])]
context={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"}
F=[c for c in num if c not in context]
Ts=[0.70,0.85,1.00,1.15,1.30,1.50]
print("D53_TEMP_START",Ts)
rows=[]
for yr in [2022,2023,2024]:
 tr=d.eval_year<yr;te=d.eval_year.eq(yr)
 for name,leaf in [("L5",5),("L7",7)]:
  m=make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=leaf,l2_regularization=1,random_state=42))
  m.fit(d.loc[tr,F],d.loc[tr,"y"]);z=m.decision_function(d.loc[te,F]);q=d.loc[te,["_race","y"]].copy()
  for T in Ts:
   q["u"]=z/T;q["p"]=q.groupby("_race").u.transform(lambda x:np.exp(x-x.max())/np.exp(x-x.max()).sum());w=q[q.y.eq(1)]
   ll=float(-np.log(w.p.clip(1e-12,1)).mean());rows.append((yr,name,T,ll));print("RESULT",yr,name,"T",T,"LL",ll)
# governance: choose T by mean LL across selection years 2022+2023 only, report 2024 after choice
r=pd.DataFrame(rows,columns=["year","model","T","LL"])
for name in ["L5","L7"]:
 a=r[(r.model==name)&r.year.isin([2022,2023])].groupby("T").LL.mean().sort_values();T=float(a.index[0])
 print("SELECTED",name,"T",T,"SEL_MEAN_LL",float(a.iloc[0]),"Y2022",float(r[(r.model==name)&(r.year==2022)&(r.T==T)].LL.iloc[0]),"Y2023",float(r[(r.model==name)&(r.year==2023)&(r.T==T)].LL.iloc[0]),"Y2024_DIAG",float(r[(r.model==name)&(r.year==2024)&(r.T==T)].LL.iloc[0]))
print("D53_TEMP_COMPLETE")
