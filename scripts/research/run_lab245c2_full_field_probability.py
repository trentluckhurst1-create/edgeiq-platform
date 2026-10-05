from pathlib import Path
import json, math, hashlib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

ROOT=Path(__file__).resolve().parents[2]
D=ROOT/"outputs/research/profitability_program/lab245b"
A1=D/"LAB245C_FULL_FIELD_AUDIT.json"; P=D/"LAB245C_FULL_FIELD_OOF.csv"
OUT=D/"LAB245C2_FULL_FIELD_PROBABILITY_RESULTS.csv"; PROB=D/"LAB245C2_FULL_FIELD_OOF_PROBABILITIES.csv"; AUD=D/"LAB245C2_FULL_FIELD_PROBABILITY_AUDIT.json"

def enrich(d):
 d=d.copy(); g=d.groupby("_race")["pred_lvs"]
 d["rel_med"]=d.pred_lvs-g.transform("median"); d["rel_mean"]=d.pred_lvs-g.transform("mean")
 sd=g.transform("std").replace(0,np.nan); d["z"]=(d.pred_lvs-g.transform("mean"))/sd
 d["rankpct"]=d.groupby("_race").pred_lvs.rank(method="average",pct=True)
 d["field_n"]=d.groupby("_race")["_horse"].transform("nunique")
 d["log_field_n"]=np.log(d.field_n.clip(lower=2))
 return d

def norm(d,raw):
 q=d.copy(); q["raw"]=np.clip(np.asarray(raw,float),1e-15,None)
 q["p_model"]=q.raw/q.groupby("_race").raw.transform("sum"); return q

def softmax(d,t):
 z=(d.pred_lvs-d.groupby("_race").pred_lvs.transform("max"))/t
 return norm(d,np.exp(np.clip(z,-50,50)))

def fitlog(tr,cols,C):
 X=tr[cols].replace([np.inf,-np.inf],np.nan).fillna(0).to_numpy(float)
 y=(tr.target_finish_position.to_numpy(float)==1).astype(int)
 m=LogisticRegression(C=C,max_iter=3000); m.fit(X,y); return m

def aplog(m,d,cols):
 X=d[cols].replace([np.inf,-np.inf],np.nan).fillna(0).to_numpy(float)
 return norm(d,m.predict_proba(X)[:,1])

def met(q):
 ll=[]; br=[]
 for _,g in q.groupby("_race",sort=False):
  y=(g.target_finish_position.to_numpy(float)==1).astype(float); p=g.p_model.to_numpy(float)
  if len(g)<2 or y.sum()!=1 or not np.isfinite(p).all(): continue
  ll.append(-math.log(max(float(p[y==1][0]),1e-15))); br.extend(((p-y)**2).tolist())
 return {"races":len(ll),"runner_rows":len(br),"log_loss":float(np.mean(ll)),"brier_runner":float(np.mean(br))}

def main():
 a=json.loads(A1.read_text(encoding="utf-8"))
 if a.get("status")!="SURVIVE_TO_FULL_FIELD_PROBABILITY": raise RuntimeError("LAB245C did not survive")
 ph=hashlib.sha256(P.read_bytes()).hexdigest()
 if ph!=a.get("oof_sha256"): raise RuntimeError("LAB245C lineage mismatch")
 d=pd.read_csv(P,low_memory=False); model=a["selected_model"]; d=d[d.model==model].copy()
 if not d._year.between(2022,2024).all(): raise RuntimeError("sealed-year breach")
 d=enrich(d); dev=d[d._year.isin([2022,2023])].copy(); val=d[d._year==2024].copy()
 specs={}; rows=[]
 for t in [5,8,10,12,15,20,25,30,40,50]:
  n=f"SOFTMAX_T{t}"; q=softmax(dev,t); rows.append({"model":n,**met(q)}); specs[n]=("soft",t)
 colsets={"REL":["rel_med"],"Z":["z"],"RANK":["rankpct"],"ALL":["rel_med","z","rankpct"],"ALL_FIELD":["rel_med","z","rankpct","log_field_n"]}
 for base,cols in colsets.items():
  for C in [.1,1,10]:
   n=f"LOGIT_{base}_C{C:g}"; m=fitlog(dev,cols,C); q=aplog(m,dev,cols); rows.append({"model":n,**met(q)}); specs[n]=("logit",m,cols)
 r=pd.DataFrame(rows).sort_values(["log_loss","brier_runner","model"]).reset_index(drop=True)
 # Governed selection: best pooled dev log loss, but candidate must improve both metrics in each dev year over T15.
 viable=[]
 for n in r.model:
  typ=specs[n]; gains={}; ok=True
  for yy in [2022,2023]:
   x=dev[dev._year==yy]; b=met(softmax(x,15)); q=softmax(x,typ[1]) if typ[0]=="soft" else aplog(typ[1],x,typ[2]); m=met(q)
   gains[str(yy)]={"log_loss_gain":b["log_loss"]-m["log_loss"],"brier_gain":b["brier_runner"]-m["brier_runner"]}
   ok &= gains[str(yy)]["log_loss_gain"]>0 and gains[str(yy)]["brier_gain"]>0
  if ok: viable.append((n,float(r.loc[r.model==n,"log_loss"].iloc[0]),gains))
 viable.sort(key=lambda z:z[1]); selected=viable[0][0] if viable else None
 confirmation=None; survive=False
 probs=[]
 if selected:
  typ=specs[selected]
  for yy in [2022,2023,2024]:
   x=d[d._year==yy]; q=softmax(x,typ[1]) if typ[0]=="soft" else aplog(typ[1],x,typ[2])
   q["calibration_model"]=selected; probs.append(q)
  qv=probs[-1]; mv=met(qv); bv=met(softmax(val,15))
  confirmation={"metrics":mv,"log_loss_gain_vs_T15":bv["log_loss"]-mv["log_loss"],"brier_gain_vs_T15":bv["brier_runner"]-mv["brier_runner"]}
  survive=mv["races"]>=1000 and confirmation["log_loss_gain_vs_T15"]>0 and confirmation["brier_gain_vs_T15"]>0
 r.to_csv(OUT,index=False)
 if probs:
  po=pd.concat(probs,ignore_index=True); po.to_csv(PROB,index=False); probsha=hashlib.sha256(PROB.read_bytes()).hexdigest()
 else: probsha=None
 audit={"contract_version":"LAB245C2_FULL_FIELD_PROBABILITY_V1","status":"SURVIVE_TO_PROFITABILITY_FORENSICS" if survive else "REJECT_FULL_FIELD_PROBABILITY","performance_model":model,"selection_years":[2022,2023],"confirmation_year":2024,"selected_calibration":selected,"viable_dev_calibrations":[x[0] for x in viable],"selected_dev_gains":viable[0][2] if viable else None,"confirmation_2024":confirmation,"holdout_2025_2026_opened":False,"market_used":False,"performance_oof_sha256":ph,"probability_oof_sha256":probsha}
 AUD.write_text(json.dumps(audit,indent=2),encoding="utf-8")
 print(r.to_string(index=False)); print(json.dumps(audit,indent=2))
if __name__=="__main__": main()
