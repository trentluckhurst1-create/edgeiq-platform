from __future__ import annotations

import csv
import hashlib
import json
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
DISCOVERY_DIR = ROOT / "docs" / "performance-intelligence" / "racingcom-source-discovery"
RAW_DIR = ROOT / "outputs" / "performance-intelligence" / "racingcom-source-discovery" / "raw" / "fresh-source-poc"
PUBLIC_DATA = ROOT / "public" / "data"

FIXTURE_CONTRACT = DISCOVERY_DIR / "edgeiq_racingcom_speed_data_fixture_contract_v1.csv"
NETWORK_LEDGER = DISCOVERY_DIR / "edgeiq_racingcom_network_response_ledger_v1.csv"
REQUEST_LEDGER = DISCOVERY_DIR / "edgeiq_racingcom_network_request_ledger_v1.csv"
STATIC_LEDGER = DISCOVERY_DIR / "edgeiq_racingcom_static_response_ledger_v1.csv"
VALIDATION_LEDGER = DISCOVERY_DIR / "edgeiq_racingcom_source_candidate_validation_v1.csv"

POC_OUT = PUBLIC_DATA / "edgeiq_racingcom_fresh_speed_payload_poc_v1.csv"
AUDIT_OUT = DISCOVERY_DIR / "edgeiq_racingcom_fresh_source_poc_audit_v1.csv"
SUMMARY_OUT = DISCOVERY_DIR / "edgeiq_racingcom_fresh_source_poc_summary_v1.json"
REPORT_OUT = DISCOVERY_DIR / "edgeiq_racingcom_fresh_source_poc_report_v1.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_filename(prefix: str, fixture_id: str, url: str, suffix: str) -> str:
    seed = f"{fixture_id}|{url}".encode("utf-8", errors="ignore")
    return f"{prefix}_{hashlib.sha256(seed).hexdigest()[:12]}{suffix}"


def fetch_url(url: str, fixture_id: str, suffix: str, extra_headers: dict[str, str] | None = None) -> tuple[bool, int | str, str, str, str]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = RAW_DIR / safe_filename("poc", fixture_id, url, suffix)
    headers = {
        "User-Agent": "EDGEiQ-Racing/1.0 governed-source-poc",
        "Accept": "application/json,text/csv,text/plain,*/*",
    }
    for key, value in (extra_headers or {}).items():
        lower = key.lower()
        if lower in {"cookie", "authorization", "proxy-authorization", "x-auth-token", "set-cookie"}:
            continue
        if lower in {"x-api-key", "referer", "content-type", "user-agent", "accept"} and value:
            headers[key] = value
    req = urllib.request.Request(
        url,
        headers=headers,
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read()
            status = getattr(response, "status", 200)
            content_type = response.headers.get("Content-Type", "")
            cache_path.write_bytes(body)
            return True, status, content_type, str(cache_path.relative_to(ROOT)), sha256_bytes(body)
    except Exception as exc:
        return False, f"ERROR:{type(exc).__name__}", str(exc), "", ""


def parse_graphql_payload(body: bytes) -> dict[str, Any] | None:
    try:
        return json.loads(body.decode("utf-8", errors="ignore"))
    except Exception:
        return None


def parse_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def parse_graphql_rows(
    fixture: dict[str, str],
    url: str,
    cache_path: str,
    sha256: str,
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    decoded_url = unquote(url)
    meet_match = re.search(r'meetCode:\s*"([^"]+)"', decoded_url)
    race_match = re.search(r"raceNumber\s*:\s*(\d+)", decoded_url)
    meet_code = meet_match.group(1) if meet_match else ""
    query_race_no = race_match.group(1) if race_match else ""
    race = payload.get("data", {}).get("sectionaltimes_callback") or {}
    for horse in race.get("Horses") or []:
        if not isinstance(horse, dict):
            continue
        horse_name = clean(horse.get("FullName"))
        raw_horse = json.dumps(horse, ensure_ascii=False)
        for section in horse.get("SectionalTimes") or []:
            if not isinstance(section, dict):
                continue
            avg_speed_mps = parse_float(section.get("AvgSpeed"))
            rows.append(
                {
                    "fixture_id": fixture.get("fixture_id", ""),
                    "race_date": fixture.get("race_date", ""),
                    "track": fixture.get("track", ""),
                    "race_no": fixture.get("race_no", ""),
                    "meet_code": meet_code,
                    "query_race_no": query_race_no,
                    "source_format": "GRAPHQL_JSON",
                    "source_candidate_id": "GRAPHQL_SECTIONALTIMES_GETRACEFORM",
                    "source_url": url,
                    "source_cache_path": cache_path,
                    "source_sha256": sha256,
                    "horse": horse_name,
                    "saddle_number": clean(horse.get("SaddleNumber")),
                    "runner_source_id": clean(horse.get("id")),
                    "trainer": clean(horse.get("Trainer")),
                    "jockey": clean(horse.get("Jockey")),
                    "final_position": clean(horse.get("FinalPosition")),
                    "section_distance_label": clean(section.get("Distance")),
                    "section_position": clean(section.get("Position")),
                    "section_time": clean(section.get("Time")),
                    "avg_speed_mps": avg_speed_mps if avg_speed_mps is not None else "",
                    "avg_speed_kmh": round(avg_speed_mps * 3.6, 3) if avg_speed_mps is not None else "",
                    "raw_record_json": json.dumps(section, ensure_ascii=False),
                    "raw_runner_json": raw_horse[:5000],
                    "normalisation_status": "NORMALISED_GRAPHQL_SECTIONAL",
                    "identity_status": "RACE_AND_RUNNER_IDENTIFIED" if meet_code and query_race_no == fixture.get("race_no", "") and horse_name else "IDENTITY_REVIEW_REQUIRED",
                    "semantics_status": "SOURCE_MPS_DISPLAY_KMH_CONVERSION",
                }
            )
    return rows


def parse_historical_csv_rows(
    fixture: dict[str, str],
    url: str,
    cache_path: str,
    sha256: str,
    body: bytes,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    text = body.decode("utf-8-sig", errors="ignore")
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return rows
    meta = lines[0].split(";")
    for line in lines[1:]:
        parts = line.split(";")
        if len(parts) < 5:
            continue
        horse = clean(parts[0])
        final_position = clean(parts[1])
        triples = parts[2:]
        for idx in range(0, len(triples) - 2, 3):
            distance = clean(triples[idx])
            speed_mps = parse_float(triples[idx + 1])
            section_time = clean(triples[idx + 2])
            if not distance and speed_mps is None and not section_time:
                continue
            rows.append(
                {
                    "fixture_id": fixture.get("fixture_id", ""),
                    "race_date": fixture.get("race_date", ""),
                    "track": fixture.get("track", ""),
                    "race_no": fixture.get("race_no", ""),
                    "meet_code": "",
                    "query_race_no": "",
                    "source_format": "HISTORICAL_CSV",
                    "source_candidate_id": "HISTORICAL_DIRECT_CSV",
                    "source_url": url,
                    "source_cache_path": cache_path,
                    "source_sha256": sha256,
                    "horse": horse,
                    "saddle_number": "",
                    "runner_source_id": "",
                    "trainer": "",
                    "jockey": "",
                    "final_position": final_position,
                    "section_distance_label": f"{distance}m" if distance.isdigit() else distance,
                    "section_position": "",
                    "section_time": section_time,
                    "avg_speed_mps": speed_mps if speed_mps is not None else "",
                    "avg_speed_kmh": round(speed_mps * 3.6, 3) if speed_mps is not None else "",
                    "raw_record_json": json.dumps({"distance": distance, "speed_mps": speed_mps, "time": section_time}, ensure_ascii=False),
                    "raw_runner_json": json.dumps({"metadata": meta, "runner_line": parts}, ensure_ascii=False)[:5000],
                    "normalisation_status": "NORMALISED_HISTORICAL_CSV_SECTIONAL",
                    "identity_status": "RACE_AND_RUNNER_IDENTIFIED" if horse else "IDENTITY_REVIEW_REQUIRED",
                    "semantics_status": "SOURCE_MPS_DISPLAY_KMH_CONVERSION",
                }
            )
    return rows


def main() -> None:
    built_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for old_file in RAW_DIR.glob("*"):
        if old_file.is_file():
            old_file.unlink()
    fixtures = read_csv(FIXTURE_CONTRACT)
    network = read_csv(NETWORK_LEDGER)
    requests = read_csv(REQUEST_LEDGER)
    static = read_csv(STATIC_LEDGER)
    validation = read_csv(VALIDATION_LEDGER)
    fixtures_by_id = {row.get("fixture_id", ""): row for row in fixtures}

    admitted_graphql_urls: dict[str, str] = {}
    for row in network:
        decoded = unquote(row.get("url", ""))
        if "sectionaltimes_callback" in decoded and row.get("status") == "200":
            admitted_graphql_urls[row.get("fixture_id", "")] = row.get("url", "")

    admitted_graphql_headers: dict[str, dict[str, str]] = {}
    for row in requests:
        decoded = unquote(row.get("url", ""))
        if "sectionaltimes_callback" not in decoded:
            continue
        try:
            headers = json.loads(row.get("safe_header_json") or "{}")
        except Exception:
            headers = {}
        admitted_graphql_headers[row.get("fixture_id", "")] = {
            key: clean(value)
            for key, value in headers.items()
            if key.lower() in {"x-api-key", "referer", "content-type", "user-agent", "accept"}
            and clean(value)
        }

    historical_csv_urls: dict[str, str] = {}
    for row in static:
        if row.get("cache_path", "").endswith(".csv") and row.get("http_status") == "200":
            historical_csv_urls[row.get("fixture_id", "")] = row.get("requested_url", "")

    output_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []

    for fixture in fixtures:
        fixture_id = fixture.get("fixture_id", "")
        visible_status = fixture.get("visible_speed_data_status", "")
        if fixture_id in admitted_graphql_urls:
            url = admitted_graphql_urls[fixture_id]
            replay_headers = admitted_graphql_headers.get(fixture_id, {})
            ok, status, content_type, cache_path, sha256 = fetch_url(url, fixture_id, ".json", replay_headers)
            time.sleep(0.4)
            rows: list[dict[str, Any]] = []
            if ok and cache_path:
                body = (ROOT / cache_path).read_bytes()
                payload = parse_graphql_payload(body)
                if payload:
                    rows = parse_graphql_rows(fixture, url, cache_path, sha256, payload)
            audit_rows.append(
                {
                    "fixture_id": fixture_id,
                    "race_date": fixture.get("race_date", ""),
                    "track": fixture.get("track", ""),
                    "race_no": fixture.get("race_no", ""),
                    "source_candidate_id": "GRAPHQL_SECTIONALTIMES_GETRACEFORM",
                    "source_url": url,
                    "fetch_status": status,
                    "content_type": content_type,
                    "cache_path": cache_path,
                    "sha256": sha256,
                    "normalised_rows": len(rows),
                    "runner_count": len({row["horse"] for row in rows}),
                    "sectional_count": len(rows),
                    "decision": "ACQUIRED_AND_NORMALISED" if rows else "ACQUISITION_OR_PARSE_FAILED",
                    "detail": "Fresh GraphQL source obtained from previously captured evidenced request using public widget headers; no cookies or user auth tokens used.",
                }
            )
            output_rows.extend(rows)
        elif fixture_id in historical_csv_urls:
            url = historical_csv_urls[fixture_id]
            ok, status, content_type, cache_path, sha256 = fetch_url(url, fixture_id, ".csv")
            time.sleep(0.4)
            rows = []
            if ok and cache_path:
                body = (ROOT / cache_path).read_bytes()
                rows = parse_historical_csv_rows(fixture, url, cache_path, sha256, body)
            audit_rows.append(
                {
                    "fixture_id": fixture_id,
                    "race_date": fixture.get("race_date", ""),
                    "track": fixture.get("track", ""),
                    "race_no": fixture.get("race_no", ""),
                    "source_candidate_id": "HISTORICAL_DIRECT_CSV",
                    "source_url": url,
                    "fetch_status": status,
                    "content_type": content_type,
                    "cache_path": cache_path,
                    "sha256": sha256,
                    "normalised_rows": len(rows),
                    "runner_count": len({row["horse"] for row in rows}),
                    "sectional_count": len(rows),
                    "decision": "ACQUIRED_AND_NORMALISED" if rows else "ACQUISITION_OR_PARSE_FAILED",
                    "detail": "Historical V2 CSV source retained and normalised through POC intermediate.",
                }
            )
            output_rows.extend(rows)
        elif visible_status == "NO_VISIBLE_SPEED_DATA":
            audit_rows.append(
                {
                    "fixture_id": fixture_id,
                    "race_date": fixture.get("race_date", ""),
                    "track": fixture.get("track", ""),
                    "race_no": fixture.get("race_no", ""),
                    "source_candidate_id": "",
                    "source_url": "",
                    "fetch_status": "",
                    "content_type": "",
                    "cache_path": "",
                    "sha256": "",
                    "normalised_rows": 0,
                    "runner_count": 0,
                    "sectional_count": 0,
                    "decision": "NEGATIVE_CONTROL_REJECTED_NO_SECTIONALS_REQUEST",
                    "detail": "No sectionaltimes_callback payload was observed for this negative-control fixture; no synthetic request generated.",
                }
            )
        else:
            audit_rows.append(
                {
                    "fixture_id": fixture_id,
                    "race_date": fixture.get("race_date", ""),
                    "track": fixture.get("track", ""),
                    "race_no": fixture.get("race_no", ""),
                    "source_candidate_id": "",
                    "source_url": "",
                    "fetch_status": "",
                    "content_type": "",
                    "cache_path": "",
                    "sha256": "",
                    "normalised_rows": 0,
                    "runner_count": 0,
                    "sectional_count": 0,
                    "decision": "NO_ADMITTED_SOURCE_REQUEST",
                    "detail": "No admitted source request exists for this fixture.",
                }
            )

    output_fields = [
        "fixture_id",
        "race_date",
        "track",
        "race_no",
        "meet_code",
        "query_race_no",
        "source_format",
        "source_candidate_id",
        "source_url",
        "source_cache_path",
        "source_sha256",
        "horse",
        "saddle_number",
        "runner_source_id",
        "trainer",
        "jockey",
        "final_position",
        "section_distance_label",
        "section_position",
        "section_time",
        "avg_speed_mps",
        "avg_speed_kmh",
        "raw_record_json",
        "raw_runner_json",
        "normalisation_status",
        "identity_status",
        "semantics_status",
    ]
    audit_fields = [
        "fixture_id",
        "race_date",
        "track",
        "race_no",
        "source_candidate_id",
        "source_url",
        "fetch_status",
        "content_type",
        "cache_path",
        "sha256",
        "normalised_rows",
        "runner_count",
        "sectional_count",
        "decision",
        "detail",
    ]
    write_csv(POC_OUT, output_rows, output_fields)
    write_csv(AUDIT_OUT, audit_rows, audit_fields)

    fresh_audits = [row for row in audit_rows if row["source_candidate_id"] == "GRAPHQL_SECTIONALTIMES_GETRACEFORM"]
    historical_audits = [row for row in audit_rows if row["source_candidate_id"] == "HISTORICAL_DIRECT_CSV"]
    negative_audits = [row for row in audit_rows if row["decision"] == "NEGATIVE_CONTROL_REJECTED_NO_SECTIONALS_REQUEST"]
    failed_audits = [row for row in audit_rows if "FAILED" in row["decision"]]
    identity_failures = [row for row in output_rows if row["identity_status"] != "RACE_AND_RUNNER_IDENTIFIED"]
    source_formats = sorted({row["source_format"] for row in output_rows})
    decision = (
        "FRESH_SOURCE_POC_PASS"
        if len(fresh_audits) >= 5
        and all(row["decision"] == "ACQUIRED_AND_NORMALISED" for row in fresh_audits)
        and len(historical_audits) >= 8
        and all(row["decision"] == "ACQUIRED_AND_NORMALISED" for row in historical_audits)
        and len(negative_audits) >= 2
        and not failed_audits
        and not identity_failures
        else "FRESH_SOURCE_POC_PARTIAL"
    )

    summary = {
        "built_utc": built_utc,
        "decision": decision,
        "fixtures": len(fixtures),
        "validation_decisions_loaded": len(validation),
        "normalised_rows": len(output_rows),
        "fresh_graphql_fixtures_acquired": len(fresh_audits),
        "historical_csv_fixtures_acquired": len(historical_audits),
        "negative_controls_rejected": len(negative_audits),
        "fresh_graphql_rows": sum(1 for row in output_rows if row["source_format"] == "GRAPHQL_JSON"),
        "historical_csv_rows": sum(1 for row in output_rows if row["source_format"] == "HISTORICAL_CSV"),
        "unique_fresh_runners": len({row["fixture_id"] + "|" + row["horse"] for row in output_rows if row["source_format"] == "GRAPHQL_JSON"}),
        "unique_historical_runners": len({row["fixture_id"] + "|" + row["horse"] for row in output_rows if row["source_format"] == "HISTORICAL_CSV"}),
        "source_formats": source_formats,
        "failed_acquisitions": len(failed_audits),
        "identity_failures": len(identity_failures),
        "production_changed": "NO",
        "ui_changed": "NO",
    }
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    report = f"""# Racing.com Fresh Source POC V1

Built UTC: {built_utc}

## Decision

`{decision}`

## Counts

- Fixtures consumed: {len(fixtures)}
- Normalised rows: {len(output_rows)}
- Fresh GraphQL fixtures acquired: {len(fresh_audits)}
- Historical CSV fixtures acquired: {len(historical_audits)}
- Negative controls rejected: {len(negative_audits)}
- Fresh GraphQL rows: {summary['fresh_graphql_rows']}
- Historical CSV rows: {summary['historical_csv_rows']}
- Unique fresh runners: {summary['unique_fresh_runners']}
- Unique historical runners: {summary['unique_historical_runners']}
- Failed acquisitions: {len(failed_audits)}
- Identity failures: {len(identity_failures)}

## Source Handling

- Fresh recent Speed Data pages were acquired through the evidenced GraphQL request `sectionaltimes_callback: getRaceForm(meetCode, raceNumber)`.
- Fresh GraphQL replay uses only public widget headers captured in the browser request ledger, including the public `x-api-key`; no cookies, authorization headers, user tokens, credentials or account state are used.
- Historical V2 CSV fixtures were retained as `HISTORICAL_DIRECT_CSV`.
- Negative controls were not queried with synthetic sectionals requests; they are rejected because no admitted sectionals request was observed in the browser evidence.
- Raw payloads are cached under `outputs/performance-intelligence/racingcom-source-discovery/raw/fresh-source-poc`.
- The normalised POC output preserves raw section records, raw runner context, source URL, cache path and SHA-256.

## Governance

- Production warehouse was not overwritten.
- V2 architecture was not modified.
- UI, pricing, probability, rating, V6.1 and V7.2G2 were not modified.
- This is proof-of-concept evidence only; no migration has been performed.
"""
    REPORT_OUT.write_text(report, encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
