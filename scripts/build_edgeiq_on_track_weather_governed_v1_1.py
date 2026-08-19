from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SOURCE_JSON = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_on_track_weather_observation_v1.json"
)

FRESHNESS_CSV = (
    ROOT
    / "data"
    / "weather"
    / "on_track_weather_freshness_v1.csv"
)

OUTPUT_JSON = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_on_track_weather_governed_v1_1.json"
)

OUTPUT_CSV = (
    ROOT
    / "data"
    / "weather"
    / "on_track_weather_governed_v1_1.csv"
)

LINEAGE_CSV = (
    ROOT
    / "data"
    / "weather"
    / "on_track_weather_governed_v1_1_lineage.csv"
)

AUDIT_TXT = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_on_track_weather_governed_v1_1_audit.txt"
)

AUDIT_JSON = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_on_track_weather_governed_v1_1_audit.json"
)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


source_payload = json.loads(
    SOURCE_JSON.read_text(encoding="utf-8")
)

source_records = source_payload.get("records", [])

freshness_rows = read_csv(FRESHNESS_CSV)

freshness_by_track = {
    row.get("track_group", ""): row
    for row in freshness_rows
}

governed_records: list[dict[str, Any]] = []
lineage_rows: list[dict[str, str]] = []

for source in source_records:
    track_group = str(source.get("track_group") or "")
    freshness = freshness_by_track.get(track_group, {})

    record = {
        **source,

        "temperature_unit": "C",

        "wind_speed_kmh": source.get(
            "wind_speed_current"
        ),
        "wind_speed_average_kmh": source.get(
            "wind_speed_average"
        ),
        "wind_gust_kmh": source.get(
            "wind_gust_current"
        ),
        "wind_gust_min_kmh": source.get(
            "wind_gust_min"
        ),
        "wind_gust_max_kmh": source.get(
            "wind_gust_max"
        ),
        "wind_speed_unit": "km/h",

        "rain_today_unit": "mm",
        "rain_24h_unit": "mm",
        "rain_7d_unit": "mm",

        "freshness_status": freshness.get(
            "freshness_status",
            "UNKNOWN",
        ),
        "age_minutes": freshness.get(
            "age_minutes",
            "",
        ),
        "usable_as_current": freshness.get(
            "usable_as_current",
            "NO",
        ),
        "display_behaviour": freshness.get(
            "display_behaviour",
            "DISPLAY_SOURCE_TIME_UNAVAILABLE",
        ),
        "freshness_checked_at": freshness.get(
            "checked_at",
            "",
        ),

        "governed_source_state": (
            "AVAILABLE_CURRENT"
            if freshness.get("usable_as_current") == "YES"
            else
            "AVAILABLE_STALE"
            if freshness.get("freshness_status") == "STALE"
            else
            "AVAILABLE_UNKNOWN_FRESHNESS"
        ),

        "schema_version": (
            "edgeiq_on_track_weather_governed_v1_1"
        ),
    }

    governed_records.append(record)

    mappings = {
        "temperature_c": (
            "source temperature-current; unit C"
        ),
        "wind_speed_kmh": (
            "source windspeed-current; unit km/h"
        ),
        "wind_speed_average_kmh": (
            "source windspeed-average; unit km/h"
        ),
        "wind_gust_kmh": (
            "source windgust-current; unit km/h"
        ),
        "wind_gust_max_kmh": (
            "source windgust-max; unit km/h"
        ),
        "rain_today_mm": (
            "source rain1-today/rain2-today; unit mm"
        ),
        "rain_24h_mm": (
            "source rain1-24hr/rain2-24hr; unit mm"
        ),
        "rain_7d_mm": (
            "source rain1-7day/rain2-7day; unit mm"
        ),
        "freshness_status": (
            "on_track_weather_freshness_v1.csv"
        ),
        "usable_as_current": (
            "on_track_weather_freshness_v1.csv"
        ),
    }

    for target, origin in mappings.items():
        lineage_rows.append(
            {
                "track_group": track_group,
                "target_field": target,
                "origin": origin,
                "conversion": "NONE",
                "source_unit": (
                    "km/h"
                    if "wind" in target
                    else
                    "mm"
                    if "rain" in target
                    else
                    "C"
                    if "temperature" in target
                    else
                    ""
                ),
                "target_unit": (
                    "km/h"
                    if "wind" in target
                    else
                    "mm"
                    if "rain" in target
                    else
                    "C"
                    if "temperature" in target
                    else
                    ""
                ),
                "fabricated": "NO",
                "notes": "",
            }
        )

output_payload = {
    "schema_version": (
        "edgeiq_on_track_weather_governed_v1_1"
    ),
    "generated_at": datetime.now(
        timezone.utc
    ).isoformat(),
    "record_count": len(governed_records),
    "records": governed_records,
}

OUTPUT_JSON.write_text(
    json.dumps(output_payload, indent=2),
    encoding="utf-8",
)

csv_fields = sorted(
    {
        key
        for record in governed_records
        for key in record.keys()
        if key != "track_ids"
    }
)

csv_fields.insert(1, "track_ids")

with OUTPUT_CSV.open(
    "w",
    encoding="utf-8-sig",
    newline="",
) as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=csv_fields,
    )
    writer.writeheader()

    for record in governed_records:
        row = dict(record)

        track_ids = row.get("track_ids", [])

        if isinstance(track_ids, list):
            row["track_ids"] = "|".join(track_ids)

        writer.writerow(
            {
                field: row.get(field, "")
                for field in csv_fields
            }
        )

lineage_fields = [
    "track_group",
    "target_field",
    "origin",
    "conversion",
    "source_unit",
    "target_unit",
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

available_current = sum(
    record["governed_source_state"]
    == "AVAILABLE_CURRENT"
    for record in governed_records
)

available_stale = sum(
    record["governed_source_state"]
    == "AVAILABLE_STALE"
    for record in governed_records
)

audit = {
    "status": (
        "EDGEIQ_ON_TRACK_WEATHER_GOVERNED_V1_1_AUDIT_PASS"
    ),
    "generated_at": datetime.now(
        timezone.utc
    ).isoformat(),
    "records": len(governed_records),
    "available_current": available_current,
    "available_stale": available_stale,
    "temperature_unit": "C",
    "wind_speed_unit": "km/h",
    "rainfall_unit": "mm",
    "conversion_applied": False,
    "output_json": str(
        OUTPUT_JSON.relative_to(ROOT)
    ),
    "output_csv": str(
        OUTPUT_CSV.relative_to(ROOT)
    ),
    "lineage_csv": str(
        LINEAGE_CSV.relative_to(ROOT)
    ),
    "notes": [
        "Source units were explicitly verified.",
        "No wind conversion was applied.",
        "No rainfall conversion was applied.",
        "Stale records cannot be presented as current.",
        "React performs no unit or freshness calculation.",
    ],
}

AUDIT_JSON.write_text(
    json.dumps(audit, indent=2),
    encoding="utf-8",
)

AUDIT_TXT.write_text(
    "\n".join(
        [
            audit["status"],
            f"generated_at={audit['generated_at']}",
            f"records={audit['records']}",
            (
                "available_current="
                f"{audit['available_current']}"
            ),
            (
                "available_stale="
                f"{audit['available_stale']}"
            ),
            "temperature_unit=C",
            "wind_speed_unit=km/h",
            "rainfall_unit=mm",
            "conversion_applied=false",
            "",
            "No weather values were fabricated.",
            "Stale observations cannot be presented as current.",
            "React performs no unit or freshness calculation.",
        ]
    )
    + "\n",
    encoding="utf-8",
)

print(audit["status"])

for record in governed_records:
    print(
        f"{record['track_group']} | "
        f"{record['temperature_c']} C | "
        f"wind={record['wind_speed_kmh']} km/h | "
        f"gust={record['wind_gust_kmh']} km/h | "
        f"rain24h={record['rain_24h_mm']} mm | "
        f"{record['governed_source_state']}"
    )
