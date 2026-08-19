from __future__ import annotations

import csv
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
PHYSICS = DATA / "edgeiq_sectional_physics_validation_v1.csv"
IDENTITY_V3 = DATA / "edgeiq_sectional_identity_engine_v3.csv"
OUT = DATA / "edgeiq_trusted_sectional_universe.csv"
SUMMARY = DATA / "edgeiq_trusted_sectional_universe_summary.csv"

FIELDS = [
    "race_date", "track", "race_no", "horse", "horse_key", "distance", "sectional_source",
    "source_lineage", "match_confidence", "identity_status", "identity_v2_status",
    "identity_v2_confidence", "identity_v3_status", "identity_v3_confidence",
    "runner_entity_confidence", "trusted_runner_identity", "trusted_race_identity",
    "trusted_modelling_identity", "trusted_execution_identity", "field_composition_confidence",
    "payload_structure_type", "physics_grade", "physics_confidence", "reconstruction_method",
    "reconstruction_confidence", "sectional_quality_grade", "sectional_confidence",
    "trusted_for_modelling", "trusted_for_execution", "raw_last_600", "raw_last_400",
    "raw_last_200", "early_speed_raw", "midrace_speed_raw", "late_speed_raw", "sustained_speed",
    "fatigue_index", "sectional_rating", "trust_notes",
]

SUMMARY_FIELDS = ["metric", "value"]


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"} else text


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{int(datetime.now().timestamp() * 1000)}.tmp")
    try:
        with tmp.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        tmp.replace(path)
    except PermissionError:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)


def number(value: object) -> float:
    raw = clean(value)
    if not raw:
        return math.nan
    try:
        return float(re.sub(r"[^0-9.\-]", "", raw))
    except ValueError:
        return math.nan


def confidence(value: object) -> int:
    parsed = number(value)
    return 0 if math.isnan(parsed) else max(0, min(100, int(round(parsed))))


def lineage(row: dict[str, str]) -> str:
    return clean(row.get("source_lineage")) or f"{clean(row.get('source_file'))}#{clean(row.get('source_row_id'))}"


def lookup(path: Path) -> dict[str, dict[str, str]]:
    return {lineage(row): row for row in read_csv(path)}


def rating_from_last_600(value: object, conf_value: object) -> str:
    last_600 = number(value)
    conf = number(conf_value)
    if math.isnan(last_600) or math.isnan(conf) or conf <= 0:
        return ""
    rating = max(0.0, min(100.0, 100.0 - (last_600 - 33.0) * 7.6))
    return f"{rating:.1f}"


def trust_decision(identity: dict[str, str], physics: dict[str, str]) -> tuple[str, str, int, str]:
    notes: list[str] = []
    modelling_identity = clean(identity.get("trusted_modelling_identity")).upper()
    execution_identity = clean(identity.get("trusted_execution_identity")).upper()
    runner_identity = clean(identity.get("trusted_runner_identity")).upper()
    race_identity = clean(identity.get("trusted_race_identity")).upper()
    identity_status = clean(identity.get("identity_v3_status")).upper()
    physics_valid = clean(physics.get("physics_valid")).upper() == "YES"
    physics_grade = clean(physics.get("physics_grade")).upper()
    reconstruction_conf = confidence(physics.get("reconstruction_confidence"))
    physics_conf = confidence(physics.get("physics_confidence"))
    id_conf = confidence(identity.get("identity_v3_confidence"))
    if modelling_identity not in {"YES", "PARTIAL"}:
        notes.append("identity v3 does not clear modelling")
    if runner_identity not in {"YES", "PARTIAL"}:
        notes.append("runner identity not trusted")
    if race_identity not in {"YES", "PARTIAL"}:
        notes.append("race identity not trusted")
    if not physics_valid or physics_grade in {"BROKEN", "WEAK", ""}:
        notes.append("physics/payload gate failed")
    if reconstruction_conf < 35:
        notes.append("reconstruction confidence too low")
    sectional_conf = round(id_conf * 0.46 + physics_conf * 0.34 + reconstruction_conf * 0.2)
    modelling = "NO"
    execution = "NO"
    if not notes and modelling_identity == "YES" and physics_valid:
        modelling = "YES"
    elif modelling_identity == "PARTIAL" and physics_valid and physics_grade in {"ELITE", "GOOD"}:
        modelling = "PARTIAL"
        notes.append("partial identity only")
    if modelling == "YES" and execution_identity == "YES" and runner_identity == "YES" and race_identity == "YES" and physics_grade in {"ELITE", "GOOD"} and sectional_conf >= 92:
        execution = "YES"
    elif modelling != "NO":
        notes.append("execution withheld by strict v3 gate")
    return modelling, execution, max(0, min(100, sectional_conf)), "; ".join(dict.fromkeys(notes)) if notes else "identity v3 and physics gates passed"


def main() -> None:
    physics_by_lineage = lookup(PHYSICS)
    rows: list[dict[str, object]] = []
    for identity in read_csv(IDENTITY_V3):
        line = lineage(identity)
        physics = physics_by_lineage.get(line, {})
        modelling, execution, sectional_conf, notes = trust_decision(identity, physics)
        if modelling == "NO":
            continue
        rows.append({
            "race_date": clean(identity.get("race_date")),
            "track": clean(identity.get("track")),
            "race_no": clean(identity.get("race_no")),
            "horse": clean(identity.get("horse")),
            "horse_key": clean(identity.get("horse_key")),
            "distance": clean(identity.get("distance")),
            "sectional_source": clean(identity.get("source_file")),
            "source_lineage": line,
            "match_confidence": clean(identity.get("identity_v3_confidence")),
            "identity_status": clean(identity.get("identity_v3_status")),
            "identity_v2_status": clean(identity.get("identity_v2_status")),
            "identity_v2_confidence": clean(identity.get("identity_v2_confidence")),
            "identity_v3_status": clean(identity.get("identity_v3_status")),
            "identity_v3_confidence": clean(identity.get("identity_v3_confidence")),
            "runner_entity_confidence": clean(identity.get("runner_entity_confidence")),
            "trusted_runner_identity": clean(identity.get("trusted_runner_identity")),
            "trusted_race_identity": clean(identity.get("trusted_race_identity")),
            "trusted_modelling_identity": clean(identity.get("trusted_modelling_identity")),
            "trusted_execution_identity": clean(identity.get("trusted_execution_identity")),
            "field_composition_confidence": clean(identity.get("field_composition_confidence")),
            "payload_structure_type": clean(physics.get("payload_structure_type")),
            "physics_grade": clean(physics.get("physics_grade")),
            "physics_confidence": clean(physics.get("physics_confidence")),
            "reconstruction_method": clean(physics.get("reconstruction_method")),
            "reconstruction_confidence": clean(physics.get("reconstruction_confidence")),
            "sectional_quality_grade": clean(physics.get("physics_grade")),
            "sectional_confidence": sectional_conf,
            "trusted_for_modelling": modelling,
            "trusted_for_execution": execution,
            "raw_last_600": clean(physics.get("last_600")),
            "raw_last_400": clean(physics.get("last_400")),
            "raw_last_200": clean(physics.get("last_200")),
            "early_speed_raw": clean(physics.get("early_velocity")),
            "midrace_speed_raw": clean(physics.get("mid_velocity")),
            "late_speed_raw": clean(physics.get("late_velocity")),
            "sustained_speed": clean(physics.get("sustained_velocity")),
            "fatigue_index": "",
            "sectional_rating": rating_from_last_600(physics.get("last_600"), sectional_conf),
            "trust_notes": notes,
        })
    identity_counts = Counter(str(row["identity_v3_status"]) for row in rows)
    physics_counts = Counter(str(row["physics_grade"]) for row in rows)
    summary = [
        {"metric": "trusted_universe_rows", "value": len(rows)},
        {"metric": "trusted_for_modelling", "value": sum(1 for row in rows if row["trusted_for_modelling"] == "YES")},
        {"metric": "partial_for_modelling", "value": sum(1 for row in rows if row["trusted_for_modelling"] == "PARTIAL")},
        {"metric": "trusted_for_execution", "value": sum(1 for row in rows if row["trusted_for_execution"] == "YES")},
        {"metric": "trusted_rows", "value": identity_counts.get("TRUSTED", 0)},
        {"metric": "likely_rows", "value": identity_counts.get("LIKELY", 0)},
        {"metric": "partial_rows", "value": identity_counts.get("PARTIAL", 0)},
    ]
    summary.extend({"metric": f"physics_{grade.lower()}", "value": count} for grade, count in sorted(physics_counts.items()))
    write_csv(OUT, rows, FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    print("=" * 90)
    print("EDGEIQ TRUSTED SECTIONAL UNIVERSE")
    print("=" * 90)
    print("ROWS:", len(rows))
    print("MODELLING TRUSTED:", sum(1 for row in rows if row["trusted_for_modelling"] == "YES"))
    print("EXECUTION TRUSTED:", sum(1 for row in rows if row["trusted_for_execution"] == "YES"))
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
