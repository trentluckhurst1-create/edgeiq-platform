from pathlib import Path
import os,json
import pandas as pd, numpy as np
ROOT=Path(__file__).resolve().parents[2]; DATA=Path(os.environ.get("EDGEIQ_DATA_ROOT",str(ROOT))).resolve()
PROB=ROOT/"outputs/research/profitability_program/lab245b/LAB245C2_FULL_FIELD_OOF_PROBABILITIES.csv"
OUT=ROOT/"outputs/research/profitability_program/lab245b/LAB245C3A_PRICE_UNIVERSE_AUDIT.csv"
DETAIL=ROOT/"outputs/research/profitability_program/lab245b/LAB245C3A_PROBABILITY_TAIL_AUDIT.csv"
def main():
 p=pd.read_csv(PROB,low_memory=False); p["_race"]=p._race.astype("string").str.strip(); p["_horse"]=p._horse.astype("string").str.strip()
 p["winner"]=(pd.to_numeric(p.target_finish_position,errors="coerce")==1).astype(int)
 roots=[DATA/"outputs",DATA/"data",DATA/"docs"]
 candidates=[]
 seen=set()
 for root in roots:
  if not root.exists(): continue
  for f in root.rglob("*.csv"):
   if f in seen: continue
   seen.add(f)
   try:
    h=pd.read_csv(f,nrows=0).columns.tolist()
   except Exception: continue
   lc={str(c).lower():c for c in h}
   race=lc.get("_race"); horse=lc.get("_horse")
   sp=next((lc[k] for k in ["_sp","sp","starting_price","startingprice","final_sp","bsp","win_sp"] if k in lc),None)
   if race and horse and sp:
    try:
     d=pd.read_csv(f,usecols=[race,horse,sp],low_memory=False)
     d=d.rename(columns={race:"_race",horse:"_horse",sp:"_sp"})
     d["_race"]=d._race.astype("string").str.strip(); d["_horse"]=d._horse.astype("string").str.strip(); d["_sp"]=pd.to_numeric(d._sp,errors="coerce")
     d=d.dropna(); d=d[d._sp>1]
     if d.duplicated(["_race","_horse"]).any(): continue
     m=p[["_race","_horse","_year"]].merge(d,on=["_race","_horse"],how="left")
     g=m.groupby("_race").agg(n=("_horse","size"),s=("_sp",lambda z:z.notna().sum()),year=("_year","first"))
     full=g[g.n.eq(g.s)]
     candidates.append({"path":str(f),"sp_column":sp,"source_rows":len(d),"matched_runner_rows":int(m._sp.notna().sum()),"complete_races":len(full),"complete_2022":int((full.year==2022).sum()),"complete_2023":int((full.year==2023).sum()),"complete_2024":int((full.year==2024).sum()),"race_coverage_pct":100*len(full)/p._race.nunique()})
    except Exception: continue
 r=pd.DataFrame(candidates).sort_values(["complete_races","matched_runner_rows"],ascending=False) if candidates else pd.DataFrame()
 r.to_csv(OUT,index=False); print("PRICE_SOURCES_FOUND",len(r)); print(r.head(30).to_string(index=False) if len(r) else "NONE")
 # Calibration tail diagnostic independent of market prices.
 bins=[0,.01,.02,.03,.05,.075,.10,.15,.20,.30,.50,1.01]
 p["p_band"]=pd.cut(p.p_model,bins,right=False)
 t=p.groupby("p_band",observed=True).agg(runners=("_horse","size"),wins=("winner","sum"),mean_p=("p_model","mean")).reset_index()
 t["actual_win_rate"]=t.wins/t.runners; t["calibration_ratio_actual_over_pred"]=t.actual_win_rate/t.mean_p
 t.to_csv(DETAIL,index=False); print("\nPROBABILITY_TAIL_CALIBRATION"); print(t.to_string(index=False))
if __name__=="__main__":main()
