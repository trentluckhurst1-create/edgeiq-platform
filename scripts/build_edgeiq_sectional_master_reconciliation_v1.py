from __future__ import annotations

import csv
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
IDENTITY = DATA / "edgeiq_sectional_identity_engine_v1.csv"
VALIDATION = DATA / "edgeiq_sectional_validation_engine.csv"
INVENTORY = DATA / "edgeiq_sectional_scraper_inventory.csv"
AUDIT = DATA / "edgeiq_sectional_pipeline_audit.csv"
TRUSTED = DATA / "edgeiq_trusted_sectional_universe.csv"
RECON_OUT = DATA / "edgeiq_sectional_master_reconciliation_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_sectional_master_summary_v1.csv"
CONFLICT_OUT = DATA / "edgeiq_sectional_duplicate_conflicts_v1.csv"
MASTER_OUT = DATA / "edgeiq_sectional_master_v1.csv"

RECON_FIELDS = [
    "sectional_race_key", "sectional_runner_key", "source_file", "source_row_id", "race_date", "track",
    "race_no", "distance", "horse", "horse_key", "source_rank", "source_quality", "lineage_confidence",
    "payload_quality", "structure_quality", "identity_status", "match_confidence", "match_method",
    "validation_status", "payload_valid", "payload_quality_grade", "split_integrity_score",
    "sectional_structure_type", "sectional_depth", "duplicate_flag", "conflict_flag", "conflict_reason",
    "preferred_source", "suppressed_duplicate", "canonical_status", "source_lineage",
]

SUMMARY_FIELDS = ["metric", "value"]

CONFLICT_FIELDS = [
    "sectional_runner_key", "conflict_type", "conflict_reason", "winner_source", "loser_source",
    "resolution_method", "suppressed_flag",
]

MASTER_FIELDS = [
    "sectional_race_key", "sectional_runner_key", "race_date", "track", "race_no", "distance",
    "horse", "horse_key", "source_file", "source_lineage", "source_rank", "identity_status",
    "match_confidence", "sectional_200", "sectional_400", "sectional_600", "last_600", "last_400",
    "last_200", "early_speed", "midrace_speed", "late_speed", "payload_quality_grade",
    "sectional_confidence", "trusted_for_modelling", "trusted_for_execution", "canonical_status",
]


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"} else text


def norm_track(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\b(BET365|SPORTSBET|LADBROKES|TAB|MRC|VRC|RACING)\b", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text).strip()
    return " ".join(text.split())


def norm_horse(value: object) -> str:
    text = clean(value).upper().replace("'", "").replace("’", "").replace("`", "")
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def race_no(value: object) -> str:
    digits = re.sub(r"[^0-9]", "", clean(value).upper().replace("RACE", "").replace("R", ""))
    return str(int(digits)) if digits else ""


def distance_value(value: object) -> str:
    digits = re.sub(r"[^0-9]", "", clean(value))
    return str(int(digits)) if digits else ""


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


def as_number(value: object) -> float:
    raw = clean(value)
    if not raw:
        return math.nan
    if ":" in raw:
        try:
            pieces = raw.split(":")
            return float(pieces[-1]) + float(pieces[-2]) * 60
        except Exception:
            return math.nan
    try:
        return float(re.sub(r"[^0-9.]", "", raw))
    except ValueError:
        return math.nan


def split_values(row: dict[str, str]) -> dict[str, str]:
    return {
        "sectional_200": "",
        "sectional_400": "",
        "sectional_600": "",
        "last_600": clean(row.get("raw_last_600")),
        "last_400": clean(row.get("raw_last_400")),
        "last_200": clean(row.get("raw_last_200")),
        "early_speed": clean(row.get("early_speed_raw")),
        "midrace_speed": clean(row.get("midrace_speed_raw")),
        "late_speed": clean(row.get("late_speed_raw")),
    }


def split_count(row: dict[str, str]) -> int:
    payload = split_values(row)
    return sum(1 for value in payload.values() if clean(value))


def impossible_payload(row: dict[str, str]) -> bool:
    for value in split_values(row).values():
        parsed = as_number(value)
        if not math.isnan(parsed) and (parsed <= 5 or parsed > 120):
            return True
    return False


def split_integrity(row: dict[str, str]) -> int:
    count = split_count(row)
    if impossible_payload(row):
        return 0
    if count >= 6:
        return 95
    if count >= 4:
        return 78
    if count >= 2:
        return 52
    if count == 1:
        return 30
    return 0


def payload_grade(row: dict[str, str]) -> str:
    score = split_integrity(row)
    if impossible_payload(row):
        return "BROKEN"
    if score >= 90:
        return "ELITE"
    if score >= 70:
        return "GOOD"
    if score >= 45:
        return "PARTIAL"
    if score > 0:
        return "WEAK"
    return "BROKEN"


def structure_type(row: dict[str, str]) -> str:
    payload = split_values(row)
    last_count = sum(1 for key in ["last_600", "last_400", "last_200"] if clean(payload[key]))
    speed_count = sum(1 for key in ["early_speed", "midrace_speed", "late_speed"] if clean(payload[key]))
    if last_count == 3 and speed_count >= 2:
        return "FULL_LADDER_AND_SPEED"
    if last_count == 3:
        return "LAST_SPLIT_LADDER"
    if speed_count >= 2:
        return "SPEED_PROFILE"
    if last_count or speed_count:
        return "PARTIAL_PAYLOAD"
    return "NO_PAYLOAD"


def source_quality(row: dict[str, str]) -> str:
    identity = clean(row.get("identity_status")).upper()
    grade = payload_grade(row)
    if identity == "TRUSTED" and grade in {"ELITE", "GOOD"}:
        return "ELITE" if grade == "ELITE" else "GOOD"
    if identity in {"TRUSTED", "LIKELY"} and grade == "PARTIAL":
        return "PARTIAL"
    if identity in {"TRUSTED", "LIKELY"} and grade == "WEAK":
        return "WEAK"
    return "BROKEN"


def lineage_confidence(row: dict[str, str]) -> int:
    identity = clean(row.get("identity_status")).upper()
    confidence = int(float(clean(row.get("match_confidence")) or 0))
    base = confidence
    if identity in {"UNSAFE", "UNMATCHED"}:
        base = min(base, 35)
    if clean(row.get("suppressed_duplicate")).upper() == "YES":
        base -= 20
    return max(0, min(100, base))


def source_rank(row: dict[str, str]) -> int:
    identity_score = lineage_confidence(row)
    payload_score = split_integrity(row)
    validation = clean(row.get("validation_status")).upper()
    duplicate_penalty = 18 if clean(row.get("suppressed_duplicate")).upper() == "YES" else 0
    malformed_penalty = 40 if validation == "BAD_SPLIT" or impossible_payload(row) else 0
    no_payload_penalty = 35 if split_count(row) == 0 else 0
    return max(0, min(100, round(identity_score * 0.52 + payload_score * 0.38 - duplicate_penalty - malformed_penalty - no_payload_penalty)))


def canonical_keys(row: dict[str, str]) -> tuple[str, str]:
    race_date = clean(row.get("matched_race_date")) or clean(row.get("race_date"))
    track = norm_track(clean(row.get("matched_track")) or clean(row.get("track")))
    race = race_no(clean(row.get("matched_race_no")) or clean(row.get("race_no")))
    distance = distance_value(clean(row.get("matched_distance")) or clean(row.get("distance")))
    horse = norm_horse(clean(row.get("matched_horse_key")) or clean(row.get("matched_horse")) or clean(row.get("horse_key")) or clean(row.get("horse")))
    race_key = "_".join([race_date, track, f"R{race}", distance]).strip("_")
    return race_key, f"{race_key}_{horse}".strip("_")


def build_reconciliation() -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    identity_rows = read_csv(IDENTITY)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    recon_rows: list[dict[str, object]] = []
    for row in identity_rows:
        race_key, runner_key = canonical_keys(row)
        grouped[runner_key].append(row)

    winners: dict[str, dict[str, str]] = {}
    for runner_key, rows in grouped.items():
        ranked = sorted(rows, key=lambda item: source_rank(item), reverse=True)
        winners[runner_key] = ranked[0]

    conflicts: list[dict[str, object]] = []
    for runner_key, rows in grouped.items():
        winner = winners[runner_key]
        duplicate = len(rows) > 1
        distances = {distance_value(clean(row.get("matched_distance")) or clean(row.get("distance"))) for row in rows if distance_value(clean(row.get("matched_distance")) or clean(row.get("distance")))}
        tracks = {norm_track(clean(row.get("matched_track")) or clean(row.get("track"))) for row in rows if norm_track(clean(row.get("matched_track")) or clean(row.get("track")))}
        split_signatures = {tuple(split_values(row).values()) for row in rows}
        conflict_reasons = []
        if duplicate:
            conflict_reasons.append("duplicate runner/race lineage")
        if len(distances) > 1:
            conflict_reasons.append("conflicting distances")
        if len(tracks) > 1:
            conflict_reasons.append("conflicting tracks")
        if len(split_signatures) > 1:
            conflict_reasons.append("conflicting split payloads")
        for row in rows:
            race_key, canonical_runner_key = canonical_keys(row)
            winner_flag = row is winner
            conflict_flag = bool(conflict_reasons)
            if conflict_flag and not winner_flag:
                conflicts.append({
                    "sectional_runner_key": canonical_runner_key,
                    "conflict_type": "DUPLICATE_PAYLOAD" if len(split_signatures) > 1 else "DUPLICATE_IDENTITY",
                    "conflict_reason": "; ".join(conflict_reasons),
                    "winner_source": clean(winner.get("source_file")),
                    "loser_source": clean(row.get("source_file")),
                    "resolution_method": "highest_source_rank",
                    "suppressed_flag": "YES",
                })
            recon_rows.append({
                "sectional_race_key": race_key,
                "sectional_runner_key": canonical_runner_key,
                "source_file": clean(row.get("source_file")),
                "source_row_id": clean(row.get("source_row_id")),
                "race_date": clean(row.get("matched_race_date")) or clean(row.get("race_date")),
                "track": norm_track(clean(row.get("matched_track")) or clean(row.get("track"))),
                "race_no": race_no(clean(row.get("matched_race_no")) or clean(row.get("race_no"))),
                "distance": distance_value(clean(row.get("matched_distance")) or clean(row.get("distance"))),
                "horse": clean(row.get("matched_horse")) or clean(row.get("horse")),
                "horse_key": clean(row.get("matched_horse_key")) or clean(row.get("horse_key")),
                "source_rank": source_rank(row),
                "source_quality": source_quality(row),
                "lineage_confidence": lineage_confidence(row),
                "payload_quality": split_integrity(row),
                "structure_quality": split_integrity(row),
                "identity_status": clean(row.get("identity_status")),
                "match_confidence": clean(row.get("match_confidence")),
                "match_method": clean(row.get("match_method")),
                "validation_status": clean(row.get("validation_status")),
                "payload_valid": "NO" if impossible_payload(row) or split_count(row) == 0 else "YES",
                "payload_quality_grade": payload_grade(row),
                "split_integrity_score": split_integrity(row),
                "sectional_structure_type": structure_type(row),
                "sectional_depth": split_count(row),
                "duplicate_flag": "YES" if duplicate else "NO",
                "conflict_flag": "YES" if conflict_flag else "NO",
                "conflict_reason": "; ".join(conflict_reasons),
                "preferred_source": "YES" if winner_flag else "NO",
                "suppressed_duplicate": "NO" if winner_flag else "YES",
                "canonical_status": "CANONICAL" if winner_flag else "SUPPRESSED_DUPLICATE",
                "source_lineage": f"{clean(row.get('source_file'))}#{clean(row.get('source_row_id'))}",
            })

    master: list[dict[str, object]] = []
    for runner_key, winner in winners.items():
        identity = clean(winner.get("identity_status")).upper()
        if identity in {"UNSAFE", "UNMATCHED"}:
            continue
        race_key, canonical_runner_key = canonical_keys(winner)
        payload = split_values(winner)
        grade = payload_grade(winner)
        rank = source_rank(winner)
        modelling = "YES" if identity in {"TRUSTED", "LIKELY"} and grade in {"ELITE", "GOOD", "PARTIAL"} and rank >= 65 else "NO"
        execution = "YES" if identity == "TRUSTED" and grade in {"ELITE", "GOOD"} and rank >= 85 else "NO"
        master.append({
            "sectional_race_key": race_key,
            "sectional_runner_key": canonical_runner_key,
            "race_date": clean(winner.get("matched_race_date")) or clean(winner.get("race_date")),
            "track": norm_track(clean(winner.get("matched_track")) or clean(winner.get("track"))),
            "race_no": race_no(clean(winner.get("matched_race_no")) or clean(winner.get("race_no"))),
            "distance": distance_value(clean(winner.get("matched_distance")) or clean(winner.get("distance"))),
            "horse": clean(winner.get("matched_horse")) or clean(winner.get("horse")),
            "horse_key": clean(winner.get("matched_horse_key")) or clean(winner.get("horse_key")),
            "source_file": clean(winner.get("source_file")),
            "source_lineage": f"{clean(winner.get('source_file'))}#{clean(winner.get('source_row_id'))}",
            "source_rank": rank,
            "identity_status": identity,
            "match_confidence": clean(winner.get("match_confidence")),
            "sectional_200": payload["sectional_200"],
            "sectional_400": payload["sectional_400"],
            "sectional_600": payload["sectional_600"],
            "last_600": payload["last_600"],
            "last_400": payload["last_400"],
            "last_200": payload["last_200"],
            "early_speed": payload["early_speed"],
            "midrace_speed": payload["midrace_speed"],
            "late_speed": payload["late_speed"],
            "payload_quality_grade": grade,
            "sectional_confidence": clean(winner.get("sectional_confidence")) or clean(winner.get("match_confidence")),
            "trusted_for_modelling": modelling,
            "trusted_for_execution": execution,
            "canonical_status": "CANONICAL",
        })
    return recon_rows, conflicts, master


def main() -> None:
    recon_rows, conflicts, master = build_reconciliation()
    grade_counts = Counter(str(row["payload_quality_grade"]) for row in recon_rows)
    summary = [
        {"metric": "source_rows", "value": len(recon_rows)},
        {"metric": "canonical_rows", "value": len(master)},
        {"metric": "trusted_modelling_rows", "value": sum(1 for row in master if row["trusted_for_modelling"] == "YES")},
        {"metric": "trusted_execution_rows", "value": sum(1 for row in master if row["trusted_for_execution"] == "YES")},
        {"metric": "duplicate_conflicts", "value": len(conflicts)},
        {"metric": "malformed_payloads", "value": sum(1 for row in recon_rows if row["payload_quality_grade"] == "BROKEN")},
        {"metric": "coverage_pct", "value": f"{(len(master) / len(recon_rows) * 100) if recon_rows else 0:.1f}"},
    ] + [{"metric": f"payload_{grade.lower()}", "value": count} for grade, count in sorted(grade_counts.items())]
    write_csv(RECON_OUT, recon_rows, RECON_FIELDS)
    write_csv(CONFLICT_OUT, conflicts, CONFLICT_FIELDS)
    write_csv(MASTER_OUT, master, MASTER_FIELDS)
    write_csv(SUMMARY_OUT, summary, SUMMARY_FIELDS)
    print("=" * 90)
    print("EDGEIQ SECTIONAL MASTER RECONCILIATION V1")
    print("=" * 90)
    print("SOURCE ROWS:", len(recon_rows))
    print("CANONICAL ROWS:", len(master))
    print("TRUSTED MODELLING:", sum(1 for row in master if row["trusted_for_modelling"] == "YES"))
    print("CONFLICTS:", len(conflicts))
    print("OUT:", MASTER_OUT)


if __name__ == "__main__":
    main()
