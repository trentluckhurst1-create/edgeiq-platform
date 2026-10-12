"""Issue23: diagnose barrier denominator and inspect LAB245B schema in one pass.

No historical outcomes loaded: reads only CSV header of performance bridge.
"""
from pathlib import Path
import pandas as pd
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
SRC=R/"outputs/research/model_v2/issue23_live_features/ISSUE23_BARRIER_CANDIDATES_V1.csv"
BR=R/"outputs/research/profitability_program/lab245b/LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"
def main():
 d=pd.read_csv(SRC,dtype={"race_id":"string","runner_id":"string"})
 if d.empty:raise RuntimeError("STOP empty input")
 for c in ["active_status_confirmed","barrier_candidate_valid"]:
  d[c]=d[c].astype("string").str.lower().eq("true")
 bad=d[d.active_status_confirmed & ~d.barrier_candidate_valid].copy()
 print("ISSUE23 BARRIER DENOMINATOR DIAGNOSTIC")
 print("INVALID_ACTIVE",len(bad))
 print(bad[["race_date","venue","race_no","race_id","runner_id","horse_name","barrier_numeric","active_field_size_candidate","barrier_pct_candidate"]].to_string(index=False))
 print("ABOVE_ACTIVE_FIELD_SIZE",int((bad.barrier_numeric>bad.active_field_size_candidate).sum()))
 print("BARRIER_MISSING",int(bad.barrier_numeric.isna().sum()))
 print("BARRIER_NONPOSITIVE",int(bad.barrier_numeric.le(0).sum()))
 print("LAB245B_SOURCE",BR,"EXISTS",BR.exists())
 if BR.exists():
  columns=pd.read_csv(BR,nrows=0).columns.tolist()
  print("LAB245B_COLUMNS",columns)
  print("HISTORICAL_OUTCOMES_NOT_LOADED; SCHEMA_ONLY")
 print("NO_SCORING; NO_2025_2026_OUTCOMES_READ")
if __name__=="__main__":main()
