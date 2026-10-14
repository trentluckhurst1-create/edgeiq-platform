"""Issue23: reconstruct five exact Stage011 clean-finish features using pre-2025 history.

Uses PERF026 certified history, strictly earlier than target race, and excludes
ALL 2025/26 historical outcomes. Not a scoreable feature matrix.
"""
from pathlib import Path
import numpy as np
import pandas as pd
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
E=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
SRC=R/"outputs/research/model_v2/issue23_live_features/ISSUE23_DECLARATION_FEATURES_V1.csv"
H=E/"outputs/research/model_lab_026/edgeiq_certified_flat_walk_forward_epi_026.csv"
OUT=R/"outputs/research/model_v2/issue23_live_features/ISSUE23_CLEAN_FINISH_FEATURES_V1.csv"
COLS=["clean_finish_mean5","clean_last_finish","clean_last_won","clean_last_top3","clean_finish_hist_n"]
def main():
 d=pd.read_csv(SRC,dtype={"canonical_horse_id":"string","race_id":"string","runner_id":"string"})
 if d.empty or d.duplicated(["race_date","race_id","runner_id"]).any():raise RuntimeError("STOP invalid declaration identities")
 if not d.feature_status.eq("DECLARATION_JOIN_ONLY_DO_NOT_SCORE").all():raise RuntimeError("STOP unexpected input status")
 d["race_date"]=pd.to_datetime(d.race_date,errors="raise")
 if not d.race_date.dt.year.ge(2025).all():raise RuntimeError("STOP expected prospective dates")
 # Read only the exact identity, date and finish columns used in Stage011.
 parts=[]
 for q in pd.read_csv(H,usecols=["canonical_horse_id","race_date","finish_position"],dtype={"canonical_horse_id":"string","race_date":"string","finish_position":"string"},chunksize=250000):
  q["race_date"]=pd.to_datetime(q.race_date,errors="coerce")
  q=q[q.race_date.dt.year.le(2024)].copy()
  q=q[q.canonical_horse_id.isin(d.canonical_horse_id)].copy()
  if not q.empty:parts.append(q)
 h=pd.concat(parts,ignore_index=True) if parts else pd.DataFrame(columns=["canonical_horse_id","race_date","finish_position"])
 h["finish_position"]=pd.to_numeric(h.finish_position,errors="coerce")
 h=h.dropna(subset=["canonical_horse_id","race_date","finish_position"])
 h=h.sort_values(["canonical_horse_id","race_date"],kind="stable")
 byhorse={key:g for key,g in h.groupby("canonical_horse_id",sort=False)}
 values=[]
 for row in d.itertuples(index=False):
  g=byhorse.get(row.canonical_horse_id)
  q=np.array([],dtype=float) if g is None else g.loc[g.race_date.lt(row.race_date),"finish_position"].tail(5).to_numpy(float)
  values.append([float(q.mean()),float(q[-1]),float(q[-1]==1),float(q[-1]<=3),float(len(q))] if len(q) else [np.nan]*5)
 for i,c in enumerate(COLS):
  if d[c].notna().any():raise RuntimeError("STOP refusing to overwrite populated "+c)
  d[c]=[v[i] for v in values]
 d["feature_status"]="PARTIAL_CLEAN_FINISH_ONLY_DO_NOT_SCORE"
 OUT.parent.mkdir(parents=True,exist_ok=True)
 if OUT.exists():raise RuntimeError("STOP immutable output exists")
 d.to_csv(OUT,index=False)
 print("ISSUE23 CLEAN FINISH PIT BUILD")
 print("RUNNERS",len(d),"RACES",d[["race_date","race_id"]].drop_duplicates().shape[0])
 print("HISTORICAL_ROWS_USED",len(h))
 for c in COLS:print(c,"NON_NULL",int(d[c].notna().sum()))
 print("OUTPUT",OUT)
 print("NOT_SCOREABLE; NO_2025_2026_HISTORY; NO_MARKET; NO_MODEL_PREDICTIONS")
if __name__=="__main__":main()
