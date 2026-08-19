from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW_JSON = ROOT / "data" / "weather" / "live_raw_on_track_weather_v1.json"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_on_track_weather_governed_v1_2.json"
OUT_CSV = ROOT / "data" / "weather" / "on_track_weather_governed_v1_2.csv"
LINEAGE_CSV = ROOT / "data" / "weather" / "on_track_weather_governed_v1_2_lineage.csv"
AUDIT_TXT = ROOT / "public" / "data" / "edgeiq_on_track_weather_governed_v1_2_audit.txt"
AUDIT_JSON = ROOT / "public" / "data" / "edgeiq_on_track_weather_governed_v1_2_audit.json"

FRESH_MINUTES = 20
STALE_MINUTES = 90

TRACK_IDS = {
    "Flemington": ["FLEMINGTON"],
    "Caulfield": ["CAULFIELD", "CAULFIELD_HEATH"],
    "Sandown": ["SANDOWN_HILLSIDE", "SANDOWN_LAKESIDE"],
    "Mornington": ["MORNINGTON"],
}

SOURCE_OWNER = {
    "Flemington": "VRC",
    "Caulfield": "TURFTRAX",
    "Sandown": "TURFTRAX",
    "Mornington": "TURFTRAX",
}

SOURCE_TYPE = {
    "Flemington": "VRC_ON_TRACK",
    "Caulfield": "MRC_TURFTRAX_ON_TRACK",
    "Sandown": "MRC_TURFTRAX_ON_TRACK",
    "Mornington": "MRC_TURFTRAX_ON_TRACK",
}


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text or text.lower() in {"n/a", "na", "none", "null", "-", "—"}:
        return None
    return text


def clean_float(value: Any) -> float | None:
    text = clean_text(value)
    if text is None:
        return None
    try:
        return float(text.replace("mm", "").replace("%", "").replace("km/h", "").replace("°", "").strip())
    except ValueError:
        return None


def first(content: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = content.get(key)
        if clean_text(value) is not None:
            return value
    return None


def nested(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def parse_observation(content: dict[str, Any], tardis: dict[str, Any]) -> tuple[str | None, str | None]:
    weather_date = clean_text(content.get("weather-date"))
    weather_time = clean_text(content.get("weather-last-update"))
    if weather_date and weather_time:
        for fmt in ("%d/%m/%y %I:%M%p", "%d/%m/%y %I:%M %p", "%d/%m/%Y %I:%M%p", "%d/%m/%Y %I:%M %p"):
            try:
                parsed = datetime.strptime(f"{weather_date} {weather_time}", fmt)
                return parsed.isoformat(), f"{weather_date} {weather_time}"
            except ValueError:
                pass
    local_calendar = clean_text(nested(tardis, "local-time", "calendar"))
    if local_calendar:
        return local_calendar, local_calendar
    return None, None


def freshness(observation_local: str | None) -> tuple[str, str, str]:
    if not observation_local:
        return "UNKNOWN", "", "NO"
    try:
        observed = datetime.fromisoformat(observation_local)
    except ValueError:
        return "UNKNOWN", "", "NO"
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=datetime.now().astimezone().tzinfo)
    age = max(0.0, (datetime.now().astimezone() - observed).total_seconds() / 60.0)
    if age <= FRESH_MINUTES:
        return "FRESH", f"{age:.1f}", "YES"
    if age <= STALE_MINUTES:
        return "AGING", f"{age:.1f}", "YES"
    return "STALE", f"{age:.1f}", "NO"


def source_state(raw_status: str, freshness_status: str, usable: str) -> str:
    if raw_status == "ACCESS_BLOCKED":
        return "ACCESS_BLOCKED"
    if raw_status == "SCHEMA_CHANGED":
        return "SCHEMA_CHANGED"
    if raw_status == "SOURCE_ERROR":
        return "SOURCE_ERROR"
    if raw_status not in {"LIVE_AVAILABLE", "LIVE_PARTIAL"}:
        return "LIVE_UNAVAILABLE"
    if usable == "YES" and freshness_status == "FRESH":
        return "AVAILABLE_CURRENT"
    if usable == "YES" and freshness_status == "AGING":
        return "AVAILABLE_AGING"
    if freshness_status == "STALE":
        return "AVAILABLE_STALE"
    return "AVAILABLE_UNKNOWN_FRESHNESS"


def main() -> int:
    raw_payload = json.loads(RAW_JSON.read_text(encoding="utf-8")) if RAW_JSON.exists() else {"records": []}
    records: list[dict[str, Any]] = []
    lineage: list[dict[str, str]] = []
    for raw in raw_payload.get("records", []):
        track_group = raw.get("track_group")
        content = raw.get("content") if isinstance(raw.get("content"), dict) else {}
        tardis = raw.get("tardis") if isinstance(raw.get("tardis"), dict) else {}
        observation_local, source_timestamp = parse_observation(content, tardis)
        fresh_status, age_minutes, usable = freshness(observation_local)
        record = {
            "track_group": track_group,
            "track_ids": TRACK_IDS.get(str(track_group), []),
            "source_owner": SOURCE_OWNER.get(str(track_group), ""),
            "source_type": SOURCE_TYPE.get(str(track_group), ""),
            "source_page": raw.get("source_page"),
            "live_request_url": raw.get("live_request_url"),
            "station_id": clean_text(content.get("stationId")) or f"{SOURCE_OWNER.get(str(track_group), 'SOURCE')}_{str(track_group).upper()}_ON_TRACK",
            "station_status": clean_text(content.get("stationActivityStatus")),
            "observation_local": observation_local,
            "source_timestamp": source_timestamp,
            "fetched_at": raw.get("fetched_at"),
            "temperature_c": clean_float(first(content, "air-temperature-current", "temperature-current")),
            "humidity_percent": clean_float(content.get("humidity-current")),
            "wind_speed_kmh": clean_float(content.get("windspeed-current")),
            "wind_speed_average_kmh": clean_float(content.get("windspeed-average")),
            "wind_direction_text": clean_text(content.get("winddirection-text")),
            "wind_direction_degrees": clean_float(content.get("winddirection-current")),
            "wind_gust_kmh": clean_float(content.get("windgust-current")),
            "wind_gust_max_kmh": clean_float(content.get("windgust-max")),
            "rain_today_mm": clean_float(first(content, "rain1-today", "rain2-today")),
            "rain_24h_mm": clean_float(first(content, "rain1-24hr", "rain2-24hr")),
            "rain_7d_mm": clean_float(first(content, "rain1-7day", "rain2-7day")),
            "weather_comment": clean_text(content.get("weather-comment")),
            "going_report": clean_text(content.get("going-report")),
            "going_report_date": clean_text(content.get("going-report-date")),
            "freshness_status": fresh_status,
            "age_minutes": age_minutes,
            "usable_as_current": usable,
            "governed_source_state": source_state(str(raw.get("source_status")), fresh_status, usable),
            "schema_version": "edgeiq_on_track_weather_governed_v1_2",
        }
        records.append(record)
        for field in [
            "temperature_c", "humidity_percent", "wind_speed_kmh", "wind_speed_average_kmh",
            "wind_direction_text", "wind_direction_degrees", "wind_gust_kmh", "wind_gust_max_kmh",
            "rain_today_mm", "rain_24h_mm", "rain_7d_mm", "weather_comment", "going_report",
            "freshness_status", "usable_as_current",
        ]:
            lineage.append({
                "track_group": str(track_group),
                "target_field": field,
                "origin": "live_raw_on_track_weather_v1.json + verified v1.1 mapping/freshness builder",
                "conversion": "NONE",
                "source_unit": "C" if field == "temperature_c" else "km/h" if "wind" in field else "mm" if "rain" in field else "",
                "target_unit": "C" if field == "temperature_c" else "km/h" if "wind" in field else "mm" if "rain" in field else "",
                "fabricated": "NO",
                "notes": "",
            })
    payload = {
        "schema_version": "edgeiq_on_track_weather_governed_v1_2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "records": records,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    fields = [
        "track_group", "track_ids", "source_owner", "source_type", "source_page", "live_request_url",
        "station_id", "station_status", "observation_local", "source_timestamp", "fetched_at",
        "temperature_c", "humidity_percent", "wind_speed_kmh", "wind_speed_average_kmh",
        "wind_direction_text", "wind_direction_degrees", "wind_gust_kmh", "wind_gust_max_kmh",
        "rain_today_mm", "rain_24h_mm", "rain_7d_mm", "weather_comment", "going_report",
        "going_report_date", "freshness_status", "age_minutes", "usable_as_current",
        "governed_source_state", "schema_version",
    ]
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["track_ids"] = "|".join(row["track_ids"])
            writer.writerow(row)
    lineage_fields = ["track_group", "target_field", "origin", "conversion", "source_unit", "target_unit", "fabricated", "notes"]
    with LINEAGE_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=lineage_fields)
        writer.writeheader()
        writer.writerows(lineage)
    current = sum(1 for row in records if row["governed_source_state"] == "AVAILABLE_CURRENT")
    aging = sum(1 for row in records if row["governed_source_state"] == "AVAILABLE_AGING")
    stale = sum(1 for row in records if row["governed_source_state"] == "AVAILABLE_STALE")
    audit = {
        "status": "EDGEIQ_ON_TRACK_WEATHER_GOVERNED_V1_2_AUDIT_PASS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records": len(records),
        "available_current": current,
        "available_aging": aging,
        "available_stale": stale,
        "lineage_rows": len(lineage),
        "output_json": str(OUT_JSON.relative_to(ROOT)),
        "output_csv": str(OUT_CSV.relative_to(ROOT)),
        "lineage_csv": str(LINEAGE_CSV.relative_to(ROOT)),
        "notes": [
            "Freshness is builder-owned.",
            "React performs no freshness or unit calculation.",
            "No weather values were fabricated.",
        ],
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    AUDIT_TXT.write_text("\n".join([
        audit["status"],
        f"generated_at={audit['generated_at']}",
        f"records={audit['records']}",
        f"available_current={current}",
        f"available_aging={aging}",
        f"available_stale={stale}",
        "temperature_unit=C",
        "wind_speed_unit=km/h",
        "rainfall_unit=mm",
        "conversion_applied=false",
        "",
        "No weather value was fabricated.",
        "React performs no freshness calculation.",
    ]) + "\n", encoding="utf-8")
    print(audit["status"])
    for row in records:
        print(f"{row['track_group']} | {row['governed_source_state']} | {row['freshness_status']} | age={row['age_minutes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
