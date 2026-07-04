from __future__ import annotations

import csv
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
IDENTITY_V1 = DATA / "edgeiq_sectional_identity_engine_v1.csv"
FIELD_MATCH = DATA / "edgeiq_sectional_field_composition_match_v1.csv"
PHYSICS = DATA / "edgeiq_sectional_physics_validation_v1.csv"
HORSE_ALIASES = DATA / "edgeiq_horse_alias_engine_v1.csv"
TRACK_ALIASES = DATA / "edgeiq_track_alias_engine_v1.csv"
OUT = DATA / "edgeiq_sectional_identity_engine_v2.csv"
SUMMARY = DATA / "edgeiq_sectional_identity_summary_v2.csv"

FIELDS = [
    "source_file", "source_row_id", "source_lineage", "race_date", "track", "race_no", "distance",
    "horse", "horse_key", "matched_race_date", "matched_track", "matched_race_no", "matched_distance",
    "matched_horse", "matched_horse_key", "identity_v1_status", "identity_v1_confidence",
    "identity_v1_method", "field_composition_confidence", "field_composition_status",
    "horse_alias_confidence", "track_alias_confidence", "distance_confidence", "race_structure_confidence",
    "physics_confidence", "physics_grade", "identity_v2_confidence", "identity_v2_status",
    "identity_v2_method", "trusted_identity_flag", "identity_escalation_reason", "duplicate_flag",
    "conflict_flag", "suppressed_duplicate", "payload_physics_valid", "source_race_group_key",
    "edgeiq_race_key",
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
    try:
        return float(clean(value))
    except ValueError:
        return math.nan


def horse_key(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"\b(NZ|AUS|GB|IRE|USA|FR|JPN|SAF|GER)\b", "", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def track_key(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\b(BET365|SPORTSBET|LADBROKES|TAB|MRC|VRC|RACING|CLUB)\b", " ", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def race_no(value: object) -> str:
    digits = re.sub(r"[^0-9]", "", clean(value).upper().replace("RACE", "").replace("R", ""))
    return str(int(digits)) if digits else ""


def distance(value: object) -> str:
    digits = re.sub(r"[^0-9]", "", clean(value))
    return str(int(digits)) if digits else ""


def confidence(value: object) -> int:
    parsed = number(value)
    return 0 if math.isnan(parsed) else max(0, min(100, int(round(parsed))))


def lineage(row: dict[str, str]) -> str:
    return f"{clean(row.get('source_file'))}#{clean(row.get('source_row_id'))}"


def race_group_key(row: dict[str, str], track_aliases: dict[str, str]) -> str:
    source_file = clean(row.get("source_file"))
    date = clean(row.get("race_date"))[:10]
    track = track_aliases.get(track_key(row.get("track")), clean(row.get("track")).upper())
    rn = race_no(row.get("race_no"))
    dist = distance(row.get("distance"))
    return f"{source_file}|{date}_{track}_R{rn}_{dist}"


def alias_confidence(path: Path, key_name: str) -> dict[str, int]:
    lookup: dict[str, int] = {}
    for row in read_csv(path):
        key = clean(row.get(key_name))
        conf = confidence(row.get("confidence"))
        if key:
            lookup[key] = max(lookup.get(key, 0), conf)
    return lookup


def track_aliases() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for row in read_csv(TRACK_ALIASES):
        raw = track_key(row.get("raw_track"))
        canonical = clean(row.get("canonical_track")).upper()
        if raw and canonical:
            lookup[raw] = canonical
    return lookup


def best_field_matches() -> dict[str, dict[str, str]]:
    grouped: dict[str, dict[str, str]] = {}
    for row in read_csv(FIELD_MATCH):
        key = clean(row.get("sectional_race_group_key"))
        if not key:
            continue
        if key not in grouped or confidence(row.get("composition_confidence")) > confidence(grouped[key].get("composition_confidence")):
            grouped[key] = row
    return grouped


def physics_lookup() -> dict[str, dict[str, str]]:
    return {clean(row.get("source_lineage")): row for row in read_csv(PHYSICS) if clean(row.get("source_lineage"))}


def distance_score(row: dict[str, str], field: dict[str, str] | None) -> int:
    if not field:
        return 0
    src = distance(row.get("distance"))
    dst = distance(field.get("edgeiq_distance"))
    if not src or not dst:
        return 0
    delta = abs(int(src) - int(dst))
    if delta == 0:
        return 100
    if delta <= 50:
        return 86
    if delta <= 100:
        return 60
    return 0


def race_structure_score(field: dict[str, str] | None) -> int:
    if not field:
        return 0
    score = 0
    score += 25 if clean(field.get("date_match")).upper() == "YES" else 0
    score += 25 if clean(field.get("track_match")).upper() == "YES" else 0
    score += 20 if clean(field.get("distance_match")).upper() == "YES" else 0
    score += 15 if clean(field.get("race_no_match")).upper() == "YES" else 0
    score += 15 if confidence(field.get("overlap_pct")) >= 60 else 0
    return score


def decide(row: dict[str, str], field: dict[str, str] | None, physics: dict[str, str] | None, horse_alias_conf: int, track_alias_conf: int) -> tuple[int, str, str, str, str]:
    v1 = confidence(row.get("match_confidence"))
    field_conf = confidence(field.get("composition_confidence")) if field else 0
    distance_conf = distance_score(row, field)
    structure_conf = race_structure_score(field)
    physics_conf = confidence(physics.get("physics_confidence")) if physics else 0
    physics_valid = physics and clean(physics.get("physics_valid")).upper() == "YES"
    physics_grade = clean(physics.get("physics_grade")).upper() if physics else ""
    notes: list[str] = []
    if not physics_valid:
        notes.append("payload physics failed or missing")
    if clean(row.get("suppressed_duplicate")).upper() == "YES":
        notes.append("duplicate unresolved")
    if field and clean(field.get("distance_match")).upper() != "YES":
        notes.append("conflicting distance")
    if field_conf < 52:
        notes.append("weak field overlap")
    if horse_alias_conf < 90:
        notes.append("horse alias confidence weak")
    if track_alias_conf < 90:
        notes.append("track alias confidence weak")
    raw_score = round(v1 * 0.12 + field_conf * 0.34 + horse_alias_conf * 0.14 + track_alias_conf * 0.1 + distance_conf * 0.1 + structure_conf * 0.1 + physics_conf * 0.1)
    score = max(0, min(100, raw_score))
    if not physics_valid:
        score = min(score, 45)
    if clean(row.get("suppressed_duplicate")).upper() == "YES":
        score = min(score, 58)
    if field and clean(field.get("race_identity_status")).upper() == "UNSAFE":
        score = min(score, 55)
    if field and clean(field.get("race_identity_status")).upper() == "UNMATCHED":
        score = min(score, 35)
    if physics_grade in {"BROKEN", "WEAK"}:
        score = min(score, 55)
    status = "UNMATCHED"
    method = "UNMATCHED"
    trusted = "NO"
    if not notes and score >= 90 and clean(field.get("race_identity_status")).upper() == "TRUSTED":
        status = "TRUSTED"
        method = "FIELD_COMPOSITION_TRUSTED"
        trusted = "YES"
    elif physics_valid and score >= 82 and field and clean(field.get("race_identity_status")).upper() in {"TRUSTED", "LIKELY"} and not any(note in notes for note in ["duplicate unresolved", "conflicting distance", "horse alias confidence weak"]):
        status = "LIKELY"
        method = "FIELD_COMPOSITION_LIKELY"
        trusted = "YES" if score >= 86 else "PARTIAL"
    elif physics_valid and score >= 62 and field_conf >= 52:
        status = "PARTIAL"
        method = "FIELD_COMPOSITION_PARTIAL"
        trusted = "PARTIAL"
    elif score > 0:
        status = "UNSAFE"
        method = "EVIDENCE_PRESENT_UNSAFE"
    return score, status, method, trusted, "; ".join(notes) if notes else "field composition, alias and physics evidence agree"


def main() -> None:
    horse_alias_conf = alias_confidence(HORSE_ALIASES, "alias_key")
    track_alias_conf = alias_confidence(TRACK_ALIASES, "track_key")
    tracks = track_aliases()
    field_matches = best_field_matches()
    physics_by_lineage = physics_lookup()
    rows: list[dict[str, object]] = []
    for row in read_csv(IDENTITY_V1):
        line = lineage(row)
        group_key = race_group_key(row, tracks)
        field = field_matches.get(group_key)
        physics = physics_by_lineage.get(line)
        horse_conf = horse_alias_conf.get(horse_key(row.get("horse_key") or row.get("horse")), 0)
        track_conf = track_alias_conf.get(track_key(row.get("track")), 0)
        score, status, method, trusted, reason = decide(row, field, physics, horse_conf, track_conf)
        rows.append({
            "source_file": clean(row.get("source_file")),
            "source_row_id": clean(row.get("source_row_id")),
            "source_lineage": line,
            "race_date": clean(row.get("race_date")),
            "track": clean(row.get("track")),
            "race_no": clean(row.get("race_no")),
            "distance": clean(row.get("distance")),
            "horse": clean(row.get("horse")),
            "horse_key": clean(row.get("horse_key")) or horse_key(row.get("horse")),
            "matched_race_date": clean(field.get("edgeiq_race_date")) if field else clean(row.get("matched_race_date")),
            "matched_track": clean(field.get("edgeiq_track")) if field else clean(row.get("matched_track")),
            "matched_race_no": clean(field.get("edgeiq_race_no")) if field else clean(row.get("matched_race_no")),
            "matched_distance": clean(field.get("edgeiq_distance")) if field else clean(row.get("matched_distance")),
            "matched_horse": clean(row.get("matched_horse")),
            "matched_horse_key": clean(row.get("matched_horse_key")),
            "identity_v1_status": clean(row.get("identity_status")),
            "identity_v1_confidence": clean(row.get("match_confidence")),
            "identity_v1_method": clean(row.get("match_method")),
            "field_composition_confidence": clean(field.get("composition_confidence")) if field else "0",
            "field_composition_status": clean(field.get("race_identity_status")) if field else "UNMATCHED",
            "horse_alias_confidence": horse_conf,
            "track_alias_confidence": track_conf,
            "distance_confidence": distance_score(row, field),
            "race_structure_confidence": race_structure_score(field),
            "physics_confidence": clean(physics.get("physics_confidence")) if physics else "0",
            "physics_grade": clean(physics.get("physics_grade")) if physics else "",
            "identity_v2_confidence": score,
            "identity_v2_status": status,
            "identity_v2_method": method,
            "trusted_identity_flag": trusted,
            "identity_escalation_reason": reason,
            "duplicate_flag": clean(row.get("duplicate_flag")),
            "conflict_flag": clean(row.get("conflict_flag")),
            "suppressed_duplicate": clean(row.get("suppressed_duplicate")),
            "payload_physics_valid": clean(physics.get("physics_valid")) if physics else "NO",
            "source_race_group_key": group_key,
            "edgeiq_race_key": clean(field.get("edgeiq_race_key")) if field else "",
        })
    counts = Counter(str(row["identity_v2_status"]) for row in rows)
    methods = Counter(str(row["identity_v2_method"]) for row in rows)
    v1_trusted = sum(1 for row in rows if row["identity_v1_status"] in {"TRUSTED", "LIKELY"})
    v2_trusted = counts.get("TRUSTED", 0) + counts.get("LIKELY", 0)
    summary = [
        {"metric": "identity_rows", "value": len(rows)},
        {"metric": "v1_trusted_or_likely", "value": v1_trusted},
        {"metric": "v2_trusted_or_likely", "value": v2_trusted},
        {"metric": "trusted_identity_rows", "value": sum(1 for row in rows if row["trusted_identity_flag"] == "YES")},
        {"metric": "partial_identity_rows", "value": sum(1 for row in rows if row["trusted_identity_flag"] == "PARTIAL")},
        {"metric": "identity_improvement", "value": v2_trusted - v1_trusted},
        {"metric": "physics_valid_rows", "value": sum(1 for row in rows if row["payload_physics_valid"] == "YES")},
        {"metric": "unresolved_ambiguities", "value": sum(1 for row in rows if row["identity_v2_status"] in {"UNSAFE", "UNMATCHED"})},
    ]
    summary.extend({"metric": f"status_{key.lower()}", "value": value} for key, value in sorted(counts.items()))
    summary.extend({"metric": f"method_{key.lower()}", "value": value} for key, value in sorted(methods.items()))
    write_csv(OUT, rows, FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    print("=" * 90)
    print("EDGEIQ SECTIONAL IDENTITY ENGINE V2")
    print("=" * 90)
    print("ROWS:", len(rows))
    print("TRUSTED IDENTITY:", summary[3]["value"])
    print("IMPROVEMENT:", summary[5]["value"])
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
