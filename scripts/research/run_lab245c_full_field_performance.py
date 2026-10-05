from pathlib import Path
import json, math, hashlib
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge

ROOT=Path(__file__).resolve().parents[2]
D=ROOT/"outputs/research/profitability_program/lab245b"
INP=D/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
OUT=D/"LAB245C_FULL_FIELD_RESULTS.csv"
OOF=D/"LAB245C_FULL_FIELD_OOF.csv"
AUD=D/"LAB245C_FULL_FIELD_AUDIT.json"
F=["hist_runs","current_distance","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_worst5","margin_std5","finishpos_mean5","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best"]

def prep(x):
 x=x.copy()
 x["hist_runs"]=pd.to_numeric(x.hist_runs,errors="coerce").fillna(0)
 x["hist0"]=(x.hist_runs==0).astype(int); x["hist1"]=(x.hist_runs==1).astype(int); x["hist2"]=(x.hist_runs==2).astype(int); x["hist3p"]=(x.hist_runs>=3).astype(int)
 x["log_hist_runs"]=np.log1p(x.hist_runs)
 feats=F+["hist0","hist1","hist2","hist3p","log_hist_runs"]
 for c in feats+["target_lvs","target_finish_position","represented_field_size"]: x[c]=pd.to_numeric(x[c],errors="coerce")
 for c in F:
  v=x[c]; med=v.groupby(x["_race"]).transform("median"); x[c+"_relmed"]=v-med
 return x,feats+[c+"_relmed" for c in F]

def score(d,p):
 q=d[["_race","target_lvs","target_finish_position","represented_field_size"]].copy(); q["p"]=p
 q=q[np.isfinite(q.target_lvs)&np.isfinite(q.p)]
 mae=mean_absolute_error(q.target_lvs,q.p); rmse=math.sqrt(mean_squared_error(q.target_lvs,q.p))
 rho=[]; complete=0
 for _,g in q.groupby("_race"):
  n=int(g.represented_field_size.iloc[0])
  if len(g)!=n: continue
  complete+=1
  if len(g)>=3 and g.target_lvs.nunique()>1 and g.p.nunique()>1: rho.append(g.target_lvs.corr(g.p,method="spearman"))
 return {"rows":len(q),"races":q._race.nunique(),"complete_fields":complete,"mae":mae,"rmse":rmse,"race_spearman_mean":float(np.nanmean(rho)) if rho else np.nan}

def modelset():
 return {
 "RIDGE":make_pipeline(SimpleImputer(strategy="median",add_indicator=True),StandardScaler(),Ridge(alpha=10)),
 "HGB":HistGradientBoostingRegressor(max_iter=300,learning_rate=.035,max_leaf_nodes=15,min_samples_leaf=25,l2_regularization=10,random_state=24531),
 "EXTRATREES":make_pipeline(SimpleImputer(strategy="median",add_indicator=True),ExtraTreesRegressor(n_estimators=450,min_samples_leaf=12,max_features=.75,n_jobs=-1,random_state=24532))
 }

def main():
 d=pd.read_csv(INP,low_memory=False)
 if not d["_year"].between(2021,2024).all(): raise RuntimeError("sealed-year breach")
 d=d[d.target_lvs.notna()].copy(); d,ff=prep(d)
 rows=[]; oo=[]
 for yy in [2022,2023,2024]:
  tr=d[d._year<yy].copy(); te=d[d._year==yy].copy()
  if tr.empty or te.empty: continue
  # PIT-safe depth prior baseline: training-only mean target by history bucket.
  tr["bucket"]=pd.cut(tr.hist_runs,[-1,0,1,2,np.inf],labels=["0","1","2","3p"])
  te["bucket"]=pd.cut(te.hist_runs,[-1,0,1,2,np.inf],labels=["0","1","2","3p"])
  pri=tr.groupby("bucket",observed=True).target_lvs.mean().to_dict(); glob=float(tr.target_lvs.mean())
  bp=te.bucket.astype(str).map(pri).fillna(glob).to_numpy(float)
  rows.append({"year":yy,"model":"DEPTH_PRIOR",**score(te,bp)})
  q=te[["_race","_horse","_year","race_date","target_lvs","target_finish_position","represented_field_size","hist_runs"]].copy(); q["model"]="DEPTH_PRIOR"; q["pred_lvs"]=bp; oo.append(q)
  for name,m in modelset().items():
   m.fit(tr[ff],tr.target_lvs); p=m.predict(te[ff])
   rows.append({"year":yy,"model":name,**score(te,p)})
   q=te[["_race","_horse","_year","race_date","target_lvs","target_finish_position","represented_field_size","hist_runs"]].copy(); q["model"]=name; q["pred_lvs"]=p; oo.append(q)
 res=pd.DataFrame(rows); oof=pd.concat(oo,ignore_index=True)
 res.to_csv(OUT,index=False); oof.to_csv(OOF,index=False)
 viable=[]
 for name in ["RIDGE","HGB","EXTRATREES"]:
  gains={}; ok=True
  for yy in [2022,2023]:
   b=res[(res.year==yy)&(res.model=="DEPTH_PRIOR")].iloc[0]; m=res[(res.year==yy)&(res.model==name)].iloc[0]
   g={"mae_gain":float(b.mae-m.mae),"rmse_gain":float(b.rmse-m.rmse),"spearman_gain":float(m.race_spearman_mean-b.race_spearman_mean)}
   gains[str(yy)]=g; ok &= all(v>0 for v in g.values())
  if ok:
   z=res[(res.year.isin([2022,2023]))&(res.model==name)]
   viable.append((name,float(z.mae.mean()),gains))
 viable.sort(key=lambda z:z[1]); selected=viable[0][0] if viable else None
 conf=None; survive=False
 if selected:
  b=res[(res.year==2024)&(res.model=="DEPTH_PRIOR")].iloc[0]; m=res[(res.year==2024)&(res.model==selected)].iloc[0]
  conf={"mae_gain":float(b.mae-m.mae),"rmse_gain":float(b.rmse-m.rmse),"spearman_gain":float(m.race_spearman_mean-b.race_spearman_mean),"complete_fields":int(m.complete_fields)}
  survive=all(conf[k]>0 for k in ["mae_gain","rmse_gain","spearman_gain"]) and conf["complete_fields"]>=500
 h=hashlib.sha256(OOF.read_bytes()).hexdigest()
 audit={"contract_version":"LAB245C_FULL_FIELD_HISTORY_DEPTH_V1","status":"SURVIVE_TO_FULL_FIELD_PROBABILITY" if survive else "REJECT_FULL_FIELD_PERFORMANCE","selection_years":[2022,2023],"confirmation_year":2024,"selected_model":selected,"viable_dev_models":[x[0] for x in viable],"selected_dev_gains":viable[0][2] if viable else None,"confirmation_2024":conf,"holdout_2025_2026_opened":False,"market_used":False,"weight_used":False,"oof_sha256":h}
 AUD.write_text(json.dumps(audit,indent=2),encoding="utf-8")
 print(res.to_string(index=False)); print(json.dumps(audit,indent=2))
if __name__=="__main__": main()
