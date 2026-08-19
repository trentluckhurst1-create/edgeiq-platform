from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_CSV = ROOT / "data" / "weather" / "turftrax_live_request_contract_candidates_v1.csv"
LIVE_ROOT = ROOT / "data" / "weather-source-live"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_live_on_track_weather_probe_v1.txt"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_live_on_track_weather_probe_v1.json"

USER_AGENT = "EDGEiQ/1.0 live-on-track-weather-one-shot-probe (production-readiness audit; polite single request)"


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def read_contract_rows() -> list[dict[str, str]]:
    if not CONTRACT_CSV.exists():
        return []
    with CONTRACT_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def schema_status(track_group: str, payload: Any) -> tuple[str, list[str]]:
    if not isinstance(payload, dict):
        return "NOT_JSON_OBJECT", []
    content = payload.get("content")
    if not isinstance(content, dict) and isinstance(payload.get("payload"), dict):
        content = payload["payload"].get("content")
    if not isinstance(content, dict):
        return "CONTENT_OBJECT_MISSING", []
    fields = sorted(content.keys())
    critical = [
        key for key in fields
        if key in {
            "temperature-current",
            "air-temperature-current",
            "humidity-current",
            "windspeed-current",
            "winddirection-text",
            "rain1-24hr",
            "rain2-24hr",
            "weather-last-update",
            "weather-date",
        }
    ]
    if len(critical) >= 3:
        return "SCHEMA_OK", critical
    return "SCHEMA_PARTIAL", critical


def main() -> int:
    rows = [row for row in read_contract_rows() if row.get("verification_status") == "PROVEN_FROM_CLIENT_CODE"]
    LIVE_ROOT.mkdir(parents=True, exist_ok=True)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results: list[dict[str, Any]] = []
    for row in rows:
        track_group = row["track_group"]
        source_dir = LIVE_ROOT / slug(track_group) / timestamp
        source_dir.mkdir(parents=True, exist_ok=True)
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-AU,en;q=0.9",
            "Referer": row["source_page"],
        }
        if row["track_group"] == "Flemington":
            headers["X-Requested-With"] = "XMLHttpRequest"
        result: dict[str, Any] = {
            "track_group": track_group,
            "request_url": row["request_url"],
            "method": row["method"],
            "source_page": row["source_page"],
            "timestamp": timestamp,
            "raw_dir": str(source_dir.relative_to(ROOT)),
            "request_headers": headers,
            "safe_probe_policy": "one request, connect timeout 10s, read timeout 20s, no retries",
        }
        try:
            response = requests.get(row["request_url"], headers=headers, timeout=(10, 20))
            result["http_status"] = response.status_code
            result["content_type"] = response.headers.get("Content-Type", "")
            result["byte_count"] = len(response.content)
            result["response_headers_file"] = str((source_dir / "headers.json").relative_to(ROOT))
            (source_dir / "headers.json").write_text(json.dumps(dict(response.headers), indent=2), encoding="utf-8")
            parsed = None
            raw_suffix = "txt"
            try:
                parsed = response.json()
                raw_suffix = "json"
                (source_dir / "raw_response.json").write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
                result["json_parse"] = "OK"
            except Exception as exc:
                (source_dir / "raw_response.txt").write_text(response.text, encoding="utf-8", errors="ignore")
                result["json_parse"] = f"FAILED: {exc}"
            result["raw_response_file"] = str((source_dir / f"raw_response.{raw_suffix}").relative_to(ROOT))
            if parsed is not None:
                status, fields = schema_status(track_group, parsed)
                result["schema_status"] = status
                result["schema_fields"] = fields
                result["accessibility"] = "LIVE_RESPONSE_OK" if response.ok else "HTTP_ERROR"
            else:
                result["schema_status"] = "UNPARSED"
                result["schema_fields"] = []
                result["accessibility"] = "NON_JSON_RESPONSE" if response.ok else "HTTP_ERROR"
        except Exception as exc:
            result["accessibility"] = "SOURCE_ERROR"
            result["error"] = str(exc)
        results.append(result)
    payload = {
        "schema_version": "edgeiq_live_on_track_weather_probe_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records": results,
        "audit_status": "EDGEIQ_LIVE_ON_TRACK_WEATHER_PROBE_V1_PASS" if all(r.get("accessibility") == "LIVE_RESPONSE_OK" and r.get("schema_status") in {"SCHEMA_OK", "SCHEMA_PARTIAL"} for r in results) else "EDGEIQ_LIVE_ON_TRACK_WEATHER_PROBE_V1_WARN",
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [payload["audit_status"], f"generated_at={payload['generated_at']}", f"records={len(results)}", ""]
    for result in results:
        lines.extend([
            f"{result['track_group']}: {result.get('accessibility')} {result.get('http_status')} {result.get('content_type')} bytes={result.get('byte_count')}",
            f"  schema={result.get('schema_status')} fields={','.join(result.get('schema_fields', []))}",
            f"  raw={result.get('raw_response_file')}",
            "",
        ])
    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")
    print(payload["audit_status"])
    for result in results:
        print(f"{result['track_group']} | {result.get('accessibility')} | {result.get('http_status')} | {result.get('schema_status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
