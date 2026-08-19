from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "weather" / "weather_source_registry_v1.csv"
CONTRACT_CSV = ROOT / "data" / "weather" / "turftrax_live_request_contract_candidates_v1.csv"
GOVERNED_JSON = ROOT / "public" / "data" / "edgeiq_on_track_weather_governed_v1_2.json"

TRACK_TO_IDS = {
    "Flemington": ["FLEMINGTON"],
    "Caulfield": ["CAULFIELD", "CAULFIELD_HEATH"],
    "Sandown": ["SANDOWN_HILLSIDE", "SANDOWN_LAKESIDE"],
    "Mornington": ["MORNINGTON"],
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    registry_rows = read_csv(REGISTRY)
    contracts = {row["track_group"]: row for row in read_csv(CONTRACT_CSV)}
    governed = json.loads(GOVERNED_JSON.read_text(encoding="utf-8")) if GOVERNED_JSON.exists() else {"records": []}
    governed_by_track = {row["track_group"]: row for row in governed.get("records", [])}
    verified_at = datetime.now(timezone.utc).isoformat()
    updated = 0
    for row in registry_rows:
        for track_group, ids in TRACK_TO_IDS.items():
            if row.get("track_id") not in ids:
                continue
            contract = contracts.get(track_group)
            governed_row = governed_by_track.get(track_group)
            if not contract or contract.get("verification_status") != "PROVEN_FROM_CLIENT_CODE":
                continue
            row["primary_observation_endpoint"] = contract.get("request_url", "")
            row["primary_observation_station_id"] = governed_row.get("station_id", "") if governed_row else ""
            row["primary_observation_update_frequency"] = f"{contract.get('polling_interval_seconds', '')} seconds"
            row["primary_observation_fields"] = "temperature_c|humidity_percent|wind_speed_kmh|wind_direction_text|wind_gust_kmh|rain_today_mm|rain_24h_mm|rain_7d_mm|weather_comment|going_report"
            row["source_status"] = "VERIFIED_PRODUCTION_ENDPOINT"
            row["last_verified_at"] = verified_at
            row["verification_method"] = "client-code trace + one-shot safe live probe + governed schema audit"
            updated += 1
    fieldnames = list(registry_rows[0].keys()) if registry_rows else []
    with REGISTRY.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(registry_rows)
    print(f"EDGEIQ_WEATHER_SOURCE_REGISTRY_LIVE_ENDPOINT_UPDATE_V1 updated_rows={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
