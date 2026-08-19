
from __future__ import annotations
import argparse, csv, json, os
from collections import defaultdict
from pathlib import Path
from edgeiq_racing_com_public_common_v1 import *
FIELDS_SECTIONAL=['source_provider','source_endpoint','source_resource_url_hash','source_meeting_id','source_race_id','source_runner_id','meeting_date','venue','race_number','race_distance_metres','runner_name','saddlecloth_number','finish_position','section_start_metres','section_end_metres','section_distance_metres','section_time_seconds','section_rank','cumulative_time_seconds','distance_from_finish_metres','timing_unit_original','timing_unit_normalised','source_retrieved_at','source_published_at','response_hash','provenance_status','identity_status','validation_status']

def make_facts():
    ensure(); speed=read_csv(PUB/'edgeiq_racingcom_runner_speed_fact_v1.csv'); sect=read_csv(PUB/'edgeiq_racingcom_runner_sectional_fact_v1.csv'); split=read_csv(PUB/'edgeiq_racingcom_runner_split_fact_v1.csv')
    speed_by_runner={(r.get('race_key',''),r.get('runner_id','')):r for r in speed}
    race_fact={}; timing_fact={}; runner_fact=[]
    for r in speed:
        rk=r.get('race_key',''); race_no=first(r,['race_number']); race_id=rk
        race_fact.setdefault(rk,{'source_provider':'RACING.COM','source_endpoint':'getRaceForm retained local payload','source_race_id':race_id,'race_key':rk,'meeting_date':r.get('race_date',''),'venue':r.get('track',''),'race_number':race_no,'race_distance_metres':'','has_sectionals':'YES' if r.get('sectional_count') else 'UNKNOWN','has_results':'YES','source_page_url':r.get('source_page_url',''),'source_payload_file':r.get('source_payload_file',''),'provenance_status':'LOCAL_GOVERNED_EVIDENCE_DIRECT_PUBLIC_NOT_CONFIRMED'})
        timing_fact.setdefault(rk,{'source_provider':'RACING.COM','source_endpoint':'getRaceForm retained local payload','race_key':rk,'meeting_date':r.get('race_date',''),'venue':r.get('track',''),'race_number':race_no,'race_time_raw':r.get('race_time_raw',''),'race_time_seconds':r.get('race_time_seconds',''),'timing_source':r.get('timing_source',''),'is_timing_complete':r.get('is_timing_complete',''),'response_hash':sha_file(ROOT/r.get('source_payload_file','')),'provenance_status':'LOCAL_GOVERNED_EVIDENCE_DIRECT_PUBLIC_NOT_CONFIRMED'})
        runner_fact.append({'source_provider':'RACING.COM','source_endpoint':'getRaceForm retained local payload','race_key':rk,'source_runner_id':r.get('runner_id',''),'meeting_date':r.get('race_date',''),'venue':r.get('track',''),'race_number':race_no,'runner_name':r.get('horse_name',''),'saddlecloth_number':r.get('saddle_number',''),'finish_position':r.get('finish_position',''),'runner_race_time_seconds':r.get('runner_race_time_seconds',''),'six_hundred_metres_time_seconds':r.get('six_hundred_metres_time_seconds',''),'two_hundred_metres_time_seconds':r.get('two_hundred_metres_time_seconds',''),'source_payload_file':r.get('source_payload_file',''),'response_hash':sha_file(ROOT/r.get('source_payload_file','')),'provenance_status':'LOCAL_GOVERNED_EVIDENCE_DIRECT_PUBLIC_NOT_CONFIRMED'})
    sectional=[]
    cum_by_key={(r.get('race_key',''),r.get('runner_id',''),r.get('distance_marker','').upper().replace('M','')):r for r in sect}
    for r in split:
        start,end,dist=split_bounds(r.get('split_distance',''))
        sp=speed_by_runner.get((r.get('race_key',''),r.get('runner_id','')),{})
        t=safe_float(r.get('split_time_seconds'))
        validation='PASS'
        if not start or not end or not dist: validation='UNIT_AMBIGUITY'
        elif t is None or t<=0: validation='BAD_SECTION_TIME'
        elif int(dist or 0)>=100 and (t<4 or t>60): validation='SECTION_TIME_IMPLAUSIBLE'
        payload=ROOT/r.get('source_payload_file','')
        cumulative=(cum_by_key.get((r.get('race_key',''),r.get('runner_id',''),end)) or {}).get('cumulative_time_seconds','')
        sectional.append({'source_provider':'RACING.COM','source_endpoint':'getRaceForm data.sectionaltimes_callback.Horses[].SplitTimes','source_resource_url_hash':sha_bytes((sp.get('source_page_url','') or r.get('source_payload_file','')).encode()),'source_meeting_id':'','source_race_id':r.get('race_key',''),'source_runner_id':r.get('runner_id',''),'meeting_date':r.get('race_date',''),'venue':r.get('track',''),'race_number':r.get('race_number',''),'race_distance_metres':max(start,end) if start and end else '','runner_name':r.get('horse_name',''),'saddlecloth_number':r.get('saddle_number',''),'finish_position':sp.get('finish_position',''),'section_start_metres':start,'section_end_metres':end,'section_distance_metres':dist,'section_time_seconds':r.get('split_time_seconds',''),'section_rank':r.get('position',''),'cumulative_time_seconds':cumulative,'distance_from_finish_metres':end,'timing_unit_original':'metres-from-finish split label','timing_unit_normalised':'section_start_metres_to_section_end_metres_from_finish','source_retrieved_at':'','source_published_at':'','response_hash':sha_file(payload),'provenance_status':'LOCAL_GOVERNED_EVIDENCE_DIRECT_PUBLIC_NOT_CONFIRMED','identity_status':'PASS' if r.get('runner_id') and r.get('horse_name') else 'MISSING_IDENTITY','validation_status':validation})
    write_csv(PROCESSED/'race_fact.csv',race_fact.values())
    write_csv(PROCESSED/'runner_result_fact.csv',runner_fact)
    write_csv(PROCESSED/'race_timing_fact.csv',timing_fact.values())
    write_csv(PROCESSED/'runner_sectional_fact.csv',sectional,FIELDS_SECTIONAL)
    prov=[{'source':'Racing.com retained getRaceForm payloads','source_path':'outputs/sectionals/raw/VIC/racingcom_full_payloads/getRaceForm_*.json','access_classification':'LOCAL_GOVERNED_EVIDENCE_DIRECT_PUBLIC_NOT_CONFIRMED','rows_normalised':len(sectional),'canonical_admission':'NO','reason':'Public anonymous runner-sectional replay not confirmed'}]
    health=[{'source':'Racing.com meeting catalogue appv2','status':'PUBLIC_ANONYMOUS_CONFIRMED','checked_at':now(),'detail':'Safe public catalogue endpoint used for meeting discovery'}, {'source':'Racing.com GraphQL runner sectionals','status':'SECTIONALS_ACCESS_REQUIRED','checked_at':now(),'detail':'Exact request is known; clean anonymous replay requires approved application credential'}]
    write_csv(PROCESSED/'source_provenance_fact.csv',prov); write_csv(PROCESSED/'source_health_fact.csv',health)
    return {'races':len(race_fact),'runner_results':len(runner_fact),'runner_sectional_rows':len(sectional),'validation_pass':sum(1 for r in sectional if r['validation_status']=='PASS')}


def fetch_runner_sectionals(meeting_code: str = "5191101", race_number: str = "1", output_root: str | None = None) -> dict:
    """Credential-ready runner sectionals fetch wrapper. Does not promote canonical rows."""
    import subprocess, sys
    out_root = output_root or str(DOC / "completion")
    cmd = [sys.executable, "scripts/replay_racing_com_runner_sectionals_v1.py", "--meeting-code", meeting_code, "--race-number", race_number, "--mode", "APPROVED_CREDENTIAL", "--output-root", out_root]
    run = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    matrix = read_csv(Path(out_root) / "runner_sectionals_access_matrix.csv")
    return {"returncode": run.returncode, "rows": matrix, "stdout_tail": run.stdout[-1000:], "stderr_tail": run.stderr[-1000:]}


def fetch_runner_sectionals_csv(input_file: str, output_root: str | None = None) -> dict:
    """Official operator file import wrapper. Preview only; no canonical promotion."""
    import subprocess, sys
    out_root = output_root or str(DOC / "completion" / "official-import")
    cmd = [sys.executable, "scripts/import_racing_com_runner_sectionals_official_file_v1.py", "--input-file", input_file, "--output-root", out_root]
    run = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    summary_path = Path(out_root) / "official_import_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    return {"returncode": run.returncode, "summary": summary, "stdout_tail": run.stdout[-1000:], "stderr_tail": run.stderr[-1000:]}


def discover_meetings():
    ensure(); r=request_public(APPV2_MEETS.format(year=2026,month=7)); raw=RAW/'meeting'/('appv2_get_meets_2026_7_'+str(r['status'])+'.json'); write_text(raw,redact_text(r['body'].decode('utf-8','ignore'))); return {'status':r['status'],'path':str(raw.relative_to(ROOT))}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mode',default='all',choices=['discover_meetings','fetch_meeting_races','fetch_race_form','fetch_results','fetch_race_timing','check_sectional_availability','fetch_runner_sectionals','fetch_sectional_download_metadata','all']); args=ap.parse_args()
    out={'mode':args.mode,'generated_at':now()}
    if args.mode in ('discover_meetings','all'): out['discover_meetings']=discover_meetings()
    if args.mode in ('fetch_meeting_races','fetch_race_form','fetch_results','fetch_race_timing','check_sectional_availability','fetch_runner_sectionals','fetch_sectional_download_metadata','all'): out['processed']=make_facts()
    write_json(DOC/'adapter_last_run.json',out); print(json.dumps(out,indent=2))
if __name__=='__main__': main()
