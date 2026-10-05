from pathlib import Path
import json, math, hashlib
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
DIR=ROOT/"outputs/research/profitability_program/lab245b"
B1=DIR/"LAB245B1_RANK_CHALLENGER_AUDIT.json"
PRED=DIR/"LAB245B1_RANK_CHALLENGER_OOF.csv"
OUT=DIR/"LAB245B2_RANK_PROBABILITY_RESULTS.csv"
AUD=DIR/"LAB245B2_RANK_PROBABILITY_AUDIT.json"
TEMPS=[0.5,0.75,1.0,1.5,2.0,2.5,3.0,4.0,5.0,6.0,8.0,10.0,12.0,15.0,20.0]

def probs(g,temp):
 x=pd.to_numeric(g["pred_lvs"],errors="coerce").to_numpy(float)
 if not np.isfinite(x).all(): return np.full(len(g),np.nan)
 z=(x-np.max(x))/temp; e=np.exp(np.clip(z,-50,50)); return e/e.sum()

def evaluate(d,temp):
 ll=[]; sq=[]; rows=[]
 for race,g in d.groupby("_race",sort=False):
  if len(g)<2: continue
  p=probs(g,temp)
  y=(pd.to_numeric(g.target_finish_position,errors="coerce").to_numpy(float)==1).astype(float)
  if not np.isfinite(p).all() or y.sum()!=1: continue
  if abs(float(p.sum())-1)>1e-10: raise RuntimeError("probability mass failure")
  ll.append(-math.log(max(float(p[y==1][0]),1e-15))); sq.extend(((p-y)**2).tolist())
  for (_,r),pi,yi in zip(g.iterrows(),p,y):
   rows.append({"_race":race,"_horse":r["_horse"],"_year":int(r["_year"]),"race_date":r["race_date"],"model":r["model"],"pred_lvs":r["pred_lvs"],"target_finish_position":r["target_finish_position"],"represented_field_size":r["represented_field_size"],"p_model":float(pi),"winner":int(yi),"temperature":temp})
 return {"races":len(ll),"runner_rows":len(rows),"log_loss":float(np.mean(ll)) if ll else np.nan,"brier_runner":float(np.mean(sq)) if sq else np.nan},pd.DataFrame(rows)

def tune(d):
 a=[]
 for t in TEMPS:
  m,_=evaluate(d,t); a.append({"temperature":t,**m})
 g=pd.DataFrame(a).sort_values(["log_loss","brier_runner","temperature"])
 return float(g.iloc[0].temperature),g

def main():
 b1=json.loads(B1.read_text(encoding="utf-8"))
 if b1.get("status")!="SURVIVE_TO_PROBABILITY_CHALLENGER": raise RuntimeError("rank challenger did not survive")
 ph=hashlib.sha256(PRED.read_bytes()).hexdigest()
 if ph!=b1.get("oof_sha256"): raise RuntimeError("rank challenger prediction lineage mismatch")
 selected=str(b1["selected_model"])
 d=pd.read_csv(PRED,low_memory=False); d=d[d.model.isin(["LVS_MEAN5",selected])].copy()
 d["_year"]=pd.to_numeric(d._year,errors="coerce")
 if d["_year"].isna().any() or not d["_year"].between(2022,2024).all(): raise RuntimeError("sealed-year breach")
 d["represented_field_size"]=pd.to_numeric(d.represented_field_size,errors="coerce")
 counts=d.groupby(["_race","model"])["_horse"].transform("nunique")
 d=d[counts.eq(d.represented_field_size)].copy()
 results=[]; probs_out=[]; grids=[]; fixed={}
 for model in ["LVS_MEAN5",selected]:
  dev=d[(d.model==model)&d._year.isin([2022,2023])]; val=d[(d.model==model)&(d._year==2024)]
  t,grid=tune(dev); fixed[model]=t; grid.insert(0,"model",model); grids.append(grid)
  dm,dp=evaluate(dev,t); vm,vp=evaluate(val,t)
  results += [{"period":"DEV_2022_2023","model":model,"temperature":t,**dm},{"period":"VALIDATION_2024","model":model,"temperature":t,**vm}]
  dp["period"]="DEV_2022_2023"; vp["period"]="VALIDATION_2024"; probs_out += [dp,vp]
 res=pd.DataFrame(results); res.to_csv(OUT,index=False)
 pd.concat(grids,ignore_index=True).to_csv(DIR/"LAB245B2_RANK_TEMPERATURE_GRID.csv",index=False)
 pp=pd.concat(probs_out,ignore_index=True); pp_path=DIR/"LAB245B2_RANK_OOF_PROBABILITIES.csv"; pp.to_csv(pp_path,index=False)
 base="LVS_MEAN5"; yearly={}; yearly_ok=True
 for yy in [2022,2023]:
  bm,_=evaluate(d[(d.model==base)&(d._year==yy)],fixed[base]); mm,_=evaluate(d[(d.model==selected)&(d._year==yy)],fixed[selected])
  yearly[str(yy)]={"log_loss_gain":bm["log_loss"]-mm["log_loss"],"brier_gain":bm["brier_runner"]-mm["brier_runner"]}
  yearly_ok &= yearly[str(yy)]["log_loss_gain"]>0 and yearly[str(yy)]["brier_gain"]>0
 bdev=res[(res.period=="DEV_2022_2023")&(res.model==base)].iloc[0]; mdev=res[(res.period=="DEV_2022_2023")&(res.model==selected)].iloc[0]
 bv=res[(res.period=="VALIDATION_2024")&(res.model==base)].iloc[0]; mv=res[(res.period=="VALIDATION_2024")&(res.model==selected)].iloc[0]
 valgain={"log_loss_gain":float(bv.log_loss-mv.log_loss),"brier_gain":float(bv.brier_runner-mv.brier_runner)}
 survive=bool(yearly_ok and mdev.races>=200 and mv.races>=100 and mdev.log_loss<bdev.log_loss and mdev.brier_runner<bdev.brier_runner and valgain["log_loss_gain"]>0 and valgain["brier_gain"]>0)
 qh=hashlib.sha256(pp_path.read_bytes()).hexdigest()
 audit={"contract_version":"LAB245B2_RANK_FULL_FIELD_SOFTMAX_V1","status":"SURVIVE_TO_PROFITABILITY_FORENSICS" if survive else "REJECT_RANK_PROBABILITY_CHALLENGER","selected_model":selected,"baseline_model":base,"temperature_selection":"2022_2023_ONLY","fixed_temperatures":fixed,"development_yearly_deltas":yearly,"confirmation_2024_deltas":valgain,"holdout_2025_2026_opened":False,"market_used":False,"b1_oof_sha256":ph,"oof_probabilities_sha256":qh,"oof_probabilities_bytes":pp_path.stat().st_size}
 AUD.write_text(json.dumps(audit,indent=2),encoding="utf-8")
 print(res.to_string(index=False)); print(json.dumps(audit,indent=2))
if __name__=="__main__": main()
