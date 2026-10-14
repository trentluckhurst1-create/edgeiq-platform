"""Issue23: governed declaration barrier candidate and race-level field status.

No scoring. Retains full declared population; only active/nonemergency runner
barrier percentiles with complete, unambiguous status are computed. Values are
candidates pending exact D45 denominator equivalence confirmation.
"""
from pathlib import Path
import numpy as np
import pandas as pd
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
SRC=R/"outputs/research/model_v2/issue23_live_features/ISSUE23_CLEAN_FINISH_FEATURES_V1.csv"
OUT=R/"outputs/research/model_v2/issue23_live_features/ISSUE23_BARRIER_CANDIDATES_V1.csv"
RACE=R/"outputs/research/model_v2/issue23_live_features/ISSUE23_BARRIER_RACE_GATE_V1.csv"
def main():
 d=pd.read_csv(SRC,dtype={"race_id":"string","runner_id":"string","canonical_horse_id":"string"})
 if d.empty or d.duplicated(["race_date","race_id","runner_id"]).any():raise RuntimeError("STOP duplicate entries")
 if not d.feature_status.eq("PARTIAL_CLEAN_FINISH_ONLY_DO_NOT_SCORE").all():raise RuntimeError("STOP unexpected input")
 if not {"scratched","emergency","barrier_numeric","active_status_confirmed"}.issubset(d):raise RuntimeError("STOP missing declarations")
 for c in ["scratched","emergency","active_status_confirmed"]:
  v=d[c].astype("string").str.lower()
  if not v.isin(["true","false"]).all():raise RuntimeError("STOP unknown "+c)
  d[c]=v.eq("true")
 if not d.active_status_confirmed.eq(~d.scratched & ~d.emergency).all():raise RuntimeError("STOP status inconsistency")
 d["barrier_numeric"]=pd.to_numeric(d.barrier_numeric,errors="coerce")
 active=d.active_status_confirmed
 d["active_field_size_candidate"]=d.assign(_active=active.astype(int)).groupby(["race_date","race_id"])._active.transform("sum")
 d["barrier_pct_candidate"]=np.nan
 valid=active & d.barrier_numeric.notna() & d.active_field_size_candidate.gt(1)
 d.loc[valid,"barrier_pct_candidate"]=(d.loc[valid,"barrier_numeric"]-1)/(d.loc[valid,"active_field_size_candidate"]-1)
 # Do not promote raw barrier into Stage011 without evidence that D45 used this denominator.
 d["barrier_candidate_valid"]=valid & d.barrier_pct_candidate.between(0,1)
 d["feature_status"]="PARTIAL_HISTORY_BARRIER_CANDIDATE_DO_NOT_SCORE"
 g=d.groupby(["race_date","race_id"],dropna=False)
 race=g.agg(declared=("runner_id","size"),active=("active_status_confirmed","sum"),barrier_candidates=("barrier_candidate_valid","sum"),scratched=("scratched","sum"),emergencies=("emergency","sum")).reset_index()
 race["barrier_coverage_complete"]=race.active.eq(race.barrier_candidates)
 for path in (OUT,RACE):
  if path.exists():raise RuntimeError("STOP immutable output already exists "+str(path))
 OUT.parent.mkdir(parents=True,exist_ok=True)
 d.to_csv(OUT,index=False);race.to_csv(RACE,index=False)
 print("ISSUE23 BARRIER CANDIDATE BUILD")
 print("RUNNERS",len(d),"RACES",len(race),"ACTIVE",int(active.sum()),"VALID_CANDIDATES",int(d.barrier_candidate_valid.sum()))
 print(race.to_string(index=False))
 print("OUTPUT",OUT)
 print("BARRIER_NOT_CERTIFIED; STAGE011_FEATURE_NOT_OVERWRITTEN; NO_SCORING; NO_MARKET; NO_OUTCOMES")
if __name__=="__main__":main()
