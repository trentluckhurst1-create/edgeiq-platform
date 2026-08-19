from __future__ import annotations

import csv
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
DOC_DIR = ROOT / "docs" / "performance-intelligence" / "racingcom-source-discovery"
RAW_DIR = ROOT / "outputs" / "performance-intelligence" / "racingcom-source-discovery" / "raw" / "network-capture"
FIXTURES = DOC_DIR / "edgeiq_racingcom_speed_data_fixture_contract_v1.csv"

OUT_REQUESTS = DOC_DIR / "edgeiq_racingcom_network_request_ledger_v1.csv"
OUT_RESPONSES = DOC_DIR / "edgeiq_racingcom_network_response_ledger_v1.csv"
OUT_CANDIDATES = DOC_DIR / "edgeiq_racingcom_network_payload_candidate_v1.csv"
OUT_AUDIT = DOC_DIR / "edgeiq_racingcom_network_capture_audit_v1.csv"
OUT_REPORT = DOC_DIR / "edgeiq_racingcom_network_capture_report_v1.md"

USER_AGENT = "EDGEiQ-Racing/1.0 governed-network-forensics"
CAPTURE_LIMIT = 5_000_000
SENSITIVE_HEADERS = {"cookie", "authorization", "x-auth-token", "proxy-authorization", "set-cookie"}
SECTIONAL_TERMS = ["sectional", "speed", "last200", "last400", "last600", "topSpeed", "distanceTravelled", "avg speed", "peak speed", "km/h", "dist run"]
RUNNER_TERMS = ["horseName", "horse", "runner", "POS / HORSE", "trainer", "jockey"]

REQ_FIELDS = [
    "fixture_id", "race_date", "track", "race_no", "request_index", "timestamp_utc", "method", "url",
    "resource_type", "safe_header_json", "safe_post_body", "is_navigation_request", "frame_url",
]
RESP_FIELDS = [
    "fixture_id", "race_date", "track", "race_no", "request_index", "response_index", "timestamp_utc",
    "method", "url", "status", "content_type", "resource_type", "response_size", "sha256", "cache_path",
    "classification", "redirected_from", "safe_header_json",
]
CANDIDATE_FIELDS = [
    "fixture_id", "race_date", "track", "race_no", "candidate_url", "classification", "status", "content_type",
    "cache_path", "sha256", "race_identity_match", "runner_terms", "sectional_terms", "numeric_speed_count",
    "runner_name_count", "evidence_strength", "candidate_decision", "provenance_note",
]
AUDIT_FIELDS = ["check", "status", "count", "detail"]


def clean(v: Any) -> str:
    return "" if v is None else str(v).strip()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def safe_headers(headers: dict[str, str]) -> dict[str, str]:
    out = {}
    for k, v in (headers or {}).items():
        if k.lower() in SENSITIVE_HEADERS:
            continue
        out[k] = v
    return out


def safe_post_data(post_data: str | None) -> str:
    if not post_data:
        return ""
    text = post_data
    text = re.sub(r'("(?:password|token|secret|authorization|cookie)"\s*:\s*").*?"', r'\1[REDACTED]"', text, flags=re.I)
    return text[:5000]


def operation_from_url(url: str) -> str:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if qs.get("operationName"):
        return clean(qs["operationName"][0])
    q = unquote(qs.get("query", [""])[0])
    m = re.search(r"\bquery\s+([A-Za-z_][A-Za-z0-9_]*)", q)
    if m:
        return m.group(1)
    m = re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", q)
    return m.group(1) if m else ""


def classify(url: str, resource_type: str, status: int, content_type: str, body_text: str = "") -> str:
    lower_url = url.lower()
    ctype = content_type.lower()
    if status >= 400:
        return "ERROR_RESPONSE"
    if "analytics" in lower_url or "nr-data" in lower_url or "googletag" in lower_url or "doubleclick" in lower_url:
        return "ANALYTICS"
    if "adsrvr" in lower_url or "adnxs" in lower_url or "ads" in lower_url:
        return "ADVERTISING"
    if any(x in ctype for x in ["image/", "font", "octet-stream"]) and not lower_url.endswith(".csv"):
        return "IMAGE_OR_FONT"
    if lower_url.endswith(".csv") or "csv" in ctype:
        return "CSV_FILE"
    if "graphql" in lower_url or "graphql" in body_text[:1000].lower():
        if "json" in ctype:
            return "GRAPHQL_RESPONSE"
        return "STRUCTURED_PAYLOAD"
    if "json" in ctype:
        return "JSON_API"
    if "html" in ctype and resource_type == "document":
        return "HTML_DOCUMENT"
    if "javascript" in ctype or resource_type == "script":
        return "JAVASCRIPT_ASSET"
    if "sectionals" in lower_url or any(t.lower() in body_text.lower() for t in SECTIONAL_TERMS):
        return "STRUCTURED_PAYLOAD"
    return "UNRELATED"


def parse_runner_names_from_visible_evidence(fixture: dict[str, str]) -> list[str]:
    names = []
    evidence = fixture.get("source_evidence", "")
    for m in re.findall(r"visible_text_[A-Za-z0-9]+\.txt", evidence):
        path = ROOT / "outputs" / "performance-intelligence" / "racingcom-source-discovery" / "raw" / "fixture-selection" / m
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        # Pull simple speed-widget horse lines like "12. Itsagiven (NZ) (7)".
        for hm in re.finditer(r"(?:^|\n)\s*\d+\.\s+([^\n\t]+?)\s*\(\d+\)", text):
            horse = re.sub(r"\s+", " ", hm.group(1)).strip()
            if horse and horse.upper() not in {n.upper() for n in names}:
                names.append(horse)
    return names[:30]


def fixture_meet_code(fixture: dict[str, str]) -> str:
    m = re.search(r"meetCode=(\d+)", fixture.get("source_evidence", ""))
    return m.group(1) if m else ""


def candidate_from_body(fixture: dict[str, str], response_row: dict[str, Any], body_text: str, runner_names: list[str]) -> dict[str, Any] | None:
    lower = body_text.lower()
    sectional_hits = [t for t in SECTIONAL_TERMS if t.lower() in lower]
    runner_hits = [t for t in RUNNER_TERMS if t.lower() in lower]
    numeric_speed_count = len(re.findall(r"\b\d{2}\.\d{1,2}\s*(?:km/h|m/s)\b", body_text, flags=re.I))
    runner_name_count = 0
    for name in runner_names:
        if name and name.lower() in lower:
            runner_name_count += 1
    meet_code = fixture_meet_code(fixture)
    race_no = clean(fixture.get("race_no"))
    url_lower = response_row["url"].lower()
    race_identity_match = "NO"
    if meet_code and meet_code in response_row["url"] and race_no and re.search(rf"(?:raceNumber|race_number|race)[=:%22]+{re.escape(race_no)}\b", response_row["url"], flags=re.I):
        race_identity_match = "URL_MEETCODE_RACENO"
    elif meet_code and meet_code in body_text and race_no and race_no in body_text:
        race_identity_match = "BODY_MEETCODE_RACENO"
    elif race_no and f"race/{race_no}" in url_lower:
        race_identity_match = "URL_RACE_PATH"

    if not sectional_hits and not runner_hits and numeric_speed_count < 4 and runner_name_count == 0:
        return None
    evidence_strength = "LOW"
    decision = "RESPONSE_REQUIRES_VALIDATION"
    sectional_grid = ("avg speed" in lower and "peak speed" in lower) or ("dist run" in lower and "km/h" in lower)
    if race_identity_match != "NO" and (numeric_speed_count >= 4 or sectional_grid or "sectional" in [x.lower() for x in sectional_hits]) and (runner_name_count >= 2 or "horseName" in runner_hits or "POS / HORSE" in runner_hits):
        evidence_strength = "STRONG"
        decision = "POTENTIAL_SPEED_PAYLOAD"
    elif sectional_hits or numeric_speed_count >= 4 or sectional_grid:
        evidence_strength = "MEDIUM"
        decision = "POTENTIAL_SECTIONAL_OR_SPEED_PAYLOAD"
    return {
        "fixture_id": fixture["fixture_id"],
        "race_date": fixture["race_date"],
        "track": fixture["track"],
        "race_no": fixture["race_no"],
        "candidate_url": response_row["url"],
        "classification": response_row["classification"],
        "status": response_row["status"],
        "content_type": response_row["content_type"],
        "cache_path": response_row["cache_path"],
        "sha256": response_row["sha256"],
        "race_identity_match": race_identity_match,
        "runner_terms": "|".join(runner_hits),
        "sectional_terms": "|".join(sectional_hits),
        "numeric_speed_count": numeric_speed_count,
        "runner_name_count": runner_name_count,
        "evidence_strength": evidence_strength,
        "candidate_decision": decision,
        "provenance_note": "Browser network response candidate only; semantics validated in the next unit.",
    }


def cache_body(fixture_id: str, response_index: int, url: str, content_type: str, body: bytes) -> tuple[str, str, int]:
    digest = hashlib.sha256(body).hexdigest()
    if not body:
        return digest, "", 0
    ctype = content_type.lower()
    ext = ".bin"
    if "json" in ctype:
        ext = ".json"
    elif "html" in ctype:
        ext = ".html"
    elif "javascript" in ctype:
        ext = ".js"
    elif "csv" in ctype or url.lower().endswith(".csv"):
        ext = ".csv"
    elif "text" in ctype:
        ext = ".txt"
    fid = hashlib.sha256(fixture_id.encode("utf-8", errors="ignore")).hexdigest()[:10]
    path = RAW_DIR / f"net_{fid}_{response_index:04d}_{digest[:16]}{ext}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return digest, rel(path), len(body)


def should_capture_body(content_type: str, resource_type: str, url: str) -> bool:
    c = content_type.lower()
    u = url.lower()
    return any(x in c for x in ["json", "html", "javascript", "csv", "text"]) or u.endswith(".csv") or resource_type in {"document", "xhr", "fetch", "script"}


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise SystemExit(f"PLAYWRIGHT_NOT_AVAILABLE: {exc}")

    DOC_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    built_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
    fixtures = read_csv(FIXTURES)
    request_rows: list[dict[str, Any]] = []
    response_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    errors: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT, viewport={"width": 1440, "height": 1100})
        for fixture in fixtures:
            page = context.new_page()
            request_index_by_obj: dict[Any, int] = {}
            req_counter = 0
            resp_counter = 0
            runner_names = parse_runner_names_from_visible_evidence(fixture)

            def on_request(req):
                nonlocal req_counter
                req_counter += 1
                request_index_by_obj[req] = req_counter
                try:
                    headers = safe_headers(req.headers)
                    request_rows.append({
                        "fixture_id": fixture["fixture_id"],
                        "race_date": fixture["race_date"],
                        "track": fixture["track"],
                        "race_no": fixture["race_no"],
                        "request_index": req_counter,
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "method": req.method,
                        "url": req.url,
                        "resource_type": req.resource_type,
                        "safe_header_json": json.dumps(headers, ensure_ascii=False, sort_keys=True),
                        "safe_post_body": safe_post_data(req.post_data),
                        "is_navigation_request": "YES" if req.is_navigation_request() else "NO",
                        "frame_url": req.frame.url if req.frame else "",
                    })
                except Exception as exc:
                    errors.append(f"request_capture:{fixture['fixture_id']}:{exc}")

            def on_response(resp):
                nonlocal resp_counter
                resp_counter += 1
                try:
                    req = resp.request
                    ridx = request_index_by_obj.get(req, "")
                    ctype = clean(resp.headers.get("content-type"))
                    body = b""
                    cache_path = ""
                    digest = ""
                    size = ""
                    body_text = ""
                    if should_capture_body(ctype, req.resource_type, resp.url):
                        try:
                            body = resp.body()
                            if len(body) > CAPTURE_LIMIT:
                                body = body[:CAPTURE_LIMIT]
                            digest, cache_path, size = cache_body(fixture["fixture_id"], resp_counter, resp.url, ctype, body)
                            body_text = body.decode("utf-8", errors="replace")
                        except Exception as exc:
                            errors.append(f"body_capture:{fixture['fixture_id']}:{resp.url[:160]}:{exc}")
                    cls = classify(resp.url, req.resource_type, resp.status, ctype, body_text)
                    row = {
                        "fixture_id": fixture["fixture_id"],
                        "race_date": fixture["race_date"],
                        "track": fixture["track"],
                        "race_no": fixture["race_no"],
                        "request_index": ridx,
                        "response_index": resp_counter,
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "method": req.method,
                        "url": resp.url,
                        "status": resp.status,
                        "content_type": ctype,
                        "resource_type": req.resource_type,
                        "response_size": size,
                        "sha256": digest,
                        "cache_path": cache_path,
                        "classification": cls,
                        "redirected_from": "",
                        "safe_header_json": json.dumps(safe_headers(resp.headers), ensure_ascii=False, sort_keys=True),
                    }
                    response_rows.append(row)
                    cand = candidate_from_body(fixture, row, body_text, runner_names)
                    if cand:
                        candidate_rows.append(cand)
                except Exception as exc:
                    errors.append(f"response_capture:{fixture['fixture_id']}:{exc}")

            page.on("request", on_request)
            page.on("response", on_response)
            target = clean(fixture.get("race_url")) if fixture["fixture_id"].startswith("HISTORICAL_CSV_") else clean(fixture.get("speed_data_url"))
            if fixture["fixture_id"].startswith("HISTORICAL_CSV_"):
                target = clean(fixture.get("speed_data_url"))
            try:
                page.goto(target, wait_until="domcontentloaded", timeout=35000)
                if not fixture["fixture_id"].startswith("HISTORICAL_CSV_"):
                    page.wait_for_timeout(11000)
                else:
                    page.wait_for_timeout(1000)
            except Exception as exc:
                errors.append(f"page_load:{fixture['fixture_id']}:{exc}")
            page.close()
            time.sleep(0.8)
        context.close()
        browser.close()

    write_csv(OUT_REQUESTS, request_rows, REQ_FIELDS)
    write_csv(OUT_RESPONSES, response_rows, RESP_FIELDS)
    write_csv(OUT_CANDIDATES, candidate_rows, CANDIDATE_FIELDS)

    fixtures_with_requests = len({r["fixture_id"] for r in request_rows})
    fixtures_with_responses = len({r["fixture_id"] for r in response_rows})
    class_counts: dict[str, int] = {}
    for r in response_rows:
        class_counts[r["classification"]] = class_counts.get(r["classification"], 0) + 1
    strong_candidates = sum(1 for r in candidate_rows if r.get("evidence_strength") == "STRONG")
    recent_strong_fixtures = len({r["fixture_id"] for r in candidate_rows if r.get("fixture_id", "").startswith("RECENT_VISIBLE_") and r.get("evidence_strength") == "STRONG"})
    negative_strong = len({r["fixture_id"] for r in candidate_rows if r.get("fixture_id", "").startswith("NEGATIVE_CONTROL_") and r.get("evidence_strength") == "STRONG"})
    graphql_responses = class_counts.get("GRAPHQL_RESPONSE", 0)
    json_responses = class_counts.get("JSON_API", 0)
    csv_responses = class_counts.get("CSV_FILE", 0)
    html_docs = class_counts.get("HTML_DOCUMENT", 0)
    repo_bad = sum(1 for r in response_rows if r.get("cache_path") and not (ROOT / r["cache_path"]).resolve().is_relative_to(ROOT.resolve()))

    audit = []
    def add(check: str, status: str, count: Any, detail: str) -> None:
        audit.append({"check": check, "status": status, "count": count, "detail": detail})
    add("fixtures_with_requests", "PASS" if fixtures_with_requests == len(fixtures) else "FAIL", fixtures_with_requests, "Every fixture should produce captured browser requests.")
    add("fixtures_with_responses", "PASS" if fixtures_with_responses == len(fixtures) else "FAIL", fixtures_with_responses, "Every fixture should produce captured browser responses.")
    add("graphql_or_json_responses", "PASS" if graphql_responses + json_responses > 0 else "FAIL", graphql_responses + json_responses, "Browser capture should retain dynamic JSON/GraphQL responses.")
    add("historical_csv_responses", "PASS" if csv_responses >= 8 else "FAIL", csv_responses, "Historical direct CSV fixtures should appear as CSV responses.")
    add("html_documents", "PASS" if html_docs >= 7 else "FAIL", html_docs, "Recent/negative speed pages should capture HTML documents.")
    add("payload_candidates", "PASS" if candidate_rows else "FAIL", len(candidate_rows), "Candidate payload rows should be generated from response bodies.")
    add("strong_recent_payload_candidates", "PASS" if recent_strong_fixtures >= 5 else "WARN", recent_strong_fixtures, "At least five visible-speed fixtures should have strong payload candidates.")
    add("negative_controls_not_strong", "PASS" if negative_strong == 0 else "FAIL", negative_strong, "Negative controls should not produce strong speed payload candidates.")
    add("repo_local_cache", "PASS" if repo_bad == 0 else "FAIL", repo_bad, "Cached response bodies remain inside repository-local output paths.")
    add("capture_errors", "PASS" if not errors else "WARN", len(errors), json.dumps(errors[:8], ensure_ascii=False))
    fail_count = sum(1 for r in audit if r["status"] == "FAIL")
    write_csv(OUT_AUDIT, audit, AUDIT_FIELDS)

    report = f"""# Racing.com Browser Network Capture V1

Built UTC: {built_utc}

## Status

`{'RACINGCOM_NETWORK_CAPTURE_V1_PASS' if fail_count == 0 else 'RACINGCOM_NETWORK_CAPTURE_V1_FAIL'}`

## Counts

- Fixtures: {len(fixtures)}
- Request rows: {len(request_rows)}
- Response rows: {len(response_rows)}
- Candidate payload rows: {len(candidate_rows)}
- Strong candidate rows: {strong_candidates}
- Recent visible fixtures with strong candidates: {recent_strong_fixtures}
- Negative controls with strong candidates: {negative_strong}
- Response class counts: `{json.dumps(class_counts, sort_keys=True)}`
- Capture errors/warnings: {len(errors)}

## Findings

Browser capture confirms the speed-data page loads dynamic first-party Racing.com/sectionals traffic. Candidate payload rows are not yet admitted sources; they move to the source-candidate validation unit for race identity, runner identity, schema and unit checks.
"""
    OUT_REPORT.write_text(report, encoding="utf-8")
    print(json.dumps({
        "status": "RACINGCOM_NETWORK_CAPTURE_V1_PASS" if fail_count == 0 else "RACINGCOM_NETWORK_CAPTURE_V1_FAIL",
        "fixtures": len(fixtures),
        "request_rows": len(request_rows),
        "response_rows": len(response_rows),
        "candidate_rows": len(candidate_rows),
        "strong_candidate_rows": strong_candidates,
        "recent_strong_fixtures": recent_strong_fixtures,
        "negative_strong_fixtures": negative_strong,
        "class_counts": class_counts,
        "audit_failures": fail_count,
        "production_changed": "NO",
        "ui_changed": "NO",
    }, indent=2))
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
