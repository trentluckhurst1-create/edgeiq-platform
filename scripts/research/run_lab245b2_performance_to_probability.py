# DEPRECATED: Do not execute. Superseded by run_lab245b2_probability_challenger.py, which enforces simple-vs-ML temporal survival gates.
# Retained only for research lineage.
from pathlib import Path
import json, math
import numpy as np
import pandas as pd
from scipy.special import softmax
from sklearn.metrics import log_loss

ROOT=Path(__file__).resolve().parents[2]
D=ROOT/"outputs/research/profitability_program/lab245b"
PRED=D/"LAB245B1_OOF_PREDICTIONS.csv"
AUDIT=D/"LAB245B1_AUDIT.json"
OUT=D/"LAB245B2_PROBABILITY_RESULTS.csv"
OUTP=D/"LAB245B2_PROBABILITIES.csv"
OUTA=D/"LAB245B2_AUDIT.json"

# Frozen temperature grid. Selected on development 2022-23 only; 2024 confirms once.
TEMPS=[0.5,0.75,1.0,1.5,2.0,3.0,4.0,6.0,8.0,12.0]

def race_probs(g,temp):
    z=g["pred_lvs"].to_numpy(float)/temp
    return softmax(z)

def score(df):
    x=df[np.isfinite(df["p_win"])].copy()
    # Only races with exactly one observed winner and >=2 scored runners are valid.
    valid=[]
    for rid,g in x.groupby("_race",sort=False):
        y=(pd.to_numeric(g["target_finish_position"],errors="coerce")==1).astype(int)
        if len(g)>=2 and y.sum()==1:
            gg=g.copy(); gg["y"]=y; valid.append(gg)
    if not valid:return {"races":0,"rows":0,"winner_log_loss":np.nan,"brier_runner":np.nan}
    q=pd.concat(valid,ignore_index=True)
    # Race winner log loss: -log probability assigned to actual best-LVS runner.
    wins=q[q["y"]==1]
    ll=float(-np.log(np.clip(wins["p_win"].to_numpy(float),1e-15,1)).mean())
    br=float(np.mean((q["p_win"].to_numpy(float)-q["y"].to_numpy(float))**2))
    return {"races":int(q["_race"].nunique()),"rows":int(len(q)),"winner_log_loss":ll,"brier_runner":br}

def main():
    if not PRED.exists() or not AUDIT.exists(): raise FileNotFoundError("LAB245B1 outputs required")
    a=json.loads(AUDIT.read_text())
    if a.get("status")!="SURVIVE_TO_LAB245B2":
        raise RuntimeError("LAB245B1 did not survive; probability stage is governance-blocked.")
    d=pd.read_csv(PRED,low_memory=False)
    if not d["_year"].between(2022,2024).all(): raise RuntimeError("Sealed-year breach.")
    selected=a["dev_selected_ml"]["model"]
    d=d[d["model"]==selected].copy()
    rows=[]; probs=[]
    for temp in TEMPS:
        q=d.copy(); q["temperature"]=temp
        q["p_win"]=q.groupby("_race",group_keys=False).apply(lambda g:pd.Series(race_probs(g,temp),index=g.index),include_groups=False).sort_index()
        for split,mask in [("DEV_2022_2023",q["_year"].isin([2022,2023])),("VALIDATION_2024",q["_year"].eq(2024))]:
            rows.append({"temperature":temp,"split":split,**score(q[mask])})
        probs.append(q)
    res=pd.DataFrame(rows)
    dev=res[res["split"]=="DEV_2022_2023"].sort_values(["winner_log_loss","brier_runner"])
    chosen=float(dev.iloc[0]["temperature"])
    val=res[(res["split"]=="VALIDATION_2024")&(res["temperature"]==chosen)].iloc[0]
    outp=pd.concat(probs,ignore_index=True)
    outp=outp[outp["temperature"]==chosen].copy()
    res.to_csv(OUT,index=False); outp.to_csv(OUTP,index=False)
    audit={"status":"LAB245B2_COMPLETE","source_model":selected,"temperature_selection":"DEV_2022_2023_ONLY","chosen_temperature":chosen,"validation_2024":val.to_dict(),"holdout_2025_2026_opened":False,"market_used":False}
    OUTA.write_text(json.dumps(audit,indent=2,default=str))
    print(res.to_string(index=False));print(json.dumps(audit,indent=2,default=str))
if __name__=="__main__":main()
