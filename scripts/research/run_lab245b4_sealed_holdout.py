from pathlib import Path
import os
import json, math
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error

ROOT=Path(__file__).resolve().parents[2]
DATA_ROOT=Path(os.environ.get("EDGEIQ_DATA_ROOT",str(ROOT))).resolve()
DIR=ROOT/"outputs/research/profitability_program/lab245b"
PIT=DIR/"LAB245B_WAREHOUSE_RUNNER_LVS.csv"
AUTHORITY=ROOT/"docs/performance-intelligence/lengths-v-standard/edgeiq_runner_lengths_v_standard_fact_v1.csv"
WAREHOUSE=ROOT/"docs/performance-intelligence/warehouse/edgeiq_performance_fact_warehouse_v1.csv"
TRAIN=DIR/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
B1=DIR/"LAB245B1_AUDIT.json"; B2=DIR/"LAB245B2_AUDIT.json"; B3=DIR/"LAB245B3_AUDIT.json"
OUT=DIR/"LAB245B4_HOLDOUT_RESULTS.json"
FEATURES=["hist_runs","current_distance","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_worst5","margin_std5","finishpos_mean5","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best"]
POLICIES={"EDGE_105":(1.05,0,999),"EDGE_110":(1.10,0,999),"EDGE_115":(1.15,0,999),"EDGE_120":(1.20,0,999)}
SP_CANDIDATES=[DATA_ROOT/"outputs/research/profitability_program/compact/EDGEIQ_PROFITABILITY_COMPACT_RUNNERS.csv",DATA_ROOT/"outputs/research/model_price_diagnostics/lab166c/LAB166E_CORRECTED_PIT_PREDICTIONS.csv"]

def stats(a,n):
 x=np.asarray(a[-n:],float); x=x[np.isfinite(x)]
 return (float(x.mean()),float(np.median(x)),float(x.std())) if len(x) else (np.nan,np.nan,np.nan)

def build_holdout():
 d=pd.read_csv(PIT,usecols=["canonical_race_id","canonical_horse_id","race_date","distance_metres","finish_position","finish_margin","runner_lvs"],low_memory=False)
 d["canonical_race_id"]=d["canonical_race_id"].astype("string").str.strip(); d["canonical_horse_id"]=d["canonical_horse_id"].astype("string").str.strip()
 d["race_date"]=pd.to_datetime(d.race_date,errors="coerce")
 for c in ["distance_metres","finish_position","finish_margin","runner_lvs"]: d[c]=pd.to_numeric(d[c],errors="coerce")
 d=d.dropna(subset=["canonical_race_id","canonical_horse_id","race_date"]).sort_values(["canonical_horse_id","race_date","canonical_race_id"],kind="stable")
 field_sizes=d.groupby("canonical_race_id")["canonical_horse_id"].nunique().to_dict()
 rows=[]
 for horse,g in d.groupby("canonical_horse_id",sort=False):
  hist=[]
  for dt,day in g.groupby("race_date",sort=True):
   lvs=[x["lvs"] for x in hist if np.isfinite(x["lvs"])]; mar=[x["margin"] for x in hist if np.isfinite(x["margin"])]; pos=[x["pos"] for x in hist if np.isfinite(x["pos"])]; dates=[x["date"] for x in hist]
   l3=stats(lvs,3); l5=stats(lvs,5); m5=stats(mar,5); p5=stats(pos,5)
   for _,r in day.iterrows():
    if dt.year in [2025,2026]:
     rec={"_race":r.canonical_race_id,"_horse":horse,"_year":int(dt.year),"race_date":dt,"target_lvs":r.runner_lvs,"target_finish_position":r.finish_position,"target_field_size":field_sizes.get(r.canonical_race_id,np.nan),"current_distance":r.distance_metres,"hist_runs":len(hist),
     "lvs_last1":lvs[-1] if lvs else np.nan,"lvs_mean3":l3[0],"lvs_mean5":l5[0],"lvs_median5":l5[1],"lvs_std5":l5[2],"lvs_peak":max(lvs) if lvs else np.nan,"lvs_worst5":min(lvs[-5:]) if lvs else np.nan,
     "margin_mean5":m5[0],"margin_std5":m5[2],"margin_worst5":max(mar[-5:]) if mar else np.nan,"finishpos_mean5":p5[0],"days_since_last":(dt-max(dates)).days if dates else np.nan}
     near=[x for x in hist if np.isfinite(x["distance"]) and pd.notna(r.distance_metres) and abs(x["distance"]-r.distance_metres)<=200]; nl=[x["lvs"] for x in near if np.isfinite(x["lvs"])]
     rec.update({"dist200_runs":len(near),"dist200_lvs_mean":float(np.mean(nl)) if nl else np.nan,"dist200_lvs_best":max(nl) if nl else np.nan}); rows.append(rec)
   for _,r in day.iterrows(): hist.append({"date":dt,"distance":float(r.distance_metres) if pd.notna(r.distance_metres) else np.nan,"pos":float(r.finish_position) if pd.notna(r.finish_position) else np.nan,"margin":float(r.finish_margin) if pd.notna(r.finish_margin) else np.nan,"lvs":float(r.runner_lvs) if pd.notna(r.runner_lvs) else np.nan})
 return pd.DataFrame(rows)

def load_sp():
 for p in SP_CANDIDATES:
  if p.exists() and {"_race","_horse","_sp"}.issubset(pd.read_csv(p,nrows=0).columns):
   s=pd.read_csv(p,usecols=["_race","_horse","_sp"],low_memory=False); s["_sp"]=pd.to_numeric(s["_sp"],errors="coerce")
   s["_race"]=s["_race"].astype("string").str.strip(); s["_horse"]=s["_horse"].astype("string").str.strip(); s=s.dropna(subset=["_race","_horse","_sp"])
   if s.duplicated(["_race","_horse"]).any(): raise RuntimeError(f"Duplicate SP keys in {p}")
   if s["_sp"].le(1).any(): raise RuntimeError(f"Invalid SP values in {p}")
   return s,str(p)
 raise FileNotFoundError("Final-SP evaluation source missing")

def main():
 a1=json.loads(B1.read_text()); a2=json.loads(B2.read_text()); a3=json.loads(B3.read_text())
 if a3.get("status")!="SURVIVE_TO_FORENSIC_HOLDOUT":
  x={"status":"HOLDOUT_REMAINS_SEALED","b3_status":a3.get("status")}; OUT.write_text(json.dumps(x,indent=2)); print(json.dumps(x,indent=2)); return
 tr=pd.read_csv(TRAIN,low_memory=False)
 if not pd.to_numeric(tr["_year"],errors="coerce").between(2021,2024).all(): raise RuntimeError("Final refit contamination: training bridge contains sealed years")
 tr=tr[(tr.target_lvs.notna())&(tr.hist_runs>=3)&np.isfinite(pd.to_numeric(tr.lvs_mean3,errors="coerce"))].copy()
 ho=build_holdout()
 if len(ho) and not pd.to_numeric(ho["_year"],errors="coerce").isin([2025,2026]).all(): raise RuntimeError("Holdout construction contains non-holdout years")
 ho=ho[(ho.target_lvs.notna())&(ho.hist_runs>=3)&np.isfinite(pd.to_numeric(ho.lvs_mean3,errors="coerce"))].copy()
 eligible_counts=ho.groupby("_race")["_horse"].transform("nunique")
 ho=ho[eligible_counts.eq(pd.to_numeric(ho["target_field_size"],errors="coerce"))].copy()
 if ho.empty: raise RuntimeError("No complete-field holdout races after experience gate")
 winner_counts=ho.assign(_winner=pd.to_numeric(ho["target_finish_position"],errors="coerce").eq(1)).groupby("_race")["_winner"].sum()
 bad_winners=winner_counts[winner_counts.ne(1)]
 if len(bad_winners): raise RuntimeError(f"Holdout winner-integrity failure races={len(bad_winners)}")
 for c in FEATURES+["target_lvs"]: tr[c]=pd.to_numeric(tr[c],errors="coerce"); ho[c]=pd.to_numeric(ho[c],errors="coerce")
 model=str(a1["dev_selected_ml"]["model"])
 if model=="RIDGE": m=make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),Ridge(alpha=10.0))
 elif model=="HGB": m=HistGradientBoostingRegressor(max_iter=250,learning_rate=.04,max_leaf_nodes=15,l2_regularization=5,random_state=245)
 else: raise RuntimeError(f"Unknown frozen model {model}")
 m.fit(tr[FEATURES],tr.target_lvs); ho["pred_lvs"]=m.predict(ho[FEATURES])
 temp=float(a2["fixed_temperatures"][model]); probs=[]
 for race,g in ho.groupby("_race",sort=False):
  z=(g.pred_lvs.to_numpy(float)-g.pred_lvs.max())/temp; e=np.exp(np.clip(z,-50,50)); probs.extend(zip(g.index,(e/e.sum()).tolist()))
 ho["p_model"]=np.nan
 for i,p in probs: ho.loc[i,"p_model"]=p
 perf={}
 for y,g in ho.groupby("_year"):
  perf[str(int(y))]={"rows":int(len(g)),"races":int(g._race.nunique()),"mae":float(mean_absolute_error(g.target_lvs,g.pred_lvs)),"rmse":float(math.sqrt(mean_squared_error(g.target_lvs,g.pred_lvs)))}
  wins=g[g.target_finish_position==1]
  perf[str(int(y))]["race_winner_log_loss"]=float((-np.log(wins.p_model.clip(lower=1e-15))).mean())
 sp,sp_path=load_sp(); x=ho.merge(sp,on=["_race","_horse"],how="inner",validate="one_to_one")
 if len(x)!=len(ho): raise RuntimeError(f"Holdout SP coverage incomplete {len(x)}/{len(ho)}")
 edge,pmin,spmax=POLICIES[a3["selected_policy"]]; x["edge_ratio"]=x.p_model*x._sp
 bets=x[(x.edge_ratio>=edge)&(x.p_model>=pmin)&(x._sp<=spmax)].copy(); bets["winner"]=(bets.target_finish_position==1).astype(int); bets["pnl"]=bets.winner*bets._sp-1
 econ={}
 for y,g in bets.groupby("_year"):
  econ[str(int(y))]={"bets":int(len(g)),"wins":int(g.winner.sum()),"profit":float(g.pnl.sum()),"pot_pct":100*float(g.pnl.sum())/len(g) if len(g) else np.nan}
 bets=bets.sort_values(["race_date","_race","_horse"],kind="stable")
 eq=bets["pnl"].cumsum().to_numpy(float); peak=np.maximum.accumulate(np.r_[0.0,eq])[1:] if len(eq) else np.array([]); dd=eq-peak if len(eq) else np.array([])
 losing=0; longest=0
 for w in bets["winner"].astype(int).tolist():
  losing=0 if w else losing+1; longest=max(longest,losing)
 total={"bets":int(len(bets)),"wins":int(bets.winner.sum()),"profit":float(bets.pnl.sum()),"pot_pct":100*float(bets.pnl.sum())/len(bets) if len(bets) else np.nan,"max_drawdown_units":float(-dd.min()) if len(dd) else np.nan,"longest_losing_run":int(longest),"mean_sp":float(bets["_sp"].mean()) if len(bets) else np.nan,"mean_edge_ratio":float(bets["edge_ratio"].mean()) if len(bets) else np.nan}
 out={"status":"FORENSIC_HOLDOUT_OPENED","model":model,"temperature":temp,"policy":a3["selected_policy"],"performance_by_year":perf,"betting_by_year":econ,"betting_total":total,"sp_source":sp_path,
 "purity_limitation":"Final SP is historical forensic pricing, not deployable offered odds.","reselection_after_holdout":False}
 OUT.write_text(json.dumps(out,indent=2,default=str)); print(json.dumps(out,indent=2,default=str))

if __name__=="__main__": main()
