from pathlib import Path
import json, math, hashlib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

ROOT=Path(__file__).resolve().parents[2]
DIR=ROOT/"outputs/research/profitability_program/lab245b"
B1=DIR/"LAB245B1_RANK_CHALLENGER_AUDIT.json"
PRED=DIR/"LAB245B1_RANK_CHALLENGER_OOF.csv"
OUT=DIR/"LAB245B2_CALIBRATION_CHALLENGER_RESULTS.csv"
AUD=DIR/"LAB245B2_CALIBRATION_CHALLENGER_AUDIT.json"

def add_race_features(d):
 d=d.copy()
 g=d.groupby("_race")["pred_lvs"]
 d["score_med"]=d["pred_lvs"]-g.transform("median")
 d["score_mean"]=d["pred_lvs"]-g.transform("mean")
 sd=g.transform("std").replace(0,np.nan)
 d["score_z"]=(d["pred_lvs"]-g.transform("mean"))/sd
 d["score_rankpct"]=d.groupby("_race")["pred_lvs"].rank(method="average",pct=True)
 return d

def normalize_by_race(d, raw):
 x=d.copy(); x["raw"]=np.asarray(raw,float)
 x["raw"]=np.clip(x["raw"],1e-12,None)
 den=x.groupby("_race")["raw"].transform("sum")
 x["p_model"]=x["raw"]/den
 return x

def metrics(x):
 ll=[]; sq=[]
 for _,g in x.groupby("_race",sort=False):
  y=(g["target_finish_position"].to_numpy(float)==1).astype(float)
  p=g["p_model"].to_numpy(float)
  if len(g)<2 or y.sum()!=1 or not np.isfinite(p).all(): continue
  ll.append(-math.log(max(float(p[y==1][0]),1e-15))); sq.extend(((p-y)**2).tolist())
 return {"races":len(ll),"runner_rows":len(sq),"log_loss":float(np.mean(ll)),"brier_runner":float(np.mean(sq))}

def softmax(d,t):
 z=(d["pred_lvs"]-d.groupby("_race")["pred_lvs"].transform("max"))/t
 return normalize_by_race(d,np.exp(np.clip(z,-50,50)))

def fit_logit(train, cols, C):
 X=train[cols].replace([np.inf,-np.inf],np.nan).fillna(0).to_numpy(float)
 y=(train["target_finish_position"].to_numpy(float)==1).astype(int)
 m=LogisticRegression(C=C,max_iter=2000,class_weight=None)
 m.fit(X,y); return m

def apply_logit(m,d,cols):
 X=d[cols].replace([np.inf,-np.inf],np.nan).fillna(0).to_numpy(float)
 return normalize_by_race(d,m.predict_proba(X)[:,1])

def main():
 b1=json.loads(B1.read_text(encoding="utf-8"))
 if b1.get("status")!="SURVIVE_TO_PROBABILITY_CHALLENGER": raise RuntimeError("B1 challenger did not survive")
 ph=hashlib.sha256(PRED.read_bytes()).hexdigest()
 if ph!=b1.get("oof_sha256"): raise RuntimeError("B1 lineage mismatch")
 model=str(b1["selected_model"])
 d=pd.read_csv(PRED,low_memory=False); d=d[d.model==model].copy()
 d["_year"]=pd.to_numeric(d._year,errors="coerce"); d["target_finish_position"]=pd.to_numeric(d.target_finish_position,errors="coerce")
 d["represented_field_size"]=pd.to_numeric(d.represented_field_size,errors="coerce")
 if d["_year"].isna().any() or not d["_year"].between(2022,2024).all(): raise RuntimeError("sealed-year breach")
 cnt=d.groupby("_race")["_horse"].transform("nunique"); d=d[cnt.eq(d.represented_field_size)].copy()
 d=add_race_features(d)
 dev=d[d._year.isin([2022,2023])].copy(); val=d[d._year==2024].copy()
 candidates=[]; predictions={}
 for t in [5,8,10,12,15,20,25,30,40]:
  name=f"SOFTMAX_T{t}"; q=softmax(dev,t); candidates.append({"model":name,**metrics(q)}); predictions[name]=("softmax",t)
 specs=[
  ("LOGIT_MED",["score_med"]),
  ("LOGIT_MEAN",["score_mean"]),
  ("LOGIT_Z",["score_z"]),
  ("LOGIT_RANK",["score_rankpct"]),
  ("LOGIT_MED_Z",["score_med","score_z"]),
  ("LOGIT_MED_RANK",["score_med","score_rankpct"]),
  ("LOGIT_ALL",["score_med","score_z","score_rankpct"]),
 ]
 for base,cols in specs:
  for C in [0.1,1.0,10.0]:
   name=f"{base}_C{C:g}"; m=fit_logit(dev,cols,C); q=apply_logit(m,dev,cols)
   candidates.append({"model":name,**metrics(q)}); predictions[name]=("logit",m,cols)
 c=pd.DataFrame(candidates).sort_values(["log_loss","brier_runner","model"]).reset_index(drop=True)
 selected=str(c.iloc[0].model)
 typ=predictions[selected]
 qv=softmax(val,typ[1]) if typ[0]=="softmax" else apply_logit(typ[1],val,typ[2])
 vm=metrics(qv)
 yearly={}; stable=True
 for yy in [2022,2023]:
  dy=dev[dev._year==yy]
  qy=softmax(dy,typ[1]) if typ[0]=="softmax" else apply_logit(typ[1],dy,typ[2])
  yearly[str(yy)]=metrics(qy)
 # Baseline is the previously tested fixed softmax T15 on the same selected performance model.
 base_dev=metrics(softmax(dev,15)); base_val=metrics(softmax(val,15))
 for yy in [2022,2023]:
  bm=metrics(softmax(dev[dev._year==yy],15)); mm=yearly[str(yy)]
  yearly[str(yy)]["log_loss_gain_vs_T15"]=bm["log_loss"]-mm["log_loss"]
  yearly[str(yy)]["brier_gain_vs_T15"]=bm["brier_runner"]-mm["brier_runner"]
  stable &= yearly[str(yy)]["log_loss_gain_vs_T15"]>0 and yearly[str(yy)]["brier_gain_vs_T15"]>0
 val_gain={"log_loss_gain_vs_T15":base_val["log_loss"]-vm["log_loss"],"brier_gain_vs_T15":base_val["brier_runner"]-vm["brier_runner"]}
 survive=bool(stable and vm["races"]>=100 and val_gain["log_loss_gain_vs_T15"]>0 and val_gain["brier_gain_vs_T15"]>0)
 c.to_csv(OUT,index=False)
 qv["period"]="VALIDATION_2024"; qv["calibration_model"]=selected
 prob_path=DIR/"LAB245B2_CALIBRATION_SELECTED_2024.csv"; qv.to_csv(prob_path,index=False)
 audit={"contract_version":"LAB245B2_CALIBRATION_CHALLENGERS_V1","status":"SURVIVE_CALIBRATION_CHALLENGER" if survive else "REJECT_CALIBRATION_CHALLENGERS","performance_model":model,"selection_years":[2022,2023],"confirmation_year":2024,"selected_calibration":selected,"candidate_count":len(c),"selected_dev_metrics":c.iloc[0].to_dict(),"baseline_T15_dev_metrics":base_dev,"development_yearly":yearly,"confirmation_2024_metrics":vm,"confirmation_2024_gains_vs_T15":val_gain,"holdout_2025_2026_opened":False,"market_used":False,"b1_oof_sha256":ph}
 AUD.write_text(json.dumps(audit,indent=2),encoding="utf-8")
 print(c.to_string(index=False)); print(json.dumps(audit,indent=2))
if __name__=="__main__": main()
