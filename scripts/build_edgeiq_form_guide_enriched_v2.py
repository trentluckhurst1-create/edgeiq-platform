from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

csv.field_size_limit(1024 * 1024 * 128)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SRC = ROOT / "src"

BASE_FEED = DATA / "edgeiq_form_guide_enriched_v1.json"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
CURRENT_RUNNERS = DATA / "race_fields.csv"
WEATHER = DATA / "edgeiq_metropolitan_weather_v1.json"
WEATHER_RACE = DATA / "edgeiq_weather_engine_v1.csv"
SECTIONALS_TERMINAL = DATA / "edgeiq_form_sectional_terminal_feed_v1.csv"
SECTIONALS_PROFILE = DATA / "edgeiq_form_sectional_profile_feed_v1.csv"
SPEED_MASTER = DATA / "edgeiq_speed_master_v1.csv"
CURRENT_EARLY_SPEED = DATA / "edgeiq_current_early_speed_v1.json"
CURRENT_LATE_SPEED = DATA / "edgeiq_current_late_speed_v1.json"
CURRENT_RACE_SHAPE = DATA / "edgeiq_current_race_shape_v2.json"
CURRENT_SUITABILITY = DATA / "edgeiq_current_suitability_v1.json"
CURRENT_FORM_MOMENTUM = DATA / "edgeiq_current_form_momentum_v1.json"
RUN_RATINGS = DATA / "run_ratings_v1.csv"
LIVE_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
LIVE_BOARD_GOVERNED = DATA / "edgeiq_live_runner_board_governed_v1.csv"
CURRENT_EPI = DATA / "edgeiq_epi_current_rating_v1.json"
EPI_WORKSPACE_TERMINAL = DATA / "edgeiq_epi_workspace_terminal_feed_v1.csv"
FAIR_PRICE = DATA / "edgeiq_fair_price_v7_2.csv"
EPR_FAIR_PRICE = DATA / "edgeiq_fair_price_epr_v1.csv"
CURRENT_MARKET = DATA / "edgeiq_current_market_v1.csv"
SPEED_MAP = DATA / "live_speed_map_v3.csv"
RACE_SHAPE = DATA / "edgeiq_current_race_shape_recovery_candidate_v1_RECOVERY_CANDIDATE.csv"
DNA = DATA / "edgeiq_runner_dna_drawer_feed_v2.csv"
PROFILE_STATS = DATA / "edgeiq_runner_profile_stats_v1.csv"
RESULTS_MASTER = DATA / "edgeiq_results_master_v1.csv"
HISTORICAL_RESULTS_WAREHOUSE = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
RESULTS_HISTORY_CLEAN = DATA / "results_history_clean.csv"
RACE_STANDARDS = DATA / "race_standards.csv"
HISTORICAL_RACE_RATINGS = DATA / "historical_race_ratings.csv"
HISTORICAL_RUN_INTELLIGENCE = DATA / "edgeiq_historical_run_intelligence_fact_v1.csv"

OUT_JSON = DATA / "edgeiq_form_guide_enriched_v2.json"
OUT_CSV = DATA / "edgeiq_form_guide_enriched_v2.csv"
REGISTRY_CSV = DATA / "edgeiq_form_guide_v3_4_engine_registry.csv"
REGISTRY_JSON = DATA / "edgeiq_form_guide_v3_4_engine_registry.json"
REGISTRY_SUMMARY = DATA / "edgeiq_form_guide_v3_4_engine_registry_summary.txt"
JOIN_AUDIT = DATA / "edgeiq_form_guide_v3_4_engine_join_audit.csv"
COVERAGE_CSV = DATA / "edgeiq_form_guide_v3_4_coverage.csv"
COVERAGE_SUMMARY = DATA / "edgeiq_form_guide_v3_4_coverage_summary.txt"
HISTORICAL_EPI_RATEABLE_SUMMARY_V38 = DATA / "edgeiq_historical_epi_final_rateable_coverage_v38_summary.json"


def clean_text(value: Any) -> str:
    if value is None or isinstance(value, (dict, list, tuple)):
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return "" if text.lower() in {"", "-", "none", "null", "n/a", "na", "unknown"} else text


def normalise_track(value: Any) -> str:
    text = clean_text(value).upper()
    text = re.sub(r"\b(BET365|SPORTSBET|LADBROKES|TAB|THE)\b", " ", text)
    text = re.sub(r"\b(RACECOURSE|RACING|TRACK)\b", " ", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def normalise_runner(value: Any) -> str:
    text = clean_text(value).upper()
    text = re.sub(r"\s*\([A-Z]{2,3}\)\s*$", "", text)
    text = text.replace("'", "").replace("’", "").replace("&", "AND")
    return re.sub(r"[^A-Z0-9]+", "", text)


def normalise_date(value: Any) -> str:
    text = clean_text(value)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return ""


def race_no(value: Any) -> str:
    match = re.search(r"\d+", clean_text(value).upper().replace("R", ""))
    return match.group(0) if match else ""


def distance_m(value: Any) -> str:
    match = re.search(r"\d+", clean_text(value))
    return match.group(0) if match else ""


def num(value: Any) -> float | None:
    text = clean_text(value).replace("$", "").replace(",", "").replace("kg", "")
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    return parsed if abs(parsed) < 100000 else None


def pct(value: Any) -> float | None:
    parsed = num(value)
    return None if parsed is None else round(parsed, 1)


def source_value(value: Any, source: str | None, version: str | None, as_at: str | None = None) -> dict[str, Any]:
    return {
        "value": value,
        "source": source if value not in (None, "") else None,
        "version": version if value not in (None, "") else None,
        "asAt": as_at if value not in (None, "") else None,
    }


def projection_source_value(value: Any, source: str, version: str, row: dict[str, Any] | None, band_field: str) -> dict[str, Any]:
    payload = source_value(value, source, version, clean_text((row or {}).get("generatedAt")) or None)
    if row:
        payload["status"] = "POPULATED" if value not in (None, "") else (clean_text(row.get("blankReason")) or clean_text(row.get("missingReason")) or clean_text(row.get("joinMethod")) or "UNAVAILABLE")
        payload["missingReason"] = "" if value not in (None, "") else (clean_text(row.get("blankReason")) or clean_text(row.get("missingReason")) or clean_text(row.get("joinMethod")))
    if value not in (None, "") and row:
        payload["joinMethod"] = clean_text(row.get("joinMethod")) or None
        payload["evidenceRuns"] = int(num(row.get("evidenceRuns")) or 0)
        payload["evidenceCoverage"] = num(row.get("evidenceCoverage"))
        payload["sourceVersion"] = clean_text(row.get("sourceVersion")) or version
        payload["band"] = clean_text(row.get(band_field)) or None
        payload["publicReasons"] = row.get("publicReasons") if isinstance(row.get("publicReasons"), list) else []
    return payload


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def csv_headers(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        return csv.DictReader(handle).fieldnames or []


def csv_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        reader = csv.DictReader(handle)
        return sum(1 for _ in reader)


def selected_race_key(date: Any, meeting: Any, number: Any) -> str:
    return "|".join([normalise_date(date), normalise_track(meeting), race_no(number)])


def public_race_key(date: Any, meeting: Any, number: Any) -> str:
    return f"{normalise_date(date)}_{normalise_track(meeting)}_R{race_no(number)}"


def first_nested_value(source: Any, paths: list[list[Any]]) -> Any:
    for path in paths:
        current = source
        for part in path:
            if isinstance(part, int):
                if not isinstance(current, list) or len(current) <= part:
                    current = None
                    break
                current = current[part]
            elif isinstance(current, dict):
                current = current.get(part)
            else:
                current = None
                break
        if clean_text(current):
            return current
    return ""


def current_catalog_index() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    catalog = read_json(CATALOG)
    races: dict[str, dict[str, Any]] = {}
    runners: dict[str, dict[str, Any]] = {}
    runner_rows: list[dict[str, Any]] = []
    seen_runner_identities: set[tuple[str, str, str, str]] = set()

    for meeting in catalog.get("meetings", []):
        for race in meeting.get("races", []):
            key = selected_race_key(meeting.get("date"), meeting.get("meeting"), race.get("raceNumber"))
            races[key] = {"meeting": meeting, "race": race}
            for runner in race.get("runners", []):
                official = runner.get("official") or {}
                source = runner.get("source") or {}
                runner_name = clean_text(official.get("runner") or source.get("horseName"))
                runner_number = race_no(official.get("no") or source.get("raceEntryNumber"))
                identity = (normalise_date(meeting.get("date")), normalise_track(meeting.get("meeting")), race_no(race.get("raceNumber")), normalise_runner(runner_name))
                runner_key = "|".join([key, runner_number, identity[3]])
                runners[runner_key] = runner
                seen_runner_identities.add(identity)
                runner_rows.append(
                    {
                        "race_date": identity[0],
                        "meeting": clean_text(meeting.get("meeting")),
                        "race_number": identity[2],
                        "runner_number": runner_number,
                        "runner_name": runner_name,
                        "runner_norm": identity[3],
                        "horse_code": clean_text(first_nested_value(runner, [["source", "horseCode"], ["source", "horse_code"], ["historicalRuns", 0, "horseCode"], ["evidenceRuns", 0, "horseCode"]])),
                    }
                )

    if CURRENT_RUNNERS.exists():
        with CURRENT_RUNNERS.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
            for row in csv.DictReader(handle):
                race_date = normalise_date(row.get("race_date"))
                meeting = clean_text(row.get("display_track") or row.get("track"))
                race_number = race_no(row.get("race_no") or row.get("race_number"))
                runner_name = clean_text(row.get("runner") or row.get("horse"))
                runner_norm = normalise_runner(row.get("horse_canon") or row.get("horse_key") or runner_name)
                identity = (race_date, normalise_track(row.get("track") or meeting), race_number, runner_norm)
                if not all(identity):
                    continue
                if identity in seen_runner_identities:
                    for existing in runner_rows:
                        existing_identity = (
                            existing.get("race_date"),
                            normalise_track(existing.get("meeting")),
                            existing.get("race_number"),
                            existing.get("runner_norm"),
                        )
                        if existing_identity == identity and not clean_text(existing.get("horse_code")):
                            existing["horse_code"] = clean_text(row.get("horse_code"))
                            break
                    continue
                seen_runner_identities.add(identity)
                runner_rows.append(
                    {
                        "race_date": race_date,
                        "meeting": meeting,
                        "race_number": race_number,
                        "runner_number": race_no(row.get("runner_number") or row.get("horse_no") or row.get("saddlecloth")),
                        "runner_name": runner_name,
                        "runner_norm": runner_norm,
                        "horse_code": clean_text(row.get("horse_code")),
                    }
                )
    return races, runners, runner_rows


def load_weather() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    if WEATHER.exists():
        payload = read_json(WEATHER)
        for row in payload.get("records", []):
            records[normalise_track(row.get("meeting") or row.get("course") or row.get("meeting_key"))] = row
    return records


def weather_object(row: dict[str, Any] | None, race: dict[str, Any]) -> dict[str, Any] | None:
    if not row:
        return None
    source = clean_text(row.get("source_name") or row.get("provider") or "edgeiq_metropolitan_weather_v1.json")
    return {
        "raceDate": race.get("raceDate"),
        "meeting": race.get("meeting"),
        "observedAt": clean_text(row.get("source_observed_time") or row.get("source_observed_datetime")) or None,
        "forecastAt": None,
        "condition": clean_text(row.get("weather_comment")) or None,
        "temperatureC": num(row.get("temperature_c")),
        "apparentTemperatureC": None,
        "windSpeedKmh": num(row.get("wind_speed_kmh")),
        "windGustKmh": num(row.get("wind_gust_kmh")),
        "windDirection": clean_text(row.get("wind_direction")) or None,
        "rainfall24hMm": num(row.get("rainfall_24h_mm")),
        "rainfall7dMm": num(row.get("rainfall_7day_mm")),
        "irrigation24hMm": parse_irrigation(row.get("irrigation"), "24"),
        "irrigation7dMm": parse_irrigation(row.get("irrigation"), "7"),
        "trackCondition": clean_text(row.get("official_track_rating")) or None,
        "rail": clean_text(row.get("official_rail")) or None,
        "weatherSource": source,
        "weatherVersion": "edgeiq_metropolitan_weather_v1",
        "asAt": clean_text(row.get("fetched_at_utc")) or None,
    }


def parse_irrigation(value: Any, window: str) -> float | None:
    text = clean_text(value).lower()
    if not text:
        return None
    if "nil" in text or "0mm" in text:
        return 0.0
    if window == "24":
        match = re.search(r"24\D{0,12}([0-9.]+)\s*mm", text)
    else:
        match = re.search(r"7\D{0,12}([0-9.]+)\s*mm", text)
    return float(match.group(1)) if match else None


def record(starts: Any, wins: Any, seconds: Any, thirds: Any) -> dict[str, Any] | None:
    s = int(num(starts) or 0)
    w = int(num(wins) or 0)
    sec = int(num(seconds) or 0)
    th = int(num(thirds) or 0)
    places = w + sec + th
    return {
        "starts": s,
        "wins": w,
        "seconds": sec,
        "thirds": th,
        "places": places,
        "winPct": round((w / s) * 100, 1) if s else 0,
        "placePct": round((places / s) * 100, 1) if s else 0,
        "display": f"{s}:{w}-{sec}-{th}",
    }


def empty_record_counts() -> dict[str, int]:
    return {"starts": 0, "wins": 0, "seconds": 0, "thirds": 0}


def result_position(value: Any) -> int | None:
    parsed = num(value)
    if parsed is None:
        return None
    position = int(parsed)
    if position != parsed or position < 1 or position >= 100:
        return None
    return position


def increment_record_counts(counts: dict[str, int], position: int) -> None:
    counts["starts"] += 1
    if position == 1:
        counts["wins"] += 1
    if position == 2:
        counts["seconds"] += 1
    if position == 3:
        counts["thirds"] += 1


def load_current_context_records(
    contexts: dict[tuple[str, str, str, str], dict[str, str]],
) -> dict[tuple[str, str, str, str], dict[str, dict[str, Any]]]:
    records = {
        key: {
            "track": empty_record_counts(),
            "distance": empty_record_counts(),
        }
        for key in contexts
    }
    if RESULTS_MASTER.exists() and contexts:
        contexts_by_runner: dict[str, list[tuple[tuple[str, str, str, str], dict[str, str]]]] = defaultdict(list)
        for key, context in contexts.items():
            contexts_by_runner[key[3]].append((key, context))

        with RESULTS_MASTER.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
            for row in csv.DictReader(handle):
                runner_key = normalise_runner(row.get("normalized_runner") or row.get("runner"))
                runner_contexts = contexts_by_runner.get(runner_key)
                if not runner_contexts:
                    continue
                if clean_text(row.get("result_status")).upper() != "RESULTED":
                    continue
                row_date = normalise_date(row.get("race_date"))
                if not row_date:
                    continue
                position = result_position(row.get("position"))
                if position is None:
                    continue
                row_track = normalise_track(row.get("normalized_track") or row.get("track"))
                row_distance = distance_m(row.get("distance"))
                for identity, context in runner_contexts:
                    if row_date >= context["race_date"]:
                        continue
                    if row_track and row_track == context["track"]:
                        increment_record_counts(records[identity]["track"], position)
                    if row_distance and row_distance == context["distance"]:
                        increment_record_counts(records[identity]["distance"], position)

    return {
        key: {
            "track": record(**value["track"]),
            "distance": record(**value["distance"]),
        }
        for key, value in records.items()
    }


def load_profile_stats(current_names: set[str]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    if not PROFILE_STATS.exists():
        return rows
    with PROFILE_STATS.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        for row in csv.DictReader(handle):
            key = normalise_runner(row.get("normalized_runner") or row.get("runner"))
            if key in current_names:
                rows[key] = row
    return rows


def apply_profile_stats(
    runner: dict[str, Any],
    stats: dict[str, Any] | None,
    context_records: dict[str, dict[str, Any]] | None = None,
) -> None:
    if not stats:
        if context_records:
            runner["trackRecord"] = context_records.get("track")
            runner["distanceRecord"] = context_records.get("distance")
        return
    runner["careerRecord"] = record(stats.get("career_starts"), stats.get("career_wins"), stats.get("career_seconds"), stats.get("career_thirds"))
    runner["trackRecord"] = (context_records or {}).get("track") or record(stats.get("latest_track_starts"), stats.get("latest_track_wins"), stats.get("latest_track_seconds"), stats.get("latest_track_thirds"))
    runner["distanceRecord"] = (context_records or {}).get("distance") or record(stats.get("latest_distance_starts"), stats.get("latest_distance_wins"), stats.get("latest_distance_seconds"), stats.get("latest_distance_thirds"))
    runner["trackDistanceRecord"] = record(stats.get("latest_track_distance_starts"), stats.get("latest_track_distance_wins"), stats.get("latest_track_distance_seconds"), stats.get("latest_track_distance_thirds"))
    runner["conditionProfile"] = [
        {"label": label, **rec}
        for label, rec in [
            ("Firm", record(stats.get("firm_starts"), stats.get("firm_wins"), stats.get("firm_seconds"), stats.get("firm_thirds"))),
            ("Good", record(stats.get("good_starts"), stats.get("good_wins"), stats.get("good_seconds"), stats.get("good_thirds"))),
            ("Soft", record(stats.get("soft_starts"), stats.get("soft_wins"), stats.get("soft_seconds"), stats.get("soft_thirds"))),
            ("Heavy", record(stats.get("heavy_starts"), stats.get("heavy_wins"), stats.get("heavy_seconds"), stats.get("heavy_thirds"))),
            ("Synthetic", record(stats.get("synthetic_starts"), stats.get("synthetic_wins"), stats.get("synthetic_seconds"), stats.get("synthetic_thirds"))),
        ]
        if rec is not None
    ]
    class_rec = record(stats.get("latest_class_starts"), stats.get("latest_class_wins"), stats.get("latest_class_seconds"), stats.get("latest_class_thirds"))
    runner["classProfile"] = [{"label": "Class", **class_rec}] if class_rec else runner.get("classProfile", [])
    jockey_rec = record(stats.get("latest_jockey_starts"), stats.get("latest_jockey_wins"), stats.get("latest_jockey_seconds"), stats.get("latest_jockey_thirds"))
    if runner.get("jockeyProfile") and isinstance(runner["jockeyProfile"], dict):
        runner["jockeyProfile"]["jockeyWithHorse"] = jockey_rec
    prep_rows = []
    for label, prefix in [("1st Up", "first_up"), ("2nd Up", "second_up"), ("3rd Up", "third_up")]:
        rec = record(stats.get(f"{prefix}_starts"), stats.get(f"{prefix}_wins"), stats.get(f"{prefix}_seconds"), stats.get(f"{prefix}_thirds"))
        if rec:
            prep_rows.append({"label": label, **rec})
    runner["raceDayPattern"] = prep_rows
    runner["preparationProfile"] = prep_rows
    runner["profileStatsSource"] = "edgeiq_runner_profile_stats_v1.csv"


def run_identity(run: dict[str, Any], runner_norm: str) -> tuple[str, str, str, str, str]:
    return (
        runner_norm,
        normalise_date(run.get("date")),
        normalise_track(run.get("track")),
        race_no(run.get("raceNumber")),
        distance_m(run.get("distance")),
    )


def horse_code_key(value: Any) -> str:
    parsed = num(value)
    if parsed is not None:
        return str(int(parsed))
    return re.sub(r"[^0-9A-Z]+", "", clean_text(value).upper())


def source_value_from_fact(value: Any, source: str, version: str, status: str | None = None, missing_reason: str | None = None) -> dict[str, Any]:
    payload = source_value(value, source if value not in (None, "") else None, version if value not in (None, "") else None)
    payload["status"] = status or ("POPULATED" if value not in (None, "") else "UNAVAILABLE")
    payload["missingReason"] = "" if value not in (None, "") else (missing_reason or status or "UNAVAILABLE")
    return payload


def parse_json_map(value: Any) -> dict[str, Any]:
    text = clean_text(value)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def split_start_to_800(split_map: dict[str, Any]) -> float | None:
    start_to_800: list[float] = []
    for label, value in split_map.items():
        text = clean_text(label).upper().replace("FINISH", "FIN")
        match = re.match(r"^(\d{3,4})-(\d{3,4}|FIN|F)$", text)
        if not match:
            continue
        start = int(match.group(1))
        end_text = match.group(2)
        if end_text in {"FIN", "F"}:
            continue
        end = int(end_text)
        if start > 800 and end >= 800:
            parsed = num(value)
            if parsed is None:
                return None
            start_to_800.append(parsed)
    return round(sum(start_to_800), 4) if start_to_800 else None


def historical_fact_to_form_run(row: dict[str, Any]) -> dict[str, Any]:
    standard_lengths = parse_json_map(row.get("standard_lengths_by_segment_json"))
    position_map = parse_json_map(row.get("position_in_running_by_segment_json"))
    movement_map = parse_json_map(row.get("movement_by_segment_json"))
    epi_value = num(row.get("epi"))
    eri_value = num(row.get("eri"))
    early_value = num(row.get("early_speed"))
    late_value = num(row.get("late_speed"))
    speed_value = num(row.get("speed_rating"))
    return {
        "date": normalise_date(row.get("race_date")),
        "track": clean_text(row.get("track_display")) or clean_text(row.get("track")),
        "raceNumber": num(row.get("race_number")),
        "distance": num(row.get("distance")),
        "condition": clean_text(row.get("track_condition")),
        "conditionFamily": clean_text(row.get("track_condition")),
        "class": clean_text(row.get("race_class")),
        "position": num(row.get("finish_position")),
        "fieldSize": num(row.get("field_size")),
        "positionInRunning": " / ".join(f"{label}:{value}" for label, value in position_map.items()) if position_map else "",
        "positionInRunningBySegment": position_map,
        "movementBySegment": movement_map,
        "barrier": num(row.get("barrier")),
        "weight": clean_text(row.get("weight")),
        "jockey": clean_text(row.get("jockey")),
        "trainer": clean_text(row.get("trainer")),
        "margin": clean_text(row.get("margin")),
        "startingPrice": clean_text(row.get("starting_price")),
        "performanceRating": epi_value,
        "raceRating": source_value_from_fact(
            eri_value,
            "edgeiq_historical_run_intelligence_fact_v1.csv:eri",
            "HISTORICAL_RUN_INTELLIGENCE_FACT_V1",
            clean_text(row.get("eri_status")),
            clean_text(row.get("eri_status")),
        ),
        "historicalEpi": source_value_from_fact(
            epi_value,
            "edgeiq_historical_run_intelligence_fact_v1.csv:epi",
            "HISTORICAL_RUN_INTELLIGENCE_FACT_V1",
            clean_text(row.get("epi_status")),
            clean_text(row.get("epi_status")),
        ),
        "sectionalIndices": {
            "indexStartTo800": source_value_from_fact(split_start_to_800(standard_lengths), "edgeiq_historical_run_intelligence_fact_v1.csv:standard_lengths_by_segment_json", "HISTORICAL_RUN_INTELLIGENCE_FACT_V1"),
            "index800To600": source_value_from_fact(standard_lengths.get("800-600"), "edgeiq_historical_run_intelligence_fact_v1.csv:standard_lengths_by_segment_json", "HISTORICAL_RUN_INTELLIGENCE_FACT_V1"),
            "index600To400": source_value_from_fact(standard_lengths.get("600-400"), "edgeiq_historical_run_intelligence_fact_v1.csv:standard_lengths_by_segment_json", "HISTORICAL_RUN_INTELLIGENCE_FACT_V1"),
            "index400To200": source_value_from_fact(standard_lengths.get("400-200"), "edgeiq_historical_run_intelligence_fact_v1.csv:standard_lengths_by_segment_json", "HISTORICAL_RUN_INTELLIGENCE_FACT_V1"),
            "index200ToFinish": source_value_from_fact(standard_lengths.get("200-F"), "edgeiq_historical_run_intelligence_fact_v1.csv:standard_lengths_by_segment_json", "HISTORICAL_RUN_INTELLIGENCE_FACT_V1"),
            "finishLen": source_value_from_fact(None, None, None),
            "benchmarkMode": "HISTORICAL_RUN_INTELLIGENCE_FACT_V1" if standard_lengths else None,
            "signConvention": "As supplied by governed historical run intelligence fact.",
        } if standard_lengths else None,
        "benchmarkEvidence": source_value_from_fact(None, None, None),
        "historicalEarlySpeed": source_value_from_fact(early_value, "edgeiq_historical_run_intelligence_fact_v1.csv:early_speed", "HISTORICAL_RUN_INTELLIGENCE_FACT_V1", clean_text(row.get("speed_status")), clean_text(row.get("speed_status"))),
        "historicalLateSpeed": source_value_from_fact(late_value, "edgeiq_historical_run_intelligence_fact_v1.csv:late_speed", "HISTORICAL_RUN_INTELLIGENCE_FACT_V1", clean_text(row.get("speed_status")), clean_text(row.get("speed_status"))),
        "historicalSpeedRating": source_value_from_fact(speed_value, "edgeiq_historical_run_intelligence_fact_v1.csv:speed_rating", "HISTORICAL_RUN_INTELLIGENCE_FACT_V1", clean_text(row.get("speed_status")), clean_text(row.get("speed_status"))),
        "historicalSuitability": source_value_from_fact(None, None, None, "NOT_A_HISTORICAL_RUN_FIELD", "CURRENT_RACE_CONTEXT_ONLY"),
        "historicalFormMomentum": source_value_from_fact(None, None, None, "NOT_A_HISTORICAL_RUN_FIELD", "CURRENT_RACE_CONTEXT_ONLY"),
        "historicalRunStatus": clean_text(row.get("source_results_status")),
        "positionInRunningStatus": clean_text(row.get("position_in_running_status")),
        "canonicalRunKey": clean_text(row.get("canonical_run_key")),
        "canonicalRaceId": clean_text(row.get("canonical_race_id")),
        "canonicalRunnerId": clean_text(row.get("canonical_runner_id")),
        "canonicalHorseId": clean_text(row.get("canonical_horse_id")),
        "note": clean_text(row.get("source_results_status")),
    }


def result_history_to_form_run(row: dict[str, Any], source_name: str) -> dict[str, Any]:
    position = num(row.get("finish_position") or row.get("finish") or row.get("position") or row.get("finish_pos_num") or row.get("finishPosition"))
    epi_value = num(row.get("epi_post") or row.get("performanceRating"))
    horse_code = clean_text(row.get("horse_code")).replace(".0", "")
    return {
        "date": normalise_date(row.get("race_date") or row.get("meeting_date") or row.get("date_k")),
        "track": clean_text(row.get("track_display") or row.get("track") or row.get("venue_name")),
        "raceNumber": num(row.get("race_number") or row.get("race_no") or row.get("race_k")),
        "distance": num(row.get("distance")),
        "condition": clean_text(row.get("track_condition") or row.get("condition") or row.get("trackCondition")),
        "conditionFamily": clean_text(row.get("track_condition") or row.get("condition") or row.get("trackCondition")),
        "class": clean_text(row.get("race_class") or row.get("class") or row.get("raceClass")),
        "position": position,
        "fieldSize": num(row.get("field_size")),
        "positionInRunning": "",
        "positionInRunningBySegment": {},
        "movementBySegment": {},
        "barrier": num(row.get("barrier")),
        "weight": clean_text(row.get("weight")),
        "jockey": clean_text(row.get("jockey")),
        "trainer": clean_text(row.get("trainer")),
        "margin": clean_text(row.get("margin") or row.get("margin_l")),
        "startingPrice": clean_text(row.get("starting_price") or row.get("sp") or row.get("bb")),
        "performanceRating": epi_value,
        "raceRating": source_value_from_fact(None, None, None, "UNAVAILABLE", f"{source_name}:NO_ERI"),
        "historicalEpi": source_value_from_fact(epi_value, f"{source_name}:epi_post", "FALLBACK_DETAILED_FORM_V1") if epi_value is not None else source_value_from_fact(None, None, None, "UNAVAILABLE", f"{source_name}:NO_EPI"),
        "sectionalIndices": None,
        "benchmarkEvidence": source_value_from_fact(None, None, None),
        "historicalEarlySpeed": source_value_from_fact(None, None, None),
        "historicalLateSpeed": source_value_from_fact(None, None, None),
        "historicalSpeedRating": source_value_from_fact(None, None, None),
        "historicalSuitability": source_value_from_fact(None, None, None, "NOT_A_HISTORICAL_RUN_FIELD", "CURRENT_RACE_CONTEXT_ONLY"),
        "historicalFormMomentum": source_value_from_fact(None, None, None, "NOT_A_HISTORICAL_RUN_FIELD", "CURRENT_RACE_CONTEXT_ONLY"),
        "historicalRunStatus": "RESULTED_RUN",
        "positionInRunningStatus": "NO_SECTIONAL_CHECKPOINT_SOURCE",
        "canonicalRunKey": "",
        "canonicalRaceId": "",
        "canonicalRunnerId": clean_text(row.get("runner_id")),
        "canonicalHorseId": f"RCOM_HORSE_{horse_code}" if horse_code else "",
        "note": f"FALLBACK_DETAILED_FORM:{source_name}",
    }


def match_current_candidates(
    current_by_code: dict[str, list[dict[str, Any]]],
    current_by_name: dict[str, list[dict[str, Any]]],
    code: str,
    runner_key: str,
) -> list[dict[str, Any]]:
    if code and current_by_code.get(code):
        return current_by_code[code]
    if runner_key and current_by_name.get(runner_key):
        return current_by_name[runner_key]
    if runner_key and len(runner_key) >= 5:
        matches: list[dict[str, Any]] = []
        for current_key, candidates in current_by_name.items():
            if len(current_key) >= 5 and (current_key.startswith(runner_key) or runner_key.startswith(current_key)):
                matches.extend(candidates)
        if len({item["identity"] for item in matches}) == 1:
            return matches
    return []


def load_historical_result_fallback(current_rows: list[dict[str, Any]]) -> dict[tuple[str, str, str, str], list[dict[str, Any]]]:
    selected: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    current_by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
    current_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in current_rows:
        identity = (row["race_date"], normalise_track(row["meeting"]), row["race_number"], row["runner_norm"])
        payload = {**row, "identity": identity}
        code = horse_code_key(row.get("horse_code"))
        if code:
            current_by_code[code].append(payload)
        if row.get("runner_norm"):
            current_by_name[row["runner_norm"]].append(payload)

    source_specs = [
        (
            HISTORICAL_RESULTS_WAREHOUSE,
            "edgeiq_historical_results_warehouse_v2_graphql.csv",
            lambda row: horse_code_key(row.get("horse_code")),
            lambda row: normalise_runner(row.get("horse")),
            lambda row: clean_text(row.get("finish")) and clean_text(row.get("finish")).upper() != "109",
        ),
        (
            RESULTS_HISTORY_CLEAN,
            "results_history_clean.csv",
            lambda row: "",
            lambda row: normalise_runner(row.get("horse_key") or row.get("horse_k") or row.get("horse")),
            lambda row: clean_text(row.get("finish_pos_num") or row.get("finish_pos")),
        ),
        (
            RESULTS_MASTER,
            "edgeiq_results_master_v1.csv",
            lambda row: "",
            lambda row: normalise_runner(row.get("normalized_runner") or row.get("runner")),
            lambda row: clean_text(row.get("result_status")).upper() == "RESULTED" and clean_text(row.get("position")),
        ),
    ]
    seen_source_keys: set[tuple[tuple[str, str, str, str], tuple[str, str, str, str, str]]] = set()
    for path, source_name, code_fn, name_fn, eligible_fn in source_specs:
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
            for row in csv.DictReader(handle):
                if not eligible_fn(row):
                    continue
                race_date = normalise_date(row.get("race_date") or row.get("meeting_date") or row.get("date_k"))
                code = code_fn(row)
                runner_key = name_fn(row)
                candidates = match_current_candidates(current_by_code, current_by_name, code, runner_key)
                if not candidates:
                    continue
                for current in candidates:
                    if race_date and current.get("race_date") and race_date >= current["race_date"]:
                        continue
                    form_run = result_history_to_form_run(row, source_name)
                    run_key = run_identity(form_run, current["identity"][3])
                    source_key = (current["identity"], run_key)
                    if source_key in seen_source_keys:
                        continue
                    seen_source_keys.add(source_key)
                    selected[current["identity"]].append(form_run)

    for identity, runs in selected.items():
        runs.sort(key=lambda item: clean_text(item.get("date")), reverse=True)
    return dict(selected)


def merge_historical_runs(
    primary: dict[tuple[str, str, str, str], list[dict[str, Any]]],
    fallback: dict[tuple[str, str, str, str], list[dict[str, Any]]],
) -> dict[tuple[str, str, str, str], list[dict[str, Any]]]:
    for identity, fallback_runs in fallback.items():
        existing = primary.setdefault(identity, [])
        existing_keys = {run_identity(run, identity[3]) for run in existing}
        for run in fallback_runs:
            key = run_identity(run, identity[3])
            if key not in existing_keys:
                existing.append(run)
                existing_keys.add(key)
        existing.sort(key=lambda item: clean_text(item.get("date")), reverse=True)
    return primary


def load_historical_run_intelligence(current_rows: list[dict[str, Any]]) -> dict[tuple[str, str, str, str], list[dict[str, Any]]]:
    selected: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    if not HISTORICAL_RUN_INTELLIGENCE.exists():
        return {}

    current_by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
    current_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in current_rows:
        identity = (row["race_date"], normalise_track(row["meeting"]), row["race_number"], row["runner_norm"])
        selected.setdefault(identity, [])
        payload = {**row, "identity": identity}
        code = horse_code_key(row.get("horse_code"))
        if code:
            current_by_code[code].append(payload)
        if not code and row.get("runner_norm"):
            current_by_name[row["runner_norm"]].append(payload)

    with HISTORICAL_RUN_INTELLIGENCE.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        for fact in csv.DictReader(handle):
            finish = num(fact.get("finish_position"))
            if finish is None:
                continue
            fact_date = normalise_date(fact.get("race_date"))
            horse_code = horse_code_key(clean_text(fact.get("canonical_horse_id")).replace("RCOM_HORSE_", ""))
            horse_key = normalise_runner(fact.get("horse_key") or fact.get("horse"))
            candidates = current_by_code.get(horse_code) if horse_code else None
            if not candidates and horse_key:
                candidates = current_by_name.get(horse_key)
            if not candidates:
                continue
            for current in candidates:
                if fact_date and current.get("race_date") and fact_date >= current["race_date"]:
                    continue
                selected[current["identity"]].append(historical_fact_to_form_run(fact))

    for identity, runs in selected.items():
        runs.sort(key=lambda item: clean_text(item.get("date")), reverse=True)
        selected[identity] = runs
    return dict(selected)


def load_sectionals(run_keys: set[tuple[str, str, str, str, str]]) -> dict[tuple[str, str, str, str, str], dict[str, Any]]:
    selected: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    priority = {"CLASS_BENCHMARK": 0, "ALL_CLASSES_BENCHMARK": 1}
    if not SECTIONALS_PROFILE.exists():
        return selected
    target_keys = run_keys
    target_no_race = {(a, b, c, e) for a, b, c, _d, e in run_keys}
    with SECTIONALS_PROFILE.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        for row in csv.DictReader(handle):
            key = (
                normalise_runner(row.get("normalized_runner") or row.get("runner")),
                normalise_date(row.get("race_date")),
                normalise_track(row.get("track")),
                race_no(row.get("race_no")),
                distance_m(row.get("distance")),
            )
            no_race_key = (key[0], key[1], key[2], key[4])
            if key not in target_keys and no_race_key not in target_no_race:
                continue
            if key not in target_keys:
                matching = [candidate for candidate in target_keys if (candidate[0], candidate[1], candidate[2], candidate[4]) == no_race_key]
                if len(matching) != 1:
                    continue
                key = matching[0]
            current = selected.get(key)
            mode = clean_text(row.get("benchmark_mode")).upper()
            if current is None or priority.get(mode, 9) < priority.get(clean_text(current.get("benchmark_mode")).upper(), 9):
                selected[key] = row
    return selected


def load_speed_master(run_keys: set[tuple[str, str, str, str, str]]) -> dict[tuple[str, str, str, str, str], dict[str, Any]]:
    selected: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    if not SPEED_MASTER.exists():
        return selected
    with SPEED_MASTER.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        for row in csv.DictReader(handle):
            key = (
                normalise_runner(row.get("normalized_runner") or row.get("runner")),
                normalise_date(row.get("race_date")),
                normalise_track(row.get("track")),
                race_no(row.get("race_no")),
                distance_m(row.get("distance")),
            )
            if key in run_keys and key not in selected:
                selected[key] = row
    return selected


def load_run_ratings(run_keys: set[tuple[str, str, str, str, str]]) -> dict[tuple[str, str, str, str, str], dict[str, Any]]:
    if not RUN_RATINGS.exists():
        return {}
    index: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    with RUN_RATINGS.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        for row in csv.DictReader(handle):
            key = (
                normalise_runner(row.get("horse_key") or row.get("horse")),
                normalise_date(row.get("run_date")),
                distance_m(row.get("distance_m") or row.get("distance")),
            )
            index[key].append(row)
    selected: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for key in run_keys:
        simple = (key[0], key[1], key[4])
        rows = index.get(simple, [])
        if len(rows) == 1:
            selected[key] = rows[0]
    return selected



# EDGEIQ_DEEP_GOVERNED_HISTORICAL_EPI_FALLBACK_V15
# Full-depth fallback for historical runs outside or blocked by terminal start_1..start_10 transport.
# Terminal governed history retains priority. This helper uses the production EPI builder's governed lookup.
def load_deep_governed_historical_epi(base: dict[str, Any]) -> dict[int, dict[str, Any]]:
    import importlib.util
    import sys

    epi_builder_path = ROOT / "scripts" / "build_edgeiq_epi_workspace_terminal_feed_v1.py"
    spec = importlib.util.spec_from_file_location(
        "edgeiq_epi_builder_deep_form_v15",
        epi_builder_path,
    )
    if spec is None or spec.loader is None:
        return {}

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    required_keys: set[tuple[str, str, str, str]] = set()
    refs: list[tuple[dict[str, Any], dict[str, Any]]] = []

    for race in base.get("races", []):
        for runner in race.get("runners", []):
            horse_key = module.runner_match_key(runner.get("runnerName"))
            for historical_run in runner.get("fullForm", []):
                key = (
                    horse_key,
                    clean_text(historical_run.get("date")),
                    module.canonical_track(historical_run.get("track")),
                    module.number_text(historical_run.get("distance")),
                )
                if key[0] and key[1] and key[2]:
                    required_keys.add(key)
                refs.append((runner, historical_run))

    governed_index = module.historical_rating_index(required_keys)
    selected: dict[int, dict[str, Any]] = {}

    for runner, historical_run in refs:
        rating, source, version = module.historical_epi_for_run(
            runner,
            historical_run,
            governed_index,
        )
        if rating is None:
            continue

        selected[id(historical_run)] = {
            "epi": rating,
            "source": source,
            "version": version,
            "as_at": None,
        }

    print(f"FORM_GUIDE_V15_DEEP_GOVERNED_LOOKUPS={len(selected)}")
    return selected


# EDGEIQ_GOVERNED_HISTORICAL_EPI_ERI_BRIDGE_V2_1
def load_governed_historical_epi(
    path: Path,
    current_runner_keys: set[tuple[str, str, str, str]],
) -> dict[
    tuple[str, str, str, str],
    dict[tuple[str, str, str], dict[str, Any]],
]:
    selected: dict[
        tuple[str, str, str, str],
        dict[tuple[str, str, str], dict[str, Any]],
    ] = {}

    if not path.exists():
        return selected

    conflicts: set[
        tuple[
            tuple[str, str, str, str],
            tuple[str, str, str],
        ]
    ] = set()

    with path.open(
        newline="",
        encoding="utf-8-sig",
        errors="replace",
    ) as handle:
        for row in csv.DictReader(handle):

            current_key = (
                normalise_date(row.get("race_date")),
                normalise_track(row.get("track")),
                race_no(row.get("race_no")),
                normalise_runner(row.get("horse")),
            )

            if current_key not in current_runner_keys:
                continue

            history = selected.setdefault(
                current_key,
                {},
            )

            for slot in range(1, 11):

                tile_epi = num(
                    row.get(f"start_{slot}")
                )

                context_text = clean_text(
                    row.get(f"start_{slot}_context")
                )

                if tile_epi is None and not context_text:
                    continue

                if not context_text:
                    continue

                try:
                    context = json.loads(context_text)
                except json.JSONDecodeError:
                    continue

                context_epi = num(
                    context.get("EPI")
                )

                epi_value = (
                    context_epi
                    if context_epi is not None
                    else tile_epi
                )

                if epi_value is None:
                    continue

                historical_key = (
                    normalise_date(
                        context.get("DATE")
                    ),
                    normalise_track(
                        context.get("TRACK")
                    ),
                    distance_m(
                        context.get("DISTANCE")
                    ),
                )

                if not all(historical_key):
                    continue

                candidate = {
                    "epi": epi_value,
                    "eri": num(
                        context.get("ERI")
                    ),
                    "source": (
                        clean_text(
                            context.get("SOURCE")
                        )
                        or (
                            "edgeiq_epi_workspace_terminal_feed_v1.csv:"
                            f"start_{slot}"
                        )
                    ),
                    "version": (
                        "GOVERNED_EPI_WORKSPACE_TERMINAL_FEED_V1"
                    ),
                    "as_at": (
                        clean_text(
                            context.get(
                                "VERSION / TIMESTAMP"
                            )
                        )
                        or None
                    ),
                }

                existing = history.get(
                    historical_key
                )

                if existing is None:
                    history[
                        historical_key
                    ] = candidate

                elif (
                    existing.get("epi")
                    != candidate.get("epi")
                    or existing.get("eri")
                    != candidate.get("eri")
                ):
                    conflicts.add(
                        (
                            current_key,
                            historical_key,
                        )
                    )

    for current_key, historical_key in conflicts:

        history = selected.get(
            current_key
        )

        if history:
            history.pop(
                historical_key,
                None,
            )

    return selected


def split_values(row: dict[str, Any]) -> dict[str, float | None]:
    labels = [clean_text(item).upper().replace("FINISH", "FIN") for item in clean_text(row.get("split_labels")).split(";")]
    values = [clean_text(item) for item in clean_text(row.get("split_lengths")).split(";")]
    output = {"S-8": None, "800-600": None, "600-400": None, "400-200": None, "200-FIN": None}
    start_to_800: list[float] = []
    start_to_800_blocked = False
    for label, value in zip(labels, values):
        if label in output:
            output[label] = num(value)
        match = re.match(r"^(\d{3,4})-(\d{3,4}|FIN|F)$", label)
        if not match:
            continue
        start = int(match.group(1))
        end_text = match.group(2)
        if end_text in {"FIN", "F"}:
            continue
        end = int(end_text)
        if start > 800 and end >= 800:
            parsed = num(value)
            if parsed is None:
                start_to_800_blocked = True
                continue
            start_to_800.append(parsed)
    if start_to_800 and not start_to_800_blocked:
        output["S-8"] = round(sum(start_to_800), 4)
    return output


def load_exact_current(path: Path, current_runner_keys: set[tuple[str, str, str, str]], name_col: str, date_col: str, track_col: str, race_col: str) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    rows: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    if not path.exists():
        return rows
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        for row in csv.DictReader(handle):
            key = (
                normalise_date(row.get(date_col)),
                normalise_track(row.get(track_col)),
                race_no(row.get(race_col)),
                normalise_runner(row.get(name_col) or row.get("horse") or row.get("runner")),
            )
            if key in current_runner_keys:
                rows[key] = row
    return rows


def load_projection_json(path: Path, current_runner_keys: set[tuple[str, str, str, str]]) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    rows: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    if not path.exists():
        return rows
    payload = read_json(path)
    for row in payload.get("runners", []):
        key = (
            normalise_date(row.get("raceDate")),
            normalise_track(row.get("meeting")),
            race_no(row.get("raceNumber")),
            normalise_runner(row.get("normalizedRunner") or row.get("normalizedRunnerName") or row.get("runnerName")),
        )
        if key in current_runner_keys:
            rows.setdefault(key, row)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_registry(current_runner_keys: set[tuple[str, str, str, str]]) -> list[dict[str, Any]]:
    candidates = [
        ("Weather", "edgeiq_metropolitan_weather_v1", WEATHER, ROOT / "scripts" / "build_edgeiq_metropolitan_weather_v1.py", WEATHER, SRC / "edgeiq-os" / "services" / "weather" / "EdgeiqWeatherService.ts", True, "race_date+meeting", "meeting"),
        ("Weather", "edgeiq_weather_engine_v1", WEATHER_RACE, None, WEATHER_RACE, SRC / "edgeiq-os" / "services" / "adapters" / "WeatherAdapter.ts", False, "race_date+track+race_no", ""),
        ("Sectionals", "edgeiq_form_sectional_profile_feed_v1", SECTIONALS_PROFILE, None, SECTIONALS_PROFILE, None, True, "historical runner+date+track+race_no+distance", "normalized_runner"),
        ("Sectionals", "edgeiq_form_sectional_terminal_feed_v1", SECTIONALS_TERMINAL, ROOT / "scripts" / "build_edgeiq_form_sectional_terminal_feed_v1.py", SECTIONALS_TERMINAL, None, False, "historical runner+date+track+race_no+distance", "normalized_runner"),
        ("Benchmark", "edgeiq_standardised_sectionals_v1/race_standards", DATA / "edgeiq_standardised_sectionals_v1.csv", None, DATA / "edgeiq_standardised_sectionals_v1.csv", None, True, "historical runner+date+track+race_no+distance", "runner"),
        ("Rating", "run_ratings_v1", RUN_RATINGS, None, RUN_RATINGS, SRC / "edgeiq-os" / "services" / "RunRatingService.ts", True, "historical runner+date+distance unique", "horse_key"),
        ("EPI", "edgeiq_live_runner_board_governed_v1", LIVE_BOARD_GOVERNED, None, LIVE_BOARD_GOVERNED, None, False, "current race_date+track+race_no+runner", "horse"),
        ("EDGEiQ Price", "edgeiq_fair_price_epr_v1", EPR_FAIR_PRICE, ROOT / "scripts" / "build_edgeiq_fair_price_epr_v1.py", EPR_FAIR_PRICE, None, True, "current race_date+track+race_no+runner from governed EPR Market V1", "horse"),
        ("EDGEiQ Price fallback", "edgeiq_fair_price_v7_2", FAIR_PRICE, None, FAIR_PRICE, None, False, "legacy fallback only when no exact EPR Market V1 price exists", "horse"),
        ("Early Speed", "edgeiq_current_early_speed_v1", CURRENT_EARLY_SPEED, ROOT / "scripts" / "build_edgeiq_current_early_speed_v1.py", CURRENT_EARLY_SPEED, SRC / "edgeiq-os" / "services" / "SpeedProfileService.ts", True, "current race_date+track+race_no+runner generated from as-of historical early_raw", "normalizedRunner"),
        ("Race Shape", "edgeiq_current_race_shape_v2", CURRENT_RACE_SHAPE, ROOT / "scripts" / "build_edgeiq_current_race_shape_v2.py", CURRENT_RACE_SHAPE, SRC / "edgeiq-os" / "race" / "components" / "MapWorkspace.tsx", True, "current race_date+track+race_no+runner generated from supported map evidence and current Early Speed V1", "normalizedRunner"),
        ("Suitability", "edgeiq_current_suitability_v1", CURRENT_SUITABILITY, ROOT / "scripts" / "build_edgeiq_current_suitability_v1.py", CURRENT_SUITABILITY, None, True, "current race_date+track+race_no+runner generated from as-of setup evidence", "normalizedRunner"),
        ("Late Speed", "edgeiq_current_late_speed_v1", CURRENT_LATE_SPEED, ROOT / "scripts" / "build_edgeiq_current_late_speed_v1.py", CURRENT_LATE_SPEED, None, True, "current race_date+track+race_no+runner generated from as-of benchmarked late sectionals / late_raw", "normalizedRunner"),
        ("Form Momentum", "edgeiq_current_form_momentum_v1", CURRENT_FORM_MOMENTUM, ROOT / "scripts" / "build_edgeiq_current_form_momentum_v1.py", CURRENT_FORM_MOMENTUM, None, True, "current race_date+track+race_no+runner generated from as-of trend evidence", "normalizedRunner"),
        ("Preparation Profile", "edgeiq_runner_profile_stats_v1", PROFILE_STATS, ROOT / "scripts" / "build_edgeiq_runner_profile_stats_v1.py", PROFILE_STATS, None, True, "current runner name", "normalized_runner"),
    ]
    rows: list[dict[str, Any]] = []
    for engine, version, source, builder, output, consumer, selected, race_key, runner_key in candidates:
        path = source if source.is_absolute() else ROOT / source
        headers = csv_headers(path) if path.suffix.lower() == ".csv" and path.exists() else []
        if path.suffix.lower() == ".json" and path.exists():
            try:
                payload = read_json(path)
                headers = list(payload.keys())
                row_count: int | str = len(payload.get("records", [])) if isinstance(payload, dict) else len(payload)
            except Exception:
                row_count = ""
        else:
            row_count = csv_count(path) if path.exists() and path.suffix.lower() == ".csv" and path.stat().st_size < 60_000_000 else ("LARGE" if path.exists() else 0)
        rows.append(
            {
                "engine_name": engine,
                "engine_version": version,
                "source_file": str(path) if path.exists() else "",
                "builder_file": str(builder) if builder and builder.exists() else "",
                "generated_output": str(output) if output and output.exists() else "",
                "consumer_file": str(consumer) if consumer and consumer.exists() else "",
                "production_status": "SELECTED" if selected else "DISCOVERED_NOT_SELECTED_FOR_CURRENT_JOIN",
                "research_status": "PRODUCTION_OR_APPROVED_FEED" if selected else "DOCUMENTED_SOURCE_OR_PRIOR_DATE",
                "input_fields": "",
                "output_fields": "|".join(headers[:80]),
                "race_key": race_key,
                "runner_key": runner_key,
                "date_coverage": "",
                "meeting_coverage": "",
                "row_count": row_count,
                "current_three_day_coverage": "",
                "scale_or_units": units_for(engine),
                "safe_for_customer_display": "YES" if selected else "NO_CURRENT_DATE_JOIN" if engine not in {"Form Momentum"} else "NO_APPROVED_ENGINE_FOUND",
                "selected_or_rejected": "selected" if selected else "rejected",
                "reason": reason_for(engine, selected),
            }
        )
    return rows


def units_for(engine: str) -> str:
    return {
        "Weather": "official weather and track observations",
        "Sectionals": "EDGEiQ Standardised Lengths versus benchmark",
        "Benchmark": "standardised lengths/race benchmark evidence",
        "Rating": "run rating points",
        "EPI": "current projection points where exact current date exists",
        "EDGEiQ Price": "assessed price decimal odds",
        "Early Speed": "speed-map/early-rating evidence",
        "Race Shape": "approved current runner-specific Race Shape V2",
        "Suitability": "approved current-race runner-specific Suitability V1",
        "Late Speed": "approved current late-sectional projection",
        "Form Momentum": "approved current as-of trend score",
        "Preparation Profile": "starts:wins-seconds-thirds by prep stage",
    }.get(engine, "")


def reason_for(engine: str, selected: bool) -> str:
    if selected:
        return "Selected because lineage and join keys are documented and matching coverage exists for the V3.4 feed."
    if engine == "Form Momentum":
        return "No approved current Form Momentum composite was located; inputs are documented but values are not fabricated."
    return "Valid project source exists but does not have exact current three-day race coverage, or it is retained as source evidence only."


def build() -> dict[str, Any]:
    base = read_json(BASE_FEED)
    race_catalog, _runner_catalog, current_rows = current_catalog_index()
    current_names = {row["runner_norm"] for row in current_rows}
    current_runner_keys = {(row["race_date"], normalise_track(row["meeting"]), row["race_number"], row["runner_norm"]) for row in current_rows}
    historical_run_intelligence = load_historical_run_intelligence(current_rows)
    historical_run_intelligence = merge_historical_runs(
        historical_run_intelligence,
        load_historical_result_fallback(current_rows),
    )
    weather = load_weather()
    profile_stats = load_profile_stats(current_names)
    current_contexts: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for race in base.get("races", []):
        race_date = normalise_date(race.get("raceDate"))
        track = normalise_track(race.get("meeting"))
        number = race_no(race.get("raceNumber"))
        distance = distance_m(race.get("distance"))
        for runner in race.get("runners", []):
            runner_norm = normalise_runner(runner.get("normalisedRunnerName") or runner.get("runnerName"))
            identity = (race_date, track, number, runner_norm)
            if all(identity) and distance:
                current_contexts[identity] = {
                    "race_date": race_date,
                    "track": track,
                    "distance": distance,
                }
    current_context_records = load_current_context_records(current_contexts)

    run_keys: set[tuple[str, str, str, str, str]] = set()
    for race in base.get("races", []):
        for runner in race.get("runners", []):
            runner_norm = normalise_runner(runner.get("normalisedRunnerName") or runner.get("runnerName"))
            race_identity = (
                normalise_date(race.get("raceDate")),
                normalise_track(race.get("meeting")),
                race_no(race.get("raceNumber")),
                runner_norm,
            )
            governed_full_form = historical_run_intelligence.get(race_identity)
            if governed_full_form is not None:
                runner["fullForm"] = governed_full_form
                runner["historySource"] = "edgeiq_historical_run_intelligence_fact_v1.csv"
                runner["lastStart"] = governed_full_form[0] if governed_full_form else None
                runner["lastFive"] = [clean_text(run.get("position")) for run in governed_full_form[:5] if clean_text(run.get("position"))]
            for run in runner.get("fullForm", []):
                key = run_identity(run, runner_norm)
                if key[0] and key[1] and key[2] and key[4]:
                    run_keys.add(key)

    sectionals = load_sectionals(run_keys)
    speed = load_speed_master(run_keys)
    run_ratings = load_run_ratings(run_keys)
    current_live = load_exact_current(LIVE_BOARD_GOVERNED, current_runner_keys, "horse", "race_date", "track", "race_no")
    current_epr_price = load_exact_current(EPR_FAIR_PRICE, current_runner_keys, "horse", "race_date", "track", "race_no")
    current_price = load_exact_current(FAIR_PRICE, current_runner_keys, "horse", "race_date", "track", "race_no")
    current_market = load_exact_current(CURRENT_MARKET, current_runner_keys, "horse_name", "race_date", "canonical_track", "race_number")
    current_epi = load_projection_json(CURRENT_EPI, current_runner_keys)
    governed_history = load_governed_historical_epi(
        EPI_WORKSPACE_TERMINAL,
        current_runner_keys,
    )
    deep_governed_history = load_deep_governed_historical_epi(base)
    current_early_speed = load_projection_json(CURRENT_EARLY_SPEED, current_runner_keys)
    current_late_speed = load_projection_json(CURRENT_LATE_SPEED, current_runner_keys)
    current_race_shape = load_projection_json(CURRENT_RACE_SHAPE, current_runner_keys)
    current_suitability = load_projection_json(CURRENT_SUITABILITY, current_runner_keys)
    current_form_momentum = load_projection_json(CURRENT_FORM_MOMENTUM, current_runner_keys)

    registry_rows = build_registry(current_runner_keys)
    join_rows: list[dict[str, Any]] = []
    csv_rows: list[dict[str, Any]] = []
    race_coverage_rows: list[dict[str, Any]] = []
    totals = Counter()
    run_totals = Counter()

    for race in base.get("races", []):
        race_key = race.get("raceKey") or selected_race_key(race.get("raceDate"), race.get("meeting"), race.get("raceNumber"))
        catalog_entry = race_catalog.get(race_key, {})
        race_source = (catalog_entry.get("race") or {}).get("source") or {}
        weather_row = weather.get(normalise_track(race.get("meeting")))
        race_weather = weather_object(weather_row, race)
        race["weather"] = race_weather
        race["tempo"] = None
        race["pressure"] = None
        race["benchmarkContext"] = {
            "source": "edgeiq_form_sectional_profile_feed_v1.csv",
            "version": "edgeiq_standardised_lengths_v1",
            "signConvention": "Values are lengths versus benchmark as supplied by std_*_len/split_lengths. Positive/negative meaning is preserved from source; no JSX conversion is performed.",
        }
        race["trackCondition"] = clean_text(race_source.get("track_condition")) or race.get("trackCondition")
        race["rail"] = clean_text(race_source.get("rail_position")) or race.get("rail")
        metrics = Counter()

        for runner in race.get("runners", []):
            runner_norm = normalise_runner(runner.get("normalisedRunnerName") or runner.get("runnerName"))
            race_identity = (normalise_date(race.get("raceDate")), normalise_track(race.get("meeting")), race_no(race.get("raceNumber")), runner_norm)
            stats = profile_stats.get(runner_norm)
            apply_profile_stats(runner, stats, current_context_records.get(race_identity))

            live_row = current_live.get(race_identity)
            epr_price_row = current_epr_price.get(race_identity)
            price_row = epr_price_row or current_price.get(race_identity)
            market_row = current_market.get(race_identity)
            epi_row = current_epi.get(race_identity)
            early_row = current_early_speed.get(race_identity)
            late_row = current_late_speed.get(race_identity)
            race_shape_row = current_race_shape.get(race_identity)
            suitability_row = current_suitability.get(race_identity)
            momentum_row = current_form_momentum.get(race_identity)

            rating_value = num(live_row.get("total_rating_points") if live_row else None)
            epi_value = num((epi_row or {}).get("value"))
            # V1.1 guard retained: do not promote stale live-board projected_spd.
            # Only the approved CURRENT_EARLY_SPEED_V1 projection feed may populate
            # today's Early Speed.
            early_speed_value = num((early_row or {}).get("earlySpeed"))
            if epr_price_row:
                edgeiq_price_value = num((epr_price_row or {}).get("edgeiq_price_epr_v1"))
                edgeiq_price_source = "edgeiq_fair_price_epr_v1.csv:edgeiq_price_epr_v1"
                edgeiq_price_version = clean_text((epr_price_row or {}).get("edgeiq_price_engine")) or "EPR_MARKET_V1"
                edgeiq_price_as_at = clean_text((epr_price_row or {}).get("built_at_epr_market_v1")) or None
                edgeiq_price_status = "POPULATED" if edgeiq_price_value is not None else (clean_text((epr_price_row or {}).get("epr_market_no_history_policy")) or clean_text((epr_price_row or {}).get("missingReason")) or "NO_CURRENT_EPR_NO_PRICE")
            else:
                edgeiq_price_value = num((price_row or {}).get("display_fair_price") or (price_row or {}).get("ui_fair_price") or (price_row or {}).get("fair_price") or (price_row or {}).get("fair_price_v7_2") or (live_row or {}).get("display_fair_price_governed") or (live_row or {}).get("fair_price_display") or (live_row or {}).get("fair_price"))
                edgeiq_price_source = "edgeiq_fair_price_v7_2.csv:display_fair_price/ui_fair_price OR edgeiq_live_runner_board_governed_v1.csv:fair_price"
                edgeiq_price_version = "v7_2_or_governed_v3"
                edgeiq_price_as_at = None
                edgeiq_price_status = "POPULATED" if edgeiq_price_value is not None else "NO_CURRENT_EPR_NO_PRICE"
            suitability_value = num((suitability_row or {}).get("suitability"))
            race_shape_value = clean_text((race_shape_row or {}).get("raceShape"))
            # V1.1 guard retained: late_power_index stays out of the current column.
            # Only the approved CURRENT_LATE_SPEED_V1 projection feed may populate
            # today's Late Speed.
            late_speed_value = num((late_row or {}).get("lateSpeed"))
            form_momentum_value = num((momentum_row or {}).get("formMomentum"))

            runner["rating"] = source_value(rating_value, "edgeiq_live_runner_board_governed_v1.csv:total_rating_points", "live_runner_board_v1", None)
            runner["epi"] = {
                "value": epi_value,
                "display": clean_text((epi_row or {}).get("display")) or (str(round(epi_value, 1)) if epi_value is not None else ""),
                "source": clean_text((epi_row or {}).get("source")) or ("edgeiq_epi_current_rating_v1.json:value" if epi_value is not None else None),
                "version": clean_text((epi_row or {}).get("version")) or ("v5_2" if epi_value is not None else None),
                "asAt": clean_text((epi_row or {}).get("asAt")) or None,
                "status": clean_text((epi_row or {}).get("status")) or ("CURRENT" if epi_value is not None else "MISSING"),
                "rankInRace": int(num((epi_row or {}).get("rankInRace")) or 0) or None,
                "activeFieldSize": int(num((epi_row or {}).get("activeFieldSize")) or 0) or None,
                "fieldHigh": num((epi_row or {}).get("fieldHigh")),
                "fieldAverage": num((epi_row or {}).get("fieldAverage")),
                "differenceFromFieldAverage": num((epi_row or {}).get("differenceFromFieldAverage")),
                "recentChange": num((epi_row or {}).get("recentChange")),
                "trend": clean_text((epi_row or {}).get("trend")) or None,
                "missingReason": clean_text((epi_row or {}).get("missingReason")) or None,
            }
            runner["earlySpeed"] = projection_source_value(early_speed_value, "edgeiq_current_early_speed_v1.json:earlySpeed", "CURRENT_EARLY_SPEED_V1", early_row, "earlySpeedBand")
            runner["edgeiqPrice"] = source_value(edgeiq_price_value, edgeiq_price_source if edgeiq_price_value is not None else None, edgeiq_price_version if edgeiq_price_value is not None else None, edgeiq_price_as_at)
            runner["edgeiqPrice"]["status"] = edgeiq_price_status
            runner["edgeiqPrice"]["missingReason"] = "" if edgeiq_price_value is not None else edgeiq_price_status
            runner["suitability"] = projection_source_value(suitability_value, "edgeiq_current_suitability_v1.json:suitability", "CURRENT_SUITABILITY_V1", suitability_row, "suitabilityBand")
            runner["raceShape"] = projection_source_value(race_shape_value or None, "edgeiq_current_race_shape_v2.json:raceShape", "CURRENT_RACE_SHAPE_V2", race_shape_row, "raceShape")
            runner["lateSpeed"] = projection_source_value(late_speed_value, "edgeiq_current_late_speed_v1.json:lateSpeed", "CURRENT_LATE_SPEED_V1", late_row, "lateSpeedBand")
            runner["formMomentum"] = projection_source_value(form_momentum_value, "edgeiq_current_form_momentum_v1.json:formMomentum", "CURRENT_FORM_MOMENTUM_V1", momentum_row, "formMomentumBand")
            market_price_value = num((market_row or {}).get("fixed_win") or runner.get("marketPrice"))
            market_price_source = "edgeiq_current_market_v1.csv:fixed_win" if (market_row or {}).get("fixed_win") else runner.get("marketSource")
            market_price_version = "LADBROKES_CANONICAL_MARKET_V1" if (market_row or {}).get("fixed_win") else "edgeiq_three_day_product_catalog_v1"
            market_price_as_at = clean_text((market_row or {}).get("edgeiq_observed_at")) or runner.get("marketAsAt")
            runner["marketPrice"] = source_value(market_price_value, market_price_source, market_price_version, market_price_as_at)
            runner["marketSource"] = runner.get("marketPrice", {}).get("source") if isinstance(runner.get("marketPrice"), dict) else runner.get("marketSource")

            sectional_matches = 0
            benchmark_matches = 0
            run_rating_matches = 0
            speed_matches = 0
            current_runner_key = (
                normalise_date(race.get("raceDate")),
                normalise_track(race.get("meeting")),
                race_no(race.get("raceNumber")),
                runner_norm,
            )
            governed_runner_history = governed_history.get(
                current_runner_key,
                {},
            )
            for run in runner.get("fullForm", []):
                key = run_identity(run, runner_norm)
                sec = sectionals.get(key)
                spd = speed.get(key)
                rating = run_ratings.get(key)
                governed_hist = governed_runner_history.get(
                    (key[1], key[2], key[4])
                )
                existing_historical_epi = run.get("historicalEpi") if isinstance(run.get("historicalEpi"), dict) else {}
                existing_race_rating = run.get("raceRating") if isinstance(run.get("raceRating"), dict) else {}
                if sec:
                    splits = split_values(sec)
                    run["sectionalIndices"] = {
                        "indexStartTo800": source_value(splits["S-8"], "edgeiq_form_sectional_profile_feed_v1.csv:split_lengths", "standardised_sectionals_v1"),
                        "index800To600": source_value(splits["800-600"], "edgeiq_form_sectional_profile_feed_v1.csv:split_lengths", "standardised_sectionals_v1"),
                        "index600To400": source_value(splits["600-400"], "edgeiq_form_sectional_profile_feed_v1.csv:split_lengths", "standardised_sectionals_v1"),
                        "index400To200": source_value(splits["400-200"], "edgeiq_form_sectional_profile_feed_v1.csv:split_lengths", "standardised_sectionals_v1"),
                        "index200ToFinish": source_value(splits["200-FIN"], "edgeiq_form_sectional_profile_feed_v1.csv:split_lengths", "standardised_sectionals_v1"),
                        "finishLen": source_value(num(sec.get("finish_len")), "edgeiq_form_sectional_profile_feed_v1.csv:finish_len", "standardised_sectionals_v1"),
                        "benchmarkMode": clean_text(sec.get("benchmark_mode")) or None,
                        "signConvention": "As supplied by standardised sectionals feed: lengths versus benchmark.",
                    }
                    sec_epi = num(sec.get("epi_post"))
                    if sec_epi is not None or not isinstance(existing_historical_epi, dict):
                        run["historicalEpi"] = source_value(sec_epi, "edgeiq_form_sectional_profile_feed_v1.csv:epi_post", "standardised_sectionals_v1")
                    run["benchmarkEvidence"] = source_value(num(sec.get("finish_len")), "edgeiq_form_sectional_profile_feed_v1.csv:finish_len", "standardised_sectionals_v1")
                    for segment_label, counter_key in [
                        ("S-8", "sectional_s_8"),
                        ("800-600", "sectional_800_600"),
                        ("600-400", "sectional_600_400"),
                        ("400-200", "sectional_400_200"),
                        ("200-FIN", "sectional_200_f"),
                    ]:
                        if splits.get(segment_label) is not None:
                            run_totals[counter_key] += 1
                    sectional_matches += 1
                    benchmark_matches += 1
                else:
                    if run.get("sectionalIndices") is None:
                        run["sectionalIndices"] = None
                    if not isinstance(run.get("historicalEpi"), dict):
                        run["historicalEpi"] = source_value(None, None, None)
                    if not isinstance(run.get("benchmarkEvidence"), dict):
                        run["benchmarkEvidence"] = source_value(None, None, None)
                deep_governed_hist = deep_governed_history.get(id(run))
                if governed_hist:
                    run["historicalEpi"] = source_value(
                        governed_hist.get("epi"),
                        governed_hist.get("source"),
                        governed_hist.get("version"),
                        governed_hist.get("as_at"),
                    )
                elif deep_governed_hist:
                    run["historicalEpi"] = source_value(
                        deep_governed_hist.get("epi"),
                        deep_governed_hist.get("source"),
                        deep_governed_hist.get("version"),
                        deep_governed_hist.get("as_at"),
                    )
                if run["historicalEpi"].get("value") is not None:
                    run_totals["historical_epi_matches"] += 1
                if rating:
                    run["raceRating"] = source_value(num(rating.get("run_rating")), "run_ratings_v1.csv:run_rating", "run_ratings_v1")
                    run_rating_matches += 1
                else:
                    if not isinstance(existing_race_rating, dict):
                        run["raceRating"] = source_value(run.get("performanceRating"), "edgeiq_historical_results_warehouse_v2_graphql.csv:performanceRating" if run.get("performanceRating") else None, "warehouse_v2")
                if (
                    governed_hist
                    and governed_hist.get("eri") is not None
                ):
                    run["raceRating"] = source_value(
                        governed_hist.get("eri"),
                        governed_hist.get("source"),
                        governed_hist.get("version"),
                        governed_hist.get("as_at"),
                    )
                if spd:
                    run["historicalEarlySpeed"] = source_value(num(spd.get("early_rating") or spd.get("early_raw")), "edgeiq_speed_master_v1.csv:early_rating/early_raw", "speed_master_v1")
                    run["historicalLateSpeed"] = source_value(num(spd.get("late_rating") or spd.get("late_raw")), "edgeiq_speed_master_v1.csv:late_rating/late_raw", "speed_master_v1")
                    run["historicalSpeedRating"] = source_value(num(spd.get("speed_rating") or spd.get("speed_rating_raw")), "edgeiq_speed_master_v1.csv:speed_rating/speed_rating_raw", "speed_master_v1")
                    speed_matches += 1
                else:
                    if not isinstance(run.get("historicalEarlySpeed"), dict):
                        run["historicalEarlySpeed"] = source_value(None, None, None)
                    if not isinstance(run.get("historicalLateSpeed"), dict):
                        run["historicalLateSpeed"] = source_value(None, None, None)
                    if not isinstance(run.get("historicalSpeedRating"), dict):
                        run["historicalSpeedRating"] = source_value(None, None, None)
                if not isinstance(run.get("historicalSuitability"), dict):
                    run["historicalSuitability"] = source_value(None, None, None)
                if not isinstance(run.get("historicalFormMomentum"), dict):
                    run["historicalFormMomentum"] = source_value(None, None, None)

            metrics["runners"] += 1
            metrics["weather"] += 1 if race_weather else 0
            metrics["rating"] += 1 if rating_value is not None else 0
            metrics["epi"] += 1 if epi_value is not None else 0
            metrics["edgeiq_price"] += 1 if edgeiq_price_value is not None else 0
            metrics["early_speed"] += 1 if early_speed_value is not None else 0
            metrics["suitability"] += 1 if suitability_value is not None else 0
            metrics["race_shape"] += 1 if race_shape_value else 0
            metrics["late_speed"] += 1 if late_speed_value is not None else 0
            metrics["form_momentum"] += 1 if form_momentum_value is not None else 0
            metrics["preparation"] += 1 if runner.get("preparationProfile") else 0
            metrics["recent_form"] += 1 if runner.get("fullForm") else 0
            metrics["career_profile"] += 1 if runner.get("careerRecord") else 0
            run_totals["runs"] += len(runner.get("fullForm", []))
            run_totals["sectional_matches"] += sectional_matches
            run_totals["benchmark_matches"] += benchmark_matches
            run_totals["run_rating_matches"] += run_rating_matches
            run_totals["historical_speed_matches"] += speed_matches
            join_rows.append(
                {
                    "race_date": race.get("raceDate"),
                    "meeting": race.get("meeting"),
                    "race_number": race.get("raceNumber"),
                    "runner_number": runner.get("runnerNumber"),
                    "runner_id": runner.get("runnerId") or "",
                    "runner_name": runner.get("runnerName"),
                    "weather_match": "YES" if race_weather else "NO",
                    "rating_match": "YES" if rating_value is not None else "NO",
                    "epi_match": "YES" if epi_value is not None else "NO",
                    "price_match": "YES" if edgeiq_price_value is not None else "NO",
                    "early_speed_match": "YES" if early_speed_value is not None else "NO",
                    "race_shape_match": "YES" if race_shape_value else "NO",
                    "suitability_match": "YES" if suitability_value is not None else "NO",
                    "late_speed_match": "YES" if late_speed_value is not None else "NO",
                    "momentum_match": "YES" if form_momentum_value is not None else "NO",
                    "profile_match": "YES" if stats else "NO",
                    "preparation_match": "YES" if runner.get("preparationProfile") else "NO",
                    "recent_form_match": "YES" if runner.get("fullForm") else "NO",
                    "sectional_run_matches": sectional_matches,
                    "benchmark_run_matches": benchmark_matches,
                    "join_method": runner.get("joinMethod"),
                    "ambiguity_reason": "",
                }
            )
            csv_rows.append(
                {
                    "raceDate": race.get("raceDate"),
                    "meeting": race.get("meeting"),
                    "raceNumber": race.get("raceNumber"),
                    "runnerNumber": runner.get("runnerNumber"),
                    "runnerName": runner.get("runnerName"),
                    "rating": rating_value if rating_value is not None else "",
                    "epi": epi_value if epi_value is not None else "",
                    "marketPrice": (runner.get("marketPrice") or {}).get("value") if isinstance(runner.get("marketPrice"), dict) else runner.get("marketPrice"),
                    "edgeiqPrice": edgeiq_price_value if edgeiq_price_value is not None else "",
                    "earlySpeed": early_speed_value if early_speed_value is not None else "",
                    "suitability": suitability_value if suitability_value is not None else "",
                    "raceShape": race_shape_value,
                    "lateSpeed": late_speed_value if late_speed_value is not None else "",
                    "formMomentum": form_momentum_value if form_momentum_value is not None else "",
                    "preparationProfile": "YES" if runner.get("preparationProfile") else "",
                    "sectionalRunMatches": sectional_matches,
                    "benchmarkRunMatches": benchmark_matches,
                }
            )

        totals.update(metrics)
        race_coverage_rows.append(
            {
                "race_date": race.get("raceDate"),
                "meeting": race.get("meeting"),
                "race_number": race.get("raceNumber"),
                "runners": metrics["runners"],
                "Weather by race": 1 if race_weather else 0,
                "Weather runner rows": metrics["weather"],
                "EPI": metrics["epi"],
                "EDGEiQ Price": metrics["edgeiq_price"],
                "Early Speed": metrics["early_speed"],
                "Suitability": metrics["suitability"],
                "Race Shape": metrics["race_shape"],
                "Late Speed": metrics["late_speed"],
                "Form Momentum": metrics["form_momentum"],
                "Preparation Profile": metrics["preparation"],
                "Career Profile": metrics["career_profile"],
                "Recent Form": metrics["recent_form"],
            }
        )

    payload = {
        "schemaVersion": "edgeiq_form_guide_enriched_v2",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceContract": {
            "base": "edgeiq_form_guide_enriched_v1.json",
            "weather": "edgeiq_metropolitan_weather_v1.json joined by normalised meeting; date/source age retained.",
            "sectionals": "edgeiq_form_sectional_profile_feed_v1.csv joined by runner+run date+track+race number+distance; CLASS_BENCHMARK preferred over ALL_CLASSES_BENCHMARK.",
            "benchmark": "standardised sectional finish_len and split_lengths in lengths versus benchmark; sign convention preserved from source feed.",
            "rating": "run_ratings_v1.csv historical run_rating joined by runner+run date+distance where unique; governed terminal historical ERI overrides only on exact current-runner plus historical date/track/distance context match.",
            "historicalEpi": "edgeiq_epi_workspace_terminal_feed_v1.csv start_1..start_10 contexts joined by exact current runner plus historical date, normalised track and distance; ambiguous contexts are excluded and unmatched runs remain blank.",
            "pricing": "edgeiq_fair_price_epr_v1.csv selected first on exact current race date/track/race/runner from governed EPR Market V1; legacy V7.2/live-board fair price remains fallback only when no exact EPR Market V1 row exists. No public-market or React-derived fallback.",
            "earlySpeed": "edgeiq_current_early_speed_v1.json current-race projection from as-of historical early_raw; stale projected_spd remains blocked.",
            "raceShape": "edgeiq_current_race_shape_v2.json runner-specific current race-shape adapter; unsupported runners are not defaulted to MIDFIELD.",
            "suitability": "edgeiq_current_suitability_v1.json current-race runner-specific setup score; not a duplicate of EPI.",
            "lateSpeed": "edgeiq_current_late_speed_v1.json current-race projection from as-of benchmarked late sectionals where available, with speed_master late_raw fallback; late_power_index remains blocked.",
            "formMomentum": "edgeiq_current_form_momentum_v1.json point-in-time trajectory score from as-of historical EPI/sectional/margin evidence; not finish-position-only.",
            "careerTrackDistance": "TRACK and DISTANCE records are current-race context aggregates from edgeiq_results_master_v1.csv where result_status=RESULTED and historical race_date < current race date. TRACK joins by canonical meeting track; DISTANCE joins by exact distance metres.",
            "preparation": "edgeiq_runner_profile_stats_v1.csv first_up/second_up/third_up factual record fields.",
            "notFabricated": ["EPI", "EDGEiQ Price", "Suitability", "Race Shape", "Form Momentum"],
        },
        "races": base.get("races", []),
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_csv(OUT_CSV, csv_rows, ["raceDate", "meeting", "raceNumber", "runnerNumber", "runnerName", "rating", "epi", "marketPrice", "edgeiqPrice", "earlySpeed", "suitability", "raceShape", "lateSpeed", "formMomentum", "preparationProfile", "sectionalRunMatches", "benchmarkRunMatches"])
    write_csv(JOIN_AUDIT, join_rows, ["race_date", "meeting", "race_number", "runner_number", "runner_id", "runner_name", "weather_match", "rating_match", "epi_match", "price_match", "early_speed_match", "race_shape_match", "suitability_match", "late_speed_match", "momentum_match", "profile_match", "preparation_match", "recent_form_match", "sectional_run_matches", "benchmark_run_matches", "join_method", "ambiguity_reason"])
    write_csv(COVERAGE_CSV, race_coverage_rows, ["race_date", "meeting", "race_number", "runners", "Weather by race", "Weather runner rows", "EPI", "EDGEiQ Price", "Early Speed", "Suitability", "Race Shape", "Late Speed", "Form Momentum", "Preparation Profile", "Career Profile", "Recent Form"])
    write_csv(REGISTRY_CSV, registry_rows, list(registry_rows[0].keys()))
    REGISTRY_JSON.write_text(json.dumps(registry_rows, indent=2), encoding="utf-8")
    summary_lines = [
        "EDGEiQ Form Guide V3.4 engine registry",
        f"Generated: {payload['generatedAt']}",
        f"Engines documented: {len(registry_rows)}",
        "",
        "Selected engines:",
        *[f"- {row['engine_name']}: {row['engine_version']} ({row['reason']})" for row in registry_rows if row["selected_or_rejected"] == "selected"],
        "",
        "Rejected/current-date gaps:",
        *[f"- {row['engine_name']}: {row['engine_version']} ({row['reason']})" for row in registry_rows if row["selected_or_rejected"] == "rejected"],
    ]
    REGISTRY_SUMMARY.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    total_runners = totals["runners"]
    rateable_summary = {}
    if HISTORICAL_EPI_RATEABLE_SUMMARY_V38.exists():
        try:
            rateable_summary = json.loads(
                HISTORICAL_EPI_RATEABLE_SUMMARY_V38.read_text(encoding="utf-8")
            )
        except json.JSONDecodeError:
            rateable_summary = {}
    rateable_lines = []
    if rateable_summary:
        rateable_lines = [
            (
                "Historical EPI Rateable Coverage: "
                f"{rateable_summary.get('RATEABLE_RATED', '')}/"
                f"{rateable_summary.get('RATEABLE_TOTAL', '')}"
                f" ({rateable_summary.get('RATEABLE_COVERAGE_PCT', '')}%)"
            ),
            (
                "Historical EPI Structurally Non-Rateable: "
                f"{rateable_summary.get('STRUCTURALLY_NON_RATEABLE', '')}/"
                f"{rateable_summary.get('TOTAL_HISTORICAL_RUNS', '')}"
            ),
            (
                "Historical EPI Rateable Unresolved: "
                f"{rateable_summary.get('RATEABLE_UNRESOLVED', '')}"
            ),
        ]
    summary = [
        "EDGEiQ Form Guide V3.4 coverage summary",
        f"Generated: {payload['generatedAt']}",
        f"Runners: {total_runners}",
        f"Weather races: 0/40 -> {sum(1 for row in race_coverage_rows if row['Weather by race'])}/{len(race_coverage_rows)}",
        f"Weather runner rows: 0/{total_runners} -> {totals['weather']}/{total_runners}",
        f"EPI: 0/{total_runners} -> {totals['epi']}/{total_runners}",
        f"Historical EPI: 0/{run_totals['runs']} -> {run_totals['historical_epi_matches']}/{run_totals['runs']}",
        *rateable_lines,
        f"Historical Rating: 0/{run_totals['runs']} -> {sum(1 for race in base.get('races', []) for runner in race.get('runners', []) for run in runner.get('fullForm', []) if isinstance(run.get('raceRating'), dict) and run.get('raceRating', {}).get('value') is not None)}/{run_totals['runs']}",
        f"EDGEiQ Price: 0/{total_runners} -> {totals['edgeiq_price']}/{total_runners}",
        f"Early Speed: 0/{total_runners} -> {totals['early_speed']}/{total_runners}",
        f"Historical Early Speed: 0/{run_totals['runs']} -> {run_totals['historical_speed_matches']}/{run_totals['runs']}",
        f"Suitability: 0/{total_runners} -> {totals['suitability']}/{total_runners}",
        f"Race Shape: 0/{total_runners} -> {totals['race_shape']}/{total_runners}",
        f"Late Speed: 0/{total_runners} -> {totals['late_speed']}/{total_runners}",
        f"Form Momentum: 0/{total_runners} -> {totals['form_momentum']}/{total_runners}",
        f"Preparation Profile: 0/{total_runners} -> {totals['preparation']}/{total_runners}",
        f"Sectional 800-600: 0/{run_totals['runs']} -> {run_totals['sectional_800_600']}/{run_totals['runs']}",
        f"Sectional 600-400: 0/{run_totals['runs']} -> {run_totals['sectional_600_400']}/{run_totals['runs']}",
        f"Sectional 400-200: 0/{run_totals['runs']} -> {run_totals['sectional_400_200']}/{run_totals['runs']}",
        f"Sectional 200-F: 0/{run_totals['runs']} -> {run_totals['sectional_200_f']}/{run_totals['runs']}",
        f"Benchmark Evidence: 0/{run_totals['runs']} -> {run_totals['benchmark_matches']}/{run_totals['runs']}",
        f"Career Profile: {totals['career_profile']}/{total_runners} -> {totals['career_profile']}/{total_runners}",
        f"Recent Form: {totals['recent_form']}/{total_runners} -> {totals['recent_form']}/{total_runners}",
        "",
        "Current-date gaps are not backfilled from prior-date model outputs.",
    ]
    COVERAGE_SUMMARY.write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(OUT_JSON)
    print(COVERAGE_SUMMARY.read_text(encoding="utf-8"))
    return payload


if __name__ == "__main__":
    build()
