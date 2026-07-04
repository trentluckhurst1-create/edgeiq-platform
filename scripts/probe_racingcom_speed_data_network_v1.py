from pathlib import Path
from datetime import datetime, timezone
import hashlib
import os
import re
import sys
from urllib.parse import parse_qs, unquote, urlparse

import pandas as pd


APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA = APP_ROOT / "public" / "data"
RAW_OUT = PROJECT_ROOT / "outputs" / "sectionals" / "raw" / "VIC" / "racingcom_network_probe"
FULL_OUT = PROJECT_ROOT / "outputs" / "sectionals" / "raw" / "VIC" / "racingcom_full_payloads"

DIAGNOSTICS = DATA / "edgeiq_vic_racingcom_speed_data_diagnostics_v1.csv"
CALENDAR_DISCOVERY = DATA / "edgeiq_racingcom_calendar_discovery_v1.csv"
OUT = DATA / "edgeiq_racingcom_speed_network_probe_v1.csv"

MAX_PAGES = int(os.environ.get("EDGEIQ_RACINGCOM_NETWORK_MAX_PAGES", "5"))
FULL_CAPTURE = os.environ.get("EDGEIQ_RACINGCOM_FULL_CAPTURE", "").strip().lower() in {"1", "true", "yes", "on"}
TERMS = [
    "last200",
    "last400",
    "last600",
    "split",
    "sectional",
    "speed",
    "horse",
    "runner",
    "topSpeed",
    "distanceTravelled",
    "speedValue",
]

RELEVANT_OPERATIONS = {
    "getRaceEntriesForField_CD",
    "getRaceResults_CD",
    "getRaceNumberList_CD",
    "getMeeting_CD",
}

OUTPUT_COLUMNS = [
    "probe_timestamp_utc",
    "page_url",
    "response_url",
    "status",
    "content_type",
    "resource_type",
    "body_size",
    "matched_terms",
    "short_body_sample",
    "raw_sample_file",
    "probe_status",
]


def log(message: str) -> None:
    print(f"[racingcom_network_probe_v1] {message}")


def clean(value) -> str:
    return str(value or "").strip()


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        log(f"missing {path.relative_to(PROJECT_ROOT)}")
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype=str, encoding="utf-8-sig", on_bad_lines="skip").fillna("")
    except Exception as exc:
        log(f"warning: failed to read {path}: {exc}")
        return pd.DataFrame()


def operation_from_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if query.get("operationName"):
        return clean(query["operationName"][0])
    graphql_query = unquote(query.get("query", [""])[0])
    match = re.search(r"\bquery\s+([A-Za-z0-9_]+)", graphql_query)
    return match.group(1) if match else ""


def candidate_urls() -> list[str]:
    urls = []
    calendar = read_csv(CALENDAR_DISCOVERY)
    if not calendar.empty and "speed_data_url" in calendar.columns:
        for value in calendar["speed_data_url"].tolist():
            url = clean(value)
            if url and url not in urls:
                urls.append(url)
            if len(urls) >= MAX_PAGES:
                return urls

    df = read_csv(DIAGNOSTICS)
    if df.empty or "metric" not in df.columns or "value" not in df.columns:
        return urls
    fetches = df[df["metric"].astype(str) == "FETCH"].copy()
    if "notes" in fetches.columns:
        dynamic = fetches[fetches["notes"].astype(str).str.contains("DYNAMIC_PAGE_NO_STATIC_DATA", case=False, na=False)]
        if not dynamic.empty:
            fetches = dynamic
    for value in fetches["value"].tolist():
        url = clean(value)
        if url and url not in urls:
            urls.append(url)
        if len(urls) >= MAX_PAGES:
            break
    return urls


def find_terms(text: str) -> list[str]:
    lower = text.lower()
    return [term for term in TERMS if term.lower() in lower]


def sample_text(text: str, limit: int = 500) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    return compact[:limit]


def sample_filename(page_url: str, response_url: str, content_type: str) -> Path:
    digest = hashlib.sha1(f"{page_url}|{response_url}".encode("utf-8")).hexdigest()[:16]
    operation = operation_from_url(response_url)
    prefix = f"{operation}_" if operation else ""
    ext = ".json" if "json" in content_type.lower() else ".txt"
    return RAW_OUT / f"{prefix}{digest}{ext}"


def full_payload_filename(page_url: str, response_url: str, content_type: str) -> Path:
    digest = hashlib.sha1(f"{page_url}|{response_url}".encode("utf-8")).hexdigest()[:18]
    operation = operation_from_url(response_url)
    prefix = f"{operation}_" if operation else "response_"
    ext = ".json" if "json" in content_type.lower() else ".txt"
    return FULL_OUT / f"{prefix}{digest}{ext}"


def empty_output(status: str, urls: list[str]) -> pd.DataFrame:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if urls:
        rows = [
            {
                "probe_timestamp_utc": now,
                "page_url": url,
                "response_url": "",
                "status": "",
                "content_type": "",
                "resource_type": "",
                "body_size": "0",
                "matched_terms": "",
                "short_body_sample": "",
                "raw_sample_file": "",
                "probe_status": status,
            }
            for url in urls
        ]
    else:
        rows = [{
            "probe_timestamp_utc": now,
            "page_url": "",
            "response_url": "",
            "status": "",
            "content_type": "",
            "resource_type": "",
            "body_size": "0",
            "matched_terms": "",
            "short_body_sample": "",
            "raw_sample_file": "",
            "probe_status": status,
        }]
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def probe_with_playwright(urls: list[str]) -> pd.DataFrame:
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    except Exception:
        return empty_output("PLAYWRIGHT_NOT_AVAILABLE", urls)

    RAW_OUT.mkdir(parents=True, exist_ok=True)
    FULL_OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="EDGEiQ-Racing/1.0 network-probe",
            viewport={"width": 1280, "height": 900},
        )

        for page_url in urls[:MAX_PAGES]:
            log(f"probing {page_url}")
            page = context.new_page()
            response_meta = []

            def handle_response(response):
                resource_type = response.request.resource_type
                if resource_type not in {"xhr", "fetch"}:
                    return
                headers = response.headers or {}
                content_type = headers.get("content-type", "")
                body_text = ""
                matched = []
                raw_file = ""
                try:
                    body_text = response.text()
                    matched = find_terms(body_text)
                    operation = operation_from_url(response.url)
                    relevant_operation = operation in RELEVANT_OPERATIONS
                    if FULL_CAPTURE and (matched or relevant_operation):
                        raw_path = full_payload_filename(page_url, response.url, content_type)
                        raw_path.write_text(body_text, encoding="utf-8")
                        raw_file = raw_path.relative_to(PROJECT_ROOT).as_posix()
                    elif matched:
                        raw_path = sample_filename(page_url, response.url, content_type)
                        raw_path.write_text(body_text[:50000], encoding="utf-8")
                        raw_file = raw_path.relative_to(PROJECT_ROOT).as_posix()
                except Exception as exc:
                    body_text = f"BODY_READ_FAILED: {exc}"
                response_meta.append({
                    "probe_timestamp_utc": now,
                    "page_url": page_url,
                    "response_url": response.url,
                    "status": str(response.status),
                    "content_type": content_type,
                    "resource_type": resource_type,
                    "body_size": str(len(body_text)),
                    "matched_terms": ", ".join(matched),
                    "short_body_sample": sample_text(body_text),
                    "raw_sample_file": raw_file,
                    "probe_status": "MATCHED_TERMS" if matched else "NO_TERMS",
                })

            page.on("response", handle_response)
            try:
                page.goto(page_url, wait_until="networkidle", timeout=45000)
                page.wait_for_timeout(3000)
            except PlaywrightTimeoutError:
                log(f"timeout while probing {page_url}")
            except Exception as exc:
                log(f"warning: failed probing {page_url}: {exc}")
            finally:
                page.close()

            if response_meta:
                rows.extend(response_meta)
            else:
                rows.append({
                    "probe_timestamp_utc": now,
                    "page_url": page_url,
                    "response_url": "",
                    "status": "",
                    "content_type": "",
                    "resource_type": "",
                    "body_size": "0",
                    "matched_terms": "",
                    "short_body_sample": "",
                    "raw_sample_file": "",
                    "probe_status": "NO_XHR_OR_FETCH_RESPONSES",
                })

        context.close()
        browser.close()

    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    urls = candidate_urls()
    if not urls:
        log("NO_NETWORK_SECTIONAL_PAYLOAD_FOUND: no dynamic Racing.com speed-data URLs available")
        output = empty_output("NO_DYNAMIC_URLS_AVAILABLE", [])
    else:
        output = probe_with_playwright(urls[:MAX_PAGES])

    output.to_csv(OUT, index=False, encoding="utf-8")

    pages = len({url for url in output["page_url"].tolist() if clean(url)})
    matched = output[output["matched_terms"].astype(str).str.len() > 0] if not output.empty else pd.DataFrame()
    endpoints = matched["response_url"].drop_duplicates().tolist() if not matched.empty else []
    if endpoints:
        log(f"API/network candidates found: {len(endpoints)}")
        for endpoint in endpoints[:10]:
            log(f"candidate endpoint: {endpoint}")
    else:
        log("NO_NETWORK_SECTIONAL_PAYLOAD_FOUND")
    log(f"pages probed: {pages}")
    log(f"responses with sectional terms: {len(matched)}")
    if FULL_CAPTURE:
        full_count = len(list(FULL_OUT.glob("*"))) if FULL_OUT.exists() else 0
        log(f"full payload capture enabled: {full_count} files in {FULL_OUT.relative_to(PROJECT_ROOT)}")
    log(f"wrote {OUT.relative_to(APP_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
