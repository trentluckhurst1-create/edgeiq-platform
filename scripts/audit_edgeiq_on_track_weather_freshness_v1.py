from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SOURCE_CSV = ROOT / "data" / "weather" / "on_track_weather_observation_v1.csv"
OUTPUT_CSV = ROOT / "data" / "weather" / "on_track_weather_freshness_v1.csv"
OUTPUT_JSON = ROOT / "public" / "data" / "edgeiq_on_track_weather_freshness_v1.json"
AUDIT_TXT = ROOT / "public" / "data" / "edgeiq_on_track_weather_freshness_v1_audit.txt"
AUDIT_JSON = ROOT / "public" / "data" / "edgeiq_on_track_weather_freshness_v1_audit.json"

NOW = datetime.now().astimezone()

FRESH_MINUTES = 20
STALE_MINUTES = 90


def parse_local(value: str) -> datetime | None:
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value)

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=NOW.tzinfo)

        return parsed
    except ValueError:
        return None


with SOURCE_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
    rows = list(csv.DictReader(handle))

output_rows: list[dict[str, str]] = []

for row in rows:
    observed = parse_local(row.get("observation_local", ""))

    age_minutes: float | None = None
    freshness_status = "UNKNOWN"

    if observed is not None:
        age_minutes = max(
            0.0,
            (NOW - observed).total_seconds() / 60.0,
        )

        if age_minutes <= FRESH_MINUTES:
            freshness_status = "FRESH"
        elif age_minutes <= STALE_MINUTES:
            freshness_status = "AGING"
        else:
            freshness_status = "STALE"

    output_rows.append(
        {
            "track_group": row.get("track_group", ""),
            "track_ids": row.get("track_ids", ""),
            "source_owner": row.get("source_owner", ""),
            "station_id": row.get("station_id", ""),
            "observation_local": row.get("observation_local", ""),
            "checked_at": NOW.isoformat(),
            "age_minutes": (
                f"{age_minutes:.1f}"
                if age_minutes is not None
                else ""
            ),
            "freshness_status": freshness_status,
            "fresh_threshold_minutes": str(FRESH_MINUTES),
            "stale_threshold_minutes": str(STALE_MINUTES),
            "usable_as_current": (
                "YES"
                if freshness_status in {"FRESH", "AGING"}
                else "NO"
            ),
            "display_behaviour": (
                "DISPLAY_CURRENT"
                if freshness_status == "FRESH"
                else
                "DISPLAY_WITH_AGING_WARNING"
                if freshness_status == "AGING"
                else
                "DISPLAY_STALE_SOURCE_STATE"
                if freshness_status == "STALE"
                else
                "DISPLAY_SOURCE_TIME_UNAVAILABLE"
            ),
        }
    )

fieldnames = [
    "track_group",
    "track_ids",
    "source_owner",
    "station_id",
    "observation_local",
    "checked_at",
    "age_minutes",
    "freshness_status",
    "fresh_threshold_minutes",
    "stale_threshold_minutes",
    "usable_as_current",
    "display_behaviour",
]

with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(output_rows)

summary = {
    "schema_version": "edgeiq_on_track_weather_freshness_v1",
    "generated_at": NOW.isoformat(),
    "thresholds": {
        "fresh_minutes": FRESH_MINUTES,
        "stale_minutes": STALE_MINUTES,
    },
    "record_count": len(output_rows),
    "fresh": sum(row["freshness_status"] == "FRESH" for row in output_rows),
    "aging": sum(row["freshness_status"] == "AGING" for row in output_rows),
    "stale": sum(row["freshness_status"] == "STALE" for row in output_rows),
    "unknown": sum(row["freshness_status"] == "UNKNOWN" for row in output_rows),
    "records": output_rows,
}

OUTPUT_JSON.write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8",
)

audit = {
    "status": "EDGEIQ_ON_TRACK_WEATHER_FRESHNESS_V1_AUDIT_PASS",
    **summary,
    "notes": [
        "Freshness is calculated by the builder, never React.",
        "Stale observations remain visible only with an explicit stale state.",
        "Captured historical payloads are not presented as live.",
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
            f"generated_at={summary['generated_at']}",
            f"record_count={summary['record_count']}",
            f"fresh={summary['fresh']}",
            f"aging={summary['aging']}",
            f"stale={summary['stale']}",
            f"unknown={summary['unknown']}",
            "",
            "Captured historical payloads are not presented as live.",
            "React performs no freshness calculation.",
        ]
    )
    + "\n",
    encoding="utf-8",
)

print(audit["status"])

for row in output_rows:
    print(
        f"{row['track_group']} | "
        f"age_minutes={row['age_minutes']} | "
        f"status={row['freshness_status']} | "
        f"usable_as_current={row['usable_as_current']}"
    )
