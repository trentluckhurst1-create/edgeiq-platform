from __future__ import annotations

import csv
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
UNIVERSE = DATA / "edgeiq_vic_three_day_meeting_universe.csv"
SCHEMA = DATA / "edgeiq_sectional_schema_v2.csv"
OUT = DATA / "edgeiq_sectional_validation_engine.csv"
SUMMARY = DATA / "edgeiq_sectional_validation_summary.csv"

SOURCE_FILES = [
    "edgeiq_sectional_schema_v2.csv",
    "edgeiq_sectional_feature_engine_v2.csv",
    "edgeiq_sectional_intelligence_v2.csv",
    "edgeiq_sectional_master_v1.csv",
    "edgeiq_vic_90day_sectional_warehouse_final_v1.csv",
    "edgeiq_vic_sectional_warehouse_v1.csv",
    "edgeiq_universal_sectional_memory_v1.csv",
    "sectionals.csv",
]

FIELDS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key",
    "distance",
    "source_file",
    "has_sectionals",
    "split_count",
    "missing_splits",
    "impossible_time_flag",
    "duplicate_flag",
    "identity_match_status",
    "field_match_status",
    "sectional_quality_grade",
    "sectional_confidence",
    "validation_notes",
]

SUMMARY_FIELDS = ["metric", "value"]


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"} else text


def norm_track(value: object) -> str:
    return " ".join(clean(value).upper().replace("_", " ").replace("|", " ").split())


def horse_key(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def race_no(value: object) -> str:
    digits = re.sub(r"[^0-9]", "", clean(value).upper().replace("RACE", "").replace("R", ""))
    return str(int(digits)) if digits else ""


def first(row: dict[str, str] | None, keys: list[str]) -> str:
    if row is None:
        return ""
    for key in keys:
        value = clean(row.get(key))
        if value:
            return value
    return ""


def race_date(row: dict[str, str]) -> str:
    return first(row, ["race_date", "date", "meeting_date"])[:10]


def track(row: dict[str, str]) -> str:
    return norm_track(first(row, ["track", "venue", "meeting"]))


def horse(row: dict[str, str]) -> str:
    return first(row, ["horse", "horse_name", "runner", "runner_name", "name"])


def distance(row: dict[str, str]) -> str:
    return first(row, ["distance", "race_distance", "dist"])


def runner_id(row: dict[str, str]) -> tuple[str, str, str, str]:
    return race_date(row), track(row), race_no(first(row, ["race_no", "race_number", "race"])), horse_key(first(row, ["horse_key", "runner_key", "horse", "horse_name", "runner", "runner_name"]))


def split_cols(row: dict[str, str]) -> list[str]:
    columns = [
        "sectional_200", "sectional_400", "sectional_600", "last_600", "last_400", "last_200",
        "last600", "last400", "last200", "l600", "l400", "l200", "split_200", "split_400", "split_600",
    ]
    return [col for col in columns if clean(row.get(col))]


def parse_time(value: object) -> float:
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


def impossible(row: dict[str, str]) -> bool:
    for col in split_cols(row):
        value = parse_time(row.get(col))
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


def source_rows() -> tuple[dict[tuple[str, str, str, str], dict[str, str]], Counter]:
    lookup: dict[tuple[str, str, str, str], dict[str, str]] = {}
    counts: Counter = Counter()
    for filename in SOURCE_FILES:
        for row in read_csv(DATA / filename):
            key = runner_id(row)
            if not key[1] or not key[2] or not key[3]:
                continue
            counts[key] += 1
            if key not in lookup:
                lookup[key] = {**row, "_source_file": filename}
    return lookup, counts


def quality(split_count: int, bad: bool, matched: bool, duplicate: bool) -> tuple[str, str]:
    if not matched or split_count == 0:
        return "MISSING", "0"
    if bad:
        return "BAD", "20"
    if split_count >= 6 and not duplicate:
        return "ELITE", "95"
    if split_count >= 4:
        return "GOOD", "80"
    if split_count >= 2:
        return "PARTIAL", "55"
    return "WEAK", "35"


def main() -> None:
    universe = read_csv(UNIVERSE)
    schema = read_csv(SCHEMA)
    source_lookup, duplicate_counts = source_rows()
    schema_lookup = {runner_id(row): row for row in schema if runner_id(row)[3]}
    rows: list[dict[str, object]] = []

    for base in universe:
        key = runner_id(base)
        if not key[1] or not key[2] or not key[3]:
            continue
        source = source_lookup.get(key) or schema_lookup.get(key)
        splits = split_cols(source or {})
        split_count = len(splits)
        bad = impossible(source or {})
        duplicate = duplicate_counts.get(key, 0) > 1
        matched = source is not None and split_count > 0
        grade, confidence = quality(split_count, bad, matched, duplicate)
        notes = []
        if source is None:
            notes.append("no sectional source matched")
        if duplicate:
            notes.append("duplicate source rows detected")
        if bad:
            notes.append("impossible split value detected")
        if source is not None and not split_count:
            notes.append("matched identity but no split fields populated")
        rows.append({
            "race_date": key[0],
            "track": key[1],
            "race_no": key[2],
            "horse": horse(base),
            "horse_key": first(base, ["horse_key", "runner_key"]) or key[3],
            "distance": distance(base),
            "source_file": clean((source or {}).get("_source_file")),
            "has_sectionals": "YES" if matched else "NO",
            "split_count": split_count,
            "missing_splits": max(0, 6 - split_count),
            "impossible_time_flag": "YES" if bad else "NO",
            "duplicate_flag": "YES" if duplicate else "NO",
            "identity_match_status": "MATCHED" if source is not None else "UNMATCHED",
            "field_match_status": "FIELD_MATCH" if source is not None else "MISSING_SOURCE",
            "sectional_quality_grade": grade,
            "sectional_confidence": confidence,
            "validation_notes": "; ".join(notes),
        })

    grade_counts = Counter(str(row["sectional_quality_grade"]) for row in rows)
    summary = [
        {"metric": "field_rows", "value": len(rows)},
        {"metric": "matched_rows", "value": sum(1 for row in rows if row["has_sectionals"] == "YES")},
        {"metric": "missing_rows", "value": sum(1 for row in rows if row["sectional_quality_grade"] == "MISSING")},
        {"metric": "bad_rows", "value": sum(1 for row in rows if row["sectional_quality_grade"] == "BAD")},
        {"metric": "duplicate_rows", "value": sum(1 for row in rows if row["duplicate_flag"] == "YES")},
        {"metric": "coverage_pct", "value": f"{(sum(1 for row in rows if row['has_sectionals'] == 'YES') / len(rows) * 100) if rows else 0:.1f}"},
    ] + [{"metric": f"grade_{grade.lower()}", "value": count} for grade, count in sorted(grade_counts.items())]

    write_csv(OUT, rows, FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    print("=" * 90)
    print("EDGEIQ SECTIONAL VALIDATION ENGINE")
    print("=" * 90)
    print("ROWS:", len(rows))
    print("MATCHED:", sum(1 for row in rows if row["has_sectionals"] == "YES"))
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
