from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests

ROOT = Path(__file__).resolve().parents[1]

AUDIT_DIR = (
    ROOT
    / "data"
    / "weather-source-audit"
    / "bom-live"
    / "87184"
    / "qc-probe"
)

AUDIT_DIR.mkdir(parents=True, exist_ok=True)

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

SCHEMA_AUDIT = (
    AUDIT_DIR
    / "EDGEIQ_BOM_87184_SCHEMA_AUDIT.txt"
)

STATION_ID = "87184"

LATEST_BASE = (
    "https://api.bom.gov.au/"
    "apikey/v1/observations/"
    f"latest/{STATION_ID}/atm/surf_air"
)

RECENT_BASE = (
    "https://api.bom.gov.au/"
    "apikey/v1/observations/"
    f"recent/{STATION_ID}/atm/surf_air"
)

PAGE_URL = (
    "https://www.bom.gov.au/"
    f"weatherstation/australia/victoria/{STATION_ID}"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-AU,en;q=0.9",
    "Referer": PAGE_URL,
    "Origin": "https://www.bom.gov.au",
}

PROBES = [
    (
        "latest_qc_false",
        LATEST_BASE,
        {"include_qc_results": "false"},
    ),
    (
        "latest_qc_true",
        LATEST_BASE,
        {"include_qc_results": "true"},
    ),
    (
        "recent_qc_false",
        RECENT_BASE,
        {"include_qc_results": "false"},
    ),
    (
        "recent_qc_true",
        RECENT_BASE,
        {"include_qc_results": "true"},
    ),
]

session = requests.Session()
session.headers.update(HEADERS)


def clean_text(value: Any) -> str | None:
    if value is None:
        return None

    text = re.sub(r"\s+", " ", str(value)).strip()

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

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = clean_text(value)

    if not text:
        return None

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        text.replace(",", ""),
    )

    if not match:
        return None

    try:
        return float(match.group(0))
    except ValueError:
        return None


def flatten(
    value: Any,
    prefix: str = "",
) -> dict[str, Any]:
    output: dict[str, Any] = {}

    if isinstance(value, dict):
        for key, child in value.items():
            next_prefix = (
                f"{prefix}.{key}"
                if prefix
                else str(key)
            )

            output.update(
                flatten(child, next_prefix)
            )

    elif isinstance(value, list):
        for index, child in enumerate(value):
            next_prefix = (
                f"{prefix}[{index}]"
                if prefix
                else f"[{index}]"
            )

            output.update(
                flatten(child, next_prefix)
            )

    else:
        output[prefix] = value

    return output


def first_matching(
    flattened: dict[str, Any],
    exact_names: Iterable[str],
    contains_names: Iterable[str] = (),
) -> Any:
    exact_set = {
        name.lower()
        for name in exact_names
    }

    for path, value in flattened.items():
        leaf = (
            path.rsplit(".", 1)[-1]
            .split("[", 1)[0]
            .lower()
        )

        if leaf in exact_set:
            cleaned = clean_text(value)

            if cleaned is not None:
                return value

    for path, value in flattened.items():
        lower_path = path.lower()

        if any(
            marker.lower() in lower_path
            for marker in contains_names
        ):
            cleaned = clean_text(value)

            if cleaned is not None:
                return value

    return None


def save_probe(
    label: str,
    url: str,
    params: dict[str, str],
) -> dict[str, Any]:
    print(f"[EDGEIQ] BOM request: {label}")

    record: dict[str, Any] = {
        "label": label,
        "url": url,
        "params": params,
    }

    try:
        response = session.get(
            url,
            params=params,
            timeout=45,
            allow_redirects=True,
        )

        content_type = response.headers.get(
            "content-type",
            "",
        )

        record.update(
            {
                "status": response.status_code,
                "final_url": response.url,
                "content_type": content_type,
                "bytes": len(response.content),
            }
        )

        raw_path = AUDIT_DIR / f"{label}.json"

        raw_path.write_text(
            response.text,
            encoding="utf-8",
            errors="ignore",
        )

        record["raw_path"] = str(
            raw_path.relative_to(ROOT)
        )

        try:
            payload = response.json()
            record["payload"] = payload
            record["json"] = True

            parsed_path = (
                AUDIT_DIR
                / f"{label}_parsed.json"
            )

            parsed_path.write_text(
                json.dumps(
                    payload,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            record["parsed_path"] = str(
                parsed_path.relative_to(ROOT)
            )

        except Exception:
            record["payload"] = None
            record["json"] = False

    except Exception as exc:
        record["error"] = str(exc)

    return record


probe_results = [
    save_probe(label, url, params)
    for label, url, params in PROBES
]

(
    AUDIT_DIR
    / "bom_qc_probe_results.json"
).write_text(
    json.dumps(
        [
            {
                key: value
                for key, value in record.items()
                if key != "payload"
            }
            for record in probe_results
        ],
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

successful = [
    record
    for record in probe_results
    if record.get("status") == 200
    and record.get("json")
    and isinstance(record.get("payload"), (dict, list))
]

if not successful:
    raise RuntimeError(
        "No BOM JSON observation request returned HTTP 200. "
        "Inspect bom_qc_probe_results.json."
    )

latest_record = next(
    (
        record
        for record in successful
        if record["label"] == "latest_qc_false"
    ),
    successful[0],
)

latest_payload = latest_record["payload"]
latest_flat = flatten(latest_payload)

recent_record = next(
    (
        record
        for record in successful
        if record["label"] == "recent_qc_false"
    ),
    None,
)

recent_payload = (
    recent_record["payload"]
    if recent_record
    else None
)

station_name = clean_text(
    first_matching(
        latest_flat,
        (
            "station_name",
            "stationName",
            "name",
            "station",
        ),
        (
            "station.name",
            "station_name",
        ),
    )
)

observation_time = clean_text(
    first_matching(
        latest_flat,
        (
            "time",
            "datetime",
            "date_time",
            "observation_time",
            "local_date_time",
            "localDateTime",
            "utc_date_time",
            "utcDateTime",
        ),
        (
            "observation.time",
            "observation_time",
            "local_date_time",
        ),
    )
)

temperature = number_or_none(
    first_matching(
        latest_flat,
        (
            "air_temperature",
            "airTemperature",
            "temperature",
            "temp",
        ),
        (
            "air_temperature",
            "airtemperature",
        ),
    )
)

apparent_temperature = number_or_none(
    first_matching(
        latest_flat,
        (
            "apparent_temperature",
            "apparentTemperature",
            "feels_like",
            "feelsLike",
        ),
        (
            "apparent_temperature",
            "feels_like",
        ),
    )
)

humidity = number_or_none(
    first_matching(
        latest_flat,
        (
            "relative_humidity",
            "relativeHumidity",
            "humidity",
        ),
        (
            "relative_humidity",
        ),
    )
)

dew_point = number_or_none(
    first_matching(
        latest_flat,
        (
            "dew_point",
            "dewPoint",
            "dew_point_temperature",
            "dewPointTemperature",
        ),
        (
            "dew_point",
        ),
    )
)

rain_since_9am = number_or_none(
    first_matching(
        latest_flat,
        (
            "rain_since_9am",
            "rainSince9am",
            "rainfall_since_9am",
            "rainfallSince9am",
        ),
        (
            "rain_since_9",
            "rainfall_since_9",
        ),
    )
)

rain_last_hour = number_or_none(
    first_matching(
        latest_flat,
        (
            "rainfall",
            "rain",
            "rain_last_hour",
            "rainLastHour",
        ),
        (
            "rainfall",
        ),
    )
)

wind_direction = clean_text(
    first_matching(
        latest_flat,
        (
            "wind_direction",
            "windDirection",
            "wind_dir",
            "windDir",
        ),
        (
            "wind_direction",
        ),
    )
)

wind_speed = number_or_none(
    first_matching(
        latest_flat,
        (
            "wind_speed_kilometre",
            "wind_speed_kmh",
            "windSpeedKmh",
            "wind_speed",
            "windSpeed",
        ),
        (
            "wind_speed",
        ),
    )
)

wind_gust = number_or_none(
    first_matching(
        latest_flat,
        (
            "gust_speed_kilometre",
            "wind_gust_kmh",
            "windGustKmh",
            "gust",
            "gust_speed",
            "gustSpeed",
        ),
        (
            "gust_speed",
            "wind_gust",
        ),
    )
)

pressure = number_or_none(
    first_matching(
        latest_flat,
        (
            "pressure",
            "mean_sea_level_pressure",
            "meanSeaLevelPressure",
            "msl_pressure",
        ),
        (
            "pressure",
        ),
    )
)

latitude = number_or_none(
    first_matching(
        latest_flat,
        (
            "latitude",
            "lat",
        ),
    )
)

longitude = number_or_none(
    first_matching(
        latest_flat,
        (
            "longitude",
            "lon",
            "lng",
        ),
    )
)

record = {
    "meeting_key": "GEELONG",
    "meeting": "Geelong",
    "provider": "BOM_OBSERVATIONS",
    "source_name": "Bureau of Meteorology",
    "source_url": PAGE_URL,
    "source_endpoint": latest_record.get(
        "final_url"
    ),

    "station_id": STATION_ID,
    "station_name": station_name,
    "station_status": "ACTIVE",

    "fetched_at_utc": datetime.now(
        timezone.utc
    ).isoformat(),

    "source_observed_datetime": observation_time,
    "source_status": "LIVE",

    "temperature_c": temperature,
    "apparent_temperature_c": apparent_temperature,
    "humidity_pct": humidity,
    "dew_point_c": dew_point,

    "rainfall_since_9am_mm": rain_since_9am,
    "rainfall_current_mm": rain_last_hour,

    "wind_direction": wind_direction,
    "wind_speed_kmh": wind_speed,
    "wind_gust_kmh": wind_gust,

    "pressure_hpa": pressure,

    "latitude": latitude,
    "longitude": longitude,

    "qc_results_included": False,
    "recent_observations_available": (
        recent_payload is not None
    ),

    "errors": [],
}

OUTPUT.write_text(
    json.dumps(
        {
            "schema_version": (
                "edgeiq_vic_bom_observations_v1"
            ),
            "generated_at_utc": datetime.now(
                timezone.utc
            ).isoformat(),
            "records": [record],
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

summary_lines = [
    "EDGEIQ VICTORIAN BOM OBSERVATIONS V1",
    "=" * 45,
    "",
    f"Station ID: {STATION_ID}",
    f"Station: {station_name}",
    f"Status: {record['source_status']}",
    f"Observed: {observation_time}",
    "",
    f"Temperature C: {temperature}",
    f"Apparent temperature C: {apparent_temperature}",
    f"Humidity %: {humidity}",
    f"Dew point C: {dew_point}",
    f"Rain since 9am mm: {rain_since_9am}",
    f"Current rainfall mm: {rain_last_hour}",
    f"Wind direction: {wind_direction}",
    f"Wind speed km/h: {wind_speed}",
    f"Wind gust km/h: {wind_gust}",
    f"Pressure hPa: {pressure}",
    "",
    "PRODUCT GOVERNANCE",
    "------------------",
    "Official BOM observations only.",
    "Missing station elements remain unavailable.",
    "No track-condition inference.",
    "No projected official track rating.",
]

SUMMARY.write_text(
    "\n".join(summary_lines),
    encoding="utf-8",
)

schema_lines = [
    "EDGEIQ BOM 87184 SCHEMA AUDIT",
    "=" * 42,
    "",
    f"Successful requests: {len(successful)}",
    f"Selected request: {latest_record['label']}",
    f"Selected URL: {latest_record.get('final_url')}",
    f"Flattened fields: {len(latest_flat)}",
    "",
    "NORMALISED VALUES",
    "-----------------",
]

for key, value in record.items():
    schema_lines.append(
        f"{key} = {value}"
    )

schema_lines.extend(
    [
        "",
        "FLATTENED PAYLOAD FIELDS",
        "------------------------",
    ]
)

for path, value in sorted(
    latest_flat.items()
):
    schema_lines.append(
        f"{path} = {value}"
    )

SCHEMA_AUDIT.write_text(
    "\n".join(schema_lines),
    encoding="utf-8",
)

print()
print("[EDGEIQ] BOM station adapter built")
print(f"[EDGEIQ] Station: {station_name}")
print(f"[EDGEIQ] Temperature: {temperature}")
print(f"[EDGEIQ] Humidity: {humidity}")
print(f"[EDGEIQ] Wind: {wind_direction} {wind_speed}")
print(f"[EDGEIQ] Rain since 9am: {rain_since_9am}")
print(f"[EDGEIQ] Output: {OUTPUT}")
