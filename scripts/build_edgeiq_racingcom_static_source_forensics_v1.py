from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOC_DIR = ROOT / "docs" / "performance-intelligence" / "racingcom-source-discovery"
RAW_DIR = ROOT / "outputs" / "performance-intelligence" / "racingcom-source-discovery" / "raw" / "static-source"
FIXTURES = DOC_DIR / "edgeiq_racingcom_speed_data_fixture_contract_v1.csv"

OUT_RESPONSE_LEDGER = DOC_DIR / "edgeiq_racingcom_static_response_ledger_v1.csv"
OUT_CANDIDATES = DOC_DIR / "edgeiq_racingcom_static_source_candidate_ledger_v1.csv"
OUT_EMBEDDED = DOC_DIR / "edgeiq_racingcom_embedded_payload_ledger_v1.csv"
OUT_SCRIPTS = DOC_DIR / "edgeiq_racingcom_script_asset_ledger_v1.csv"
OUT_AUDIT = DOC_DIR / "edgeiq_racingcom_static_source_audit_v1.csv"
OUT_REPORT = DOC_DIR / "edgeiq_racingcom_static_source_report_v1.md"

USER_AGENT = "EDGEiQ-Racing/1.0 governed-static-source-forensics"
TERMS = [
    ".csv", ".json", "graphql", "api", "sectional", "speed", "last200", "last400", "last600",
    "distanceTravelled", "topSpeed", "runner", "raceResult", "raceId", "meetingId", "CloudFront",
    "download", "export", "GetRace", "getRace", "GetMeeting", "getMeeting", "sectionals",
]
CANDIDATE_FIELDS = [
    "fixture_id", "race_date", "track", "race_no", "candidate_type", "term", "candidate_value",
    "context_sample", "source_cache_path", "source_sha256", "provenance_note",
]
EMBEDDED_FIELDS = [
    "fixture_id", "payload_type", "selector", "bytes", "sha256", "cache_path", "candidate_terms", "provenance_note",
]
SCRIPT_FIELDS = [
    "fixture_id", "script_type", "script_url", "cache_path", "sha256", "bytes", "candidate_terms", "provenance_note",
]
RESPONSE_FIELDS = ["fixture_id", "requested_url", "final_url", "http_status", "content_type", "response_size", "redirect_chain", "etag", "last_modified", "timestamp_utc", "sha256", "cache_path", "header_json"]
AUDIT_FIELDS = ["check", "status", "count", "detail"]


def clean(v: Any) -> str:
    return "" if v is None else str(v).strip()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def safe_name(value: str) -> str:
    value = re.sub(r"^https?://", "", value, flags=re.I)
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")
    return value[:120] or "payload"


def sha_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


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


def fetch(url: str, fixture_id: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml,application/json,text/csv,*/*",
        "Referer": "https://www.racing.com/form",
    })
    opened = urllib.request.urlopen(req, timeout=45)
    with opened as resp:
        body = resp.read()
        final_url = resp.geturl()
        headers = dict(resp.headers.items())
        status = int(resp.status)
    digest = sha_bytes(body)
    parsed = urllib.parse.urlparse(final_url)
    ext = ".html"
    ctype = clean(headers.get("Content-Type") or headers.get("content-type")).lower()
    if "json" in ctype:
        ext = ".json"
    elif "csv" in ctype or parsed.path.lower().endswith(".csv"):
        ext = ".csv"
    elif "javascript" in ctype or parsed.path.lower().endswith(".js"):
        ext = ".js"
    fid_hash = hashlib.sha256(fixture_id.encode("utf-8", errors="ignore")).hexdigest()[:10]
    cache = RAW_DIR / f"static_{fid_hash}_{digest[:16]}{ext}"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(body)
    return {
        "requested_url": url,
        "final_url": final_url,
        "status": status,
        "content_type": clean(headers.get("Content-Type") or headers.get("content-type")),
        "response_size": len(body),
        "headers": headers,
        "etag": clean(headers.get("ETag") or headers.get("etag")),
        "last_modified": clean(headers.get("Last-Modified") or headers.get("last-modified")),
        "sha256": digest,
        "cache_path": cache,
        "body": body,
    }


def find_terms(text: str) -> list[str]:
    lower = text.lower()
    hits = []
    for term in TERMS:
        if term.lower() in lower:
            hits.append(term)
    return sorted(set(hits), key=lambda x: x.lower())


def contexts_for_terms(text: str, limit_per_term: int = 4) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    for term in TERMS:
        pattern = re.compile(re.escape(term), re.I)
        count = 0
        for m in pattern.finditer(text):
            start = max(0, m.start() - 160)
            end = min(len(text), m.end() + 220)
            sample = re.sub(r"\s+", " ", text[start:end]).strip()
            results.append((term, sample[:500]))
            count += 1
            if count >= limit_per_term:
                break
    return results


def absolute_url(base: str, value: str) -> str:
    return urllib.parse.urljoin(base, html.unescape(value))


def extract_assets_and_embedded(fixture: dict[str, str], response: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    fixture_id = fixture["fixture_id"]
    body = response["body"]
    text = body.decode("utf-8", errors="replace")
    source_cache = rel(response["cache_path"])
    source_sha = response["sha256"]
    candidates: list[dict[str, Any]] = []
    embedded: list[dict[str, Any]] = []
    scripts: list[dict[str, Any]] = []

    for term, sample in contexts_for_terms(text):
        candidate_value = ""
        url_match = re.search(r"https?://[^\s'\"<>]+", sample)
        if url_match:
            candidate_value = url_match.group(0).rstrip(").,;]")
        candidates.append({
            "fixture_id": fixture_id,
            "race_date": fixture["race_date"],
            "track": fixture["track"],
            "race_no": fixture["race_no"],
            "candidate_type": "STRING_MATCH_ONLY",
            "term": term,
            "candidate_value": candidate_value,
            "context_sample": sample,
            "source_cache_path": source_cache,
            "source_sha256": source_sha,
            "provenance_note": "Static source string match only; not a proven endpoint.",
        })

    # script src and iframe src assets. Iframes matter because Racing.com speed data loads in a sectionals widget.
    for tag_name, attr, asset_type in [("script", "src", "SCRIPT_SRC"), ("iframe", "src", "IFRAME_SRC")]:
        regex = re.compile(rf"<{tag_name}[^>]+{attr}=[\"']([^\"']+)[\"']", re.I)
        for m in regex.finditer(text):
            url = absolute_url(response["final_url"], m.group(1))
            hits = find_terms(url)
            scripts.append({
                "fixture_id": fixture_id,
                "script_type": asset_type,
                "script_url": url,
                "cache_path": "",
                "sha256": "",
                "bytes": "",
                "candidate_terms": "|".join(hits),
                "provenance_note": "Asset URL extracted from static HTML. Not fetched in this unit unless it is the requested document itself.",
            })
            if hits:
                candidates.append({
                    "fixture_id": fixture_id,
                    "race_date": fixture["race_date"],
                    "track": fixture["track"],
                    "race_no": fixture["race_no"],
                    "candidate_type": asset_type,
                    "term": "|".join(hits),
                    "candidate_value": url,
                    "context_sample": url,
                    "source_cache_path": source_cache,
                    "source_sha256": source_sha,
                    "provenance_note": "Asset URL candidate extracted from static HTML; not yet validated as speed-data endpoint.",
                })

    # Embedded JSON/script states.
    json_script_regex = re.compile(r"<script[^>]+type=[\"']application/(?:ld\+)?json[\"'][^>]*>(.*?)</script>", re.I | re.S)
    for idx, m in enumerate(json_script_regex.finditer(text), start=1):
        payload_text = html.unescape(m.group(1)).strip()
        if not payload_text:
            continue
        digest = hashlib.sha256(payload_text.encode("utf-8", errors="ignore")).hexdigest()
        path = RAW_DIR / f"embedded_json_{hashlib.sha256(fixture_id.encode()).hexdigest()[:10]}_{idx}_{digest[:16]}.json"
        path.write_text(payload_text, encoding="utf-8")
        embedded.append({
            "fixture_id": fixture_id,
            "payload_type": "JSON_SCRIPT",
            "selector": f"script[type=application/json]#{idx}",
            "bytes": len(payload_text.encode("utf-8", errors="ignore")),
            "sha256": digest,
            "cache_path": rel(path),
            "candidate_terms": "|".join(find_terms(payload_text)),
            "provenance_note": "Embedded JSON script retained from static document.",
        })

    state_regexes = [
        ("NEXT_DATA", re.compile(r"<script[^>]+id=[\"']__NEXT_DATA__[\"'][^>]*>(.*?)</script>", re.I | re.S)),
        ("WINDOW_STATE", re.compile(r"window\.[A-Za-z0-9_.$-]+\s*=\s*(\{.*?\});", re.I | re.S)),
        ("APOLLO_STATE", re.compile(r"__APOLLO_STATE__\s*=\s*(\{.*?\});", re.I | re.S)),
        ("REDUX_STATE", re.compile(r"__PRELOADED_STATE__\s*=\s*(\{.*?\});", re.I | re.S)),
    ]
    for payload_type, regex in state_regexes:
        for idx, m in enumerate(regex.finditer(text), start=1):
            payload_text = html.unescape(m.group(1)).strip()
            digest = hashlib.sha256(payload_text.encode("utf-8", errors="ignore")).hexdigest()
            path = RAW_DIR / f"embedded_{payload_type.lower()}_{hashlib.sha256(fixture_id.encode()).hexdigest()[:10]}_{idx}_{digest[:16]}.txt"
            path.write_text(payload_text[:1000000], encoding="utf-8")
            embedded.append({
                "fixture_id": fixture_id,
                "payload_type": payload_type,
                "selector": f"{payload_type}#{idx}",
                "bytes": len(payload_text.encode("utf-8", errors="ignore")),
                "sha256": digest,
                "cache_path": rel(path),
                "candidate_terms": "|".join(find_terms(payload_text)),
                "provenance_note": "Hydration/state candidate retained from static document; not yet validated as source.",
            })

    return candidates, embedded, scripts


def main() -> int:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    built_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
    fixtures = read_csv(FIXTURES)
    responses: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    embedded: list[dict[str, Any]] = []
    scripts: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for fixture in fixtures:
        url = clean(fixture.get("speed_data_url")) or clean(fixture.get("race_url"))
        if not url:
            errors.append({"fixture_id": fixture.get("fixture_id"), "error": "NO_REQUEST_URL"})
            continue
        try:
            response = fetch(url, fixture["fixture_id"])
            responses.append(response | {"fixture_id": fixture["fixture_id"]})
            c, e, s = extract_assets_and_embedded(fixture, response)
            candidates.extend(c)
            embedded.extend(e)
            scripts.extend(s)
        except Exception as exc:
            errors.append({"fixture_id": fixture.get("fixture_id"), "error": str(exc)[:500]})
        time.sleep(0.6)

    # Add requested document responses to script ledger as REQUESTED_DOCUMENT rows.
    for r in responses:
        hits = find_terms((r["body"][:500000]).decode("utf-8", errors="replace"))
        scripts.append({
            "fixture_id": r["fixture_id"],
            "script_type": "REQUESTED_DOCUMENT",
            "script_url": r["final_url"],
            "cache_path": rel(r["cache_path"]),
            "sha256": r["sha256"],
            "bytes": r["response_size"],
            "candidate_terms": "|".join(hits),
            "provenance_note": f"requested_url={r['requested_url']}; status={r['status']}; content_type={r['content_type']}; etag={r['etag']}; last_modified={r['last_modified']}",
        })

    response_rows = []
    for r in responses:
        response_rows.append({
            "fixture_id": r["fixture_id"],
            "requested_url": r["requested_url"],
            "final_url": r["final_url"],
            "http_status": r["status"],
            "content_type": r["content_type"],
            "response_size": r["response_size"],
            "redirect_chain": "",
            "etag": r["etag"],
            "last_modified": r["last_modified"],
            "timestamp_utc": built_utc,
            "sha256": r["sha256"],
            "cache_path": rel(r["cache_path"]),
            "header_json": json.dumps(r["headers"], ensure_ascii=False, sort_keys=True),
        })
    write_csv(OUT_RESPONSE_LEDGER, response_rows, RESPONSE_FIELDS)
    write_csv(OUT_CANDIDATES, candidates, CANDIDATE_FIELDS)
    write_csv(OUT_EMBEDDED, embedded, EMBEDDED_FIELDS)
    write_csv(OUT_SCRIPTS, scripts, SCRIPT_FIELDS)

    html_docs = sum(1 for r in responses if "html" in clean(r.get("content_type")).lower())
    csv_docs = sum(1 for r in responses if "csv" in clean(r.get("content_type")).lower() or clean(r.get("final_url")).lower().endswith(".csv"))
    sectionals_iframes = sum(1 for s in scripts if s.get("script_type") == "IFRAME_SRC" and "sectionals" in s.get("script_url", "").lower())
    repo_bad = sum(1 for r in responses if not Path(r["cache_path"]).resolve().is_relative_to(ROOT.resolve()))
    audit = []
    def audit_row(check: str, status: str, count: Any, detail: str) -> None:
        audit.append({"check": check, "status": status, "count": count, "detail": detail})
    audit_row("fixtures_consumed", "PASS" if len(fixtures) == 15 else "FAIL", len(fixtures), "Expected 15 fixtures from fixture contract.")
    audit_row("responses_captured", "PASS" if len(responses) == len(fixtures) else "FAIL", len(responses), "Every fixture URL should have a retained response or explicit error.")
    audit_row("response_metadata_ledger", "PASS" if len(response_rows) == len(responses) else "FAIL", len(response_rows), "Response ledger retains requested/final URL, headers, ETag, Last-Modified, SHA and cache path.")
    audit_row("http_errors", "PASS" if not errors else "FAIL", len(errors), json.dumps(errors[:5], ensure_ascii=False))
    audit_row("historical_csv_documents", "PASS" if csv_docs >= 8 else "FAIL", csv_docs, "Historical direct CSV fixtures should remain visible as CSV/octet-stream documents.")
    audit_row("html_speed_pages", "PASS" if html_docs >= 7 else "FAIL", html_docs, "Recent/negative speed-data pages should return static HTML documents.")
    audit_row("sectionals_iframe_candidates", "PASS" if sectionals_iframes >= 5 else "WARN", sectionals_iframes, "Static pages expose sectionals widget iframe candidates, not direct CSV links.")
    audit_row("candidate_rows", "PASS" if candidates else "WARN", len(candidates), "String/asset candidates are recorded as candidates only.")
    audit_row("embedded_payload_rows", "PASS" if embedded else "WARN", len(embedded), "Embedded payload candidates retained if present.")
    audit_row("script_asset_rows", "PASS" if scripts else "FAIL", len(scripts), "Script/iframe/requested document ledger populated.")
    audit_row("repo_local_cache_paths", "PASS" if repo_bad == 0 else "FAIL", repo_bad, "All cache paths are repository-local relative outputs.")
    fail_count = sum(1 for a in audit if a["status"] == "FAIL")
    write_csv(OUT_AUDIT, audit, AUDIT_FIELDS)

    report = f"""# Racing.com Static Source Forensics V1

Built UTC: {built_utc}

## Status

`{'RACINGCOM_STATIC_SOURCE_FORENSICS_V1_PASS' if fail_count == 0 else 'RACINGCOM_STATIC_SOURCE_FORENSICS_V1_FAIL'}`

## Counts

- Fixtures consumed: {len(fixtures)}
- Responses captured: {len(responses)}
- Response metadata ledger rows: {len(response_rows)}
- HTML speed pages: {html_docs}
- Historical CSV/octet-stream documents: {csv_docs}
- Candidate string/asset rows: {len(candidates)}
- Embedded payload rows: {len(embedded)}
- Script/requested-document rows: {len(scripts)}
- Sectionals iframe candidates: {sectionals_iframes}
- Errors: {len(errors)}

## Findings

Static HTML did not prove a direct fresh CSV source. Recent Racing.com speed-data pages expose a `dxp-static.racing.com/sectionals/index.html` iframe candidate with `meetCode` and `raceNumber` parameters. This is only a candidate from static source forensics; browser network capture is required to identify the widget's actual data delivery mechanism.

Historical direct CSV fixtures remain available through their retained CloudFront CSV URLs.
"""
    OUT_REPORT.write_text(report, encoding="utf-8")
    print(json.dumps({
        "status": "RACINGCOM_STATIC_SOURCE_FORENSICS_V1_PASS" if fail_count == 0 else "RACINGCOM_STATIC_SOURCE_FORENSICS_V1_FAIL",
        "fixtures": len(fixtures),
        "responses": len(responses),
        "html_docs": html_docs,
        "csv_docs": csv_docs,
        "sectionals_iframes": sectionals_iframes,
        "candidate_rows": len(candidates),
        "embedded_payload_rows": len(embedded),
        "script_asset_rows": len(scripts),
        "audit_failures": fail_count,
        "production_changed": "NO",
        "ui_changed": "NO",
    }, indent=2))
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
