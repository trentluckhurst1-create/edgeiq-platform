from pathlib import Path
import os
import json
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT=Path(__file__).resolve().parents[2]
DATA_ROOT=Path(os.environ.get("EDGEIQ_DATA_ROOT",str(ROOT))).resolve()
SRC=DATA_ROOT/"outputs/research/model_lab_027/certified_pre_race_feature_matrix_027.csv"
OUTDIR=ROOT/"outputs/research/profitability_program/lab245b_l27"
OUT=OUTDIR/"LAB245B_L27_NEXT_PERFORMANCE_RESULTS.csv"
SUMMARY=OUTDIR/"LAB245B_L27_SUMMARY.json"

EPI_FEATURES=["epi_last1","epi_last2_mean","epi_last3_mean","epi_last5_mean","epi_last10_mean",
"epi_career_mean","epi_career_peak","epi_career_stdev","epi_last3_trend","epi_last5_trend",
"same_track_epi_mean","same_distance_epi_mean","same_condition_epi_mean","same_class_epi_mean"]
OTHER=["prior_starts","days_since_last_run","prior_win_rate","same_track_starts","same_distance_starts",
"same_condition_starts","same_class_starts","distance_metres","benchmark_prior_races_026"]
FEATURES=EPI_FEATURES+OTHER

def epi_level_to_lvs(x): return (x-50.0)/2.5
def epi_delta_to_lvs(x): return x/2.5

def rank_metric(frame,pred):
 vals=[]
 z=frame[["canonical_race_id","target_lvs"]].copy(); z["pred"]=pred
 for _,g in z.groupby("canonical_race_id",sort=False):
  g=g.dropna()
  if len(g)>=3 and g["target_lvs"].nunique()>1 and g["pred"].nunique()>1:
   v=spearmanr(g["target_lvs"],g["pred"]).statistic
   if np.isfinite(v): vals.append(v)
 return float(np.mean(vals)) if vals else np.nan

def metrics(frame,pred):
 y=frame.target_lvs.to_numpy(float); e=pred-y
 return {"rows":len(frame),"mae":float(np.mean(np.abs(e))),"rmse":float(np.sqrt(np.mean(e*e))),
         "race_spearman":rank_metric(frame,pred)}

def main():
 if not SRC.exists(): raise FileNotFoundError(SRC)
 use=["race_date","canonical_race_id","horse_id","target_epi_026"]+FEATURES
 d=pd.read_csv(SRC,usecols=use,low_memory=False)
 d["race_date"]=pd.to_datetime(d.race_date,errors="coerce")
 d["_year"]=d.race_date.dt.year
 if d["_year"].dropna().max()>2026: raise RuntimeError("unexpected future year")
 d=d[d._year.between(2021,2024)].copy()
 if d["_year"].gt(2024).any(): raise RuntimeError("sealed-year breach")
 if d.duplicated(["canonical_race_id","horse_id"]).any(): raise RuntimeError("duplicate race/horse keys")
 for c in ["target_epi_026"]+FEATURES: d[c]=pd.to_numeric(d[c],errors="coerce")
 d["target_lvs"]=epi_level_to_lvs(d["target_epi_026"])
 # EPI level features invert the documented EPI=50+2.5*LVS transform.
 for c in EPI_FEATURES:
  if c.endswith("_trend") or c=="epi_career_stdev": d[c]=epi_delta_to_lvs(d[c])
  else: d[c]=epi_level_to_lvs(d[c])
 d=d[d.target_lvs.notna()].copy()
 if d.empty: raise RuntimeError("no labelled rows")
 print("LABELLED_BY_YEAR="+json.dumps({int(y):int(n) for y,n in d.groupby("_year").size().items()}))
 print("RACES_BY_YEAR="+json.dumps({int(y):int(n) for y,n in d.groupby("_year").canonical_race_id.nunique().items()}))
 print("SEALED_2025_2026_LOADED=NO")
 baselines={"LVS_LAST1":"epi_last1","LVS_MEAN3":"epi_last3_mean","LVS_MEAN5":"epi_last5_mean",
            "LVS_CAREER":"epi_career_mean"}
 rows=[]; oof={}
 for year in [2022,2023,2024]:
  tr=d[d._year<year]; te=d[d._year==year]
  if tr.empty or te.empty: continue
  for name,col in baselines.items():
   p=te[col].fillna(tr[col].median()).to_numpy(float)
   rows.append({"year":year,"model":name,**metrics(te,p)})
  models={
   "RIDGE":make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),Ridge(alpha=10.0)),
   "HGB":make_pipeline(SimpleImputer(strategy="median"),HistGradientBoostingRegressor(max_iter=250,learning_rate=.04,max_leaf_nodes=15,l2_regularization=5,random_state=245))
  }
  for name,m in models.items():
   m.fit(tr[FEATURES],tr.target_lvs); p=m.predict(te[FEATURES])
   rows.append({"year":year,"model":name,**metrics(te,p)})
   if year in [2022,2023]: oof.setdefault(name,[]).append((te.copy(),p))
 # pooled development selection: 2022-23 only.
 dev=[]
 for name in list(baselines)+["RIDGE","HGB"]:
  parts=[]
  for year in [2022,2023]:
   te=d[d._year==year]
   if name in baselines:
    tr=d[d._year<year]; p=te[baselines[name]].fillna(tr[baselines[name]].median()).to_numpy(float)
   else:
    hit=[x for x in oof.get(name,[]) if len(x[0]) and int(x[0]._year.iloc[0])==year]
    if not hit: continue
    te,p=hit[0]
   parts.append((te,p))
  if parts:
   frame=pd.concat([x[0] for x in parts],ignore_index=True); pred=np.concatenate([x[1] for x in parts])
   dev.append({"model":name,**metrics(frame,pred)})
 devdf=pd.DataFrame(dev).sort_values(["rmse","mae"],kind="stable")
 best_base=devdf[devdf.model.isin(baselines)].iloc[0]
 best_ml=devdf[devdf.model.isin(["RIDGE","HGB"])].iloc[0]
 res=pd.DataFrame(rows); confirm=res[res.year==2024].set_index("model")
 yearly_ok=True; yearly_deltas={}
 for yy in [2022,2023]:
  yyres=res[res.year==yy].set_index("model"); sy=yyres.loc[best_base.model]; my=yyres.loc[best_ml.model]
  yearly_deltas[str(yy)]={"mae_gain":float(sy.mae-my.mae),"rmse_gain":float(sy.rmse-my.rmse),"spearman_gain":float(my.race_spearman-sy.race_spearman)}
  yearly_ok=yearly_ok and my.mae<sy.mae and my.rmse<sy.rmse and my.race_spearman>sy.race_spearman
 survive=(yearly_ok and best_ml.mae<best_base.mae and best_ml.rmse<best_base.rmse and best_ml.race_spearman>best_base.race_spearman
          and best_ml.model in confirm.index and best_base.model in confirm.index
          and confirm.loc[best_ml.model,"mae"]<confirm.loc[best_base.model,"mae"]
          and confirm.loc[best_ml.model,"rmse"]<confirm.loc[best_base.model,"rmse"]
          and confirm.loc[best_ml.model,"race_spearman"]>confirm.loc[best_base.model,"race_spearman"])
 OUTDIR.mkdir(parents=True,exist_ok=True); res.to_csv(OUT,index=False)
 summary={"status":"SURVIVES_TO_B2" if survive else "REJECT_B1","source":"MODEL_LAB_027_CERTIFIED_PRE_RACE",
 "target":"LAB026_EPI_INVERTED_TO_LVS","target_formula":"(target_epi_026-50)/2.5",
 "same_day_history":"PROHIBITED_BY_LAB027_GOVERNANCE","future_history":"PROHIBITED_BY_LAB027_GOVERNANCE",
 "market_features":"EXCLUDED","development_years":[2022,2023],"confirmation_year":2024,"sealed_years":[2025,2026],
 "best_baseline":best_base.to_dict(),"best_ml":best_ml.to_dict(),"development_yearly_stability_required":True,"development_yearly_deltas":yearly_deltas}
 SUMMARY.write_text(json.dumps(summary,indent=2,default=float),encoding="utf-8")
 print(json.dumps(summary,indent=2,default=float)); print(f"OUT={OUT}")
if __name__=="__main__": main()
