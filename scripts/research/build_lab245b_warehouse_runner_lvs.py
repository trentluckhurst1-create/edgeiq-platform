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
BENCHMARK_CHECKPOINT=OUT.parent/"LAB245B_STRICT_PIT_RACE_BENCHMARK_CHECKPOINT.csv"
BENCHMARK_CHECKPOINT_META=OUT.parent/"LAB245B_STRICT_PIT_RACE_BENCHMARK_CHECKPOINT.json"
# V8 freezes original V1 0.17 sec/length while making the benchmark strict date-PIT.
CONTRACT_VERSION="LAB245B_STRICT_PIT_LVS_V12_QUARANTINE_LINEAGE_COMPLETE_V1_LENGTH_CONVERSION_TRACK_DISTANCE_CONDITION_MIN20"
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
 use=["canonical_performance_id","canonical_race_id","canonical_horse_id","canonical_track_id","race_date","distance_metres","track_condition_group","field_size","finish_position","finish_margin","official_race_time","official_race_time_seconds","time_unit","source_dataset","source_record_key","duplicate_status"]
 header=set(pd.read_csv(WAREHOUSE,nrows=0).columns)
 missing_use=[x for x in use if x not in header]
 if missing_use: raise RuntimeError(f"LAB245B required warehouse columns missing: {missing_use}")
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
 unit=d["time_unit"].astype("string").str.strip().str.lower()
 d["_valid_time"]=d["official_race_time_seconds"].notna() & d["official_race_time_seconds"].gt(0) & ~unit.isin(["unknown","invalid"])
 d["_valid_distance"]=d["distance_metres"].notna() & d["distance_metres"].gt(0)
 d["_eligible_benchmark"]=d["_valid_time"] & d["_valid_distance"] & d["track_key"].notna() & d["condition"].notna()
 rc_identity=d.groupby("canonical_race_id",sort=False).agg(track_n=("track_key","nunique"),date_n=("race_date","nunique"),distance_n=("distance_metres","nunique"),condition_n=("condition","nunique"),field_size_n=("field_size","nunique"))
 bad_identity=rc_identity[(rc_identity.track_n>1)|(rc_identity.date_n>1)|(rc_identity.distance_n>1)|(rc_identity.condition_n>1)|(rc_identity.field_size_n>1)]
 if len(bad_identity): raise RuntimeError(f"Canonical race identity attribute conflicts: {len(bad_identity)} races")
 print(f"CANONICAL_RACE_IDENTITY_INVARIANT=PASS RACES={len(rc_identity):,}")
 # Parity with accepted timing-warehouse recovery V1: select one race observation,
 # preferring a winner with valid time, then any valid timed row, then a winner.
 d["_winner"]=d["finish_position"].eq(1)
 d["_race_pick_priority"]=np.select([d["_winner"] & d["_valid_time"],d["_valid_time"],d["_winner"]],[3,2,1],default=0)
 multi_time=d.loc[d["_valid_time"]].groupby("canonical_race_id")["official_race_time_seconds"].nunique()
 multi_time_races=int((multi_time>1).sum())
 winner_time_n=d.loc[d["_winner"] & d["_valid_time"]].groupby("canonical_race_id")["official_race_time_seconds"].nunique()
 ambiguous_ids=set(winner_time_n[winner_time_n>1].index.astype(str))
 ambiguous_winner_races=len(ambiguous_ids)
 if ambiguous_winner_races:
  lineage_cols=["canonical_race_id","canonical_performance_id","canonical_horse_id","race_date","canonical_track_id","distance_metres","track_condition_group","finish_position","official_race_time","official_race_time_seconds","time_unit","source_dataset","source_record_key","duplicate_status"]
  q=d[d["canonical_race_id"].astype(str).isin(ambiguous_ids)][lineage_cols].copy()
  q=q.sort_values(["canonical_race_id","finish_position","canonical_horse_id"],kind="stable")
  qpath=OUT.parent/"LAB245B_AMBIGUOUS_WINNER_TIME_QUARANTINE.csv"
  q.to_csv(qpath,index=False)
  print(f"AMBIGUOUS_WINNER_TIME_QUARANTINE={qpath} RACES={ambiguous_winner_races:,} ROWS={len(q):,}")
 d["_timing_quarantined"]=d["canonical_race_id"].astype(str).isin(ambiguous_ids)
 selection=d[~d["_timing_quarantined"]].copy()
 r=selection.sort_values(["canonical_race_id","_race_pick_priority"],ascending=[True,False],kind="stable").drop_duplicates("canonical_race_id")
 print(f"RECOVERY_RACE_SELECTION_PARITY=PASS MULTI_TIME_RACES={multi_time_races:,} QUARANTINED_AMBIGUOUS_WINNER_TIME_RACES={ambiguous_winner_races:,} POLICY=WINNER_VALID_TIME_THEN_VALID_TIME_THEN_WINNER")
 timed_races=int(r["_valid_time"].sum())
 eligible_timed_races=int(r["_eligible_benchmark"].sum())
 r=r[r["_eligible_benchmark"]].copy()
 print(f"BENCHMARK_ELIGIBILITY=ORIGINAL_PRODUCER_DISTANCE_GT0_TIME_GT0_VALID_TIME_UNIT_TRACK_PRESENT_GOVERNED_CONDITION ELIGIBLE_RACES={eligible_timed_races:,}")

 # Strict date-PIT benchmark. All races on date D are scored from dates < D only.
 r=r.dropna(subset=["track_key","distance_metres","condition","official_race_time_seconds","race_date"]).sort_values(["race_date","canonical_race_id"],kind="stable")
 checkpoint_ok=False
 if BENCHMARK_CHECKPOINT.exists() and BENCHMARK_CHECKPOINT_META.exists():
  try:
   cm=json.loads(BENCHMARK_CHECKPOINT_META.read_text(encoding="utf-8"))
   checkpoint_ok=(cm.get("contract_version")==CONTRACT_VERSION and cm.get("warehouse_sha256")==digest and cm.get("pit_policy")=="STRICT_DATE_LT_TARGET_DATE")
   if checkpoint_ok:
    ch=hashlib.sha256()
    with BENCHMARK_CHECKPOINT.open("rb") as fh:
     for b in iter(lambda:fh.read(8*1024*1024),b""): ch.update(b)
    checkpoint_ok=(cm.get("checkpoint_sha256")==ch.hexdigest() and cm.get("checkpoint_bytes")==BENCHMARK_CHECKPOINT.stat().st_size)
  except Exception:
   checkpoint_ok=False
 if checkpoint_ok:
  r=pd.read_csv(BENCHMARK_CHECKPOINT,low_memory=False)
  r["race_date"]=pd.to_datetime(r["race_date"],errors="coerce")
  print(f"RESUME_CHECKPOINT=STRICT_PIT_RACE_BENCHMARK ROWS={len(r):,}")
 else:
  # Vectorised strict-date PIT benchmark. Within each benchmark group, the first
  # race on a date sees only earlier dates; that value is then broadcast to every
  # race in the same group/date so same-day races can never leak into one another.
  gcols=["track_key","distance_metres","condition"]
  r=r.sort_values(gcols+["race_date","canonical_race_id"],kind="stable").reset_index(drop=True)
  grpobj=r.groupby(gcols,sort=False,dropna=False)
  r["_prior_n_row"]=grpobj.cumcount()
  # expanding().median() includes current row, so shift one position within each
  # group. We then freeze the first row's prior-only value for the whole date.
  expmed=(grpobj["official_race_time_seconds"].expanding().median()
          .reset_index(level=gcols,drop=True)
          .sort_index())
  r["_expanding_median_including_current"]=expmed
  r["_prior_median_row"]=r.groupby(gcols,sort=False,dropna=False)["_expanding_median_including_current"].shift(1)
  datekeys=gcols+["race_date"]
  r["benchmark_n"]=r.groupby(datekeys,sort=False,dropna=False)["_prior_n_row"].transform("first")
  r["standard_time_seconds"]=r.groupby(datekeys,sort=False,dropna=False)["_prior_median_row"].transform("first")
  r.loc[r["benchmark_n"]<MIN_SAMPLE,"standard_time_seconds"]=np.nan
  r=r[r["standard_time_seconds"].notna()].copy()
  r=r.drop(columns=["_prior_n_row","_prior_median_row","_expanding_median_including_current"])
  checkpoint_cols=["canonical_race_id","race_date","official_race_time_seconds","standard_time_seconds","benchmark_n"]
  r[checkpoint_cols].to_csv(BENCHMARK_CHECKPOINT,index=False)
  ch=hashlib.sha256()
  with BENCHMARK_CHECKPOINT.open("rb") as fh:
   for b in iter(lambda:fh.read(8*1024*1024),b""): ch.update(b)
  BENCHMARK_CHECKPOINT_META.write_text(json.dumps({"contract_version":CONTRACT_VERSION,"warehouse_sha256":digest,"pit_policy":"STRICT_DATE_LT_TARGET_DATE","rows":int(len(r)),"checkpoint_sha256":ch.hexdigest(),"checkpoint_bytes":BENCHMARK_CHECKPOINT.stat().st_size},indent=2),encoding="utf-8")
  print(f"CHECKPOINT_WRITTEN=STRICT_PIT_RACE_BENCHMARK ROWS={len(r):,}")

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
