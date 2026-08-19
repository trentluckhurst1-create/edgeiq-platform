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

SCHEMA_PATH = WEATHER_DIR / "weather_payload_deep_schema_v1.csv"
VALUE_PATH = WEATHER_DIR / "weather_payload_candidate_values_v1.csv"
BOM_SCHEMA_PATH = WEATHER_DIR / "bom_payload_deep_schema_v1.csv"
AUDIT_TXT = PUBLIC_DIR / "edgeiq_weather_payload_schema_v1_audit.txt"
AUDIT_JSON = PUBLIC_DIR / "edgeiq_weather_payload_schema_v1_audit.json"

WEATHER_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

WEATHER_KEYWORDS = (
    "temp",
    "temperature",
    "apparent",
    "humidity",
    "humid",
    "wind",
    "gust",
    "rain",
    "rainfall",
    "precip",
    "pressure",
    "dew",
    "weather",
    "condition",
    "track",
    "going",
    "moisture",
    "timestamp",
    "updated",
    "update",
    "time",
    "date",
    "station",
    "latitude",
    "longitude",
    "lat",
    "lon",
)

SOURCE_FILES = [
    {
        "source_owner": "VRC",
        "track_group": "Flemington",
        "path": AUDIT_ROOT / "live-vrc" / "vrc_turf_raw.json",
    },
    {
        "source_owner": "TURFTRAX",
        "track_group": "Caulfield",
        "path": AUDIT_ROOT / "live-turftrax" / "caulfield_raw.json",
    },
    {
        "source_owner": "TURFTRAX",
        "track_group": "Sandown",
        "path": AUDIT_ROOT / "live-turftrax" / "ladbrokes_raw.json",
    },
    {
        "source_owner": "TURFTRAX",
        "track_group": "Mornington",
        "path": AUDIT_ROOT / "live-turftrax" / "mornington_raw.json",
    },
]

BOM_FILES = [
    {
        "station_id": station_id,
        "path": AUDIT_ROOT / "bom-live" / station_id / "latest_raw.json",
    }
    for station_id in ("87184", "89002", "90173", "94852")
]


def scalar_preview(value: Any, limit: int = 300) -> str:
    if value is None:
        return ""

    if isinstance(value, bool):
        text = "true" if value else "false"
    else:
        text = str(value)

    text = text.replace("\r", " ").replace("\n", " ").strip()

    if len(text) > limit:
        return text[:limit] + "..."

    return text


def detect_json_string(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    stripped = value.strip()

    if not stripped:
        return value

    if not (
        (stripped.startswith("{") and stripped.endswith("}"))
        or
        (stripped.startswith("[") and stripped.endswith("]"))
    ):
        return value

    try:
        return json.loads(stripped)
    except Exception:
        return value


def walk(
    value: Any,
    path: str,
    rows: list[dict[str, str]],
    candidates: list[dict[str, str]],
    source_owner: str,
    source_name: str,
    repository_file: str,
    depth: int = 0,
    max_depth: int = 12,
) -> None:
    if depth > max_depth:
        return

    decoded = detect_json_string(value)

    if decoded is not value:
        rows.append(
            {
                "source_owner": source_owner,
                "source_name": source_name,
                "repository_file": repository_file,
                "json_path": path,
                "value_type": "json_encoded_string",
                "container_size": "",
                "value_preview": scalar_preview(value),
                "depth": str(depth),
            }
        )

        walk(
            decoded,
            f"{path}.__decoded__",
            rows,
            candidates,
            source_owner,
            source_name,
            repository_file,
            depth + 1,
            max_depth,
        )
        return

    if isinstance(decoded, dict):
        rows.append(
            {
                "source_owner": source_owner,
                "source_name": source_name,
                "repository_file": repository_file,
                "json_path": path,
                "value_type": "object",
                "container_size": str(len(decoded)),
                "value_preview": "",
                "depth": str(depth),
            }
        )

        for key, child in decoded.items():
            child_path = f"{path}.{key}" if path else str(key)

            walk(
                child,
                child_path,
                rows,
                candidates,
                source_owner,
                source_name,
                repository_file,
                depth + 1,
                max_depth,
            )

        return

    if isinstance(decoded, list):
        rows.append(
            {
                "source_owner": source_owner,
                "source_name": source_name,
                "repository_file": repository_file,
                "json_path": path,
                "value_type": "array",
                "container_size": str(len(decoded)),
                "value_preview": "",
                "depth": str(depth),
            }
        )

        for index, child in enumerate(decoded[:20]):
            child_path = f"{path}[{index}]"

            walk(
                child,
                child_path,
                rows,
                candidates,
                source_owner,
                source_name,
                repository_file,
                depth + 1,
                max_depth,
            )

        return

    value_type = type(decoded).__name__

    rows.append(
        {
            "source_owner": source_owner,
            "source_name": source_name,
            "repository_file": repository_file,
            "json_path": path,
            "value_type": value_type,
            "container_size": "",
            "value_preview": scalar_preview(decoded),
            "depth": str(depth),
        }
    )

    lowered_path = path.lower()

    if any(keyword in lowered_path for keyword in WEATHER_KEYWORDS):
        candidates.append(
            {
                "source_owner": source_owner,
                "source_name": source_name,
                "repository_file": repository_file,
                "json_path": path,
                "candidate_field": path.split(".")[-1],
                "value_type": value_type,
                "value": scalar_preview(decoded, 1000),
                "candidate_category": classify_candidate(lowered_path),
                "verification_status": "UNREVIEWED",
                "canonical_target_field": "",
                "notes": "",
            }
        )


def classify_candidate(path: str) -> str:
    checks = [
        ("TEMPERATURE", ("temp", "temperature")),
        ("APPARENT_TEMPERATURE", ("apparent", "feels")),
        ("HUMIDITY", ("humidity", "humid")),
        ("WIND_GUST", ("gust",)),
        ("WIND", ("wind",)),
        ("RAINFALL", ("rain", "precip")),
        ("PRESSURE", ("pressure",)),
        ("DEW_POINT", ("dew",)),
        ("TIMESTAMP", ("timestamp", "updated", "update", "time", "date")),
        ("STATION", ("station", "stn")),
        ("LATITUDE", ("latitude", ".lat")),
        ("LONGITUDE", ("longitude", ".lon")),
        ("TRACK", ("track", "going", "moisture")),
    ]

    for category, keywords in checks:
        if any(keyword in path for keyword in keywords):
            return category

    return "OTHER"


def write_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, str]],
) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


schema_rows: list[dict[str, str]] = []
candidate_rows: list[dict[str, str]] = []
bom_rows: list[dict[str, str]] = []

for source in SOURCE_FILES:
    path = source["path"]

    if not path.exists() or path.stat().st_size <= 2:
        continue

    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        continue

    walk(
        payload,
        "$",
        schema_rows,
        candidate_rows,
        source["source_owner"],
        source["track_group"],
        str(path.relative_to(ROOT)),
    )

for source in BOM_FILES:
    path = source["path"]

    if not path.exists() or path.stat().st_size <= 2:
        continue

    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        continue

    temporary_candidates: list[dict[str, str]] = []

    walk(
        payload,
        "$",
        bom_rows,
        temporary_candidates,
        "BOM",
        source["station_id"],
        str(path.relative_to(ROOT)),
    )

    candidate_rows.extend(temporary_candidates)

schema_fields = [
    "source_owner",
    "source_name",
    "repository_file",
    "json_path",
    "value_type",
    "container_size",
    "value_preview",
    "depth",
]

candidate_fields = [
    "source_owner",
    "source_name",
    "repository_file",
    "json_path",
    "candidate_field",
    "value_type",
    "value",
    "candidate_category",
    "verification_status",
    "canonical_target_field",
    "notes",
]

write_csv(SCHEMA_PATH, schema_fields, schema_rows)
write_csv(BOM_SCHEMA_PATH, schema_fields, bom_rows)
write_csv(VALUE_PATH, candidate_fields, candidate_rows)

category_counts: dict[str, int] = {}

for row in candidate_rows:
    category = row["candidate_category"]
    category_counts[category] = category_counts.get(category, 0) + 1

audit = {
    "status": "EDGEIQ_WEATHER_PAYLOAD_SCHEMA_V1_AUDIT_PASS",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "on_track_schema_rows": len(schema_rows),
    "bom_schema_rows": len(bom_rows),
    "candidate_value_rows": len(candidate_rows),
    "candidate_category_counts": category_counts,
    "schema_path": str(SCHEMA_PATH.relative_to(ROOT)),
    "bom_schema_path": str(BOM_SCHEMA_PATH.relative_to(ROOT)),
    "candidate_values_path": str(VALUE_PATH.relative_to(ROOT)),
    "notes": [
        "Nested dictionaries, arrays, and JSON-encoded strings were inspected.",
        "Only candidate values were extracted.",
        "No candidate field has yet been declared canonical.",
        "No track-to-BOM station mapping was created.",
    ],
}

AUDIT_JSON.write_text(
    json.dumps(audit, indent=2),
    encoding="utf-8",
)

lines = [
    audit["status"],
    f"generated_at={audit['generated_at']}",
    f"on_track_schema_rows={audit['on_track_schema_rows']}",
    f"bom_schema_rows={audit['bom_schema_rows']}",
    f"candidate_value_rows={audit['candidate_value_rows']}",
    "",
    "CANDIDATE CATEGORY COUNTS",
]

for category in sorted(category_counts):
    lines.append(f"{category}={category_counts[category]}")

lines.extend(
    [
        "",
        "No candidate has been promoted to production.",
        "No station has been assigned to a racecourse.",
    ]
)

AUDIT_TXT.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
)

print(audit["status"])
print(f"on_track_schema_rows={len(schema_rows)}")
print(f"bom_schema_rows={len(bom_rows)}")
print(f"candidate_value_rows={len(candidate_rows)}")
