from __future__ import annotations
import argparse,json,subprocess,sys
from edgeiq_daily_operations_common_v1 import *
def run(cmd):
    r=subprocess.run([sys.executable,*cmd],cwd=ROOT,text=True,capture_output=True)
    return {"cmd":"python "+" ".join(cmd),"returncode":r.returncode,"stdout":r.stdout[-4000:],"stderr":r.stderr[-4000:]}
def main():
    parser=add_common_args(argparse.ArgumentParser()); args=parser.parse_args(); start,end,mode=resolve_date_window(args)
    common=["--mode","RECENT_BACKFILL","--date-from",start.isoformat(),"--date-to",end.isoformat()]
    results=[run(["scripts/build_edgeiq_daily_race_discovery_v1.py",*common]),run(["scripts/build_edgeiq_daily_official_results_ingestion_v1.py",*common]),run(["scripts/build_edgeiq_daily_official_timing_ingestion_v1.py",*common]),run(["scripts/build_edgeiq_daily_condition_evidence_v1.py",*common]),run(["scripts/build_edgeiq_delayed_speed_data_ingestion_v1.py",*common]),run(["scripts/build_edgeiq_race_data_lifecycle_fact_v1.py",*common])]
    status='PASS' if all(r['returncode']==0 for r in results) else 'PARTIAL_RETRYABLE'
    payload={"status":status,"date_from":start.isoformat(),"date_to":end.isoformat(),"stages":results}; write_json_atomic(DATA/'edgeiq_recent_results_speed_backfill_manifest_v1.json',payload); print(json.dumps(payload,indent=2)); return 0 if status=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())
