from pathlib import Path
import pandas as pd, numpy as np, json
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, brier_score_loss
ROOT=Path(__file__).resolve().parents[2]; D=ROOT/"outputs/research/profitability_program/lab245b"; D.mkdir(parents=True,exist_ok=True)
P=D/"LAB245C2_FULL_FIELD_OOF_PROBABILITIES.csv"; OUT=D/"LAB245C5_DEPTH_RANK_RECALIBRATION.csv"; AUD=D/"LAB245C5_DEPTH_RANK_RECALIBRATION.json"
def add_features(x):
 x=x.copy(); eps=1e-9
 x["field_size"]=x.groupby("_race")["_horse"].transform("size")
 x["rank"]=x.groupby("_race")["p_model"].rank(method="first",ascending=False)
 x["logit_p"]=np.log(np.clip(x.p_model,eps,1-eps)/np.clip(1-x.p_model,eps,1))
 x["log_hist"]=np.log1p(x.hist_runs.clip(lower=0))
 x["hist0"]=(x.hist_runs==0).astype(float); x["hist1"]=(x.hist_runs==1).astype(float); x["hist2"]=(x.hist_runs==2).astype(float)
 x["hist10p"]=(x.hist_runs>=10).astype(float); x["rank1"]=(x["rank"]==1).astype(float); x["rank2"]=(x["rank"]==2).astype(float)
 x["inv_field"]=1/x.field_size; x["rank_pct"]=x["rank"]/x.field_size
 x["y"]=(x.target_finish_position==1).astype(int)
 return x
FEATURES=["logit_p","log_hist","hist0","hist1","hist2","hist10p","rank1","rank2","inv_field","rank_pct"]
def normalize_race(g,col):
 q=np.clip(g[col].to_numpy(float),1e-12,None); return q/q.sum()
def score(x,col):
 y=x.y.to_numpy(); p=np.clip(x[col].to_numpy(float),1e-12,1-1e-12)
 return {"rows":len(x),"races":x._race.nunique(),"log_loss":float(log_loss(y,p)),"brier":float(brier_score_loss(y,p))}
def main():
 x=add_features(pd.read_csv(P,low_memory=False))
 rows=[]; preds=[]
 # Strict expanding chronology. 2022 model fits 2021 OOF if present; otherwise 2022 is diagnostic baseline only.
 years=sorted(int(y) for y in x._year.dropna().unique())
 for yr in [2023,2024]:
  te=x[x._year.eq(yr)].copy(); tr=x[x._year.lt(yr)].copy()
  if tr.y.nunique()<2 or len(tr)<100:
   print(f"{yr}: insufficient earlier OOF rows for governed recalibration; baseline only"); continue
  m=LogisticRegression(C=1.0,max_iter=2000,solver="lbfgs")
  m.fit(tr[FEATURES].fillna(0),tr.y)
  te["raw_recal"]=m.predict_proba(te[FEATURES].fillna(0))[:,1]
  te["p_recal"]=te.groupby("_race",group_keys=False).apply(lambda g: pd.Series(normalize_race(g,"raw_recal"),index=g.index),include_groups=False).sort_index()
  a=score(te,"p_model"); b=score(te,"p_recal")
  rows.append({"year":yr,"baseline_log_loss":a["log_loss"],"recal_log_loss":b["log_loss"],"log_loss_gain":a["log_loss"]-b["log_loss"],"baseline_brier":a["brier"],"recal_brier":b["brier"],"brier_gain":a["brier"]-b["brier"],"races":b["races"]})
  preds.append(te[["_race","_horse","_year","hist_runs","rank","field_size","y","p_model","p_recal"]])
 out=pd.concat(preds,ignore_index=True) if preds else pd.DataFrame(); out.to_csv(OUT,index=False)
 audit={"contract":"LAB245C5_DEPTH_RANK_RECALIBRATION_V1","features":FEATURES,"chronology":"FIT_2022_SCORE_2023; FIT_2022_2023_SCORE_2024","selection":"NO_THRESHOLD_MINING; architecture diagnostic","2024_role":"OBSERVED_DIAGNOSTIC_NOT_PRISTINE_FOR_NEW_ARCHITECTURE","2025_2026_opened":False,"results":rows}
 AUD.write_text(json.dumps(audit,indent=2)); print(json.dumps(audit,indent=2))
 print("\nYEAR RESULTS"); print(pd.DataFrame(rows).to_string(index=False))
if __name__=="__main__":main()
