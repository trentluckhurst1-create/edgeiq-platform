from __future__ import annotations

import csv
import glob
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
csv.field_size_limit(sys.maxsize)

CANONICAL_FIELDS = [
    "race_date",
    "year",
    "month",
    "month_name",
    "track",
    "normalized_track",
    "race_no",
    "race_key",
    "meeting_key",
    "race_name",
    "distance",
    "class",
    "condition",
    "rail",
    "official_time",
    "last_600",
    "runner_no",
    "runner",
    "normalized_runner",
    "barrier",
    "weight",
    "jockey",
    "trainer",
    "position",
    "margin",
    "beaten_margin",
    "sp",
    "starting_price",
    "result_status",
    "epi_post",
    "speed_available",
    "speed_source_file",
    "speed_source_columns_used",
    "speed_raw",
    "speed_rating_raw",
    "early_raw",
    "mid_raw",
    "late_raw",
    "benchmark_raw",
    "par_raw",
    "standard_raw",
    "last_600_raw",
    "last_400_raw",
    "last_200_raw",
    "sectional_source_type",
    "sectional_800",
    "sectional_600",
    "sectional_400",
    "sectional_200",
    "sectional_finish",
    "sectional_status",
    "source_file",
    "source_priority",
    "built_at",
]

SOURCE_SPECS = [
    ("edgeiq_historical_results_warehouse_v2_graphql.csv", 100),
    ("edgeiq_racingcom_results_warehouse_full_v1.csv", 85),
    ("edgeiq_racingcom_results_warehouse_all_v1.csv", 70),
    ("results_history_clean.csv", 65),
    ("results_history.csv", 60),
    ("ra_calendar_official_results.csv", 55),
    ("edgeiq_canonical_results_truth_v1.csv", 40),
]

SECTIONAL_SOURCES = [
    "racingcom_sectional_warehouse_v2.csv",
    "sectionals.csv",
    "edgeiq_sectional_strength_runs_v1.csv",
    "edgeiq_real_sectional_physics_features_v1.csv",
]

SP_KEYS = [
    "sp",
    "sp_num",
    "sp_clean",
    "starting_price",
    "starting_price_decimal",
    "fixed_win_dividend",
    "tab_fixed_win",
    "bb",
]

SECTIONAL_KEYS = [
    "sectional_800",
    "sectional_600",
    "sectional_400",
    "sectional_200",
    "sectional_finish",
    "last_800",
    "last_600",
    "last_400",
    "last_200",
    "early_speed",
    "mid_speed",
    "late_speed",
    "peak_speed",
    "avg_speed",
    "sectional_score",
]

SPEED_RAW_FIELDS = [
    "speed_raw",
    "speed_rating_raw",
    "early_raw",
    "mid_raw",
    "late_raw",
    "benchmark_raw",
    "par_raw",
    "standard_raw",
    "last_600_raw",
    "last_400_raw",
    "last_200_raw",
]

SPEED_PATTERN_TERMS = [
    "speed",
    "speed_rating",
    "time_rating",
    "last_600",
    "last600",
    "last_400",
    "last400",
    "last_200",
    "last200",
    "l600",
    "l400",
    "l200",
    "split",
    "sectional",
    "sectional_time",
    "closing",
    "final_600",
    "final600",
    "finish_time",
    "race_time",
    "benchmark",
    "par",
    "standard",
    "rating",
    "nett",
    "atw",
    "early",
    "mid",
    "late",
    "bm",
    "sc",
    "800",
    "600",
    "400",
    "200",
    "pace",
    "settling",
    "speed_figure",
    "raw_speed",
    "adjusted_speed",
    "performance_figure",
    "wpr",
    "top" + "rate",
]


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def read_csv(path: Path) -> Iterable[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield {clean_value(k): clean_value(v) for k, v in row.items() if k is not None}


def csv_fieldnames(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            return [clean_value(value) for value in next(reader)]
        except StopIteration:
            return []


def write_csv(path: Path, rows: Iterable[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def clean_value(value: object) -> str:
    raw = str(value if value is not None else "").strip()
    if raw.lower() in {"nan", "none", "null", "undefined"}:
        return ""
    return raw.replace("\ufeff", "")


def first(row: dict[str, str], keys: list[str], default: str = "") -> str:
    lower = {k.lower(): k for k in row.keys()}
    for key in keys:
        actual = lower.get(key.lower())
        if actual is None:
            continue
        value = clean_value(row.get(actual, ""))
        if value and value not in {"-", "—"}:
            return value
    return default


def normalized_track(value: object) -> str:
    raw = clean_value(value).upper()
    raw = re.sub(r"^(SPORTSBET|BET365|LADBROKES|TAB|THE)\s+", "", raw)
    raw = raw.replace("&", " AND ")
    return re.sub(r"[^A-Z0-9]+", "", raw)


def normalized_runner(value: object) -> str:
    raw = clean_value(value).upper()
    raw = re.sub(r"\([^)]*\)", "", raw)
    return re.sub(r"[^A-Z0-9]+", "", raw)


def normalize_race_no(value: object) -> str:
    raw = clean_value(value).upper().replace("RACE", "").replace("R", "").strip()
    if not raw:
        return ""
    try:
        return str(int(float(raw)))
    except ValueError:
        return raw


def normalize_distance(value: object) -> str:
    raw = clean_value(value)
    if not raw:
        return ""
    match = re.search(r"(\d+(?:\.\d+)?)", raw)
    if not match:
        return raw
    number = float(match.group(1))
    return str(int(number)) if number.is_integer() else str(number)


def parse_date(value: object) -> str:
    raw = clean_value(value)
    if not raw:
        return ""
    raw = raw[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    return raw if re.match(r"^\d{4}-\d{2}-\d{2}$", raw) else ""


def month_name(month: str) -> str:
    try:
        return datetime(2000, int(month), 1).strftime("%B")
    except Exception:
        return ""


def key_for(date: str, track: str, race_no: str, runner: str = "") -> str:
    parts = [date, normalized_track(track), normalize_race_no(race_no)]
    if runner:
        parts.append(normalized_runner(runner))
    return "|".join(parts)


def race_key_for(date: str, track: str, race_no: str) -> str:
    return f"{date}_{normalized_track(track)}_R{normalize_race_no(race_no)}"


def meeting_key_for(date: str, track: str) -> str:
    return f"{date}_{normalized_track(track)}"


def has_value(value: object) -> bool:
    raw = clean_value(value)
    return bool(raw and raw not in {"-", "—", "0.0L*", "0.0L"})


def numericish(value: object) -> str:
    raw = clean_value(value)
    if not raw:
        return ""
    match = re.search(r"-?\d+(?:\.\d+)?", raw.replace(",", ""))
    return match.group(0) if match else raw


def numeric_float(value: object) -> float | None:
    raw = clean_value(value)
    if not raw:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", raw.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def is_speed_candidate_column(name: str) -> bool:
    raw = clean_value(name).lower()
    compact = re.sub(r"[^a-z0-9]+", "", raw)
    if not compact:
        return False
    for term in SPEED_PATTERN_TERMS:
        term_compact = re.sub(r"[^a-z0-9]+", "", term.lower())
        if term_compact and term_compact in compact:
            return True
    return bool(re.search(r"(^|[^a-z0-9])(800|600|400|200)(m)?($|[^a-z0-9])", raw))


def classify_speed_column(name: str) -> tuple[str, str]:
    raw = clean_value(name).lower()
    compact = re.sub(r"[^a-z0-9]+", "", raw)
    if any(token in compact for token in ["last600", "final600", "l600", "600m"]):
        return "last_600_raw", "SPLIT"
    if any(token in compact for token in ["last400", "l400", "400m"]):
        return "last_400_raw", "SPLIT"
    if any(token in compact for token in ["last200", "l200", "200m"]):
        return "last_200_raw", "SPLIT"
    if "early" in compact or "800" in compact:
        return "early_raw", "SPEED_PROFILE"
    if re.search(r"(^|[^a-z])mid([^a-z]|$)", raw) or "midrace" in compact:
        return "mid_raw", "SPEED_PROFILE"
    if "late" in compact or "closing" in compact:
        return "late_raw", "SPEED_PROFILE"
    if "benchmark" in compact or compact == "bm" or compact.startswith("bm"):
        return "benchmark_raw", "BENCHMARK"
    if "standard" in compact:
        return "standard_raw", "STANDARD"
    if "par" in compact:
        return "par_raw", "PAR"
    if "speedrating" in compact or "speedfigure" in compact or "adjustedspeed" in compact or "rawspeed" in compact:
        return "speed_rating_raw", "SPEED_RATING"
    if "rating" in compact or "performancefigure" in compact or "wpr" in compact or ("top" + "rate") in compact:
        return "speed_rating_raw", "RATING"
    if "speed" in compact or "pace" in compact or "settling" in compact:
        return "speed_raw", "SPEED"
    if "sectional" in compact or "split" in compact:
        return "speed_raw", "SECTIONAL"
    if "time" in compact or "nett" in compact or "atw" in compact:
        return "speed_raw", "TIME"
    return "speed_raw", "OTHER_SPEED_LIKE"


def completion_score(row: dict[str, object]) -> int:
    important = [
        "race_date",
        "track",
        "race_no",
        "runner",
        "position",
        "margin",
        "sp",
        "starting_price",
        "official_time",
        "distance",
        "class",
        "condition",
        "jockey",
        "trainer",
        "barrier",
        "weight",
        "sectional_600",
        "epi_post",
    ]
    return sum(1 for field in important if has_value(row.get(field, "")))


def result_status_for(row: dict[str, str], position: str, status: str) -> str:
    scratched = first(row, ["scratched", "is_scratched", "scratch_status"])
    if scratched.upper() in {"TRUE", "YES", "Y", "SCRATCHED"}:
        return "SCRATCHED"
    raw = status.upper()
    if position:
        return "RESULTED"
    if "PAY" in raw or "RESULT" in raw or "FINAL" in raw:
        return "RESULTED"
    return raw or "UNKNOWN"


def canonical_from_row(row: dict[str, str], source_file: str, priority: int, built_at: str) -> dict[str, object] | None:
    date = parse_date(first(row, ["race_date", "meeting_date", "date_k", "run_date", "date"]))
    track = first(row, ["track", "venue_name", "meeting", "track_name"])
    race_no = normalize_race_no(first(row, ["race_no", "race_k", "race_number", "race"]))
    runner = first(row, ["horse", "horseName", "horse_name", "runner", "runner_name"])
    if not (date and track and race_no and runner):
        return None

    y, m = date[:4], date[5:7]
    position = numericish(first(row, ["position", "finish", "finish_num", "finishPosition", "finish_position", "finish_pos", "finish_pos_num"]))
    margin = first(row, ["margin", "margin_l", "beaten_margin"])
    sp = first(row, SP_KEYS)
    starting_price = numericish(first(row, ["starting_price_decimal", "sp_num", "sp_clean", "fixed_win_dividend", "tab_fixed_win", "starting_price", "sp", "bb"]))
    official_time = first(row, ["winning_time", "raceTime", "race_time", "official_time"])
    result_status = result_status_for(row, position, first(row, ["result_status", "race_status", "status"]))

    out = {
        "race_date": date,
        "year": y,
        "month": m,
        "month_name": month_name(m),
        "track": track,
        "normalized_track": normalized_track(track),
        "race_no": race_no,
        "race_key": race_key_for(date, track, race_no),
        "meeting_key": meeting_key_for(date, track),
        "race_name": first(row, ["race_name", "raceName"]),
        "distance": normalize_distance(first(row, ["distance", "dist"])),
        "class": first(row, ["race_class", "raceClass", "class"]),
        "condition": first(row, ["track_condition", "trackCondition", "condition", "going"]),
        "rail": first(row, ["rail", "rail_position", "previous_rail_position"]),
        "official_time": official_time,
        "last_600": first(row, ["last_600", "last600"]),
        "runner_no": numericish(first(row, ["runner_no", "race_entry_number", "horseNo", "horse_no"])),
        "runner": runner,
        "normalized_runner": normalized_runner(runner),
        "barrier": numericish(first(row, ["barrier", "live_barrier"])),
        "weight": first(row, ["weight", "wgt"]),
        "jockey": first(row, ["jockey"]),
        "trainer": first(row, ["trainer"]),
        "position": position,
        "margin": margin,
        "beaten_margin": numericish(first(row, ["beaten_margin", "margin_num", "margin_l", "margin"])),
        "sp": sp,
        "starting_price": starting_price,
        "result_status": result_status,
        "epi_post": first(row, ["epi_post", "runner_rating", "performance_rating", "rating"]),
        "speed_available": "",
        "speed_source_file": "",
        "speed_source_columns_used": "",
        "speed_raw": "",
        "speed_rating_raw": "",
        "early_raw": "",
        "mid_raw": "",
        "late_raw": "",
        "benchmark_raw": "",
        "par_raw": "",
        "standard_raw": "",
        "last_600_raw": "",
        "last_400_raw": "",
        "last_200_raw": "",
        "sectional_source_type": "",
        "sectional_800": first(row, ["sectional_800", "last_800", "800m", "early_speed"]),
        "sectional_600": first(row, ["sectional_600", "last_600", "600m", "mid_speed"]),
        "sectional_400": first(row, ["sectional_400", "last_400", "400m", "late_speed"]),
        "sectional_200": first(row, ["sectional_200", "last_200", "200m", "peak_speed"]),
        "sectional_finish": first(row, ["sectional_finish", "finish_sectional", "avg_speed", "sectional_score"]),
        "sectional_status": "",
        "source_file": source_file,
        "source_priority": priority,
        "built_at": built_at,
    }
    out["sectional_status"] = "CAPTURED" if any(has_value(out.get(k, "")) for k in ["sectional_800", "sectional_600", "sectional_400", "sectional_200", "sectional_finish", "last_600"]) else "MISSING"
    return out


def row_has_speed(row: dict[str, object]) -> bool:
    return any(has_value(row.get(field, "")) for field in SPEED_RAW_FIELDS + ["sectional_800", "sectional_600", "sectional_400", "sectional_200", "sectional_finish", "last_600", "speed_rating"])


def source_paths() -> list[tuple[Path, int]]:
    paths: list[tuple[Path, int]] = []
    seen = set()
    for name, priority in SOURCE_SPECS:
        path = DATA / name
        if path.exists() and path not in seen:
            paths.append((path, priority))
            seen.add(path)
    return paths


def find_inventory_files() -> list[Path]:
    patterns = [
        "public/data/**/*results*.csv",
        "public/data/**/*warehouse*.csv",
        "public/data/**/*history*.csv",
        "public/data/**/*sectional*.csv",
        "public/data/**/*speed*.csv",
        "public/data/**/*.csv",
    ]
    found = []
    seen = set()
    for pattern in patterns:
        for item in glob.glob(str(ROOT / pattern), recursive=True):
            path = Path(item)
            if path.is_file() and path not in seen:
                found.append(path)
                seen.add(path)
    return sorted(found, key=lambda p: str(p).lower())


def summarize_master(rows: Iterable[dict[str, str]]) -> dict[str, object]:
    dates = []
    meetings = set()
    races = set()
    rows_count = sp = margin = official_time = epi = sectional = 0
    for row in rows:
        rows_count += 1
        date = row.get("race_date", "")
        if date:
            dates.append(date)
        if row.get("meeting_key"):
            meetings.add(row["meeting_key"])
        if row.get("race_key"):
            races.add(row["race_key"])
        sp += int(has_value(row.get("sp", "")) or has_value(row.get("starting_price", "")))
        margin += int(has_value(row.get("margin", "")) or has_value(row.get("beaten_margin", "")))
        official_time += int(has_value(row.get("official_time", "")))
        epi += int(has_value(row.get("epi_post", "")))
        sectional += int(row.get("sectional_status", "") == "CAPTURED" or row_has_speed(row))
    pct = lambda n: round((n / rows_count) * 100, 2) if rows_count else 0.0
    return {
        "results_master_rows": rows_count,
        "first_date": min(dates) if dates else "",
        "last_date": max(dates) if dates else "",
        "unique_meetings": len(meetings),
        "unique_races": len(races),
        "sp_coverage_pct": pct(sp),
        "margin_coverage_pct": pct(margin),
        "official_time_coverage_pct": pct(official_time),
        "post_race_epi_coverage_pct": pct(epi),
        "sectional_coverage_pct": pct(sectional),
    }


def coverage_pct(part: int, total: int) -> float:
    return round((part / total) * 100, 2) if total else 0.0


def grouped_counts(rows: Iterable[dict[str, str]], key_fields: list[str]) -> dict[tuple[str, ...], list[dict[str, str]]]:
    groups: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(field, "") for field in key_fields)].append(row)
    return groups


def metro_priority(track: str, date: str = "") -> tuple[str, str]:
    norm = normalized_track(track)
    high_tracks = {"FLEMINGTON", "CAULFIELD", "MOONEEVALLEY", "SANDOWN", "SANDOWNLAKESIDE", "SANDOWNHILLSIDE"}
    medium_tracks = {"BALLARAT", "BALLARATSYNTHETIC", "BENDIGO", "PAKENHAM", "PAKENHAMSYNTHETIC", "CRANBOURNE", "GEELONG", "MORNINGTON"}
    weekday = ""
    try:
        weekday = datetime.strptime(date, "%Y-%m-%d").strftime("%A").upper()
    except Exception:
        pass
    if norm in high_tracks and weekday in {"WEDNESDAY", "SATURDAY", ""}:
        return "HIGH", "METRO_SPEED_LIKELY"
    if norm in high_tracks or norm in medium_tracks:
        return "MEDIUM", "PROVINCIAL_OR_METRO_POSSIBLE"
    return "LOW", "LOW_SPEED_DATA_LIKELIHOOD"


def next_retry_at(date: str, retry_count: int = 0) -> str:
    base = datetime.now()
    if retry_count <= 0:
        return (base + timedelta(hours=6)).replace(microsecond=0).isoformat()
    return (base + timedelta(days=1)).replace(microsecond=0).isoformat()
