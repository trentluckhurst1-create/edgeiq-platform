from __future__ import annotations
import argparse,json,subprocess,sys,time
from pathlib import Path
from edgeiq_daily_operations_common_v1 import *

def run_stage(run_id,name,cmd,args_extra):
    start=time.time(); full=[sys.executable,cmd,*args_extra]
    r=subprocess.run(full,cwd=ROOT,text=True,capture_output=True)
    result={"stage":name,"cmd":"python "+cmd+" "+" ".join(args_extra),"returncode":r.returncode,"runtime_seconds":round(time.time()-start,3),"stdout":r.stdout[-5000:],"stderr":r.stderr[-5000:]}
    stage_checkpoint(run_id,name,"PASS" if r.returncode==0 else "FAIL",{"rows":{},"hashes":{}},{"rows":{},"hashes":{},"rejected_rows":"0"},exception=r.stderr[-1000:],retryable=r.returncode in {2})
    return result

def main():
    parser=add_common_args(argparse.ArgumentParser()); args=parser.parse_args(); start,end,window_mode=resolve_date_window(args)
    mode=clean(args.mode).upper() or 'DAILY'; run_id=args.resume_run_id or operation_run_id('DAILYOPS',start,end)
    cfg=load_config(); lock_path=ROOT/clean(cfg.get('lock_path','public/data/edgeiq_daily_operations_engine_v1.lock.json'))
    lock=None
    if mode!='HEALTH_CHECK': lock=acquire_lock(lock_path,mode)
    stages=[]; started=time.time()
    try:
        child_window_mode = 'DEEP_BACKFILL' if start != end or mode in {'DRY_RUN','HEALTH_CHECK'} else window_mode
        common=['--mode',child_window_mode,'--date-from',start.isoformat(),'--date-to',end.isoformat()]
        if args.dry_run: common.append('--dry-run')
        if args.no_publish or args.dry_run: common.append('--no-publish')
        if args.fixture_root: common += ['--fixture-root', args.fixture_root, '--offline']
        if mode in {'DAILY','DRY_RUN','PREVIOUS_DAY','RESULTS_ONLY','CURRENT_DAY','CURRENT_DAY_REFRESH','BACKFILL'}:
            stages.append(run_stage(run_id,'race_discovery','scripts/build_edgeiq_daily_race_discovery_v1.py',common))
            stages.append(run_stage(run_id,'official_results','scripts/build_edgeiq_daily_official_results_ingestion_v1.py',common))
            stages.append(run_stage(run_id,'official_timing','scripts/build_edgeiq_daily_official_timing_ingestion_v1.py',common))
            stages.append(run_stage(run_id,'condition_evidence','scripts/build_edgeiq_daily_condition_evidence_v1.py',common))
        if mode in {'DAILY','DRY_RUN','SPEED_ONLY','BACKFILL','SPEED_PENDING_REFRESH'}:
            stages.append(run_stage(run_id,'delayed_speed','scripts/build_edgeiq_delayed_speed_data_ingestion_v1.py',common))
        if mode in {'DAILY','DRY_RUN','BACKFILL','SPEED_ONLY','RESULTS_ONLY','CURRENT_DAY','CURRENT_DAY_REFRESH'}:
            stages.append(run_stage(run_id,'lifecycle','scripts/build_edgeiq_race_data_lifecycle_fact_v1.py',common))
        if mode in {'DAILY','DRY_RUN','PREVIOUS_DAY','BACKFILL','RESULTS_ONLY'}:
            stages.append(run_stage(run_id,'canonical_timing_update','scripts/update_edgeiq_canonical_historical_timing_warehouse_v1.py',common))
        if mode in {'DAILY','FULL_REBUILD','PERFORMANCE_REFRESH_ONLY'} and not (args.dry_run or args.no_publish):
            stages.append(run_stage(run_id,'performance_refresh','scripts/run_edgeiq_incremental_performance_refresh_v1.py',common))
        elif mode in {'DAILY','DRY_RUN'}:
            stages.append(run_stage(run_id,'performance_refresh_dry_run','scripts/run_edgeiq_incremental_performance_refresh_v1.py',[*common,'--dry-run','--no-publish']))
        failed=[s for s in stages if s['returncode'] not in {0}]
        retryable=[s for s in stages if s['returncode']==2]
        final='PASS' if not failed else ('PARTIAL_RETRYABLE' if retryable and len(retryable)==len(failed) else 'FAILED_MANDATORY_STAGE')
        if not failed and all('PASS_NO_NEW_DATA' in s.get('stdout','') for s in stages[:2]): final='PASS_NO_NEW_DATA'
        lifecycle=read_csv(DATA/'edgeiq_race_data_lifecycle_fact_v1.csv')
        manifest={"operation_run_id":run_id,"mode":mode,"date_from":start.isoformat(),"date_to":end.isoformat(),"status":final,"started_at_utc":now_utc(),"total_runtime_seconds":round(time.time()-started,3),"stages":stages,"metrics":{"races_in_lifecycle":len(lifecycle),"pending_result_races":sum(1 for r in lifecycle if r.get('result_status')=='RESULT_PENDING'),"pending_timing_races":sum(1 for r in lifecycle if r.get('timing_status')=='TIME_PENDING'),"pending_condition_races":sum(1 for r in lifecycle if r.get('condition_status')=='CONDITION_PENDING'),"pending_speed_races":sum(1 for r in lifecycle if r.get('speed_status') in {'SPEED_PENDING','SPEED_DATA_PENDING'}),"timed_races":count_rows(DATA/'edgeiq_canonical_historical_timing_warehouse_v1.csv'),"performance_base":count_rows(DATA/'edgeiq_performance_intelligence_base_fact_v1.csv'),"normalisation_rows":count_rows(DATA/'edgeiq_performance_normalisation_fact_v1.csv'),"horse_ratings":count_rows(DATA/'edgeiq_horse_performance_rating_fact_v1.csv'),"epi_rows":count_rows(DATA/'edgeiq_epi_fact_v1.csv')}}
        write_json_atomic(DATA/'edgeiq_daily_operations_manifest_v1.json',manifest)
        write_csv_atomic(DATA/'edgeiq_daily_operations_summary_v1.csv',[{"metric":k,"value":v} for k,v in manifest['metrics'].items()]+[{"metric":"status","value":final},{"metric":"operation_run_id","value":run_id}],['metric','value'])
        alerts=[]
        if manifest['metrics']['normalisation_rows']==0: alerts.append({"operation_run_id":run_id,"severity":"INFO","category":"NORMALISATION_UNAVAILABLE","message":"No post-cutoff normalisation rows available or no eligible source rows yet.","created_at_utc":now_utc(),"builder_version":BUILDER_VERSION})
        for source in read_csv(DATA/'edgeiq_external_source_access_health_fact_v1.csv'):
            status=clean(source.get('access_status'))
            if status in {'SUPPORTED_CREDENTIAL_REQUIRED','SOURCE_ACCESS_FORBIDDEN','SUPPORTED_COMMERCIAL_ACCESS_REQUIRED','LEGAL_OR_LICENSING_REVIEW_REQUIRED','SUPPORTED_MANUAL_EXPORT_REQUIRED','SOURCE_CONTRACT_OBSOLETE'}:
                severity='ACTION_REQUIRED' if status in {'SUPPORTED_CREDENTIAL_REQUIRED','SOURCE_ACCESS_FORBIDDEN','SUPPORTED_MANUAL_EXPORT_REQUIRED','SUPPORTED_COMMERCIAL_ACCESS_REQUIRED','LEGAL_OR_LICENSING_REVIEW_REQUIRED'} else 'WARNING'
                alerts.append({"operation_run_id":run_id,"severity":severity,"category":status,"message":clean(source.get('source_name'))+" requires operator action: "+clean(source.get('operator_action_required')),"created_at_utc":now_utc(),"builder_version":BUILDER_VERSION})
            elif status=='SOURCE_DELAYED':
                alerts.append({"operation_run_id":run_id,"severity":"INFO","category":"SOURCE_PUBLICATION_DELAYED","message":clean(source.get('source_name'))+" has no governed new publication yet.","created_at_utc":now_utc(),"builder_version":BUILDER_VERSION})
        for source in read_csv(ROOT/'data'/'processed'/'racing-com-public-v1'/'source_health_fact.csv'):
            status=clean(source.get('status'))
            if status in {'CREDENTIAL_REQUIRED','SECTIONALS_ACCESS_REQUIRED','ACCESS_FORBIDDEN','SCHEMA_CHANGED','SECTIONALS_SCHEMA_CHANGED','UNKNOWN'}:
                severity='ACTION_REQUIRED' if status in {'CREDENTIAL_REQUIRED','SECTIONALS_ACCESS_REQUIRED'} else 'WARNING'
                alerts.append({"operation_run_id":run_id,"severity":severity,"category":'RACING_COM_PUBLIC_'+status,"message":clean(source.get('source'))+': '+clean(source.get('detail')),"created_at_utc":now_utc(),"builder_version":BUILDER_VERSION})
            elif status in {'SECTIONALS_PENDING','SECTIONALS_AVAILABLE','VISIBLE_PAGE_AVAILABLE','VISIBLE_PAGE_NO_SECTIONALS','VISIBLE_PAGE_PROMOTED'}:
                alerts.append({"operation_run_id":run_id,"severity":"INFO","category":'RACING_COM_PUBLIC_'+status,"message":clean(source.get('source'))+': '+clean(source.get('detail')),"created_at_utc":now_utc(),"builder_version":BUILDER_VERSION})
            elif status in {'VISIBLE_PAGE_ACCESS_BLOCKED','VISIBLE_PAGE_SCHEMA_CHANGED','VISIBLE_PAGE_VALIDATION_FAILED','VISIBLE_PAGE_TRANSIENT_FAILURE'}:
                alerts.append({"operation_run_id":run_id,"severity":"WARNING","category":'RACING_COM_PUBLIC_'+status,"message":clean(source.get('source'))+': '+clean(source.get('detail')),"created_at_utc":now_utc(),"builder_version":BUILDER_VERSION})
            elif status in {'PUBLIC_ANONYMOUS_CONFIRMED','SECTIONALS_VALIDATED','READY_FOR_PROMOTION','PROMOTED'}:
                alerts.append({"operation_run_id":run_id,"severity":"INFO","category":"RACING_COM_PUBLIC_SOURCE_OK","message":clean(source.get('source'))+' status '+status+'.',"created_at_utc":now_utc(),"builder_version":BUILDER_VERSION})
        for s in failed: alerts.append({"operation_run_id":run_id,"severity":"WARNING" if s['returncode']==2 else "CRITICAL","category":"AUDIT_FAILURE","message":s['stage']+" failed or retryable","created_at_utc":now_utc(),"builder_version":BUILDER_VERSION})
        write_csv_atomic(DATA/'edgeiq_daily_operations_alert_fact_v1.csv',alerts,['operation_run_id','severity','category','message','created_at_utc','builder_version'])
        run_dir=DOCS/'runs'/start.isoformat(); run_dir.mkdir(parents=True,exist_ok=True)
        md=['# EDGEiQ Daily Operations Report','',f'Run: {run_id}',f'Mode: {mode}',f'Date range: {start.isoformat()} to {end.isoformat()}',f'Status: {final}','', '## Metrics']
        for k,v in manifest['metrics'].items(): md.append(f'- {k}: {v}')
        md += ['','## Stage Results']
        for s in stages: md.append(f"- {s['stage']}: rc={s['returncode']} runtime={s['runtime_seconds']}s")
        (run_dir/'EDGEIQ_DAILY_OPERATIONS_REPORT.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
        print(json.dumps(manifest,indent=2)); return 0 if final in {'PASS','PASS_NO_NEW_DATA','PASS_WITH_PENDING_SOURCES'} else (2 if final=='PARTIAL_RETRYABLE' else 1)
    finally:
        if lock: release_lock(lock_path,lock)
if __name__=='__main__': raise SystemExit(main())
