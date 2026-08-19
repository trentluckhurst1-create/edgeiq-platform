from __future__ import annotations

import csv
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

MASTER_RECON = DATA / "edgeiq_sectional_master_reconciliation_v1.csv"
MASTER = DATA / "edgeiq_sectional_master_v1.csv"
DUPLICATES = DATA / "edgeiq_sectional_duplicate_conflicts_v1.csv"
IDENTITY = DATA / "edgeiq_sectional_identity_engine_v1.csv"
OUT = DATA / "edgeiq_sectional_payload_reconstruction_v1.csv"
SUMMARY = DATA / "edgeiq_sectional_payload_reconstruction_summary_v1.csv"

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
    "match_method",
    "validation_status",
    "canonical_status",
    "duplicate_flag",
    "conflict_flag",
    "suppressed_duplicate",
    "payload_quality_grade",
    "raw_last_600",
    "raw_last_400",
    "raw_last_200",
    "raw_sectional_600",
    "raw_sectional_400",
    "raw_sectional_200",
    "raw_early_speed",
    "raw_midrace_speed",
    "raw_late_speed",
    "payload_structure_type",
    "schema_variant",
    "split_depth",
    "split_spacing",
    "structure_confidence",
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
    "reconstruction_method",
    "reconstruction_confidence",
    "reconstruction_notes",
    "payload_repaired",
    "unsafe_reconstruction",
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
    if ":" in raw:
        try:
            pieces = [float(piece) for piece in raw.split(":") if piece.strip()]
            if len(pieces) == 3:
                return pieces[0] * 3600 + pieces[1] * 60 + pieces[2]
            if len(pieces) == 2:
                return pieces[0] * 60 + pieces[1]
        except Exception:
            return math.nan
    try:
        return float(re.sub(r"[^0-9.\-]", "", raw))
    except ValueError:
        return math.nan


def fmt(value: float) -> str:
    return "" if math.isnan(value) else f"{value:.2f}".rstrip("0").rstrip(".")


def fmt_velocity(value: float) -> str:
    return "" if math.isnan(value) else f"{value:.3f}"


def as_int(value: object) -> int:
    parsed = number(value)
    return 0 if math.isnan(parsed) else int(parsed)


def valid_time(value: float, minimum: float, maximum: float) -> bool:
    return not math.isnan(value) and minimum <= value <= maximum


def valid_last_ladder(last_600: float, last_400: float, last_200: float) -> bool:
    if not (valid_time(last_600, 27.0, 48.0) and valid_time(last_400, 17.0, 34.0) and valid_time(last_200, 8.0, 18.5)):
        return False
    if not (last_600 > last_400 > last_200):
        return False
    first_200 = last_600 - last_400
    middle_200 = last_400 - last_200
    final_200 = last_200
    return all(valid_time(piece, 8.0, 18.5) for piece in [first_200, middle_200, final_200])


def acceleration_ok(last_600: float, last_400: float, last_200: float) -> bool:
    if not valid_last_ladder(last_600, last_400, last_200):
        return False
    pieces = [last_600 - last_400, last_400 - last_200, last_200]
    return max(pieces) - min(pieces) <= 4.8


def velocity(distance: float, seconds: float) -> float:
    if math.isnan(seconds) or seconds <= 0:
        return math.nan
    return distance / seconds


def signature(row: dict[str, str]) -> str:
    return f"{clean(row.get('source_file'))}#{clean(row.get('source_row_id'))}"


def identity_lookup() -> dict[str, dict[str, str]]:
    return {signature(row): row for row in read_csv(IDENTITY)}


def classify_structure(last_600: float, last_400: float, last_200: float, speeds: list[float], master_type: str) -> tuple[str, str, int, str, int]:
    present_last = sum(0 if math.isnan(value) else 1 for value in [last_600, last_400, last_200])
    present_speed = sum(0 if math.isnan(value) else 1 for value in speeds)
    if present_last == 3 and valid_last_ladder(last_600, last_400, last_200):
        variant = "RACINGCOM_LAST_SPLITS" if "RACINGCOM" in master_type.upper() or present_speed else "LAST_SPLIT_LADDER"
        return "FINAL_SPLITS_ONLY", variant, 3, "200", 90 if acceleration_ok(last_600, last_400, last_200) else 72
    if present_last == 3:
        return "MALFORMED", "LAST_SPLIT_LADDER_INCOHERENT", present_last, "200", 22
    if present_last in {1, 2}:
        return "PARTIAL", "PARTIAL_LAST_SPLITS", present_last, "200", 38
    if present_speed:
        return "PARTIAL", "SPEED_PROFILE_ONLY", present_speed, "UNKNOWN", 26
    return "BROKEN", "NO_PAYLOAD", 0, "", 0


def reconstruct(row: dict[str, str], identity: dict[str, str] | None) -> dict[str, object]:
    source_row = identity or row
    raw_last_600 = number(source_row.get("raw_last_600") or row.get("last_600"))
    raw_last_400 = number(source_row.get("raw_last_400") or row.get("last_400"))
    raw_last_200 = number(source_row.get("raw_last_200") or row.get("last_200"))
    raw_sectional_600 = number(source_row.get("sectional_600") or row.get("sectional_600"))
    raw_sectional_400 = number(source_row.get("sectional_400") or row.get("sectional_400"))
    raw_sectional_200 = number(source_row.get("sectional_200") or row.get("sectional_200"))
    raw_early_speed = number(source_row.get("early_speed_raw") or row.get("early_speed"))
    raw_midrace_speed = number(source_row.get("midrace_speed_raw") or row.get("midrace_speed"))
    raw_late_speed = number(source_row.get("late_speed_raw") or row.get("late_speed"))

    notes: list[str] = []
    repaired = "NO"
    method = "NONE"
    unsafe = "NO"
    last_600 = raw_last_600
    last_400 = raw_last_400
    last_200 = raw_last_200
    sectional_600 = raw_sectional_600
    sectional_400 = raw_sectional_400
    sectional_200 = raw_sectional_200

    structure, variant, depth, spacing, structure_confidence = classify_structure(
        last_600,
        last_400,
        last_200,
        [raw_early_speed, raw_midrace_speed, raw_late_speed],
        clean(row.get("sectional_structure_type")),
    )

    if structure == "FINAL_SPLITS_ONLY":
        sectional_600 = last_600 - last_400
        sectional_400 = last_400 - last_200
        sectional_200 = last_200
        method = "DIRECT"
        confidence = 84 if acceleration_ok(last_600, last_400, last_200) else 68
        notes.append("last-600/400/200 ladder accepted and converted to 200m segments")
    elif all(not math.isnan(value) for value in [raw_sectional_600, raw_sectional_400, raw_sectional_200]):
        candidate_600 = raw_sectional_600 + raw_sectional_400 + raw_sectional_200
        candidate_400 = raw_sectional_400 + raw_sectional_200
        candidate_200 = raw_sectional_200
        if valid_last_ladder(candidate_600, candidate_400, candidate_200):
            last_600, last_400, last_200 = candidate_600, candidate_400, candidate_200
            structure = "INCREMENTAL"
            variant = "THREE_INCREMENTAL_200M_SEGMENTS"
            depth = 3
            spacing = "200"
            structure_confidence = 76
            method = "DERIVED_INCREMENTAL"
            confidence = 70
            repaired = "YES"
            notes.append("incremental 200m pieces safely rebuilt into last split ladder")
        else:
            method = "UNSAFE"
            confidence = 0
            unsafe = "YES"
            notes.append("incremental candidates failed split ladder validation")
    elif structure == "PARTIAL":
        method = "PARTIAL_RECOVERY"
        confidence = 28 if depth else 0
        notes.append("partial payload preserved without inventing missing splits")
    else:
        method = "NONE"
        confidence = 0
        notes.append("no mathematically coherent split payload")

    if method in {"DIRECT", "DERIVED_INCREMENTAL"} and not acceleration_ok(last_600, last_400, last_200):
        confidence = min(confidence, 42)
        notes.append("acceleration/fatigue curve is weak; confidence penalised")
    if clean(row.get("suppressed_duplicate")).upper() == "YES":
        confidence = max(0, confidence - 18)
        notes.append("duplicate-suppressed lineage penalised")
    if clean(row.get("identity_status")).upper() in {"UNSAFE", "UNMATCHED"}:
        confidence = min(confidence, 35)
        notes.append("unsafe identity caps reconstruction confidence")
    if method == "UNSAFE":
        unsafe = "YES"

    return {
        "sectional_race_key": clean(row.get("sectional_race_key")),
        "sectional_runner_key": clean(row.get("sectional_runner_key")),
        "source_file": clean(row.get("source_file")),
        "source_row_id": clean(row.get("source_row_id")),
        "source_lineage": clean(row.get("source_lineage")) or signature(row),
        "race_date": clean(row.get("race_date")),
        "track": clean(row.get("track")),
        "race_no": clean(row.get("race_no")),
        "distance": clean(row.get("distance")),
        "horse": clean(row.get("horse")),
        "horse_key": clean(row.get("horse_key")),
        "identity_status": clean(row.get("identity_status")),
        "match_confidence": clean(row.get("match_confidence")),
        "match_method": clean(row.get("match_method")),
        "validation_status": clean(row.get("validation_status")),
        "canonical_status": clean(row.get("canonical_status")),
        "duplicate_flag": clean(row.get("duplicate_flag")),
        "conflict_flag": clean(row.get("conflict_flag")),
        "suppressed_duplicate": clean(row.get("suppressed_duplicate")),
        "payload_quality_grade": clean(row.get("payload_quality_grade")),
        "raw_last_600": fmt(raw_last_600),
        "raw_last_400": fmt(raw_last_400),
        "raw_last_200": fmt(raw_last_200),
        "raw_sectional_600": fmt(raw_sectional_600),
        "raw_sectional_400": fmt(raw_sectional_400),
        "raw_sectional_200": fmt(raw_sectional_200),
        "raw_early_speed": fmt_velocity(raw_early_speed),
        "raw_midrace_speed": fmt_velocity(raw_midrace_speed),
        "raw_late_speed": fmt_velocity(raw_late_speed),
        "payload_structure_type": structure,
        "schema_variant": variant,
        "split_depth": depth,
        "split_spacing": spacing,
        "structure_confidence": structure_confidence,
        "sectional_200": fmt(sectional_200),
        "sectional_400": fmt(sectional_400),
        "sectional_600": fmt(sectional_600),
        "last_600": fmt(last_600),
        "last_400": fmt(last_400),
        "last_200": fmt(last_200),
        "early_velocity": fmt_velocity(raw_early_speed),
        "mid_velocity": fmt_velocity(raw_midrace_speed),
        "late_velocity": fmt_velocity(raw_late_speed or velocity(200, last_200)),
        "sustained_velocity": fmt_velocity(velocity(600, last_600)),
        "reconstruction_method": method,
        "reconstruction_confidence": max(0, min(100, round(confidence))),
        "reconstruction_notes": "; ".join(notes),
        "payload_repaired": repaired,
        "unsafe_reconstruction": unsafe,
    }


def main() -> None:
    recon = read_csv(MASTER_RECON)
    read_csv(MASTER)
    read_csv(DUPLICATES)
    identities = identity_lookup()
    rows = [reconstruct(row, identities.get(clean(row.get("source_lineage")) or signature(row))) for row in recon]
    structure_counts = Counter(str(row["payload_structure_type"]) for row in rows)
    method_counts = Counter(str(row["reconstruction_method"]) for row in rows)
    recovered = sum(1 for row in rows if clean(row.get("reconstruction_method")) in {"DIRECT", "DERIVED_INCREMENTAL", "DERIVED_CUMULATIVE", "PARTIAL_RECOVERY"})
    trusted_physics_candidates = sum(1 for row in rows if as_int(row.get("reconstruction_confidence")) >= 65 and clean(row.get("unsafe_reconstruction")) != "YES")
    summary = [
        {"metric": "source_rows", "value": len(rows)},
        {"metric": "reconstructed_rows", "value": sum(1 for row in rows if clean(row.get("reconstruction_method")) in {"DIRECT", "DERIVED_INCREMENTAL", "DERIVED_CUMULATIVE"})},
        {"metric": "recovered_payloads", "value": recovered},
        {"metric": "partial_recoveries", "value": method_counts.get("PARTIAL_RECOVERY", 0)},
        {"metric": "unsafe_reconstructions", "value": sum(1 for row in rows if clean(row.get("unsafe_reconstruction")) == "YES")},
        {"metric": "trusted_physics_candidates", "value": trusted_physics_candidates},
        {"metric": "structure_variants", "value": len(structure_counts)},
        {"metric": "reconstruction_success_pct", "value": f"{(recovered / len(rows) * 100) if rows else 0:.1f}"},
    ]
    summary.extend({"metric": f"structure_{key.lower()}", "value": value} for key, value in sorted(structure_counts.items()))
    summary.extend({"metric": f"method_{key.lower()}", "value": value} for key, value in sorted(method_counts.items()))
    write_csv(OUT, rows, FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    print("=" * 90)
    print("EDGEIQ SECTIONAL PAYLOAD RECONSTRUCTION V1")
    print("=" * 90)
    print("ROWS:", len(rows))
    print("RECONSTRUCTED:", sum(1 for row in rows if clean(row.get("reconstruction_method")) in {"DIRECT", "DERIVED_INCREMENTAL", "DERIVED_CUMULATIVE"}))
    print("UNSAFE:", sum(1 for row in rows if clean(row.get("unsafe_reconstruction")) == "YES"))
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
