from __future__ import annotations

import csv
import re
import time
from collections import Counter
from pathlib import Path

try:
    import requests
except Exception:
    requests = None

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_ASSETS = DATA / "edgeiq_qld_source_page_asset_inspection_v1.csv"

OUT = DATA / "edgeiq_qld_asset_schema_extraction_v1.csv"
SUMMARY = DATA / "edgeiq_qld_asset_schema_summary_v1.csv"
CANDIDATES = DATA / "edgeiq_qld_explicit_position_schema_candidates_v1.csv"
FAILURES = DATA / "edgeiq_qld_asset_schema_failures_v1.csv"

OUT_FIELDS = [
    "track","source_url","asset_url","asset_type","asset_hint","schema_fields_detected",
    "runner_identity_detected","horse_identity_detected","timestamp_detected",
    "coordinate_schema_detected","lane_path_schema_detected","distance_off_rail_detected",
    "running_order_detected","rank_schema_detected","position_map_schema_detected",
    "speed_vector_detected","schema_quality_grade","schema_status","recommended_next_step","notes"
]

SUMMARY_FIELDS = ["metric","value"]

CANDIDATE_FIELDS = [
    "priority","track","source_url","asset_url","schema_quality_grade","schema_status",
    "schema_fields_detected","expected_research_value","recommended_action","notes"
]

FAILURE_FIELDS = [
    "track","source_url","asset_url","failure_type","failure_reason","recommended_repair","notes"
]

def clean(v):
    return str(v or "").strip()

def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig", errors="ignore") as f:
        return list(csv.DictReader(f))

def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{time.time_ns()}")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({field: r.get(field, "") for field in fields})
    tmp.replace(path)

def fetch(url):
    if requests is None or not url.lower().startswith(("http://", "https://")):
        return "", "NO_REQUESTS_OR_INVALID_URL"
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "EDGEiQ research schema inspection"})
        if r.status_code >= 400:
            return "", f"HTTP_{r.status_code}"
        return r.text[:500000], "FETCHED"
    except Exception as e:
        return "", f"FETCH_FAILED_{type(e).__name__}"

def detect(text, url):
    blob = (text + " " + url).lower()

    fields = sorted(set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]{2,60}\b', blob)))
    keep = [f for f in fields if any(t in f.lower() for t in [
        "horse","runner","saddle","tab","barrier","time","date","timestamp",
        "lat","lng","long","coord","xpos","ypos","rail","lane","path",
        "position","map","rank","order","speed","velocity","distance","gps","split"
    ])]

    runner = any(t in blob for t in ["runner", "runnerid", "saddle", "tabnumber", "tab_no"])
    horse = any(t in blob for t in ["horse", "horsename", "horse_name", "runnername"])
    timestamp = any(t in blob for t in ["timestamp", "datetime", "race_time", "created"])
    coordinate = any(t in blob for t in ["latitude", "longitude", "coordinate", "xpos", "ypos", "x_pos", "y_pos"])
    lane_path = any(t in blob for t in ["lane", "path", "off rail", "off_rail", "track position", "position map"])
    off_rail = any(t in blob for t in ["off rail", "off_rail", "distance off rail", "distance_off_rail"])
    running_order = any(t in blob for t in ["running order", "running_order", "inrunning", "in_running"])
    rank = any(t in blob for t in ["rank", "position_rank", "section_rank"])
    position_map = any(t in blob for t in ["position map", "positionmap", "position_map", "map"])
    speed = any(t in blob for t in ["speed", "top_speed", "topspeed", "velocity", "gps"])

    if rank and (runner or horse):
        grade, status = "A", "EXPLICIT_POSITION_SCHEMA_CONFIRMED"
    elif coordinate and (runner or horse):
        grade, status = "B", "STRONG_GPS_PATH_SCHEMA"
    elif (lane_path or position_map or speed) and (runner or horse):
        grade, status = "C", "USABLE_POSITIONAL_PROXY_SCHEMA"
    elif lane_path or position_map or speed or rank or coordinate:
        grade, status = "D", "WEAK_SCHEMA_HINT"
    else:
        grade, status = "F", "NO_USABLE_SCHEMA"

    return keep[:80], runner, horse, timestamp, coordinate, lane_path, off_rail, running_order, rank, position_map, speed, grade, status

def main():
    rows = read_csv(IN_ASSETS)
    out = []
    candidates = []
    failures = []

    for r in rows:
        asset_url = clean(r.get("asset_url")) or clean(r.get("source_url"))
        source_url = clean(r.get("source_url"))
        hint = clean(r.get("asset_hint"))

        if hint not in {"HIGH_VALUE_POSITION_ASSET", "GPS_PATH_ASSET", "COORDINATE_ASSET"}:
            continue

        text, status = fetch(asset_url)
        fields, runner, horse, timestamp, coordinate, lane_path, off_rail, running_order, rank, position_map, speed, grade, schema_status = detect(text, asset_url)

        if not text:
            failures.append({
                "track": clean(r.get("track")),
                "source_url": source_url,
                "asset_url": asset_url,
                "failure_type": status,
                "failure_reason": "Asset/source was not text-readable through polite request.",
                "recommended_repair": "Manual browser/network inspection or local downloaded asset required.",
                "notes": "QLD schema extraction only. No modelling/execution."
            })

        result = {
            "track": clean(r.get("track")),
            "source_url": source_url,
            "asset_url": asset_url,
            "asset_type": clean(r.get("asset_type")),
            "asset_hint": hint,
            "schema_fields_detected": "|".join(fields),
            "runner_identity_detected": "YES" if runner else "NO",
            "horse_identity_detected": "YES" if horse else "NO",
            "timestamp_detected": "YES" if timestamp else "NO",
            "coordinate_schema_detected": "YES" if coordinate else "NO",
            "lane_path_schema_detected": "YES" if lane_path else "NO",
            "distance_off_rail_detected": "YES" if off_rail else "NO",
            "running_order_detected": "YES" if running_order else "NO",
            "rank_schema_detected": "YES" if rank else "NO",
            "position_map_schema_detected": "YES" if position_map else "NO",
            "speed_vector_detected": "YES" if speed else "NO",
            "schema_quality_grade": grade,
            "schema_status": schema_status,
            "recommended_next_step": "Build source-specific parser after manual schema verification." if grade in {"A","B","C"} else "Keep as diagnostics only.",
            "notes": f"fetch_status={status}. Offline QLD asset schema extraction only. No modelling/execution."
        }
        out.append(result)

        if grade in {"A","B","C"}:
            candidates.append({
                "priority": "HIGH" if grade == "A" else "MEDIUM",
                "track": result["track"],
                "source_url": source_url,
                "asset_url": asset_url,
                "schema_quality_grade": grade,
                "schema_status": schema_status,
                "schema_fields_detected": result["schema_fields_detected"],
                "expected_research_value": "Potential QLD explicit/richer positional or GPS/path schema.",
                "recommended_action": "Manually verify schema stability before parser build.",
                "notes": "Research-only. No execution."
            })

    counts = Counter(r["schema_quality_grade"] for r in out)

    summary = [
        {"metric":"assets_inspected","value":len(out)},
        {"metric":"explicit_position_schema_confirmed","value":counts.get("A",0)},
        {"metric":"strong_gps_path_schema","value":counts.get("B",0)},
        {"metric":"usable_positional_proxy_schema","value":counts.get("C",0)},
        {"metric":"weak_schema_hint","value":counts.get("D",0)},
        {"metric":"no_usable_schema","value":counts.get("F",0)},
        {"metric":"runner_identity_detected_rows","value":sum(1 for r in out if r["runner_identity_detected"]=="YES")},
        {"metric":"coordinate_schema_detected_rows","value":sum(1 for r in out if r["coordinate_schema_detected"]=="YES")},
        {"metric":"lane_path_schema_detected_rows","value":sum(1 for r in out if r["lane_path_schema_detected"]=="YES")},
        {"metric":"rank_schema_detected_rows","value":sum(1 for r in out if r["rank_schema_detected"]=="YES")},
        {"metric":"position_map_schema_detected_rows","value":sum(1 for r in out if r["position_map_schema_detected"]=="YES")},
        {"metric":"candidate_rows","value":len(candidates)},
        {"metric":"failure_rows","value":len(failures)},
        {"metric":"live_modelling_yes","value":0},
        {"metric":"live_execution_yes","value":0},
        {"metric":"offline_research_only","value":"YES"}
    ]

    write_csv(OUT, out, OUT_FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    write_csv(CANDIDATES, candidates, CANDIDATE_FIELDS)
    write_csv(FAILURES, failures, FAILURE_FIELDS)

    print("=" * 88)
    print("EDGEIQ QLD ASSET SCHEMA EXTRACTION V1")
    print("=" * 88)
    for row in summary:
        print(f"{row['metric']}: {row['value']}")

if __name__ == "__main__":
    main()
