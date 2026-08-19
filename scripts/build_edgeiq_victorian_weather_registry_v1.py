from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

METRO_BUILDER = (
    ROOT
    / "scripts"
    / "build_edgeiq_metropolitan_weather_registry_v1.py"
)

TRACK_BUILDER = (
    ROOT
    / "scripts"
    / "build_edgeiq_racing_australia_track_and_audit_bom_v1.py"
)

BOM_BUILDER = (
    ROOT
    / "scripts"
    / "build_edgeiq_vic_bom_observations_v1.py"
)

METRO_FEED = (
    DATA
    / "edgeiq_metropolitan_weather_v1.json"
)

TRACK_FEED = (
    DATA
    / "edgeiq_vic_official_track_conditions_v1.json"
)

BOM_FEED = (
    DATA
    / "edgeiq_vic_bom_observations_v1.json"
)

OUTPUT = METRO_FEED

SUMMARY = (
    DATA
    / "edgeiq_metropolitan_weather_v1_summary.txt"
)

AUDIT = (
    DATA
    / "edgeiq_victorian_weather_registry_v1_audit.txt"
)

HIGH_AUTHORITY_KEYS = {
    "FLEMINGTON",
    "CAULFIELD",
    "SANDOWN",
    "MORNINGTON",
}


def run_builder(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"{label} builder not found: {path}"
        )

    print(f"[EDGEIQ] Running {label}")

    result = subprocess.run(
        [sys.executable, str(path)],
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
            f"{label} failed with exit code "
            f"{result.returncode}"
        )


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Required feed not found: {path}"
        )

    payload = json.loads(
        path.read_text(
            encoding="utf-8-sig",
        )
    )

    if not isinstance(payload, dict):
        raise TypeError(
            f"Expected object in {path}"
        )

    return payload


def text(value: Any) -> str | None:
    if value is None:
        return None

    cleaned = str(value).strip()

    if not cleaned:
        return None

    if cleaned.lower() in {
        "-",
        "—",
        "none",
        "null",
        "n/a",
        "na",
    }:
        return None

    return cleaned


def number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def canonical_key(value: Any) -> str:
    cleaned = text(value) or ""

    cleaned = cleaned.upper()

    prefixes = (
        "SPORTSBET-",
        "SPORTSBET ",
        "LADBROKES ",
        "BET365 ",
        "SOUTHSIDE ",
    )

    for prefix in prefixes:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break

    aliases = {
        "CAULFIELD HEATH": "CAULFIELD",
        "SANDOWN HILLSIDE": "SANDOWN",
        "SANDOWN LAKESIDE": "SANDOWN",
        "LADBROKES PARK": "SANDOWN",
        "BALLARAT SYNTHETIC": "BALLARAT SYNTHETIC",
        "GEELONG SYNTHETIC": "GEELONG SYNTHETIC",
    }

    return aliases.get(
        cleaned.strip(),
        cleaned.strip(),
    )


def bom_by_key(
    payload: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    records = payload.get("records", [])

    if not isinstance(records, list):
        return {}

    output: dict[str, dict[str, Any]] = {}

    for record in records:
        if not isinstance(record, dict):
            continue

        key = canonical_key(
            record.get("meeting_key")
            or record.get("meeting")
        )

        if key:
            output[key] = record

    return output


def build_regional_record(
    track: dict[str, Any],
    bom: dict[str, Any] | None,
    generated_at: str,
) -> dict[str, Any]:
    meeting_key = canonical_key(
        track.get("meeting_key")
        or track.get("meeting")
    )

    bom_live = bool(
        bom
        and bom.get("source_status") == "LIVE"
    )

    provider = (
        "RACING_AUSTRALIA_BOM"
        if bom_live
        else "RACING_AUSTRALIA"
    )

    source_name = (
        "Racing Australia + Bureau of Meteorology"
        if bom_live
        else "Racing Australia"
    )

    source_observed_datetime = (
        text(
            bom.get("source_observed_datetime")
        )
        if bom
        else None
    )

    errors: list[str] = []

    if bom:
        raw_errors = bom.get("errors", [])

        if isinstance(raw_errors, list):
            errors.extend(
                str(item)
                for item in raw_errors
                if item
            )

    return {
        "meeting_key": meeting_key,
        "meeting": track.get("meeting"),
        "course": track.get("meeting"),
        "meeting_date": track.get("meeting_date"),

        "provider": provider,
        "source_name": source_name,
        "source_url": track.get("source_url"),
        "source_endpoint": (
            bom.get("source_endpoint")
            if bom_live and bom
            else None
        ),

        "fetched_at_utc": generated_at,

        "source_observed_date": (
            source_observed_datetime[:10]
            if source_observed_datetime
            and len(source_observed_datetime) >= 10
            else track.get("meeting_date")
        ),

        "source_observed_time": (
            source_observed_datetime[11:16]
            if source_observed_datetime
            and len(source_observed_datetime) >= 16
            else None
        ),

        "source_observed_datetime": (
            source_observed_datetime
        ),

        "station_status": (
            bom.get("station_status")
            if bom_live and bom
            else None
        ),

        "source_status": "LIVE",

        "official_track_rating": (
            track.get("official_track_rating")
        ),

        "official_track_rating_updated": None,

        "official_rail": (
            track.get("official_rail")
        ),

        "going_stick": None,

        "temperature_c": (
            number(bom.get("temperature_c"))
            if bom_live and bom
            else None
        ),

        "apparent_temperature_c": (
            number(
                bom.get(
                    "apparent_temperature_c"
                )
            )
            if bom_live and bom
            else None
        ),

        "temperature_min_c": (
            number(
                bom.get("temperature_min_c")
            )
            if bom_live and bom
            else None
        ),

        "temperature_max_c": (
            number(
                bom.get("temperature_max_c")
            )
            if bom_live and bom
            else None
        ),

        "humidity_pct": (
            number(bom.get("humidity_pct"))
            if bom_live and bom
            else None
        ),

        "dew_point_c": (
            number(bom.get("dew_point_c"))
            if bom_live and bom
            else None
        ),

        "rainfall_24h_mm": (
            number(
                track.get("rainfall_24h_mm")
            )
            if track.get("rainfall_24h_mm")
            is not None
            else (
                number(
                    bom.get("rainfall_24h_mm")
                )
                if bom_live and bom
                else None
            )
        ),

        "rainfall_since_9am_mm": (
            number(
                bom.get(
                    "rainfall_since_9am_mm"
                )
            )
            if bom_live and bom
            else None
        ),

        "rainfall_since_midnight_mm": (
            number(
                bom.get(
                    "rainfall_since_midnight_mm"
                )
            )
            if bom_live and bom
            else None
        ),

        "rainfall_today_mm": (
            number(
                bom.get(
                    "rainfall_since_9am_mm"
                )
            )
            if bom_live and bom
            else number(
                track.get("rainfall_24h_mm")
            )
        ),

        "rainfall_current_mm": (
            number(
                bom.get("rainfall_current_mm")
            )
            if bom_live and bom
            else None
        ),

        "rainfall_1h_mm": (
            number(bom.get("rainfall_1h_mm"))
            if bom_live and bom
            else None
        ),

        "rainfall_7day_mm": number(
            track.get("rainfall_7day_mm")
        ),

        "forecast_rainfall": None,

        "weather_forecast": (
            track.get("weather_forecast")
        ),

        "moisture_loss_mm": None,
        "moisture_loss_7day_mm": None,
        "soil_moisture": None,

        "irrigation": track.get("irrigation"),

        "weather_comment": (
            track.get("weather_forecast")
        ),

        "additional_comment": (
            track.get("additional_information")
            or track.get("comment")
        ),

        "wind_direction": (
            bom.get("wind_direction")
            if bom_live and bom
            else None
        ),

        "wind_direction_degrees": None,

        "wind_speed_kmh": (
            number(bom.get("wind_speed_kmh"))
            if bom_live and bom
            else None
        ),

        "wind_average_kmh": None,

        "wind_gust_kmh": (
            number(bom.get("wind_gust_kmh"))
            if bom_live and bom
            else None
        ),

        "wind_gust_max_kmh": (
            number(
                bom.get("wind_gust_max_kmh")
            )
            if bom_live and bom
            else None
        ),

        "wind_gust_event": None,

        "pressure_hpa": (
            number(bom.get("pressure_hpa"))
            if bom_live and bom
            else None
        ),

        "wind_station": (
            bom.get("station_name")
            if bom_live and bom
            else None
        ),

        "wind_station_count": (
            1 if bom_live else 0
        ),

        "station_id": (
            bom.get("station_id")
            if bom_live and bom
            else None
        ),

        "official_station_id": (
            bom.get("official_station_id")
            if bom_live and bom
            else None
        ),

        "station_name": (
            bom.get("station_name")
            if bom_live and bom
            else None
        ),

        "station_type": (
            "BOM AUTOMATIC WEATHER STATION"
            if bom_live
            else None
        ),

        "venue_id": None,
        "report_id": None,

        "penetrometer": (
            track.get("penetrometer")
        ),

        "track_type": track.get("track_type"),

        "rainfall_report": (
            track.get("rainfall_report")
        ),

        "provider_description": (
            "Official racing track conditions "
            "combined with official live "
            "meteorological observations."
            if bom_live
            else (
                "Official racing track "
                "conditions."
            )
        ),

        "turf_http_status": 200,

        "wind_http_status": (
            bom.get("http_status")
            if bom_live and bom
            else None
        ),

        "api_status": 0,

        "errors": errors,
    }


def main() -> int:
    generated_at = datetime.now(
        timezone.utc
    ).isoformat()

    run_builder(
        METRO_BUILDER,
        "metropolitan weather registry",
    )

    run_builder(
        TRACK_BUILDER,
        "Racing Australia track conditions",
    )

    run_builder(
        BOM_BUILDER,
        "Victorian BOM observations",
    )

    metro_payload = read_json(METRO_FEED)
    track_payload = read_json(TRACK_FEED)
    bom_payload = read_json(BOM_FEED)

    metro_records = metro_payload.get(
        "records",
        [],
    )

    if not isinstance(metro_records, list):
        metro_records = []

    track_records = track_payload.get(
        "records",
        [],
    )

    if not isinstance(track_records, list):
        track_records = []

    bom_lookup = bom_by_key(bom_payload)

    final_records: list[dict[str, Any]] = []

    seen_identity: set[tuple[str, str]] = set()

    for record in metro_records:
        if not isinstance(record, dict):
            continue

        key = canonical_key(
            record.get("meeting_key")
            or record.get("meeting")
        )

        meeting_date = text(
            record.get("meeting_date")
        ) or ""

        identity = (key, meeting_date)

        if identity in seen_identity:
            continue

        seen_identity.add(identity)
        final_records.append(record)

    for track in track_records:
        if not isinstance(track, dict):
            continue

        key = canonical_key(
            track.get("meeting_key")
            or track.get("meeting")
        )

        if not key:
            continue

        if key in HIGH_AUTHORITY_KEYS:
            continue

        meeting_date = text(
            track.get("meeting_date")
        ) or ""

        identity = (key, meeting_date)

        if identity in seen_identity:
            continue

        record = build_regional_record(
            track,
            bom_lookup.get(key),
            generated_at,
        )

        final_records.append(record)
        seen_identity.add(identity)

    provider_registry: dict[str, str] = {}

    for record in final_records:
        key = canonical_key(
            record.get("meeting_key")
            or record.get("meeting")
        )

        provider = text(
            record.get("provider")
        )

        if key and provider:
            provider_registry[key] = provider

    output_payload = {
        "schema_version": (
            "edgeiq_victorian_weather_registry_v1"
        ),
        "generated_at_utc": generated_at,
        "provider_registry": provider_registry,
        "records": final_records,
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
        "EDGEIQ VICTORIAN WEATHER REGISTRY V1",
        "=" * 48,
        "",
        f"Generated: {generated_at}",
        f"Records: {len(final_records)}",
        "",
        "PROVIDER REGISTRY",
        "-----------------",
    ]

    for key in sorted(provider_registry):
        summary_lines.append(
            f"{key}: {provider_registry[key]}"
        )

    summary_lines.extend(
        [
            "",
            "NORMALISED RECORDS",
            "------------------",
        ]
    )

    for record in final_records:
        summary_lines.extend(
            [
                "",
                (
                    f"{record.get('meeting_date')} | "
                    f"{record.get('meeting')}"
                ),
                (
                    "  Provider: "
                    f"{record.get('provider')}"
                ),
                (
                    "  Status: "
                    f"{record.get('source_status')}"
                ),
                (
                    "  Track: "
                    f"{record.get('official_track_rating')}"
                ),
                (
                    "  Rail: "
                    f"{record.get('official_rail')}"
                ),
                (
                    "  Temperature: "
                    f"{record.get('temperature_c')}"
                ),
                (
                    "  Humidity: "
                    f"{record.get('humidity_pct')}"
                ),
                (
                    "  Wind: "
                    f"{record.get('wind_direction')} "
                    f"{record.get('wind_speed_kmh')}"
                ),
                (
                    "  Rain 24h: "
                    f"{record.get('rainfall_24h_mm')}"
                ),
                (
                    "  Rain 7d: "
                    f"{record.get('rainfall_7day_mm')}"
                ),
                (
                    "  Station: "
                    f"{record.get('station_name')}"
                ),
                (
                    "  Errors: "
                    f"{len(record.get('errors', []))}"
                ),
            ]
        )

    summary_lines.extend(
        [
            "",
            "PRODUCT GOVERNANCE",
            "------------------",
            "Club station data has highest authority.",
            (
                "Racing Australia supplies official "
                "track conditions."
            ),
            (
                "BOM supplies live meteorological "
                "observations."
            ),
            (
                "Forecast wording remains labelled "
                "as forecast."
            ),
            (
                "No projected future official track "
                "rating."
            ),
            "No inferred steward decision.",
        ]
    )

    SUMMARY.write_text(
        "\n".join(summary_lines),
        encoding="utf-8",
    )

    duplicate_keys: list[str] = []
    identity_count: dict[tuple[str, str], int] = {}

    for record in final_records:
        identity = (
            canonical_key(
                record.get("meeting_key")
                or record.get("meeting")
            ),
            text(record.get("meeting_date")) or "",
        )

        identity_count[identity] = (
            identity_count.get(identity, 0) + 1
        )

    for identity, count in identity_count.items():
        if count > 1:
            duplicate_keys.append(
                f"{identity[0]}|{identity[1]}"
            )

    audit_lines = [
        "EDGEIQ VICTORIAN WEATHER REGISTRY AUDIT",
        "=" * 50,
        "",
        f"Generated: {generated_at}",
        f"Records: {len(final_records)}",
        (
            "Duplicate meeting/date identities: "
            f"{len(duplicate_keys)}"
        ),
        (
            "Live records: "
            f"{sum(record.get('source_status') == 'LIVE' for record in final_records)}"
        ),
        "",
    ]

    required_keys = {
        "FLEMINGTON",
        "CAULFIELD",
        "SANDOWN",
        "MORNINGTON",
        "GEELONG",
        "BALLARAT",
        "HAMILTON",
        "DONALD",
    }

    available_keys = {
        canonical_key(
            record.get("meeting_key")
            or record.get("meeting")
        )
        for record in final_records
    }

    for key in sorted(required_keys):
        audit_lines.append(
            f"{key}: "
            f"{'PASS' if key in available_keys else 'MISSING'}"
        )

    audit_lines.extend(
        [
            "",
            "DUPLICATES",
            "----------",
        ]
    )

    audit_lines.extend(
        duplicate_keys or ["None"]
    )

    AUDIT.write_text(
        "\n".join(audit_lines),
        encoding="utf-8",
    )

    print()
    print(
        "[EDGEIQ] Victorian weather registry built"
    )
    print(f"[EDGEIQ] Records: {len(final_records)}")
    print(
        "[EDGEIQ] Providers: "
        f"{len(provider_registry)}"
    )
    print(
        "[EDGEIQ] Duplicate identities: "
        f"{len(duplicate_keys)}"
    )
    print(f"[EDGEIQ] Output: {OUTPUT}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
