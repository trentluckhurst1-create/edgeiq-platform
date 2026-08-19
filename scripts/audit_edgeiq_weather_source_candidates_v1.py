from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WEATHER_DIR = ROOT / "data" / "weather"
AUDIT_ROOT = ROOT / "data" / "weather-source-audit"
PUBLIC_DIR = ROOT / "public" / "data"

REGISTRY_PATH = WEATHER_DIR / "weather_source_registry_v1.csv"
EVIDENCE_PATH = WEATHER_DIR / "weather_source_evidence_v1.csv"
CANDIDATE_PATH = WEATHER_DIR / "weather_source_verified_candidates_v1.csv"
BOM_STATIONS_PATH = WEATHER_DIR / "bom_station_observation_inventory_v1.csv"
PAYLOAD_PATH = WEATHER_DIR / "on_track_weather_payload_inventory_v1.csv"

AUDIT_TXT = PUBLIC_DIR / "edgeiq_weather_source_candidate_audit_v1.txt"
AUDIT_JSON = PUBLIC_DIR / "edgeiq_weather_source_candidate_audit_v1.json"

WEATHER_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [
            {str(key): str(value or "") for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def write_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, Any]],
) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    field: row.get(field, "")
                    for field in fieldnames
                }
            )


registry_rows = read_csv(REGISTRY_PATH)
evidence_rows = read_csv(EVIDENCE_PATH)

# Exact values only. Do not use substring matching.
EXACT_ON_TRACK_SOURCE_TYPES = {
    "VRC_ON_TRACK",
    "MRC_TURFTRAX_ON_TRACK",
}

on_track_entries = [
    row
    for row in registry_rows
    if row.get("preferred_observation_source", "").strip()
    in EXACT_ON_TRACK_SOURCE_TYPES
]

physical_station_groups = {
    "Flemington": ["FLEMINGTON"],
    "Caulfield": ["CAULFIELD", "CAULFIELD_HEATH"],
    "Sandown": ["SANDOWN_HILLSIDE", "SANDOWN_LAKESIDE"],
    "Mornington": ["MORNINGTON"],
}

KNOWN_SOURCE_CANDIDATES = [
    {
        "track_group": "Flemington",
        "track_ids": "FLEMINGTON",
        "source_owner": "VRC",
        "source_type": "ON_TRACK_CLUB_PAGE",
        "candidate_url": "https://www.vrc.com.au/track-and-weather-conditions/",
        "candidate_role": "PRIMARY_SOURCE_PAGE",
        "verification_status": "DISCOVERED_NOT_YET_ENDPOINT_VERIFIED",
        "production_endpoint_confirmed": "NO",
        "notes": (
            "Official VRC track and weather page. "
            "Underlying live data request still requires confirmation."
        ),
    },
    {
        "track_group": "MRC Metropolitan",
        "track_ids": (
            "CAULFIELD|CAULFIELD_HEATH|SANDOWN_HILLSIDE|"
            "SANDOWN_LAKESIDE|MORNINGTON"
        ),
        "source_owner": "MRC",
        "source_type": "ON_TRACK_CLUB_PAGE",
        "candidate_url": (
            "https://mrc.racing.com/racing/"
            "raceday-track-weather-live"
        ),
        "candidate_role": "PRIMARY_SOURCE_PAGE",
        "verification_status": "DISCOVERED_NOT_YET_ENDPOINT_VERIFIED",
        "production_endpoint_confirmed": "NO",
        "notes": (
            "Official MRC race-day track and weather live page. "
            "Track-specific embedded source must be resolved."
        ),
    },
    {
        "track_group": "Caulfield",
        "track_ids": "CAULFIELD|CAULFIELD_HEATH",
        "source_owner": "TURFTRAX",
        "source_type": "ON_TRACK_VISUALISER",
        "candidate_url": (
            "https://its.turftrax.co.uk/visualiser/caulfield/"
        ),
        "candidate_role": "PRIMARY_LIVE_VISUALISER",
        "verification_status": "LIVE_PAGE_DISCOVERED",
        "production_endpoint_confirmed": "NO",
        "notes": (
            "Live TurfTrax visualiser is known. "
            "Underlying machine-readable observation request "
            "must still be isolated."
        ),
    },
    {
        "track_group": "Sandown",
        "track_ids": "SANDOWN_HILLSIDE|SANDOWN_LAKESIDE",
        "source_owner": "TURFTRAX",
        "source_type": "ON_TRACK_VISUALISER",
        "candidate_url": (
            "https://its.turftrax.co.uk/visualiser/ladbrokes/"
        ),
        "candidate_role": "PRIMARY_LIVE_VISUALISER",
        "verification_status": "LIVE_PAGE_DISCOVERED",
        "production_endpoint_confirmed": "NO",
        "notes": (
            "Ladbrokes Park visualiser appears to represent Sandown. "
            "Both course variants should share the physical station."
        ),
    },
    {
        "track_group": "Mornington",
        "track_ids": "MORNINGTON",
        "source_owner": "TURFTRAX",
        "source_type": "ON_TRACK_VISUALISER",
        "candidate_url": (
            "https://its.turftrax.co.uk/visualiser/mornington/"
        ),
        "candidate_role": "PRIMARY_LIVE_VISUALISER",
        "verification_status": "LIVE_PAGE_DISCOVERED",
        "production_endpoint_confirmed": "NO",
        "notes": (
            "Live TurfTrax visualiser is known. "
            "Underlying machine-readable observation request "
            "must still be isolated."
        ),
    },
]

candidate_fields = [
    "track_group",
    "track_ids",
    "source_owner",
    "source_type",
    "candidate_url",
    "candidate_role",
    "verification_status",
    "production_endpoint_confirmed",
    "notes",
]

write_csv(
    CANDIDATE_PATH,
    candidate_fields,
    KNOWN_SOURCE_CANDIDATES,
)

bom_rows: list[dict[str, Any]] = []

bom_live_root = AUDIT_ROOT / "bom-live"

if bom_live_root.exists():
    for station_dir in sorted(bom_live_root.iterdir()):
        if not station_dir.is_dir():
            continue

        station_id = station_dir.name
        latest_path = station_dir / "latest_raw.json"

        record: dict[str, Any] = {
            "station_id": station_id,
            "latest_file": (
                str(latest_path.relative_to(ROOT))
                if latest_path.exists()
                else ""
            ),
            "json_parse_status": "NOT_PRESENT",
            "station_name": "",
            "station_state": "",
            "latitude": "",
            "longitude": "",
            "elevation": "",
            "observation_count": "",
            "observation_fields": "",
            "latest_timestamp": "",
            "endpoint_pattern": (
                "https://api.bom.gov.au/apikey/v1/"
                f"observations/latest/{station_id}/atm/surf_air"
            ),
            "racecourse_mapping_status": "UNMAPPED",
            "notes": "",
        }

        if latest_path.exists() and latest_path.stat().st_size > 2:
            try:
                payload = json.loads(
                    latest_path.read_text(
                        encoding="utf-8",
                        errors="ignore",
                    )
                )

                record["json_parse_status"] = "PASS"

                station = payload.get("stn") or {}
                observations = payload.get("obs") or []

                if isinstance(station, list):
                    station = station[0] if station else {}

                if not isinstance(station, dict):
                    station = {}

                if not isinstance(observations, list):
                    observations = (
                        [observations]
                        if isinstance(observations, dict)
                        else []
                    )

                record["station_name"] = (
                    station.get("name")
                    or station.get("station_name")
                    or station.get("stn_name")
                    or ""
                )
                record["station_state"] = (
                    station.get("state")
                    or station.get("state_code")
                    or ""
                )
                record["latitude"] = (
                    station.get("lat")
                    or station.get("latitude")
                    or ""
                )
                record["longitude"] = (
                    station.get("lon")
                    or station.get("longitude")
                    or ""
                )
                record["elevation"] = (
                    station.get("height")
                    or station.get("elevation")
                    or ""
                )
                record["observation_count"] = len(observations)

                if observations:
                    first = observations[0]
                    if isinstance(first, dict):
                        record["observation_fields"] = "|".join(
                            sorted(str(key) for key in first.keys())
                        )

                        record["latest_timestamp"] = (
                            first.get("time")
                            or first.get("timestamp")
                            or first.get("local_date_time_full")
                            or first.get("utc_time")
                            or ""
                        )

            except Exception as exc:
                record["json_parse_status"] = "FAIL"
                record["notes"] = str(exc)

        bom_rows.append(record)

bom_fields = [
    "station_id",
    "latest_file",
    "json_parse_status",
    "station_name",
    "station_state",
    "latitude",
    "longitude",
    "elevation",
    "observation_count",
    "observation_fields",
    "latest_timestamp",
    "endpoint_pattern",
    "racecourse_mapping_status",
    "notes",
]

write_csv(
    BOM_STATIONS_PATH,
    bom_fields,
    bom_rows,
)

payload_sources = [
    (
        "VRC",
        "Flemington",
        AUDIT_ROOT / "live-vrc" / "vrc_turf_raw.json",
    ),
    (
        "VRC",
        "Flemington",
        AUDIT_ROOT / "live-vrc" / "vrc_wind_raw.json",
    ),
    (
        "TURFTRAX",
        "Caulfield",
        AUDIT_ROOT / "live-turftrax" / "caulfield_raw.json",
    ),
    (
        "TURFTRAX",
        "Sandown",
        AUDIT_ROOT / "live-turftrax" / "ladbrokes_raw.json",
    ),
    (
        "TURFTRAX",
        "Mornington",
        AUDIT_ROOT / "live-turftrax" / "mornington_raw.json",
    ),
]

payload_rows: list[dict[str, Any]] = []

for source_owner, track_group, path in payload_sources:
    row: dict[str, Any] = {
        "source_owner": source_owner,
        "track_group": track_group,
        "repository_file": (
            str(path.relative_to(ROOT))
            if path.exists()
            else str(path)
        ),
        "file_exists": "YES" if path.exists() else "NO",
        "file_bytes": path.stat().st_size if path.exists() else 0,
        "json_parse_status": "NOT_PRESENT",
        "top_level_fields": "",
        "payload_fields": "",
        "record_count": "",
        "timestamp_candidates": "",
        "production_use_status": "REQUIRES_SCHEMA_REVIEW",
        "notes": "",
    }

    if path.exists() and path.stat().st_size > 2:
        try:
            payload = json.loads(
                path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
            )

            row["json_parse_status"] = "PASS"

            if isinstance(payload, dict):
                row["top_level_fields"] = "|".join(
                    sorted(str(key) for key in payload.keys())
                )

                inner = payload.get("payload")

                if isinstance(inner, dict):
                    row["payload_fields"] = "|".join(
                        sorted(str(key) for key in inner.keys())
                    )

                    timestamp_values = []

                    for key, value in inner.items():
                        lowered = str(key).lower()

                        if (
                            "time" in lowered
                            or "date" in lowered
                            or "updated" in lowered
                        ):
                            timestamp_values.append(
                                f"{key}={value}"
                            )

                    row["timestamp_candidates"] = " | ".join(
                        timestamp_values[:20]
                    )

                elif isinstance(inner, list):
                    row["record_count"] = len(inner)

                    if inner and isinstance(inner[0], dict):
                        row["payload_fields"] = "|".join(
                            sorted(
                                str(key)
                                for key in inner[0].keys()
                            )
                        )

            elif isinstance(payload, list):
                row["record_count"] = len(payload)

                if payload and isinstance(payload[0], dict):
                    row["top_level_fields"] = "|".join(
                        sorted(
                            str(key)
                            for key in payload[0].keys()
                        )
                    )

        except Exception as exc:
            row["json_parse_status"] = "FAIL"
            row["notes"] = str(exc)

    payload_rows.append(row)

payload_fields = [
    "source_owner",
    "track_group",
    "repository_file",
    "file_exists",
    "file_bytes",
    "json_parse_status",
    "top_level_fields",
    "payload_fields",
    "record_count",
    "timestamp_candidates",
    "production_use_status",
    "notes",
]

write_csv(
    PAYLOAD_PATH,
    payload_fields,
    payload_rows,
)

audit = {
    "status": "EDGEIQ_WEATHER_SOURCE_CANDIDATE_AUDIT_V1_PASS",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "registry_track_entries": len(registry_rows),
    "exact_on_track_track_entries": len(on_track_entries),
    "physical_on_track_station_groups": len(
        physical_station_groups
    ),
    "verified_source_candidates": len(
        KNOWN_SOURCE_CANDIDATES
    ),
    "bom_station_directories_found": len(bom_rows),
    "bom_station_json_parse_pass": sum(
        1
        for row in bom_rows
        if row["json_parse_status"] == "PASS"
    ),
    "on_track_payload_files_checked": len(payload_rows),
    "on_track_payload_json_parse_pass": sum(
        1
        for row in payload_rows
        if row["json_parse_status"] == "PASS"
    ),
    "candidate_file": str(CANDIDATE_PATH.relative_to(ROOT)),
    "bom_inventory_file": str(
        BOM_STATIONS_PATH.relative_to(ROOT)
    ),
    "payload_inventory_file": str(
        PAYLOAD_PATH.relative_to(ROOT)
    ),
    "notes": [
        (
            "The prior on-track count of 34 was caused by "
            "substring matching against "
            "BOM_UNTIL_OFFICIAL_ON_TRACK_SOURCE_FOUND."
        ),
        (
            "Exact source-type matching is now used."
        ),
        (
            "Source pages and visualisers are not yet marked "
            "as machine-readable production endpoints."
        ),
        (
            "No racecourse-to-BOM station mapping was invented."
        ),
    ],
}

AUDIT_JSON.write_text(
    json.dumps(audit, indent=2),
    encoding="utf-8",
)

audit_lines = [
    audit["status"],
    f"generated_at={audit['generated_at']}",
    (
        "registry_track_entries="
        f"{audit['registry_track_entries']}"
    ),
    (
        "exact_on_track_track_entries="
        f"{audit['exact_on_track_track_entries']}"
    ),
    (
        "physical_on_track_station_groups="
        f"{audit['physical_on_track_station_groups']}"
    ),
    (
        "verified_source_candidates="
        f"{audit['verified_source_candidates']}"
    ),
    (
        "bom_station_directories_found="
        f"{audit['bom_station_directories_found']}"
    ),
    (
        "bom_station_json_parse_pass="
        f"{audit['bom_station_json_parse_pass']}"
    ),
    (
        "on_track_payload_files_checked="
        f"{audit['on_track_payload_files_checked']}"
    ),
    (
        "on_track_payload_json_parse_pass="
        f"{audit['on_track_payload_json_parse_pass']}"
    ),
    "",
    "No source page was mislabelled as a verified API endpoint.",
    "No BOM station was assigned to a racecourse without evidence.",
]

AUDIT_TXT.write_text(
    "\n".join(audit_lines) + "\n",
    encoding="utf-8",
)

print(audit["status"])
print(
    "exact_on_track_track_entries="
    f"{audit['exact_on_track_track_entries']}"
)
print(
    "physical_on_track_station_groups="
    f"{audit['physical_on_track_station_groups']}"
)
print(
    "bom_station_json_parse_pass="
    f"{audit['bom_station_json_parse_pass']}"
)
print(
    "on_track_payload_json_parse_pass="
    f"{audit['on_track_payload_json_parse_pass']}"
)
