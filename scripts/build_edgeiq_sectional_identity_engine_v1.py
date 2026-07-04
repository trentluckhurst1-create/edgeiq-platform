from __future__ import annotations

import csv
import math
import re
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
AUDIT = DATA / "edgeiq_sectional_pipeline_audit.csv"
UNIVERSE = DATA / "edgeiq_vic_three_day_meeting_universe.csv"
SCHEMA = DATA / "edgeiq_sectional_schema_v2.csv"
OUT = DATA / "edgeiq_sectional_identity_engine_v1.csv"
SUMMARY = DATA / "edgeiq_sectional_identity_summary_v1.csv"

FIELDS = [
    "source_file",
    "source_row_id",
    "race_date",
    "track",
    "race_no",
    "distance",
    "race_time",
    "horse",
    "horse_key",
    "normalized_track",
    "normalized_horse",
    "matched_race_date",
    "matched_track",
    "matched_race_no",
    "matched_distance",
    "matched_horse",
    "matched_horse_key",
    "match_confidence",
    "match_method",
    "identity_status",
    "validation_status",
    "duplicate_flag",
    "conflict_flag",
    "conflict_reason",
    "preferred_row",
    "suppressed_duplicate",
    "split_count",
    "raw_last_600",
    "raw_last_400",
    "raw_last_200",
    "early_speed_raw",
    "midrace_speed_raw",
    "late_speed_raw",
    "sustained_speed",
    "fatigue_index",
    "sectional_rating",
    "sectional_confidence",
    "identity_notes",
]

SUMMARY_FIELDS = ["metric", "value"]

TRACK_ALIASES = {
    "CAULFIELD HEATH": "CAULFIELD HEATH",
    "CAULFIELD": "CAULFIELD",
    "THE VALLEY": "MOONEE VALLEY",
    "MOONEE VALLEY": "MOONEE VALLEY",
    "BET365 GEELONG": "GEELONG",
    "GEELONG": "GEELONG",
    "SPORTSBET PAKENHAM": "PAKENHAM",
    "PAKENHAM": "PAKENHAM",
    "LADBROKES PARK": "SANDOWN",
    "SANDOWN": "SANDOWN",
}


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"} else text


def normalized_horse(value: object) -> str:
    text = clean(value).upper()
    text = text.replace("'", "").replace("`", "").replace("’", "")
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"\b(NZ|AUS|IRE|GB|USA|FR|JPN|SAF|GER)\b", "", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def normalized_track(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\b(BET365|SPORTSBET|LADBROKES|TAB|MRC|VRC|RACING)\b", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text).strip()
    text = " ".join(text.split())
    return TRACK_ALIASES.get(text, text)


def race_no(value: object) -> str:
    digits = re.sub(r"[^0-9]", "", clean(value).upper().replace("RACE", "").replace("R", ""))
    return str(int(digits)) if digits else ""


def distance_value(value: object) -> str:
    digits = re.sub(r"[^0-9]", "", clean(value))
    return str(int(digits)) if digits else ""


def first(row: dict[str, str] | None, keys: list[str]) -> str:
    if row is None:
        return ""
    for key in keys:
        value = clean(row.get(key))
        if value:
            return value
    return ""


def date_value(row: dict[str, str]) -> str:
    return first(row, ["race_date", "date", "meeting_date", "run_date"])[:10]


def track_value(row: dict[str, str]) -> str:
    return first(row, ["track", "venue", "meeting"])


def horse_value(row: dict[str, str]) -> str:
    return first(row, ["horse", "horse_name", "runner", "runner_name", "name"])


def split_columns(row: dict[str, str]) -> list[str]:
    names = [
        "sectional_200", "sectional_400", "sectional_600", "last_600", "last_400", "last_200",
        "last600", "last400", "last200", "l600", "l400", "l200", "split_200", "split_400", "split_600",
    ]
    return [name for name in names if clean(row.get(name))]


def as_number(value: object) -> float:
    raw = clean(value)
    if not raw:
        return math.nan
    if ":" in raw:
        try:
            parts = raw.split(":")
            return float(parts[-1]) + float(parts[-2]) * 60
        except Exception:
            return math.nan
    try:
        return float(re.sub(r"[^0-9.]", "", raw))
    except ValueError:
        return math.nan


def impossible_split(row: dict[str, str]) -> bool:
    for name in split_columns(row):
        value = as_number(row.get(name))
        if not math.isnan(value) and (value <= 5 or value > 120):
            return True
    return False


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


def source_files() -> list[Path]:
    files: list[Path] = []
    for row in read_csv(AUDIT):
        relative = clean(row.get("source_file"))
        if not relative:
            continue
        path = ROOT / relative
        if path.exists() and path.suffix.lower() == ".csv":
            files.append(path)
    return sorted(set(files), key=lambda item: str(item).lower())


def load_universe() -> list[dict[str, str]]:
    rows = read_csv(UNIVERSE)
    schema = {(date_value(row), normalized_track(track_value(row)), race_no(first(row, ["race_no", "race_number", "race"])), normalized_horse(horse_value(row))): row for row in read_csv(SCHEMA)}
    out = []
    for row in rows:
        key = (date_value(row), normalized_track(track_value(row)), race_no(first(row, ["race_no", "race_number", "race"])), normalized_horse(horse_value(row)))
        merged = dict(row)
        if key in schema:
            merged.update({f"schema_{k}": v for k, v in schema[key].items()})
        out.append(merged)
    return out


def universe_indexes(universe: list[dict[str, str]]) -> dict[str, dict[tuple[str, ...], list[dict[str, str]]]]:
    indexes: dict[str, dict[tuple[str, ...], list[dict[str, str]]]] = {
        "exact_race_horse": {},
        "date_track_race": {},
        "date_track_horse": {},
        "date_horse": {},
        "horse": {},
        "track_distance": {},
    }
    for row in universe:
        date = date_value(row)
        trk = normalized_track(track_value(row))
        rn = race_no(first(row, ["race_no", "race_number", "race"]))
        dist = distance_value(first(row, ["distance", "race_distance", "dist"]))
        hrs = normalized_horse(horse_value(row))
        pairs = [
            ("exact_race_horse", (date, trk, rn, hrs)),
            ("date_track_race", (date, trk, rn)),
            ("date_track_horse", (date, trk, hrs)),
            ("date_horse", (date, hrs)),
            ("horse", (hrs,)),
            ("track_distance", (trk, dist)),
        ]
        for name, key in pairs:
            if all(key):
                indexes[name].setdefault(key, []).append(row)
    return indexes


def distance_close(source: str, target: str) -> bool:
    if not source or not target:
        return False
    try:
        return abs(int(source) - int(target)) <= 50
    except ValueError:
        return False


def score_match(source: dict[str, str], candidate: dict[str, str]) -> tuple[int, str, list[str]]:
    notes: list[str] = []
    src_date = date_value(source)
    src_track = normalized_track(track_value(source))
    src_race = race_no(first(source, ["race_no", "race_number", "race"]))
    src_dist = distance_value(first(source, ["distance", "race_distance", "dist"]))
    src_horse = normalized_horse(horse_value(source))
    dst_date = date_value(candidate)
    dst_track = normalized_track(track_value(candidate))
    dst_race = race_no(first(candidate, ["race_no", "race_number", "race"]))
    dst_dist = distance_value(first(candidate, ["distance", "race_distance", "dist"]))
    dst_horse = normalized_horse(horse_value(candidate))
    if not src_horse or not dst_horse:
        return 0, "UNMATCHED", ["missing horse identity"]
    horse_ratio = SequenceMatcher(None, src_horse, dst_horse).ratio()
    score = 0
    if src_date and src_date == dst_date:
        score += 25
    elif src_date:
        notes.append("date mismatch")
    if src_track and src_track == dst_track:
        score += 20
    elif src_track:
        notes.append("track mismatch")
    if src_race and src_race == dst_race:
        score += 15
    elif src_race:
        notes.append("race number mismatch")
    if src_dist and dst_dist and src_dist == dst_dist:
        score += 10
    elif distance_close(src_dist, dst_dist):
        score += 6
        notes.append("distance tolerance match")
    elif src_dist:
        notes.append("distance mismatch")
    if src_horse == dst_horse:
        score += 30
    elif horse_ratio >= 0.88:
        score += 20
        notes.append("fuzzy horse match")
    elif horse_ratio >= 0.78:
        score += 12
        notes.append("weak fuzzy horse match")
    else:
        notes.append("horse mismatch")

    if src_date == dst_date and src_track == dst_track and src_race == dst_race and src_horse == dst_horse:
        method = "EXACT"
    elif src_date == dst_date and src_track == dst_track and src_race == dst_race and horse_ratio >= 0.88:
        method = "EXACT_NORMALIZED"
    elif src_date == dst_date and src_track == dst_track and src_horse == dst_horse:
        method = "DATE_TRACK_HORSE"
    elif src_date == dst_date and src_dist and distance_close(src_dist, dst_dist) and src_horse == dst_horse:
        method = "DATE_DISTANCE_HORSE"
    elif src_track == dst_track and src_dist and distance_close(src_dist, dst_dist):
        method = "TRACK_DISTANCE"
    elif horse_ratio >= 0.88:
        method = "FUZZY_HORSE"
    elif score:
        method = "PARTIAL"
    else:
        method = "UNMATCHED"
    return min(100, score), method, notes


def identity_status(confidence: int, method: str, source: dict[str, str]) -> str:
    has_race = bool(date_value(source) and normalized_track(track_value(source)) and race_no(first(source, ["race_no", "race_number", "race"])))
    has_horse = bool(normalized_horse(horse_value(source)))
    if confidence >= 92 and method in {"EXACT", "EXACT_NORMALIZED"} and has_race and has_horse:
        return "TRUSTED"
    if confidence >= 82 and has_race and has_horse and method in {"DATE_TRACK_HORSE", "DATE_DISTANCE_HORSE", "FUZZY_HORSE"}:
        return "LIKELY"
    if confidence >= 58 and has_horse:
        return "PARTIAL"
    if confidence > 0:
        return "UNSAFE"
    return "UNMATCHED"


def candidate_pool(source: dict[str, str], indexes: dict[str, dict[tuple[str, ...], list[dict[str, str]]]]) -> list[dict[str, str]]:
    src_date = date_value(source)
    src_track = normalized_track(track_value(source))
    src_race = race_no(first(source, ["race_no", "race_number", "race"]))
    src_dist = distance_value(first(source, ["distance", "race_distance", "dist"]))
    src_horse = normalized_horse(horse_value(source))
    keys = [
        ("exact_race_horse", (src_date, src_track, src_race, src_horse)),
        ("date_track_race", (src_date, src_track, src_race)),
        ("date_track_horse", (src_date, src_track, src_horse)),
        ("date_horse", (src_date, src_horse)),
        ("horse", (src_horse,)),
        ("track_distance", (src_track, src_dist)),
    ]
    pool: list[dict[str, str]] = []
    seen: set[int] = set()
    for name, key in keys:
        if not all(key):
            continue
        for row in indexes[name].get(key, []):
            marker = id(row)
            if marker not in seen:
                pool.append(row)
                seen.add(marker)
    return pool[:80]


def best_candidate(source: dict[str, str], indexes: dict[str, dict[tuple[str, ...], list[dict[str, str]]]]) -> tuple[dict[str, str] | None, int, str, list[str]]:
    if not normalized_horse(horse_value(source)):
        return None, 0, "UNMATCHED", ["missing horse identity"]
    universe = candidate_pool(source, indexes)
    if not universe:
        return None, 0, "UNMATCHED", ["no indexed candidate"]
    scored = []
    for candidate in universe:
        score, method, notes = score_match(source, candidate)
        if score:
            scored.append((score, method, notes, candidate))
    if not scored:
        return None, 0, "UNMATCHED", ["no candidate above zero"]
    scored.sort(key=lambda item: item[0], reverse=True)
    score, method, notes, candidate = scored[0]
    return candidate, score, method, notes


def build_rows() -> list[dict[str, object]]:
    universe = load_universe()
    indexes = universe_indexes(universe)
    rows: list[dict[str, object]] = []
    preferred_key_counts: Counter = Counter()
    raw_identity_counts: Counter = Counter()
    for path in source_files():
        for index, source in enumerate(read_csv(path), start=1):
            source_file = str(path.relative_to(ROOT))
            split_count = len(split_columns(source))
            candidate, confidence, method, notes = best_candidate(source, indexes)
            status = identity_status(confidence, method, source)
            validation = "BAD_SPLIT" if impossible_split(source) else "HAS_SPLITS" if split_count else "NO_SPLITS"
            matched_key = ""
            if candidate:
                matched_key = "|".join([
                    date_value(candidate),
                    normalized_track(track_value(candidate)),
                    race_no(first(candidate, ["race_no", "race_number", "race"])),
                    normalized_horse(horse_value(candidate)),
                ])
                preferred_key_counts[matched_key] += 1
            raw_key = "|".join([date_value(source), normalized_track(track_value(source)), race_no(first(source, ["race_no", "race_number", "race"])), normalized_horse(horse_value(source))])
            raw_identity_counts[raw_key] += 1
            rows.append({
                "source_file": source_file,
                "source_row_id": index,
                "race_date": date_value(source),
                "track": normalized_track(track_value(source)),
                "race_no": race_no(first(source, ["race_no", "race_number", "race"])),
                "distance": distance_value(first(source, ["distance", "race_distance", "dist"])),
                "race_time": first(source, ["race_time", "time", "jump_time"]),
                "horse": horse_value(source),
                "horse_key": first(source, ["horse_key", "runner_key"]) or normalized_horse(horse_value(source)),
                "normalized_track": normalized_track(track_value(source)),
                "normalized_horse": normalized_horse(horse_value(source)),
                "matched_race_date": date_value(candidate or {}),
                "matched_track": normalized_track(track_value(candidate or {})),
                "matched_race_no": race_no(first(candidate or {}, ["race_no", "race_number", "race"])),
                "matched_distance": distance_value(first(candidate or {}, ["distance", "race_distance", "dist"])),
                "matched_horse": horse_value(candidate or {}),
                "matched_horse_key": first(candidate or {}, ["horse_key", "runner_key"]) or normalized_horse(horse_value(candidate or {})),
                "match_confidence": confidence,
                "match_method": method,
                "identity_status": status,
                "validation_status": validation,
                "duplicate_flag": "NO",
                "conflict_flag": "NO",
                "conflict_reason": "",
                "preferred_row": "YES" if status in {"TRUSTED", "LIKELY"} and validation != "BAD_SPLIT" else "NO",
                "suppressed_duplicate": "NO",
                "split_count": split_count,
                "raw_last_600": first(source, ["last_600", "last600", "l600"]),
                "raw_last_400": first(source, ["last_400", "last400", "l400"]),
                "raw_last_200": first(source, ["last_200", "last200", "l200"]),
                "early_speed_raw": first(source, ["early_speed", "early_speed_raw"]),
                "midrace_speed_raw": first(source, ["midrace_speed", "midrace_speed_raw"]),
                "late_speed_raw": first(source, ["late_speed", "late_speed_raw"]),
                "sustained_speed": first(source, ["sustained_speed", "sustained_speed_raw"]),
                "fatigue_index": first(source, ["fatigue_index", "fatigue"]),
                "sectional_rating": first(source, ["sectional_rating", "sectional_score", "rating"]),
                "sectional_confidence": first(source, ["sectional_confidence", "confidence"]),
                "identity_notes": "; ".join(notes),
                "_matched_key": matched_key,
                "_raw_key": raw_key,
            })

    best_by_match: dict[str, int] = {}
    for idx, row in enumerate(rows):
        key = str(row.get("_matched_key", ""))
        if not key:
            continue
        current = best_by_match.get(key)
        if current is None or int(row["match_confidence"]) > int(rows[current]["match_confidence"]):
            best_by_match[key] = idx
    for idx, row in enumerate(rows):
        raw_count = raw_identity_counts.get(str(row.get("_raw_key", "")), 0)
        match_count = preferred_key_counts.get(str(row.get("_matched_key", "")), 0)
        duplicate = raw_count > 1 or match_count > 1
        row["duplicate_flag"] = "YES" if duplicate else "NO"
        if duplicate and best_by_match.get(str(row.get("_matched_key", ""))) != idx:
            row["suppressed_duplicate"] = "YES"
            row["preferred_row"] = "NO"
        if duplicate:
            row["conflict_flag"] = "YES"
            row["conflict_reason"] = "multiple sectional rows share source or matched identity"
        row.pop("_matched_key", None)
        row.pop("_raw_key", None)
    return rows


def main() -> None:
    rows = build_rows()
    status_counts = Counter(str(row["identity_status"]) for row in rows)
    method_counts = Counter(str(row["match_method"]) for row in rows)
    summary = [
        {"metric": "identity_rows", "value": len(rows)},
        {"metric": "trusted_rows", "value": status_counts.get("TRUSTED", 0)},
        {"metric": "likely_rows", "value": status_counts.get("LIKELY", 0)},
        {"metric": "partial_rows", "value": status_counts.get("PARTIAL", 0)},
        {"metric": "unsafe_rows", "value": status_counts.get("UNSAFE", 0)},
        {"metric": "unmatched_rows", "value": status_counts.get("UNMATCHED", 0)},
        {"metric": "duplicate_conflicts", "value": sum(1 for row in rows if row["conflict_flag"] == "YES")},
        {"metric": "coverage_pct", "value": f"{((status_counts.get('TRUSTED', 0) + status_counts.get('LIKELY', 0)) / len(rows) * 100) if rows else 0:.1f}"},
    ] + [{"metric": f"method_{method.lower()}", "value": count} for method, count in sorted(method_counts.items())]
    write_csv(OUT, rows, FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    print("=" * 90)
    print("EDGEIQ SECTIONAL IDENTITY ENGINE V1")
    print("=" * 90)
    print("ROWS:", len(rows))
    print("TRUSTED:", status_counts.get("TRUSTED", 0))
    print("LIKELY:", status_counts.get("LIKELY", 0))
    print("UNMATCHED:", status_counts.get("UNMATCHED", 0))
    print("OUT:", OUT)


SUMMARY_FIELDS = ["metric", "value"]


if __name__ == "__main__":
    main()
