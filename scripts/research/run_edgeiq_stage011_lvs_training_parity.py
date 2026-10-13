"""Stage011 historical feature-definition parity check, fail closed.

Compares candidate LVS aggregations against genuine PIT training warehouse
features on rows with exactly identified prior runner-LVS histories.
Does not use target outcomes or 2025-26 evaluation rows.
"""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd

FEATURES=["lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5"]
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--pit",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage006\V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv")
 p.add_argument("--runs",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_WAREHOUSE_RUNNER_LVS.csv")
 p.add_argument("--max-rows",type=int,default=150)
 a=p.parse_args()
 if a.max_rows<1:raise RuntimeError("STOP invalid sample size")
 h=pd.read_csv(a.pit,dtype="string")
 w=pd.read_csv(a.runs,dtype="string",usecols=["canonical_race_id","canonical_horse_id","race_date","runner_lvs"])
 print("PIT_ROWS",len(h),"PIT_COLUMNS",h.columns.tolist())
 # Never silently assume _horse or horse_code means canonical_horse_id.
 keys=[c for c in ("canonical_horse_id","_horse","horse_code") if c in h]
 print("PIT_ID_CANDIDATES",keys,"RUNNER_ID","canonical_horse_id")
 if "_horse" not in h or "_race" not in h:
  raise RuntimeError("STOP PIT missing verified historical keys")
 # Full 91,434-row exact observation join was verified independently.
 # Recheck sampled exact race+horse+date observations before feature comparison.
 check=h[["_race","_horse","race_date"]].merge(
  w[["canonical_race_id","canonical_horse_id","race_date"]],
  left_on=["_race","_horse"],right_on=["canonical_race_id","canonical_horse_id"],
  how="left",validate="one_to_one",indicator=True,suffixes=("_pit","_warehouse"))
 if not check["_merge"].eq("both").all() or not check["race_date_pit"].eq(check["race_date_warehouse"]).all():
  raise RuntimeError("STOP historical exact observation parity failed")
 if "race_date" not in h or not set(FEATURES).issubset(h):raise RuntimeError("STOP PIT feature schema incomplete")
 h["dt"]=pd.to_datetime(h.race_date,errors="coerce")
 h=h[h.dt.lt(pd.Timestamp("2025-01-01"))].copy()
 w["dt"]=pd.to_datetime(w.race_date,errors="coerce")
 w["v"]=pd.to_numeric(w.runner_lvs,errors="coerce")
 w=w[w.dt.lt(pd.Timestamp("2025-01-01"))&w.v.notna()].copy()
 if w.duplicated(["canonical_race_id","canonical_horse_id"]).any():raise RuntimeError("STOP duplicate historical race/horse")
 w=w.sort_values(["canonical_horse_id","dt","canonical_race_id"])
 sample=h.dropna(subset=["_horse","dt"]).head(a.max_rows)
 errors={f:[] for f in FEATURES}
 n=0
 for _,r in sample.iterrows():
  prior=w[w.canonical_horse_id.eq(r["_horse"])&w.dt.lt(r["dt"])]
  if prior.empty:continue
  v=prior.v.to_numpy(dtype=float)
  last=v[-5:]
  calc={"lvs_last1":v[-1],"lvs_mean3":np.mean(v[-3:]),"lvs_mean5":np.mean(last),
        "lvs_median5":np.median(last),"lvs_std5":np.std(last,ddof=0),
        "lvs_peak":np.max(v),"lvs_worst5":np.min(last)}
  n+=1
  for f in FEATURES:
   actual=pd.to_numeric(pd.Series([r[f]]),errors="coerce").iloc[0]
   if pd.notna(actual):errors[f].append(abs(float(actual)-float(calc[f])))
 print("EXACT_OBSERVATION_JOIN",len(check),"COMPARED_ROWS",n)
 for f,values in errors.items():
  print("PARITY",f,"N",len(values),"MAX_ABS_ERROR",max(values) if values else None,
        "EXACT",sum(e<1e-8 for e in values),"/",len(values))
 if n==0:print("STOP NO_COMPARABLE_ROWS")
 elif any(v and max(v)>1e-8 for v in errors.values()):print("STOP FEATURE_DEFINITION_MISMATCH; do not promote candidates")
 else:print("SAMPLED_PARITY_ONLY; full lineage and missingness still require certification")
if __name__=="__main__":main()
