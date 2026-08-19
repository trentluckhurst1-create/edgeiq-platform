from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
BATCH_DIR = DATA / "racingcom_rendered_speed_data_batches"

CSV_NORMALISED = DATA / "racingcom_sectionals_normalised_v1.csv"
HISTORY_MASTER = DATA / "racingcom_sectional_history_master_v1.csv"

WAREHOUSE_OUT = DATA / "racingcom_sectional_warehouse_v2.csv"
HORSE_PROFILE_OUT = DATA / "racingcom_sectional_horse_profiles_v2.csv"
RACE_PROFILE_OUT = DATA / "racingcom_sectional_race_profiles_v2.csv"
AUDIT_OUT = DATA / "racingcom_sectional_warehouse_v2_audit.csv"

COUNTRY_SUFFIXES = ("NZ", "IRE", "GB", "FR", "USA", "JPN", "GER", "SAF")
SPEED_COLUMNS = ("early_speed", "mid_speed", "late_speed", "peak_speed", "avg_speed")

WAREHOUSE_COLUMNS = [
    "meeting_date",
    "track",
    "race_no",
    "horse_name",
    "horse_key",
    "position",
    "layout_type",
    "dist_run",
    "early_speed",
    "mid_speed",
    "late_speed",
    "peak_speed",
    "avg_speed",
    "source_file",
    "source_url",
]

HORSE_PROFILE_COLUMNS = [
    "horse_key",
    "horse_name",
    "runs_with_sectionals",
    "avg_early_speed",
    "avg_mid_speed",
    "avg_late_speed",
    "avg_peak_speed",
    "avg_speed",
    "best_early_speed",
    "best_mid_speed",
    "best_late_speed",
    "best_peak_speed",
    "latest_meeting_date",
    "latest_track",
    "latest_race_no",
]

RACE_PROFILE_COLUMNS = [
    "meeting_date",
    "track",
    "race_no",
    "runners",
    "avg_field_speed",
    "avg_early_speed",
    "avg_mid_speed",
    "avg_late_speed",
    "avg_peak_speed",
    "layout_types_present",
]

AUDIT_COLUMNS = [
    "batch_normalised_files",
    "batch_splits_files",
    "batch_offsets",
    "legacy_source_files_used",
    "warehouse_rows",
    "warehouse_unique_horses",
    "warehouse_unique_races",
    "layout_a_rows",
    "layout_b_rows",
    "horses_with_multiple_runs",
    "races_with_multiple_runners",
    "final_status",
]


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return "" if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as handle:
            return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    tmp.replace(path)


def canonical_horse_key(value: Any) -> str:
    raw = clean(value).upper()
    if not raw:
        return ""
    suffix_pattern = "|".join(COUNTRY_SUFFIXES)
    raw = re.sub(rf"\s*\(({suffix_pattern})\)\s*$", "", raw, flags=re.IGNORECASE)
    raw = re.sub(rf"\s+({suffix_pattern})\s*$", "", raw, flags=re.IGNORECASE)
    raw = re.sub(rf"({suffix_pattern})$", "", raw, flags=re.IGNORECASE)
    return re.sub(r"[^A-Z0-9]+", "", raw)


def track_display(value: Any) -> str:
    track = clean(value).upper()
    track = re.sub(r"^(SPORTSBET|LADBROKES|BET365|PICKLEBET PARK|SOUTHSIDE)\s+", "", track)
    track = re.sub(r"[^A-Z0-9]+", " ", track)
    return re.sub(r"\s+", " ", track).strip()


def race_no_key(value: Any) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else clean(value)


def parse_float(value: Any) -> float | None:
    text = clean(value).replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def normalise_speed(value: Any) -> float | None:
    parsed = parse_float(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed * 3.6 if parsed < 30 else parsed


def format_number(value: float | None) -> str:
    if value is None:
        return ""
    rounded = round(value, 2)
    if rounded.is_integer():
        return str(int(rounded))
    return f"{rounded:.2f}".rstrip("0").rstrip(".")


def avg(values: list[float]) -> float | None:
    return mean(values) if values else None


def int_sort(value: Any) -> int:
    match = re.search(r"\d+", clean(value))
    return int(match.group(0)) if match else 999


def date_sort(value: Any) -> str:
    return clean(value) or "0000-00-00"


def race_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return clean(row.get("meeting_date")), track_display(row.get("track")), race_no_key(row.get("race_no"))


def candidate_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (*race_key(row), canonical_horse_key(row.get("horse_key") or row.get("horse_name")))


def source_list(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        for piece in clean(value).split(";"):
            piece = clean(piece)
            if piece and piece not in parts:
                parts.append(piece)
    return ";".join(parts)


def speed_score(row: dict[str, Any]) -> int:
    return sum(1 for column in SPEED_COLUMNS if parse_float(row.get(column)) is not None)


def row_quality(row: dict[str, Any]) -> tuple[int, int, int]:
    layout = clean(row.get("layout_type")).upper()
    priority = {
        "LAYOUT_A_SUMMARY_SPEED": 50,
        "CSV_DOWNLOAD_SUMMARY_SPEED": 40,
        "HISTORY_SUMMARY_SPEED": 35,
        "LAYOUT_B_SPLIT_TIMING": 25,
    }.get(layout, 10)
    return speed_score(row), priority, 1 if clean(row.get("dist_run")) else 0


def batch_offset(path: Path) -> str:
    match = re.search(r"batch_(\d+)_", path.name)
    return match.group(1) if match else ""


def build_candidate(path: Path, row: dict[str, Any], layout_type: str, url_column: str) -> dict[str, str]:
    horse_name = clean(row.get("horse_name") or row.get("horse") or row.get("runner"))
    candidate = {
        "meeting_date": clean(row.get("meeting_date") or row.get("race_date")),
        "track": track_display(row.get("track")),
        "race_no": race_no_key(row.get("race_no")),
        "horse_name": horse_name,
        "horse_key": canonical_horse_key(row.get("horse_key") or horse_name),
        "position": clean(row.get("position") or row.get("finish_position")),
        "layout_type": clean(row.get("layout_type")) or layout_type,
        "dist_run": clean(row.get("dist_run") or row.get("distance")),
        "source_file": path.name,
        "source_url": clean(row.get(url_column) or row.get("source_url") or row.get("source_speed_data_url")),
    }
    for column in SPEED_COLUMNS:
        candidate[column] = format_number(normalise_speed(row.get(column)))
    return candidate


def split_candidates(split_files: list[Path]) -> tuple[list[dict[str, str]], set[tuple[str, str, str, str]]]:
    grouped: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for path in split_files:
        for row in read_csv(path):
            candidate = build_candidate(path, row, "LAYOUT_B_SPLIT_TIMING", "source_url")
            key = candidate_key(candidate)
            if all(key):
                grouped.setdefault(key, candidate)
    return list(grouped.values()), set(grouped)


def merge_candidate(existing: dict[str, str] | None, new_row: dict[str, str]) -> dict[str, str]:
    if existing is None:
        return new_row
    if row_quality(new_row) > row_quality(existing):
        merged = dict(new_row)
        other = existing
    else:
        merged = dict(existing)
        other = new_row
    merged["source_file"] = source_list(merged.get("source_file"), other.get("source_file"))
    merged["source_url"] = source_list(merged.get("source_url"), other.get("source_url"))
    for column in WAREHOUSE_COLUMNS:
        if not clean(merged.get(column)) and clean(other.get(column)):
            merged[column] = clean(other.get(column))
    return merged


def build_warehouse() -> tuple[list[dict[str, str]], list[Path], list[Path], list[str]]:
    normalised_files = sorted(BATCH_DIR.glob("batch_*_normalised.csv")) if BATCH_DIR.exists() else []
    split_files = sorted(BATCH_DIR.glob("batch_*_splits.csv")) if BATCH_DIR.exists() else []
    split_rows, split_keys = split_candidates(split_files)
    candidates: list[dict[str, str]] = []

    for path in normalised_files:
        for row in read_csv(path):
            candidate = build_candidate(path, row, "LAYOUT_A_SUMMARY_SPEED", "source_url")
            key = candidate_key(candidate)
            if key in split_keys and clean(candidate.get("layout_type")).upper() == "LAYOUT_B_SPLIT_TIMING":
                candidate["source_file"] = source_list(candidate["source_file"], f"batch_{batch_offset(path)}_splits.csv")
            candidates.append(candidate)
    candidates.extend(split_rows)

    legacy_used: list[str] = []
    for path, layout in ((CSV_NORMALISED, "CSV_DOWNLOAD_SUMMARY_SPEED"), (HISTORY_MASTER, "HISTORY_SUMMARY_SPEED")):
        rows = read_csv(path)
        if rows:
            legacy_used.append(path.name)
        for row in rows:
            candidates.append(build_candidate(path, row, layout, "source_speed_data_url"))

    by_key: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for candidate in candidates:
        key = candidate_key(candidate)
        if not all(key):
            continue
        candidate["meeting_date"], candidate["track"], candidate["race_no"], candidate["horse_key"] = key
        by_key[key] = merge_candidate(by_key.get(key), candidate)

    rows = sorted(
        by_key.values(),
        key=lambda row: (
            date_sort(row.get("meeting_date")),
            clean(row.get("track")),
            int_sort(row.get("race_no")),
            int_sort(row.get("position")),
            clean(row.get("horse_name")),
        ),
    )
    return rows, normalised_files, split_files, legacy_used


def build_horse_profiles(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if clean(row.get("horse_key")):
            groups[clean(row.get("horse_key"))].append(row)

    profiles: list[dict[str, str]] = []
    for horse_key, group in groups.items():
        latest = max(group, key=lambda row: (date_sort(row.get("meeting_date")), int_sort(row.get("race_no"))))
        names = Counter(clean(row.get("horse_name")) for row in group if clean(row.get("horse_name")))
        profile = {
            "horse_key": horse_key,
            "horse_name": names.most_common(1)[0][0] if names else clean(latest.get("horse_name")),
            "runs_with_sectionals": len(group),
            "latest_meeting_date": clean(latest.get("meeting_date")),
            "latest_track": clean(latest.get("track")),
            "latest_race_no": clean(latest.get("race_no")),
        }
        for column in SPEED_COLUMNS:
            values = [value for value in (parse_float(row.get(column)) for row in group) if value is not None]
            profile[f"avg_{column}" if column != "avg_speed" else "avg_speed"] = format_number(avg(values))
            if column != "avg_speed":
                profile[f"best_{column}"] = format_number(max(values) if values else None)
        profiles.append(profile)
    return sorted(profiles, key=lambda row: clean(row.get("horse_name")))


def build_race_profiles(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = race_key(row)
        if all(key):
            groups[key].append(row)
    profiles: list[dict[str, str]] = []
    for (meeting_date, track, rn), group in groups.items():
        profile = {
            "meeting_date": meeting_date,
            "track": track,
            "race_no": rn,
            "runners": len(group),
            "layout_types_present": ";".join(sorted({clean(row.get("layout_type")) for row in group if clean(row.get("layout_type"))})),
        }
        profile["avg_field_speed"] = format_number(avg([value for value in (parse_float(row.get("avg_speed")) for row in group) if value is not None]))
        for column in ("early_speed", "mid_speed", "late_speed", "peak_speed"):
            profile[f"avg_{column}"] = format_number(avg([value for value in (parse_float(row.get(column)) for row in group) if value is not None]))
        profiles.append(profile)
    return sorted(profiles, key=lambda row: (date_sort(row.get("meeting_date")), clean(row.get("track")), int_sort(row.get("race_no"))))


def build_audit(rows: list[dict[str, str]], normalised_files: list[Path], split_files: list[Path], legacy_used: list[str]) -> list[dict[str, str]]:
    horse_counts = Counter(clean(row.get("horse_key")) for row in rows if clean(row.get("horse_key")))
    race_counts = Counter(race_key(row) for row in rows if all(race_key(row)))
    offsets = sorted({batch_offset(path) for path in normalised_files if batch_offset(path)})
    final_status = "NO_BATCH_FILES_FOUND"
    if rows and normalised_files:
        final_status = "SECTIONAL_WAREHOUSE_V2_BUILT"
    elif rows:
        final_status = "SECTIONAL_WAREHOUSE_V2_PARTIAL_LEGACY_ONLY"
    return [
        {
            "batch_normalised_files": len(normalised_files),
            "batch_splits_files": len(split_files),
            "batch_offsets": ";".join(offsets),
            "legacy_source_files_used": ";".join(legacy_used),
            "warehouse_rows": len(rows),
            "warehouse_unique_horses": len(horse_counts),
            "warehouse_unique_races": len(race_counts),
            "layout_a_rows": sum(1 for row in rows if clean(row.get("layout_type")).upper() == "LAYOUT_A_SUMMARY_SPEED"),
            "layout_b_rows": sum(1 for row in rows if clean(row.get("layout_type")).upper() == "LAYOUT_B_SPLIT_TIMING"),
            "horses_with_multiple_runs": sum(1 for count in horse_counts.values() if count > 1),
            "races_with_multiple_runners": sum(1 for count in race_counts.values() if count > 1),
            "final_status": final_status,
        }
    ]


def main() -> None:
    rows, normalised_files, split_files, legacy_used = build_warehouse()
    horse_profiles = build_horse_profiles(rows)
    race_profiles = build_race_profiles(rows)
    audit = build_audit(rows, normalised_files, split_files, legacy_used)

    write_csv(WAREHOUSE_OUT, rows, WAREHOUSE_COLUMNS)
    write_csv(HORSE_PROFILE_OUT, horse_profiles, HORSE_PROFILE_COLUMNS)
    write_csv(RACE_PROFILE_OUT, race_profiles, RACE_PROFILE_COLUMNS)
    write_csv(AUDIT_OUT, audit, AUDIT_COLUMNS)

    row = audit[0]
    print("Racing.com sectional warehouse V2 built")
    print(f"batch_normalised_files={row['batch_normalised_files']}")
    print(f"warehouse_rows={row['warehouse_rows']}")
    print(f"warehouse_unique_horses={row['warehouse_unique_horses']}")
    print(f"warehouse_unique_races={row['warehouse_unique_races']}")
    print(f"final_status={row['final_status']}")


if __name__ == "__main__":
    main()
