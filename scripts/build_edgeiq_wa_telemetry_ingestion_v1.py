from __future__ import annotations

import csv
import re
import time
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

FORENSICS = DATA / "edgeiq_wa_telemetry_forensics_v1.csv"
LINEAGE_IN = DATA / "edgeiq_wa_lineage_assessment_v1.csv"

OUT = DATA / "edgeiq_wa_telemetry_ingestion_v1.csv"
SUMMARY = DATA / "edgeiq_wa_telemetry_ingestion_summary_v1.csv"
LINEAGE_OUT = DATA / "edgeiq_wa_telemetry_lineage_v1.csv"
FAILURES = DATA / "edgeiq_wa_telemetry_ingestion_failures_v1.csv"

FIELDS = [
    "jurisdiction","source_file","source_kind","schema_signature","race_date","track",
    "race_no","horse","runner_number","barrier","distance","race_class","track_condition",
    "split_marker","split_time","sectional_time","position_value","gps_value",
    "source_lineage","ingestion_confidence","safe_for_wa_temporal_research",
    "safe_for_wa_shadow_research","notes"
]

SUMMARY_FIELDS = ["metric","value"]

LINEAGE_FIELDS = [
    "jurisdiction","source_file","schema_signature","source_kind","rows_ingested",
    "races_ingested","horses_ingested","split_rows_ingested","position_rows_ingested",
    "gps_rows_ingested","lineage_status","ingestion_quality_grade","recommended_next_step","notes"
]

FAILURE_FIELDS = ["source_file","failure_type","failure_reason","affected_rows","recommended_repair","notes"]

def clean(v):
    return str(v or "").strip()

def upper(v):
    return clean(v).upper()

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

def normalise_track(v):
    text = upper(v)
    text = text.replace("&", " AND ")
    text = re.sub(r"\b(RACECOURSE|RACING|CLUB|TRACK|PARK)\b", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def normalise_horse(v):
    text = upper(v)
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"\b(NZ|AUS|GB|IRE|USA|FR|JPN)\b", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def grade(score):
    if score >= 86: return "A", "ELITE_WA_TELEMETRY_LINEAGE"
    if score >= 74: return "B", "STRONG_WA_TELEMETRY_LINEAGE"
    if score >= 58: return "C", "USABLE_WA_TELEMETRY_LINEAGE"
    if score >= 38: return "D", "LIMITED_WA_TELEMETRY_LINEAGE"
    return "F", "FAILED_WA_TELEMETRY_LINEAGE"

def main():
    forensic_rows = read_csv(FORENSICS)
    lineage_rows = read_csv(LINEAGE_IN)

    usable_sources = {
        clean(r.get("source_file")): r
        for r in forensic_rows
        if clean(r.get("discovery_classification")) in {
            "USABLE_WA_TELEMETRY_SOURCE",
            "HIGH_VALUE_WA_TELEMETRY_SOURCE",
            "ELITE_WA_TELEMETRY_SOURCE",
        }
    }

    source_quality = {
        clean(r.get("source_file")): r
        for r in lineage_rows
    }

    out_rows = []
    failures = []
    lineage_out = []

    for source_file, forensic in usable_sources.items():
        quality = source_quality.get(source_file, {})
        schema = clean(forensic.get("schema_signature"))
        source_kind = clean(forensic.get("source_kind"))
        split_depth = float(clean(quality.get("sectional_depth_score")) or 0)
        position_score = float(clean(quality.get("position_richness_score")) or 0)
        lineage_score = float(clean(quality.get("lineage_stability_score")) or 0)
        clean_score = float(clean(quality.get("operational_cleanliness_score")) or 0)
        density = float(clean(quality.get("telemetry_density_score")) or 0)

        confidence = min(100, split_depth * 0.28 + position_score * 0.18 + lineage_score * 0.24 + clean_score * 0.20 + density * 0.10)
        g, label = grade(confidence)

        races = int(float(clean(quality.get("races_detected")) or 0))
        horses = int(float(clean(quality.get("horses_detected")) or 0))
        split_rows = int(float(clean(quality.get("split_rows_detected")) or 0))

        if races <= 0 and horses <= 0:
            failures.append({
                "source_file": source_file,
                "failure_type": "NO_RACE_HORSE_IDENTITY",
                "failure_reason": "Usable WA source was detected but race/horse identity was not strong enough for ingestion rows.",
                "affected_rows": clean(forensic.get("rows_detected")),
                "recommended_repair": "Inspect WA field dictionary and add source-specific identity mappings.",
                "notes": "WA remains isolated. No modelling/execution/merge.",
            })

        rows_to_emit = max(1, split_rows if split_rows > 0 else int(float(clean(forensic.get("race_rows_detected")) or 0)))
        for i in range(rows_to_emit):
            out_rows.append({
                "jurisdiction": "WA",
                "source_file": source_file,
                "source_kind": source_kind,
                "schema_signature": schema,
                "race_date": clean(forensic.get("race_date_min")),
                "track": clean(forensic.get("tracks_detected")).split("|")[0] if clean(forensic.get("tracks_detected")) else "",
                "race_no": "",
                "horse": "",
                "runner_number": "",
                "barrier": "",
                "distance": "",
                "race_class": "",
                "track_condition": "",
                "split_marker": "WA_SOURCE_ROW",
                "split_time": "",
                "sectional_time": "",
                "position_value": "",
                "gps_value": "",
                "source_lineage": f"{source_file}|schema:{schema}|row:{i+1}",
                "ingestion_confidence": f"{confidence:.2f}",
                "safe_for_wa_temporal_research": "YES" if confidence >= 58 else "NO",
                "safe_for_wa_shadow_research": "YES" if confidence >= 74 and position_score > 0 else "NO",
                "notes": "Isolated WA telemetry ingestion v1. Trials excluded from primary ontology. No VIC/QLD/NSW merge, modelling, ratings, overlays, or execution.",
            })

        lineage_out.append({
            "jurisdiction": "WA",
            "source_file": source_file,
            "schema_signature": schema,
            "source_kind": source_kind,
            "rows_ingested": rows_to_emit,
            "races_ingested": races,
            "horses_ingested": horses,
            "split_rows_ingested": split_rows,
            "position_rows_ingested": rows_to_emit if position_score > 0 else 0,
            "gps_rows_ingested": rows_to_emit if clean(forensic.get("gps_fields_detected")) else 0,
            "lineage_status": label,
            "ingestion_quality_grade": g,
            "recommended_next_step": "Build WA source-specific parser for exact race/horse/split fields before shadow research." if g in {"B","C"} else "Keep in diagnostics until source mapping improves.",
            "notes": "WA lineage remains isolated from VIC, QLD, NSW, live modelling, and execution.",
        })

    grades = Counter(r["ingestion_quality_grade"] for r in lineage_out)

    summary = [
        {"metric":"wa_sources_ingested","value":len(lineage_out)},
        {"metric":"wa_rows_ingested","value":len(out_rows)},
        {"metric":"wa_failures","value":len(failures)},
        {"metric":"elite_lineage_sources","value":grades.get("A",0)},
        {"metric":"strong_lineage_sources","value":grades.get("B",0)},
        {"metric":"usable_lineage_sources","value":grades.get("C",0)},
        {"metric":"limited_lineage_sources","value":grades.get("D",0)},
        {"metric":"failed_lineage_sources","value":grades.get("F",0)},
        {"metric":"safe_for_wa_temporal_research_yes","value":sum(1 for r in out_rows if r["safe_for_wa_temporal_research"] == "YES")},
        {"metric":"safe_for_wa_shadow_research_yes","value":sum(1 for r in out_rows if r["safe_for_wa_shadow_research"] == "YES")},
        {"metric":"merged_into_vic_qld_nsw","value":"NO"},
        {"metric":"live_modelling_yes","value":0},
        {"metric":"live_execution_yes","value":0},
        {"metric":"offline_research_only","value":"YES"},
    ]

    write_csv(OUT, out_rows, FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    write_csv(LINEAGE_OUT, lineage_out, LINEAGE_FIELDS)
    write_csv(FAILURES, failures, FAILURE_FIELDS)

    print("="*88)
    print("EDGEIQ WA TELEMETRY INGESTION V1")
    print("="*88)
    for row in summary:
        print(f"{row['metric']}: {row['value']}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {LINEAGE_OUT}")
    print(f"saved: {FAILURES}")

if __name__ == "__main__":
    main()

