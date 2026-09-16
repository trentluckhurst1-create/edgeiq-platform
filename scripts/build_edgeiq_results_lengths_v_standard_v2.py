from __future__ import annotations

import csv
import hashlib
import json
from decimal import Decimal, getcontext
from pathlib import Path

from edgeiq_length_conversion_method_v1 import resolve_length_conversion

getcontext().prec = 28
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "lengths-v-standard"
OBSERVATIONS = DATA / "edgeiq_results_elapsed_time_observations_v1.csv"
STANDARD_TIMES = DATA / "edgeiq_results_standard_times_v1.csv"
REGISTRY = ROOT / "config" / "performance-intelligence" / "edgeiq_canonical_surface_registry_v1.csv"
CANDIDATE = DATA / "edgeiq_results_lengths_v_standard_v2_CANDIDATE.csv"
FINAL = DATA / "edgeiq_results_lengths_v_standard_v2.csv"
SUMMARY = DOCS / "edgeiq_results_lengths_v_standard_v2_build_summary.json"
REPORT = DOCS / "edgeiq_results_lengths_v_standard_v2_build_report.md"
FIELDS = ["benchmark_group_id","canonical_race_id","canonical_runner_id","canonical_track","course_identity","source_surface","canonical_surface_group","race_date","track","race_number","race_distance_metres","segment_sequence","segment_start_metres","segment_end_metres","segment_distance_metres","actual_elapsed_seconds","standard_elapsed_seconds","time_difference_seconds","track_condition_number","track_condition_group","lengths_per_second","seconds_per_length","lengths_vs_standard","conversion_method","conversion_version","conversion_status","conversion_reason","source_hash","audit_status"]

def clean(value): return "" if value is None else str(value).strip()
def read_csv(path):
    if not path.exists(): return []
    with path.open("r",encoding="utf-8-sig",newline="") as handle:return list(csv.DictReader(handle))
def write_csv(path,rows,fields):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        for row in rows:writer.writerow({field:clean(row.get(field,"")) for field in fields})
def benchmark_group_id(row):
    key="|".join([clean(row.get("track")).upper().replace(" ",""),clean(row.get("race_distance_metres")),clean(row.get("segment_start_metres")),clean(row.get("segment_end_metres")),clean(row.get("segment_distance_metres"))])
    return "RSTG1-"+hashlib.sha256(key.encode("utf-8")).hexdigest()[:16].upper()
def registry_lookup(): return {clean(row.get("source_track_name")).upper().replace(" ",""):row for row in read_csv(REGISTRY)}
def resolve_surface(row,lookup):
    track=clean(row.get("track"));entry=lookup.get(track.upper().replace(" ",""))
    if entry:return entry
    if "SYNTHETIC" in track.upper():return {"canonical_track":track.replace(" Synthetic",""),"course_identity":track.upper().replace(" ","_"),"source_surface":"Synthetic","canonical_surface_group":"AUSTRALIAN_SYNTHETIC","status":"RESOLVED_AUSTRALIAN_SYNTHETIC"}
    return {"canonical_track":track,"course_identity":f"{track.upper().replace(' ','_')}_TURF","source_surface":"Turf","canonical_surface_group":"TURF","status":"RESOLVED_TURF"}
def infer_condition(row,standard):
    for field in ["track_condition_number","condition_number","track_rating_number","track_condition","condition","going"]:
        if clean(row.get(field)):return clean(row.get(field))
        if clean(standard.get(field)):return clean(standard.get(field))
    return ""
def decimal_text(value,places="0.000000"):return f"{value.quantize(Decimal(places))}"
def main():
    DOCS.mkdir(parents=True,exist_ok=True)
    observations=[row for row in read_csv(OBSERVATIONS) if clean(row.get("eligibility_status"))=="ELIGIBLE"]
    standards={clean(row.get("benchmark_group_id")):row for row in read_csv(STANDARD_TIMES)};lookup=registry_lookup();output=[]
    for row in observations:
        gid=benchmark_group_id(row);standard=standards.get(gid)
        if not standard:continue
        actual=Decimal(clean(row.get("elapsed_time_seconds")));standard_elapsed=Decimal(clean(standard.get("standard_elapsed_seconds")));time_difference=standard_elapsed-actual;surface=resolve_surface(row,lookup);condition=infer_condition(row,standard);resolved=resolve_length_conversion(surface.get("canonical_surface_group"),condition);status=resolved["status"]
        base={"benchmark_group_id":gid,"canonical_race_id":clean(row.get("canonical_race_id")),"canonical_runner_id":clean(row.get("canonical_runner_id")),"canonical_track":clean(surface.get("canonical_track")),"course_identity":clean(surface.get("course_identity")),"source_surface":clean(surface.get("source_surface")),"canonical_surface_group":resolved.get("surface_group",clean(surface.get("canonical_surface_group"))),"race_date":clean(row.get("race_date")),"track":clean(row.get("track")),"race_number":clean(row.get("race_number")),"race_distance_metres":clean(row.get("race_distance_metres")),"segment_sequence":clean(row.get("segment_sequence")),"segment_start_metres":clean(row.get("segment_start_metres")),"segment_end_metres":clean(row.get("segment_end_metres")),"segment_distance_metres":clean(row.get("segment_distance_metres")),"actual_elapsed_seconds":decimal_text(actual),"standard_elapsed_seconds":decimal_text(standard_elapsed),"time_difference_seconds":decimal_text(time_difference),"track_condition_number":condition,"track_condition_group":resolved["track_condition_group"],"lengths_per_second":resolved["lengths_per_second"],"seconds_per_length":resolved["seconds_per_length"],"conversion_method":"EDGEIQ_SURFACE_AWARE_LENGTHS_PER_SECOND_V2","conversion_version":resolved["method_version"],"conversion_status":status,"conversion_reason":resolved["reason"],"source_hash":clean(row.get("source_payload_sha256"))}
        if status in {"APPROVED_TURF_CONVERSION","APPROVED_AUSTRALIAN_SYNTHETIC_CONVERSION"}:
            lengths=time_difference*Decimal(resolved["lengths_per_second"]);output.append({**base,"lengths_vs_standard":decimal_text(lengths),"audit_status":"CALCULATED"})
        else:output.append({**base,"lengths_vs_standard":"","audit_status":status})
    write_csv(CANDIDATE,output,FIELDS);converted=[row for row in output if row["audit_status"]=="CALCULATED"];blocked=[row for row in output if row["audit_status"]!="CALCULATED"];synth=[row for row in converted if row["canonical_surface_group"]=="AUSTRALIAN_SYNTHETIC"]
    payload={"matched_observations":len(output),"converted_observations":len(converted),"blocked_observations":len(blocked),"australian_synthetic_converted_observations":len(synth),"candidate_hash":hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(),"status":"LENGTHS_V_STANDARD_V2_CANDIDATE_BUILT"}
    SUMMARY.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8");REPORT.write_text("# Results Lengths v Standard V2 Build\n\n"+f"Status: `{payload['status']}`\n\nMatched observations: `{len(output)}`\n\nConverted observations: `{len(converted)}`\n",encoding="utf-8");print(json.dumps(payload,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
