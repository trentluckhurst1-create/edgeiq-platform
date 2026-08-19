from __future__ import annotations
import argparse,json
from edgeiq_daily_operations_common_v1 import *
FIELDS=["canonical_race_id","canonical_meeting_id","race_date","jurisdiction","result_status","timing_status","condition_status","speed_status","performance_base_status","normalisation_status","rating_status","publication_status","overall_lifecycle_status","first_discovered_at","last_checked_at","last_changed_at","result_source_hash","timing_source_hash","condition_source_hash","speed_source_hash","retry_eligible","next_retry_class","unresolved_reason","builder_version","contract_version"]
HIST_FIELDS=FIELDS+["operation_run_id","transition_recorded_at"]
def main():
    parser=add_common_args(argparse.ArgumentParser()); args=parser.parse_args(); start,end,mode=resolve_date_window(args)
    run_id=args.resume_run_id or operation_run_id('LIFECYCLE',start,end)
    races={}
    for r in read_csv(DATA/'edgeiq_daily_race_discovery_v1.csv'):
        cid=clean(r.get('canonical_race_id'));
        if cid: races.setdefault(cid, {"canonical_race_id":cid,"canonical_meeting_id":r.get('canonical_meeting_id',''),"race_date":r.get('meeting_date',''),"jurisdiction":r.get('jurisdiction','AU'),"first_discovered_at":r.get('source_observed_at','')})
    for r in read_csv(DATA/'edgeiq_daily_official_results_fact_v1.csv'):
        cid=clean(r.get('canonical_race_id')); races.setdefault(cid,{"canonical_race_id":cid,"canonical_meeting_id":r.get('canonical_meeting_id',''),"race_date":r.get('race_date',''),"jurisdiction":"AU","first_discovered_at":now_utc()}); races[cid].update({"result_status":r.get('result_status','RESULT_OFFICIAL'),"result_source_hash":r.get('source_evidence_sha256','')})
    for r in read_csv(DATA/'edgeiq_daily_official_timing_candidate_v1.csv'):
        cid=clean(r.get('canonical_race_id')); races.setdefault(cid,{"canonical_race_id":cid,"canonical_meeting_id":r.get('canonical_meeting_id',''),"race_date":r.get('race_date',''),"jurisdiction":"AU","first_discovered_at":now_utc()}); races[cid].update({"timing_status":r.get('timing_status','OFFICIAL_TIME_AVAILABLE'),"timing_source_hash":r.get('source_evidence_sha256','')})
    for r in read_csv(DATA/'edgeiq_daily_condition_evidence_v1.csv'):
        cid=clean(r.get('canonical_race_id')); races.setdefault(cid,{"canonical_race_id":cid,"canonical_meeting_id":r.get('canonical_meeting_id',''),"race_date":r.get('race_date',''),"jurisdiction":"AU","first_discovered_at":now_utc()}); races[cid].update({"condition_status":r.get('status','SOURCE_UNAVAILABLE'),"condition_source_hash":r.get('source_evidence_sha256','')})
    speed_by={}
    for r in read_csv(DATA/'edgeiq_delayed_speed_data_ingestion_v1.csv'):
        cid=clean(r.get('canonical_race_id')); speed_by.setdefault(cid,[]).append(r)
    for cid,items in speed_by.items():
        races.setdefault(cid,{"canonical_race_id":cid,"canonical_meeting_id":"","race_date":items[0].get('race_date',''),"jurisdiction":"AU","first_discovered_at":now_utc()})
        status='SPEED_DATA_AVAILABLE' if any(i.get('speed_status')=='SPEED_DATA_AVAILABLE' for i in items) else 'SPEED_DATA_PENDING'
        races[cid].update({"speed_status":status,"speed_source_hash":sha_text(''.join(sorted(i.get('evidence_hash','') for i in items)))})
    current=[]
    for cid,r in sorted(races.items()):
        result=r.get('result_status') or 'RESULT_PENDING'
        timing=r.get('timing_status') or 'TIME_PENDING'
        cond=r.get('condition_status') or 'CONDITION_PENDING'
        speed=r.get('speed_status') or 'SPEED_PENDING'
        perf='PERFORMANCE_BASE_AVAILABLE' if timing in {'TIMING_ACCEPTED','OFFICIAL_TIME_AVAILABLE'} and cond in {'RACE_LEVEL_OFFICIAL','MEETING_LEVEL_GOVERNED_INHERITANCE'} else 'GOVERNED_UNAVAILABLE'
        norm='NORMALISATION_PENDING' if perf=='PERFORMANCE_BASE_AVAILABLE' else 'GOVERNED_UNAVAILABLE'
        overall='COMPLETE' if result.startswith('RESULT_OFFICIAL') and timing in {'TIMING_ACCEPTED','OFFICIAL_TIME_AVAILABLE'} and cond.startswith('RACE_LEVEL') and speed=='SPEED_DATA_AVAILABLE' else 'SOURCE_DELAYED'
        unresolved=[]
        if result=='RESULT_PENDING': unresolved.append('RESULT_PENDING')
        if timing=='TIME_PENDING': unresolved.append('TIME_PENDING')
        if cond=='CONDITION_PENDING': unresolved.append('CONDITION_PENDING')
        if speed=='SPEED_PENDING': unresolved.append('SPEED_PENDING')
        retry='TRUE' if unresolved or overall!='COMPLETE' else 'FALSE'
        row={"canonical_race_id":cid,"canonical_meeting_id":r.get('canonical_meeting_id',''),"race_date":r.get('race_date',''),"jurisdiction":r.get('jurisdiction','AU'),"result_status":result,"timing_status":timing,"condition_status":cond,"speed_status":speed,"performance_base_status":perf,"normalisation_status":norm,"rating_status":"RATED_PENDING" if norm=='NORMALISATION_PENDING' else 'GOVERNED_UNAVAILABLE',"publication_status":"PUBLISHED_PENDING","overall_lifecycle_status":overall,"first_discovered_at":r.get('first_discovered_at') or now_utc(),"last_checked_at":now_utc(),"last_changed_at":now_utc(),"result_source_hash":r.get('result_source_hash',''),"timing_source_hash":r.get('timing_source_hash',''),"condition_source_hash":r.get('condition_source_hash',''),"speed_source_hash":r.get('speed_source_hash',''),"retry_eligible":retry,"next_retry_class":unresolved[0] if unresolved else 'COMPLETE_NO_RECHECK_REQUIRED',"unresolved_reason":";".join(unresolved),"builder_version":BUILDER_VERSION,"contract_version":CONTRACT_VERSION}
        current.append(row)
    history=read_csv(DATA/'edgeiq_race_data_lifecycle_history_fact_v1.csv')
    for row in current:
        h=dict(row); h['operation_run_id']=run_id; h['transition_recorded_at']=now_utc(); history.append(h)
    write_csv_atomic(DATA/'edgeiq_race_data_lifecycle_fact_v1.csv',current,FIELDS); write_csv_atomic(DATA/'edgeiq_race_data_lifecycle_history_fact_v1.csv',history,HIST_FIELDS)
    payload={"status":"PASS" if current else "PASS_NO_NEW_DATA","operation_run_id":run_id,"races":len(current),"pending":sum(1 for r in current if r['overall_lifecycle_status']!='COMPLETE')}; write_json_atomic(DATA/'edgeiq_race_data_lifecycle_fact_v1_summary.json',payload); print(json.dumps(payload,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
