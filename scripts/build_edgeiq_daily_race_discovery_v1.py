from __future__ import annotations
import argparse, json
from pathlib import Path
from edgeiq_daily_operations_common_v1 import *

FIELDS=["operation_run_id","requested_date","jurisdiction","state","meeting_date","meeting_name","canonical_meeting_id","source_meeting_id","race_number","canonical_race_id","source_race_id","race_name","scheduled_time","distance_metres","surface","current_condition","race_status","source_authority","source_url","source_observed_at","source_evidence_sha256","discovery_status","builder_version","contract_version"]
REJ_FIELDS=FIELDS+["rejection_reason"]

def source_rows(fixture_root: str=""):
    if fixture_root:
        return read_csv(Path(fixture_root)/"daily_race_discovery_fixture.csv")
    return read_csv(DATA/"edgeiq_vic_three_day_race_list_v1.csv") + read_csv(DATA/"edgeiq_vic_three_day_meeting_universe.csv")

def main():
    parser=add_common_args(argparse.ArgumentParser())
    args=parser.parse_args(); start,end,mode=resolve_date_window(args)
    run_id=args.resume_run_id or operation_run_id("DISCOVERY",start,end)
    rows=[]; rejected=[]; seen=set()
    for src in source_rows(args.fixture_root):
        if not in_window(src,start,end,["race_date","meeting_date","date"]): continue
        track=first(src,["track","normalised_track","meeting_name","track_name"])
        rno=first(src,["race_no","race_number","race"])
        mdate=first(src,["race_date","meeting_date","date"], start.isoformat())
        if args.track and norm_track(track)!=norm_track(args.track): continue
        if not track or not rno:
            out={k:"" for k in REJ_FIELDS}; out.update({"operation_run_id":run_id,"requested_date":start.isoformat(),"source_evidence_sha256":row_sha(src),"discovery_status":"INVALID_SOURCE_RECORD","rejection_reason":"MISSING_TRACK_OR_RACE_NUMBER","builder_version":BUILDER_VERSION,"contract_version":CONTRACT_VERSION}); rejected.append(out); continue
        dist=first(src,["distance_metres","distance","distance_m"])
        cid=canonical_race_id(mdate,track,rno,dist); cmeet=canonical_meeting_id(mdate,track)
        key=cid
        if key in seen: continue
        seen.add(key)
        rows.append({
            "operation_run_id":run_id,"requested_date":start.isoformat(),"jurisdiction":"AU","state":clean(args.state or "VIC"),"meeting_date":mdate,"meeting_name":track,"canonical_meeting_id":cmeet,"source_meeting_id":first(src,["source_meeting_id","meeting_id","meetingId"]),"race_number":rno,"canonical_race_id":cid,"source_race_id":first(src,["source_race_id","race_id","raceId"]),"race_name":first(src,["race_name","name"]),"scheduled_time":first(src,["scheduled_time","race_time","time"]),"distance_metres":dist,"surface":first(src,["surface","surface_group"],"TURF"),"current_condition":first(src,["condition","track_condition","current_condition"]),"race_status":first(src,["race_status","status"],"SCHEDULED"),"source_authority":"RACINGCOM_THREE_DAY_PRODUCT_CATALOG" if not args.fixture_root else "FIXTURE", "source_url":first(src,["source_url","url"]),"source_observed_at":now_utc(),"source_evidence_sha256":row_sha(src),"discovery_status":"DISCOVERED","builder_version":BUILDER_VERSION,"contract_version":CONTRACT_VERSION})
    write_csv_atomic(DATA/"edgeiq_daily_race_discovery_v1.csv",rows,FIELDS); write_csv_atomic(DATA/"edgeiq_daily_race_discovery_v1_rejections.csv",rejected,REJ_FIELDS)
    payload={"status":"PASS" if rows or rejected else "PASS_NO_NEW_DATA","mode":mode,"date_from":start.isoformat(),"date_to":end.isoformat(),"operation_run_id":run_id,"races_discovered":len(rows),"rejections":len(rejected)}
    write_json_atomic(DATA/"edgeiq_daily_race_discovery_v1_summary.json",payload); print(json.dumps(payload,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
