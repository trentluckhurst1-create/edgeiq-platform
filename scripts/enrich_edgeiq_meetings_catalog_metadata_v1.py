from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import build_edgeiq_racing_australia_track_conditions_v1 as racing_australia_builder

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
RACING_AUSTRALIA = DATA / "edgeiq_racing_australia_track_conditions_v1.json"
WEATHER = DATA / "edgeiq_victorian_track_weather_v1.json"
AUDIT = DATA / "edgeiq_meetings_catalog_metadata_enrichment_v1.json"

SPONSOR_PREFIXES = (
    "LADBROKES ",
    "SPORTSBET-",
    "SPORTSBET ",
    "BET365 ",
    "BETDELUXE ",
    "PICKLEBET PARK ",
)

ALIASES = {
    "CAULFIELD HEATH": "CAULFIELD",
    "SANDOWN HILLSIDE": "SANDOWN",
    "SANDOWN LAKESIDE": "SANDOWN",
    "LADBROKES PARK": "SANDOWN",
    "LADBROKES PARK HILLSIDE": "SANDOWN",
    "LADBROKES PARK LAKESIDE": "SANDOWN",
    "BALLARAT SYNTHETIC": "BALLARAT",
    "SPORTSBET-BALLARAT SYNTHETIC": "BALLARAT",
    "GEELONG SYNTHETIC": "GEELONG",
    "PAKENHAM SYNTHETIC": "PAKENHAM",
    "SOUTHSIDE PAKENHAM SYNTHETIC": "PAKENHAM",
    "BELMONT PARK": "BELMONT",
}


def text(value: Any) -> str:
    if value is None:
        return ""
    value = str(value).strip()
    if value.lower() in {"", "none", "null", "n/a", "na", "-", "tba"}:
        return ""
    return value


def meeting_key(value: Any) -> str:
    raw = text(value).upper()
    for prefix in SPONSOR_PREFIXES:
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
            break
    raw = ALIASES.get(raw, raw)
    return raw.replace(" ", "_")


def combined_track(source: dict[str, Any]) -> str:
    condition = text(source.get("track_condition") or source.get("going"))
    rating = text(source.get("track_rating") or source.get("track_rating_short"))
    if condition and rating:
        if rating.lower() in condition.lower():
            return condition
        return f"{condition} {rating}"
    return condition or rating


def load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    records = payload.get("records", []) if isinstance(payload, dict) else []
    return [row for row in records if isinstance(row, dict)]


def racing_australia_index() -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in load_records(RACING_AUSTRALIA):
        race_date = text(row.get("race_date"))[:10]
        track = meeting_key(row.get("canonical_track_identity") or row.get("meeting_display"))
        if race_date and track:
            result[(race_date, track)] = row
    return result


def weather_index() -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in load_records(WEATHER):
        race_date = text(row.get("race_date"))[:10]
        track = meeting_key(row.get("canonical_track_identity") or row.get("canonical_venue_name"))
        if race_date and track:
            result[(race_date, track)] = row
    return result


def first_race_source(races: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not races:
        return None
    source = races[0].setdefault("source", {})
    return source if isinstance(source, dict) else None


def main() -> int:
    if not CATALOG.exists():
        print("EDGEIQ_MEETINGS_CATALOG_METADATA_ENRICHMENT_V1 FAIL catalog_missing")
        return 1

    # Refresh the governed Racing Australia source in the same stage so Meetings
    # can never silently rely on a stale conditions file.
    ra_refresh_status = racing_australia_builder.main()
    if ra_refresh_status != 0:
        print("EDGEIQ_MEETINGS_CATALOG_METADATA_ENRICHMENT_V1 FAIL racing_australia_refresh")
        return 1

    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    racing_australia = racing_australia_index()
    weather = weather_index()

    meetings_seen = 0
    ra_matches = 0
    track_enriched_ra = 0
    rail_enriched_ra = 0
    weather_enriched_ra = 0
    track_enriched_fallback = 0
    rail_enriched_fallback = 0
    weather_enriched_fallback = 0

    for meeting in payload.get("meetings", []):
        if not isinstance(meeting, dict):
            continue
        meetings_seen += 1
        races = [r for r in meeting.get("races", []) if isinstance(r, dict)]
        source = first_race_source(races)

        meeting_date = text(meeting.get("date"))[:10]
        key = meeting_key(meeting.get("meeting") or meeting.get("name") or meeting.get("venue"))
        ra = racing_australia.get((meeting_date, key))

        # Racing Australia Track Conditions is the governed meeting-level authority
        # for Australian track condition, rail and weather forecast. Raw race-feed
        # values are preserved and used only when no governed value is available.
        if ra:
            ra_matches += 1
            track = text(ra.get("track_condition"))
            rail = text(ra.get("rail"))
            weather_forecast = text(ra.get("weather_forecast"))

            meeting["trackCondition"] = track or meeting.get("trackCondition")
            meeting["rail"] = rail or meeting.get("rail")
            meeting["weather"] = weather_forecast or meeting.get("weather")
            meeting["trackMetadataAuthority"] = "Racing Australia"
            meeting["trackMetadataSourceUrl"] = ra.get("source_url")

            if source is not None:
                if track:
                    source["official_track_rating"] = track
                    source["official_track_rating_provenance"] = "RACING_AUSTRALIA_TRACK_CONDITIONS"
                    track_enriched_ra += 1
                if rail:
                    source["rail_position"] = rail
                    source["rail_position_provenance"] = "RACING_AUSTRALIA_TRACK_CONDITIONS"
                    rail_enriched_ra += 1
                if weather_forecast:
                    source["weather"] = weather_forecast
                    source["weather_provenance"] = "RACING_AUSTRALIA_TRACK_CONDITIONS"
                    weather_enriched_ra += 1

                for target, source_field in (
                    ("track_type", "track_type"),
                    ("penetrometer", "penetrometer"),
                    ("irrigation", "irrigation"),
                    ("rainfall", "rainfall"),
                    ("track_comment", "comment"),
                    ("track_additional_information", "additional_information"),
                ):
                    value = text(ra.get(source_field))
                    if value:
                        source[target] = value
                        source[f"{target}_provenance"] = "RACING_AUSTRALIA_TRACK_CONDITIONS"

        # Fallback only for values the governed source did not supply or when no
        # matching Racing Australia row exists. Never fabricate.
        latest_track = ""
        latest_rail = ""
        for race in races:
            race_source = race.get("source") if isinstance(race.get("source"), dict) else {}
            candidate = combined_track(race_source)
            if candidate:
                latest_track = candidate
            rail_candidate = text(race_source.get("rail_position") or race.get("rail"))
            if rail_candidate:
                latest_rail = rail_candidate

        existing_track = text(meeting.get("trackCondition"))
        if not existing_track and latest_track:
            meeting["trackCondition"] = latest_track
            if source is not None:
                source["official_track_rating"] = latest_track
                source["official_track_rating_provenance"] = "LATEST_OFFICIAL_RACE_FEED_VALUE"
            track_enriched_fallback += 1

        existing_rail = text(meeting.get("rail"))
        if not existing_rail and latest_rail:
            meeting["rail"] = latest_rail
            if source is not None:
                source["rail_position"] = latest_rail
                source["rail_position_provenance"] = "LATEST_OFFICIAL_RACE_FEED_VALUE"
            rail_enriched_fallback += 1

        existing_weather = text(meeting.get("weather"))
        if not existing_weather:
            w = weather.get((meeting_date, key))
            if w and source is not None:
                temp = text(w.get("temperature_c"))
                direction = text(w.get("wind_direction"))
                speed = text(w.get("wind_speed_kmh"))
                rain = text(w.get("rain_since_9am_mm"))
                disclosure = text(w.get("user_disclosure"))
                usable = any((temp, direction, speed, rain, disclosure))
                if usable:
                    if disclosure:
                        source["weather"] = disclosure
                        meeting["weather"] = disclosure
                    if temp:
                        source["weather_max"] = temp
                    if direction:
                        source["weather_wind_direction"] = direction
                    if speed:
                        source["weather_wind_speed"] = f"{speed} km/h"
                    if rain:
                        source["weather_rain"] = f"{rain} mm"
                    source["weather_provenance"] = "EDGEIQ_VICTORIAN_TRACK_WEATHER_V1_FALLBACK"
                    weather_enriched_fallback += 1

    payload["metadataEnrichedAt"] = datetime.now(timezone.utc).isoformat()
    payload["meetingsMetadataAuthority"] = "Racing Australia Track Conditions"
    CATALOG.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    audit = {
        "schema_version": "edgeiq_meetings_catalog_metadata_enrichment_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "meetings_seen": meetings_seen,
        "racing_australia_matches": ra_matches,
        "track_enriched_racing_australia": track_enriched_ra,
        "rail_enriched_racing_australia": rail_enriched_ra,
        "weather_enriched_racing_australia": weather_enriched_ra,
        "track_enriched_fallback": track_enriched_fallback,
        "rail_enriched_fallback": rail_enriched_fallback,
        "weather_enriched_fallback": weather_enriched_fallback,
        "fabricated_values": 0,
    }
    AUDIT.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

    print("EDGEIQ_MEETINGS_CATALOG_METADATA_ENRICHMENT_V1 PASS")
    print(f"MEETINGS_SEEN={meetings_seen}")
    print(f"RACING_AUSTRALIA_MATCHES={ra_matches}")
    print(f"TRACK_ENRICHED_RA={track_enriched_ra}")
    print(f"RAIL_ENRICHED_RA={rail_enriched_ra}")
    print(f"WEATHER_ENRICHED_RA={weather_enriched_ra}")
    print(f"TRACK_ENRICHED_FALLBACK={track_enriched_fallback}")
    print(f"RAIL_ENRICHED_FALLBACK={rail_enriched_fallback}")
    print(f"WEATHER_ENRICHED_FALLBACK={weather_enriched_fallback}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
