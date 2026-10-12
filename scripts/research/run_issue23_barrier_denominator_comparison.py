"""Issue23: barrier denominator candidates using declared and active field counts.

Research-only: compare formulas; do not overwrite certified Stage011 barrier.
No market, outcomes, or historical data read.
"""
from pathlib import Path
import pandas as pd
import numpy as np
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
SRC=R/"outputs/research/model_v2/issue23_live_features/ISSUE23_BARRIER_CANDIDATES_V1.csv"
OUT=R/"outputs/research/model_v2/issue23_live_features/ISSUE23_BARRIER_DENOMINATOR_COMPARISON.csv"
def main():
 d=pd.read_csv(SRC,dtype={"race_id":"string","runner_id":"string"})
 if d.empty or d.duplicated(["race_date","race_id","runner_id"]).any():raise RuntimeError("STOP invalid identities")
 for c in ("active_status_confirmed","scratched","emergency"):
  s=d[c].astype("string").str.lower()
  if not s.isin(["true","false"]).all():raise RuntimeError("STOP unknown "+c)
  d[c]=s.eq("true")
 d["barrier_numeric"]=pd.to_numeric(d.barrier_numeric,errors="coerce")
 d["declared_field_size"]=d.groupby(["race_date","race_id"]).runner_id.transform("size")
 d["active_field_size"]=d.groupby(["race_date","race_id"]).active_status_confirmed.transform("sum")
 d["declared_field_pct_candidate"]=np.where(d.declared_field_size.gt(1),(d.barrier_numeric-1)/(d.declared_field_size-1),np.nan)
 d["active_field_pct_candidate"]=np.where(d.active_field_size.gt(1),(d.barrier_numeric-1)/(d.active_field_size-1),np.nan)
 d["barrier_exceeds_active_field"]=d.barrier_numeric.gt(d.active_field_size)
 d["barrier_exceeds_declared_field"]=d.barrier_numeric.gt(d.declared_field_size)
 d["status"]="COMPARISON_ONLY_NOT_CERTIFIED"
 if OUT.exists():raise RuntimeError("STOP immutable output exists")
 OUT.parent.mkdir(parents=True,exist_ok=True)
 d.to_csv(OUT,index=False)
 active=d[d.active_status_confirmed]
 print("ISSUE23 BARRIER DENOMINATOR COMPARISON")
 print("ACTIVE",len(active),"ABOVE_ACTIVE",int(active.barrier_exceeds_active_field.sum()),"ABOVE_DECLARED",int(active.barrier_exceeds_declared_field.sum()))
 print("ACTIVE_PCT_IN_0_1",int(active.active_field_pct_candidate.between(0,1).sum()))
 print("DECLARED_PCT_IN_0_1",int(active.declared_field_pct_candidate.between(0,1).sum()))
 print(active.groupby(["race_date","venue","race_no"]).agg(active=("runner_id","size"),declared=("declared_field_size","first"),above_active=("barrier_exceeds_active_field","sum"),above_declared=("barrier_exceeds_declared_field","sum")).to_string())
 print("OUTPUT",OUT)
 print("NOT_CERTIFIED; NO_SCORING; NO_OUTCOMES")
if __name__=="__main__":main()
