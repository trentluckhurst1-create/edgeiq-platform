"""Issue23: pre-race disagreement gate; develop 2022, confirm 2023, evaluate 2024."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2")
PAIR=ROOT/"issue23_full_pairwise"
OUT=ROOT/"issue23_disagreement_gate"
EXPECTED={2022:(612,138,108),2023:(2396,495,405),2024:(2402,552,495)}
print("ISSUE23 — PRE-RACE DISAGREEMENT GATE")
print("DEVELOP=2022 CONFIRM=2023 EVALUATE=2024; NO MARKET; NO 2025-26",flush=True)

def prepare(year):
 path=PAIR/f"ISSUE23_FULL_PAIRWISE_{year}.csv"
 if not path.is_file():raise RuntimeError(f"STOP missing challenger: {path}")
 d=pd.read_csv(path,dtype={"_race":str,"_horse":str})
 needed={"_race","_horse","y","p","challenger_score"}
 if not needed.issubset(d.columns):raise RuntimeError("STOP missing required columns")
 if d.duplicated(["_race","_horse"]).any():raise RuntimeError("STOP duplicate identity")
 if d[list(needed-{"_race","_horse"})].isna().any().any():raise RuntimeError("STOP missing model fields")
 records=[]
 for race,g in d.groupby("_race",sort=False):
  if int(g.y.sum())!=1:raise RuntimeError("STOP invalid winner")
  a=g.sort_values(["p","_horse"],ascending=[False,True],kind="stable")
  b=g.sort_values(["challenger_score","_horse"],ascending=[False,True],kind="stable")
  ca=a.iloc[0];cb=b.iloc[0]
  lead=float(ca.p-a.iloc[1].p)
  pairlead=float(cb.challenger_score-b.iloc[1].challenger_score)
  # All gating inputs are model predictions, available before the race.
  rank=int(np.flatnonzero(a["_horse"].to_numpy()==cb["_horse"])[0])+1
  records.append(dict(race=race,base_horse=ca["_horse"],pair_horse=cb["_horse"],base_correct=int(ca.y),pair_correct=int(cb.y),different=int(ca["_horse"]!=cb["_horse"]),base_lead=lead,pair_lead=pairlead,pair_stage011_rank=rank))
 t=pd.DataFrame(records)
 e=EXPECTED[year]
 if (len(t),int(t.base_correct.sum()),int(t.pair_correct.sum()))!=e:raise RuntimeError("STOP population/baseline drift")
 print(f"YEAR={year} RACES={len(t)} BASE={t.base_correct.sum()} PAIRWISE={t.pair_correct.sum()} DISAGREEMENTS={t.different.sum()}",flush=True)
 return t

d={y:prepare(y) for y in EXPECTED}
# Predeclared gate family: only switch if Stage011 ranks challenger 2nd and
# Stage011's top-two probability lead is low. One threshold selected in 2022,
# with 2023 confirmation required before the 2024 evaluation.
thresholds=(0.01,0.02,0.03,0.05,0.08,0.12)
def report(t,thr):
 switch=(t.different.eq(1)&t.pair_stage011_rank.eq(2)&t.base_lead.le(thr))
 up=int((switch&t.pair_correct.eq(1)&t.base_correct.eq(0)).sum())
 down=int((switch&t.pair_correct.eq(0)&t.base_correct.eq(1)).sum())
 return int(switch.sum()),up,down,up-down

print("DEVELOPMENT_2022")
for thr in thresholds:
 n,up,down,delta=report(d[2022],thr)
 print(f"THRESHOLD={thr:.2f} SWITCHES={n} CORRECTED={up} LOST={down} NET={delta:+d}")
# Selection from 2022 alone, conservative tie-break toward fewer switches.
chosen=max(thresholds,key=lambda th:(report(d[2022],th)[3],-report(d[2022],th)[0],-th))
print(f"FROZEN_THRESHOLD={chosen:.2f}",flush=True)
n23,u23,l23,delta23=report(d[2023],chosen)
print(f"CONFIRM_2023 SWITCHES={n23} CORRECTED={u23} LOST={l23} NET={delta23:+d}")
if delta23<=0:
 print("STOP_GATE_REJECTED_ON_2023; 2024 NOT USED FOR GATE EVALUATION",flush=True)
else:
 n24,u24,l24,delta24=report(d[2024],chosen)
 print(f"EVALUATE_2024 SWITCHES={n24} CORRECTED={u24} LOST={l24} NET={delta24:+d} BASE_HITS=552 GATED_HITS={552+delta24} DELTA_PP={100*delta24/2402:+.4f}",flush=True)
 print("NO_PROMOTION: 2022-24 REUSED DEVELOPMENT; 2025-26 SEALED",flush=True)
