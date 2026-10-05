from pathlib import Path
import pandas as pd,numpy as np,math,json
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");O=R/"outputs/research/profitability_program/lab245b";P=R/"outputs/research/model_price_diagnostics/lab231/LAB231_HISTORICAL_PERFORMANCE_FEATURES.csv"
d=pd.read_csv(P,low_memory=False);d=d[d._year.between(2021,2024)].copy();d["y"]=pd.to_numeric(d["_y"],errors="coerce").fillna(0).astype(int)
raw=[c for c in d if c.startswith("h231_") and not c.endswith("_rank_pct") and not c.endswith("_z")]
rank=[c for c in d if c.endswith("_rank_pct") and c.startswith("h231_")];z=[c for c in d if c.endswith("_z") and c.startswith("h231_")]
def pick(words): return [c for c in raw if any(w in c for w in words)]
recent=pick(["last1","last3","last5","margin","finishpos","days_since_last_perf"])
longpeak=pick(["last10","peak","near_peak","recent_above"])
context=pick(["dist200","same_class","same_condition"])
hist=pick(["hist_perf_runs"])
families={"RECENT":list(dict.fromkeys(hist+recent)),"RECENT_LONGPEAK":list(dict.fromkeys(hist+recent+longpeak)),"RECENT_CONTEXT":list(dict.fromkeys(hist+recent+context)),"RAW37":raw,"RAW_PLUS_RANK":raw+rank,"ALL111":raw+rank+z}
def mk(seed):return make_pipeline(SimpleImputer(strategy="median",add_indicator=True),HistGradientBoostingClassifier(max_iter=350,learning_rate=.035,max_leaf_nodes=15,min_samples_leaf=30,l2_regularization=10,random_state=seed))
def met(z0):
 a=[]
 for _,g in z0.groupby("_race",sort=False):
  w=np.flatnonzero(g.y.to_numpy()==1)
  if len(w)!=1:continue
  s=g.s.to_numpy(float);p=np.clip(s,1e-12,None);p/=p.sum();rk=int(pd.Series(s).rank(ascending=False,method="first").iloc[w[0]])
  a.append((rk,-math.log(max(p[w[0]],1e-12))))
 a=np.asarray(a,float);return len(a),np.mean(a[:,0]<=1),np.mean(a[:,0]<=2),np.mean(a[:,0]<=3),np.mean(1/a[:,0]),np.mean(a[:,1])
rows=[]
for yr in [2022,2023,2024]:
 tr=d[d._year<yr];te=d[d._year==yr]
 for i,(name,ff) in enumerate(families.items()):
  m=mk(2700+i);m.fit(tr[ff],tr.y);q=te[["_race","y"]].copy();q["s"]=m.predict_proba(te[ff])[:,1];rows.append([yr,name,len(ff),*met(q)])
out=pd.DataFrame(rows,columns=["year","model","features","races","top1","top2","top3","mrr","race_log_loss"]);print(out.to_string(index=False))
dev=out[out.year.isin([2022,2023])].groupby("model").mean(numeric_only=True).drop(columns=["year","features","races"]).sort_values(["top1","race_log_loss"],ascending=[False,True]);print("\nDEV\n"+dev.to_string())
aud={"contract":"LAB245D14_RICH_FEATURE_BLOCKS_V1","families":families,"selection_years":[2022,2023],"2024_role":"OBSERVED_DIAGNOSTIC_ONLY","2025_2026_opened":False,"dev":dev.reset_index().to_dict("records")}
out.to_csv(O/"LAB245D14_RICH_FEATURE_BLOCKS.csv",index=False);(O/"LAB245D14_RICH_FEATURE_BLOCKS.json").write_text(json.dumps(aud,indent=2));print(json.dumps(aud,indent=2))
