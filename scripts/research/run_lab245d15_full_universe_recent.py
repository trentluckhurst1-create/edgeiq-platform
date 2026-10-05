from pathlib import Path
import pandas as pd,numpy as np,math,json
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");O=R/"outputs/research/profitability_program/lab245b";P=O/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
d=pd.read_csv(P,low_memory=False);d=d[d._year.between(2021,2024)&d.target_lvs.notna()].copy()
base=["hist_runs","current_distance","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_std5","margin_worst5","finishpos_mean5","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best"]
# Governed bridge already supplies PIT-safe recent summaries. Derive only algebraic trajectory features from those summaries.
d["log_hist"]=np.log1p(pd.to_numeric(d.hist_runs,errors="coerce").fillna(0))
d["last1_minus_peak"]=d.lvs_last1-d.lvs_peak
d["last1_minus_mean5"]=d.lvs_last1-d.lvs_mean5
d["peak_minus_mean5"]=d.lvs_peak-d.lvs_mean5
d["dist_best_minus_peak"]=d.dist200_lvs_best-d.lvs_peak
d["recent_consistency"]=d.lvs_mean5-d.lvs_std5
d["margin_stability"]=d.margin_mean5-d.margin_std5
d["has_dist200"]=(pd.to_numeric(d.dist200_runs,errors="coerce").fillna(0)>0).astype(int)
derived=["log_hist","last1_minus_peak","last1_minus_mean5","peak_minus_mean5","dist_best_minus_peak","recent_consistency","margin_stability","has_dist200"]
rich=base+derived
def mk(seed):return make_pipeline(SimpleImputer(strategy="median",add_indicator=True),HistGradientBoostingClassifier(max_iter=350,learning_rate=.035,max_leaf_nodes=15,min_samples_leaf=30,l2_regularization=10,random_state=seed))
def met(z):
 a=[]
 for _,g in z.groupby("_race",sort=False):
  w=np.flatnonzero(g.y.to_numpy()==1)
  if len(w)!=1:continue
  s=g.s.to_numpy(float);p=np.clip(s,1e-12,None);p/=p.sum();rk=int(pd.Series(s).rank(ascending=False,method="first").iloc[w[0]])
  a.append((rk,-math.log(max(p[w[0]],1e-12))))
 a=np.asarray(a,float);return len(a),np.mean(a[:,0]<=1),np.mean(a[:,0]<=2),np.mean(a[:,0]<=3),np.mean(1/a[:,0]),np.mean(a[:,1])
d["y"]=(pd.to_numeric(d.target_finish_position,errors="coerce")==1).astype(int);rows=[]
for yr in [2022,2023,2024]:
 tr=d[d._year<yr];te=d[d._year==yr]
 for i,(name,ff) in enumerate([("BASE17",base),("FULL_RECENT25",rich)]):
  m=mk(2800+i);m.fit(tr[ff],tr.y);q=te[["_race","y"]].copy();q["s"]=m.predict_proba(te[ff])[:,1];rows.append([yr,name,len(ff),*met(q)])
out=pd.DataFrame(rows,columns=["year","model","features","races","top1","top2","top3","mrr","race_log_loss"]);print(out.to_string(index=False))
dev=out[out.year.isin([2022,2023])].groupby("model").mean(numeric_only=True).drop(columns=["year","features","races"]).sort_values(["top1","race_log_loss"],ascending=[False,True]);print("\nDEV\n"+dev.to_string())
aud={"contract":"LAB245D15_FULL_UNIVERSE_RECENT_V1","rows":len(d),"races":int(d._race.nunique()),"base_features":base,"derived_features":derived,"selection_years":[2022,2023],"2024_role":"OBSERVED_DIAGNOSTIC_ONLY","2025_2026_opened":False,"market_used":False,"dev":dev.reset_index().to_dict("records")}
out.to_csv(O/"LAB245D15_FULL_UNIVERSE_RECENT.csv",index=False);(O/"LAB245D15_FULL_UNIVERSE_RECENT.json").write_text(json.dumps(aud,indent=2));print(json.dumps(aud,indent=2))
