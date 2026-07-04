from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RENDERED_NORMALISED = DATA / "racingcom_rendered_speed_data_normalised_v1.csv"
RENDERED_SPLITS = DATA / "racingcom_rendered_speed_data_splits_v1.csv"
CSV_NORMALISED = DATA / "racingcom_sectionals_normalised_v1.csv"
HISTORY_MASTER = DATA / "racingcom_sectional_history_master_v1.csv"

WAREHOUSE_OUT = DATA / "racingcom_sectional_warehouse_v1.csv"
HORSE_PROFILE_OUT = DATA / "racingcom_sectional_horse_profiles_v1.csv"
RACE_PROFILE_OUT = DATA / "racingcom_sectional_race_profiles_v1.csv"
AUDIT_OUT = DATA / "racingcom_sectional_warehouse_v1_audit.csv"

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
    raw = re.sub(rf"\s*\(({suffix_pattern})\)\s*$", "", raw, flags=re.IGNORECASE).strip()
    raw = re.sub(rf"\s+({suffix_pattern})\s*$", "", raw, flags=re.IGNORECASE).strip()
    raw = re.sub(rf"({suffix_pattern})$", "", raw, flags=re.IGNORECASE).strip()
    return re.sub(r"[^A-Z0-9]+", "", raw)


def track_display(value: Any) -> str:
    track = clean(value).upper()
    track = re.sub(r"^(SPORTSBET|LADBROKES|BET365|PICKLEBET PARK|SOUTHSIDE)\s+", "", track)
    track = re.sub(r"[^A-Z0-9]+", " ", track)
    return re.sub(r"\s+", " ", track).strip()


def race_no_key(value: Any) -> str:
    text = clean(value)
    match = re.search(r"\d+", text)
    return str(int(match.group(0))) if match else text


def parse_float(value: Any) -> float | None:
    text = clean(value).replace(",", "")
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def normalise_speed_value(value: Any) -> float | None:
    parsed = parse_float(value)
    if parsed is None or parsed <= 0:
        return None
    # CSV-derived sectional files carry metre-per-second style speeds around 16-19.
    # Rendered Racing.com speed pages carry km/h style speeds around 50-70.
    return parsed * 3.6 if parsed < 30 else parsed


def format_number(value: float | None) -> str:
    if value is None:
        return ""
    rounded = round(value, 2)
    if rounded.is_integer():
        return str(int(rounded))
    return f"{rounded:.2f}".rstrip("0").rstrip(".")


def average(values: list[float]) -> float | None:
    return mean(values) if values else None


def numeric_from_row(row: dict[str, Any], column: str) -> float | None:
    return parse_float(row.get(column))


def source_list(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        for piece in clean(value).split(";"):
            piece = clean(piece)
            if piece and piece not in parts:
                parts.append(piece)
    return ";".join(parts)


def candidate_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        clean(row.get("meeting_date")),
        track_display(row.get("track")),
        race_no_key(row.get("race_no")),
        canonical_horse_key(row.get("horse_key") or row.get("horse_name")),
    )


def race_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return clean(row.get("meeting_date")), track_display(row.get("track")), race_no_key(row.get("race_no"))


def int_sort(value: Any) -> int:
    text = clean(value)
    match = re.search(r"\d+", text)
    return int(match.group(0)) if match else 999


def date_sort(value: Any) -> str:
    return clean(value) or "0000-00-00"


def speed_score(row: dict[str, Any]) -> int:
    return sum(1 for column in SPEED_COLUMNS if parse_float(row.get(column)) is not None)


def row_quality(row: dict[str, Any]) -> tuple[int, int, int]:
    layout = clean(row.get("layout_type")).upper()
    layout_priority = {
        "LAYOUT_A_SUMMARY_SPEED": 40,
        "CSV_DOWNLOAD_SUMMARY_SPEED": 35,
        "HISTORY_SUMMARY_SPEED": 30,
        "LAYOUT_B_SPLIT_TIMING": 20,
    }.get(layout, 10)
    return speed_score(row), layout_priority, 1 if clean(row.get("dist_run")) else 0


def build_candidate(
    source_path: Path,
    row: dict[str, Any],
    layout_type: str,
    source_url_column: str,
    source_file_value: str = "",
) -> dict[str, str]:
    horse_name = clean(row.get("horse_name") or row.get("horse") or row.get("runner"))
    horse_key = canonical_horse_key(row.get("horse_key") or horse_name)
    source_file = source_file_value or clean(row.get("source_file")) or source_path.name
    candidate = {
        "meeting_date": clean(row.get("meeting_date") or row.get("race_date")),
        "track": track_display(row.get("track")),
        "race_no": race_no_key(row.get("race_no")),
        "horse_name": horse_name,
        "horse_key": horse_key,
        "position": clean(row.get("position") or row.get("finish_position")),
        "layout_type": clean(row.get("layout_type")) or layout_type,
        "dist_run": clean(row.get("dist_run") or row.get("distance")),
        "source_file": source_file,
        "source_url": clean(row.get(source_url_column) or row.get("source_url") or row.get("source_speed_data_url")),
    }
    for column in SPEED_COLUMNS:
        candidate[column] = format_number(normalise_speed_value(row.get(column)))
    return candidate


def split_candidates(split_rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], set[tuple[str, str, str, str]]]:
    grouped: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in split_rows:
        candidate = build_candidate(
            RENDERED_SPLITS,
            row,
            "LAYOUT_B_SPLIT_TIMING",
            "source_url",
            RENDERED_SPLITS.name,
        )
        key = candidate_key(candidate)
        if not all(key):
            continue
        grouped.setdefault(key, candidate)
    return list(grouped.values()), set(grouped)


def merge_candidate(existing: dict[str, str] | None, new_row: dict[str, str]) -> dict[str, str]:
    if existing is None:
        return new_row
    if row_quality(new_row) > row_quality(existing):
        merged = dict(new_row)
        previous = existing
    else:
        merged = dict(existing)
        previous = new_row
    merged["source_file"] = source_list(merged.get("source_file"), previous.get("source_file"))
    merged["source_url"] = source_list(merged.get("source_url"), previous.get("source_url"))
    for column in WAREHOUSE_COLUMNS:
        if not clean(merged.get(column)) and clean(previous.get(column)):
            merged[column] = clean(previous.get(column))
    return merged


def build_warehouse() -> tuple[list[dict[str, str]], dict[str, int]]:
    source_rows = {
        RENDERED_NORMALISED: read_csv(RENDERED_NORMALISED),
        RENDERED_SPLITS: read_csv(RENDERED_SPLITS),
        CSV_NORMALISED: read_csv(CSV_NORMALISED),
        HISTORY_MASTER: read_csv(HISTORY_MASTER),
    }
    split_runner_rows, split_keys = split_candidates(source_rows[RENDERED_SPLITS])
    candidates: list[dict[str, str]] = []

    for row in source_rows[RENDERED_NORMALISED]:
        candidate = build_candidate(RENDERED_NORMALISED, row, "LAYOUT_A_SUMMARY_SPEED", "source_url")
        key = candidate_key(candidate)
        if key in split_keys and clean(candidate.get("layout_type")).upper() == "LAYOUT_B_SPLIT_TIMING":
            candidate["source_file"] = source_list(RENDERED_NORMALISED.name, RENDERED_SPLITS.name)
        candidates.append(candidate)

    candidates.extend(split_runner_rows)

    for row in source_rows[CSV_NORMALISED]:
        candidates.append(build_candidate(CSV_NORMALISED, row, "CSV_DOWNLOAD_SUMMARY_SPEED", "source_speed_data_url"))

    for row in source_rows[HISTORY_MASTER]:
        candidates.append(build_candidate(HISTORY_MASTER, row, "HISTORY_SUMMARY_SPEED", "source_speed_data_url"))

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
    input_counts = {path.name: len(rows) for path, rows in source_rows.items()}
    return rows, input_counts


def build_horse_profiles(warehouse_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in warehouse_rows:
        horse_key = clean(row.get("horse_key"))
        if horse_key:
            groups[horse_key].append(row)

    profiles: list[dict[str, str]] = []
    for horse_key, rows in groups.items():
        latest = max(rows, key=lambda row: (date_sort(row.get("meeting_date")), int_sort(row.get("race_no"))))
        name_counts = Counter(clean(row.get("horse_name")) for row in rows if clean(row.get("horse_name")))
        profile = {
            "horse_key": horse_key,
            "horse_name": name_counts.most_common(1)[0][0] if name_counts else clean(latest.get("horse_name")),
            "runs_with_sectionals": len(rows),
            "latest_meeting_date": clean(latest.get("meeting_date")),
            "latest_track": clean(latest.get("track")),
            "latest_race_no": clean(latest.get("race_no")),
        }
        for column in SPEED_COLUMNS:
            values = [value for value in (numeric_from_row(row, column) for row in rows) if value is not None]
            output_column = f"avg_{column}" if column != "avg_speed" else "avg_speed"
            profile[output_column] = format_number(average(values))
            if column != "avg_speed":
                profile[f"best_{column}"] = format_number(max(values) if values else None)
        profiles.append(profile)

    return sorted(profiles, key=lambda row: clean(row.get("horse_name")))


def build_race_profiles(warehouse_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in warehouse_rows:
        key = race_key(row)
        if all(key):
            groups[key].append(row)

    profiles: list[dict[str, str]] = []
    for key, rows in groups.items():
        meeting_date, track, race_no = key
        profile = {
            "meeting_date": meeting_date,
            "track": track,
            "race_no": race_no,
            "runners": len(rows),
            "layout_types_present": ";".join(sorted({clean(row.get("layout_type")) for row in rows if clean(row.get("layout_type"))})),
        }
        profile["avg_field_speed"] = format_number(
            average([value for value in (numeric_from_row(row, "avg_speed") for row in rows) if value is not None])
        )
        for column in ("early_speed", "mid_speed", "late_speed", "peak_speed"):
            profile[f"avg_{column}"] = format_number(
                average([value for value in (numeric_from_row(row, column) for row in rows) if value is not None])
            )
        profiles.append(profile)

    return sorted(profiles, key=lambda row: (date_sort(row.get("meeting_date")), clean(row.get("track")), int_sort(row.get("race_no"))))


def build_audit(warehouse_rows: list[dict[str, str]], input_counts: dict[str, int]) -> list[dict[str, str]]:
    race_groups: dict[tuple[str, str, str], int] = defaultdict(int)
    horse_groups: dict[str, int] = defaultdict(int)
    for row in warehouse_rows:
        horse_groups[clean(row.get("horse_key"))] += 1
        race_groups[race_key(row)] += 1

    missing_or_empty_inputs = [name for name, count in input_counts.items() if count == 0]
    final_status = "NO_SECTIONAL_DATA_FOUND"
    if warehouse_rows:
        final_status = "SECTIONAL_WAREHOUSE_PARTIAL" if missing_or_empty_inputs else "SECTIONAL_WAREHOUSE_BUILT"

    return [
        {
            "warehouse_rows": len(warehouse_rows),
            "warehouse_unique_horses": len({clean(row.get("horse_key")) for row in warehouse_rows if clean(row.get("horse_key"))}),
            "warehouse_unique_races": len(race_groups),
            "layout_a_rows": sum(1 for row in warehouse_rows if clean(row.get("layout_type")).upper() == "LAYOUT_A_SUMMARY_SPEED"),
            "layout_b_rows": sum(1 for row in warehouse_rows if clean(row.get("layout_type")).upper() == "LAYOUT_B_SPLIT_TIMING"),
            "horses_with_multiple_runs": sum(1 for count in horse_groups.values() if count > 1),
            "races_with_multiple_runners": sum(1 for count in race_groups.values() if count > 1),
            "final_status": final_status,
        }
    ]


def main() -> None:
    warehouse_rows, input_counts = build_warehouse()
    horse_profiles = build_horse_profiles(warehouse_rows)
    race_profiles = build_race_profiles(warehouse_rows)
    audit_rows = build_audit(warehouse_rows, input_counts)

    write_csv(WAREHOUSE_OUT, warehouse_rows, WAREHOUSE_COLUMNS)
    write_csv(HORSE_PROFILE_OUT, horse_profiles, HORSE_PROFILE_COLUMNS)
    write_csv(RACE_PROFILE_OUT, race_profiles, RACE_PROFILE_COLUMNS)
    write_csv(AUDIT_OUT, audit_rows, AUDIT_COLUMNS)

    audit = audit_rows[0]
    print("Racing.com sectional warehouse V1 built")
    print(f"warehouse_rows={audit['warehouse_rows']}")
    print(f"warehouse_unique_horses={audit['warehouse_unique_horses']}")
    print(f"warehouse_unique_races={audit['warehouse_unique_races']}")
    print(f"final_status={audit['final_status']}")


if __name__ == "__main__":
    main()
