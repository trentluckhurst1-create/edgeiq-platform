from __future__ import annotations
import argparse,json,subprocess,sys
from edgeiq_daily_operations_common_v1 import *
def main():
    parser=add_common_args(argparse.ArgumentParser()); args=parser.parse_args(); start,end,mode=resolve_date_window(args)
    before=count_rows(DATA/'edgeiq_canonical_historical_timing_warehouse_v1.csv')
    cmd=[sys.executable,'scripts/run_edgeiq_victoria_performance_intelligence_refresh_v1.py']
    if args.dry_run or args.no_publish:
        payload={"status":"PASS_DRY_RUN_NO_REFRESH","reason":"no-publish/dry-run requested","timed_races":before}; write_json_atomic(DATA/'edgeiq_incremental_performance_refresh_v1_summary.json',payload); print(json.dumps(payload,indent=2)); return 0
    r=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    manifest={}
    try: manifest=json.loads((DATA/'edgeiq_victoria_performance_intelligence_refresh_manifest_v1.json').read_text(encoding='utf-8'))
    except Exception: pass
    payload={"status":"PASS" if r.returncode==0 else "FAILED_MANDATORY_STAGE","returncode":r.returncode,"stdout":r.stdout[-4000:],"stderr":r.stderr[-4000:],"refresh_manifest_status":manifest.get('status',''),"row_counts":manifest.get('row_counts',{})}; write_json_atomic(DATA/'edgeiq_incremental_performance_refresh_v1_summary.json',payload); print(json.dumps(payload,indent=2)); return r.returncode
if __name__=='__main__': raise SystemExit(main())
