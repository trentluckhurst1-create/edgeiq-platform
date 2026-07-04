from __future__ import annotations

import csv
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
RECON = DATA / "edgeiq_sectional_payload_reconstruction_v1.csv"
OUT = DATA / "edgeiq_sectional_physics_validation_v1.csv"
SUMMARY = DATA / "edgeiq_sectional_physics_summary_v1.csv"

FIELDS = [
    "sectional_race_key",
    "sectional_runner_key",
    "source_file",
    "source_row_id",
    "source_lineage",
    "race_date",
    "track",
    "race_no",
    "distance",
    "horse",
    "horse_key",
    "identity_status",
    "match_confidence",
    "payload_structure_type",
    "schema_variant",
    "reconstruction_method",
    "reconstruction_confidence",
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
    "physics_valid",
    "physics_grade",
    "physics_confidence",
    "velocity_integrity",
    "fatigue_integrity",
    "split_integrity",
    "physics_notes",
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


def fmt(value: float) -> str:
    return "" if math.isnan(value) else f"{value:.3f}".rstrip("0").rstrip(".")


def score_label(score: int) -> str:
    if score >= 90:
        return "ELITE"
    if score >= 74:
        return "GOOD"
    if score >= 52:
        return "PARTIAL"
    if score > 0:
        return "WEAK"
    return "BROKEN"


def segment_scores(last_600: float, last_400: float, last_200: float) -> tuple[int, int, int, list[str]]:
    notes: list[str] = []
    if any(math.isnan(value) for value in [last_600, last_400, last_200]):
        return 0, 0, 0, ["missing full last-600/400/200 ladder"]
    if not (last_600 > last_400 > last_200):
        return 0, 0, 0, ["split ladder order broken"]
    pieces = [last_600 - last_400, last_400 - last_200, last_200]
    if any(piece <= 0 for piece in pieces):
        return 0, 0, 0, ["negative or zero sectional segment"]
    split_integrity = 100
    velocity_integrity = 100
    fatigue_integrity = 100
    for piece in pieces:
        if piece < 8.0 or piece > 18.5:
            split_integrity -= 55
            velocity_integrity -= 45
            notes.append(f"200m segment outside racing bounds: {piece:.2f}")
        elif piece < 9.2 or piece > 15.8:
            split_integrity -= 15
            velocity_integrity -= 12
    spread = max(pieces) - min(pieces)
    if spread > 4.8:
        velocity_integrity -= 45
        fatigue_integrity -= 35
        notes.append(f"segment spread too wide: {spread:.2f}s")
    elif spread > 3.2:
        velocity_integrity -= 18
        fatigue_integrity -= 12
    velocities = [200.0 / piece for piece in pieces]
    if max(velocities) - min(velocities) > 5.6:
        velocity_integrity -= 45
        notes.append("impossible acceleration/velocity swing")
    if last_600 < 27.0 or last_600 > 48.0:
        split_integrity -= 50
        notes.append("last 600 outside accepted range")
    return max(0, split_integrity), max(0, velocity_integrity), max(0, fatigue_integrity), notes


def validate(row: dict[str, str]) -> dict[str, object]:
    last_600 = number(row.get("last_600"))
    last_400 = number(row.get("last_400"))
    last_200 = number(row.get("last_200"))
    split_integrity, velocity_integrity, fatigue_integrity, notes = segment_scores(last_600, last_400, last_200)
    reconstruction_confidence = number(row.get("reconstruction_confidence"))
    if math.isnan(reconstruction_confidence):
        reconstruction_confidence = 0
    method = clean(row.get("reconstruction_method")).upper()
    if method in {"NONE", "UNSAFE"}:
        notes.append("no safe reconstruction method")
    if clean(row.get("payload_structure_type")).upper() in {"BROKEN", "UNKNOWN", "MALFORMED"}:
        notes.append("payload structure is not trusted")
    score = round(split_integrity * 0.42 + velocity_integrity * 0.28 + fatigue_integrity * 0.16 + reconstruction_confidence * 0.14)
    if clean(row.get("unsafe_reconstruction")).upper() == "YES":
        score = min(score, 25)
        notes.append("unsafe reconstruction flag")
    if clean(row.get("suppressed_duplicate")).upper() == "YES":
        score = min(score, 72)
        notes.append("duplicate lineage caps physics confidence")
    if clean(row.get("identity_status")).upper() in {"UNSAFE", "UNMATCHED"}:
        score = min(score, 52)
        notes.append("identity unsafe; physics cannot be execution trusted")
    grade = score_label(score)
    valid = "YES" if grade in {"ELITE", "GOOD", "PARTIAL"} and method not in {"NONE", "UNSAFE"} and split_integrity > 0 else "NO"
    return {
        "sectional_race_key": clean(row.get("sectional_race_key")),
        "sectional_runner_key": clean(row.get("sectional_runner_key")),
        "source_file": clean(row.get("source_file")),
        "source_row_id": clean(row.get("source_row_id")),
        "source_lineage": clean(row.get("source_lineage")),
        "race_date": clean(row.get("race_date")),
        "track": clean(row.get("track")),
        "race_no": clean(row.get("race_no")),
        "distance": clean(row.get("distance")),
        "horse": clean(row.get("horse")),
        "horse_key": clean(row.get("horse_key")),
        "identity_status": clean(row.get("identity_status")),
        "match_confidence": clean(row.get("match_confidence")),
        "payload_structure_type": clean(row.get("payload_structure_type")),
        "schema_variant": clean(row.get("schema_variant")),
        "reconstruction_method": clean(row.get("reconstruction_method")),
        "reconstruction_confidence": clean(row.get("reconstruction_confidence")),
        "sectional_200": clean(row.get("sectional_200")),
        "sectional_400": clean(row.get("sectional_400")),
        "sectional_600": clean(row.get("sectional_600")),
        "last_600": clean(row.get("last_600")),
        "last_400": clean(row.get("last_400")),
        "last_200": clean(row.get("last_200")),
        "early_velocity": clean(row.get("early_velocity")),
        "mid_velocity": clean(row.get("mid_velocity")),
        "late_velocity": clean(row.get("late_velocity")),
        "sustained_velocity": clean(row.get("sustained_velocity")),
        "physics_valid": valid,
        "physics_grade": grade,
        "physics_confidence": max(0, min(100, score)),
        "velocity_integrity": velocity_integrity,
        "fatigue_integrity": fatigue_integrity,
        "split_integrity": split_integrity,
        "physics_notes": "; ".join(dict.fromkeys(notes)) if notes else "sectional ladder passes physics checks",
    }


def main() -> None:
    rows = [validate(row) for row in read_csv(RECON)]
    grade_counts = Counter(str(row["physics_grade"]) for row in rows)
    valid_rows = [row for row in rows if row["physics_valid"] == "YES"]
    trusted_physics = [row for row in valid_rows if clean(row.get("identity_status")).upper() in {"TRUSTED", "LIKELY"} and int(row["physics_confidence"]) >= 74]
    summary = [
        {"metric": "physics_rows", "value": len(rows)},
        {"metric": "physics_valid_rows", "value": len(valid_rows)},
        {"metric": "trusted_physics_rows", "value": len(trusted_physics)},
        {"metric": "broken_ladders", "value": grade_counts.get("BROKEN", 0)},
        {"metric": "weak_ladders", "value": grade_counts.get("WEAK", 0)},
        {"metric": "physics_success_pct", "value": f"{(len(valid_rows) / len(rows) * 100) if rows else 0:.1f}"},
    ]
    summary.extend({"metric": f"physics_{key.lower()}", "value": value} for key, value in sorted(grade_counts.items()))
    write_csv(OUT, rows, FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    print("=" * 90)
    print("EDGEIQ SECTIONAL PHYSICS VALIDATION V1")
    print("=" * 90)
    print("ROWS:", len(rows))
    print("VALID:", len(valid_rows))
    print("TRUSTED PHYSICS:", len(trusted_physics))
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
