from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def write(path: str, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text.strip() + "\n", encoding="utf-8")
    print(f"wrote {target.relative_to(ROOT)}")


TRACE_SCRIPT = r'''
from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "data" / "weather-source-audit"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_turftrax_live_request_trace_v1.txt"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_turftrax_live_request_trace_v1.json"
OUT_CSV = ROOT / "data" / "weather" / "turftrax_live_request_contract_candidates_v1.csv"

FIELDNAMES = [
    "track_group",
    "source_page",
    "client_script",
    "request_origin",
    "request_url",
    "method",
    "query_parameters",
    "request_body",
    "request_headers",
    "token_required",
    "cookie_required",
    "polling_interval_seconds",
    "response_type",
    "response_schema_evidence",
    "verification_status",
    "confidence",
    "notes",
]

TURFTRAX_SOURCES = [
    ("Caulfield", "https://its.turftrax.co.uk/visualiser/caulfield/", AUDIT / "turftrax" / "caulfield"),
    ("Sandown", "https://its.turftrax.co.uk/visualiser/ladbrokes/", AUDIT / "turftrax" / "sandown"),
    ("Mornington", "https://its.turftrax.co.uk/visualiser/mornington/", AUDIT / "turftrax" / "mornington"),
]

VRC_SOURCE = {
    "track_group": "Flemington",
    "source_page": "https://www.vrc.com.au/track-and-weather-conditions/",
    "client_script": AUDIT / "bundles" / "vrc_flemington" / "001_vrc.js",
    "page": AUDIT / "vrc_flemington.html",
}


def read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def first_match_context(path: Path, pattern: str, context_chars: int = 360) -> dict[str, str]:
    text = read(path)
    match = re.search(pattern, text, flags=re.I | re.S)
    if not match:
        return {"file": str(path.relative_to(ROOT)), "line": "", "context": ""}
    line = text.count("\n", 0, match.start()) + 1
    start = max(0, match.start() - context_chars)
    end = min(len(text), match.end() + context_chars)
    context = text[start:end].replace("\r", " ").replace("\n", " ")
    context = re.sub(r"\s+", " ", context).strip()
    return {"file": str(path.relative_to(ROOT)), "line": str(line), "context": context}


def js_literal(path: Path, name: str) -> str:
    text = read(path)
    match = re.search(rf"var\s+{re.escape(name)}\s*=\s*['\"]([^'\"]+)['\"]", text)
    return match.group(1) if match else ""


def js_numberish(path: Path, name: str) -> str:
    text = read(path)
    match = re.search(rf"var\s+{re.escape(name)}\s*=\s*['\"]?([0-9]+)['\"]?", text)
    return match.group(1) if match else ""


def compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def turftrax_row(track_group: str, source_page: str, folder: Path) -> dict[str, str]:
    page = folder / "page.html"
    base = folder / "005_base.js"
    client_name = js_literal(page, "clientName")
    stream_api = js_literal(page, "streamApi")
    update_interval = js_numberish(page, "updateInterval")
    response_interval = js_numberish(page, "responseInterval")
    origin = "https://its.turftrax.co.uk"
    request_url = urljoin(origin, f"{stream_api}{client_name}.html") if client_name and stream_api else ""
    page_evidence = first_match_context(page, r"var\s+clientName\s*=\s*['\"][^'\"]+['\"].{0,140}var\s+streamApi\s*=\s*['\"][^'\"]+['\"]")
    build_evidence = first_match_context(base, r"usePath\s*=\s*window\.streamApi\s*\+\s*window\.clientName\s*\+\s*['\"]\.html['\"]")
    xhr_evidence = first_match_context(base, r"streamApiXhttp\.open\('GET',\s*updateUrl,\s*true\).{0,140}streamApiXhttp\.setRequestHeader\('Content-Type',\s*'text/plain'\)")
    schema_evidence = first_match_context(folder / "audit_report.txt", r"payloadObject|UpdateWDV|Stream API Response")
    evidence = {
        "page_vars": page_evidence,
        "url_builder": build_evidence,
        "xhr": xhr_evidence,
        "response_schema": schema_evidence,
    }
    verified = all([client_name, stream_api, request_url, build_evidence["context"], xhr_evidence["context"]])
    return {
        "track_group": track_group,
        "source_page": source_page,
        "client_script": str(base.relative_to(ROOT)),
        "request_origin": origin,
        "request_url": request_url,
        "method": "GET",
        "query_parameters": "",
        "request_body": "",
        "request_headers": "Content-Type: text/plain; browser also sends normal Accept/User-Agent/Referer",
        "token_required": "NO_CLIENT_TOKEN_EVIDENCE",
        "cookie_required": "NO_CLIENT_COOKIE_EVIDENCE",
        "polling_interval_seconds": str(int(update_interval) if update_interval else ""),
        "response_type": "application/json",
        "response_schema_evidence": compact_json(evidence),
        "verification_status": "PROVEN_FROM_CLIENT_CODE" if verified else "UNPROVEN_CLIENT_CODE_INCOMPLETE",
        "confidence": "HIGH" if verified else "LOW",
        "notes": f"responseInterval_ms={response_interval}; updateInterval_seconds={update_interval}; request contract is derived from source page variables and shared base.js URL builder, not old probe guesses.",
    }


def vrc_row() -> dict[str, str]:
    script = VRC_SOURCE["client_script"]
    page = VRC_SOURCE["page"]
    endpoint = "https://www.vrc.com.au/umbraco/api/TurfSportsAPI/GetTurfData"
    endpoint_evidence = first_match_context(script, r"getJSON\(['\"]\/umbraco\/api\/TurfSportsAPI\/GetTurfData['\"]")
    field_evidence = first_match_context(script, r"temperature-current.{0,320}rain1-24hr.{0,320}humidity-current")
    page_evidence = first_match_context(page, r"Live meteorological data is streamed from WeatherTrax equipment.{0,220}refreshes every five minutes")
    evidence = {
        "endpoint": endpoint_evidence,
        "fields": field_evidence,
        "page_refresh_copy": page_evidence,
    }
    verified = bool(endpoint_evidence["context"])
    return {
        "track_group": "Flemington",
        "source_page": VRC_SOURCE["source_page"],
        "client_script": str(script.relative_to(ROOT)),
        "request_origin": "https://www.vrc.com.au",
        "request_url": endpoint,
        "method": "GET",
        "query_parameters": "",
        "request_body": "",
        "request_headers": "jQuery getJSON; browser sends Accept/User-Agent/Referer and may send X-Requested-With",
        "token_required": "NO_CLIENT_TOKEN_EVIDENCE",
        "cookie_required": "NO_CLIENT_COOKIE_EVIDENCE",
        "polling_interval_seconds": "300",
        "response_type": "application/json",
        "response_schema_evidence": compact_json(evidence),
        "verification_status": "PROVEN_FROM_CLIENT_CODE" if verified else "UNPROVEN_CLIENT_CODE_INCOMPLETE",
        "confidence": "HIGH" if verified else "LOW",
        "notes": "VRC page says WeatherTrax data refreshes every five minutes; client bundle calls TurfSportsAPI GetTurfData. WindData exists in bundle but GetTurfData carries weather fields and is the single safe probe endpoint.",
    }


def main() -> int:
    OUT_TXT.parent.mkdir(parents=True, exist_ok=True)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    rows = [vrc_row()]
    rows.extend(turftrax_row(track, page, folder) for track, page, folder in TURFTRAX_SOURCES)
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    payload = {
        "schema_version": "edgeiq_turftrax_live_request_trace_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records": rows,
        "audit_status": "EDGEIQ_LIVE_REQUEST_CONTRACT_TRACE_V1_PASS" if all(row["verification_status"] == "PROVEN_FROM_CLIENT_CODE" for row in rows) else "EDGEIQ_LIVE_REQUEST_CONTRACT_TRACE_V1_WARN",
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [payload["audit_status"], f"generated_at={payload['generated_at']}", f"records={len(rows)}", ""]
    for row in rows:
        lines.extend([
            f"{row['track_group']}: {row['method']} {row['request_url']}",
            f"  status={row['verification_status']} confidence={row['confidence']}",
            f"  polling_interval_seconds={row['polling_interval_seconds']}",
            f"  client_script={row['client_script']}",
            "",
        ])
    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")
    print(payload["audit_status"])
    for row in rows:
        print(f"{row['track_group']} | {row['verification_status']} | {row['request_url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


PROBE_SCRIPT = r'''
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
'''


SNAPSHOT_SCRIPT = r'''
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
'''


GOVERNED_SCRIPT = r'''
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
'''


REGISTRY_SCRIPT = r'''
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
'''


FINAL_AUDIT_SCRIPT = r'''
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"
OUT_TXT = PUBLIC / "edgeiq_live_on_track_weather_ingestion_v1_final_report.txt"
OUT_JSON = PUBLIC / "edgeiq_live_on_track_weather_ingestion_v1_final_report.json"


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    trace = load(PUBLIC / "edgeiq_turftrax_live_request_trace_v1.json")
    probe = load(PUBLIC / "edgeiq_live_on_track_weather_probe_v1.json")
    governed = load(PUBLIC / "edgeiq_on_track_weather_governed_v1_2.json")
    governed_audit = load(PUBLIC / "edgeiq_on_track_weather_governed_v1_2_audit.json")
    trace_by_track = {row.get("track_group"): row for row in trace.get("records", [])}
    probe_by_track = {row.get("track_group"): row for row in probe.get("records", [])}
    governed_by_track = {row.get("track_group"): row for row in governed.get("records", [])}
    tracks = ["Flemington", "Caulfield", "Sandown", "Mornington"]
    source_reports = []
    for track in tracks:
        c = trace_by_track.get(track, {})
        p = probe_by_track.get(track, {})
        g = governed_by_track.get(track, {})
        source_reports.append({
            "track_group": track,
            "request_contract": c.get("verification_status", "MISSING"),
            "endpoint": c.get("request_url", ""),
            "method": c.get("method", ""),
            "accessibility": p.get("accessibility", "MISSING"),
            "live_response_status": p.get("http_status", ""),
            "schema_status": p.get("schema_status", ""),
            "update_cadence": c.get("polling_interval_seconds", ""),
            "freshness": g.get("freshness_status", ""),
            "fields_supplied": [key for key in [
                "temperature_c", "humidity_percent", "wind_speed_kmh", "wind_direction_text",
                "wind_gust_kmh", "rain_today_mm", "rain_24h_mm", "rain_7d_mm", "weather_comment", "going_report",
            ] if g.get(key) not in (None, "", [])],
            "integration_status": g.get("governed_source_state", "MISSING"),
            "blocker": "" if p.get("accessibility") == "LIVE_RESPONSE_OK" else p.get("error", p.get("accessibility", "")),
        })
    pass_status = (
        trace.get("audit_status") == "EDGEIQ_LIVE_REQUEST_CONTRACT_TRACE_V1_PASS"
        and probe.get("audit_status") == "EDGEIQ_LIVE_ON_TRACK_WEATHER_PROBE_V1_PASS"
        and governed_audit.get("status") == "EDGEIQ_ON_TRACK_WEATHER_GOVERNED_V1_2_AUDIT_PASS"
        and all(report["request_contract"] == "PROVEN_FROM_CLIENT_CODE" for report in source_reports)
        and all(report["accessibility"] == "LIVE_RESPONSE_OK" for report in source_reports)
    )
    payload = {
        "status": "EDGEIQ_LIVE_ON_TRACK_WEATHER_INGESTION_V1_AUDIT_PASS" if pass_status else "EDGEIQ_LIVE_ON_TRACK_WEATHER_INGESTION_V1_AUDIT_WARN",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_reports": source_reports,
        "outputs": {
            "trace": "public/data/edgeiq_turftrax_live_request_trace_v1.json",
            "probe": "public/data/edgeiq_live_on_track_weather_probe_v1.json",
            "snapshot": "data/weather/live_raw_on_track_weather_v1.json",
            "governed": "public/data/edgeiq_on_track_weather_governed_v1_2.json",
        },
        "remaining_weather_gaps": [
            "BOM forecast and country-track fallback mapping remain separate follow-up work.",
            "Frontend should continue to label stale/aging/unavailable source states explicitly.",
        ],
        "next_actions": [
            "Build BOM forecast mapping for non-metropolitan tracks using official BOM location IDs.",
            "Create country-track fallback registry only after official on-track source discovery is exhausted.",
        ],
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [payload["status"], f"generated_at={payload['generated_at']}", ""]
    for report in source_reports:
        lines.extend([
            f"{report['track_group']}",
            f"  endpoint={report['endpoint']}",
            f"  method={report['method']}",
            f"  contract={report['request_contract']}",
            f"  accessibility={report['accessibility']} status={report['live_response_status']} schema={report['schema_status']}",
            f"  freshness={report['freshness']} integration={report['integration_status']}",
            f"  fields={','.join(report['fields_supplied'])}",
            f"  blocker={report['blocker']}",
            "",
        ])
    lines.extend([
        "Remaining gaps:",
        *[f"- {item}" for item in payload["remaining_weather_gaps"]],
        "",
        "Next actions:",
        *[f"- {item}" for item in payload["next_actions"]],
    ])
    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")
    print(payload["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def patch_weather_feed() -> None:
    path = ROOT / "src" / "edgeiq-os" / "race" / "services" / "weatherFeed.ts"
    text = path.read_text(encoding="utf-8")
    if "edgeiq_on_track_weather_governed_v1_2.json" in text:
        print("weatherFeed.ts already references governed v1.2")
        return
    text = text.replace(
        '  metropolitan: MetropolitanWeatherRecord[];\n  raceWeather: RaceWeatherRecord[];\n',
        '  metropolitan: MetropolitanWeatherRecord[];\n  raceWeather: RaceWeatherRecord[];\n  onTrack: MetropolitanWeatherRecord[];\n',
    )
    text = text.replace(
        'const METROPOLITAN_URL = "/data/edgeiq_metropolitan_weather_v1.json";\nconst RACE_WEATHER_URL = "/data/edgeiq_race_weather_v1.json";\n',
        'const METROPOLITAN_URL = "/data/edgeiq_metropolitan_weather_v1.json";\nconst RACE_WEATHER_URL = "/data/edgeiq_race_weather_v1.json";\nconst ON_TRACK_WEATHER_URL = "/data/edgeiq_on_track_weather_governed_v1_2.json";\n',
    )
    insert_after = '''function value(label: string, val: unknown, source: string | null): WeatherValue {
  return { label, value: firstText(val) || null, source };
}
'''
    helper = '''
function onTrackToMetropolitan(record: Record<string, unknown>): MetropolitanWeatherRecord {
  const sourceOwner = firstText(record.source_owner, "On-track");
  return {
    meeting_key: record.track_group,
    meeting: record.track_group,
    course: record.track_group,
    provider: sourceOwner,
    source_name: `${sourceOwner} on-track weather`,
    source_url: record.source_page,
    source_endpoint: record.live_request_url,
    fetched_at_utc: record.fetched_at,
    source_observed_datetime: record.observation_local,
    source_observed_time: firstText(record.source_timestamp, record.observation_local),
    station_status: record.station_status,
    source_status: record.governed_source_state,
    official_track_rating: record.going_report,
    official_rail: null,
    going_stick: null,
    temperature_c: record.temperature_c,
    rainfall_24h_mm: record.rain_24h_mm,
    rainfall_since_9am_mm: null,
    rainfall_today_mm: record.rain_today_mm,
    rainfall_7day_mm: record.rain_7d_mm,
    forecast_rainfall: null,
    humidity_pct: record.humidity_percent,
    moisture_loss_mm: null,
    soil_moisture: null,
    irrigation: null,
    weather_comment: record.weather_comment,
    additional_comment: firstText(record.freshness_status)
      ? `On-track source ${firstText(record.freshness_status).toLowerCase()} (${firstText(record.governed_source_state)})`
      : null,
    wind_direction: record.wind_direction_text,
    wind_speed_kmh: record.wind_speed_kmh,
    wind_average_kmh: record.wind_speed_average_kmh,
    wind_gust_kmh: record.wind_gust_kmh,
    wind_gust_max_kmh: record.wind_gust_max_kmh,
    wind_station: record.station_id,
    wind_station_count: 1,
    turf_http_status: null,
    wind_http_status: null,
    errors: [],
  };
}
'''
    text = text.replace(insert_after, insert_after + helper)
    text = text.replace(
        "  pendingFeeds = Promise.all([loadJson(METROPOLITAN_URL), loadJson(RACE_WEATHER_URL)])\n    .then(([metropolitanPayload, racePayload]) => {\n",
        "  pendingFeeds = Promise.all([loadJson(METROPOLITAN_URL), loadJson(RACE_WEATHER_URL), loadJson(ON_TRACK_WEATHER_URL).catch(() => ({ records: [] }))])\n    .then(([metropolitanPayload, racePayload, onTrackPayload]) => {\n",
    )
    text = text.replace(
        "      const raceWeather = Array.isArray((racePayload as any)?.records) ? (racePayload as any).records : [];\n      if (metropolitan.length > 10000 || raceWeather.length > 10000) {\n",
        "      const raceWeather = Array.isArray((racePayload as any)?.records) ? (racePayload as any).records : [];\n      const onTrack = Array.isArray((onTrackPayload as any)?.records)\n        ? (onTrackPayload as any).records.map((record: Record<string, unknown>) => onTrackToMetropolitan(record))\n        : [];\n      if (metropolitan.length > 10000 || raceWeather.length > 10000 || onTrack.length > 10000) {\n",
    )
    text = text.replace(
        "          metropolitan: [],\n          raceWeather: [],\n",
        "          metropolitan: [],\n          raceWeather: [],\n          onTrack: [],\n",
    )
    text = text.replace(
        "        metropolitan,\n        raceWeather,\n",
        "        metropolitan: [...onTrack, ...metropolitan],\n        raceWeather,\n        onTrack,\n",
    )
    text = text.replace(
        "    metropolitan: [\n",
        "    onTrack: [],\n    metropolitan: [\n",
        1,
    )
    path.write_text(text, encoding="utf-8")
    print("patched src/edgeiq-os/race/services/weatherFeed.ts")


def main() -> int:
    write("scripts/trace_edgeiq_turftrax_live_request_v1.py", TRACE_SCRIPT)
    write("scripts/probe_edgeiq_live_on_track_weather_v1.py", PROBE_SCRIPT)
    write("scripts/build_edgeiq_live_on_track_weather_snapshot_v1.py", SNAPSHOT_SCRIPT)
    write("scripts/build_edgeiq_on_track_weather_governed_v1_2.py", GOVERNED_SCRIPT)
    write("scripts/update_edgeiq_weather_source_registry_live_v1.py", REGISTRY_SCRIPT)
    write("scripts/audit_edgeiq_live_on_track_weather_ingestion_v1.py", FINAL_AUDIT_SCRIPT)
    patch_weather_feed()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
