from __future__ import annotations

import csv
import math
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
PHYSICS = DATA / "edgeiq_sectional_physics_validation_v1.csv"
OUT = DATA / "edgeiq_canonical_split_schema_v1.csv"

FIELDS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key",
    "distance",
    "sectional_race_key",
    "sectional_runner_key",
    "source_file",
    "source_lineage",
    "identity_status",
    "match_confidence",
    "payload_structure_type",
    "schema_variant",
    "reconstruction_method",
    "sectional_200",
    "sectional_400",
    "sectional_600",
    "last_600",
    "last_400",
    "last_200",
    "early_velocity",
    "mid_velocity",
    "late_velocity",
    "sustained_velocity",
    "fatigue_curve",
    "acceleration_curve",
    "payload_quality_grade",
    "physics_grade",
    "reconstruction_confidence",
    "sectional_confidence",
    "trusted_for_modelling",
    "trusted_for_execution",
    "canonical_status",
]


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


def fmt(value: float) -> str:
    return "" if math.isnan(value) else f"{value:.3f}".rstrip("0").rstrip(".")


def derive(row: dict[str, str]) -> dict[str, object] | None:
    if clean(row.get("physics_valid")).upper() != "YES":
        return None
    identity = clean(row.get("identity_status")).upper()
    if identity in {"UNSAFE", "UNMATCHED", ""}:
        return None
    physics_grade = clean(row.get("physics_grade")).upper()
    physics_confidence = number(row.get("physics_confidence"))
    reconstruction_confidence = number(row.get("reconstruction_confidence"))
    match_confidence = number(row.get("match_confidence"))
    if math.isnan(physics_confidence):
        physics_confidence = 0
    if math.isnan(reconstruction_confidence):
        reconstruction_confidence = 0
    if math.isnan(match_confidence):
        match_confidence = 0
    last_600 = number(row.get("last_600"))
    last_400 = number(row.get("last_400"))
    last_200 = number(row.get("last_200"))
    segments = [last_600 - last_400, last_400 - last_200, last_200] if not any(math.isnan(value) for value in [last_600, last_400, last_200]) else [math.nan, math.nan, math.nan]
    velocities = [200.0 / segment if not math.isnan(segment) and segment > 0 else math.nan for segment in segments]
    early_velocity = number(row.get("early_velocity"))
    mid_velocity = velocities[1]
    late_velocity = number(row.get("late_velocity")) or velocities[2]
    sustained_velocity = number(row.get("sustained_velocity"))
    if math.isnan(sustained_velocity) and not math.isnan(last_600) and last_600 > 0:
        sustained_velocity = 600.0 / last_600
    fatigue_curve = velocities[2] - velocities[0] if not (math.isnan(velocities[2]) or math.isnan(velocities[0])) else math.nan
    acceleration_curve = max(velocities) - min(velocities) if not any(math.isnan(value) for value in velocities) else math.nan
    sectional_confidence = round(match_confidence * 0.36 + reconstruction_confidence * 0.28 + physics_confidence * 0.36)
    modelling = "YES" if identity in {"TRUSTED", "LIKELY"} and physics_grade in {"ELITE", "GOOD", "PARTIAL"} and sectional_confidence >= 74 else "NO"
    execution = "YES" if identity == "TRUSTED" and physics_grade in {"ELITE", "GOOD"} and sectional_confidence >= 88 and reconstruction_confidence >= 78 else "NO"
    return {
        "race_date": clean(row.get("race_date")),
        "track": clean(row.get("track")),
        "race_no": clean(row.get("race_no")),
        "horse": clean(row.get("horse")),
        "horse_key": clean(row.get("horse_key")),
        "distance": clean(row.get("distance")),
        "sectional_race_key": clean(row.get("sectional_race_key")),
        "sectional_runner_key": clean(row.get("sectional_runner_key")),
        "source_file": clean(row.get("source_file")),
        "source_lineage": clean(row.get("source_lineage")),
        "identity_status": identity,
        "match_confidence": clean(row.get("match_confidence")),
        "payload_structure_type": clean(row.get("payload_structure_type")),
        "schema_variant": clean(row.get("schema_variant")),
        "reconstruction_method": clean(row.get("reconstruction_method")),
        "sectional_200": clean(row.get("sectional_200")),
        "sectional_400": clean(row.get("sectional_400")),
        "sectional_600": clean(row.get("sectional_600")),
        "last_600": clean(row.get("last_600")),
        "last_400": clean(row.get("last_400")),
        "last_200": clean(row.get("last_200")),
        "early_velocity": fmt(early_velocity),
        "mid_velocity": fmt(mid_velocity),
        "late_velocity": fmt(late_velocity),
        "sustained_velocity": fmt(sustained_velocity),
        "fatigue_curve": fmt(fatigue_curve),
        "acceleration_curve": fmt(acceleration_curve),
        "payload_quality_grade": clean(row.get("payload_structure_type")),
        "physics_grade": physics_grade,
        "reconstruction_confidence": clean(row.get("reconstruction_confidence")),
        "sectional_confidence": max(0, min(100, sectional_confidence)),
        "trusted_for_modelling": modelling,
        "trusted_for_execution": execution,
        "canonical_status": "CANONICAL_PHYSICS",
    }


def main() -> None:
    rows = [row for row in (derive(row) for row in read_csv(PHYSICS)) if row is not None]
    write_csv(OUT, rows, FIELDS)
    print("=" * 90)
    print("EDGEIQ CANONICAL SPLIT SCHEMA V1")
    print("=" * 90)
    print("ROWS:", len(rows))
    print("TRUSTED MODELLING:", sum(1 for row in rows if row["trusted_for_modelling"] == "YES"))
    print("TRUSTED EXECUTION:", sum(1 for row in rows if row["trusted_for_execution"] == "YES"))
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
