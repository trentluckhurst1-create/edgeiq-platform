from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SECTIONALS = DATA / "racingcom_sectionals_normalised_v1.csv"
EDGEIQ_SOURCES = [
    DATA / "edgeiq_vic_live_terminal_feed_v1.csv",
    DATA / "edgeiq_vic_three_day_meeting_universe.csv",
    DATA / "edgeiq_live_runner_board_v1.csv",
]

OUT = DATA / "racingcom_sectionals_coverage_v1.csv"
AUDIT = DATA / "racingcom_sectionals_coverage_v1_audit.csv"

COUNTRY_SUFFIXES = ("IRE", "USA", "JPN", "GER", "SAF", "NZ", "GB", "FR")

OUT_COLUMNS = [
    "track",
    "race_no",
    "horse_name",
    "horse_key",
    "edgeiq_runner_found",
    "sectional_found",
    "avg_speed",
    "early_speed",
    "mid_speed",
    "late_speed",
    "peak_speed",
    "sectional_source_file",
    "coverage_status",
]

AUDIT_COLUMNS = [
    "edgeiq_rows_loaded",
    "sectional_rows_loaded",
    "edgeiq_unique_horses",
    "sectional_unique_horses",
    "matched_horses",
    "missing_horses",
    "coverage_pct",
    "races_checked",
    "races_with_sectional_coverage",
    "final_status",
]


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return "" if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    tmp.replace(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as handle:
            return list(csv.DictReader(handle))


def first(row: dict[str, str], columns: tuple[str, ...]) -> str:
    for column in columns:
        value = clean(row.get(column))
        if value:
            return value
    return ""


def canonical_horse_key(value: Any) -> str:
    raw = clean(value).upper()
    pattern = "|".join(COUNTRY_SUFFIXES)
    without_bracket_suffix = re.sub(rf"\s*\(({pattern})\)\s*$", "", raw, flags=re.IGNORECASE).strip()
    return re.sub(r"[^A-Z0-9]+", "", without_bracket_suffix)


def race_no(value: Any) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def sort_key_string(value: Any) -> tuple[int, str]:
    text = clean(value)
    try:
        return (0, f"{float(text):010.3f}")
    except ValueError:
        return (1, text)


def pick_edgeiq_source() -> tuple[Path | None, list[dict[str, str]]]:
    for path in EDGEIQ_SOURCES:
        rows = read_csv(path)
        if rows:
            return path, rows
    return None, []


def edgeiq_horse_key(row: dict[str, str]) -> str:
    return canonical_horse_key(first(row, ("horse", "runner", "horse_name", "runner_name", "horse_canon", "horse_key")))


def sectional_horse_key(row: dict[str, str]) -> str:
    return canonical_horse_key(first(row, ("horse_name", "horse", "runner", "runner_name", "horse_key")))


def normalise_track(value: Any) -> str:
    raw = clean(value).upper()
    raw = re.sub(r"^(SPORTSBET|SPORTS BET|LADBROKES|BET365|TABTOUCH|TAB)\s+", "", raw).strip()
    raw = re.sub(r"[^A-Z0-9]+", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


def race_key(row: dict[str, str]) -> str:
    return "|".join([normalise_track(row.get("track")), race_no(row.get("race_no"))])


def sectional_quality(row: dict[str, str]) -> tuple[int, tuple[int, str], tuple[int, str], str]:
    has_avg = 1 if clean(row.get("avg_speed")) else 0
    date_key = sort_key_string(row.get("meeting_date"))
    dist_key = sort_key_string(row.get("dist_run"))
    return (has_avg, date_key, dist_key, clean(row.get("source_file")))


def build_sectional_latest(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    by_horse: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = sectional_horse_key(row)
        if key:
            by_horse[key].append(row)
    latest: dict[str, dict[str, str]] = {}
    for key, group in by_horse.items():
        latest[key] = sorted(group, key=sectional_quality, reverse=True)[0]
    return latest


def final_status(edgeiq_rows: int, sectional_rows: int, coverage_pct: float) -> str:
    if edgeiq_rows == 0:
        return "NO_EDGEIQ_RUNNER_SOURCE_FOUND"
    if sectional_rows == 0:
        return "NO_SECTIONALS_FOUND"
    if coverage_pct >= 25:
        return "SECTIONAL_COVERAGE_IMPROVED"
    return "SECTIONAL_COVERAGE_LOW"


def main() -> None:
    source_path, edgeiq_rows_raw = pick_edgeiq_source()
    sectionals = read_csv(SECTIONALS)
    latest_sectional = build_sectional_latest(sectionals)

    edgeiq_rows: list[dict[str, str]] = []
    seen_runner_keys: set[tuple[str, str, str]] = set()
    for row in edgeiq_rows_raw:
        key = edgeiq_horse_key(row)
        track = first(row, ("track", "venue"))
        rn = race_no(first(row, ("race_no", "race_number", "race")))
        if not key:
            continue
        runner_key = (normalise_track(track), rn, key)
        if runner_key in seen_runner_keys:
            continue
        seen_runner_keys.add(runner_key)
        edgeiq_rows.append(row)

    output_rows: list[dict[str, Any]] = []
    matched_horse_keys: set[str] = set()
    races_checked: set[str] = set()
    races_with_coverage: set[str] = set()

    for row in edgeiq_rows:
        key = edgeiq_horse_key(row)
        section = latest_sectional.get(key)
        track = first(row, ("track", "venue"))
        rn = race_no(first(row, ("race_no", "race_number", "race")))
        race = "|".join([normalise_track(track), rn])
        if race:
            races_checked.add(race)
        if section:
            matched_horse_keys.add(key)
            if race:
                races_with_coverage.add(race)
        horse_name = first(row, ("horse", "runner", "horse_name", "runner_name", "horse_key")) or clean(section.get("horse_name") if section else "")
        output_rows.append(
            {
                "track": track,
                "race_no": rn,
                "horse_name": horse_name,
                "horse_key": key,
                "edgeiq_runner_found": "TRUE",
                "sectional_found": "TRUE" if section else "FALSE",
                "avg_speed": clean(section.get("avg_speed")) if section else "",
                "early_speed": clean(section.get("early_speed")) if section else "",
                "mid_speed": clean(section.get("mid_speed")) if section else "",
                "late_speed": clean(section.get("late_speed")) if section else "",
                "peak_speed": clean(section.get("peak_speed")) if section else "",
                "sectional_source_file": clean(section.get("source_file")) if section else "",
                "coverage_status": "MATCHED_SECTIONAL" if section else "MISSING_SECTIONAL",
            }
        )

    edgeiq_keys = {edgeiq_horse_key(row) for row in edgeiq_rows if edgeiq_horse_key(row)}
    for key, section in sorted(latest_sectional.items(), key=lambda item: (normalise_track(item[1].get("track")), race_no(item[1].get("race_no")), item[0])):
        if key in edgeiq_keys:
            continue
        output_rows.append(
            {
                "track": clean(section.get("track")),
                "race_no": race_no(section.get("race_no")),
                "horse_name": clean(section.get("horse_name")),
                "horse_key": key,
                "edgeiq_runner_found": "FALSE",
                "sectional_found": "TRUE",
                "avg_speed": clean(section.get("avg_speed")),
                "early_speed": clean(section.get("early_speed")),
                "mid_speed": clean(section.get("mid_speed")),
                "late_speed": clean(section.get("late_speed")),
                "peak_speed": clean(section.get("peak_speed")),
                "sectional_source_file": clean(section.get("source_file")),
                "coverage_status": "SECTIONAL_ONLY_NOT_IN_EDGEIQ_SOURCE",
            }
        )

    edgeiq_unique_horses = len(edgeiq_keys)
    sectional_unique_horses = len(latest_sectional)
    matched_horses = len(edgeiq_keys & set(latest_sectional))
    missing_horses = max(edgeiq_unique_horses - matched_horses, 0)
    coverage_pct = round((matched_horses / edgeiq_unique_horses * 100), 2) if edgeiq_unique_horses else 0.0
    status = final_status(len(edgeiq_rows), len(sectionals), coverage_pct)

    audit_row = {
        "edgeiq_rows_loaded": len(edgeiq_rows),
        "sectional_rows_loaded": len(sectionals),
        "edgeiq_unique_horses": edgeiq_unique_horses,
        "sectional_unique_horses": sectional_unique_horses,
        "matched_horses": matched_horses,
        "missing_horses": missing_horses,
        "coverage_pct": coverage_pct,
        "races_checked": len(races_checked),
        "races_with_sectional_coverage": len(races_with_coverage),
        "final_status": status,
    }

    write_csv(OUT, output_rows, OUT_COLUMNS)
    write_csv(AUDIT, [audit_row], AUDIT_COLUMNS)

    source_name = source_path.name if source_path else "NO_SOURCE"
    print(f"[racingcom_sectional_coverage_v1] edgeiq_source={source_name}")
    print(f"[racingcom_sectional_coverage_v1] edgeiq_rows={len(edgeiq_rows)} sectionals={len(sectionals)} matched={matched_horses} coverage_pct={coverage_pct}")
    print(f"[racingcom_sectional_coverage_v1] final_status={status}")
    print(f"[racingcom_sectional_coverage_v1] wrote {OUT.relative_to(ROOT)}")
    print(f"[racingcom_sectional_coverage_v1] wrote {AUDIT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
