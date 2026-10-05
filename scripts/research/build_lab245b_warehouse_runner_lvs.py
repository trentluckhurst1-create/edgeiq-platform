from pathlib import Path
import os
import hashlib
from bisect import insort
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
DATA_ROOT=Path(os.environ.get("EDGEIQ_DATA_ROOT",str(ROOT))).resolve()
WAREHOUSE=DATA_ROOT/"docs/performance-intelligence/warehouse/edgeiq_performance_fact_warehouse_v1.csv"
LCP=DATA_ROOT/"public/data/edgeiq_length_conversion_parameter_fact_v2.csv"
OUT=ROOT/"outputs/research/profitability_program/lab245b/LAB245B_WAREHOUSE_RUNNER_LVS.csv"
MIN_SAMPLE=20
EXPECTED_WAREHOUSE_SIZE=416143437
EXPECTED_WAREHOUSE_SHA256="bcdcef1c7cb9144feae5783ca2fa83b1dc2b8dc07a42ac31c31fd7bd12b53107"

def cond(x):
 s=str(x or "").upper()
 if "FIRM" in s or s=="FAST": return "FIRM"
 if "GOOD" in s:return "GOOD"
 if any(z in s for z in ["SOFT","DEAD","SLOW"]):return "SOFT"
 if "HEAVY" in s or "HVY" in s:return "HEAVY"
 if any(z in s for z in ["SYNTH","POLY","TAPETA"]):return "STANDARD_SYNTHETIC"
 return s

def _median_sorted(vals):
 n=len(vals)
 if not n:return np.nan
 m=n//2
 return float(vals[m]) if n%2 else float((vals[m-1]+vals[m])/2.0)

def main():
 OUT.parent.mkdir(parents=True,exist_ok=True)
 if not WAREHOUSE.exists():raise FileNotFoundError(WAREHOUSE)
 if WAREHOUSE.stat().st_size!=EXPECTED_WAREHOUSE_SIZE: raise RuntimeError(f"Warehouse size drift: {WAREHOUSE.stat().st_size}")
 h=hashlib.sha256()
 with WAREHOUSE.open("rb") as fh:
  for b in iter(lambda:fh.read(16*1024*1024),b""): h.update(b)
 digest=h.hexdigest()
 if digest!=EXPECTED_WAREHOUSE_SHA256: raise RuntimeError(f"Warehouse SHA drift: {digest}")
 print(f"WAREHOUSE_FROZEN_AUTHORITY=PASS SHA256={digest}")
 use=["canonical_race_id","canonical_horse_id","canonical_track_id","race_date","jurisdiction","track","track_layout","distance_metres","track_condition","track_condition_group","finish_position","finish_margin","official_race_time","official_race_time_seconds","time_unit"]
 d=pd.read_csv(WAREHOUSE,usecols=use,low_memory=False)
 d["race_date"]=pd.to_datetime(d["race_date"],errors="coerce")
 for x in ["distance_metres","finish_position","finish_margin","official_race_time","official_race_time_seconds"]:d[x]=pd.to_numeric(d[x],errors="coerce")
 # Fail closed against the known historical centiseconds /1000 regression.
 cs=d["time_unit"].astype("string").str.upper().eq("CENTISECONDS_TO_SECONDS_V1") & d["official_race_time"].notna() & d["official_race_time_seconds"].notna()
 if cs.any():
  unit_err=(d.loc[cs,"official_race_time"]/100.0-d.loc[cs,"official_race_time_seconds"]).abs().max()
  if unit_err>0.001: raise RuntimeError(f"Centiseconds conversion invariant failed max_abs_error={unit_err}")
  print(f"CENTISECONDS_UNIT_CHECK=PASS ROWS={int(cs.sum()):,} MAX_ABS_ERROR={unit_err:.9f}")
 d["condition"]=d["track_condition_group"].fillna(d["track_condition"]).map(cond)
 d["track_key"]=d["canonical_track_id"].fillna("").astype(str).str.strip()
 d["track_display_key"]=d["track"].fillna("").astype(str).str.strip().str.upper()
 d["layout_key"]=d["track_layout"].fillna("").astype(str).str.strip().str.upper()
 d["jurisdiction_key"]=d["jurisdiction"].fillna("").astype(str).str.strip().str.upper()
 txt=(d["track"].fillna("")+" "+d["track_layout"].fillna("")+" "+d["track_condition"].fillna("")+" "+d["track_condition_group"].fillna("")).str.upper()
 d["surface"]=np.where(txt.str.contains("SYNTHETIC|POLY|TAPETA|FIBRE|FIBER",regex=True),"AUSTRALIAN_SYNTHETIC","TURF")
 d["_valid_time"]=d["official_race_time_seconds"].gt(0)
 d["_winner"]=d["finish_position"].eq(1)
 r=d.sort_values(["canonical_race_id","_winner","_valid_time"],ascending=[True,False,False],kind="stable").drop_duplicates("canonical_race_id")
 r=r[r["_valid_time"]].copy()
 timed_races=len(r)

 # Strict date-PIT benchmark. All races on date D are scored from dates < D only.
 r=r.dropna(subset=["track_key","distance_metres","condition","official_race_time_seconds","race_date"]).sort_values(["race_date","canonical_race_id"],kind="stable")
 history={}
 scored=[]
 for race_date,day in r.groupby("race_date",sort=True):
  day=day.copy()
  std=[]; counts=[]
  for _,row in day.iterrows():
   k=(row["track_key"],row["distance_metres"],row["condition"],row["jurisdiction_key"])
   vals=history.get(k,[])
   counts.append(len(vals))
   std.append(_median_sorted(vals) if len(vals)>=MIN_SAMPLE else np.nan)
  day["benchmark_n"]=counts
  day["standard_time_seconds"]=std
  scored.append(day)
  # Add the whole date only after every race on the date has been scored.
  for _,row in day.iterrows():
   k=(row["track_key"],row["distance_metres"],row["condition"],row["jurisdiction_key"])
   insort(history.setdefault(k,[]),float(row["official_race_time_seconds"]))
 r=pd.concat(scored,ignore_index=True)
 r=r[r["standard_time_seconds"].notna()].copy()

 p=pd.read_csv(LCP,usecols=["surface_group","track_condition_group","seconds_per_length"])
 p["seconds_per_length"]=pd.to_numeric(p["seconds_per_length"],errors="coerce")
 expected={("AUSTRALIAN_SYNTHETIC","STANDARD_SYNTHETIC"):1/6,("TURF","FIRM"):1/6,("TURF","GOOD"):1/6,("TURF","SOFT"):0.2,("TURF","HEAVY"):0.2}
 actual={(str(x.surface_group).upper(),str(x.track_condition_group).upper()):float(x.seconds_per_length) for _,x in p.iterrows() if pd.notna(x.seconds_per_length)}
 for k,v in expected.items():
  if k not in actual or abs(actual[k]-v)>1e-6: raise RuntimeError(f"Length conversion authority drift {k}: {actual.get(k)} expected {v}")
 print("LENGTH_CONVERSION_AUTHORITY=PASS")
 p=p.rename(columns={"surface_group":"surface","track_condition_group":"condition"})
 r=r.merge(p,on=["surface","condition"],how="inner",validate="many_to_one")
 r["race_lvs"]=-(r["official_race_time_seconds"]-r["standard_time_seconds"])/r["seconds_per_length"]
 race_lvs=r[["canonical_race_id","race_lvs","standard_time_seconds","seconds_per_length","benchmark_n"]]
 out=d.merge(race_lvs,on="canonical_race_id",how="inner",validate="many_to_one")
 # Algebra recovered from original producer: runner LVS = race LVS - finish margin.\n # LAB245B intentionally uses the later governed surface/condition seconds-per-length table, not the legacy flat 0.17.
 out["runner_lvs"]=out["race_lvs"]-out["finish_margin"]
 out["runner_time_equivalent_seconds"]=out["official_race_time_seconds"]+out["finish_margin"]*out["seconds_per_length"]
 keep=["canonical_race_id","canonical_horse_id","race_date","distance_metres","finish_position","finish_margin","runner_time_equivalent_seconds","runner_lvs","race_lvs","standard_time_seconds","seconds_per_length","benchmark_n"]
 out[keep].to_csv(OUT,index=False)
 lvs_races=r["canonical_race_id"].nunique()
 print(f"SOURCE_ROWS={len(d):,}")
 print(f"TIMED_RACES={timed_races:,}")
 print(f"LVS_RACES={lvs_races:,}")
 print(f"RUNNER_ROWS={len(out):,}")
 print("PIT_POLICY=STRICT_DATE_LT_TARGET_DATE")
 print("RUNNER_LVS_POLICY=ORIGINAL_PRODUCER_ALGEBRA_WITH_GOVERNED_SURFACE_CONDITION_LENGTH_CONVERSION")
 print("RUNNER_TIME_EQUIVALENT_POLICY=ORIGINAL_PRODUCER_RACE_TIME_PLUS_MARGIN_X_SECONDS_PER_LENGTH")
 print("BENCHMARK_GROUPING=GOVERNED_DOWNSTREAM_CONTRACT_TRACK_ID_DISTANCE_CONDITION_JURISDICTION_MIN20_MEDIAN")
 print("BENCHMARK_POLICY=LAB245B_STRICT_DATE_PIT_NOT_OLD_ALL_HISTORY_PRODUCTION_STANDARD")
 print("KNOWN_RECOVERY_TIMED_RACES=70,308 DELTA_RACES=54,978 LVS_RACES=52,414")
 if abs(timed_races-70308)>10:raise RuntimeError("Timed-race recovery count materially disagrees with certified audit.")
 if lvs_races<=0 or lvs_races>=timed_races:raise RuntimeError("Invalid PIT LVS recovery funnel.")
 print(f"OUT={OUT}")
if __name__=="__main__":main()
