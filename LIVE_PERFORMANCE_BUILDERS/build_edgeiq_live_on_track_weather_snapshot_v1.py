from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROBE_JSON = ROOT / "public" / "data" / "edgeiq_live_on_track_weather_probe_v1.json"
OUT_JSON = ROOT / "data" / "weather" / "live_raw_on_track_weather_v1.json"
OUT_CSV = ROOT / "data" / "weather" / "live_raw_on_track_weather_v1.csv"
STATUS_CSV = ROOT / "data" / "weather" / "live_raw_on_track_weather_source_status_v1.csv"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def content_from(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    if isinstance(payload.get("content"), dict):
        return payload["content"]
    nested = payload.get("payload")
    if isinstance(nested, dict) and isinstance(nested.get("content"), dict):
        return nested["content"]
    return {}


def tardis_from(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    if isinstance(payload.get("tardis"), dict):
        return payload["tardis"]
    nested = payload.get("payload")
    if isinstance(nested, dict) and isinstance(nested.get("tardis"), dict):
        return nested["tardis"]
    return {}


def header_from(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    if isinstance(payload.get("header"), dict):
        return payload["header"]
    nested = payload.get("payload")
    if isinstance(nested, dict) and isinstance(nested.get("header"), dict):
        return nested["header"]
    return {}


def main() -> int:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    probe = load_json(PROBE_JSON) if PROBE_JSON.exists() else {"records": []}
    records = []
    statuses = []
    for probe_row in probe.get("records", []):
        raw_file = ROOT / str(probe_row.get("raw_response_file", ""))
        payload = None
        if raw_file.exists() and raw_file.suffix.lower() == ".json":
            payload = load_json(raw_file)
        content = content_from(payload)
        status = "LIVE_UNAVAILABLE"
        if probe_row.get("accessibility") == "LIVE_RESPONSE_OK" and content:
            status = "LIVE_AVAILABLE"
        elif probe_row.get("accessibility") == "SOURCE_ERROR":
            status = "SOURCE_ERROR"
        elif probe_row.get("http_status") and int(probe_row.get("http_status")) in {401, 403}:
            status = "ACCESS_BLOCKED"
        elif probe_row.get("schema_status") not in {"SCHEMA_OK", "SCHEMA_PARTIAL"}:
            status = "SCHEMA_CHANGED"
        record = {
            "track_group": probe_row.get("track_group"),
            "source_page": probe_row.get("source_page"),
            "live_request_url": probe_row.get("request_url"),
            "method": probe_row.get("method"),
            "fetched_at": probe_row.get("timestamp"),
            "http_status": probe_row.get("http_status"),
            "content_type": probe_row.get("content_type"),
            "byte_count": probe_row.get("byte_count"),
            "source_status": status,
            "raw_response_file": probe_row.get("raw_response_file"),
            "headers_file": probe_row.get("response_headers_file"),
            "header": header_from(payload),
            "content": content,
            "tardis": tardis_from(payload),
            "schema_status": probe_row.get("schema_status"),
            "schema_fields": probe_row.get("schema_fields", []),
        }
        records.append(record)
        statuses.append({
            "track_group": record["track_group"],
            "source_status": status,
            "http_status": record["http_status"],
            "schema_status": record["schema_status"],
            "raw_response_file": record["raw_response_file"],
            "notes": "Raw source preserved; no weather values fabricated.",
        })
    payload = {
        "schema_version": "edgeiq_live_raw_on_track_weather_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "records": records,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    csv_fields = ["track_group", "source_page", "live_request_url", "method", "fetched_at", "http_status", "content_type", "byte_count", "source_status", "raw_response_file", "headers_file", "schema_status"]
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for record in records:
            writer.writerow({field: record.get(field, "") for field in csv_fields})
    status_fields = ["track_group", "source_status", "http_status", "schema_status", "raw_response_file", "notes"]
    with STATUS_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=status_fields)
        writer.writeheader()
        writer.writerows(statuses)
    print("EDGEIQ_LIVE_RAW_ON_TRACK_WEATHER_SNAPSHOT_V1_BUILT")
    for row in statuses:
        print(f"{row['track_group']} | {row['source_status']} | {row['schema_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
