from pathlib import Path
import pandas as pd,numpy as np,math,json
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");O=R/"outputs/research/profitability_program/lab245b"
A=pd.read_csv(R/"outputs/research/model_price_diagnostics/lab231/LAB231_HISTORICAL_PERFORMANCE_FEATURES.csv",low_memory=False)
B=pd.read_csv(O/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv",low_memory=False)
bf=["hist_runs","current_distance","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_std5","margin_worst5","finishpos_mean5","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best"]
rf=[c for c in A.columns if c.startswith("h231_")]
X=A.merge(B[["_race","_horse"]+bf],on=["_race","_horse"],how="inner");X["y"]=pd.to_numeric(X["_y"],errors="coerce").fillna(0).astype(int)
def mk(seed):return make_pipeline(SimpleImputer(strategy="median",add_indicator=True),HistGradientBoostingClassifier(max_iter=350,learning_rate=.035,max_leaf_nodes=15,min_samples_leaf=30,l2_regularization=10,random_state=seed))
def met(z):
 a=[]
 for _,g in z.groupby("_race",sort=False):
  w=np.flatnonzero(g.y.to_numpy()==1)
  if len(w)!=1:continue
  s=g.s.to_numpy(float);p=np.clip(s,1e-12,None);p/=p.sum();rk=int(pd.Series(s).rank(ascending=False,method="first").iloc[w[0]])
  a.append((rk,-math.log(max(p[w[0]],1e-12))))
 a=np.asarray(a,float);return len(a),np.mean(a[:,0]<=1),np.mean(a[:,0]<=2),np.mean(a[:,0]<=3),np.mean(1/a[:,0]),np.mean(a[:,1])
rows=[]
for yr in [2022,2023,2024]:
 tr=X[X._year<yr];te=X[X._year==yr]
 for name,ff,seed in [("COMPACT17",bf,2601),("RICH111",rf,2602)]:
  m=mk(seed);m.fit(tr[ff],tr.y);z=te[["_race","y"]].copy();z["s"]=m.predict_proba(te[ff])[:,1]
  rows.append([yr,name,*met(z)])
out=pd.DataFrame(rows,columns=["year","model","races","top1","top2","top3","mrr","race_log_loss"]);print(out.to_string(index=False))
dev=out[out.year.isin([2022,2023])].groupby("model").mean(numeric_only=True).drop(columns=["year","races"]).sort_values("top1",ascending=False);print("\nDEV\n"+dev.to_string())
aud={"contract":"LAB245D13_APPLES_TO_APPLES_V1","same_runner_intersection":len(X),"same_races":int(X._race.nunique()),"selection_years":[2022,2023],"2024_role":"OBSERVED_DIAGNOSTIC_ONLY","2025_2026_opened":False,"dev":dev.reset_index().to_dict("records")}
(O/"LAB245D13_APPLES_TO_APPLES.csv").write_text(out.to_csv(index=False));(O/"LAB245D13_APPLES_TO_APPLES.json").write_text(json.dumps(aud,indent=2));print(json.dumps(aud,indent=2))
