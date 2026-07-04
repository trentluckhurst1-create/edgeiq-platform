from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
UNIVERSE = DATA / "edgeiq_vic_three_day_meeting_universe.csv"
MASTER = DATA / "edgeiq_sectional_master_v1.csv"
IDENTITY = DATA / "edgeiq_sectional_identity_engine_v1.csv"
HORSE_ALIASES = DATA / "edgeiq_horse_alias_engine_v1.csv"
TRACK_ALIASES = DATA / "edgeiq_track_alias_engine_v1.csv"
OUT = DATA / "edgeiq_sectional_field_composition_match_v1.csv"
SUMMARY = DATA / "edgeiq_sectional_field_composition_summary_v1.csv"

FIELDS = [
    "sectional_race_group_key",
    "edgeiq_race_key",
    "source_file",
    "source_race_date",
    "source_track",
    "source_race_no",
    "source_distance",
    "edgeiq_race_date",
    "edgeiq_track",
    "edgeiq_race_no",
    "edgeiq_distance",
    "date_match",
    "track_match",
    "distance_match",
    "race_no_match",
    "horse_overlap_count",
    "edgeiq_runner_count",
    "sectional_runner_count",
    "overlap_pct",
    "distance_delta",
    "composition_confidence",
    "race_identity_status",
    "matched_horses",
    "conflict_reason",
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


def horse_key(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"\b(NZ|AUS|GB|IRE|USA|FR|JPN|SAF|GER)\b", "", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def race_no(value: object) -> str:
    digits = re.sub(r"[^0-9]", "", clean(value).upper().replace("RACE", "").replace("R", ""))
    return str(int(digits)) if digits else ""


def distance(value: object) -> str:
    digits = re.sub(r"[^0-9]", "", clean(value))
    return str(int(digits)) if digits else ""


def distance_delta(a: object, b: object) -> int:
    try:
        return abs(int(distance(a)) - int(distance(b)))
    except ValueError:
        return 9999


def first(row: dict[str, str], names: list[str]) -> str:
    for name in names:
        value = clean(row.get(name))
        if value:
            return value
    return ""


def horse_alias_map() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for row in read_csv(HORSE_ALIASES):
        alias = clean(row.get("alias_key"))
        key = clean(row.get("horse_key")) or alias
        if alias and key:
            lookup[alias] = key
    return lookup


def track_alias_map() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for row in read_csv(TRACK_ALIASES):
        raw = clean(row.get("raw_track")).upper()
        canonical = clean(row.get("canonical_track")).upper()
        if raw and canonical:
            lookup[track_key(raw)] = canonical
            lookup[track_key(canonical)] = canonical
    return lookup


def track_key(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\b(BET365|SPORTSBET|LADBROKES|TAB|MRC|VRC|RACING|CLUB)\b", " ", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def canonical_track(value: object, aliases: dict[str, str]) -> str:
    key = track_key(value)
    return aliases.get(key, " ".join(re.sub(r"[^A-Z0-9]+", " ", clean(value).upper()).split()))


def canonical_horse(value: object, aliases: dict[str, str]) -> str:
    key = horse_key(value)
    return aliases.get(key, key)


def build_edgeiq_groups(horse_aliases: dict[str, str], track_aliases: dict[str, str]) -> dict[str, dict[str, object]]:
    groups: dict[str, dict[str, object]] = {}
    for row in read_csv(UNIVERSE):
        race_date = first(row, ["race_date", "date"])[:10]
        track = canonical_track(first(row, ["track", "meeting"]), track_aliases)
        rn = race_no(first(row, ["race_no", "race_number", "race"]))
        dist = distance(first(row, ["distance", "race_distance", "dist"]))
        horse = canonical_horse(first(row, ["horse_key", "horse", "runner", "horse_name", "runner_name"]), horse_aliases)
        if not race_date or not track or not rn or not horse:
            continue
        key = f"{race_date}_{track}_R{rn}_{dist}"
        group = groups.setdefault(key, {"race_date": race_date, "track": track, "race_no": rn, "distance": dist, "horses": set()})
        group["horses"].add(horse)
    return groups


def build_sectional_groups(horse_aliases: dict[str, str], track_aliases: dict[str, str]) -> dict[str, dict[str, object]]:
    groups: dict[str, dict[str, object]] = {}
    source_rows = read_csv(IDENTITY)
    if not source_rows:
        source_rows = read_csv(MASTER)
    for row in source_rows:
        race_date = first(row, ["race_date", "source_race_date"])[:10]
        track = canonical_track(first(row, ["track", "source_track"]), track_aliases)
        rn = race_no(first(row, ["race_no", "source_race_no", "race_number"]))
        dist = distance(first(row, ["distance", "source_distance"]))
        horse = canonical_horse(first(row, ["horse_key", "horse", "runner", "horse_name", "runner_name"]), horse_aliases)
        source_file = first(row, ["source_file"])
        if not race_date or not track or not horse:
            continue
        key = f"{source_file}|{race_date}_{track}_R{rn}_{dist}"
        group = groups.setdefault(key, {"source_file": source_file, "race_date": race_date, "track": track, "race_no": rn, "distance": dist, "horses": set()})
        group["horses"].add(horse)
    return groups


def status(confidence: int, overlap_pct: float, date_ok: bool, track_ok: bool, distance_ok: bool, race_no_ok: bool, conflicts: list[str]) -> str:
    if conflicts and confidence < 80:
        return "UNSAFE"
    if date_ok and track_ok and distance_ok and overlap_pct >= 72 and confidence >= 88:
        return "TRUSTED"
    if overlap_pct >= 62 and confidence >= 76 and date_ok and (track_ok or distance_ok):
        return "LIKELY"
    if overlap_pct >= 35 and confidence >= 52:
        return "PARTIAL"
    if confidence > 0:
        return "UNSAFE"
    return "UNMATCHED"


def compare(sectional_key: str, sectional: dict[str, object], edgeiq_key: str, edgeiq: dict[str, object]) -> dict[str, object]:
    sectional_horses = set(sectional["horses"])
    edgeiq_horses = set(edgeiq["horses"])
    overlap = sectional_horses & edgeiq_horses
    edgeiq_count = len(edgeiq_horses)
    sectional_count = len(sectional_horses)
    overlap_pct = (len(overlap) / max(1, min(edgeiq_count, sectional_count))) * 100
    date_ok = sectional["race_date"] == edgeiq["race_date"]
    track_ok = sectional["track"] == edgeiq["track"]
    delta = distance_delta(sectional["distance"], edgeiq["distance"])
    distance_ok = delta <= 50
    race_ok = bool(sectional["race_no"]) and sectional["race_no"] == edgeiq["race_no"]
    confidence = 0
    confidence += 22 if date_ok else 0
    confidence += 18 if track_ok else 0
    confidence += 14 if distance_ok else 0
    confidence += 10 if race_ok else 0
    confidence += min(36, round(overlap_pct * 0.36))
    conflicts: list[str] = []
    if not date_ok:
        conflicts.append("date mismatch")
    if not track_ok:
        conflicts.append("track mismatch")
    if not distance_ok:
        conflicts.append(f"distance delta {delta}")
    if not race_ok and sectional["race_no"]:
        conflicts.append("race number mismatch")
    if len(overlap) < 3 and overlap_pct < 50:
        conflicts.append("weak field overlap")
    race_status = status(confidence, overlap_pct, date_ok, track_ok, distance_ok, race_ok, conflicts)
    return {
        "sectional_race_group_key": sectional_key,
        "edgeiq_race_key": edgeiq_key,
        "source_file": sectional["source_file"],
        "source_race_date": sectional["race_date"],
        "source_track": sectional["track"],
        "source_race_no": sectional["race_no"],
        "source_distance": sectional["distance"],
        "edgeiq_race_date": edgeiq["race_date"],
        "edgeiq_track": edgeiq["track"],
        "edgeiq_race_no": edgeiq["race_no"],
        "edgeiq_distance": edgeiq["distance"],
        "date_match": "YES" if date_ok else "NO",
        "track_match": "YES" if track_ok else "NO",
        "distance_match": "YES" if distance_ok else "NO",
        "race_no_match": "YES" if race_ok else "NO",
        "horse_overlap_count": len(overlap),
        "edgeiq_runner_count": edgeiq_count,
        "sectional_runner_count": sectional_count,
        "overlap_pct": f"{overlap_pct:.1f}",
        "distance_delta": delta if delta != 9999 else "",
        "composition_confidence": max(0, min(100, confidence)),
        "race_identity_status": race_status,
        "matched_horses": "|".join(sorted(overlap)),
        "conflict_reason": "; ".join(conflicts),
    }


def candidate_edgeiq(sectional: dict[str, object], edgeiq_groups: dict[str, dict[str, object]]) -> list[tuple[str, dict[str, object]]]:
    candidates: list[tuple[str, dict[str, object]]] = []
    for key, group in edgeiq_groups.items():
        if sectional["race_date"] != group["race_date"]:
            continue
        overlap = set(sectional["horses"]) & set(group["horses"])
        if sectional["track"] == group["track"] or distance_delta(sectional["distance"], group["distance"]) <= 100 or overlap:
            candidates.append((key, group))
    return candidates


def main() -> None:
    horse_aliases = horse_alias_map()
    track_aliases = track_alias_map()
    edgeiq_groups = build_edgeiq_groups(horse_aliases, track_aliases)
    sectional_groups = build_sectional_groups(horse_aliases, track_aliases)
    rows: list[dict[str, object]] = []
    for sectional_key, sectional in sectional_groups.items():
        candidates = candidate_edgeiq(sectional, edgeiq_groups)
        if not candidates:
            rows.append({
                "sectional_race_group_key": sectional_key,
                "edgeiq_race_key": "",
                "source_file": sectional["source_file"],
                "source_race_date": sectional["race_date"],
                "source_track": sectional["track"],
                "source_race_no": sectional["race_no"],
                "source_distance": sectional["distance"],
                "edgeiq_race_date": "",
                "edgeiq_track": "",
                "edgeiq_race_no": "",
                "edgeiq_distance": "",
                "date_match": "NO",
                "track_match": "NO",
                "distance_match": "NO",
                "race_no_match": "NO",
                "horse_overlap_count": 0,
                "edgeiq_runner_count": 0,
                "sectional_runner_count": len(sectional["horses"]),
                "overlap_pct": "0.0",
                "distance_delta": "",
                "composition_confidence": 0,
                "race_identity_status": "UNMATCHED",
                "matched_horses": "",
                "conflict_reason": "no EDGEiQ candidate race",
            })
            continue
        scored = [compare(sectional_key, sectional, edgeiq_key, edgeiq) for edgeiq_key, edgeiq in candidates]
        scored.sort(key=lambda row: int(row["composition_confidence"]), reverse=True)
        rows.extend(scored[:5])
    status_counts = Counter(str(row["race_identity_status"]) for row in rows)
    best_rows = {}
    for row in rows:
        key = str(row["sectional_race_group_key"])
        if key not in best_rows or int(row["composition_confidence"]) > int(best_rows[key]["composition_confidence"]):
            best_rows[key] = row
    summary = [
        {"metric": "sectional_race_groups", "value": len(sectional_groups)},
        {"metric": "edgeiq_race_groups", "value": len(edgeiq_groups)},
        {"metric": "candidate_rows", "value": len(rows)},
        {"metric": "best_trusted", "value": sum(1 for row in best_rows.values() if row["race_identity_status"] == "TRUSTED")},
        {"metric": "best_likely", "value": sum(1 for row in best_rows.values() if row["race_identity_status"] == "LIKELY")},
        {"metric": "best_partial", "value": sum(1 for row in best_rows.values() if row["race_identity_status"] == "PARTIAL")},
        {"metric": "best_unmatched", "value": sum(1 for row in best_rows.values() if row["race_identity_status"] == "UNMATCHED")},
    ]
    summary.extend({"metric": f"status_{key.lower()}", "value": value} for key, value in sorted(status_counts.items()))
    write_csv(OUT, rows, FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    print("=" * 90)
    print("EDGEIQ SECTIONAL FIELD COMPOSITION MATCH V1")
    print("=" * 90)
    print("SECTIONAL RACES:", len(sectional_groups))
    print("CANDIDATE ROWS:", len(rows))
    print("BEST TRUSTED:", summary[3]["value"])
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
