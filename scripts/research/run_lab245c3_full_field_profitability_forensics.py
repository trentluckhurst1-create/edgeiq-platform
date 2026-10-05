from pathlib import Path
import os,json,hashlib
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]; DATA_ROOT=Path(os.environ.get("EDGEIQ_DATA_ROOT",str(ROOT))).resolve()
D=ROOT/"outputs/research/profitability_program/lab245b"
A2=D/"LAB245C2_FULL_FIELD_PROBABILITY_AUDIT.json"; PROB=D/"LAB245C2_FULL_FIELD_OOF_PROBABILITIES.csv"
OUT=D/"LAB245C3_FINAL_SP_POLICY_RESULTS.csv"; AUD=D/"LAB245C3_FINAL_SP_AUDIT.json"
SP_CANDIDATES=[DATA_ROOT/"outputs/research/profitability_program/compact/EDGEIQ_PROFITABILITY_COMPACT_RUNNERS.csv",DATA_ROOT/"outputs/research/model_price_diagnostics/lab166c/LAB166E_CORRECTED_PIT_PREDICTIONS.csv"]
POLICIES=[("EDGE_105",1.05),("EDGE_110",1.10),("EDGE_115",1.15),("EDGE_120",1.20)]

def load_sp():
 for p in SP_CANDIDATES:
  if p.exists():
   h=pd.read_csv(p,nrows=0).columns
   if {"_race","_horse","_sp"}.issubset(h):
    d=pd.read_csv(p,usecols=["_race","_horse","_sp"],low_memory=False)
    d["_race"]=d["_race"].astype("string").str.strip(); d["_horse"]=d["_horse"].astype("string").str.strip(); d["_sp"]=pd.to_numeric(d["_sp"],errors="coerce")
    d=d.dropna(); 
    if d.duplicated(["_race","_horse"]).any(): raise RuntimeError("duplicate SP identity")
    d=d[d._sp>1].copy(); return d,p
 raise FileNotFoundError("No governed final-SP source")

def metrics(x):
 x=x.sort_values(["race_date","_race","_horse"],kind="stable").copy(); n=len(x)
 if not n:return {"bets":0,"races_bet":0,"wins":0,"strike_pct":np.nan,"profit":0.0,"pot_pct":np.nan,"race_cluster_profit_z":np.nan,"max_drawdown_units":np.nan,"longest_losing_run":0,"mean_sp":np.nan,"mean_edge_ratio":np.nan}
 pnl=x.winner*x._sp-1.; eq=pnl.cumsum().to_numpy(); peak=np.maximum.accumulate(np.r_[0.,eq])[1:]; dd=eq-peak
 rp=pd.DataFrame({"r":x._race,"p":pnl}).groupby("r").p.sum(); z=(rp.mean()/(rp.std(ddof=1)/np.sqrt(len(rp)))) if len(rp)>1 and rp.std(ddof=1)>0 else np.nan
 losing=longest=0
 for w in x.winner.astype(int): losing=0 if w else losing+1; longest=max(longest,losing)
 return {"bets":n,"races_bet":int(x._race.nunique()),"wins":int(x.winner.sum()),"strike_pct":100*x.winner.mean(),"profit":float(pnl.sum()),"pot_pct":100*float(pnl.mean()),"race_cluster_profit_z":float(z),"max_drawdown_units":float(-dd.min()),"longest_losing_run":longest,"mean_sp":float(x._sp.mean()),"mean_edge_ratio":float(x.edge_ratio.mean())}

def main():
 a=json.loads(A2.read_text()); 
 if a.get("status")!="SURVIVE_TO_PROFITABILITY_FORENSICS": raise RuntimeError("LAB245C2 did not survive")
 ph=hashlib.sha256(PROB.read_bytes()).hexdigest()
 if ph!=a.get("probability_oof_sha256"): raise RuntimeError("probability lineage mismatch")
 p=pd.read_csv(PROB,low_memory=False)
 if not p._year.between(2022,2024).all(): raise RuntimeError("sealed-year breach")
 p["_race"]=p["_race"].astype("string").str.strip(); p["_horse"]=p["_horse"].astype("string").str.strip(); p["race_date"]=pd.to_datetime(p.race_date,errors="coerce")
 p["winner"]=(pd.to_numeric(p.target_finish_position,errors="coerce")==1).astype(int)
 sp,sp_path=load_sp(); d=p.merge(sp,on=["_race","_horse"],how="left",validate="one_to_one")
 total=int(d._race.nunique()); cov=d.groupby("_race").agg(n=("_horse","size"),s=("_sp",lambda z:z.notna().sum())); keep=set(cov.index[cov.n.eq(cov.s)])
 d=d[d._race.isin(keep)].copy(); covered=int(d._race.nunique()); print(f"FINAL_SP_COMPLETE_FIELDS={covered:,}/{total:,} ({100*covered/total:.2f}%)")
 if not covered: raise RuntimeError("No exact complete-field SP races")
 d["edge_ratio"]=d.p_model*d._sp
 rows=[]
 for name,e in POLICIES:
  for period,ys in [("YEAR_2022",[2022]),("YEAR_2023",[2023]),("DEV_2022_2023",[2022,2023]),("VALIDATION_2024",[2024])]:
   rows.append({"policy":name,"edge_min":e,"period":period,**metrics(d[d._year.isin(ys)&(d.edge_ratio>=e)])})
 r=pd.DataFrame(rows); r.to_csv(OUT,index=False); print(r.to_string(index=False))
 y22=r[r.period.eq("YEAR_2022")].copy()
 eligible=y22[(y22.bets>=50)&(y22.pot_pct>=2)&(y22.race_cluster_profit_z>=.5)].copy()
 selected=None; status="REJECT_NO_2022_SELECTION_POLICY"; band_profit={}; maxshare=None
 if len(eligible):
  eligible["score"]=eligible.pot_pct*(eligible.bets/(eligible.bets+200)); selected=str(eligible.sort_values(["score","bets"],ascending=False).iloc[0].policy)
  y23=r[(r.period=="YEAR_2023")&(r.policy==selected)].iloc[0]; pool=r[(r.period=="DEV_2022_2023")&(r.policy==selected)].iloc[0]
  e=dict(POLICIES)[selected]; db=d[d._year.isin([2022,2023])&(d.edge_ratio>=e)].copy(); db["pnl"]=db.winner*db._sp-1
  db["band"]=pd.cut(db._sp,[1,3,6,12,np.inf],right=False,labels=["1_3","3_6","6_12","12_PLUS"]); band_profit={str(k):float(v) for k,v in db.groupby("band",observed=True).pnl.sum().items()}
  pos=[max(0,v) for v in band_profit.values()]; maxshare=max(pos)/sum(pos) if sum(pos)>0 else 1.
  if y23.bets>=50 and y23.pot_pct>=1 and pool.bets>=150 and pool.pot_pct>=2 and pool.race_cluster_profit_z>=1 and maxshare<=.8:
   v=r[(r.period=="VALIDATION_2024")&(r.policy==selected)].iloc[0]; lim=max(25,.25*v.bets)
   status="SURVIVE_TO_OFFERED_PRICE_VALIDATION" if v.bets>=100 and v.pot_pct>=1 and v.race_cluster_profit_z>=.5 and v.max_drawdown_units<=lim else "REJECT_2024_POLICY_CONFIRMATION"
  else: status="REJECT_2023_POLICY_CONFIRMATION"
 audit={"contract_version":"LAB245C3_FINAL_SP_FORENSICS_V1","status":status,"selected_policy":selected,"selection_rule":"2022 only: >=50 bets, POT>=2%, race-cluster z>=0.5; maximize POT*n/(n+200), freeze thereafter","confirmation_rule":"2023 fixed policy >=50 bets POT>=1%; pooled 22-23 >=150 bets POT>=2% cluster-z>=1 and max positive SP-band share<=80%; then one 2024 confirmation","development_odds_band_profit":band_profit,"development_max_positive_profit_band_share":maxshare,"sp_source":str(sp_path),"probability_races_total":total,"complete_field_sp_races":covered,"sp_coverage_pct":100*covered/total,"final_sp_role":"FORENSIC_ONLY_NOT_DEPLOYABLE_OFFERED_PRICE","holdout_2025_2026_opened":False,"market_used_in_probability_model":False,"probability_oof_sha256":ph}
 AUD.write_text(json.dumps(audit,indent=2)); print(json.dumps(audit,indent=2))
if __name__=="__main__":main()
