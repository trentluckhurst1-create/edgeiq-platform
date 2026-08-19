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
