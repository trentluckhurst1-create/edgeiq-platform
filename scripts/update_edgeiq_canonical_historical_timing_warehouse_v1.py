from __future__ import annotations
import argparse,json,shutil
from pathlib import Path
from edgeiq_daily_operations_common_v1 import *
CAND_FIELDS=["recovered_timing_observation_id","canonical_race_id","canonical_meeting_id","race_date","jurisdiction","track","track_layout","race_number","distance_metres","race_class","race_class_group","surface_group","surface_evidence_status","track_condition","track_condition_group","field_size","winner_canonical_performance_id","winner_canonical_horse_id","winner_horse_name","winner_finish_position","official_race_time_seconds","time_unit","source_dataset","source_record_key","source_row_evidence_sha256","identity_status","unit_semantics_status","condition_evidence_status","timing_recovery_status","builder_version","built_at_utc"]
AUDIT_FIELDS=["operation_run_id","canonical_race_id","candidate_id","classification","reason","existing_id","candidate_hash","existing_hash"]

def condition_group(label):
    s=clean(label).upper()
    if 'HEAVY' in s: return 'HEAVY'
    if 'SOFT' in s: return 'SOFT'
    if 'GOOD' in s or 'FIRM' in s: return 'GOOD'
    if 'SYNTH' in s: return 'SYNTHETIC'
    return ''

def main():
    parser=add_common_args(argparse.ArgumentParser()); parser.add_argument('--candidate-path',default=''); args=parser.parse_args(); start,end,mode=resolve_date_window(args)
    run_id=args.resume_run_id or operation_run_id('CANONICAL-TIMING',start,end)
    existing=read_csv(DATA/'edgeiq_canonical_historical_timing_warehouse_v1.csv')
    existing_by_race={clean(r.get('canonical_race_id')):r for r in existing}
    timing=read_csv(Path(args.candidate_path)) if args.candidate_path else read_csv(DATA/'edgeiq_daily_official_timing_candidate_v1.csv')
    results_by_race={clean(r.get('canonical_race_id')):r for r in read_csv(DATA/'edgeiq_daily_official_results_fact_v1.csv')}
    candidate=[]
    for t in timing:
        if clean(t.get('timing_status')) not in {'TIMING_ACCEPTED','OFFICIAL_TIME_AVAILABLE'}: continue
        cid=clean(t.get('canonical_race_id')); r=results_by_race.get(cid,{})
        sec=clean(t.get('official_race_time_seconds'))
        try:
            if float(sec)<=0: continue
        except Exception: continue
        cond=first(r,['track_condition'], first(t,['track_condition']))
        row={"recovered_timing_observation_id":"TWRD-"+key_hash([cid,sec,t.get('source_evidence_sha256')],24),"canonical_race_id":cid,"canonical_meeting_id":clean(t.get('canonical_meeting_id')),"race_date":clean(t.get('race_date')),"jurisdiction":"VIC","track":clean(t.get('track')),"track_layout":"","race_number":clean(t.get('race_number')),"distance_metres":clean(t.get('distance_metres')),"race_class":first(r,['race_class','class']),"race_class_group":"","surface_group":"TURF","surface_evidence_status":"GOVERNED_DAILY_DEFAULT_FOR_VIC_NON_SYNTHETIC_UNLESS_SOURCE_OVERRIDES","track_condition":cond,"track_condition_group":condition_group(cond),"field_size":first(r,['field_size']),"winner_canonical_performance_id":"","winner_canonical_horse_id":"","winner_horse_name":first(r,['runner_name','winner_horse_name']),"winner_finish_position":"1","official_race_time_seconds":sec,"time_unit":clean(t.get('official_time_unit')) or 'SECONDS',"source_dataset":"edgeiq_daily_official_timing_candidate_v1.csv","source_record_key":cid,"source_row_evidence_sha256":clean(t.get('source_evidence_sha256')),"identity_status":"CANONICAL_RACE_ID_PRESENT","unit_semantics_status":"EXPLICIT_OFFICIAL_RACE_TIME_SECONDS_WITH_TIME_UNIT","condition_evidence_status":"AVAILABLE" if cond else 'SOURCE_UNAVAILABLE',"timing_recovery_status":"DAILY_GOVERNED_TIMING","builder_version":BUILDER_VERSION,"built_at_utc":now_utc()}
        candidate.append(row)
    audit=[]; accepted=[]
    for c in candidate:
        ex=existing_by_race.get(c['canonical_race_id'])
        ch=row_sha(c); eh=row_sha(ex) if ex else ''
        if not ex:
            audit.append({"operation_run_id":run_id,"canonical_race_id":c['canonical_race_id'],"candidate_id":c['recovered_timing_observation_id'],"classification":"NEW_CANONICAL_TIMING","reason":"No existing canonical timing row","existing_id":"","candidate_hash":ch,"existing_hash":""}); accepted.append(c)
        elif clean(ex.get('official_race_time_seconds'))==clean(c.get('official_race_time_seconds')) and clean(ex.get('source_row_evidence_sha256'))==clean(c.get('source_row_evidence_sha256')):
            audit.append({"operation_run_id":run_id,"canonical_race_id":c['canonical_race_id'],"candidate_id":c['recovered_timing_observation_id'],"classification":"UNCHANGED_DUPLICATE","reason":"Same race/time/evidence","existing_id":ex.get('recovered_timing_observation_id',''),"candidate_hash":ch,"existing_hash":eh})
        else:
            audit.append({"operation_run_id":run_id,"canonical_race_id":c['canonical_race_id'],"candidate_id":c['recovered_timing_observation_id'],"classification":"SAME_AUTHORITY_CONFLICT","reason":"Existing canonical timing differs; manual governance required","existing_id":ex.get('recovered_timing_observation_id',''),"candidate_hash":ch,"existing_hash":eh})
    write_csv_atomic(DATA/'edgeiq_daily_timing_canonical_candidate_v1.csv',candidate,CAND_FIELDS); write_csv_atomic(DATA/'edgeiq_daily_timing_canonical_update_audit_v1.csv',audit,AUDIT_FIELDS)
    before=len(existing); after=before + (0 if args.dry_run or args.no_publish else len(accepted))
    rollback=''
    if accepted and not args.dry_run and not args.no_publish:
        rollback_dir=ROOT/'docs/daily-operations-engine-v1/rollback'/run_id; rollback_dir.mkdir(parents=True,exist_ok=True); rollback= str(rollback_dir)
        src=DATA/'edgeiq_canonical_historical_timing_warehouse_v1.csv'; shutil.copy2(src, rollback_dir/src.name)
        write_csv_atomic(src, existing+accepted, CAND_FIELDS)
        hist=read_csv(DATA/'edgeiq_canonical_historical_timing_warehouse_revision_history_v1.csv'); hist += accepted; write_csv_atomic(DATA/'edgeiq_canonical_historical_timing_warehouse_revision_history_v1.csv',hist,CAND_FIELDS)
    payload={"status":"PASS" if accepted or audit else "PASS_NO_NEW_DATA","operation_run_id":run_id,"dry_run":bool(args.dry_run or args.no_publish),"timed_races_before":before,"timed_races_after":after,"new_canonical_rows":len(accepted),"corrected_rows":0,"conflicts":sum(1 for a in audit if 'CONFLICT' in a['classification']),"rollback_path":rollback}
    write_json_atomic(DATA/'edgeiq_daily_timing_canonical_update_v1_summary.json',payload); print(json.dumps(payload,indent=2)); return 0 if payload['conflicts']==0 else 2
if __name__=='__main__': raise SystemExit(main())
