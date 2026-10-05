from pathlib import Path
import pandas as pd,numpy as np,math,json
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH");D=R/"outputs/research/profitability_program/lab245b";P=R/"outputs/research/model_price_diagnostics/lab231/LAB231_HISTORICAL_PERFORMANCE_FEATURES.csv"
def met(z):
 a=[]
 for _,g in z.groupby("_race",sort=False):
  w=np.flatnonzero(g.y.to_numpy()==1)
  if len(w)!=1:continue
  s=g.s.to_numpy(float);p=np.clip(s,1e-12,None);p/=p.sum();rk=int(pd.Series(s).rank(ascending=False,method="first").iloc[w[0]])
  a.append((rk,-math.log(max(p[w[0]],1e-12))))
 a=np.asarray(a,float);return len(a),np.mean(a[:,0]<=1),np.mean(a[:,0]<=2),np.mean(a[:,0]<=3),np.mean(1/a[:,0]),np.mean(a[:,1])
def mk(seed,leaf=15,ml=30,l2=10):return make_pipeline(SimpleImputer(strategy="median",add_indicator=True),HistGradientBoostingClassifier(max_iter=350,learning_rate=.035,max_leaf_nodes=leaf,min_samples_leaf=ml,l2_regularization=l2,random_state=seed))
def main():
 d=pd.read_csv(P,low_memory=False);d=d[d._year.between(2021,2024)].copy();d["y"]=pd.to_numeric(d["_y"],errors="coerce").fillna(0).astype(int)
 feats=[c for c in d.columns if c.startswith("h231_")]
 raw=[c for c in feats if not c.endswith("_rank_pct") and not c.endswith("_z")]
 rank=[c for c in feats if c.endswith("_rank_pct")]
 families={"RAW":raw,"RAW_RANK":raw+rank,"ALL115":feats}
 rows=[]
 for yr in [2022,2023,2024]:
  tr=d[d._year<yr];te=d[d._year==yr]
  for i,(name,ff) in enumerate(families.items()):
   m=mk(2511+i);m.fit(tr[ff],tr.y);z=te[["_race","y"]].copy();z["s"]=m.predict_proba(te[ff])[:,1]
   n,t1,t2,t3,mrr,ll=met(z);rows.append([yr,name,len(ff),n,t1,t2,t3,mrr,ll])
 out=pd.DataFrame(rows,columns=["year","model","features","races","top1","top2","top3","mrr","race_log_loss"]);out.to_csv(D/"LAB245D11_LAB231_RICH_HGB.csv",index=False)
 dev=out[out.year.isin([2022,2023])].groupby("model").mean(numeric_only=True).drop(columns=["year","features","races"]).sort_values(["top1","mrr"],ascending=False)
 aud={"contract":"LAB245D11_LAB231_RICH_HGB_V1","source":"LAB231_HISTORICAL_PERFORMANCE_FEATURES.csv","selection_years":[2022,2023],"2024_role":"OBSERVED_DIAGNOSTIC_ONLY","2025_2026_opened":False,"market_used":False,"feature_counts":{k:len(v) for k,v in families.items()},"dev":dev.reset_index().to_dict("records")}
 (D/"LAB245D11_LAB231_RICH_HGB.json").write_text(json.dumps(aud,indent=2));print(out.to_string(index=False));print("\nDEV\n"+dev.to_string());print("\n"+json.dumps(aud,indent=2))
if __name__=="__main__":main()
