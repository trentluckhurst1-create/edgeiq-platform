from pathlib import Path
import os, json, hashlib, shutil, sys
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
DATA_ROOT=Path(os.environ.get("EDGEIQ_DATA_ROOT",str(ROOT))).resolve()
OUT=ROOT/"outputs/research/profitability_program/lab245b/LAB245B_PREFLIGHT.json"
WAREHOUSE=DATA_ROOT/"docs/performance-intelligence/warehouse/edgeiq_performance_fact_warehouse_v1.csv"
LCP=DATA_ROOT/"public/data/edgeiq_length_conversion_parameter_fact_v2.csv"
AUTH=DATA_ROOT/"docs/performance-intelligence/lengths-v-standard/edgeiq_runner_lengths_v_standard_fact_v1.csv"
WH_SIZE=416143437
WH_SHA="bcdcef1c7cb9144feae5783ca2fa83b1dc2b8dc07a42ac31c31fd7bd12b53107"
AUTH_SIZE=80343742
AUTH_SHA="b08bb7a334ddba2f6a76942452dd964cd59db05001dc5710ff19aa7fc6e12926"

def sha256(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(16*1024*1024),b""): h.update(b)
 return h.hexdigest()

def cols(p):
 return list(pd.read_csv(p,nrows=0).columns)

def main():
 OUT.parent.mkdir(parents=True,exist_ok=True)
 usage=shutil.disk_usage(ROOT)
 a={"data_root":str(DATA_ROOT),"python":sys.version.split()[0],"research_root":str(ROOT),"free_disk_bytes":int(usage.free),"checks":{},"status":"PASS"}
 if usage.free < 2_000_000_000:
  a["status"]="FAIL"; a["checks"]["disk_space"]={"status":"FAIL","required_free_bytes":2_000_000_000,"actual_free_bytes":int(usage.free)}
 else: a["checks"]["disk_space"]={"status":"PASS","required_free_bytes":2_000_000_000,"actual_free_bytes":int(usage.free)}
 for name,p,size,digest,need in [
  ("warehouse",WAREHOUSE,WH_SIZE,WH_SHA,{"canonical_race_id","canonical_horse_id","canonical_track_id","race_date","distance_metres","track_condition","finish_position","finish_margin","official_race_time","official_race_time_seconds","time_unit"}),
  ("length_conversion",LCP,None,None,{"surface_group","track_condition_group","seconds_per_length"}),
 ]:
  x={"path":str(p),"exists":p.exists()}
  if not p.exists(): x["status"]="FAIL_MISSING"; a["status"]="FAIL"
  else:
   x["bytes"]=p.stat().st_size
   x["columns"]=cols(p)
   miss=sorted(need-set(x["columns"]))
   x["missing_columns"]=miss
   if size is not None and x["bytes"]!=size: x["status"]="FAIL_SIZE"; a["status"]="FAIL"
   elif miss: x["status"]="FAIL_SCHEMA"; a["status"]="FAIL"
   else:
    if digest is not None:
     x["sha256"]=sha256(p)
     if x["sha256"]!=digest: x["status"]="FAIL_SHA"; a["status"]="FAIL"
     else: x["status"]="PASS"
    else: x["status"]="PASS"
  a["checks"][name]=x
 x={"path":str(AUTH),"exists":AUTH.exists(),"role":"PARITY_ONLY_NOT_FORECAST_TARGET"}
 if AUTH.exists():
  x["bytes"]=AUTH.stat().st_size
  x["status"]="PASS" if x["bytes"]==AUTH_SIZE else "WARN_SIZE_DRIFT"
  if x["bytes"]==AUTH_SIZE:
   x["sha256"]=sha256(AUTH)
   if x["sha256"]!=AUTH_SHA: x["status"]="WARN_SHA_DRIFT"
 a["checks"]["historical_runner_lvs_authority"]=x
 OUT.write_text(json.dumps(a,indent=2),encoding="utf-8")
 print(json.dumps(a,indent=2))
 if a["status"]!="PASS": raise SystemExit(2)
if __name__=="__main__": main()
