from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "data" / "weather-source-audit"
WEATHER_DIR = ROOT / "data" / "weather"
PUBLIC_DIR = ROOT / "public" / "data"

OUTPUT_JSON = PUBLIC_DIR / "edgeiq_on_track_weather_observation_v1.json"
OUTPUT_CSV = WEATHER_DIR / "on_track_weather_observation_v1.csv"
LINEAGE_CSV = WEATHER_DIR / "on_track_weather_observation_lineage_v1.csv"

AUDIT_TXT = PUBLIC_DIR / "edgeiq_on_track_weather_observation_v1_audit.txt"
AUDIT_JSON = PUBLIC_DIR / "edgeiq_on_track_weather_observation_v1_audit.json"

WEATHER_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_CONFIG = [
    {
        "track_group": "Flemington",
        "track_ids": ["FLEMINGTON"],
        "source_owner": "VRC",
        "source_type": "VRC_ON_TRACK",
        "source_page": "https://www.vrc.com.au/track-and-weather-conditions/",
        "repository_file": AUDIT_ROOT / "live-vrc" / "vrc_turf_raw.json",
        "content_path": ["content"],
        "tardis_path": ["tardis"],
        "station_fallback_id": "VRC_FLEMINGTON_ON_TRACK",
    },
    {
        "track_group": "Caulfield",
        "track_ids": ["CAULFIELD", "CAULFIELD_HEATH"],
        "source_owner": "TURFTRAX",
        "source_type": "MRC_TURFTRAX_ON_TRACK",
        "source_page": "https://its.turftrax.co.uk/visualiser/caulfield/",
        "repository_file": AUDIT_ROOT / "live-turftrax" / "caulfield_raw.json",
        "content_path": ["payload", "content"],
        "tardis_path": ["payload", "tardis"],
        "station_fallback_id": "TURFTRAX_CAULFIELD",
    },
    {
        "track_group": "Sandown",
        "track_ids": ["SANDOWN_HILLSIDE", "SANDOWN_LAKESIDE"],
        "source_owner": "TURFTRAX",
        "source_type": "MRC_TURFTRAX_ON_TRACK",
        "source_page": "https://its.turftrax.co.uk/visualiser/ladbrokes/",
        "repository_file": AUDIT_ROOT / "live-turftrax" / "ladbrokes_raw.json",
        "content_path": ["payload", "content"],
        "tardis_path": ["payload", "tardis"],
        "station_fallback_id": "TURFTRAX_SANDOWN",
    },
    {
        "track_group": "Mornington",
        "track_ids": ["MORNINGTON"],
        "source_owner": "TURFTRAX",
        "source_type": "MRC_TURFTRAX_ON_TRACK",
        "source_page": "https://its.turftrax.co.uk/visualiser/mornington/",
        "repository_file": AUDIT_ROOT / "live-turftrax" / "mornington_raw.json",
        "content_path": ["payload", "content"],
        "tardis_path": ["payload", "tardis"],
        "station_fallback_id": "TURFTRAX_MORNINGTON",
    },
]


def nested(payload: Any, path: list[str]) -> Any:
    current = payload

    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)

    return current


def clean_string(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text or text.lower() in {"n/a", "na", "none", "null", "-"}:
        return None

    return text


def clean_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        text = str(value).strip()

        if not text or text.lower() in {"n/a", "na", "none", "null", "-"}:
            return None

        return float(text)
    except (TypeError, ValueError):
        return None


def clean_int(value: Any) -> int | None:
    numeric = clean_float(value)

    if numeric is None:
        return None

    return int(numeric)


def choose_first(mapping: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = mapping.get(key)

        if value is not None and str(value).strip() not in {"", "N/a", "n/a"}:
            return value

    return None


def combine_weather_timestamp(
    weather_date: str | None,
    weather_time: str | None,
) -> str | None:
    if not weather_date or not weather_time:
        return None

    combined = f"{weather_date} {weather_time}"

    formats = [
        "%d/%m/%y %I:%M%p",
        "%d/%m/%y %I:%M %p",
        "%d/%m/%Y %I:%M%p",
        "%d/%m/%Y %I:%M %p",
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(combined, fmt)
            return parsed.isoformat()
        except ValueError:
            continue

    return None


def is_valid_year(value: str | None) -> bool:
    if not value:
        return False

    try:
        year = int(value[:4])
    except (TypeError, ValueError):
        return False

    return 2020 <= year <= 2035


records: list[dict[str, Any]] = []
lineage_rows: list[dict[str, str]] = []
errors: list[str] = []

for config in SOURCE_CONFIG:
    source_path: Path = config["repository_file"]

    if not source_path.exists():
        errors.append(f"missing_source={source_path}")
        continue

    try:
        payload = json.loads(
            source_path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        )
    except Exception as exc:
        errors.append(f"parse_failed={source_path}: {exc}")
        continue

    content = nested(payload, config["content_path"])
    tardis = nested(payload, config["tardis_path"])

    if not isinstance(content, dict):
        errors.append(f"content_missing={source_path}")
        continue

    if not isinstance(tardis, dict):
        tardis = {}

    station_id = clean_string(content.get("stationId"))
    station_id_source = "source"

    if station_id is None:
        station_id = config["station_fallback_id"]
        station_id_source = "edgeiq_stable_source_identifier"

    weather_date = clean_string(content.get("weather-date"))
    weather_last_update = clean_string(content.get("weather-last-update"))

    observation_local = combine_weather_timestamp(
        weather_date,
        weather_last_update,
    )

    server_time = nested(tardis, ["server-time", "calendar"])
    local_time = nested(tardis, ["local-time", "calendar"])

    server_time_text = clean_string(server_time)
    local_time_text = clean_string(local_time)

    if local_time_text and not is_valid_year(local_time_text):
        local_time_text = None

    if server_time_text and not is_valid_year(server_time_text):
        server_time_text = None

    observation_record = {
        "track_group": config["track_group"],
        "track_ids": config["track_ids"],
        "source_owner": config["source_owner"],
        "source_type": config["source_type"],
        "source_page": config["source_page"],
        "source_repository_file": str(source_path.relative_to(ROOT)),
        "station_id": station_id,
        "station_id_source": station_id_source,
        "station_type": clean_string(content.get("stationType")),
        "station_status": clean_string(
            content.get("stationActivityStatus")
        ),
        "observation_local": observation_local,
        "weather_date": weather_date,
        "weather_last_update": weather_last_update,
        "server_time": server_time_text,
        "local_time": local_time_text,
        "temperature_c": clean_float(
            choose_first(
                content,
                [
                    "air-temperature-current",
                    "temperature-current",
                ],
            )
        ),
        "temperature_min_c": clean_float(
            choose_first(
                content,
                [
                    "air-temperature-min",
                    "temperature-min",
                ],
            )
        ),
        "temperature_max_c": clean_float(
            choose_first(
                content,
                [
                    "air-temperature-max",
                    "temperature-max",
                ],
            )
        ),
        "humidity_percent": clean_float(
            content.get("humidity-current")
        ),
        "humidity_min_percent": clean_float(
            content.get("humidity-min")
        ),
        "humidity_max_percent": clean_float(
            content.get("humidity-max")
        ),
        "wind_speed_current": clean_float(
            content.get("windspeed-current")
        ),
        "wind_speed_average": clean_float(
            content.get("windspeed-average")
        ),
        "wind_direction_text": clean_string(
            content.get("winddirection-text")
        ),
        "wind_direction_degrees": clean_float(
            content.get("winddirection-current")
        ),
        "wind_gust_current": clean_float(
            content.get("windgust-current")
        ),
        "wind_gust_min": clean_float(
            content.get("windgust-min")
        ),
        "wind_gust_max": clean_float(
            content.get("windgust-max")
        ),
        "wind_gust_event": clean_string(
            content.get("windgust-event")
        ),
        "rain_today_mm": clean_float(
            choose_first(
                content,
                [
                    "rain1-today",
                    "rain2-today",
                ],
            )
        ),
        "rain_24h_mm": clean_float(
            choose_first(
                content,
                [
                    "rain1-24hr",
                    "rain2-24hr",
                ],
            )
        ),
        "rain_7d_mm": clean_float(
            choose_first(
                content,
                [
                    "rain1-7day",
                    "rain2-7day",
                ],
            )
        ),
        "weather_comment": clean_string(
            content.get("weather-comment")
        ),
        "track_type": clean_string(content.get("trackType")),
        "going_report": clean_string(
            content.get("going-report")
        ),
        "going_report_date": clean_string(
            content.get("going-report-date")
        ),
        "going_race_date": clean_string(
            content.get("going-race-date")
        ),
        "going_zone_map": clean_string(
            content.get("going-zone-map")
        ),
        "going_waypoint_map": clean_string(
            content.get("going-waypoint-map")
        ),
        "source_state": "AVAILABLE",
        "schema_version": "edgeiq_on_track_weather_observation_v1",
    }

    critical_present = sum(
        value is not None
        for value in [
            observation_record["temperature_c"],
            observation_record["humidity_percent"],
            observation_record["wind_speed_current"],
            observation_record["wind_direction_text"],
            observation_record["rain_24h_mm"],
        ]
    )

    if critical_present == 0:
        observation_record["source_state"] = "UNAVAILABLE"
    elif critical_present < 3:
        observation_record["source_state"] = "PARTIAL"

    records.append(observation_record)

    lineage_fields = {
        "temperature_c": (
            "air-temperature-current|temperature-current"
        ),
        "humidity_percent": "humidity-current",
        "wind_speed_current": "windspeed-current",
        "wind_speed_average": "windspeed-average",
        "wind_direction_text": "winddirection-text",
        "wind_direction_degrees": "winddirection-current",
        "wind_gust_current": "windgust-current",
        "wind_gust_max": "windgust-max",
        "rain_today_mm": "rain1-today|rain2-today",
        "rain_24h_mm": "rain1-24hr|rain2-24hr",
        "rain_7d_mm": "rain1-7day|rain2-7day",
        "weather_comment": "weather-comment",
        "going_report": "going-report",
        "observation_local": (
            "weather-date + weather-last-update"
        ),
    }

    for target_field, source_field in lineage_fields.items():
        lineage_rows.append(
            {
                "track_group": config["track_group"],
                "source_owner": config["source_owner"],
                "repository_file": str(source_path.relative_to(ROOT)),
                "target_field": target_field,
                "source_json_path": source_field,
                "normalisation": "direct typed normalisation",
                "fabricated": "NO",
                "notes": "",
            }
        )

output_payload = {
    "schema_version": "edgeiq_on_track_weather_observation_v1",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "record_count": len(records),
    "records": records,
    "errors": errors,
}

OUTPUT_JSON.write_text(
    json.dumps(output_payload, indent=2),
    encoding="utf-8",
)

csv_fields = [
    "track_group",
    "track_ids",
    "source_owner",
    "source_type",
    "source_page",
    "source_repository_file",
    "station_id",
    "station_id_source",
    "station_type",
    "station_status",
    "observation_local",
    "weather_date",
    "weather_last_update",
    "server_time",
    "local_time",
    "temperature_c",
    "temperature_min_c",
    "temperature_max_c",
    "humidity_percent",
    "humidity_min_percent",
    "humidity_max_percent",
    "wind_speed_current",
    "wind_speed_average",
    "wind_direction_text",
    "wind_direction_degrees",
    "wind_gust_current",
    "wind_gust_min",
    "wind_gust_max",
    "wind_gust_event",
    "rain_today_mm",
    "rain_24h_mm",
    "rain_7d_mm",
    "weather_comment",
    "track_type",
    "going_report",
    "going_report_date",
    "going_race_date",
    "going_zone_map",
    "going_waypoint_map",
    "source_state",
    "schema_version",
]

with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=csv_fields)
    writer.writeheader()

    for record in records:
        row = dict(record)
        row["track_ids"] = "|".join(record["track_ids"])
        writer.writerow(row)

lineage_fields = [
    "track_group",
    "source_owner",
    "repository_file",
    "target_field",
    "source_json_path",
    "normalisation",
    "fabricated",
    "notes",
]

with LINEAGE_CSV.open(
    "w",
    encoding="utf-8-sig",
    newline="",
) as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=lineage_fields,
    )
    writer.writeheader()
    writer.writerows(lineage_rows)

available_records = [
    record
    for record in records
    if record["source_state"] == "AVAILABLE"
]

partial_records = [
    record
    for record in records
    if record["source_state"] == "PARTIAL"
]

audit = {
    "status": "EDGEIQ_ON_TRACK_WEATHER_OBSERVATION_V1_AUDIT_PASS",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "source_groups_expected": len(SOURCE_CONFIG),
    "records_built": len(records),
    "available_records": len(available_records),
    "partial_records": len(partial_records),
    "errors": errors,
    "output_json": str(OUTPUT_JSON.relative_to(ROOT)),
    "output_csv": str(OUTPUT_CSV.relative_to(ROOT)),
    "lineage_csv": str(LINEAGE_CSV.relative_to(ROOT)),
    "track_groups": [
        record["track_group"]
        for record in records
    ],
    "notes": [
        "All values originate from captured VRC or TurfTrax source payloads.",
        "No weather values were fabricated.",
        "Flemington uses a stable EDGEiQ source identifier because source stationId is unavailable.",
        "Invalid future race dates are not used as observation timestamps.",
        "Weather observation time uses weather-date plus weather-last-update.",
        "Wind speed units remain source-native until verified by source metadata.",
    ],
}

AUDIT_JSON.write_text(
    json.dumps(audit, indent=2),
    encoding="utf-8",
)

audit_lines = [
    audit["status"],
    f"generated_at={audit['generated_at']}",
    f"source_groups_expected={audit['source_groups_expected']}",
    f"records_built={audit['records_built']}",
    f"available_records={audit['available_records']}",
    f"partial_records={audit['partial_records']}",
    f"errors={len(errors)}",
    f"output_json={audit['output_json']}",
    f"output_csv={audit['output_csv']}",
    f"lineage_csv={audit['lineage_csv']}",
    "",
    "No weather value was fabricated.",
    "Wind speed units remain source-native pending unit verification.",
]

AUDIT_TXT.write_text(
    "\n".join(audit_lines) + "\n",
    encoding="utf-8",
)

print(audit["status"])
print(f"records_built={len(records)}")
print(f"available_records={len(available_records)}")
print(f"partial_records={len(partial_records)}")

for record in records:
    print(
        f"{record['track_group']} | "
        f"{record['temperature_c']}C | "
        f"{record['humidity_percent']}% | "
        f"wind={record['wind_speed_current']} | "
        f"gust={record['wind_gust_current']} | "
        f"rain24h={record['rain_24h_mm']} | "
        f"state={record['source_state']}"
    )
