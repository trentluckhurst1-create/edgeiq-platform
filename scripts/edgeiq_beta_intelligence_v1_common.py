from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

CURRENT_RUNNERS = DATA / "race_fields.csv"
RESULTS_MASTER = DATA / "edgeiq_results_master_v1.csv"
RESULTS_TERMINAL = DATA / "edgeiq_results_terminal_feed_v1.csv"
PROFILE_STATS = DATA / "edgeiq_runner_profile_stats_v1.csv"
LIVE_SPEED_MAP = DATA / "live_speed_map_v3.csv"
LIVE_BOARD_GOVERNED = DATA / "edgeiq_live_runner_board_governed_v1.csv"
EARLY_SPEED = DATA / "edgeiq_current_early_speed_v1.json"
LATE_SPEED = DATA / "edgeiq_current_late_speed_v1.json"
METRO_WEATHER = DATA / "edgeiq_metropolitan_weather_v1.json"

csv.field_size_limit(1024 * 1024 * 128)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean(value: Any) -> str:
    if value is None or isinstance(value, (dict, list, tuple)):
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return "" if text.lower() in {"", "-", "none", "null", "n/a", "na", "unknown"} else text


def canon_runner(value: Any) -> str:
    text = clean(value).upper()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = text.replace("'", "").replace("\u2019", "").replace("&", "AND")
    return re.sub(r"[^A-Z0-9]+", "", text)


def canon_track(value: Any) -> str:
    text = clean(value).upper()
    text = re.sub(r"\b(BET365|SPORTSBET|LADBROKES|TAB|THE)\b", " ", text)
    text = re.sub(r"\b(RACECOURSE|RACING|TRACK)\b", " ", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def normalise_date(value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    text = text.split("T", 1)[0].split(" ", 1)[0].replace("/", "-")
    parts = text.split("-")
    if len(parts) != 3:
        return ""
    if len(parts[0]) == 4:
        y, m, d = parts
    else:
        d, m, y = parts
    try:
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    except ValueError:
        return ""


def parse_date(value: Any) -> date | None:
    text = normalise_date(value)
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def race_no(value: Any) -> str:
    match = re.search(r"\d+", clean(value).upper().replace("R", ""))
    return str(int(match.group(0))) if match else ""


def to_float(value: Any) -> float | None:
    text = clean(value).replace("$", "").replace(",", "").replace("kg", "")
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def round_or_none(value: float | None, digits: int = 1) -> float | None:
    return None if value is None else round(value, digits)


def identity(date_value: Any, meeting: Any, race_number: Any, runner: Any) -> tuple[str, str, str, str]:
    return (normalise_date(date_value), canon_track(meeting), race_no(race_number), canon_runner(runner))


def race_identity(date_value: Any, meeting: Any, race_number: Any) -> tuple[str, str, str]:
    return (normalise_date(date_value), canon_track(meeting), race_no(race_number))


def condition_family(value: Any) -> str:
    text = clean(value).upper()
    if "HEAVY" in text:
        return "HEAVY"
    if "SOFT" in text:
        return "SOFT"
    if "SYNTH" in text or "POLY" in text:
        return "SYNTHETIC"
    if "FIRM" in text:
        return "FIRM"
    if "GOOD" in text:
        return "GOOD"
    return ""


def class_family(value: Any) -> str:
    text = clean(value).upper()
    if not text:
        return ""
    if "MAIDEN" in text or text == "MDN":
        return "MAIDEN"
    match = re.search(r"BM\s*([0-9]+)", text)
    if match:
        number = int(match.group(1))
        if number <= 58:
            return "BM_LOW"
        if number <= 70:
            return "BM_MID"
        return "BM_HIGH"
    if "GROUP" in text or re.search(r"\bG[123]\b", text):
        return "GROUP"
    if "LISTED" in text:
        return "LISTED"
    return re.sub(r"[^A-Z0-9]+", "_", text).strip("_")[:24]


def distance_band(value: Any) -> str:
    distance = to_float(value)
    if distance is None:
        return ""
    d = int(distance)
    if d < 1200:
        return "SPRINT_1000_1199"
    if d < 1400:
        return "SPRINT_1200_1399"
    if d < 1600:
        return "MILE_1400_1599"
    if d < 2000:
        return "MIDDLE_1600_1999"
    return "STAYING_2000_PLUS"


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_summary(path: Path, lines: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "min": None, "max": None, "mean": None, "median": None, "stddev": None, "unique": 0, "null_count": None, "zero_count": 0}
    return {
        "count": len(values),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "mean": round(mean(values), 2),
        "median": round(median(values), 2),
        "stddev": round(pstdev(values), 2) if len(values) > 1 else 0.0,
        "unique": len({round(v, 2) for v in values}),
        "null_count": None,
        "zero_count": sum(1 for v in values if v == 0),
    }


def load_current_runners() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not CURRENT_RUNNERS.exists():
        return rows
    with CURRENT_RUNNERS.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        for index, row in enumerate(csv.DictReader(handle), start=1):
            runner_name = clean(row.get("horse") or row.get("runner"))
            meeting = clean(row.get("display_track") or row.get("track"))
            race_number = race_no(row.get("race_no") or row.get("race_number"))
            runner_number = race_no(row.get("runner_number") or row.get("horse_no") or row.get("saddlecloth"))
            out = {
                "sourceIndex": index,
                "raceDate": normalise_date(row.get("race_date")),
                "meeting": meeting,
                "meetingKey": canon_track(meeting or row.get("track")),
                "raceNumber": int(race_number or 0) or None,
                "raceNo": race_number,
                "runnerId": clean(row.get("runner_id")) or None,
                "runnerNumber": int(runner_number or 0) or None,
                "runnerName": runner_name,
                "normalizedRunner": canon_runner(row.get("horse_canon") or runner_name),
                "distance": to_float(row.get("distance_m") or row.get("distance")),
                "distanceBand": distance_band(row.get("distance_m") or row.get("distance")),
                "raceClass": clean(row.get("race_class") or row.get("class")),
                "classFamily": class_family(row.get("race_class") or row.get("class")),
                "trackCondition": clean(row.get("track_condition") or row.get("track_rating")),
                "conditionFamily": condition_family(row.get("track_condition") or row.get("track_rating")),
                "rail": clean(row.get("rail_position") or row.get("rail")),
                "barrier": to_float(row.get("barrier")),
                "fieldSize": to_float(row.get("field_size")),
                "jockey": clean(row.get("jockey")),
                "trainer": clean(row.get("trainer")),
                "weight": clean(row.get("weight")),
                "market": to_float(row.get("market_price") or row.get("market") or row.get("ui_price")),
                "gear": clean(row.get("current_gear") or row.get("gear_changes")),
                "isScratched": clean(row.get("is_scratched")).lower() in {"true", "1", "yes"} or clean(row.get("runner_status")).upper() == "SCRATCHED",
                "raceKey": clean(row.get("race_key")),
                "raw": row,
            }
            out["identity"] = identity(out["raceDate"], out["meeting"], out["raceNumber"], out["runnerName"])
            out["raceIdentity"] = race_identity(out["raceDate"], out["meeting"], out["raceNumber"])
            rows.append(out)
    return rows


def load_current_projection(path: Path, value_key: str) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("runners", payload if isinstance(payload, list) else [])
    out: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = identity(row.get("raceDate"), row.get("meeting"), row.get("raceNumber"), row.get("runnerName") or row.get("normalizedRunner"))
        if key[3] and key not in out:
            out[key] = row
    return out


def load_exact_csv(path: Path, runner_field: str = "horse") -> dict[tuple[str, str, str, str], dict[str, Any]]:
    if not path.exists():
        return {}
    out: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        for row in csv.DictReader(handle):
            key = identity(row.get("race_date") or row.get("raceDate"), row.get("display_track") or row.get("track") or row.get("meeting"), row.get("race_no") or row.get("raceNumber"), row.get(runner_field) or row.get("runner") or row.get("horse_key"))
            if key[3] and key not in out:
                out[key] = row
    return out


def load_history_for_current(current: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    names = {row["normalizedRunner"] for row in current}
    histories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    source = RESULTS_MASTER if RESULTS_MASTER.exists() else RESULTS_TERMINAL
    if not source.exists():
        return histories
    with source.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        for row in csv.DictReader(handle):
            runner = canon_runner(row.get("normalized_runner") or row.get("runner"))
            if runner not in names:
                continue
            row_date = parse_date(row.get("race_date"))
            if row_date is None:
                continue
            histories[runner].append(
                {
                    "raceDate": row_date,
                    "raceDateText": normalise_date(row.get("race_date")),
                    "track": clean(row.get("track")),
                    "trackKey": canon_track(row.get("track")),
                    "raceNo": race_no(row.get("race_no")),
                    "distance": to_float(row.get("distance")),
                    "distanceBand": distance_band(row.get("distance")),
                    "class": clean(row.get("class")),
                    "classFamily": class_family(row.get("class")),
                    "condition": clean(row.get("condition")),
                    "conditionFamily": condition_family(row.get("condition")),
                    "position": to_float(row.get("position")),
                    "margin": to_float(row.get("beaten_margin") or row.get("margin")),
                    "sp": to_float(row.get("sp") or row.get("starting_price")),
                    "epiPost": to_float(row.get("epi_post")),
                    "earlyRaw": to_float(row.get("early_raw")),
                    "lateRaw": to_float(row.get("late_raw")),
                    "speedRating": to_float(row.get("speed_rating_raw") or row.get("speed_rating")),
                    "finishLen": to_float(row.get("sectional_finish") or row.get("std_finish_len")),
                    "barrier": to_float(row.get("barrier")),
                    "jockey": clean(row.get("jockey")),
                    "trainer": clean(row.get("trainer")),
                    "sourceFile": source.name,
                }
            )
    for bucket in histories.values():
        bucket.sort(key=lambda item: item["raceDate"], reverse=True)
    return histories


def asof_history(history: list[dict[str, Any]], race_date: Any) -> tuple[list[dict[str, Any]], int]:
    selected = parse_date(race_date)
    if selected is None:
        return [], 0
    excluded = sum(1 for row in history if row["raceDate"] >= selected)
    return [row for row in history if row["raceDate"] < selected], excluded


def profile_score(rows: list[dict[str, Any]]) -> float | None:
    if not rows:
        return None
    starts = len(rows)
    wins = sum(1 for row in rows if row.get("position") == 1)
    places = sum(1 for row in rows if row.get("position") is not None and row["position"] <= 3)
    win_pct = wins / starts
    place_pct = places / starts
    return clamp(42 + win_pct * 34 + place_pct * 24 + min(starts, 8) * 1.0)


def score_to_band(value: float | None) -> str | None:
    if value is None:
        return None
    if value >= 85:
        return "STRONG FIT"
    if value >= 70:
        return "POSITIVE"
    if value >= 50:
        return "NEUTRAL"
    if value >= 35:
        return "QUESTIONABLE"
    return "POOR FIT"


def momentum_band(value: float | None) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    if value >= 1.0:
        return "IMPROVING", "IMPROVING"
    if value <= -1.0:
        return "DECLINING", "DECLINING"
    return "HOLDING", "HOLDING"


def source_rows_for_inventory() -> list[dict[str, Any]]:
    return [
        {
            "source_file": "public/data/edgeiq_results_master_v1.csv",
            "builder": "historical results warehouse",
            "source_field": "race_date, runner, track, distance, class, condition, position, margin, epi_post, early_raw, late_raw",
            "units_scale": "dated historical evidence; raw units vary by source field",
            "historical_current": "historical",
            "as_of_safe": "YES when race_date < selected race date",
            "coverage": "current runners by normalized_runner",
            "production_research_status": "production evidence",
            "selected_rejected": "selected",
            "reason": "Primary dated evidence for current-race suitability and form-momentum factors.",
        },
        {
            "source_file": "public/data/edgeiq_current_early_speed_v1.json",
            "builder": "build_edgeiq_current_early_speed_v1.py",
            "source_field": "earlySpeed",
            "units_scale": "0-100 current projection",
            "historical_current": "current projection",
            "as_of_safe": "YES by upstream audit",
            "coverage": "current runners",
            "production_research_status": "production current intelligence",
            "selected_rejected": "selected",
            "reason": "Approved current early-speed factor; not derived in React.",
        },
        {
            "source_file": "public/data/edgeiq_current_late_speed_v1.json",
            "builder": "build_edgeiq_current_late_speed_v1.py",
            "source_field": "lateSpeed",
            "units_scale": "0-100 current projection",
            "historical_current": "current projection",
            "as_of_safe": "YES by upstream audit",
            "coverage": "current runners",
            "production_research_status": "production current intelligence",
            "selected_rejected": "selected",
            "reason": "Approved current late-speed factor; not copied from late_power_index.",
        },
        {
            "source_file": "public/data/edgeiq_live_runner_board_governed_v1.csv",
            "builder": "governed live runner board",
            "source_field": "projected_rating_v5_2, fair_price fields",
            "units_scale": "current EPI and price fields",
            "historical_current": "current",
            "as_of_safe": "YES as current race input; not used as speed/momentum replacement",
            "coverage": "current runners",
            "production_research_status": "production current intelligence",
            "selected_rejected": "selected",
            "reason": "EPI is an allowed Suitability factor but never the whole suitability score.",
        },
        {
            "source_file": "public/data/live_speed_map_v3.csv",
            "builder": "build_live_speed_map_engine_v3.py",
            "source_field": "speed_map_bucket, map_style, confidence, tempo_fit",
            "units_scale": "categorical map evidence",
            "historical_current": "current shell with historical memory",
            "as_of_safe": "PARTIAL; only rows with runner evidence are used",
            "coverage": "current runners",
            "production_research_status": "production map evidence",
            "selected_rejected": "selected",
            "reason": "Used as evidence where not merely unsupported LOW/MIDFIELD default.",
        },
    ]


def evidence_coverage(count: int, available: int) -> float | None:
    if available <= 0:
        return None
    return round((count / available) * 100, 1)


def write_distribution(path_csv: Path, path_summary: Path, rows: list[dict[str, Any]]) -> None:
    write_csv(path_csv, rows, ["metric", "count", "coverage_pct", "minimum", "maximum", "mean", "median", "standard_deviation", "unique_values", "null_count", "zero_count", "flag"])
    lines = ["EDGEIQ BETA INTELLIGENCE V1 DISTRIBUTION SUMMARY"]
    for row in rows:
        lines.append(
            f"{row['metric']}: count={row['count']} coverage={row['coverage_pct']}% min={row['minimum']} max={row['maximum']} mean={row['mean']} median={row['median']} std={row['standard_deviation']} unique={row['unique_values']} nulls={row['null_count']} zeroes={row['zero_count']} flag={row['flag']}"
        )
    write_summary(path_summary, lines)
