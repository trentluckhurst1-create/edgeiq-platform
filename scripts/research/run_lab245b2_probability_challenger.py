from pathlib import Path
import json, math
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
DIR=ROOT/"outputs/research/profitability_program/lab245b"
B1=DIR/"LAB245B1_AUDIT.json"
PRED=DIR/"LAB245B1_OOF_PREDICTIONS.csv"
OUT=DIR/"LAB245B2_PROBABILITY_RESULTS.csv"
AUD=DIR/"LAB245B2_AUDIT.json"
TEMPS=[0.5,0.75,1.0,1.5,2.0,2.5,3.0,4.0,5.0,6.0,8.0,10.0,12.0]

def probs(g,temp):
 x=pd.to_numeric(g["pred_lvs"],errors="coerce").to_numpy(float)
 if not np.isfinite(x).all(): return np.full(len(g),np.nan)
 z=(x-np.max(x))/temp
 e=np.exp(np.clip(z,-50,50))
 return e/e.sum()

def evaluate(d,temp):
 rows=[]; ll=[]; sqerr=[]
 for race,g in d.groupby("_race",sort=False):
  if len(g)<2: continue
  p=probs(g,temp)
  y=(pd.to_numeric(g["target_finish_position"],errors="coerce").to_numpy(float)==1).astype(float)
  if not np.isfinite(p).all() or y.sum()!=1: continue
  s=float(p.sum())
  if abs(s-1.0)>1e-10: raise RuntimeError(f"Probability mass failure race={race} sum={s}")
  win=float(p[y==1][0]); ll.append(-math.log(max(win,1e-15)))
  sqerr.extend(((p-y)**2).tolist())
  for (_,r),pi,yi in zip(g.iterrows(),p,y):
   rows.append({"_race":race,"_horse":r["_horse"],"_year":int(r["_year"]),"model":r["model"],
                "race_date":r["race_date"],"pred_lvs":r["pred_lvs"],"target_finish_position":r["target_finish_position"],
                "p_model":float(pi),"winner":int(yi),"temperature":temp})
 return {"races":len(ll),"runner_rows":len(rows),"log_loss":float(np.mean(ll)) if ll else np.nan,
         "brier_runner":float(np.mean(sqerr)) if sqerr else np.nan},pd.DataFrame(rows)

def tune(d):
 cand=[]
 for t in TEMPS:
  m,_=evaluate(d,t); cand.append({"temperature":t,**m})
 c=pd.DataFrame(cand).sort_values(["log_loss","brier_runner","temperature"])
 return float(c.iloc[0]["temperature"]),c

def main():
 if not B1.exists() or not PRED.exists(): raise FileNotFoundError("LAB245B1 outputs missing")
 b1=json.loads(B1.read_text(encoding="utf-8"))
 if b1.get("status")!="SURVIVE_TO_LAB245B2":
  audit={"status":"SKIPPED_B1_REJECTED","b1_status":b1.get("status"),"holdout_2025_2026_opened":False,"market_used":False}
  AUD.write_text(json.dumps(audit,indent=2),encoding="utf-8"); print(json.dumps(audit,indent=2)); return
 d=pd.read_csv(PRED,low_memory=False)
 if "target_field_size" not in d.columns: raise RuntimeError("LAB245B2 requires full target field size for probability completeness")
 d["target_field_size"]=pd.to_numeric(d["target_field_size"],errors="coerce")
 eligible_counts=d.groupby(["_race","model"])["_horse"].transform("nunique")
 complete=eligible_counts.eq(d["target_field_size"])
 incomplete_rows=int((~complete).sum()); incomplete_races=int(d.loc[~complete,"_race"].nunique())
 d=d[complete].copy()
 print(f"PROBABILITY_FIELD_COMPLETENESS=FULL_VALID_TARGET_FIELD_ONLY EXCLUDED_RACES={incomplete_races:,} EXCLUDED_ROWS={incomplete_rows:,}")
 d["_year"]=pd.to_numeric(d["_year"],errors="coerce")
 d["target_finish_position"]=pd.to_numeric(d["target_finish_position"],errors="coerce")
 d["pred_lvs"]=pd.to_numeric(d["pred_lvs"],errors="coerce")
 if d["_year"].isna().any() or not d["_year"].between(2022,2024).all(): raise RuntimeError("Sealed-year breach")
 simple=str(b1["dev_selected_simple"]["model"]); ml=str(b1["dev_selected_ml"]["model"])
 selected=d[d["model"].isin([simple,ml])].copy()
 results=[]; prob_parts=[]; tune_parts=[]
 fixed={}
 for model in [simple,ml]:
  dev=selected[(selected["model"]==model)&(selected["_year"].isin([2022,2023]))]
  val=selected[(selected["model"]==model)&(selected["_year"]==2024)]
  t,grid=tune(dev); fixed[model]=t; grid.insert(0,"model",model); tune_parts.append(grid)
  dm,dp=evaluate(dev,t); vm,vp=evaluate(val,t)
  results += [{"period":"DEV_2022_2023","model":model,"temperature":t,**dm},
              {"period":"VALIDATION_2024","model":model,"temperature":t,**vm}]
  dp["period"]="DEV_2022_2023"; vp["period"]="VALIDATION_2024"; prob_parts += [dp,vp]
 res=pd.DataFrame(results)
 sdev=res[(res.period=="DEV_2022_2023")&(res.model==simple)].iloc[0]
 mdev=res[(res.period=="DEV_2022_2023")&(res.model==ml)].iloc[0]
 sval=res[(res.period=="VALIDATION_2024")&(res.model==simple)].iloc[0]
 mval=res[(res.period=="VALIDATION_2024")&(res.model==ml)].iloc[0]
 yearly_ok=True; yearly_deltas={}
 for yy in [2022,2023]:
  sy=selected[(selected["model"]==simple)&(selected["_year"]==yy)]; my=selected[(selected["model"]==ml)&(selected["_year"]==yy)]
  sm,_=evaluate(sy,fixed[simple]); mm,_=evaluate(my,fixed[ml])
  yearly_deltas[str(yy)]={"log_loss_gain":float(sm["log_loss"]-mm["log_loss"]),"brier_gain":float(sm["brier_runner"]-mm["brier_runner"])}
  yearly_ok=yearly_ok and mm["log_loss"]<sm["log_loss"] and mm["brier_runner"]<sm["brier_runner"]
 survive=bool(yearly_ok and mdev.log_loss<sdev.log_loss and mdev.brier_runner<sdev.brier_runner and
              mval.log_loss<sval.log_loss and mval.brier_runner<sval.brier_runner)
 res.to_csv(OUT,index=False)
 pd.concat(tune_parts,ignore_index=True).to_csv(DIR/"LAB245B2_TEMPERATURE_GRID.csv",index=False)
 pd.concat(prob_parts,ignore_index=True).to_csv(DIR/"LAB245B2_OOF_PROBABILITIES.csv",index=False)
 audit={"status":"SURVIVE_TO_LAB245B3" if survive else "REJECT_PROBABILITY_CHALLENGER",
        "selected_simple":simple,"selected_ml":ml,"temperature_selection":"DEV_2022_2023_ONLY",
        "fixed_temperatures":fixed,"survival_rule":"ML beats simple on race-winner log loss and runner Brier in DEV and fixed 2024",
        "probability_mass":"EXACT_WITHIN_1E-10","probability_field_universe":"FULL_VALID_TARGET_FIELD_ONLY","development_yearly_stability_required":True,"development_yearly_deltas":yearly_deltas,"holdout_2025_2026_opened":False,"market_used":False}
 AUD.write_text(json.dumps(audit,indent=2),encoding="utf-8")
 print(res.to_string(index=False)); print(json.dumps(audit,indent=2))

if __name__=="__main__": main()
