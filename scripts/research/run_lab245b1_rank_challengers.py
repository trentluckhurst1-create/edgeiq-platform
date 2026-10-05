from pathlib import Path
import json, math, hashlib
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge, HuberRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT=Path(__file__).resolve().parents[2]
OUTDIR=ROOT/"outputs/research/profitability_program/lab245b"
INP=OUTDIR/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
TARGET_MANIFEST=OUTDIR/"LAB245B_WAREHOUSE_RUNNER_LVS.manifest.json"
EXPECTED_TARGET_CONTRACT="LAB245B_STRICT_PIT_LVS_V12_QUARANTINE_LINEAGE_COMPLETE_V1_LENGTH_CONVERSION_TRACK_DISTANCE_CONDITION_MIN20"
FEATURES=["hist_runs","current_distance","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_worst5","margin_std5","finishpos_mean5","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best"]

def score(d,p,full):
 y=d.target_lvs.to_numpy(float); p=np.asarray(p,float); ok=np.isfinite(y)&np.isfinite(p)
 y=y[ok]; p=p[ok]; t=d.loc[ok,["_race","target_lvs"]].copy(); t["pred"]=p
 rho=[]
 for race,g in t.groupby("_race",sort=False):
  expected=full.get(race)
  if expected is None or len(g)!=int(expected): continue
  if len(g)>=3 and g.target_lvs.nunique()>1 and g.pred.nunique()>1: rho.append(g.target_lvs.corr(g.pred,method="spearman"))
 return {"rows":len(y),"races":int(t._race.nunique()),"mae":mean_absolute_error(y,p),"rmse":math.sqrt(mean_squared_error(y,p)),"ranking_full_field_races":len(rho),"race_spearman_mean":float(np.nanmean(rho)) if rho else np.nan}

def race_relative_features(df, feats):
 x=df.copy()
 for c in feats:
  v=pd.to_numeric(x[c],errors="coerce")
  med=v.groupby(x["_race"]).transform("median")
  x[c+"_relmed"]=v-med
 return x, feats+[c+"_relmed" for c in feats]

def models():
 return {
  "RIDGE_A1":make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),Ridge(alpha=1.0)),
  "RIDGE_A10":make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),Ridge(alpha=10.0)),
  "RIDGE_A100":make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),Ridge(alpha=100.0)),
  "HGB_SHALLOW":HistGradientBoostingRegressor(max_iter=300,learning_rate=.035,max_leaf_nodes=7,min_samples_leaf=30,l2_regularization=10,random_state=2451),
  "HGB_BASE":HistGradientBoostingRegressor(max_iter=250,learning_rate=.04,max_leaf_nodes=15,l2_regularization=5,random_state=2452),
  "EXTRATREES":make_pipeline(SimpleImputer(strategy="median"),ExtraTreesRegressor(n_estimators=350,min_samples_leaf=12,max_features=.75,n_jobs=-1,random_state=2453))
 }

def main():
 tm=json.loads(TARGET_MANIFEST.read_text(encoding="utf-8"))
 if tm.get("contract_version")!=EXPECTED_TARGET_CONTRACT: raise RuntimeError("target lineage mismatch")
 d=pd.read_csv(INP,low_memory=False)
 if not d["_year"].between(2021,2024).all(): raise RuntimeError("sealed-year breach")
 d["hist_runs"]=pd.to_numeric(d.hist_runs,errors="coerce").fillna(0)
 raw=d.copy(); d=d[d.target_lvs.notna() & (d.hist_runs>=3)].copy()
 d=d[np.isfinite(pd.to_numeric(d.lvs_mean3,errors="coerce"))].copy()
 for c in FEATURES+["target_lvs"]: d[c]=pd.to_numeric(d[c],errors="coerce")
 full=raw.groupby("_race").represented_field_size.first().astype(int).to_dict()
 base_pred={}
 rows=[]; preds=[]
 for year in [2022,2023,2024]:
  tr=d[d._year<year].copy(); te=d[d._year==year].copy()
  if tr.empty or te.empty: continue
  baseline=te.lvs_mean5.to_numpy(float)
  rows.append({"year":year,"model":"LVS_MEAN5","family":"BASELINE",**score(te,baseline,full)})
  q=te[["_race","_horse","_year","race_date","target_lvs","target_finish_position","target_field_size","represented_field_size"]].copy(); q["model"]="LVS_MEAN5"; q["pred_lvs"]=baseline; preds.append(q)
  for family in ["ABS","RACE_REL"]:
   if family=="ABS": tr2,te2,ff=tr,te,FEATURES
   else:
    both=pd.concat([tr.assign(__split=0),te.assign(__split=1)],ignore_index=True)
    both,ff=race_relative_features(both,FEATURES)
    tr2=both[both.__split==0]; te2=both[both.__split==1]
   year_preds={}
   for name,m in models().items():
    m.fit(tr2[ff],tr2.target_lvs); p=m.predict(te2[ff]); key=family+"_"+name
    year_preds[key]=p
    rows.append({"year":year,"model":key,"family":family,**score(te,p,full)})
    q=te[["_race","_horse","_year","race_date","target_lvs","target_finish_position","target_field_size","represented_field_size"]].copy(); q["model"]=key; q["pred_lvs"]=p; preds.append(q)
   # Fixed, non-optimized blends to test level+ranking complementarity.
   for w in [.25,.5,.75]:
    p=w*year_preds[family+"_RIDGE_A10"]+(1-w)*year_preds[family+"_HGB_SHALLOW"]
    key=f"{family}_BLEND_RIDGE_HGB_{int(w*100):02d}"
    rows.append({"year":year,"model":key,"family":family+"_BLEND",**score(te,p,full)})
    q=te[["_race","_horse","_year","race_date","target_lvs","target_finish_position","target_field_size","represented_field_size"]].copy(); q["model"]=key; q["pred_lvs"]=p; preds.append(q)
 res=pd.DataFrame(rows); pred=pd.concat(preds,ignore_index=True)
 res.to_csv(OUTDIR/"LAB245B1_RANK_CHALLENGER_RESULTS.csv",index=False)
 pred_path=OUTDIR/"LAB245B1_RANK_CHALLENGER_OOF.csv"; pred.to_csv(pred_path,index=False)
 # Select on 2022-23 only. Require improvement over LVS_MEAN5 in MAE/RMSE/Spearman in each dev year.
 viable=[]
 for name in res.model.unique():
  if name=="LVS_MEAN5": continue
  ok=True; gains={}
  for yy in [2022,2023]:
   b=res[(res.year==yy)&(res.model=="LVS_MEAN5")].iloc[0]; m=res[(res.year==yy)&(res.model==name)].iloc[0]
   gains[str(yy)]={"mae_gain":float(b.mae-m.mae),"rmse_gain":float(b.rmse-m.rmse),"spearman_gain":float(m.race_spearman_mean-b.race_spearman_mean)}
   ok &= gains[str(yy)]["mae_gain"]>0 and gains[str(yy)]["rmse_gain"]>0 and gains[str(yy)]["spearman_gain"]>0
  if ok:
   dg=res[(res.year.isin([2022,2023]))&(res.model==name)]
   viable.append((name,float(dg.mae.mean()),float(dg.rmse.mean()),float(dg.race_spearman_mean.mean()),gains))
 viable=sorted(viable,key=lambda z:(z[1],z[2],-z[3]))
 selected=viable[0][0] if viable else None
 confirmation=None; survive=False
 if selected:
  b=res[(res.year==2024)&(res.model=="LVS_MEAN5")].iloc[0]; m=res[(res.year==2024)&(res.model==selected)].iloc[0]
  confirmation={"mae_gain":float(b.mae-m.mae),"rmse_gain":float(b.rmse-m.rmse),"spearman_gain":float(m.race_spearman_mean-b.race_spearman_mean)}
  survive=all(v>0 for v in confirmation.values())
 h=hashlib.sha256(pred_path.read_bytes()).hexdigest()
 audit={"contract_version":"LAB245B1_RANK_CHALLENGERS_V1","status":"SURVIVE_TO_PROBABILITY_CHALLENGER" if survive else "REJECT_RANK_CHALLENGERS","selection_years":[2022,2023],"confirmation_year":2024,"holdout_2025_2026_opened":False,"market_used":False,"selected_model":selected,"viable_dev_models":[x[0] for x in viable],"selected_dev_gains":viable[0][4] if viable else None,"confirmation_2024_gains":confirmation,"oof_sha256":h}
 (OUTDIR/"LAB245B1_RANK_CHALLENGER_AUDIT.json").write_text(json.dumps(audit,indent=2),encoding="utf-8")
 print(res.to_string(index=False)); print(json.dumps(audit,indent=2))
if __name__=="__main__": main()
