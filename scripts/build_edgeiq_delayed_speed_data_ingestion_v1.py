from __future__ import annotations
import argparse,json
from pathlib import Path
from edgeiq_daily_operations_common_v1 import *
FIELDS=["operation_run_id","canonical_race_id","canonical_runner_id","race_date","track","race_number","runner_name","source_race_id","source_runner_id","metric_name","raw_value","raw_unit","canonical_value","canonical_unit","source_timestamp","publication_timestamp","collection_timestamp","evidence_hash","source_authority","speed_status","parser_version","contract_version"]
def main():
    parser=add_common_args(argparse.ArgumentParser()); args=parser.parse_args(); start,end,mode=resolve_date_window(args)
    run_id=args.resume_run_id or operation_run_id('SPEED',start,end)
    speed_sources=[]
    for p in [DATA/'edgeiq_racingcom_runner_speed_fact_v1.csv', DATA/'racingcom_rendered_speed_data_normalised_v1.csv', DATA/'racingcom_rendered_speed_data_splits_v1.csv']:
        speed_sources += read_csv(p)
    races=read_csv(DATA/'edgeiq_daily_official_results_fact_v1.csv') or read_csv(DATA/'edgeiq_daily_race_discovery_v1.csv')
    rows=[]; matched=set()
    for s in speed_sources:
        if not in_window(s,start,end,['race_date','date','meeting_date']): continue
        track=first(s,['track','track_name','meeting_name']); rno=first(s,['race_number','race_no']); rdate=first(s,['race_date','date','meeting_date']); runner=first(s,['runner_name','horse','horse_name'])
        cid=canonical_race_id(rdate,track,rno,first(s,['distance_metres','distance'])); matched.add(cid)
        metric=first(s,['metric_name','speed_metric','sectional_name'],'SPEED_DATA')
        val=first(s,['canonical_value','value','raw_value','speed_value','last600','last_600'])
        rows.append({"operation_run_id":run_id,"canonical_race_id":cid,"canonical_runner_id":"EIQ_RUNNER-"+key_hash([cid,runner],16) if runner else '',"race_date":rdate,"track":track,"race_number":rno,"runner_name":runner,"source_race_id":first(s,['source_race_id','race_id']),"source_runner_id":first(s,['source_runner_id','runner_id']),"metric_name":metric,"raw_value":val,"raw_unit":first(s,['raw_unit','unit']),"canonical_value":val,"canonical_unit":first(s,['canonical_unit','unit']),"source_timestamp":first(s,['source_timestamp','captured_at']),"publication_timestamp":first(s,['publication_timestamp','updated_at']),"collection_timestamp":now_utc(),"evidence_hash":row_sha(s),"source_authority":"RACINGCOM_SPEED_DATA_OUTPUTS","speed_status":"SPEED_DATA_AVAILABLE" if val else "SPEED_DATA_PARTIAL","parser_version":BUILDER_VERSION,"contract_version":CONTRACT_VERSION})
    for r in races:
        if not in_window(r,start,end,['race_date','meeting_date']): continue
        cid=clean(r.get('canonical_race_id')) or canonical_race_id(first(r,['race_date','meeting_date']),first(r,['track','meeting_name']),first(r,['race_number','race_no']),first(r,['distance_metres','distance']))
        if cid not in matched:
            rows.append({"operation_run_id":run_id,"canonical_race_id":cid,"race_date":first(r,['race_date','meeting_date']),"track":first(r,['track','meeting_name']),"race_number":first(r,['race_number','race_no']),"collection_timestamp":now_utc(),"evidence_hash":first(r,['source_evidence_sha256'],row_sha(r)),"source_authority":"RACINGCOM_SPEED_DATA_OUTPUTS","speed_status":"SPEED_DATA_NOT_YET_PUBLISHED","parser_version":BUILDER_VERSION,"contract_version":CONTRACT_VERSION})
    write_csv_atomic(DATA/'edgeiq_delayed_speed_data_ingestion_v1.csv',rows,FIELDS)
    payload={"status":"PASS" if rows else "PASS_NO_NEW_DATA","operation_run_id":run_id,"speed_rows":len(rows),"available":sum(1 for r in rows if r['speed_status']=='SPEED_DATA_AVAILABLE'),"pending":sum(1 for r in rows if r['speed_status']=='SPEED_DATA_NOT_YET_PUBLISHED')}; write_json_atomic(DATA/'edgeiq_delayed_speed_data_ingestion_v1_summary.json',payload); print(json.dumps(payload,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
