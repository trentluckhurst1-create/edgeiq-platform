from __future__ import annotations

import csv
import html
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "racingcom_form_speed_data_url_audit_v1.csv"
OUTPUT = DATA / "racingcom_speed_data_client_assets_v1.csv"
AUDIT = DATA / "racingcom_speed_data_client_assets_v1_audit.csv"

PUBLIC_HOST = "www.racing.com"
USER_AGENT = "EDGEiQ-Racing/1.0 speed-data-client-assets-v1 (public page discovery only; no private API)"
SLEEP_SECONDS = float(os.environ.get("EDGEIQ_RACINGCOM_CLIENT_ASSET_SLEEP_SECONDS", "0.75"))
MAX_URLS = int(os.environ.get("EDGEIQ_RACINGCOM_CLIENT_ASSET_MAX_URLS", "48"))
SNIPPET_CHARS = 280

PRIVATE_ENDPOINT_PATTERNS = (
    "graphql",
    "graphql.rmdprod",
    "rmdprod",
    "x-api-key",
    "headerapikey",
    "/api/",
    "/services/",
)

API_KEY_PATTERNS = (
    "x-api-key",
    "headerapikey",
    "api key",
    "apikey",
)

KEYWORD_PATTERNS = (
    "csv",
    "download",
    "sectional",
    "sectionals",
    "speed",
    "split",
    "splits",
)

OUTPUT_COLUMNS = [
    "race_date",
    "track",
    "race_no",
    "speed_data_url",
    "asset_type",
    "asset_url",
    "asset_host",
    "asset_path",
    "same_origin",
    "keyword_match",
    "embedded_blob_type",
    "embedded_blob_id",
    "embedded_blob_chars",
    "embedded_json_valid",
    "embedded_top_keys",
    "evidence_snippet",
    "discovery_status",
    "safety_flag",
    "captured_at",
]

AUDIT_COLUMNS = [
    "input_rows_loaded",
    "unique_speed_data_urls",
    "pages_attempted",
    "pages_fetched",
    "pages_failed",
    "script_src_urls_found",
    "next_data_blobs_found",
    "window_state_blobs_found",
    "json_script_tags_found",
    "same_origin_public_asset_urls_found",
    "keyword_public_links_found",
    "csv_or_download_links_found",
    "graphql_used",
    "api_key_extracted",
    "private_endpoint_used",
    "safety_blocked_refs",
    "output_rows",
    "final_status",
]


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return "" if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def log(message: str) -> None:
    print(f"[racingcom_client_assets_v1] {message}")


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    tmp.replace(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as handle:
            return list(csv.DictReader(handle))


def is_private_reference(value: str) -> bool:
    lower = clean(value).lower()
    return any(pattern in lower for pattern in PRIVATE_ENDPOINT_PATTERNS)


def contains_api_key_reference(value: str) -> bool:
    lower = clean(value).lower()
    return any(pattern in lower for pattern in API_KEY_PATTERNS)


def is_public_speed_data_page(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    if parsed.netloc.lower() != PUBLIC_HOST:
        return False
    if is_private_reference(url):
        return False
    return bool(re.fullmatch(r"/form/\d{4}-\d{2}-\d{2}/[^/]+/race/\d+/speed-data", parsed.path))


def is_public_asset_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"}:
        return False
    if is_private_reference(url):
        return False
    if contains_api_key_reference(url):
        return False
    return bool(parsed.netloc)


def is_same_origin(url: str) -> bool:
    return urlparse(url).netloc.lower() == PUBLIC_HOST


def fetch_public_page(url: str) -> tuple[str, str, int]:
    if not is_public_speed_data_page(url):
        return "", "SAFETY_BLOCKED_NON_PUBLIC_SPEED_DATA_URL", 0

    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://www.racing.com/",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read().decode(charset, errors="replace")
            return body, "FETCHED", int(response.status)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return body, f"HTTP_{exc.code}", int(exc.code)
    except URLError as exc:
        return "", f"URL_ERROR_{clean(exc.reason)}", 0
    except Exception as exc:  # noqa: BLE001 - discovery should keep auditing other pages.
        return "", f"ERROR_{exc.__class__.__name__}", 0


def decoded_html(page: str) -> str:
    text = html.unescape(page)
    text = text.replace("\\u002F", "/")
    text = text.replace("\\/", "/")
    return text


def keyword_match(value: str) -> str:
    lower = clean(value).lower()
    matches = [keyword for keyword in KEYWORD_PATTERNS if keyword in lower]
    return "|".join(sorted(set(matches)))


def snippet(value: str) -> str:
    return clean(value)[:SNIPPET_CHARS]


def absolute_url(raw_url: str, base_url: str) -> str:
    raw = clean(raw_url)
    if not raw or raw.startswith(("mailto:", "tel:", "javascript:", "#", "data:")):
        return ""
    return urljoin(base_url, raw)


def row_base(source_row: dict[str, str], captured_at: str) -> dict[str, Any]:
    return {
        "race_date": clean(source_row.get("race_date")),
        "track": clean(source_row.get("track")),
        "race_no": clean(source_row.get("race_no")),
        "speed_data_url": clean(source_row.get("speed_data_url")),
        "captured_at": captured_at,
    }


def asset_row(
    source_row: dict[str, str],
    captured_at: str,
    asset_type: str,
    asset_url: str,
    embedded_blob_type: str = "",
    embedded_blob_id: str = "",
    embedded_blob_chars: int | str = "",
    embedded_json_valid: str = "",
    embedded_top_keys: str = "",
    evidence: str = "",
    discovery_status: str = "PUBLIC_CLIENT_ASSET_FOUND",
    safety_flag: str = "PUBLIC_PAGE_ONLY",
) -> dict[str, Any]:
    parsed = urlparse(asset_url) if asset_url else None
    row = row_base(source_row, captured_at)
    row.update(
        {
            "asset_type": asset_type,
            "asset_url": asset_url,
            "asset_host": parsed.netloc if parsed else "",
            "asset_path": parsed.path if parsed else "",
            "same_origin": str(is_same_origin(asset_url)).upper() if asset_url else "",
            "keyword_match": keyword_match(asset_url or evidence),
            "embedded_blob_type": embedded_blob_type,
            "embedded_blob_id": embedded_blob_id,
            "embedded_blob_chars": embedded_blob_chars,
            "embedded_json_valid": embedded_json_valid,
            "embedded_top_keys": embedded_top_keys,
            "evidence_snippet": snippet(evidence),
            "discovery_status": discovery_status,
            "safety_flag": safety_flag,
        }
    )
    return row


def parse_top_keys(raw_json: str) -> tuple[str, str]:
    try:
        payload = json.loads(raw_json)
    except Exception:
        return "FALSE", ""
    if isinstance(payload, dict):
        return "TRUE", "|".join(str(key) for key in list(payload.keys())[:20])
    if isinstance(payload, list):
        return "TRUE", f"LIST_LEN_{len(payload)}"
    return "TRUE", type(payload).__name__.upper()


def parse_script_srcs(page: str, base_url: str) -> tuple[list[str], int]:
    found: list[str] = []
    blocked = 0
    for match in re.finditer(r"""<script\b[^>]*\bsrc\s*=\s*["']([^"']+)["'][^>]*>""", page, flags=re.IGNORECASE | re.DOTALL):
        url = absolute_url(match.group(1), base_url)
        if not url:
            continue
        if is_private_reference(url) or contains_api_key_reference(url):
            blocked += 1
            continue
        if is_public_asset_url(url):
            found.append(url)
        else:
            blocked += 1
    return sorted(set(found)), blocked


def parse_href_src_keyword_links(page: str, base_url: str) -> tuple[list[tuple[str, str]], int]:
    decoded = decoded_html(page)
    found: list[tuple[str, str]] = []
    blocked = 0
    pattern = r"""(?:href|src|action)\s*=\s*["']([^"']+)["']"""
    for match in re.finditer(pattern, decoded, flags=re.IGNORECASE):
        raw = clean(match.group(1))
        if not keyword_match(raw):
            continue
        url = absolute_url(raw, base_url)
        if not url:
            continue
        if is_private_reference(url) or contains_api_key_reference(url):
            blocked += 1
            continue
        if is_public_asset_url(url):
            found.append((url, raw))
        else:
            blocked += 1
    return sorted(set(found)), blocked


def parse_same_origin_assets(page: str, base_url: str) -> tuple[list[str], int]:
    decoded = decoded_html(page)
    found: list[str] = []
    blocked = 0
    pattern = r"""(?:href|src|action)\s*=\s*["']([^"']+)["']"""
    for match in re.finditer(pattern, decoded, flags=re.IGNORECASE):
        url = absolute_url(match.group(1), base_url)
        if not url:
            continue
        if is_private_reference(url) or contains_api_key_reference(url):
            blocked += 1
            continue
        if is_same_origin(url) and is_public_asset_url(url):
            found.append(url)
    return sorted(set(found)), blocked


def parse_json_script_tags(page: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    pattern = r"""<script\b([^>]*)type\s*=\s*["']application/(?:ld\+)?json["']([^>]*)>(.*?)</script>"""
    for index, match in enumerate(re.finditer(pattern, page, flags=re.IGNORECASE | re.DOTALL), start=1):
        attrs = f"{match.group(1)} {match.group(2)}"
        body = clean(match.group(3))
        id_match = re.search(r"""id\s*=\s*["']([^"']+)["']""", attrs, flags=re.IGNORECASE)
        json_valid, top_keys = parse_top_keys(html.unescape(body))
        rows.append(
            {
                "id": clean(id_match.group(1)) if id_match else f"json_script_{index}",
                "body": body,
                "json_valid": json_valid,
                "top_keys": top_keys,
            }
        )
    return rows


def parse_next_data(page: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    pattern = r"""<script\b[^>]*id\s*=\s*["']__NEXT_DATA__["'][^>]*>(.*?)</script>"""
    for index, match in enumerate(re.finditer(pattern, page, flags=re.IGNORECASE | re.DOTALL), start=1):
        body = html.unescape(match.group(1)).strip()
        json_valid, top_keys = parse_top_keys(body)
        rows.append(
            {
                "id": "__NEXT_DATA__" if index == 1 else f"__NEXT_DATA___{index}",
                "body": body,
                "json_valid": json_valid,
                "top_keys": top_keys,
            }
        )
    return rows


def parse_window_state_blobs(page: str) -> list[dict[str, Any]]:
    decoded = decoded_html(page)
    rows: list[dict[str, Any]] = []
    patterns = [
        r"""window\.__[A-Za-z0-9_]+\s*=\s*({.*?});\s*</script>""",
        r"""window\.[A-Za-z0-9_]*(?:state|State|STORE|Store|DATA|Data)[A-Za-z0-9_]*\s*=\s*({.*?});\s*</script>""",
    ]
    seen: set[str] = set()
    for pattern in patterns:
        for match in re.finditer(pattern, decoded, flags=re.IGNORECASE | re.DOTALL):
            full = match.group(0)
            key_match = re.search(r"""window\.([A-Za-z0-9_]+)\s*=""", full)
            blob_id = key_match.group(1) if key_match else "window_state"
            body = match.group(1).strip()
            signature = f"{blob_id}:{body[:200]}"
            if signature in seen:
                continue
            seen.add(signature)
            json_valid, top_keys = parse_top_keys(body)
            rows.append(
                {
                    "id": blob_id,
                    "body": body,
                    "json_valid": json_valid,
                    "top_keys": top_keys,
                }
            )
    return rows


def load_speed_urls() -> tuple[list[dict[str, str]], int]:
    rows = read_csv(INPUT)
    seen: set[str] = set()
    output: list[dict[str, str]] = []
    for row in rows:
        url = clean(row.get("speed_data_url"))
        if not url or url in seen:
            continue
        if clean(row.get("fetch_status")) and clean(row.get("fetch_status")) != "FETCHED":
            continue
        seen.add(url)
        output.append(row)
    return output[:MAX_URLS], len(rows)


def final_status(
    public_assets: int,
    embedded_blobs: int,
    pages_fetched: int,
    safety_blocked_refs: int,
) -> str:
    if safety_blocked_refs and not public_assets and not embedded_blobs:
        return "SAFETY_BLOCKED"
    if embedded_blobs:
        return "PUBLIC_EMBEDDED_DATA_FOUND"
    if public_assets:
        return "PUBLIC_CLIENT_ASSETS_FOUND"
    if pages_fetched:
        return "NO_PUBLIC_CLIENT_SOURCE_FOUND"
    return "NO_PUBLIC_CLIENT_SOURCE_FOUND"


def main() -> None:
    captured_at = datetime.now(timezone.utc).isoformat()
    speed_rows, input_rows_loaded = load_speed_urls()
    output_rows: list[dict[str, Any]] = []

    pages_attempted = 0
    pages_fetched = 0
    pages_failed = 0
    script_src_urls_found = 0
    next_data_blobs_found = 0
    window_state_blobs_found = 0
    json_script_tags_found = 0
    same_origin_asset_urls_found = 0
    keyword_public_links_found = 0
    csv_or_download_links_found = 0
    safety_blocked_refs = 0

    graphql_used = False
    api_key_extracted = False
    private_endpoint_used = False

    log(f"loaded {len(speed_rows)} unique speed-data URLs from {INPUT.name}")

    for source_row in speed_rows:
        url = clean(source_row.get("speed_data_url"))
        if not is_public_speed_data_page(url):
            safety_blocked_refs += 1
            output_rows.append(
                asset_row(
                    source_row,
                    captured_at,
                    "BLOCKED_URL",
                    "",
                    evidence=url,
                    discovery_status="SAFETY_BLOCKED_NON_PUBLIC_SPEED_DATA_URL",
                    safety_flag="SAFETY_BLOCKED",
                )
            )
            continue

        pages_attempted += 1
        time.sleep(SLEEP_SECONDS)
        page, fetch_status, http_status = fetch_public_page(url)
        if fetch_status != "FETCHED":
            pages_failed += 1
            output_rows.append(
                asset_row(
                    source_row,
                    captured_at,
                    "FETCH_FAILURE",
                    "",
                    evidence=f"{fetch_status} HTTP {http_status}",
                    discovery_status=fetch_status,
                    safety_flag="PUBLIC_PAGE_ONLY",
                )
            )
            continue

        pages_fetched += 1

        if is_private_reference(page):
            # Private/API-looking references may exist in page source. This script records the
            # safety boundary by refusing to call or extract them.
            safety_blocked_refs += len(re.findall("|".join(re.escape(pattern) for pattern in PRIVATE_ENDPOINT_PATTERNS), page, flags=re.IGNORECASE))

        script_urls, blocked = parse_script_srcs(page, url)
        safety_blocked_refs += blocked
        for script_url in script_urls:
            script_src_urls_found += 1
            output_rows.append(
                asset_row(
                    source_row,
                    captured_at,
                    "SCRIPT_SRC",
                    script_url,
                    evidence=script_url,
                    discovery_status="PUBLIC_CLIENT_ASSET_FOUND",
                    safety_flag="PUBLIC_PAGE_ONLY",
                )
            )

        next_blobs = parse_next_data(page)
        for blob in next_blobs:
            next_data_blobs_found += 1
            output_rows.append(
                asset_row(
                    source_row,
                    captured_at,
                    "EMBEDDED_NEXT_DATA",
                    "",
                    embedded_blob_type="__NEXT_DATA__",
                    embedded_blob_id=blob["id"],
                    embedded_blob_chars=len(blob["body"]),
                    embedded_json_valid=blob["json_valid"],
                    embedded_top_keys=blob["top_keys"],
                    evidence=blob["body"],
                    discovery_status="PUBLIC_EMBEDDED_DATA_FOUND",
                    safety_flag="PUBLIC_PAGE_ONLY",
                )
            )

        window_blobs = parse_window_state_blobs(page)
        for blob in window_blobs:
            window_state_blobs_found += 1
            output_rows.append(
                asset_row(
                    source_row,
                    captured_at,
                    "WINDOW_STATE_BLOB",
                    "",
                    embedded_blob_type="WINDOW_STATE",
                    embedded_blob_id=blob["id"],
                    embedded_blob_chars=len(blob["body"]),
                    embedded_json_valid=blob["json_valid"],
                    embedded_top_keys=blob["top_keys"],
                    evidence=blob["body"],
                    discovery_status="PUBLIC_EMBEDDED_DATA_FOUND",
                    safety_flag="PUBLIC_PAGE_ONLY",
                )
            )

        json_scripts = parse_json_script_tags(page)
        for blob in json_scripts:
            json_script_tags_found += 1
            output_rows.append(
                asset_row(
                    source_row,
                    captured_at,
                    "JSON_SCRIPT_TAG",
                    "",
                    embedded_blob_type="JSON_SCRIPT",
                    embedded_blob_id=blob["id"],
                    embedded_blob_chars=len(blob["body"]),
                    embedded_json_valid=blob["json_valid"],
                    embedded_top_keys=blob["top_keys"],
                    evidence=blob["body"],
                    discovery_status="PUBLIC_EMBEDDED_DATA_FOUND",
                    safety_flag="PUBLIC_PAGE_ONLY",
                )
            )

        same_origin_urls, blocked = parse_same_origin_assets(page, url)
        safety_blocked_refs += blocked
        for asset_url in same_origin_urls:
            same_origin_asset_urls_found += 1
            output_rows.append(
                asset_row(
                    source_row,
                    captured_at,
                    "SAME_ORIGIN_PUBLIC_ASSET",
                    asset_url,
                    evidence=asset_url,
                    discovery_status="PUBLIC_CLIENT_ASSET_FOUND",
                    safety_flag="PUBLIC_PAGE_ONLY",
                )
            )

        keyword_links, blocked = parse_href_src_keyword_links(page, url)
        safety_blocked_refs += blocked
        for asset_url, raw in keyword_links:
            keyword_public_links_found += 1
            if "csv" in raw.lower() or "download" in raw.lower() or "csv" in asset_url.lower() or "download" in asset_url.lower():
                csv_or_download_links_found += 1
            output_rows.append(
                asset_row(
                    source_row,
                    captured_at,
                    "KEYWORD_PUBLIC_LINK",
                    asset_url,
                    evidence=raw,
                    discovery_status="PUBLIC_CLIENT_ASSET_FOUND",
                    safety_flag="PUBLIC_PAGE_ONLY",
                )
            )

    public_asset_count = script_src_urls_found + same_origin_asset_urls_found + keyword_public_links_found
    embedded_blob_count = next_data_blobs_found + window_state_blobs_found + json_script_tags_found
    status = final_status(public_asset_count, embedded_blob_count, pages_fetched, safety_blocked_refs)

    audit_row = {
        "input_rows_loaded": input_rows_loaded,
        "unique_speed_data_urls": len(speed_rows),
        "pages_attempted": pages_attempted,
        "pages_fetched": pages_fetched,
        "pages_failed": pages_failed,
        "script_src_urls_found": script_src_urls_found,
        "next_data_blobs_found": next_data_blobs_found,
        "window_state_blobs_found": window_state_blobs_found,
        "json_script_tags_found": json_script_tags_found,
        "same_origin_public_asset_urls_found": same_origin_asset_urls_found,
        "keyword_public_links_found": keyword_public_links_found,
        "csv_or_download_links_found": csv_or_download_links_found,
        "graphql_used": str(graphql_used).upper(),
        "api_key_extracted": str(api_key_extracted).upper(),
        "private_endpoint_used": str(private_endpoint_used).upper(),
        "safety_blocked_refs": safety_blocked_refs,
        "output_rows": len(output_rows),
        "final_status": status,
    }

    write_csv(OUTPUT, output_rows, OUTPUT_COLUMNS)
    write_csv(AUDIT, [audit_row], AUDIT_COLUMNS)

    log(f"wrote {OUTPUT.relative_to(ROOT)} rows={len(output_rows)}")
    log(f"wrote {AUDIT.relative_to(ROOT)} final_status={status}; embedded_blobs={embedded_blob_count}; public_assets={public_asset_count}")


if __name__ == "__main__":
    main()
