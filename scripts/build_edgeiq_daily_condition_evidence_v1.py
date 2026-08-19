from __future__ import annotations
import argparse,json
from pathlib import Path
from edgeiq_daily_operations_common_v1 import *
FIELDS=["operation_run_id","canonical_race_id","canonical_meeting_id","race_date","track","race_number","condition_code","condition_label","condition_scope","evidence_source","evidence_timestamp","inherited_from_meeting","inheritance_contract_version","source_evidence_sha256","status","rejection_reason","builder_version","contract_version"]
def main():
    parser=add_common_args(argparse.ArgumentParser()); args=parser.parse_args(); start,end,mode=resolve_date_window(args)
    run_id=args.resume_run_id or operation_run_id('CONDITION',start,end)
    src=read_csv(DATA/'edgeiq_daily_official_results_fact_v1.csv') or read_csv(DATA/'edgeiq_vic_three_day_race_list_v1.csv')
    rows=[]
    seen=set()
    for r in src:
        if not in_window(r,start,end,['race_date','meeting_date']): continue
        cond=first(r,['track_condition','condition','going','current_condition'])
        track=first(r,['track','track_name','meeting_name']); rno=first(r,['race_number','race_no']); rdate=first(r,['race_date','meeting_date']); dist=first(r,['distance_metres','distance'])
        cid=clean(r.get('canonical_race_id')) or canonical_race_id(rdate,track,rno,dist)
        if cid in seen: continue
        seen.add(cid)
        status='RACE_LEVEL_OFFICIAL' if cond else 'SOURCE_NOT_PUBLISHED'
        rows.append({"operation_run_id":run_id,"canonical_race_id":cid,"canonical_meeting_id":clean(r.get('canonical_meeting_id')) or canonical_meeting_id(rdate,track),"race_date":rdate,"track":track,"race_number":rno,"condition_code":cond.upper().replace(' ','') if cond else '',"condition_label":cond,"condition_scope":"RACE_LEVEL" if cond else "UNAVAILABLE","evidence_source":"OFFICIAL_RESULTS_FACT" if cond else "NO_OFFICIAL_CONDITION_SOURCE","evidence_timestamp":now_utc(),"inherited_from_meeting":"FALSE","inheritance_contract_version":"","source_evidence_sha256":first(r,['source_evidence_sha256'],row_sha(r)),"status":status,"rejection_reason":"" if cond else "CONDITION_NOT_PUBLISHED_IN_SUPPORTED_SOURCE","builder_version":BUILDER_VERSION,"contract_version":CONTRACT_VERSION})
    write_csv_atomic(DATA/'edgeiq_daily_condition_evidence_v1.csv',rows,FIELDS)
    payload={"status":"PASS" if rows else "PASS_NO_NEW_DATA","operation_run_id":run_id,"condition_rows":len(rows),"available":sum(1 for r in rows if r['status'] in {'RACE_LEVEL_OFFICIAL','MEETING_LEVEL_GOVERNED_INHERITANCE'})}; write_json_atomic(DATA/'edgeiq_daily_condition_evidence_v1_summary.json',payload); print(json.dumps(payload,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
