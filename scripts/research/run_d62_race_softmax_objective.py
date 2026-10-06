from pathlib import Path
import pandas as pd,numpy as np
from sklearn.impute import SimpleImputer
from sklearn.ensemble import HistGradientBoostingClassifier,HistGradientBoostingRegressor

P=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\d45\D45_FROZEN_PIT_FEATURE_MATRIX.csv")
d=pd.read_csv(P);d["date"]=pd.to_datetime(d["race_date"]);d["year_eval"]=d.date.dt.year
meta={"_race","_horse","race_date","date","y","target_finish_position","current_track_id","barrier_zone","year","year_eval"}
num=[c for c in d.columns if c not in meta and pd.api.types.is_numeric_dtype(d[c])]
context={c for c in num if c.startswith(("tb_mech_","db_mech_","tdb_mech_"))}|{"distance_band_200"}
F=[c for c in num if c not in context]
print("D62_CONTRACT RACE_SOFTMAX_NLL_ONLY FEATURES",len(F),"LR",.05,"STEPS",200,"LEAVES",5,"L2",1)

def softmax_by_race(scores,races):
 p=np.empty(len(scores),float)
 z=pd.DataFrame({"r":np.asarray(races),"s":scores,"i":np.arange(len(scores))})
 for _,g in z.groupby("r",sort=False):
  v=g.s.to_numpy();e=np.exp(v-v.max());p[g.i.to_numpy()]=e/e.sum()
 return p

def metrics(rows,scores,label):
 q=rows[["_race","y"]].copy();q["s"]=scores;q["p"]=softmax_by_race(scores,q["_race"].to_numpy())
 q["rank"]=q.groupby("_race").s.rank(ascending=False,method="first");w=q[q.y.eq(1)]
 return {"LABEL":label,"RACES":len(w),"TOP1":float((w["rank"]==1).mean()),"TOP2":float((w["rank"]<=2).mean()),"TOP3":float((w["rank"]<=3).mean()),"MRR":float((1/w["rank"]).mean()),"LL":float(-np.log(w.p.clip(1e-12,1)).mean())}

for yr in [2022,2023,2024]:
 tr=d.year_eval<yr;te=d.year_eval.eq(yr)
 imp=SimpleImputer(strategy="median");Xtr=imp.fit_transform(d.loc[tr,F]);Xte=imp.transform(d.loc[te,F]);y=d.loc[tr,"y"].to_numpy(float);r=d.loc[tr,"_race"].to_numpy()
 base=HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=5,l2_regularization=1,random_state=42)
 base.fit(Xtr,y);sb=base.decision_function(Xte)
 print("D62_RESULT",yr,metrics(d.loc[te],sb,"BASE"))
 strn=np.zeros(len(Xtr));ste=np.zeros(len(Xte))
 for k in range(200):
  p=softmax_by_race(strn,r);res=y-p
  tree=HistGradientBoostingRegressor(max_iter=1,learning_rate=1.0,max_leaf_nodes=5,l2_regularization=1,random_state=42+k)
  tree.fit(Xtr,res)
  strn += .05*tree.predict(Xtr);ste += .05*tree.predict(Xte)
 print("D62_RESULT",yr,metrics(d.loc[te],ste,"RACE_SOFTMAX"))
print("D62_COMPLETE")
