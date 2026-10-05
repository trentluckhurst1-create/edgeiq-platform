from pathlib import Path
import os
import hashlib
import json
from bisect import insort
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
DATA_ROOT=Path(os.environ.get("EDGEIQ_DATA_ROOT",str(ROOT))).resolve()
WAREHOUSE=DATA_ROOT/"docs/performance-intelligence/warehouse/edgeiq_performance_fact_warehouse_v1.csv"
OUT=ROOT/"outputs/research/profitability_program/lab245b/LAB245B_WAREHOUSE_RUNNER_LVS.csv"
MANIFEST=OUT.with_suffix(".manifest.json")
PREFLIGHT=OUT.parent/"LAB245B_PREFLIGHT.json"
# V8 freezes original V1 0.17 sec/length while making the benchmark strict date-PIT.
CONTRACT_VERSION="LAB245B_STRICT_PIT_LVS_V8_V1_LENGTH_CONVERSION_TRACK_DISTANCE_CONDITION_MIN20"
MIN_SAMPLE=20
V1_SECONDS_PER_LENGTH=0.17
V1_LENGTH_CONVERSION_CONTRACT="edgeiq_lengths_v_standard_methodology_v1.json:GOVERNED_CONSTANT_FROM_EXISTING_LENGTH_CONVERSION_CONTEXT_V1"
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
 digest=None
 if PREFLIGHT.exists():
  try:
   pf=json.loads(PREFLIGHT.read_text(encoding="utf-8"))
   wh=pf.get("checks",{}).get("warehouse",{})
   if pf.get("status")=="PASS" and wh.get("status")=="PASS" and wh.get("bytes")==EXPECTED_WAREHOUSE_SIZE and wh.get("sha256")==EXPECTED_WAREHOUSE_SHA256:
    digest=EXPECTED_WAREHOUSE_SHA256
    print("WAREHOUSE_SHA_REUSED_FROM_PREFLIGHT=YES")
  except Exception:
   digest=None
 if digest is None:
  h=hashlib.sha256()
  with WAREHOUSE.open("rb") as fh:
   for b in iter(lambda:fh.read(16*1024*1024),b""): h.update(b)
  digest=h.hexdigest()
  if digest!=EXPECTED_WAREHOUSE_SHA256: raise RuntimeError(f"Warehouse SHA drift: {digest}")
 print(f"WAREHOUSE_FROZEN_AUTHORITY=PASS SHA256={digest}")
 use=["canonical_race_id","canonical_horse_id","canonical_track_id","race_date","jurisdiction","track","track_layout","distance_metres","track_condition","track_condition_group","field_size","finish_position","finish_margin","official_race_time","official_race_time_seconds","time_unit"]
 d=pd.read_csv(WAREHOUSE,usecols=use,low_memory=False)
 d["race_date"]=pd.to_datetime(d["race_date"],errors="coerce")
 for x in ["distance_metres","finish_position","finish_margin","official_race_time","official_race_time_seconds"]:d[x]=pd.to_numeric(d[x],errors="coerce")
 # Fail closed against the known historical centiseconds /1000 regression.
 cs=d["time_unit"].astype("string").str.upper().eq("CENTISECONDS_TO_SECONDS_V1") & d["official_race_time"].notna() & d["official_race_time_seconds"].notna()
 if cs.any():
  unit_err=(d.loc[cs,"official_race_time"]/100.0-d.loc[cs,"official_race_time_seconds"]).abs().max()
  if unit_err>0.001: raise RuntimeError(f"Centiseconds conversion invariant failed max_abs_error={unit_err}")
  print(f"CENTISECONDS_UNIT_CHECK=PASS ROWS={int(cs.sum()):,} MAX_ABS_ERROR={unit_err:.9f}")
 grp=d["track_condition_group"].astype("string").str.strip().str.upper()
 d["condition"]=grp
 d.loc[d["condition"].isin(["","UNKNOWN","NAN","NONE","<NA>"]),"condition"]=pd.NA
 d["track_key"]=d["canonical_track_id"].fillna("").astype(str).str.strip()
 d.loc[d["track_key"].eq(""),"track_key"]=pd.NA
 d["track_display_key"]=d["track"].fillna("").astype(str).str.strip().str.upper()
 d["layout_key"]=d["track_layout"].fillna("").astype(str).str.strip().str.upper()
 d["jurisdiction_key"]=d["jurisdiction"].fillna("").astype(str).str.strip().str.upper()
 unit=d["time_unit"].astype("string").str.strip().str.lower()
 d["_valid_time"]=d["official_race_time_seconds"].notna() & d["official_race_time_seconds"].gt(0) & ~unit.isin(["unknown","invalid"])
 d["_valid_distance"]=d["distance_metres"].notna() & d["distance_metres"].gt(0)
 d["_eligible_benchmark"]=d["_valid_time"] & d["_valid_distance"] & d["track_key"].notna() & d["condition"].notna()
 rc=d.groupby("canonical_race_id",sort=False).agg(track_n=("track_key","nunique"),date_n=("race_date","nunique"),distance_n=("distance_metres","nunique"),condition_n=("condition","nunique"),jurisdiction_n=("jurisdiction_key","nunique"),field_size_n=("field_size","nunique"),time_n=("official_race_time_seconds","nunique"))
 bad=rc[(rc.track_n>1)|(rc.date_n>1)|(rc.distance_n>1)|(rc.condition_n>1)|(rc.jurisdiction_n>1)|(rc.field_size_n>1)|(rc.time_n>1)]
 if len(bad): raise RuntimeError(f"Canonical race attribute conflicts: {len(bad)} races")
 print(f"CANONICAL_RACE_ATTRIBUTE_INVARIANT=PASS RACES={len(rc):,}")
 d["_winner"]=d["finish_position"].eq(1)
 d["_race_pick_priority"]=np.select([d["_winner"] & d["_valid_time"],d["_valid_time"],d["_winner"]],[3,2,1],default=0)
 r=d.sort_values(["canonical_race_id","_race_pick_priority"],ascending=[True,False],kind="stable").drop_duplicates("canonical_race_id")
 timed_races=int(r["_valid_time"].sum())
 eligible_timed_races=int(r["_eligible_benchmark"].sum())
 r=r[r["_eligible_benchmark"]].copy()
 print(f"BENCHMARK_ELIGIBILITY=ORIGINAL_PRODUCER_DISTANCE_GT0_TIME_GT0_VALID_TIME_UNIT_TRACK_PRESENT_GOVERNED_CONDITION ELIGIBLE_RACES={eligible_timed_races:,}")

 # Strict date-PIT benchmark. All races on date D are scored from dates < D only.
 r=r.dropna(subset=["track_key","distance_metres","condition","official_race_time_seconds","race_date"]).sort_values(["race_date","canonical_race_id"],kind="stable")
 history={}
 scored=[]
 for race_date,day in r.groupby("race_date",sort=True):
  day=day.copy()
  keys=list(zip(day["track_key"],day["distance_metres"],day["condition"]))
  times=day["official_race_time_seconds"].to_numpy(float)
  counts=[]; std=[]
  for k in keys:
   vals=history.get(k,[])
   counts.append(len(vals))
   std.append(_median_sorted(vals) if len(vals)>=MIN_SAMPLE else np.nan)
  day["benchmark_n"]=counts
  day["standard_time_seconds"]=std
  scored.append(day)
  # Add the whole date only after every race on the date has been scored.
  for k,t in zip(keys,times):
   insort(history.setdefault(k,[]),float(t))
 r=pd.concat(scored,ignore_index=True)
 r=r[r["standard_time_seconds"].notna()].copy()

 sec_per_len=V1_SECONDS_PER_LENGTH
 r["seconds_per_length"]=sec_per_len
 print("LENGTH_CONVERSION=ORIGINAL_PRODUCER_GOVERNED_CONSTANT_0.17")
 r["race_lvs"]=-(r["official_race_time_seconds"]-r["standard_time_seconds"])/r["seconds_per_length"]
 race_lvs=r[["canonical_race_id","race_lvs","standard_time_seconds","seconds_per_length","benchmark_n"]]
 out=d.merge(race_lvs,on="canonical_race_id",how="inner",validate="many_to_one")
 # Runner target is defined only for a valid finishing outcome; benchmark race history remains race-level.
 valid_runner=out["finish_position"].gt(0) & out["finish_margin"].notna() & out["finish_margin"].ge(0)
 invalid_runner_rows=int((~valid_runner).sum())
 # Preserve every runner in an eligible benchmark race so downstream probability completeness
 # is measured against the actual represented field. Invalid finishing outcomes receive no LVS target.
 out["runner_lvs"]=np.nan
 out["runner_time_equivalent_seconds"]=np.nan
 out.loc[valid_runner,"runner_lvs"]=out.loc[valid_runner,"race_lvs"]-out.loc[valid_runner,"finish_margin"]
 out.loc[valid_runner,"runner_time_equivalent_seconds"]=out.loc[valid_runner,"official_race_time_seconds"]+out.loc[valid_runner,"finish_margin"]*out.loc[valid_runner,"seconds_per_length"]
 print(f"RUNNER_TARGET_VALIDITY=FINISH_POSITION_GT0_AND_FINITE_NONNEGATIVE_MARGIN INVALID_TARGET_NULL={invalid_runner_rows:,} ALL_RUNNERS_PRESERVED=YES")
 # Algebra recovered from original producer: runner LVS = race LVS - finish margin.
 # Baseline parity: original governed producer constant 0.17. Condition-dependent conversion is reserved for a separately named challenger.
 keep=["canonical_race_id","canonical_horse_id","race_date","distance_metres","field_size","finish_position","finish_margin","runner_time_equivalent_seconds","runner_lvs","race_lvs","standard_time_seconds","seconds_per_length","benchmark_n"]
 out[keep].to_csv(OUT,index=False)
 oh=hashlib.sha256()
 with OUT.open("rb") as fh:
  for b in iter(lambda:fh.read(16*1024*1024),b""): oh.update(b)
 output_sha=oh.hexdigest()
 manifest={"contract_version":CONTRACT_VERSION,"warehouse_sha256":digest,"warehouse_bytes":WAREHOUSE.stat().st_size,"pit_policy":"STRICT_DATE_LT_TARGET_DATE","benchmark_grouping":"canonical_track_id+distance_metres+condition","minimum_prior_races":MIN_SAMPLE,"runner_formula":"race_lvs-finish_margin","seconds_per_length":V1_SECONDS_PER_LENGTH,"length_conversion_contract":V1_LENGTH_CONVERSION_CONTRACT,"valid_runner_rule":"finish_position>0 and finite nonnegative finish_margin","output_sha256":output_sha,"output_bytes":OUT.stat().st_size,"rows_all_represented_runners":int(len(out)),"rows_valid_lvs_target":int(out["runner_lvs"].notna().sum()),"races":int(out["canonical_race_id"].nunique())}
 MANIFEST.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
 lvs_races=r["canonical_race_id"].nunique()
 print(f"SOURCE_ROWS={len(d):,}")
 print(f"TIMED_RACES={timed_races:,}")
 print(f"LVS_RACES={lvs_races:,}")
 print(f"RUNNER_ROWS_ALL={len(out):,}")
 print(f"RUNNER_ROWS_VALID_LVS={int(out['runner_lvs'].notna().sum()):,}")
 print("PIT_POLICY=STRICT_DATE_LT_TARGET_DATE")
 print("RUNNER_LVS_POLICY=ORIGINAL_PRODUCER_ALGEBRA_WITH_ORIGINAL_GOVERNED_CONSTANT_0.17")
 print("RUNNER_TIME_EQUIVALENT_POLICY=ORIGINAL_PRODUCER_RACE_TIME_PLUS_MARGIN_X_SECONDS_PER_LENGTH")
 print("BENCHMARK_GROUPING=RECOVERED_PRODUCTION_CONTRACT_TRACK_ID_DISTANCE_CONDITION_MIN20_MEDIAN")
 print("BENCHMARK_CONTRACT=edgeiq_standard_time_grouping_contract_v1 APPROVED=track+distance+condition MIN_OBS=20")
 print("BENCHMARK_POLICY=LAB245B_STRICT_DATE_PIT_NOT_OLD_ALL_HISTORY_PRODUCTION_STANDARD")
 print("BENCHMARK_OUTLIER_POLICY=NONE")
 print("KNOWN_RECOVERY_TIMED_RACES=70,308 DELTA_RACES=54,978 LVS_RACES=52,414")
 if abs(timed_races-70308)>10:raise RuntimeError("Timed-race recovery count materially disagrees with certified audit.")
 if lvs_races<=0 or lvs_races>=timed_races:raise RuntimeError("Invalid PIT LVS recovery funnel.")
 print(f"OUT={OUT}")
 print(f"MANIFEST={MANIFEST}")
if __name__=="__main__":main()
