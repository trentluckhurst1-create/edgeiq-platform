from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]

VRC_BUILDER = ROOT / "scripts" / "build_edgeiq_metropolitan_weather_v1.py"

OUTPUT = ROOT / "public" / "data" / "edgeiq_metropolitan_weather_v1.json"
SUMMARY = ROOT / "public" / "data" / "edgeiq_metropolitan_weather_v1_summary.txt"

RAW_DIR = (
    ROOT
    / "data"
    / "weather-source-audit"
    / "live-turftrax"
)

RAW_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

TURFTRAX_CLIENTS = {
    "CAULFIELD": {
        "client": "caulfield",
        "meeting": "Caulfield",
        "course": "Caulfield",
        "source_url": (
            "https://its.turftrax.co.uk/"
            "visualiser/caulfield/"
        ),
    },
    "SANDOWN": {
        "client": "ladbrokes",
        "meeting": "Sandown",
        "course": "Sandown",
        "source_url": (
            "https://its.turftrax.co.uk/"
            "visualiser/ladbrokes/"
        ),
    },
    "MORNINGTON": {
        "client": "mornington",
        "meeting": "Mornington",
        "course": "Mornington",
        "source_url": (
            "https://its.turftrax.co.uk/"
            "visualiser/mornington/"
        ),
    },
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-AU,en;q=0.9",
}


def clean_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).replace("\r\n", "\n").replace("\r", "\n").strip()

    if not text:
        return None

    if text.lower() in {
        "-",
        "—",
        "n/a",
        "na",
        "none",
        "null",
        "undefined",
    }:
        return None

    return text


def number_or_none(value: Any) -> float | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()

    if not text:
        return None

    text = text.replace("*", "")
    text = text.replace(",", "")
    text = re.sub(
        r"(?i)(mm|km/h|kph|°c|c|%)",
        "",
        text,
    ).strip()

    match = re.search(r"-?\d+(?:\.\d+)?", text)

    if not match:
        return None

    try:
        return float(match.group(0))
    except ValueError:
        return None


def first_value(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key not in data:
            continue

        value = data.get(key)

        if value is None:
            continue

        if isinstance(value, str) and not value.strip():
            continue

        return value

    return None


def rainfall_value(
    content: dict[str, Any],
    manual_key: str,
    primary_key: str,
    secondary_key: str,
) -> float | None:
    have_manual = bool(content.get("haveManualRain"))

    if have_manual:
        manual_value = number_or_none(content.get(manual_key))

        if manual_value is not None:
            return manual_value

    primary_value = number_or_none(content.get(primary_key))

    if primary_value is not None:
        return primary_value

    return number_or_none(content.get(secondary_key))


def fetch_turftrax(
    session: requests.Session,
    meeting_key: str,
    config: dict[str, str],
    fetched_at: str,
) -> dict[str, Any]:
    client = config["client"]

    endpoint = (
        "https://its.turftrax.co.uk/"
        f"visualiser/stream/{client}.html"
    )

    errors: list[str] = []

    status_code: int | None = None
    payload: dict[str, Any] = {}

    try:
        response = session.get(
            endpoint,
            timeout=45,
            headers={
                "Referer": config["source_url"],
            },
        )

        status_code = response.status_code
        response.raise_for_status()

        raw = response.json()

        if isinstance(raw, dict):
            payload = raw

    except Exception as exc:
        errors.append(str(exc))

    raw_path = RAW_DIR / f"{client}_raw.json"

    raw_path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    api_status = payload.get("status")

    nested_payload = payload.get("payload", {})

    if not isinstance(nested_payload, dict):
        nested_payload = {}

    header = nested_payload.get("header", {})

    if not isinstance(header, dict):
        header = {}

    content = nested_payload.get("content", {})

    if not isinstance(content, dict):
        content = {}

    tardis = nested_payload.get("tardis", {})

    if not isinstance(tardis, dict):
        tardis = {}

    local_time = tardis.get("local-time", {})

    if not isinstance(local_time, dict):
        local_time = {}

    official_track_rating = clean_text(
        first_value(
            content,
            "going-report",
            "official-going",
            "goingReportText",
        )
    )

    official_rail = clean_text(
        first_value(
            content,
            "rail-report",
            "rails",
            "railReport",
        )
    )

    going_stick = clean_text(
        first_value(
            content,
            "stick-report",
            "stickReport",
            "going-stick",
        )
    )

    temperature = number_or_none(
        first_value(
            content,
            "air-temperature-current",
            "temperature-current",
            "temperature",
        )
    )

    rainfall_24h = rainfall_value(
        content,
        "rain0-24hr",
        "rain1-24hr",
        "rain2-24hr",
    )

    rainfall_today = rainfall_value(
        content,
        "rain0-today",
        "rain1-today",
        "rain2-today",
    )

    rainfall_7day = rainfall_value(
        content,
        "rain0-7day",
        "rain1-7day",
        "rain2-7day",
    )

    rainfall_since = number_or_none(
        first_value(
            content,
            "rain1-since",
            "rain2-since",
        )
    )

    rainfall_current = number_or_none(
        first_value(
            content,
            "rain1-current",
            "rain2-current",
        )
    )

    record = {
        "meeting_key": meeting_key,
        "meeting": config["meeting"],
        "course": config["course"],

        "provider": "TURFTRAX_WDV",
        "source_name": "TurfTrax",
        "source_url": config["source_url"],
        "source_endpoint": endpoint,

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

        "source_observed_datetime": clean_text(
            local_time.get("calendar")
        ),

        "station_status": clean_text(
            content.get("stationActivityStatus")
        ),

        "source_status": (
            "LIVE"
            if (
                status_code == 200
                and api_status == 0
                and bool(content)
            )
            else "UNAVAILABLE"
        ),

        "official_track_rating": official_track_rating,
        "official_track_rating_updated": clean_text(
            content.get("going-report-date")
        ),

        "official_rail": official_rail,
        "going_stick": going_stick,

        "temperature_c": temperature,

        "temperature_min_c": number_or_none(
            first_value(
                content,
                "air-temperature-min",
                "temperature-min",
            )
        ),

        "temperature_max_c": number_or_none(
            first_value(
                content,
                "air-temperature-max",
                "temperature-max",
            )
        ),

        "rainfall_24h_mm": rainfall_24h,
        "rainfall_since_9am_mm": rainfall_since,
        "rainfall_today_mm": rainfall_today,
        "rainfall_current_mm": rainfall_current,
        "rainfall_7day_mm": rainfall_7day,

        "forecast_rainfall": None,

        "humidity_pct": number_or_none(
            content.get("humidity-current")
        ),

        "humidity_min_pct": number_or_none(
            content.get("humidity-min")
        ),

        "humidity_max_pct": number_or_none(
            content.get("humidity-max")
        ),

        "moisture_loss_mm": number_or_none(
            content.get("et-24hr")
        ),

        "moisture_loss_7day_mm": number_or_none(
            content.get("et-7day")
        ),

        "soil_moisture": None,

        "irrigation": clean_text(
            content.get("irrigation-report")
        ),

        "weather_comment": clean_text(
            content.get("weather-comment")
        ),

        "additional_comment": clean_text(
            content.get("additional-comment")
        ),

        "wind_direction": clean_text(
            first_value(
                content,
                "winddirection-text",
                "winddirection-current",
            )
        ),

        "wind_direction_degrees": number_or_none(
            content.get("winddirection-current")
        ),

        "wind_speed_kmh": number_or_none(
            content.get("windspeed-current")
        ),

        "wind_average_kmh": number_or_none(
            content.get("windspeed-average")
        ),

        "wind_gust_kmh": number_or_none(
            content.get("windgust-current")
        ),

        "wind_gust_max_kmh": number_or_none(
            content.get("windgust-max")
        ),

        "wind_gust_event": clean_text(
            content.get("windgust-event")
        ),

        "wind_station": clean_text(
            first_value(
                content,
                "venueName",
                "location-venue",
            )
        ),

        "wind_station_count": 1,

        "meeting_date": clean_text(
            first_value(
                content,
                "location-date",
                "going-race-date",
            )
        ),

        "meeting_title": clean_text(
            content.get("location-title")
        ),

        "station_id": content.get("stationId"),
        "station_type": clean_text(
            content.get("stationType")
        ),

        "venue_id": content.get("venueId"),

        "report_id": clean_text(
            content.get("usingReport")
        ),

        "going_waypoint_map": clean_text(
            content.get("going-waypoint-map")
        ),

        "going_zone_map": clean_text(
            content.get("going-zone-map")
        ),

        "provider_description": clean_text(
            header.get("description")
        ),

        "provider_signature": clean_text(
            header.get("signature")
        ),

        "turf_http_status": status_code,
        "wind_http_status": status_code,
        "api_status": api_status,

        "errors": errors,
    }

    return record


def run_vrc_builder() -> dict[str, Any]:
    if not VRC_BUILDER.exists():
        raise FileNotFoundError(
            f"VRC builder not found: {VRC_BUILDER}"
        )

    result = subprocess.run(
        [
            sys.executable,
            str(VRC_BUILDER),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )

    if result.stdout:
        print(result.stdout.rstrip())

    if result.returncode != 0:
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr)

        raise RuntimeError(
            "Existing VRC weather builder failed."
        )

    if not OUTPUT.exists():
        raise FileNotFoundError(
            f"VRC builder did not create: {OUTPUT}"
        )

    return json.loads(
        OUTPUT.read_text(
            encoding="utf-8",
        )
    )


def main() -> int:
    fetched_at = datetime.now(
        timezone.utc
    ).isoformat()

    print("[EDGEIQ] Refreshing VRC provider")

    base_feed = run_vrc_builder()

    vrc_records = base_feed.get("records", [])

    if not isinstance(vrc_records, list):
        vrc_records = []

    session = requests.Session()
    session.headers.update(HEADERS)

    turftrax_records: list[dict[str, Any]] = []

    for meeting_key, config in TURFTRAX_CLIENTS.items():
        print(
            f"[EDGEIQ] Refreshing TurfTrax provider: "
            f"{meeting_key}"
        )

        record = fetch_turftrax(
            session,
            meeting_key,
            config,
            fetched_at,
        )

        turftrax_records.append(record)

        print(
            f"[EDGEIQ] {meeting_key}: "
            f"{record['source_status']} | "
            f"{record['official_track_rating']} | "
            f"{record['temperature_c']} C | "
            f"{record['rainfall_24h_mm']} mm"
        )

    records = [
        *vrc_records,
        *turftrax_records,
    ]

    provider_registry = {
        "FLEMINGTON": "VRC_TURFSPORTS",
        "CAULFIELD": "TURFTRAX_WDV",
        "SANDOWN": "TURFTRAX_WDV",
        "MORNINGTON": "TURFTRAX_WDV",
    }

    output_payload = {
        "schema_version": (
            "edgeiq_metropolitan_weather_v2"
        ),
        "generated_at_utc": fetched_at,
        "provider_registry": provider_registry,
        "records": records,
    }

    OUTPUT.write_text(
        json.dumps(
            output_payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summary_lines = [
        "EDGEIQ METROPOLITAN WEATHER PROVIDER REGISTRY",
        "=" * 52,
        "",
        f"Generated: {fetched_at}",
        f"Records: {len(records)}",
        "",
        "PROVIDER REGISTRY",
        "-----------------",
    ]

    for meeting_key, provider in provider_registry.items():
        summary_lines.append(
            f"{meeting_key}: {provider}"
        )

    summary_lines.extend(
        [
            "",
            "NORMALISED RECORDS",
            "------------------",
        ]
    )

    for record in records:
        summary_lines.extend(
            [
                "",
                f"Meeting: {record.get('meeting')}",
                f"Provider: {record.get('provider')}",
                f"Status: {record.get('source_status')}",
                (
                    "Official track rating: "
                    f"{record.get('official_track_rating')}"
                ),
                (
                    "Official rail: "
                    f"{record.get('official_rail')}"
                ),
                (
                    "GoingStick: "
                    f"{record.get('going_stick')}"
                ),
                (
                    "Temperature C: "
                    f"{record.get('temperature_c')}"
                ),
                (
                    "Rainfall 24h mm: "
                    f"{record.get('rainfall_24h_mm')}"
                ),
                (
                    "Rainfall today mm: "
                    f"{record.get('rainfall_today_mm')}"
                ),
                (
                    "Rainfall 7 day mm: "
                    f"{record.get('rainfall_7day_mm')}"
                ),
                (
                    "Humidity %: "
                    f"{record.get('humidity_pct')}"
                ),
                (
                    "Wind: "
                    f"{record.get('wind_direction')} "
                    f"{record.get('wind_speed_kmh')} km/h"
                ),
                (
                    "Observed: "
                    f"{record.get('source_observed_date')} "
                    f"{record.get('source_observed_time')}"
                ),
                (
                    "Errors: "
                    f"{len(record.get('errors', []))}"
                ),
            ]
        )

    summary_lines.extend(
        [
            "",
            "PRODUCT GOVERNANCE",
            "------------------",
            "Official source observations only.",
            "Forecasts remain clearly labelled.",
            "No projected future track rating.",
            "No inferred steward decision.",
        ]
    )

    SUMMARY.write_text(
        "\n".join(summary_lines),
        encoding="utf-8",
    )

    unavailable = [
        record.get("meeting")
        for record in records
        if record.get("source_status") != "LIVE"
    ]

    print()
    print("[EDGEIQ] Metropolitan weather registry built")
    print(f"[EDGEIQ] Output: {OUTPUT}")
    print(f"[EDGEIQ] Records: {len(records)}")
    print(
        f"[EDGEIQ] Unavailable providers: "
        f"{len(unavailable)}"
    )

    if unavailable:
        print(
            "[EDGEIQ] Unavailable: "
            + ", ".join(str(item) for item in unavailable)
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
