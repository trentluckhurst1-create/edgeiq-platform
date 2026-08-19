from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DATA = ROOT / "public" / "data"


def read_text(path: str | Path) -> str:
    target = Path(path)
    if not target.is_absolute():
        target = ROOT / target
    return target.read_text(encoding="utf-8", errors="replace")


def write_text(path: str | Path, text: str) -> None:
    target = Path(path)
    if not target.is_absolute():
        target = ROOT / target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, indent=2, ensure_ascii=False))


def read_json(path: str | Path) -> Any:
    target = Path(path)
    if not target.is_absolute():
        target = ROOT / target
    return json.loads(target.read_text(encoding="utf-8", errors="replace"))


def read_csv(path: str | Path) -> list[dict[str, str]]:
    target = Path(path)
    if not target.is_absolute():
        target = ROOT / target
    if not target.exists():
        return []
    with target.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
      return [dict(row) for row in csv.DictReader(handle)]


def clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"", "-", "none", "null", "undefined", "n/a", "na"}:
        return ""
    return text


def normalise_track(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean(value).upper())


def normalise_runner(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", clean(value).upper().replace("'", ""))


def race_key_from_parts(date: Any, meeting: Any, race_number: Any) -> str:
    match = re.search(r"\d+", clean(race_number))
    return "|".join([clean(date), normalise_track(meeting), match.group(0) if match else ""])


def count_populated(rows: list[dict[str, Any]], fields: list[str]) -> tuple[int, int]:
    total = len(rows)
    covered = 0
    for row in rows:
        if any(clean(row.get(field)) for field in fields):
            covered += 1
    return covered, total


def pct(covered: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((covered / total) * 100, 2)


def format_pct(covered: int, total: int) -> str:
    return f"{pct(covered, total):.2f}%"


def load_catalog() -> dict[str, Any]:
    path = PUBLIC_DATA / "edgeiq_three_day_product_catalog_v1.json"
    return read_json(path) if path.exists() else {"meetings": []}


def catalog_runners() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    catalog = load_catalog()
    for meeting in catalog.get("meetings", []):
        for race in meeting.get("races", []):
            race_key = clean(race.get("raceKey")) or race_key_from_parts(meeting.get("date"), meeting.get("meeting"), race.get("raceNumber"))
            for runner in race.get("runners", []):
                official = runner.get("official") or {}
                source = runner.get("source") or {}
                output.append({
                    "meeting_key": clean(meeting.get("meetingKey")),
                    "meeting": clean(meeting.get("meeting")),
                    "date": clean(meeting.get("date")),
                    "race_key": race_key,
                    "race_no": clean(race.get("raceNumber")),
                    "race_name": clean(race.get("raceName")),
                    "runner_no": clean(official.get("no") or official.get("number") or source.get("runnerNumber") or source.get("saddlecloth")),
                    "runner": clean(official.get("runner") or source.get("horseName") or source.get("runnerName") or source.get("horse")),
                    "barrier": clean(official.get("barrier") or source.get("barrierNumber") or source.get("barrier")),
                    "weight": clean(official.get("weight") or source.get("weight")),
                    "jockey": clean(official.get("jockey") or source.get("jockeyName") or source.get("jockey")),
                    "trainer": clean(official.get("trainer") or source.get("trainerName") or source.get("trainer")),
                    "market": clean(official.get("market") or source.get("market") or source.get("fixedOdds")),
                    "scratched": clean(official.get("scratched") or source.get("scratched")),
                })
    return output


def load_form_enriched_runners() -> list[dict[str, Any]]:
    path = PUBLIC_DATA / "edgeiq_form_guide_enriched_v2.json"
    if not path.exists():
        return []
    feed = read_json(path)
    output: list[dict[str, Any]] = []
    for race in feed.get("races", []):
        for runner in race.get("runners", []):
            row = {
                "race_key": clean(race.get("raceKey")),
                "meeting": clean(race.get("meeting")),
                "date": clean(race.get("raceDate")),
                "race_no": clean(race.get("raceNumber")),
                "runner_no": clean(runner.get("runnerNumber")),
                "runner": clean(runner.get("runnerName")),
                "normalised_runner": normalise_runner(runner.get("runnerName")),
                "epi": unwrap(runner.get("epi")),
                "rating": unwrap(runner.get("rating")),
                "market": unwrap(runner.get("marketPrice")),
                "edgeiq_price": unwrap(runner.get("edgeiqPrice")),
                "early_speed": unwrap(runner.get("earlySpeed")),
                "late_speed": unwrap(runner.get("lateSpeed")),
                "suitability": unwrap(runner.get("suitability")),
                "race_shape": unwrap(runner.get("raceShape")),
                "form_momentum": unwrap(runner.get("formMomentum")),
                "track_record": record_display(runner.get("trackRecord")),
                "distance_record": record_display(runner.get("distanceRecord")),
                "condition_record": record_display(runner.get("conditionRecord")),
                "career_record": record_display(runner.get("careerRecord")),
                "track_distance_record": record_display(runner.get("trackDistanceRecord")),
                "recent_form_count": str(len(runner.get("fullForm") or [])),
                "last_five": " ".join(str(x) for x in (runner.get("lastFive") or [])),
                "sectionals": "yes" if any((run.get("sectionalIndices") or {}) for run in (runner.get("fullForm") or [])) else "",
                "gear": clean(runner.get("gear_current") or runner.get("currentGear")),
                "scratched": str(bool(runner.get("scratched"))),
            }
            output.append(row)
    return output


def unwrap(value: Any) -> str:
    if isinstance(value, dict) and "value" in value:
        return clean(value.get("value"))
    return clean(value)


def record_display(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    if clean(value.get("display")):
        return clean(value.get("display"))
    starts = value.get("starts")
    if starts is None:
        return ""
    return f"{starts}:{value.get('wins', 0)}-{value.get('seconds', 0)}-{value.get('thirds', 0)}"


def indexed_by_race_runner(rows: list[dict[str, str]]) -> set[tuple[str, str]]:
    output: set[tuple[str, str]] = set()
    for row in rows:
        key = clean(row.get("race_key"))
        runner = normalise_runner(row.get("horse") or row.get("runner"))
        if key and runner:
            output.add((key, runner))
    return output


FIELD_TRACE: list[dict[str, str]] = [
    {"workspace": "Race", "displayed_field": "Race identity", "canonical_builder": "build_edgeiq_three_day_product_catalog_v1.py", "service": "threeDayCatalog.ts", "feed": "edgeiq_three_day_product_catalog_v1.json", "ui": "RaceFileV3 / RaceWorkspace", "reason": "meeting/race state"},
    {"workspace": "Field", "displayed_field": "Runner number", "canonical_builder": "build_edgeiq_three_day_product_catalog_v1.py", "service": "formGuideNormaliser.ts", "feed": "edgeiq_three_day_product_catalog_v1.json", "ui": "RaceFormGuideWorkspace", "reason": "race field"},
    {"workspace": "Field", "displayed_field": "Silks", "canonical_builder": "build_edgeiq_three_day_product_catalog_v1.py", "service": "formGuideNormaliser.ts", "feed": "edgeiq_three_day_product_catalog_v1.json", "ui": "RaceFormGuideWorkspace", "reason": "race field"},
    {"workspace": "Field", "displayed_field": "Trainer", "canonical_builder": "build_edgeiq_three_day_product_catalog_v1.py", "service": "formGuideNormaliser.ts", "feed": "edgeiq_three_day_product_catalog_v1.json", "ui": "RaceFormGuideWorkspace", "reason": "race field"},
    {"workspace": "Field", "displayed_field": "Jockey", "canonical_builder": "build_edgeiq_three_day_product_catalog_v1.py", "service": "formGuideNormaliser.ts", "feed": "edgeiq_three_day_product_catalog_v1.json", "ui": "RaceFormGuideWorkspace", "reason": "race field"},
    {"workspace": "Field", "displayed_field": "Weight", "canonical_builder": "build_edgeiq_three_day_product_catalog_v1.py", "service": "formGuideNormaliser.ts", "feed": "edgeiq_three_day_product_catalog_v1.json", "ui": "RaceFormGuideWorkspace / MapWorkspace", "reason": "race field"},
    {"workspace": "Field", "displayed_field": "Barrier", "canonical_builder": "build_edgeiq_three_day_product_catalog_v1.py", "service": "formGuideNormaliser.ts / mapFeed.ts", "feed": "edgeiq_three_day_product_catalog_v1.json / edgeiq_map_terminal_feed_v1.csv", "ui": "RaceFormGuideWorkspace / MapWorkspace", "reason": "race field and map feed"},
    {"workspace": "Performance", "displayed_field": "EPI", "canonical_builder": "build_edgeiq_form_guide_enriched_v2.py / build_edgeiq_epi_workspace_terminal_feed_v1.py", "service": "formGuideNormaliser.ts / epiWorkspaceFeed.ts", "feed": "edgeiq_form_guide_enriched_v2.json / edgeiq_epi_workspace_terminal_feed_v1.csv", "ui": "RaceFormGuideWorkspace / EpiWorkspaceWorkspace", "reason": "current and historical ratings"},
    {"workspace": "Performance", "displayed_field": "ERI", "canonical_builder": "build_edgeiq_form_guide_enriched_v2.py", "service": "formGuideNormaliser.ts / epiWorkspaceFeed.ts", "feed": "edgeiq_form_guide_enriched_v2.json / edgeiq_epi_workspace_terminal_feed_v1.csv", "ui": "Recent form / EPI context", "reason": "historical race strength"},
    {"workspace": "Form", "displayed_field": "Early Speed", "canonical_builder": "build_edgeiq_current_early_speed_v1.py", "service": "formGuideNormaliser.ts", "feed": "edgeiq_form_guide_enriched_v2.json", "ui": "RaceFormGuideWorkspace", "reason": "current race speed projection"},
    {"workspace": "Form", "displayed_field": "Late Speed", "canonical_builder": "build_edgeiq_current_late_speed_v1.py", "service": "formGuideNormaliser.ts", "feed": "edgeiq_form_guide_enriched_v2.json", "ui": "RaceFormGuideWorkspace", "reason": "current race late speed projection"},
    {"workspace": "Form", "displayed_field": "Suitability", "canonical_builder": "build_edgeiq_current_suitability_v1.py", "service": "formGuideNormaliser.ts", "feed": "edgeiq_form_guide_enriched_v2.json", "ui": "RaceFormGuideWorkspace", "reason": "current race suitability"},
    {"workspace": "Form", "displayed_field": "Form Momentum", "canonical_builder": "build_edgeiq_current_form_momentum_v1.py", "service": "formGuideNormaliser.ts", "feed": "edgeiq_form_guide_enriched_v2.json", "ui": "RaceFormGuideWorkspace", "reason": "current form trend"},
    {"workspace": "Market", "displayed_field": "Market", "canonical_builder": "build_edgeiq_market_terminal_feed_v1.py", "service": "marketFeed.ts / formGuideNormaliser.ts", "feed": "edgeiq_market_terminal_feed_v1.csv / edgeiq_form_guide_enriched_v2.json", "ui": "MarketWorkspace / RaceFormGuideWorkspace", "reason": "current market when available"},
    {"workspace": "Market", "displayed_field": "EDGEiQ Price", "canonical_builder": "build_edgeiq_form_guide_enriched_v2.py / build_edgeiq_market_terminal_feed_v1.py", "service": "marketFeed.ts / formGuideNormaliser.ts", "feed": "edgeiq_market_terminal_feed_v1.csv / edgeiq_form_guide_enriched_v2.json", "ui": "MarketWorkspace / RaceFormGuideWorkspace", "reason": "assessed price"},
    {"workspace": "Map", "displayed_field": "Run style / map", "canonical_builder": "build_edgeiq_map_terminal_feed_v1.py", "service": "mapFeed.ts", "feed": "edgeiq_map_terminal_feed_v1.csv", "ui": "MapWorkspace", "reason": "expected settling read"},
    {"workspace": "Nexus", "displayed_field": "Key insights", "canonical_builder": "build_edgeiq_insights_terminal_feed_v1.py", "service": "insightsFeed.ts", "feed": "edgeiq_insights_terminal_feed_v1.csv", "ui": "InsightsWorkspace", "reason": "current race intelligence"},
    {"workspace": "Results", "displayed_field": "Race result context", "canonical_builder": "build_edgeiq_meeting_results_terminal_feed_v1.py / historical run services", "service": "ResultsWorkspace.ts", "feed": "runner historical run context", "ui": "ResultsWorkspace", "reason": "runner-level historical result currently connected where available"},
    {"workspace": "Track/Weather", "displayed_field": "Track and weather", "canonical_builder": "build_edgeiq_on_track_weather_governed_v1_2.py", "service": "weatherFeed.ts / MeetingWeatherWorkspace", "feed": "governed live-weather v1.2 outputs", "ui": "Meeting workspace weather", "reason": "meeting-level weather integration preserved"},
    {"workspace": "Scratchings/Gear", "displayed_field": "Scratchings and gear", "canonical_builder": "meeting scratchings and gear builders", "service": "MeetingScratchingsWorkspace / MeetingGearChangesWorkspace", "feed": "meeting governed feeds", "ui": "Meeting tabs", "reason": "meeting-level tabs"},
]
