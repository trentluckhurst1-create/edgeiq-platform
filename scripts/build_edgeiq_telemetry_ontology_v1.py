from __future__ import annotations

import csv
import re
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUTS = {
    "VIC_TELEMETRY_HEALTH": DATA / "edgeiq_telemetry_health_monitor_v1.csv",
    "VIC_LONGITUDINAL": DATA / "edgeiq_longitudinal_telemetry_accumulation_v1.csv",
    "QLD_INGESTION": DATA / "edgeiq_qld_telemetry_ingestion_v1.csv",
    "QLD_POSITIONAL": DATA / "edgeiq_qld_positional_telemetry_v1.csv",
    "NSW_RANKS": DATA / "edgeiq_nsw_positional_rank_telemetry_v2.csv",
    "NSW_TRANSITIONS": DATA / "edgeiq_nsw_rank_transition_states_v2.csv",
    "WA_INGESTION": DATA / "edgeiq_wa_telemetry_ingestion_v1.csv",
    "WA_LINEAGE": DATA / "edgeiq_wa_telemetry_lineage_v1.csv",
}

OUT = DATA / "edgeiq_telemetry_ontology_v1.csv"
SUMMARY = DATA / "edgeiq_telemetry_ontology_summary_v1.csv"
DICTIONARY = DATA / "edgeiq_telemetry_ontology_dictionary_v1.csv"
GAPS = DATA / "edgeiq_telemetry_ontology_gaps_v1.csv"

OUT_FIELDS = [
    "jurisdiction",
    "source_layer",
    "source_file",
    "race_date",
    "track",
    "race_no",
    "horse",
    "raw_signal_name",
    "raw_signal_value",
    "universal_signal_family",
    "universal_state",
    "universal_phase",
    "universal_movement",
    "universal_pressure",
    "telemetry_confidence",
    "lineage_confidence",
    "ontology_confidence",
    "safe_for_cross_jurisdiction_research",
    "safe_for_shadow_research",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

DICTIONARY_FIELDS = [
    "universal_signal_family",
    "definition",
    "source_jurisdictions",
    "source_layers",
    "example_raw_fields",
    "ontology_status",
    "notes",
]

GAP_FIELDS = [
    "jurisdiction",
    "gap_type",
    "affected_layer",
    "affected_rows",
    "severity",
    "recommended_repair",
    "notes",
]

def clean(v):
    return str(v or "").strip()

def upper(v):
    return clean(v).upper()

def read_csv(path):
    if not path.exists():
        return []
    try:
        with path.open("r", newline="", encoding="utf-8-sig", errors="ignore") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []

def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{time.time_ns()}")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({field: r.get(field, "") for field in fields})
    tmp.replace(path)

def parse_float(v, default=0.0):
    try:
        return float(clean(v).replace("%", ""))
    except Exception:
        return default

def normalise_track(v):
    text = upper(v)
    text = text.replace("&", " AND ")
    text = re.sub(r"\b(RACECOURSE|RACING|CLUB|TRACK|PARK)\b", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def normalise_horse(v):
    text = upper(v)
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"\b(NZ|AUS|GB|IRE|USA|FR|JPN)\b", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def yes(v):
    return upper(v) == "YES"

def family_from_raw(name, value):
    n = upper(name)
    v = upper(value)
    if any(t in n for t in ["RANK", "POSITION", "MOVEMENT", "PRESSURE", "LANE"]):
        return "POSITIONAL_RACE_STATE"
    if any(t in n for t in ["SPLIT", "SECTIONAL", "PHASE", "EARLY", "MID", "LATE", "LAST"]):
        return "TEMPORAL_PHASE"
    if any(t in n for t in ["GPS", "SPEED", "VELOCITY", "DISTANCE_TRAVELLED"]):
        return "SPEED_GPS_TELEMETRY"
    if any(t in n for t in ["LINEAGE", "SCHEMA", "SOURCE"]):
        return "LINEAGE_PROVENANCE"
    if any(t in n for t in ["HEALTH", "DRIFT", "DEGRAD", "CONFIDENCE"]):
        return "TELEMETRY_HEALTH"
    if any(t in v for t in ["ADVANC", "FADING", "LEADER", "MIDFIELD", "BACKMARKER", "PRESSURE"]):
        return "POSITIONAL_RACE_STATE"
    return "GENERAL_TELEMETRY"

def universal_state(value):
    v = upper(value)
    if "LEADER" in v:
        return "LEADER_STATE"
    if "PRESSURE" in v or "ON_PACE" in v:
        return "PRESSURE_STATE"
    if "MIDFIELD" in v or "PACK" in v:
        return "MIDFIELD_STATE"
    if "BACKMARKER" in v or "REAR" in v:
        return "BACKMARKER_STATE"
    if "STABLE" in v or "HOLDING" in v:
        return "STABLE_STATE"
    if "DECAY" in v or "DEGRAD" in v or "FADING" in v:
        return "DECAY_STATE"
    if "ADVANC" in v:
        return "ADVANCING_STATE"
    if "ELITE" in v or "HIGH" in v:
        return "HIGH_TRUST_STATE"
    if "USABLE" in v or "STRONG" in v:
        return "USABLE_STATE"
    return "UNCLASSIFIED_STATE"

def universal_phase(signal_name, value):
    text = f"{signal_name} {value}".upper()
    if "600" in text or "EARLY" in text:
        return "EARLY_PHASE"
    if "400" in text or "MID" in text:
        return "MID_PHASE"
    if "200" in text or "LATE" in text:
        return "LATE_PHASE"
    if "FINISH" in text:
        return "FINISH_PHASE"
    return "UNKNOWN_PHASE"

def universal_movement(value):
    v = upper(value)
    if "ADVANC" in v:
        return "ADVANCING"
    if "FADING" in v or "DROPPING" in v or "DECEL" in v:
        return "FADING"
    if "STABLE" in v or "HOLDING" in v:
        return "STABLE"
    if "ACCEL" in v:
        return "ACCELERATING"
    return "UNKNOWN_MOVEMENT"

def universal_pressure(value):
    v = upper(value)
    if "FRONT" in v or "LEADER" in v:
        return "FRONT_PRESSURE"
    if "PACE" in v or "PRESSURE" in v:
        return "PACE_PRESSURE"
    if "PACK" in v or "MIDFIELD" in v:
        return "PACK_PRESSURE"
    if "REAR" in v or "BACK" in v:
        return "REAR_PRESSURE"
    return "UNKNOWN_PRESSURE"

def conf_from_row(row):
    fields = [
        "telemetry_confidence", "extraction_confidence", "ingestion_confidence",
        "telemetry_health_score", "lineage_integrity_score", "phase_confidence_score",
        "ontology_confidence"
    ]
    vals = [parse_float(row.get(f), 0.0) for f in fields if clean(row.get(f))]
    if vals:
        return max(vals)
    grade = upper(row.get("telemetry_grade") or row.get("ingestion_quality_grade") or row.get("lineage_trust_grade"))
    return {"A": 92, "B": 82, "C": 68, "D": 48, "F": 20}.get(grade, 55)

def add_row(rows, jurisdiction, layer, source_file, base, signal_name, signal_value, note):
    fam = family_from_raw(signal_name, signal_value)
    tele_conf = conf_from_row(base)
    lineage_conf = parse_float(base.get("lineage_integrity_score"), tele_conf)
    ontology_conf = min(100.0, tele_conf * 0.65 + lineage_conf * 0.25 + (10 if fam != "GENERAL_TELEMETRY" else 0))
    rows.append({
        "jurisdiction": jurisdiction,
        "source_layer": layer,
        "source_file": source_file,
        "race_date": clean(base.get("race_date") or base.get("observation_date")),
        "track": normalise_track(base.get("track")),
        "race_no": clean(base.get("race_no")),
        "horse": normalise_horse(base.get("horse")),
        "raw_signal_name": signal_name,
        "raw_signal_value": signal_value,
        "universal_signal_family": fam,
        "universal_state": universal_state(signal_value),
        "universal_phase": universal_phase(signal_name, signal_value),
        "universal_movement": universal_movement(signal_value),
        "universal_pressure": universal_pressure(signal_value),
        "telemetry_confidence": f"{tele_conf:.2f}",
        "lineage_confidence": f"{lineage_conf:.2f}",
        "ontology_confidence": f"{ontology_conf:.2f}",
        "safe_for_cross_jurisdiction_research": "YES" if ontology_conf >= 58 and fam != "GENERAL_TELEMETRY" else "NO",
        "safe_for_shadow_research": "YES" if ontology_conf >= 78 and yes(base.get("safe_for_shadow_research") or base.get("safe_for_qld_shadow_research") or base.get("safe_for_nsw_shadow_research") or base.get("safe_for_wa_shadow_research")) else "NO",
        "notes": note,
    })

def main():
    ontology = []
    gaps = []

    for layer, path in INPUTS.items():
        rows = read_csv(path)
        if not rows:
            gaps.append({
                "jurisdiction": layer.split("_")[0],
                "gap_type": "MISSING_SOURCE_LAYER",
                "affected_layer": layer,
                "affected_rows": 0,
                "severity": "HIGH",
                "recommended_repair": f"Generate or verify {path.name}",
                "notes": "Ontology engine skipped missing layer. No modelling/execution.",
            })
            continue

        jurisdiction = layer.split("_")[0]
        for r in rows:
            if jurisdiction == "VIC":
                for field in ["telemetry_status","telemetry_stability_state","telemetry_decay_detected","payload_drift_detected","schema_drift_detected"]:
                    if clean(r.get(field)):
                        add_row(ontology, "VIC", layer, path.name, r, field, clean(r.get(field)), "VIC behavioural/telemetry state mapped into universal ontology.")
            elif jurisdiction == "QLD":
                for field in ["split_marker","early_phase_value","mid_phase_value","late_phase_value","gps_speed","movement_direction","acceleration_signature","spatial_pressure_state","running_order_state"]:
                    if clean(r.get(field)):
                        add_row(ontology, "QLD", layer, path.name, r, field, clean(r.get(field)), "QLD structured telemetry mapped into universal ontology.")
            elif jurisdiction == "NSW":
                for field in ["position_state","movement_state","race_state_pressure","transition_strength","rank_at_split","transition_status"]:
                    if clean(r.get(field)):
                        add_row(ontology, "NSW", layer, path.name, r, field, clean(r.get(field)), "NSW positional race-state telemetry mapped into universal ontology.")
            elif jurisdiction == "WA":
                for field in ["split_marker","sectional_time","position_value","gps_value","lineage_status"]:
                    if clean(r.get(field)):
                        add_row(ontology, "WA", layer, path.name, r, field, clean(r.get(field)), "WA operational telemetry mapped into universal ontology.")

    fams = Counter(r["universal_signal_family"] for r in ontology)
    jurisdictions_by_family = {}
    layers_by_family = {}
    fields_by_family = {}
    for r in ontology:
        fam = r["universal_signal_family"]
        jurisdictions_by_family.setdefault(fam, set()).add(r["jurisdiction"])
        layers_by_family.setdefault(fam, set()).add(r["source_layer"])
        fields_by_family.setdefault(fam, set()).add(r["raw_signal_name"])

    definitions = {
        "POSITIONAL_RACE_STATE": "Universal mapping for rank, position, movement, pressure and race-state evolution signals.",
        "TEMPORAL_PHASE": "Universal mapping for split, sectional, early/mid/late and finish-phase timing signals.",
        "SPEED_GPS_TELEMETRY": "Universal mapping for speed, GPS, velocity and distance-travelled style telemetry.",
        "LINEAGE_PROVENANCE": "Universal mapping for source, schema and telemetry provenance signals.",
        "TELEMETRY_HEALTH": "Universal mapping for drift, degradation, quality and confidence signals.",
        "GENERAL_TELEMETRY": "Payload fields that are not yet mapped to a stronger universal behavioural concept.",
    }

    dictionary = []
    for fam, count in fams.most_common():
        js = sorted(jurisdictions_by_family.get(fam, set()))
        ls = sorted(layers_by_family.get(fam, set()))
        fs = sorted(fields_by_family.get(fam, set()))
        status = "CORE_ONTOLOGY" if len(js) >= 2 and fam != "GENERAL_TELEMETRY" else "JURISDICTION_SPECIFIC" if fam != "GENERAL_TELEMETRY" else "UNMAPPED_GENERAL"
        dictionary.append({
            "universal_signal_family": fam,
            "definition": definitions.get(fam, ""),
            "source_jurisdictions": "|".join(js),
            "source_layers": "|".join(ls),
            "example_raw_fields": "|".join(fs[:20]),
            "ontology_status": status,
            "notes": f"{count} ontology rows mapped. Offline semantic telemetry layer only.",
        })

    by_jur = Counter(r["jurisdiction"] for r in ontology)
    by_safe = sum(1 for r in ontology if r["safe_for_cross_jurisdiction_research"] == "YES")
    by_shadow = sum(1 for r in ontology if r["safe_for_shadow_research"] == "YES")
    summary = [
        {"metric": "ontology_rows", "value": len(ontology)},
        {"metric": "dictionary_rows", "value": len(dictionary)},
        {"metric": "gap_rows", "value": len(gaps)},
        {"metric": "vic_rows", "value": by_jur.get("VIC", 0)},
        {"metric": "qld_rows", "value": by_jur.get("QLD", 0)},
        {"metric": "nsw_rows", "value": by_jur.get("NSW", 0)},
        {"metric": "wa_rows", "value": by_jur.get("WA", 0)},
        {"metric": "positional_race_state_rows", "value": fams.get("POSITIONAL_RACE_STATE", 0)},
        {"metric": "temporal_phase_rows", "value": fams.get("TEMPORAL_PHASE", 0)},
        {"metric": "speed_gps_rows", "value": fams.get("SPEED_GPS_TELEMETRY", 0)},
        {"metric": "telemetry_health_rows", "value": fams.get("TELEMETRY_HEALTH", 0)},
        {"metric": "lineage_provenance_rows", "value": fams.get("LINEAGE_PROVENANCE", 0)},
        {"metric": "safe_for_cross_jurisdiction_research_yes", "value": by_safe},
        {"metric": "safe_for_shadow_research_yes", "value": by_shadow},
        {"metric": "merged_raw_jurisdictions", "value": "NO"},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "offline_research_only", "value": "YES"},
    ]

    write_csv(OUT, ontology, OUT_FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    write_csv(DICTIONARY, dictionary, DICTIONARY_FIELDS)
    write_csv(GAPS, gaps, GAP_FIELDS)

    print("=" * 88)
    print("EDGEIQ TELEMETRY ONTOLOGY ENGINE V1")
    print("=" * 88)
    for row in summary:
        print(f"{row['metric']}: {row['value']}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {DICTIONARY}")
    print(f"saved: {GAPS}")

if __name__ == "__main__":
    main()
