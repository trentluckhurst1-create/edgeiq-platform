from pathlib import Path
import os
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
DATA_ROOT=Path(os.environ.get("EDGEIQ_DATA_ROOT",str(ROOT))).resolve()
DIR=ROOT/"outputs/research/profitability_program/lab245b"
B2=DIR/"LAB245B2_AUDIT.json"
PROB=DIR/"LAB245B2_OOF_PROBABILITIES.csv"
SP_CANDIDATES=[
 DATA_ROOT/"outputs/research/profitability_program/compact/EDGEIQ_PROFITABILITY_COMPACT_RUNNERS.csv",
 DATA_ROOT/"outputs/research/model_price_diagnostics/lab166c/LAB166E_CORRECTED_PIT_PREDICTIONS.csv",
]
OUT=DIR/"LAB245B3_FINAL_SP_POLICY_RESULTS.csv"
AUD=DIR/"LAB245B3_AUDIT.json"

# Small predeclared policy family; no post-2023 tuning.
POLICIES=[
 ("EDGE_105",1.05,0.00,999.0),
 ("EDGE_110",1.10,0.00,999.0),
 ("EDGE_115",1.15,0.00,999.0),
 ("EDGE_120",1.20,0.00,999.0),
]

def load_sp():
 for p in SP_CANDIDATES:
  if p.exists():
   h=pd.read_csv(p,nrows=0).columns.tolist()
   req={"_race","_horse","_sp"}
   if req.issubset(h):
    d=pd.read_csv(p,usecols=["_race","_horse","_sp"],low_memory=False)
    d["_race"]=d["_race"].astype("string").str.strip(); d["_horse"]=d["_horse"].astype("string").str.strip()
    d["_sp"]=pd.to_numeric(d["_sp"],errors="coerce")
    d=d.dropna(subset=["_race","_horse","_sp"])
    if d.duplicated(["_race","_horse"]).any(): raise RuntimeError(f"Duplicate SP keys in {p}")
    if d["_sp"].le(1).any(): raise RuntimeError(f"Invalid SP in {p}")
    return d,p
 raise FileNotFoundError("No governed final-SP evaluation source found")

def metrics(x):
 x=x.sort_values(["race_date","_race","_horse"],kind="stable").copy()
 bets=len(x); wins=int(x["winner"].sum())
 pnl=x["winner"]*x["_sp"]-1.0
 equity=pnl.cumsum(); peak=np.maximum.accumulate(np.r_[0.0,equity.to_numpy(float)])[1:]
 dd=equity.to_numpy(float)-peak
 return {"bets":bets,"wins":wins,"strike_pct":100*wins/bets if bets else np.nan,
         "profit":float(pnl.sum()),"pot_pct":100*float(pnl.sum())/bets if bets else np.nan,
         "max_drawdown_units":float(dd.min()) if bets else np.nan,
         "mean_sp":float(x["_sp"].mean()) if bets else np.nan,
         "mean_edge_ratio":float(x["edge_ratio"].mean()) if bets else np.nan}

def apply(d,edge,pmin,spmax):
 return d[(d.edge_ratio>=edge)&(d.p_model>=pmin)&(d._sp<=spmax)].copy()

def main():
 if not B2.exists() or not PROB.exists(): raise FileNotFoundError("LAB245B2 outputs missing")
 b2=json.loads(B2.read_text(encoding="utf-8"))
 if b2.get("status")!="SURVIVE_TO_LAB245B3":
  a={"status":"SKIPPED_B2_REJECTED","b2_status":b2.get("status"),"holdout_2025_2026_opened":False}
  AUD.write_text(json.dumps(a,indent=2),encoding="utf-8"); print(json.dumps(a,indent=2)); return
 p=pd.read_csv(PROB,low_memory=False)
 ml=str(b2["selected_ml"]); p=p[p.model==ml].copy()
 if not p["_year"].between(2022,2024).all(): raise RuntimeError("Sealed-year breach")
 p["race_date"]=pd.to_datetime(p["race_date"],errors="coerce")
 sp,sp_path=load_sp(); d=p.merge(sp,on=["_race","_horse"],how="inner",validate="one_to_one")
 if len(d)!=len(p):
  race_ids=set(sp["_race"].dropna().astype(str)); horse_ids=set(sp["_horse"].dropna().astype(str))
  race_overlap=int(p["_race"].astype(str).isin(race_ids).sum()); horse_overlap=int(p["_horse"].astype(str).isin(horse_ids).sum())
  raise RuntimeError(f"Final-SP exact identity coverage incomplete joined={len(d)}/{len(p)} race_id_rows_overlapping={race_overlap} horse_id_rows_overlapping={horse_overlap}; fuzzy matching prohibited")
 d["edge_ratio"]=d["p_model"]*d["_sp"]
 rows=[]
 for name,e,pm,sm in POLICIES:
  for period,years in [("DEV_2022_2023",[2022,2023]),("YEAR_2022",[2022]),("YEAR_2023",[2023]),("VALIDATION_2024",[2024])]:
   x=apply(d[d["_year"].isin(years)],e,pm,sm)
   rows.append({"policy":name,"edge_min":e,"p_min":pm,"sp_max":sm,"period":period,**metrics(x)})
 r=pd.DataFrame(rows); r.to_csv(OUT,index=False)
 y22=r[r.period=="YEAR_2022"].copy(); y23=r[r.period=="YEAR_2023"].set_index("policy"); pooled=r[r.period=="DEV_2022_2023"].set_index("policy")
 # Temporal policy ladder: select once on 2022, then freeze for 2023 and 2024.
 eligible22=y22[(y22.bets>=50)&(y22.pot_pct>0)].copy()
 if eligible22.empty:
  status="REJECT_NO_2022_SELECTION_POLICY"; selected=None
 else:
  # Conservative 2022-only score; no 2023/2024 information enters policy selection.
  eligible22["selection_score"]=eligible22["pot_pct"]*(eligible22["bets"]/(eligible22["bets"]+200.0))
  selected=str(eligible22.sort_values(["selection_score","bets"],ascending=[False,False]).iloc[0].policy)
  c23=y23.loc[selected]; cp=pooled.loc[selected]
  if not (c23.bets>=50 and c23.pot_pct>0 and cp.bets>=150 and cp.pot_pct>0):
   status="REJECT_2023_POLICY_CONFIRMATION"
  else:
   v=r[(r.period=="VALIDATION_2024")&(r.policy==selected)].iloc[0]
   status="SURVIVE_TO_FORENSIC_HOLDOUT" if v.bets>=100 and v.pot_pct>0 else "REJECT_2024_POLICY_CONFIRMATION"
 a={"status":status,"selected_policy":selected,"policy_family_size":len(POLICIES),"policy_contract":"LAB245B_B3_SELECTIVE_BETTING_PREDECLARED.json edge thresholds 0.05/0.10/0.15/0.20",
    "selection":"2022 only; >=50 bets and positive POT; choose highest POT shrunk toward zero by n/(n+200), then freeze policy",
    "development_confirmation":"fixed policy 2023 requires >=50 bets and positive POT; pooled 2022-23 requires >=150 bets and positive POT",
    "validation":"same fixed policy 2024 requires >=100 bets and positive POT",
    "sp_source":str(sp_path),"final_sp_role":"HISTORICAL_POLICY_SELECTION_AND_FORENSICS_ONLY",
    "deployability_limitation":"Final SP is not a deployable offered price. Any surviving policy requires validation on actual pre-race offered odds.",
    "holdout_2025_2026_opened":False,"market_used_in_probability_model":False}
 AUD.write_text(json.dumps(a,indent=2),encoding="utf-8")
 print(r.to_string(index=False)); print(json.dumps(a,indent=2))

if __name__=="__main__": main()
