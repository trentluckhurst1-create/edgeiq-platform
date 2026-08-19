from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "public" / "data" / "edgeiq_metropolitan_weather_v1.json"
SUMMARY = ROOT / "public" / "data" / "edgeiq_metropolitan_weather_v1_summary.txt"
RAW_DIR = ROOT / "data" / "weather-source-audit" / "live-vrc"

TURF_URL = "https://www.vrc.com.au/umbraco/api/TurfSportsAPI/GetTurfData"
WIND_URL = None

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-AU,en;q=0.9",
    "Referer": "https://www.vrc.com.au/track-and-weather-conditions/",
}


def first_value(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = data.get(key)

        if value is None:
            continue

        if isinstance(value, str):
            value = value.strip()

            if not value or value in {"-", "—"}:
                continue

        return value

    return None


def number_or_none(value: Any) -> float | None:
    if value is None:
        return None

    text = str(value).strip().lower()
    text = text.replace("mm", "").replace("%", "").replace("°c", "").replace("°", "")
    text = text.replace("km/h", "").strip()

    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def clean_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).replace("\r\n", "\n").replace("\r", "\n").strip()

    if not text or text in {"-", "—"}:
        return None

    return text


def extract_wind(payload: Any) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []

    if isinstance(payload, list):
        candidates = [row for row in payload if isinstance(row, dict)]

    elif isinstance(payload, dict):
        if isinstance(payload.get("data"), list):
            candidates = [
                row for row in payload["data"]
                if isinstance(row, dict)
            ]
        else:
            for key, value in payload.items():
                if isinstance(value, dict):
                    candidates.append({"station": key, **value})

    if not candidates:
        return {
            "wind_direction": None,
            "wind_speed_kmh": None,
            "wind_station": None,
            "wind_station_count": 0,
        }

    preferred = None

    for row in candidates:
        station_text = " ".join(
            str(row.get(key, ""))
            for key in ("station", "name", "location", "id")
        ).lower()

        if "straight" in station_text or "flemington" in station_text:
            preferred = row
            break

    selected = preferred or candidates[0]

    return {
        "wind_direction": clean_text(
            first_value(
                selected,
                "directionText",
                "direction_text",
                "directionName",
                "direction_name",
                "direction",
            )
        ),
        "wind_speed_kmh": number_or_none(
            first_value(
                selected,
                "speed",
                "windSpeed",
                "wind_speed",
                "speedKmh",
                "speed_kmh",
            )
        ),
        "wind_station": clean_text(
            first_value(
                selected,
                "station",
                "name",
                "location",
                "id",
            )
        ),
        "wind_station_count": len(candidates),
    }


def fetch_json(session: requests.Session, url: str) -> tuple[Any, int]:
    response = session.get(url, timeout=45)
    response.raise_for_status()
    return response.json(), response.status_code


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update(HEADERS)

    fetched_at = datetime.now(timezone.utc).isoformat()

    errors: list[str] = []
    turf_payload: Any = {}
    wind_payload: Any = {}
    turf_status = None
    wind_status = None

    try:
        turf_payload, turf_status = fetch_json(session, TURF_URL)
    except Exception as exc:
        errors.append(f"Turf data error: {exc}")

    wind_status = None
    wind_payload = {}

    (RAW_DIR / "vrc_turf_raw.json").write_text(
        json.dumps(turf_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    (RAW_DIR / "vrc_wind_raw.json").write_text(
        json.dumps(wind_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    content: dict[str, Any] = {}

    if isinstance(turf_payload, dict):
        candidate = turf_payload.get("content", turf_payload)

        if isinstance(candidate, dict):
            content = candidate

    going_report = clean_text(
        first_value(
            content,
            "going-report",
            "goingReport",
            "track-rating",
            "trackRating",
        )
    )

    if going_report in {"0", "0.0"}:
        going_report = None

    rail = clean_text(
        first_value(
            content,
            "rail-report",
            "railReport",
            "rail-position",
            "railPosition",
            "rail",
        )
    )

    going_stick = clean_text(
        first_value(
            content,
            "stick-report",
            "stickReport",
            "going-stick",
            "goingStick",
        )
    )

    temperature = number_or_none(
        first_value(
            content,
            "temperature-current",
            "temperatureCurrent",
            "temperature",
        )
    )

    rainfall_24h = number_or_none(
        first_value(
            content,
            "rain1-24hr",
            "rain2-24hr",
            "rain-24hr",
            "rain24hr",
            "rainfall24Hours",
        )
    )

    rainfall_today = number_or_none(
        first_value(
            content,
            "rain1-today",
            "rain2-today",
            "rainfallToday",
        )
    )

    rainfall_since = number_or_none(
        first_value(
            content,
            "rain1-since",
            "rain2-since",
            "rainfallSince",
        )
    )

    rainfall_current = number_or_none(
        first_value(
            content,
            "rain1-current",
            "rain2-current",
            "rainfallCurrent",
        )
    )

    rainfall_7day = number_or_none(
        first_value(
            content,
            "rain1-7day",
            "rain2-7day",
            "rainfall7Day",
        )
    )

    humidity = number_or_none(
        first_value(
            content,
            "humidity-current",
            "humidityCurrent",
            "humidity",
        )
    )

    moisture_loss = number_or_none(
        first_value(
            content,
            "et-24hr",
            "moisture-loss",
            "moistureLoss",
        )
    )

    irrigation = clean_text(
        first_value(
            content,
            "irrigation-report",
            "irrigationReport",
            "irrigation",
        )
    )

    weather_comment = clean_text(
        first_value(
            content,
            "weather-comment",
            "weatherComment",
            "weather",
        )
    )

    additional_comment = clean_text(
        first_value(
            content,
            "additional-comment",
            "additionalComment",
        )
    )

    wind = {
        "wind_direction": clean_text(
            first_value(
                content,
                "winddirection-text",
                "windDirectionText",
                "winddirection-current",
            )
        ),
        "wind_speed_kmh": number_or_none(
            first_value(
                content,
                "windspeed-current",
                "windSpeedCurrent",
                "windspeed-average",
            )
        ),
        "wind_average_kmh": number_or_none(
            first_value(
                content,
                "windspeed-average",
                "windSpeedAverage",
            )
        ),
        "wind_gust_kmh": number_or_none(
            first_value(
                content,
                "windgust-current",
                "windGustCurrent",
            )
        ),
        "wind_gust_event": clean_text(
            first_value(
                content,
                "windgust-event",
                "windGustEvent",
            )
        ),
        "wind_station": clean_text(
            first_value(
                content,
                "location-venue",
                "venueName",
                "stationId",
            )
        ),
        "wind_station_count": 1,
    }

    record = {
        "meeting_key": "FLEMINGTON",
        "meeting": "Flemington",
        "course": "Flemington",
        "provider": "VRC_TURFSPORTS",
        "source_name": "Victoria Racing Club",
        "source_url": "https://www.vrc.com.au/track-and-weather-conditions/",
        "fetched_at_utc": fetched_at,
        "source_observed_date": clean_text(
            first_value(
                content,
                "weather-date",
                "location-date",
            )
        ),
        "source_observed_time": clean_text(
            first_value(
                content,
                "weather-last-update",
            )
        ),
        "station_status": clean_text(
            first_value(
                content,
                "stationActivityStatus",
            )
        ),
        "source_status": "LIVE" if content else "UNAVAILABLE",
        "official_track_rating": going_report,
        "official_rail": rail,
        "going_stick": going_stick,
        "temperature_c": temperature,
        "rainfall_24h_mm": rainfall_24h,
        "rainfall_since_9am_mm": rainfall_since,
        "rainfall_today_mm": rainfall_today,
        "rainfall_current_mm": rainfall_current,
        "rainfall_7day_mm": rainfall_7day,
        "forecast_rainfall": None,
        "humidity_pct": humidity,
        "moisture_loss_mm": moisture_loss,
        "soil_moisture": None,
        "irrigation": irrigation,
        "weather_comment": weather_comment,
        "additional_comment": additional_comment,
        "wind_direction": wind["wind_direction"],
        "wind_speed_kmh": wind["wind_speed_kmh"],
        "wind_average_kmh": wind["wind_average_kmh"],
        "wind_gust_kmh": wind["wind_gust_kmh"],
        "wind_gust_event": wind["wind_gust_event"],
        "wind_station": wind["wind_station"],
        "wind_station_count": wind["wind_station_count"],
        "turf_http_status": turf_status,
        "wind_http_status": wind_status,
        "errors": errors,
    }

    output_payload = {
        "schema_version": "edgeiq_metropolitan_weather_v1",
        "generated_at_utc": fetched_at,
        "records": [record],
    }

    OUTPUT.write_text(
        json.dumps(output_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    populated = [
        key
        for key, value in record.items()
        if value is not None and value != "" and value != [] and value != {}
    ]

    summary_lines = [
        "EDGEIQ METROPOLITAN WEATHER V1",
        "================================",
        "",
        f"Generated: {fetched_at}",
        f"Provider: {record['provider']}",
        f"Meeting: {record['meeting']}",
        f"Source status: {record['source_status']}",
        f"Source observed date: {record['source_observed_date']}",
        f"Source observed time: {record['source_observed_time']}",
        f"Station status: {record['station_status']}",
        f"Turf HTTP status: {turf_status}",
        f"Wind HTTP status: {wind_status}",
        f"Populated fields: {len(populated)}",
        f"Errors: {len(errors)}",
        "",
        "NORMALISED VALUES",
        "-----------------",
        f"Official track rating: {record['official_track_rating']}",
        f"Official rail: {record['official_rail']}",
        f"GoingStick: {record['going_stick']}",
        f"Temperature C: {record['temperature_c']}",
        f"Rainfall 24h mm: {record['rainfall_24h_mm']}",
        f"Rainfall today mm: {record['rainfall_today_mm']}",
        f"Rainfall since mm: {record['rainfall_since_9am_mm']}",
        f"Rainfall current mm: {record['rainfall_current_mm']}",
        f"Rainfall 7 day mm: {record['rainfall_7day_mm']}",
        f"Humidity %: {record['humidity_pct']}",
        f"Moisture loss mm: {record['moisture_loss_mm']}",
        f"Irrigation: {record['irrigation']}",
        f"Weather comment: {record['weather_comment']}",
        f"Wind direction: {record['wind_direction']}",
        f"Wind speed km/h: {record['wind_speed_kmh']}",
        f"Wind average km/h: {record['wind_average_kmh']}",
        f"Wind gust km/h: {record['wind_gust_kmh']}",
        f"Wind gust time: {record['wind_gust_event']}",
        "",
        "PRODUCT GOVERNANCE",
        "------------------",
        "Official source values only.",
        "No projected future track rating.",
        "No inferred steward decision.",
    ]

    if errors:
        summary_lines.extend(["", "ERRORS", "------", *errors])

    SUMMARY.write_text("\n".join(summary_lines), encoding="utf-8")

    print("[EDGEIQ] VRC weather feed built")
    print(f"[EDGEIQ] Output: {OUTPUT}")
    print(f"[EDGEIQ] Source status: {record['source_status']}")
    print(f"[EDGEIQ] Track rating: {record['official_track_rating']}")
    print(f"[EDGEIQ] Rainfall 24h: {record['rainfall_24h_mm']}")
    print(f"[EDGEIQ] Temperature: {record['temperature_c']}")
    print(f"[EDGEIQ] Humidity: {record['humidity_pct']}")
    print(f"[EDGEIQ] Errors: {len(errors)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())




