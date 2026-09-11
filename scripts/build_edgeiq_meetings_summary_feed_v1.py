from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
WINDOW = DATA / "edgeiq_three_day_window_v1.json"
OUTPUT = DATA / "edgeiq_meetings_summary_feed_v1.json"


def text(value: Any) -> str:
    if value is None:
        return ""
    value = str(value).replace("\n", " ").strip()
    if value.lower() in {"", "-", "none", "null", "undefined", "n/a", "na", "pending"}:
        return ""
    return re.sub(r"\s+", " ", value)


def first(*values: Any) -> str:
    for value in values:
        candidate = text(value)
        if candidate:
            return candidate
    return ""


def scratched(runner: dict[str, Any]) -> bool:
    official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
    source = runner.get("source") if isinstance(runner.get("source"), dict) else {}
    if official.get("scratched") is True or source.get("scratched") is True or source.get("is_scratched") is True:
        return True
    return "scratch" in first(official.get("status"), source.get("status")).lower()


def race_status(race: dict[str, Any]) -> str:
    source = race.get("source") if isinstance(race.get("source"), dict) else {}
    raw = first(source.get("race_status"), source.get("result_status"), source.get("full_status"), source.get("meet_status"))
    upper = raw.upper()
    if "FINAL" in upper:
        return "Final fields"
    if "ACCEPT" in upper:
        return "Acceptances"
    if "RESULT" in upper:
        return "Results"
    if "ABANDON" in upper:
        return "Abandoned"
    return raw or "Not supplied"


def meeting_status(meeting: dict[str, Any], races: list[dict[str, Any]]) -> str:
    source = meeting.get("source") if isinstance(meeting.get("source"), dict) else {}
    first_source = races[0].get("source", {}) if races and isinstance(races[0].get("source"), dict) else {}
    raw = first(source.get("FullStatus"), source.get("MeetStatus"), source.get("Status"), first_source.get("full_status"), first_source.get("meet_status"))
    upper = raw.upper()
    if "ACCEPT" in upper:
        return "Acceptances"
    if "FINAL" in upper:
        return "Final fields"
    if "RESULT" in upper:
        return "Results"
    if "ABANDON" in upper:
        return "Abandoned"
    return raw or "Not supplied"


def race_time(race: dict[str, Any]) -> str:
    return first(race.get("raceTime"), race.get("source", {}).get("race_time"), race.get("source", {}).get("race_time_local")) or "Not supplied"


def restriction(name: str) -> str:
    match = re.search(r"(2YO|3YO\+?|Fillies|Mares|Colts|Geldings)", name, flags=re.I)
    return match.group(0) if match else "Not supplied"


def condition_kind(value: str) -> str:
    lower = value.lower()
    if "heavy" in lower:
        return "heavy"
    if "soft" in lower:
        return "soft"
    if "good" in lower:
        return "good"
    return "other"


def main() -> int:
    if not CATALOG.exists() or not WINDOW.exists():
        print("EDGEIQ_MEETINGS_SUMMARY_FEED_V1 FAIL source_missing")
        return 1

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    window = json.loads(WINDOW.read_text(encoding="utf-8"))
    meetings = [m for m in catalog.get("meetings", []) if isinstance(m, dict)]
    generated_at = first(catalog.get("generatedAt"), window.get("generatedAt"), datetime.now(timezone.utc).isoformat())

    days: list[dict[str, Any]] = []
    total_meetings = 0
    total_races = 0

    for window_day in window.get("dates", []):
        if not isinstance(window_day, dict):
            continue
        date_value = text(window_day.get("date"))[:10]
        key = text(window_day.get("key"))
        day_meetings: list[dict[str, Any]] = []

        for meeting in meetings:
            if text(meeting.get("date"))[:10] != date_value:
                continue
            races = sorted(
                [r for r in meeting.get("races", []) if isinstance(r, dict)],
                key=lambda r: int(r.get("raceNumber") or 0),
            )
            first_race = races[0] if races else {}
            first_source = first_race.get("source") if isinstance(first_race.get("source"), dict) else {}
            meeting_source = meeting.get("source") if isinstance(meeting.get("source"), dict) else {}

            track = first(
                first_source.get("official_track_rating"),
                meeting.get("trackCondition"),
                first_race.get("trackCondition"),
                first_source.get("track_rating_short"),
                first_source.get("going"),
                first_source.get("track_condition"),
                first_source.get("track_rating"),
            ) or "Not supplied"
            rail = first(meeting.get("rail"), first_race.get("rail"), first_source.get("rail_position")) or "Not supplied"
            weather = first(meeting.get("weather"), first_source.get("weather")) or "Awaiting Weather Feed"
            wind_direction = first(first_source.get("weather_wind_direction"))
            wind_speed = first(first_source.get("weather_wind_speed"))
            wind = f"{wind_direction} {wind_speed}".strip() if (wind_direction or wind_speed) else "Not supplied"
            temp_min = first(first_source.get("weather_min"))
            temp_max = first(first_source.get("weather_max"))
            temp = f"{temp_min}-{temp_max}" if temp_min and temp_max else (temp_max or temp_min or "Not supplied")
            rain = first(first_source.get("rainfall"), first_source.get("weather_rain")) or "Not supplied"
            irrigation = first(first_source.get("irrigation")) or "Not supplied"
            official_update = first(first_source.get("built_at"), catalog.get("generatedAt")) or "Not supplied"

            race_summaries: list[dict[str, Any]] = []
            declared = 0
            scratches = 0
            for race in races:
                runners = [r for r in race.get("runners", []) if isinstance(r, dict)]
                declared += len(runners)
                scratches += sum(1 for runner in runners if scratched(runner))
                race_name = first(race.get("raceName")) or "Unnamed race"
                race_summaries.append(
                    {
                        "raceKey": text(race.get("raceKey")),
                        "raceNumber": int(race.get("raceNumber") or 0),
                        "time": race_time(race),
                        "distance": first(race.get("distance")) or "Not supplied",
                        "name": race_name,
                        "raceClass": first(race.get("raceClass")) or "Not supplied",
                        "restriction": restriction(race_name),
                        "fieldSize": len(runners),
                        "status": race_status(race),
                    }
                )

            day_meetings.append(
                {
                    "meetingKey": text(meeting.get("meetingKey")),
                    "meeting": first(meeting.get("meeting")) or "Unnamed meeting",
                    "providerMeetingKey": first(meeting.get("providerMeetingKey")),
                    "date": date_value,
                    "venue": first(meeting_source.get("Venue"), meeting_source.get("Track"), meeting.get("providerMeetingKey"), meeting.get("meeting")) or "Not supplied",
                    "state": first(meeting_source.get("State"), first_source.get("state")) or "Not supplied",
                    "track": track,
                    "rail": rail,
                    "weather": weather,
                    "wind": wind,
                    "temp": temp,
                    "rain24h": rain,
                    "irrigation24h": irrigation,
                    "officialUpdate": official_update,
                    "races": int(meeting.get("raceCount") or len(races)),
                    "declared": declared,
                    "scratchings": scratches,
                    "first": race_time(races[0]) if races else "Not supplied",
                    "last": race_time(races[-1]) if races else "Not supplied",
                    "status": meeting_status(meeting, races),
                    "raceSummaries": race_summaries,
                }
            )

        totals = {
            "meetings": len(day_meetings),
            "races": sum(int(m.get("races") or 0) for m in day_meetings),
            "declared": sum(int(m.get("declared") or 0) for m in day_meetings),
            "scratchings": sum(int(m.get("scratchings") or 0) for m in day_meetings),
            "heavyTracks": sum(1 for m in day_meetings if condition_kind(text(m.get("track"))) == "heavy"),
            "softTracks": sum(1 for m in day_meetings if condition_kind(text(m.get("track"))) == "soft"),
            "goodTracks": sum(1 for m in day_meetings if condition_kind(text(m.get("track"))) == "good"),
            "weatherAlerts": sum(1 for m in day_meetings if text(m.get("weather")) not in {"", "Awaiting Weather Feed"}),
        }
        days.append(
            {
                "key": key,
                "date": date_value,
                "dayOffset": int(window_day.get("dayOffset") or 0),
                "generatedAt": generated_at,
                "totals": totals,
                "meetings": day_meetings,
            }
        )
        total_meetings += len(day_meetings)
        total_races += totals["races"]

    payload = {
        "schemaVersion": "edgeiq_meetings_summary_feed_v1",
        "timezone": "Australia/Melbourne",
        "generatedAt": generated_at,
        "sourceCatalog": CATALOG.name,
        "sourceWindow": WINDOW.name,
        "purpose": "LIGHTWEIGHT_MEETINGS_ONLY",
        "days": days,
    }
    OUTPUT.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")

    print("EDGEIQ_MEETINGS_SUMMARY_FEED_V1 PASS")
    print(f"MEETINGS={total_meetings}")
    print(f"RACES={total_races}")
    print(f"BYTES={OUTPUT.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
