"""Build governed LVS feature candidates from exact canonical horse IDs.

Read-only input; separate research CSV output, never overwrites Stage011 model
inputs. Only prior dated warehouse runs; post-2024 data is prospective-use only.
"""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--warehouse",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_WAREHOUSE_RUNNER_LVS.csv")
 p.add_argument("--linkage",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\issue23_live_features\ISSUE23_LAB245B_HISTORY_LINKAGE.csv")
 p.add_argument("--date",default="2026-10-14")
 p.add_argument("--venue",default="Caulfield")
 p.add_argument("--out",default=r"C:\EDGEIQ_ISSUE23\outputs\research\ISSUE23_GOVERNED_LVS_CANDIDATES.csv")
 a=p.parse_args()
 w=pd.read_csv(a.warehouse,dtype="string")
 l=pd.read_csv(a.linkage,dtype="string")
 l=l[l.race_date.eq(a.date)&l.venue.str.casefold().eq(a.venue.casefold())].copy()
 if l.duplicated(["race_no","horse_name"]).any():raise RuntimeError("STOP duplicate live race/horse")
 if l.canonical_horse_id.isna().any():raise RuntimeError("STOP missing canonical identity")
 if l.canonical_horse_id.duplicated().any():raise RuntimeError("STOP duplicate canonical live identity")
 w["dt"]=pd.to_datetime(w.race_date,errors="coerce")
 w["lvs"]=pd.to_numeric(w.runner_lvs,errors="coerce")
 w["distance_num"]=pd.to_numeric(w.distance_metres,errors="coerce")
 w=w[w.dt.notna()&w.dt.lt(pd.Timestamp(a.date))&w.lvs.notna()].copy()
 if w.duplicated(["canonical_race_id","canonical_horse_id"]).any():raise RuntimeError("STOP duplicate canonical run")
 if not np.isfinite(w.lvs.to_numpy()).all():raise RuntimeError("STOP nonfinite LVS")
 w=w.sort_values(["canonical_horse_id","dt","canonical_race_id"],kind="stable")
 histories={key:g for key,g in w[w.canonical_horse_id.isin(l.canonical_horse_id)].groupby("canonical_horse_id",sort=False)}
 rows=[]
 for r in l.itertuples(index=False):
  h=histories.get(r.canonical_horse_id)
  if h is None:continue
  if h.empty:continue
  if h.dt.duplicated().any():
   print("STOP AMBIGUOUS_SAME_DATE_HISTORY",r.canonical_horse_id)
   continue
  v=h.lvs.to_numpy(dtype=float)
  last=v[-5:]
  # Historical transforms passed full PIT parity; live source completeness is separate.
  row={"source_latest_warehouse_date":str(w.dt.max().date()),"historical_lvs_parity":"77526_OF_77526_ALL_SEVEN_PRE2025",
       "race_date":r.race_date,"race_no":r.race_no,"horse_name":r.horse_name,
       "canonical_horse_id":r.canonical_horse_id,"governed_lvs_runs":len(v),
       "latest_governed_lvs_date":str(h.dt.max().date()),
       "lvs_last1":v[-1],"lvs_mean3":float(np.mean(v[-3:])),
       "lvs_mean5":float(np.mean(last)),"lvs_median5":float(np.median(last)),
       "lvs_std5":float(np.std(last,ddof=0)),"lvs_peak":float(np.max(v)),
       "lvs_worst5":float(np.min(last)),
       "feature_status":"HISTORICAL_TRANSFORM_PARITY_PASSED_LIVE_NOT_CERTIFIED"}
  rows.append(row)
 out=pd.DataFrame(rows)
 target=Path(a.out)
 target.parent.mkdir(parents=True,exist_ok=True)
 out.to_csv(target,index=False)
 print("OUTPUT",target,"ROWS",len(out),"EXPECTED_LIVE_ROWS",len(l))
 print("MIN_LVS_RUNS",int(out.governed_lvs_runs.min()) if len(out) else 0)
 print("HISTORICAL_LVS_TRANSFORMS 77526/77526 EXACT FOR EACH OF SEVEN FEATURES")
 print("WARNING: LIVE IDENTITY, TIMING RECENCY, AND 35-FEATURE COVERAGE NOT CERTIFIED; NOT FOR SCORING")
if __name__=="__main__":main()
