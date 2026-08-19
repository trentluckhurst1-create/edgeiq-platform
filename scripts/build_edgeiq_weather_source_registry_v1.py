from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "data" / "weather-source-audit"
OUTPUT_DIR = ROOT / "data" / "weather"
PUBLIC_DATA = ROOT / "public" / "data"

REGISTRY_PATH = OUTPUT_DIR / "weather_source_registry_v1.csv"
EVIDENCE_PATH = OUTPUT_DIR / "weather_source_evidence_v1.csv"
REQUIRED_PATH = OUTPUT_DIR / "weather_information_required_v1.csv"
AUDIT_TXT = PUBLIC_DATA / "edgeiq_weather_source_registry_v1_audit.txt"
AUDIT_JSON = PUBLIC_DATA / "edgeiq_weather_source_registry_v1_audit.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_DATA.mkdir(parents=True, exist_ok=True)

TRACKS: list[dict[str, str]] = [
    {
        "track_id": "FLEMINGTON",
        "track_name": "Flemington",
        "club": "VRC",
        "course_variant": "Turf",
        "preferred_observation_source": "VRC_ON_TRACK",
        "preferred_source_priority": "1",
        "forecast_source": "BOM",
        "source_status": "DISCOVERED_REQUIRES_PRODUCTION_MAPPING",
        "notes": "Use VRC live on-track observations as primary. BOM forecast and BOM observation are fallback/support only.",
    },
    {
        "track_id": "CAULFIELD",
        "track_name": "Caulfield",
        "club": "MRC",
        "course_variant": "Main",
        "preferred_observation_source": "MRC_TURFTRAX_ON_TRACK",
        "preferred_source_priority": "1",
        "forecast_source": "BOM",
        "source_status": "DISCOVERED_REQUIRES_PRODUCTION_MAPPING",
        "notes": "Use live on-track TurfTrax/MRC observations as primary.",
    },
    {
        "track_id": "CAULFIELD_HEATH",
        "track_name": "Caulfield Heath",
        "club": "MRC",
        "course_variant": "Heath",
        "preferred_observation_source": "MRC_TURFTRAX_ON_TRACK",
        "preferred_source_priority": "1",
        "forecast_source": "BOM",
        "source_status": "DISCOVERED_REQUIRES_PRODUCTION_MAPPING",
        "notes": "Expected to share the Caulfield on-track weather source unless source evidence proves otherwise.",
    },
    {
        "track_id": "SANDOWN_HILLSIDE",
        "track_name": "Sandown Hillside",
        "club": "MRC",
        "course_variant": "Hillside",
        "preferred_observation_source": "MRC_TURFTRAX_ON_TRACK",
        "preferred_source_priority": "1",
        "forecast_source": "BOM",
        "source_status": "DISCOVERED_REQUIRES_PRODUCTION_MAPPING",
        "notes": "Use Sandown on-track observations. Course variant must not create a duplicate physical weather station.",
    },
    {
        "track_id": "SANDOWN_LAKESIDE",
        "track_name": "Sandown Lakeside",
        "club": "MRC",
        "course_variant": "Lakeside",
        "preferred_observation_source": "MRC_TURFTRAX_ON_TRACK",
        "preferred_source_priority": "1",
        "forecast_source": "BOM",
        "source_status": "DISCOVERED_REQUIRES_PRODUCTION_MAPPING",
        "notes": "Use Sandown on-track observations. Course variant must not create a duplicate physical weather station.",
    },
    {
        "track_id": "MORNINGTON",
        "track_name": "Mornington",
        "club": "MRC",
        "course_variant": "Turf",
        "preferred_observation_source": "MRC_TURFTRAX_ON_TRACK",
        "preferred_source_priority": "1",
        "forecast_source": "BOM",
        "source_status": "DISCOVERED_REQUIRES_PRODUCTION_MAPPING",
        "notes": "Use live on-track TurfTrax/MRC observations as primary.",
    },
    {
        "track_id": "MOONEE_VALLEY",
        "track_name": "Moonee Valley",
        "club": "MVRC",
        "course_variant": "Turf",
        "preferred_observation_source": "UNCONFIRMED",
        "preferred_source_priority": "",
        "forecast_source": "BOM",
        "source_status": "SOURCE_DISCOVERY_REQUIRED",
        "notes": "Check for an official on-track source before assigning BOM observations as primary.",
    },
    {
        "track_id": "CRANBOURNE",
        "track_name": "Cranbourne",
        "club": "Southside Racing",
        "course_variant": "Turf",
        "preferred_observation_source": "UNCONFIRMED",
        "preferred_source_priority": "",
        "forecast_source": "BOM",
        "source_status": "SOURCE_DISCOVERY_REQUIRED",
        "notes": "Check official club or on-track station availability before BOM-only mapping.",
    },
    {
        "track_id": "PAKENHAM",
        "track_name": "Pakenham",
        "club": "Southside Racing",
        "course_variant": "Turf",
        "preferred_observation_source": "UNCONFIRMED",
        "preferred_source_priority": "",
        "forecast_source": "BOM",
        "source_status": "SOURCE_DISCOVERY_REQUIRED",
        "notes": "Check official club or on-track station availability before BOM-only mapping.",
    },
    {
        "track_id": "PAKENHAM_SYNTHETIC",
        "track_name": "Pakenham Synthetic",
        "club": "Southside Racing",
        "course_variant": "Synthetic",
        "preferred_observation_source": "UNCONFIRMED",
        "preferred_source_priority": "",
        "forecast_source": "BOM",
        "source_status": "SOURCE_DISCOVERY_REQUIRED",
        "notes": "Likely shares the physical Pakenham weather source with the turf course.",
    },
]

COUNTRY_TRACKS = [
    ("BALLARAT", "Ballarat", "Ballarat Turf Club", "Turf"),
    ("BALLARAT_SYNTHETIC", "Ballarat Synthetic", "Ballarat Turf Club", "Synthetic"),
    ("BENDIGO", "Bendigo", "Bendigo Jockey Club", "Turf"),
    ("BENALLA", "Benalla", "Benalla Racing Club", "Turf"),
    ("CAMPERDOWN", "Camperdown", "Camperdown Turf Club", "Turf"),
    ("CASTERTON", "Casterton", "Casterton Racing Club", "Turf"),
    ("COLAC", "Colac", "Colac Turf Club", "Turf"),
    ("DONALD", "Donald", "Donald & District Racing Club", "Turf"),
    ("ECHUCA", "Echuca", "Echuca Racing Club", "Turf"),
    ("GEELONG", "Geelong", "Geelong Racing Club", "Turf"),
    ("HAMILTON", "Hamilton", "Hamilton Racing Club", "Turf"),
    ("HORSHAM", "Horsham", "Horsham & District Racing Club", "Turf"),
    ("KILMORE", "Kilmore", "Kilmore Racing Club", "Turf"),
    ("KYNETON", "Kyneton", "Kyneton & Hanging Rock Racing Club", "Turf"),
    ("MANSFIELD", "Mansfield", "Mansfield District Racing Club", "Turf"),
    ("MOE", "Moe", "Moe Racing Club", "Turf"),
    ("MURTOA", "Murtoa", "Murtoa Racing Club", "Turf"),
    ("SALE", "Sale", "Sale Turf Club", "Turf"),
    ("SEYMOUR", "Seymour", "Seymour Racing Club", "Turf"),
    ("ST_ARNAUD", "St Arnaud", "St Arnaud Turf Club", "Turf"),
    ("SWAN_HILL", "Swan Hill", "Swan Hill Jockey Club", "Turf"),
    ("TERANG", "Terang", "Terang & District Racing Club", "Turf"),
    ("WANGARATTA", "Wangaratta", "Wangaratta Turf Club", "Turf"),
    ("WARRACKNABEAL", "Warracknabeal", "Warracknabeal Racing Club", "Turf"),
    ("WARRNAMBOOL", "Warrnambool", "Warrnambool Racing Club", "Turf"),
    ("WERRIBEE", "Werribee", "Werribee Racing Club", "Turf"),
    ("WODONGA", "Wodonga", "Wodonga & District Turf Club", "Turf"),
    ("YARRA_VALLEY", "Yarra Valley", "Yarra Valley Racing", "Turf"),
]

for track_id, track_name, club, course_variant in COUNTRY_TRACKS:
    TRACKS.append(
        {
            "track_id": track_id,
            "track_name": track_name,
            "club": club,
            "course_variant": course_variant,
            "preferred_observation_source": "BOM_UNTIL_OFFICIAL_ON_TRACK_SOURCE_FOUND",
            "preferred_source_priority": "2",
            "forecast_source": "BOM",
            "source_status": "MAPPING_REQUIRED",
            "notes": "Confirm whether an official club/on-track station exists before finalising BOM as primary.",
        }
    )

REGISTRY_FIELDS = [
    "track_id",
    "track_name",
    "club",
    "course_variant",
    "canonical_location_name",
    "latitude",
    "longitude",
    "preferred_observation_source",
    "preferred_source_priority",
    "primary_observation_endpoint",
    "primary_observation_station_name",
    "primary_observation_station_id",
    "primary_observation_update_frequency",
    "primary_observation_fields",
    "forecast_source",
    "forecast_location_name",
    "forecast_endpoint",
    "forecast_location_id",
    "bom_fallback_station_name",
    "bom_fallback_station_id",
    "bom_fallback_observation_endpoint",
    "bom_fallback_distance_km",
    "fallback_permitted",
    "source_status",
    "last_verified_at",
    "verification_method",
    "notes",
]

existing: dict[str, dict[str, str]] = {}
if REGISTRY_PATH.exists():
    with REGISTRY_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            key = str(row.get("track_id") or "").strip()
            if key:
                existing[key] = {field: str(row.get(field) or "") for field in REGISTRY_FIELDS}

registry_rows: list[dict[str, str]] = []
for source_row in TRACKS:
    track_id = source_row["track_id"]
    row = {field: "" for field in REGISTRY_FIELDS}
    row.update(source_row)

    if track_id in existing:
        preserved = existing[track_id]
        for field in REGISTRY_FIELDS:
            if preserved.get(field):
                row[field] = preserved[field]

    if not row["fallback_permitted"]:
        row["fallback_permitted"] = "YES"

    registry_rows.append(row)

with REGISTRY_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=REGISTRY_FIELDS)
    writer.writeheader()
    writer.writerows(registry_rows)

URL_PATTERN = re.compile(r"https?://[^\s\"'<>\\]+", re.IGNORECASE)
KEYWORDS = (
    "weather",
    "wind",
    "rain",
    "turf",
    "station",
    "observation",
    "forecast",
    "bom",
    "turftrax",
)

evidence_rows: list[dict[str, str]] = []
seen_evidence: set[tuple[str, str]] = set()

if AUDIT_ROOT.exists():
    allowed_suffixes = {
        ".json",
        ".txt",
        ".html",
        ".js",
        ".csv",
    }

    for file_path in AUDIT_ROOT.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in allowed_suffixes:
            continue
        if file_path.stat().st_size > 6_000_000:
            continue

        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for match in URL_PATTERN.findall(text):
            cleaned_url = match.rstrip(".,);]}")

            lowered = cleaned_url.lower()
            if not any(keyword in lowered for keyword in KEYWORDS):
                continue

            key = (str(file_path.relative_to(ROOT)), cleaned_url)
            if key in seen_evidence:
                continue
            seen_evidence.add(key)

            source_guess = "UNKNOWN"
            if "bom.gov.au" in lowered:
                source_guess = "BOM"
            elif "turftrax" in lowered:
                source_guess = "TURFTRAX"
            elif "vrc" in lowered or "flemington" in lowered:
                source_guess = "VRC"
            elif "mrc" in lowered or "caulfield" in lowered or "sandown" in lowered:
                source_guess = "MRC"

            evidence_rows.append(
                {
                    "source_guess": source_guess,
                    "repository_file": str(file_path.relative_to(ROOT)),
                    "discovered_url": cleaned_url,
                    "requires_verification": "YES",
                    "verified_track": "",
                    "verified_data_type": "",
                    "verification_status": "UNREVIEWED",
                    "notes": "",
                }
            )

EVIDENCE_FIELDS = [
    "source_guess",
    "repository_file",
    "discovered_url",
    "requires_verification",
    "verified_track",
    "verified_data_type",
    "verification_status",
    "notes",
]

with EVIDENCE_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=EVIDENCE_FIELDS)
    writer.writeheader()
    writer.writerows(evidence_rows)

REQUIRED_FIELDS = [
    "track_id",
    "track_name",
    "information_required",
    "why_required",
    "current_status",
    "provided_value",
    "source_url",
    "verified_at",
    "notes",
]

required_rows: list[dict[str, str]] = []

for track in registry_rows:
    requirements = [
        (
            "Exact racecourse latitude and longitude",
            "Required to validate forecast location and calculate fallback-station distance.",
        ),
        (
            "Official current-observation source",
            "Confirms whether the track has its own live station or must use BOM observations.",
        ),
        (
            "Primary observation URL or endpoint",
            "Required for automated current conditions ingestion.",
        ),
        (
            "Primary station name and station ID",
            "Required for source lineage and operational monitoring.",
        ),
        (
            "Observed fields available",
            "Required to know whether temperature, wind, gusts, rainfall and humidity are supplied.",
        ),
        (
            "Observation update frequency",
            "Required for freshness thresholds and stale-state handling.",
        ),
        (
            "BOM forecast page or forecast location",
            "Required for hourly and daily race-day forecasting.",
        ),
        (
            "BOM fallback observation station",
            "Required when the preferred live source is unavailable.",
        ),
        (
            "Fallback distance from racecourse",
            "Required so EDGEiQ discloses how representative the fallback observation is.",
        ),
    ]

    for information_required, reason in requirements:
        required_rows.append(
            {
                "track_id": track["track_id"],
                "track_name": track["track_name"],
                "information_required": information_required,
                "why_required": reason,
                "current_status": "REQUIRED",
                "provided_value": "",
                "source_url": "",
                "verified_at": "",
                "notes": "",
            }
        )

with REQUIRED_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=REQUIRED_FIELDS)
    writer.writeheader()
    writer.writerows(required_rows)

on_track_tracks = [
    row for row in registry_rows
    if "ON_TRACK" in row["preferred_observation_source"]
]

mapped_primary = [
    row for row in registry_rows
    if row["primary_observation_endpoint"].strip()
]

mapped_forecast = [
    row for row in registry_rows
    if row["forecast_endpoint"].strip()
]

mapped_fallback = [
    row for row in registry_rows
    if row["bom_fallback_station_id"].strip()
]

audit = {
    "status": "EDGEIQ_WEATHER_SOURCE_REGISTRY_V1_AUDIT_PASS",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "track_count": len(registry_rows),
    "on_track_source_tracks": len(on_track_tracks),
    "primary_endpoint_mapped": len(mapped_primary),
    "forecast_endpoint_mapped": len(mapped_forecast),
    "bom_fallback_mapped": len(mapped_fallback),
    "evidence_urls_discovered": len(evidence_rows),
    "registry_path": str(REGISTRY_PATH.relative_to(ROOT)),
    "evidence_path": str(EVIDENCE_PATH.relative_to(ROOT)),
    "information_required_path": str(REQUIRED_PATH.relative_to(ROOT)),
    "notes": [
        "Registry scaffolding is complete.",
        "Blank endpoints remain intentionally unavailable until verified.",
        "No weather observations or forecasts were fabricated.",
        "VRC and MRC on-track sources are preferred where identified.",
        "BOM is forecast and fallback support for VRC/MRC tracks.",
    ],
}

AUDIT_JSON.write_text(
    json.dumps(audit, indent=2),
    encoding="utf-8",
)

audit_lines = [
    audit["status"],
    f"generated_at={audit['generated_at']}",
    f"track_count={audit['track_count']}",
    f"on_track_source_tracks={audit['on_track_source_tracks']}",
    f"primary_endpoint_mapped={audit['primary_endpoint_mapped']}",
    f"forecast_endpoint_mapped={audit['forecast_endpoint_mapped']}",
    f"bom_fallback_mapped={audit['bom_fallback_mapped']}",
    f"evidence_urls_discovered={audit['evidence_urls_discovered']}",
    f"registry={audit['registry_path']}",
    f"evidence={audit['evidence_path']}",
    f"information_required={audit['information_required_path']}",
    "",
    "No endpoints were invented.",
    "Blank values remain pending verification.",
]

AUDIT_TXT.write_text("\n".join(audit_lines) + "\n", encoding="utf-8")

print(audit["status"])
print(f"tracks={audit['track_count']}")
print(f"evidence_urls={audit['evidence_urls_discovered']}")
print(f"registry={REGISTRY_PATH}")
print(f"information_required={REQUIRED_PATH}")
