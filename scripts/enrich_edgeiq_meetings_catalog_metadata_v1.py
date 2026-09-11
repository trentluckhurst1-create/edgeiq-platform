from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
WEATHER = DATA / "edgeiq_victorian_track_weather_v1.json"
AUDIT = DATA / "edgeiq_meetings_catalog_metadata_enrichment_v1.json"


def text(value: Any) -> str:
    if value is None:
        return ""
    value = str(value).strip()
    if value.lower() in {"", "none", "null", "n/a", "na", "-"}:
        return ""
    return value


def meeting_key(value: Any) -> str:
    raw = text(value).upper()
    for prefix in ("LADBROKES ", "SPORTSBET ", "BET365 "):
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
    aliases = {
        "CAULFIELD HEATH": "CAULFIELD",
        "SANDOWN HILLSIDE": "SANDOWN",
        "SANDOWN LAKESIDE": "SANDOWN",
        "LADBROKES PARK": "SANDOWN",
        "LADBROKES PARK HILLSIDE": "SANDOWN",
        "LADBROKES PARK LAKESIDE": "SANDOWN",
        "BALLARAT SYNTHETIC": "BALLARAT",
        "GEELONG SYNTHETIC": "GEELONG",
        "PAKENHAM SYNTHETIC": "PAKENHAM",
    }
    return aliases.get(raw, raw).replace(" ", "_")


def combined_track(source: dict[str, Any]) -> str:
    condition = text(source.get("track_condition") or source.get("going"))
    rating = text(source.get("track_rating") or source.get("track_rating_short"))
    if condition and rating:
        if rating.lower() in condition.lower():
            return condition
        return f"{condition} {rating}"
    return condition or rating


def weather_index() -> dict[tuple[str, str], dict[str, Any]]:
    if not WEATHER.exists():
        return {}
    try:
        payload = json.loads(WEATHER.read_text(encoding="utf-8"))
    except Exception:
        return {}
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in payload.get("records", []):
        if not isinstance(row, dict):
            continue
        race_date = text(row.get("race_date"))[:10]
        track = meeting_key(row.get("canonical_track_identity") or row.get("canonical_venue_name"))
        if race_date and track:
            result[(race_date, track)] = row
    return result


def main() -> int:
    if not CATALOG.exists():
        print("EDGEIQ_MEETINGS_CATALOG_METADATA_ENRICHMENT_V1 FAIL catalog_missing")
        return 1

    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    weather = weather_index()
    track_enriched = 0
    rail_enriched = 0
    weather_enriched = 0
    meetings_seen = 0

    for meeting in payload.get("meetings", []):
        if not isinstance(meeting, dict):
            continue
        meetings_seen += 1
        races = [r for r in meeting.get("races", []) if isinstance(r, dict)]

        # Use the latest race carrying an official track condition/rating as the
        # meeting-level current rating. Preserve each race's raw fields unchanged.
        latest_track = ""
        latest_rail = ""
        for race in races:
            source = race.get("source") if isinstance(race.get("source"), dict) else {}
            candidate = combined_track(source)
            if candidate:
                latest_track = candidate
            rail = text(source.get("rail_position") or race.get("rail"))
            if rail:
                latest_rail = rail

        if races and latest_track:
            first_source = races[0].setdefault("source", {})
            if isinstance(first_source, dict):
                first_source["official_track_rating"] = latest_track
                first_source["official_track_rating_provenance"] = "LATEST_OFFICIAL_RACE_FEED_VALUE"
                track_enriched += 1
            meeting["trackCondition"] = latest_track

        if latest_rail:
            meeting["rail"] = latest_rail
            if races:
                first_source = races[0].setdefault("source", {})
                if isinstance(first_source, dict):
                    first_source["rail_position"] = latest_rail
                    first_source["rail_position_provenance"] = "LATEST_OFFICIAL_RACE_FEED_VALUE"
            rail_enriched += 1

        w = weather.get((text(meeting.get("date"))[:10], meeting_key(meeting.get("meeting"))))
        if w and races:
            source = races[0].setdefault("source", {})
            if isinstance(source, dict):
                temp = text(w.get("temperature_c"))
                direction = text(w.get("wind_direction"))
                speed = text(w.get("wind_speed_kmh"))
                rain = text(w.get("rain_since_9am_mm"))
                disclosure = text(w.get("user_disclosure"))
                usable = any((temp, direction, speed, rain))
                if usable:
                    if disclosure:
                        source["weather"] = disclosure
                    if temp:
                        source["weather_max"] = temp
                    if direction:
                        source["weather_wind_direction"] = direction
                    if speed:
                        source["weather_wind_speed"] = f"{speed} km/h"
                    if rain:
                        source["weather_rain"] = f"{rain} mm"
                    source["weather_provenance"] = "EDGEIQ_VICTORIAN_TRACK_WEATHER_V1"
                    weather_enriched += 1

    payload["metadataEnrichedAt"] = datetime.now(timezone.utc).isoformat()
    CATALOG.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    audit = {
        "schema_version": "edgeiq_meetings_catalog_metadata_enrichment_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "meetings_seen": meetings_seen,
        "track_enriched": track_enriched,
        "rail_enriched": rail_enriched,
        "weather_enriched": weather_enriched,
        "fabricated_values": 0,
    }
    AUDIT.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print("EDGEIQ_MEETINGS_CATALOG_METADATA_ENRICHMENT_V1 PASS")
    print(f"MEETINGS_SEEN={meetings_seen}")
    print(f"TRACK_ENRICHED={track_enriched}")
    print(f"RAIL_ENRICHED={rail_enriched}")
    print(f"WEATHER_ENRICHED={weather_enriched}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
