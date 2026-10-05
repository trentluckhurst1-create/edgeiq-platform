from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
DIR=ROOT/"outputs/research/profitability_program/lab245b"
B2=DIR/"LAB245B2_AUDIT.json"
PROB=DIR/"LAB245B2_OOF_PROBABILITIES.csv"
MARKET=ROOT/"outputs/research/profitability_program/compact/EDGEIQ_PROFITABILITY_COMPACT_RUNNERS.csv"
OUT=DIR/"LAB245B3_FINAL_SP_POLICY_RESULTS.csv"
AUD=DIR/"LAB245B3_AUDIT.json"

EDGE_THRESHOLDS=[1.00,1.05,1.10,1.15,1.20,1.25,1.30,1.40,1.50,1.75,2.00]
MAX_ODDS=[5.0,8.0,12.0,20.0,50.0,9999.0]
MIN_BETS_2022=100
MIN_BETS_CONFIRM=75

def metrics(x):
 x=x.sort_values(["race_date","_race","_horse"],kind="stable").copy()
 n=len(x); wins=int(x["winner"].sum())
 profit=float(np.where(x["winner"].eq(1),x["final_sp"]-1.0,-1.0).sum()) if n else 0.0
 pnl=np.where(x["winner"].eq(1),x["final_sp"]-1.0,-1.0)
 eq=np.cumsum(pnl); peak=np.maximum.accumulate(np.r_[0.0,eq])[:-1] if n else np.array([])
 dd=eq-peak if n else np.array([])
 maxdd=float(-dd.min()) if n else 0.0
 longest=cur=0
 for w in x["winner"].astype(int):
  if w: cur=0
  else: cur+=1; longest=max(longest,cur)
 return {"bets":n,"wins":wins,"strike_rate":wins/n if n else np.nan,"profit":profit,
         "pot":profit/n if n else np.nan,"max_drawdown_units":maxdd,"longest_losing_run":longest}

def main():
 if not B2.exists() or not PROB.exists(): raise FileNotFoundError("LAB245B2 outputs missing")
 b2=json.loads(B2.read_text(encoding="utf-8"))
 if b2.get("status")!="SURVIVE_TO_LAB245B3":
  audit={"status":"SKIPPED_B2_REJECTED","b2_status":b2.get("status"),"holdout_2025_2026_opened":False}
  AUD.write_text(json.dumps(audit,indent=2),encoding="utf-8"); print(json.dumps(audit,indent=2)); return
 if not MARKET.exists(): raise FileNotFoundError(MARKET)
 p=pd.read_csv(PROB,low_memory=False)
 m=pd.read_csv(MARKET,low_memory=False)
 need={"_race","_horse","_year","winner","final_sp"}
 miss=sorted(need-set(m.columns))
 if miss: raise RuntimeError(f"LAB245B3 market contract missing columns: {miss}")
 for c in ["_race","_horse"]: p[c]=p[c].astype("string").str.strip(); m[c]=m[c].astype("string").str.strip()
 m["_year"]=pd.to_numeric(m["_year"],errors="coerce"); m["winner"]=pd.to_numeric(m["winner"],errors="coerce"); m["final_sp"]=pd.to_numeric(m["final_sp"],errors="coerce")
 if m["_year"].gt(2024).any():
  # Never even join sealed years during policy discovery.
  m=m[m["_year"].between(2021,2024)].copy()
 if not p["_year"].between(2022,2024).all(): raise RuntimeError("Probability file contains sealed years")
 ml=str(b2["selected_ml"])
 p=p[p["model"].astype(str).eq(ml)].copy()
 d=p.merge(m[["_race","_horse","_year","winner","final_sp"]],on=["_race","_horse","_year"],how="inner",validate="one_to_one")
 if len(d)!=len(p): raise RuntimeError(f"Market join incomplete: probabilities={len(p)} joined={len(d)}")
 if d["final_sp"].isna().any() or (d["final_sp"]<=1).any(): raise RuntimeError("Invalid final SP in joined forensic universe")
 d["edge_multiple"]=d["p_model"]*d["final_sp"]
 # Policy selection is 2022 only. No 2023/2024 information enters the threshold choice.
 grid=[]
 for e in EDGE_THRESHOLDS:
  for cap in MAX_ODDS:
   x=d[(d["_year"]==2022)&(d["edge_multiple"]>=e)&(d["final_sp"]<=cap)]
   z=metrics(x); grid.append({"edge_threshold":e,"max_odds":cap,**z})
 g=pd.DataFrame(grid)
 eligible=g[g["bets"]>=MIN_BETS_2022].copy()
 if eligible.empty:
  audit={"status":"REJECT_NO_2022_POLICY_VOLUME","minimum_2022_bets":MIN_BETS_2022,"holdout_2025_2026_opened":False,"final_sp_forensic_only":True}
  g.to_csv(DIR/"LAB245B3_2022_POLICY_GRID.csv",index=False); AUD.write_text(json.dumps(audit,indent=2),encoding="utf-8"); print(json.dumps(audit,indent=2)); return
 # Conservative objective: highest 2022 profit among positive-POT policies, tie-break lower drawdown then more bets.
 pos=eligible[eligible["pot"]>0].copy()
 if pos.empty:
  audit={"status":"REJECT_NO_POSITIVE_2022_POLICY","minimum_2022_bets":MIN_BETS_2022,"holdout_2025_2026_opened":False,"final_sp_forensic_only":True}
  g.to_csv(DIR/"LAB245B3_2022_POLICY_GRID.csv",index=False); AUD.write_text(json.dumps(audit,indent=2),encoding="utf-8"); print(json.dumps(audit,indent=2)); return
 best=pos.sort_values(["profit","max_drawdown_units","bets"],ascending=[False,True,False]).iloc[0]
 e=float(best.edge_threshold); cap=float(best.max_odds)
 rows=[]
 for yy in [2022,2023,2024]:
  x=d[(d["_year"]==yy)&(d["edge_multiple"]>=e)&(d["final_sp"]<=cap)]
  rows.append({"year":yy,"edge_threshold":e,"max_odds":cap,**metrics(x)})
 res=pd.DataFrame(rows)
 y23=res[res.year==2023].iloc[0]; y24=res[res.year==2024].iloc[0]
 survive=bool(y23.bets>=MIN_BETS_CONFIRM and y24.bets>=MIN_BETS_CONFIRM and y23.pot>0 and y24.pot>0)
 # Stability diagnostics only; never used to reselect the policy.
 bets=d[(d["edge_multiple"]>=e)&(d["final_sp"]<=cap)].copy()
 bets["odds_band"]=pd.cut(bets["final_sp"],[1,3,5,8,12,20,50,np.inf],right=True)
 band=bets.groupby(["_year","odds_band"],observed=True).apply(lambda x:pd.Series(metrics(x))).reset_index()
 g.to_csv(DIR/"LAB245B3_2022_POLICY_GRID.csv",index=False); res.to_csv(OUT,index=False); band.to_csv(DIR/"LAB245B3_ODDS_BAND_STABILITY.csv",index=False)
 audit={"status":"SURVIVE_TO_MANUAL_LAB245B4_DISPATCH" if survive else "REJECT_FINAL_SP_POLICY",
        "policy_selected_on":"2022_ONLY","edge_threshold":e,"max_final_sp":cap,
        "minimum_2022_bets":MIN_BETS_2022,"minimum_confirmation_bets_each_year":MIN_BETS_CONFIRM,
        "confirmation_years":[2023,2024],"holdout_2025_2026_opened":False,
        "final_sp_forensic_only":True,"deployable_profitability_claim":False,
        "market_as_model_feature":False,"manual_holdout_dispatch_required":True}
 AUD.write_text(json.dumps(audit,indent=2),encoding="utf-8")
 print(res.to_string(index=False)); print(json.dumps(audit,indent=2))
if __name__=="__main__": main()
