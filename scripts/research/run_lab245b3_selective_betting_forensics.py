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
CONTRACT=ROOT/"scripts/research/LAB245B_B3_SELECTIVE_BETTING_PREDECLARED.json"

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
 losing=0; longest=0
 for w in x["winner"].astype(int).tolist():
  losing=0 if w else losing+1
  longest=max(longest,losing)
 mean_pnl=float(pnl.mean()) if bets else np.nan
 sd_pnl=float(pnl.std(ddof=1)) if bets>1 else np.nan
 se_pnl=sd_pnl/np.sqrt(bets) if bets>1 and np.isfinite(sd_pnl) and sd_pnl>0 else np.nan
 profit_z=mean_pnl/se_pnl if np.isfinite(se_pnl) and se_pnl>0 else np.nan
 race_count=int(x["_race"].nunique()) if bets else 0
 max_bets_per_race=int(x.groupby("_race").size().max()) if bets else 0
 multi_bet_race_pct=100.0*float((x.groupby("_race").size()>1).mean()) if bets else np.nan
 return {"bets":bets,"races_bet":race_count,"bets_per_race":bets/race_count if race_count else np.nan,"max_bets_per_race":max_bets_per_race,"multi_bet_race_pct":multi_bet_race_pct,"wins":wins,"strike_pct":100*wins/bets if bets else np.nan,
         "profit":float(pnl.sum()),"pot_pct":100*float(pnl.sum())/bets if bets else np.nan,
         "mean_profit_per_bet":mean_pnl,"profit_se_per_bet":se_pnl,"profit_z":profit_z,"race_cluster_profit_z":race_cluster_profit_z,
         "max_drawdown_units":float(-dd.min()) if bets else np.nan,"longest_losing_run":int(longest),
         "mean_sp":float(x["_sp"].mean()) if bets else np.nan,
         "mean_edge_ratio":float(x["edge_ratio"].mean()) if bets else np.nan}

def apply(d,edge,pmin,spmax):
 return d[(d.edge_ratio>=edge)&(d.p_model>=pmin)&(d._sp<=spmax)].copy()

def main():
 if not B2.exists() or not PROB.exists(): raise FileNotFoundError("LAB245B2 outputs missing")
 if not CONTRACT.exists(): raise FileNotFoundError(CONTRACT)
 contract=json.loads(CONTRACT.read_text(encoding="utf-8"))
 expected_deltas=[round(e-1.0,10) for _,e,_,_ in POLICIES]
 declared_deltas=[round(float(x),10) for x in contract.get("candidate_edge_thresholds",[])]
 if declared_deltas!=expected_deltas: raise RuntimeError(f"LAB245B3 policy contract drift: declared edge deltas={declared_deltas} expected={expected_deltas}")
 if contract.get("development")!=[2022,2023] or contract.get("confirmation")!=2024 or contract.get("sealed")!=[2025,2026]: raise RuntimeError("LAB245B3 temporal contract drift")
 if contract.get("market_as_model_feature")!="NO": raise RuntimeError("LAB245B3 market-feature contract drift")
 b2=json.loads(B2.read_text(encoding="utf-8"))
 if b2.get("status")!="SURVIVE_TO_LAB245B3":
  a={"status":"SKIPPED_B2_REJECTED","b2_status":b2.get("status"),"holdout_2025_2026_opened":False}
  AUD.write_text(json.dumps(a,indent=2),encoding="utf-8"); print(json.dumps(a,indent=2)); return
 p=pd.read_csv(PROB,low_memory=False)
 ml=str(b2["selected_ml"]); p=p[p.model==ml].copy()
 if not p["_year"].between(2022,2024).all(): raise RuntimeError("Sealed-year breach")
 p["race_date"]=pd.to_datetime(p["race_date"],errors="coerce")
 sp,sp_path=load_sp()
 d=p.merge(sp,on=["_race","_horse"],how="left",validate="one_to_one")
 total_prob_races=int(d["_race"].nunique())
 race_cov=d.groupby("_race").agg(rows=("_horse","size"),sp_rows=("_sp",lambda s:int(s.notna().sum())))
 covered=set(race_cov.index[race_cov["rows"].eq(race_cov["sp_rows"])])
 d=d[d["_race"].isin(covered)].copy()
 if d.empty: raise RuntimeError("No complete-field exact-identity final-SP races; fuzzy matching prohibited")
 market_covered_races=int(d["_race"].nunique())
 market_coverage_pct=100.0*market_covered_races/total_prob_races if total_prob_races else 0.0
 print(f"FINAL_SP_UNIVERSE=EXACT_IDENTITY_COMPLETE_FIELD_INTERSECTION RACES={market_covered_races:,}/{total_prob_races:,} COVERAGE_PCT={market_coverage_pct:.3f}")
 d["edge_ratio"]=d["p_model"]*d["_sp"]
 rows=[]
 for name,e,pm,sm in POLICIES:
  for period,years in [("DEV_2022_2023",[2022,2023]),("YEAR_2022",[2022]),("YEAR_2023",[2023]),("VALIDATION_2024",[2024])]:
   x=apply(d[d["_year"].isin(years)],e,pm,sm)
   rows.append({"policy":name,"edge_min":e,"p_min":pm,"sp_max":sm,"period":period,**metrics(x)})
 r=pd.DataFrame(rows); r.to_csv(OUT,index=False)
 y22=r[r.period=="YEAR_2022"].copy(); y23=r[r.period=="YEAR_2023"].set_index("policy"); pooled=r[r.period=="DEV_2022_2023"].set_index("policy")
 # Temporal policy ladder: select once on 2022, then freeze for 2023 and 2024.
 eligible22=y22[(y22.bets>=50)&(y22.pot_pct>=2.0)&(y22.race_cluster_profit_z>=0.5)].copy()
 if eligible22.empty:
  status="REJECT_NO_2022_SELECTION_POLICY"; selected=None
 else:
  # Conservative 2022-only score; no 2023/2024 information enters policy selection.
  eligible22["selection_score"]=eligible22["pot_pct"]*(eligible22["bets"]/(eligible22["bets"]+200.0))
  selected=str(eligible22.sort_values(["selection_score","bets"],ascending=[False,False]).iloc[0].policy)
  c23=y23.loc[selected]; cp=pooled.loc[selected]
  # Stability-only odds-band concentration check on pooled development for the already-frozen policy.
  pe,ppm,psm=next((e,pm,sm) for n,e,pm,sm in POLICIES if n==selected)
  devbets=apply(d[d["_year"].isin([2022,2023])],pe,ppm,psm).copy()
  devbets["pnl"]=devbets["winner"]*devbets["_sp"]-1.0
  devbets["sp_band"]=pd.cut(devbets["_sp"],bins=[1.0,3.0,6.0,12.0,np.inf],right=False,labels=["1_3","3_6","6_12","12_PLUS"])
  band_profit=devbets.groupby("sp_band",observed=True)["pnl"].sum().to_dict()
  positive_parts=[max(0.0,float(v)) for v in band_profit.values()]; positive_total=sum(positive_parts)
  max_positive_share=(max(positive_parts)/positive_total) if positive_total>0 else 1.0
  odds_band_ok=max_positive_share<=0.80
  if not (c23.bets>=50 and c23.pot_pct>=1.0 and cp.bets>=150 and cp.pot_pct>=2.0 and cp.race_cluster_profit_z>=1.0 and odds_band_ok):
   status="REJECT_2023_POLICY_CONFIRMATION"
  else:
   v=r[(r.period=="VALIDATION_2024")&(r.policy==selected)].iloc[0]
   dd_limit=max(25.0,0.25*float(v.bets))
   status="SURVIVE_TO_FORENSIC_HOLDOUT" if v.bets>=100 and v.pot_pct>=1.0 and v.race_cluster_profit_z>=0.5 and v.max_drawdown_units<=dd_limit else "REJECT_2024_POLICY_CONFIRMATION"
 a={"contract_version":"LAB245B3_PREDECLARED_FINAL_SP_FORENSICS_V1","status":status,"selected_policy":selected,"policy_family_size":len(POLICIES),"policy_contract":"LAB245B_B3_SELECTIVE_BETTING_PREDECLARED.json edge thresholds 0.05/0.10/0.15/0.20",
    "selection":"2022 only; >=50 bets, POT>=2%, race-clustered profit_z>=0.5; choose highest POT shrunk toward zero by n/(n+200), then freeze policy",
    "development_confirmation":"fixed policy 2023 requires >=50 bets and POT>=1%; pooled 2022-23 requires >=150 bets, POT>=2%, race-clustered profit_z>=1.0, and no single SP band >80% of positive gross profit",
    "development_odds_band_profit":band_profit if selected else {},"development_max_positive_profit_band_share":max_positive_share if selected else None,
    "validation":"same fixed policy 2024 requires >=100 bets, POT>=1%, race-clustered profit_z>=0.5, and max drawdown <= max(25 units, 25% of bets)",
    "exposure_diagnostics":"reports races_bet, bets_per_race, max_bets_per_race and multi_bet_race_pct; multiple bets in one race remain correlated exposure and are not treated as independent evidence",
    "sp_source":str(sp_path),"final_sp_probability_races_total":total_prob_races,"final_sp_complete_field_races":market_covered_races,"final_sp_race_coverage_pct":market_coverage_pct,"final_sp_role":"HISTORICAL_POLICY_SELECTION_AND_FORENSICS_ONLY",
    "deployability_limitation":"Final SP is not a deployable offered price. Any surviving policy requires validation on actual pre-race offered odds.",
    "holdout_2025_2026_opened":False,"market_used_in_probability_model":False}
 AUD.write_text(json.dumps(a,indent=2),encoding="utf-8")
 print(r.to_string(index=False)); print(json.dumps(a,indent=2))

if __name__=="__main__": main()
