from __future__ import annotations
import argparse,json,re
from decimal import Decimal
from edgeiq_daily_operations_common_v1 import *
FIELDS=["operation_run_id","canonical_race_id","canonical_meeting_id","race_date","track","race_number","distance_metres","official_time_raw","official_time_unit","official_race_time_seconds","source_authority","source_publication_timestamp","source_evidence_sha256","timing_status","timing_candidate_id","builder_version","contract_version"]
REJ_FIELDS=FIELDS+["rejection_reason"]

def parse_seconds(raw):
    s=clean(raw).lower().replace('sec','').replace('s','').strip()
    if not s: return ('','')
    if ':' in s:
        parts=[Decimal(p) for p in s.split(':')]
        if len(parts)==2: return (f"{(parts[0]*60+parts[1]).quantize(Decimal('0.000001')):f}", 'MINUTES_SECONDS_TEXT')
    try:
        val=Decimal(s)
        if val <= 0: return ('','INVALID')
        if val > 10000: return ('','UNSUPPORTED_TIME_UNIT')
        return (f"{val.quantize(Decimal('0.000001')):f}", 'SECONDS')
    except Exception:
        return ('','UNSUPPORTED_TIME_UNIT')

def main():
    parser=add_common_args(argparse.ArgumentParser()); args=parser.parse_args(); start,end,mode=resolve_date_window(args)
    run_id=args.resume_run_id or operation_run_id('TIMING',start,end)
    source=read_csv(DATA/'edgeiq_daily_official_results_fact_v1.csv')
    if args.fixture_root and not source: source=read_csv(Path(args.fixture_root)/'official_results_fixture.csv')
    by_race={}
    for r in source:
        if not in_window(r,start,end,['race_date']): continue
        raw=first(r,['official_race_time_seconds','winner_race_time_seconds','race_time_seconds','official_race_time','race_time','winning_time'])
        if raw and clean(r.get('canonical_race_id')) not in by_race: by_race[clean(r.get('canonical_race_id')) or canonical_race_id(first(r,['race_date']),first(r,['track']),first(r,['race_number','race_no']),first(r,['distance_metres','distance']))]=r
    out=[]; rej=[]
    for cid,r in by_race.items():
        raw=first(r,['official_race_time_seconds','winner_race_time_seconds','race_time_seconds','official_race_time','race_time','winning_time'])
        sec,unit=parse_seconds(raw)
        base={"operation_run_id":run_id,"canonical_race_id":cid,"canonical_meeting_id":clean(r.get('canonical_meeting_id')) or canonical_meeting_id(first(r,['race_date']),first(r,['track'])),"race_date":first(r,['race_date']),"track":first(r,['track','track_name']),"race_number":first(r,['race_number','race_no']),"distance_metres":first(r,['distance_metres','distance']),"official_time_raw":raw,"official_time_unit":unit,"official_race_time_seconds":sec,"source_authority":"DAILY_OFFICIAL_RESULTS_FACT","source_publication_timestamp":first(r,['source_publication_timestamp']),"source_evidence_sha256":first(r,['source_evidence_sha256'],row_sha(r)),"timing_candidate_id":"DTO-"+key_hash([cid,raw,first(r,['source_evidence_sha256'])],24),"builder_version":BUILDER_VERSION,"contract_version":CONTRACT_VERSION}
        if sec:
            base['timing_status']='TIMING_ACCEPTED'; out.append(base)
        else:
            base['timing_status']='TIMING_UNIT_UNSUPPORTED' if unit=='UNSUPPORTED_TIME_UNIT' else 'TIMING_NOT_PUBLISHED'; base['rejection_reason']=base['timing_status']; rej.append(base)
    write_csv_atomic(DATA/'edgeiq_daily_official_timing_candidate_v1.csv',out,FIELDS); write_csv_atomic(DATA/'edgeiq_daily_official_timing_rejections_v1.csv',rej,REJ_FIELDS)
    payload={"status":"PASS" if out or rej else "PASS_NO_NEW_DATA","operation_run_id":run_id,"timing_candidates":len(out),"rejections":len(rej),"mode":mode}; write_json_atomic(DATA/'edgeiq_daily_official_timing_ingestion_v1_summary.json',payload); print(json.dumps(payload,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
