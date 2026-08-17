from __future__ import annotations
import argparse,json
from pathlib import Path
from edgeiq_daily_operations_common_v1 import *
RAW_FIELDS=["operation_run_id","source_name","source_file","source_row_number","source_observed_at","source_evidence_sha256","raw_payload_sha256","raw_status"]
FACT_FIELDS=["operation_run_id","canonical_race_id","canonical_meeting_id","race_date","track","race_number","distance_metres","track_condition","official_race_time_seconds","official_race_time_raw","race_status","official_status","field_size","runner_name","runner_source_id","source_horse_id","source_race_entry_id","horse_code","runner_id","race_entry_number","finish_position","placing_status","margin","starting_price","jockey","trainer","weight","barrier","source_publication_timestamp","source_evidence_sha256","result_status","builder_version","contract_version"]
REJ_FIELDS=FACT_FIELDS+["rejection_reason"]

def candidates(args,start,end):
    if args.fixture_root: return [(Path(args.fixture_root)/"official_results_fixture.csv", read_csv(Path(args.fixture_root)/"official_results_fixture.csv"))]
    paths=[DATA/"edgeiq_historical_results_warehouse_v2_graphql.csv",DATA/"race_results.csv",DATA/"results_history_clean.csv",DATA/"ra_calendar_official_results.csv",DATA/"ra_extracted_results.csv"]
    return [(p,read_csv(p)) for p in paths if p.exists()]

def main():
    parser=add_common_args(argparse.ArgumentParser()); args=parser.parse_args(); start,end,mode=resolve_date_window(args)
    run_id=args.resume_run_id or operation_run_id("RESULTS",start,end)
    raw=[]; facts=[]; rejected=[]; rowno=0
    for path,rows in candidates(args,start,end):
        for src in rows:
            if not in_window(src,start,end,["race_date","meeting_date","date"]): continue
            rowno+=1; ev=row_sha(src); raw.append({"operation_run_id":run_id,"source_name":path.stem,"source_file":str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),"source_row_number":rowno,"source_observed_at":now_utc(),"source_evidence_sha256":ev,"raw_payload_sha256":ev,"raw_status":"RAW_CAPTURED"})
            rdate=first(src,["race_date","meeting_date","date"]); track=first(src,["track","track_name","meeting_name"]); rno=first(src,["race_number","race_no","race"]); dist=first(src,["distance_metres","distance"])
            if not (rdate and track and rno):
                rejected.append({"operation_run_id":run_id,"race_date":rdate,"track":track,"race_number":rno,"source_evidence_sha256":ev,"result_status":"INVALID_SOURCE_RECORD","rejection_reason":"MISSING_RACE_IDENTITY","builder_version":BUILDER_VERSION,"contract_version":CONTRACT_VERSION}); continue
            cid=canonical_race_id(rdate,track,rno,dist); cmeet=canonical_meeting_id(rdate,track)
            finish=first(src,["finish_position","finished_position","position","pos"])
            runner=first(src,["horse","horse_name","runner_name","runner"])
            status="RESULT_OFFICIAL" if finish or first(src,["official_race_time_seconds","official_race_time","race_time"]) else "RESULT_PROVISIONAL"
            facts.append({"operation_run_id":run_id,"canonical_race_id":cid,"canonical_meeting_id":cmeet,"race_date":rdate,"track":track,"race_number":rno,"distance_metres":dist,"track_condition":first(src,["track_condition","condition","going"]),"official_race_time_seconds":first(src,["official_race_time_seconds","winner_race_time_seconds","race_time_seconds"]),"official_race_time_raw":first(src,["official_race_time","race_time","winning_time","official_race_time_seconds","winner_race_time_seconds","race_time_seconds"]),"race_status":"RACE_RUN","official_status":status,"field_size":first(src,["field_size","runners","starter_count"]),"runner_name":runner,"runner_source_id":first(src,["runner_source_id","source_runner_id","runner_id","horse_id"]),"source_horse_id":first(src,["source_horse_id","ra_horse_id","horse_code","horseCode"]),"source_race_entry_id":first(src,["source_race_entry_id","race_entry_id","race_entry_number","raceentry"]),"horse_code":first(src,["horse_code","horseCode","source_horse_id","ra_horse_id"]),"runner_id":first(src,["runner_id","source_runner_id"]),"race_entry_number":first(src,["race_entry_number","race_entry_id","source_race_entry_id","raceentry"]),"finish_position":finish,"placing_status":"PLACED" if finish in {"1","1.0","2","2.0","3","3.0"} else ("UNPLACED" if finish else ""),"margin":first(src,["margin","beaten_margin"]),"starting_price":first(src,["sp","starting_price","price"]),"jockey":first(src,["jockey","jockey_name"]),"trainer":first(src,["trainer","trainer_name"]),"weight":first(src,["weight","weight_carried_kg","weight_carried","weight_kg"]),"barrier":first(src,["barrier","barrier_number"]),"source_publication_timestamp":first(src,["source_publication_timestamp","updated_at","captured_at"]),"source_evidence_sha256":ev,"result_status":status,"builder_version":BUILDER_VERSION,"contract_version":CONTRACT_VERSION})
    write_csv_atomic(DATA/"edgeiq_daily_official_results_raw_snapshot_v1.csv",raw,RAW_FIELDS); write_csv_atomic(DATA/"edgeiq_daily_official_results_fact_v1.csv",facts,FACT_FIELDS); write_csv_atomic(DATA/"edgeiq_daily_official_results_rejections_v1.csv",rejected,REJ_FIELDS)
    payload={"status":"PASS" if facts or rejected else "PASS_NO_NEW_DATA","operation_run_id":run_id,"facts":len(facts),"raw_rows":len(raw),"rejections":len(rejected),"mode":mode,"date_from":start.isoformat(),"date_to":end.isoformat()}
    write_json_atomic(DATA/"edgeiq_daily_official_results_ingestion_v1_summary.json",payload); print(json.dumps(payload,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
