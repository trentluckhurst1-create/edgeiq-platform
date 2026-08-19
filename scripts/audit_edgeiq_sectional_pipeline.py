from __future__ import annotations

import csv
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
AUDIT_OUT = DATA / "edgeiq_sectional_pipeline_audit.csv"
SUMMARY_OUT = DATA / "edgeiq_sectional_pipeline_summary.csv"

PATTERNS = ("sectional", "racingcom", "racing_com", "split", "tempo")
SKIP_PARTS = {"node_modules", "dist", ".git", "__pycache__"}
VIC_TRACKS = {
    "BALLARAT", "BENDIGO", "CAULFIELD", "CAULFIELD HEATH", "CRANBOURNE", "FLEMINGTON",
    "GEELONG", "HAMILTON", "HORSHAM", "KYNETON", "MOE", "MORNINGTON", "PAKENHAM",
    "SALE", "SANDOWN", "STAWELL", "SWAN HILL", "WANGARATTA", "WARRACKNABEAL",
    "WARRNAMBOOL", "WERRIBEE", "YARRA VALLEY",
}

AUDIT_FIELDS = [
    "source_file",
    "rows",
    "unique_horses",
    "unique_races",
    "date_min",
    "date_max",
    "track_coverage",
    "vic_race_coverage",
    "missing_race_date",
    "missing_track",
    "missing_race_no",
    "missing_horse",
    "missing_distance",
    "missing_split_fields",
    "duplicate_horse_race_rows",
    "impossible_split_values",
    "malformed_times",
    "non_vic_contamination",
    "stale_output",
    "parser_failure_hints",
    "status",
]

SUMMARY_FIELDS = ["metric", "value"]


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"} else text


def norm_track(value: object) -> str:
    return " ".join(clean(value).upper().replace("_", " ").replace("|", " ").split())


def horse_key(value: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", clean(value).upper())


def race_no(value: object) -> str:
    digits = re.sub(r"[^0-9]", "", clean(value).upper().replace("RACE", "").replace("R", ""))
    return str(int(digits)) if digits else ""


def first(row: dict[str, str], keys: list[str]) -> str:
    for key in keys:
        value = clean(row.get(key))
        if value:
            return value
    return ""


def date_value(row: dict[str, str]) -> str:
    raw = first(row, ["race_date", "date", "meeting_date", "run_date"])
    return raw[:10] if raw else ""


def runner_name(row: dict[str, str]) -> str:
    return first(row, ["horse", "horse_name", "runner", "runner_name", "name"])


def distance(row: dict[str, str]) -> str:
    return first(row, ["distance", "race_distance", "dist"])


def race_identity(row: dict[str, str]) -> tuple[str, str, str]:
    return date_value(row), norm_track(first(row, ["track", "venue", "meeting"])), race_no(first(row, ["race_no", "race_number", "race"]))


def runner_identity(row: dict[str, str]) -> tuple[str, str, str, str]:
    race_date, track, race = race_identity(row)
    return race_date, track, race, horse_key(first(row, ["horse_key", "runner_key", "horse", "horse_name", "runner", "runner_name"]))


def split_columns(fieldnames: list[str]) -> list[str]:
    out = []
    for name in fieldnames:
        lowered = name.lower()
        if any(excluded in lowered for excluded in ("rating", "confidence", "grade", "source", "comment", "note", "index", "score")):
            continue
        if any(token in lowered for token in ("split", "last_600", "last600", "last_400", "last400", "last_200", "last200", "l600", "l400", "l200")):
            out.append(name)
            continue
        if re.match(r"^sectional_?\d{3}$", lowered):
            out.append(name)
    return out


def parse_number(value: object) -> float:
    raw = clean(value)
    if not raw:
        return math.nan
    if ":" in raw:
        pieces = raw.split(":")
        try:
            return float(pieces[-1]) + float(pieces[-2]) * 60
        except Exception:
            return math.nan
    try:
        return float(re.sub(r"[^0-9.]", "", raw))
    except ValueError:
        return math.nan


def malformed_time(value: object) -> bool:
    raw = clean(value)
    if not raw:
        return False
    if not re.search(r"\d", raw):
        return True
    if ":" in raw and not re.match(r"^\d{1,2}:\d{2}(\.\d+)?$", raw):
        return True
    return False


def impossible(value: object) -> bool:
    parsed = parse_number(value)
    if math.isnan(parsed):
        return False
    return parsed <= 5 or parsed > 120


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str], str]:
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            return list(reader), list(reader.fieldnames or []), ""
    except Exception as exc:
        return [], [], str(exc)


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


def candidate_csvs() -> list[Path]:
    paths: list[Path] = []
    for path in ROOT.rglob("*.csv"):
        if any(part.lower() in SKIP_PARTS for part in path.parts):
            continue
        if any(pattern in path.name.lower() for pattern in PATTERNS):
            paths.append(path)
    return sorted(paths, key=lambda item: str(item).lower())


def audit_file(path: Path) -> dict[str, object]:
    rows, fields, error = read_csv(path)
    split_cols = split_columns(fields)
    dates = sorted({date_value(row) for row in rows if date_value(row)})
    races = [race_identity(row) for row in rows]
    runners = [runner_identity(row) for row in rows]
    race_counter = Counter(runners)
    tracks = sorted({item[1] for item in races if item[1]})
    vic_races = {item for item in races if item[1] in VIC_TRACKS}
    split_missing = 0
    impossible_count = 0
    malformed_count = 0
    for row in rows:
        populated = [col for col in split_cols if clean(row.get(col))]
        if split_cols and not populated:
            split_missing += 1
        for col in populated:
            if impossible(row.get(col)):
                impossible_count += 1
            if malformed_time(row.get(col)):
                malformed_count += 1
    age_days = (datetime.now(timezone.utc).timestamp() - path.stat().st_mtime) / 86400
    non_vic = len({item for item in races if item[1] and item[1] not in VIC_TRACKS})
    hints = []
    if error:
        hints.append(error)
    if not fields:
        hints.append("no headers")
    if not split_cols:
        hints.append("no split-like columns")
    if rows and not any(runner_name(row) for row in rows):
        hints.append("no horse identity")
    return {
        "source_file": str(path.relative_to(ROOT)),
        "rows": len(rows),
        "unique_horses": len({item[3] for item in runners if item[3]}),
        "unique_races": len({item for item in races if item[1] or item[2]}),
        "date_min": dates[0] if dates else "",
        "date_max": dates[-1] if dates else "",
        "track_coverage": len(tracks),
        "vic_race_coverage": len(vic_races),
        "missing_race_date": sum(1 for row in rows if not date_value(row)),
        "missing_track": sum(1 for row in rows if not race_identity(row)[1]),
        "missing_race_no": sum(1 for row in rows if not race_identity(row)[2]),
        "missing_horse": sum(1 for row in rows if not runner_name(row)),
        "missing_distance": sum(1 for row in rows if not distance(row)),
        "missing_split_fields": split_missing if split_cols else len(rows),
        "duplicate_horse_race_rows": sum(count - 1 for key, count in race_counter.items() if key[3] and count > 1),
        "impossible_split_values": impossible_count,
        "malformed_times": malformed_count,
        "non_vic_contamination": non_vic,
        "stale_output": "YES" if age_days > 7 else "NO",
        "parser_failure_hints": "; ".join(hints),
        "status": "FAIL" if error else "WARN" if hints or impossible_count or malformed_count else "OK",
    }


def main() -> None:
    audit_rows = [audit_file(path) for path in candidate_csvs()]
    total_rows = sum(int(row["rows"]) for row in audit_rows)
    bad_rows = sum(int(row["impossible_split_values"]) + int(row["malformed_times"]) for row in audit_rows)
    summary = [
        {"metric": "detected_csv_files", "value": len(audit_rows)},
        {"metric": "total_rows", "value": total_rows},
        {"metric": "unique_races", "value": sum(int(row["unique_races"]) for row in audit_rows)},
        {"metric": "vic_race_coverage", "value": sum(int(row["vic_race_coverage"]) for row in audit_rows)},
        {"metric": "missing_horse_rows", "value": sum(int(row["missing_horse"]) for row in audit_rows)},
        {"metric": "missing_split_rows", "value": sum(int(row["missing_split_fields"]) for row in audit_rows)},
        {"metric": "duplicate_rows", "value": sum(int(row["duplicate_horse_race_rows"]) for row in audit_rows)},
        {"metric": "bad_split_values", "value": bad_rows},
        {"metric": "stale_outputs", "value": sum(1 for row in audit_rows if row["stale_output"] == "YES")},
        {"metric": "failed_files", "value": sum(1 for row in audit_rows if row["status"] == "FAIL")},
        {"metric": "warning_files", "value": sum(1 for row in audit_rows if row["status"] == "WARN")},
    ]
    write_csv(AUDIT_OUT, audit_rows, AUDIT_FIELDS)
    write_csv(SUMMARY_OUT, summary, SUMMARY_FIELDS)
    print("=" * 90)
    print("EDGEIQ SECTIONAL PIPELINE AUDIT")
    print("=" * 90)
    print("FILES:", len(audit_rows))
    print("ROWS:", total_rows)
    print("BAD SPLIT VALUES:", bad_rows)
    print("OUT:", AUDIT_OUT)


if __name__ == "__main__":
    main()
