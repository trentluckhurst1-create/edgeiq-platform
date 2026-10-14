"""Issue23: audit frozen 0.01 gate, uncertainty and pre-race selection integrity."""
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2")
PAIR=ROOT/"issue23_full_pairwise"
OUT=ROOT/"issue23_disagreement_gate"
THRESHOLD=.01
OUT.mkdir(parents=True,exist_ok=True)
rows=[]
for year in (2022,2023,2024):
 p=PAIR/f"ISSUE23_FULL_PAIRWISE_{year}.csv"
 d=pd.read_csv(p,dtype={"_race":str,"_horse":str})
 if d.duplicated(["_race","_horse"]).any():raise RuntimeError("STOP duplicate identity")
 for race,g in d.groupby("_race",sort=False):
  if int(g.y.sum())!=1:raise RuntimeError("STOP winner contract")
  a=g.sort_values(["p","_horse"],ascending=[False,True],kind="stable").reset_index(drop=True)
  b=g.sort_values(["challenger_score","_horse"],ascending=[False,True],kind="stable").reset_index(drop=True)
  top=a.iloc[0];alt=b.iloc[0]
  rank=int(np.flatnonzero(a._horse.to_numpy()==alt["_horse"])[0])+1
  lead=float(a.iloc[0].p-a.iloc[1].p)
  switch=bool(top["_horse"]!=alt["_horse"] and rank==2 and lead<=THRESHOLD)
  rows.append(dict(year=year,race=race,base_horse=top["_horse"],pair_horse=alt["_horse"],selected_horse=alt["_horse"] if switch else top["_horse"],base_correct=int(top.y),pair_correct=int(alt.y),gated_correct=int(alt.y if switch else top.y),switch=int(switch),stage011_top2_gap=lead,stage011_pair_rank=rank))
r=pd.DataFrame(rows)
for year,g in r.groupby("year"):
 delta=(g.gated_correct-g.base_correct).to_numpy(dtype=float)
 n=len(delta);gain=int(delta.sum());up=int((delta==1).sum());down=int((delta==-1).sum())
 se=np.std(delta,ddof=1)/np.sqrt(n)
 # Approximate paired race-level 95% interval; not independent validation.
 lo=100*(delta.mean()-1.96*se);hi=100*(delta.mean()+1.96*se)
 print(f"YEAR={year} RACES={n} BASE={g.base_correct.sum()} GATED={g.gated_correct.sum()} SWITCHES={g.switch.sum()} GAIN={gain:+d} CORRECTED={up} LOST={down} DELTA_PP={100*delta.mean():+.4f} APPROX_95CI_PP=[{lo:+.4f},{hi:+.4f}]",flush=True)
 if year==2024 and (n,int(g.base_correct.sum()),int(g.gated_correct.sum()),int(g.switch.sum()),up,down)!=(2402,552,567,140,36,21):raise RuntimeError("STOP frozen 2024 audit mismatch")
r.to_csv(OUT/"ISSUE23_FROZEN_GATE_RACE_AUDIT.csv",index=False)
print("FROZEN_GATE=pairwise top horse only if Stage011 rank=2 and Stage011 top2 p gap<=0.01")
print("AUDIT_PATH="+str(OUT/"ISSUE23_FROZEN_GATE_RACE_AUDIT.csv"))
print("NO_PROMOTION: reused development 2022-24; 2025-26 sealed")
