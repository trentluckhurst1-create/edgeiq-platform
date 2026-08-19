from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]

OUTPUT = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_vic_bom_observations_v1.json"
)

SUMMARY = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_vic_bom_observations_v1_summary.txt"
)

AUDIT = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_vic_bom_observations_v1_audit.txt"
)

RAW_DIR = (
    ROOT
    / "data"
    / "weather-source-audit"
    / "bom-live"
)

STATIONS = {
    "GEELONG": {
        "station_id": "87184",
        "official_station_id": "087184",
        "meeting": "Geelong",
        "expected_station_name": "Geelong Racecourse",
    },
    "BALLARAT": {
        "station_id": "89002",
        "official_station_id": "089002",
        "meeting": "Ballarat",
        "expected_station_name": "Ballarat",
    },
    "HAMILTON": {
        "station_id": "90173",
        "official_station_id": "090173",
        "meeting": "Hamilton",
        "expected_station_name": "Hamilton",
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
    "Origin": "https://www.bom.gov.au",
}


def get_path(
    payload: dict[str, Any],
    path: str,
) -> Any:
    current: Any = payload

    for part in path.split("."):
        if not isinstance(current, dict):
            return None

        if part not in current:
            return None

        current = current[part]

    return current


def number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def text(value: Any) -> str | None:
    if value is None:
        return None

    cleaned = str(value).strip()

    if not cleaned:
        return None

    return cleaned


def mps_to_kmh(value: Any) -> float | None:
    numeric = number(value)

    if numeric is None:
        return None

    return round(numeric * 3.6, 1)


def plausible(
    value: float | None,
    minimum: float,
    maximum: float,
) -> float | None:
    if value is None:
        return None

    if value < minimum or value > maximum:
        return None

    return value


def fetch_station(
    meeting_key: str,
    config: dict[str, str],
) -> dict[str, Any]:
    station_id = config["station_id"]

    endpoint = (
        "https://api.bom.gov.au/apikey/v1/"
        f"observations/latest/{station_id}/atm/surf_air"
    )

    page_url = (
        "https://www.bom.gov.au/weatherstation/"
        f"australia/victoria/{station_id}"
    )

    station_dir = RAW_DIR / station_id
    station_dir.mkdir(parents=True, exist_ok=True)

    status_code: int | None = None
    errors: list[str] = []
    payload: dict[str, Any] = {}

    try:
        response = requests.get(
            endpoint,
            params={
                "include_qc_results": "false",
            },
            headers={
                **HEADERS,
                "Referer": page_url,
            },
            timeout=45,
        )

        status_code = response.status_code
        response.raise_for_status()

        raw = response.json()

        if isinstance(raw, dict):
            payload = raw

    except Exception as exc:
        errors.append(str(exc))

    raw_path = station_dir / "latest_raw.json"

    raw_path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    station_name = text(
        get_path(
            payload,
            "stn.identity.bom_stn_name",
        )
    )

    observed = text(
        get_path(
            payload,
            "obs.datetime_utc",
        )
    )

    temperature = plausible(
        number(
            get_path(
                payload,
                "obs.temp.dry_bulb_1min_cel",
            )
        ),
        -20.0,
        55.0,
    )

    apparent_temperature = plausible(
        number(
            get_path(
                payload,
                "obs.temp.apparent_1min_cel",
            )
        ),
        -30.0,
        60.0,
    )

    minimum_temperature = plausible(
        number(
            get_path(
                payload,
                "obs.temp.dry_bulb_min_cel",
            )
        ),
        -30.0,
        55.0,
    )

    maximum_temperature = plausible(
        number(
            get_path(
                payload,
                "obs.temp.dry_bulb_max_cel",
            )
        ),
        -20.0,
        60.0,
    )

    humidity = plausible(
        number(
            get_path(
                payload,
                "obs.temp.rel_hum_percent",
            )
        ),
        0.0,
        100.0,
    )

    dew_point = plausible(
        number(
            get_path(
                payload,
                "obs.temp.dew_pnt_1min_cel",
            )
        ),
        -30.0,
        40.0,
    )

    rainfall_since_9am = plausible(
        number(
            get_path(
                payload,
                "obs.precip.since_0900lct_total_mm",
            )
        ),
        0.0,
        1000.0,
    )

    rainfall_since_midnight = plausible(
        number(
            get_path(
                payload,
                "obs.precip.since_0000lct_total_mm",
            )
        ),
        0.0,
        1000.0,
    )

    rainfall_10min = plausible(
        number(
            get_path(
                payload,
                "obs.precip.10min_total_mm",
            )
        ),
        0.0,
        500.0,
    )

    rainfall_1h = plausible(
        number(
            get_path(
                payload,
                "obs.precip.1h_total_mm",
            )
        ),
        0.0,
        500.0,
    )

    rainfall_24h = plausible(
        number(
            get_path(
                payload,
                "obs.precip.24h_0900lct_total_mm",
            )
        ),
        0.0,
        1000.0,
    )

    wind_direction = text(
        get_path(
            payload,
            "obs.wind.dirn_10m_ord",
        )
    )

    wind_speed = plausible(
        mps_to_kmh(
            get_path(
                payload,
                "obs.wind.speed_10m_mps",
            )
        ),
        0.0,
        300.0,
    )

    wind_gust = plausible(
        mps_to_kmh(
            get_path(
                payload,
                "obs.wind.gust_speed_10m_mps",
            )
        ),
        0.0,
        400.0,
    )

    wind_gust_max = plausible(
        mps_to_kmh(
            get_path(
                payload,
                "obs.wind.gust_speed_10m_max_mps",
            )
        ),
        0.0,
        400.0,
    )

    latitude = number(
        get_path(
            payload,
            "stn.location.lat_dec_deg",
        )
    )

    longitude = number(
        get_path(
            payload,
            "stn.location.long_dec_deg",
        )
    )

    populated_core = sum(
        value is not None
        for value in (
            observed,
            temperature,
            humidity,
            rainfall_since_9am,
            wind_direction,
            wind_speed,
        )
    )

    source_live = (
        status_code == 200
        and bool(payload)
        and populated_core >= 3
    )

    if station_name:
        expected = config["expected_station_name"].upper()

        if expected not in station_name.upper():
            errors.append(
                "Station identity mismatch: "
                f"expected {config['expected_station_name']}, "
                f"received {station_name}"
            )

    return {
        "meeting_key": meeting_key,
        "meeting": config["meeting"],

        "provider": "BOM_OBSERVATIONS",
        "source_name": "Bureau of Meteorology",
        "source_url": page_url,
        "source_endpoint": (
            f"{endpoint}?include_qc_results=false"
        ),

        "station_id": station_id,
        "official_station_id": config[
            "official_station_id"
        ],
        "station_name": station_name,
        "station_status": (
            "ACTIVE"
            if source_live
            else "UNAVAILABLE"
        ),

        "fetched_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "source_observed_datetime": observed,
        "source_status": (
            "LIVE"
            if source_live
            else "UNAVAILABLE"
        ),

        "temperature_c": temperature,
        "apparent_temperature_c": (
            apparent_temperature
        ),
        "temperature_min_c": minimum_temperature,
        "temperature_max_c": maximum_temperature,

        "humidity_pct": humidity,
        "dew_point_c": dew_point,

        "rainfall_since_9am_mm": (
            rainfall_since_9am
        ),
        "rainfall_since_midnight_mm": (
            rainfall_since_midnight
        ),
        "rainfall_current_mm": rainfall_10min,
        "rainfall_1h_mm": rainfall_1h,
        "rainfall_24h_mm": rainfall_24h,

        "wind_direction": wind_direction,
        "wind_speed_kmh": wind_speed,
        "wind_gust_kmh": wind_gust,
        "wind_gust_max_kmh": wind_gust_max,

        "pressure_hpa": None,

        "latitude": latitude,
        "longitude": longitude,

        "http_status": status_code,
        "core_fields_populated": populated_core,
        "errors": errors,
    }


records = [
    fetch_station(meeting_key, config)
    for meeting_key, config in STATIONS.items()
]

payload = {
    "schema_version": (
        "edgeiq_vic_bom_observations_v1"
    ),
    "generated_at_utc": datetime.now(
        timezone.utc
    ).isoformat(),
    "records": records,
}

OUTPUT.write_text(
    json.dumps(
        payload,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

summary_lines = [
    "EDGEIQ VICTORIAN BOM OBSERVATIONS V1",
    "=" * 45,
    "",
]

audit_lines = [
    "EDGEIQ VICTORIAN BOM OBSERVATION AUDIT",
    "=" * 48,
    "",
]

for record in records:
    summary_lines.extend(
        [
            f"Meeting: {record['meeting']}",
            f"Station: {record['station_name']}",
            f"Station ID: {record['station_id']}",
            f"Official ID: {record['official_station_id']}",
            f"Status: {record['source_status']}",
            f"Observed: {record['source_observed_datetime']}",
            f"Temperature C: {record['temperature_c']}",
            (
                "Apparent temperature C: "
                f"{record['apparent_temperature_c']}"
            ),
            (
                "Temperature range C: "
                f"{record['temperature_min_c']} to "
                f"{record['temperature_max_c']}"
            ),
            f"Humidity %: {record['humidity_pct']}",
            f"Dew point C: {record['dew_point_c']}",
            (
                "Rain since 9am mm: "
                f"{record['rainfall_since_9am_mm']}"
            ),
            (
                "Rain 24h mm: "
                f"{record['rainfall_24h_mm']}"
            ),
            (
                "Rain 10min mm: "
                f"{record['rainfall_current_mm']}"
            ),
            (
                "Wind: "
                f"{record['wind_direction']} "
                f"{record['wind_speed_kmh']} km/h"
            ),
            (
                "Wind gust: "
                f"{record['wind_gust_kmh']} km/h"
            ),
            (
                "Maximum gust: "
                f"{record['wind_gust_max_kmh']} km/h"
            ),
            f"Errors: {len(record['errors'])}",
            "",
        ]
    )

    audit_lines.extend(
        [
            f"{record['meeting_key']}",
            f"  HTTP: {record['http_status']}",
            f"  Status: {record['source_status']}",
            (
                "  Core fields: "
                f"{record['core_fields_populated']}"
            ),
            f"  Station: {record['station_name']}",
            f"  Temperature: {record['temperature_c']}",
            f"  Humidity: {record['humidity_pct']}",
            (
                "  Wind: "
                f"{record['wind_direction']} "
                f"{record['wind_speed_kmh']}"
            ),
            (
                "  Rain since 9am: "
                f"{record['rainfall_since_9am_mm']}"
            ),
            f"  Errors: {record['errors']}",
            "",
        ]
    )

summary_lines.extend(
    [
        "PRODUCT GOVERNANCE",
        "------------------",
        "Official BOM observations only.",
        "Exact BOM schema paths only.",
        "Wind converted from m/s to km/h.",
        "Missing station readings remain unavailable.",
        "No track-condition inference.",
        "No projected official track rating.",
    ]
)

SUMMARY.write_text(
    "\n".join(summary_lines),
    encoding="utf-8",
)

AUDIT.write_text(
    "\n".join(audit_lines),
    encoding="utf-8",
)

print("[EDGEIQ] Exact-schema BOM registry built")

for record in records:
    print(
        f"[EDGEIQ] {record['meeting_key']}: "
        f"{record['source_status']} | "
        f"{record['temperature_c']} C | "
        f"{record['humidity_pct']}% | "
        f"{record['wind_direction']} "
        f"{record['wind_speed_kmh']} km/h | "
        f"rain {record['rainfall_since_9am_mm']} mm"
    )

print(f"[EDGEIQ] Output: {OUTPUT}")

