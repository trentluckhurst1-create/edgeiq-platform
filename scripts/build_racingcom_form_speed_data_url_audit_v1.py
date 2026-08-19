from __future__ import annotations

import csv
import html
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUTPUT = DATA / "racingcom_form_speed_data_url_audit_v1.csv"
SUMMARY = DATA / "racingcom_form_speed_data_url_audit_v1_summary.csv"

SOURCE_FILES = [
    DATA / "edgeiq_vic_live_terminal_feed_v1.csv",
    DATA / "edgeiq_vic_three_day_race_fields.csv",
    DATA / "edgeiq_vic_three_day_meeting_universe.csv",
    DATA / "race_fields.csv",
    DATA / "edgeiq_racingcom_calendar_discovery_v1.csv",
]

PUBLIC_HOST = "www.racing.com"
BASE_URL = "https://www.racing.com"
USER_AGENT = "EDGEiQ-Racing/1.0 form-speed-data-url-audit (public pages only; no private API)"
SLEEP_SECONDS = float(os.environ.get("EDGEIQ_RACINGCOM_URL_AUDIT_SLEEP_SECONDS", "0.75"))
MAX_RACES = int(os.environ.get("EDGEIQ_RACINGCOM_URL_AUDIT_MAX_RACES", "48"))

PRIVATE_ENDPOINT_PATTERNS = (
    "graphql",
    "graphql.rmdprod",
    "rmdprod",
    "x-api-key",
    "headerapikey",
    "/api/",
    "/services/",
)

OUTPUT_COLUMNS = [
    "input_source",
    "race_date",
    "track",
    "track_slug",
    "race_no",
    "form_url",
    "speed_data_url",
    "fetch_status",
    "http_status",
    "page_public_status",
    "csv_links_found",
    "csv_url",
    "discovery_status",
    "safety_flag",
    "captured_at",
]

SUMMARY_COLUMNS = [
    "source_files_checked",
    "source_files_found",
    "candidate_rows_loaded",
    "unique_race_contexts",
    "speed_data_pages_attempted",
    "speed_data_pages_fetched",
    "csv_links_found",
    "graphql_used",
    "api_key_extracted",
    "private_endpoint_used",
    "final_status",
]


@dataclass(frozen=True)
class RaceContext:
    input_source: str
    race_date: str
    track: str
    race_no: str


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return "" if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def log(message: str) -> None:
    print(f"[racingcom_url_audit_v1] {message}")


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


def first(row: dict[str, str], columns: list[str]) -> str:
    for column in columns:
        value = clean(row.get(column))
        if value:
            return value
    return ""


def race_no(value: Any) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def race_date(value: Any) -> str:
    text = clean(value)
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    return match.group(0) if match else ""


def normalise_track_for_slug(track: str) -> str:
    text = clean(track).lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[’']", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text


def is_private_reference(value: str) -> bool:
    lower = clean(value).lower()
    return any(pattern in lower for pattern in PRIVATE_ENDPOINT_PATTERNS)


def is_public_racingcom_page(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    if parsed.netloc.lower() != PUBLIC_HOST:
        return False
    if is_private_reference(url):
        return False
    return parsed.path.lower().startswith("/form/")


def is_public_csv_or_download_candidate(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    if parsed.netloc.lower() != PUBLIC_HOST:
        return False
    if is_private_reference(url):
        return False
    lower = url.lower()
    return ".csv" in lower or "csv" in lower or "download" in lower


def form_url(context: RaceContext) -> str:
    track_slug = normalise_track_for_slug(context.track)
    return f"{BASE_URL}/form/{context.race_date}/{track_slug}/race/{context.race_no}"


def speed_data_url(context: RaceContext) -> str:
    return f"{form_url(context)}/speed-data"


def fetch_public_page(url: str) -> tuple[str, str, int]:
    if not is_public_racingcom_page(url):
        return "", "SAFETY_BLOCKED_NON_PUBLIC_URL", 0

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
    except Exception as exc:  # noqa: BLE001 - audit each URL independently.
        return "", f"ERROR_{exc.__class__.__name__}", 0


def html_for_link_search(page: str) -> str:
    text = html.unescape(page)
    text = text.replace("\\u002F", "/")
    text = text.replace("\\/", "/")
    return text


def absolute_links(page: str, base_url: str) -> list[str]:
    decoded = html_for_link_search(page)
    links: list[str] = []
    seen: set[str] = set()

    for match in re.finditer(r"""(?:href|src|action)\s*=\s*["']([^"']+)["']""", decoded, flags=re.IGNORECASE):
        raw = clean(match.group(1))
        if not raw or raw.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        absolute = urljoin(base_url, raw)
        if absolute not in seen:
            seen.add(absolute)
            links.append(absolute)

    for match in re.finditer(r"""https://www\.racing\.com/[^"'\s<>\\]+""", decoded, flags=re.IGNORECASE):
        absolute = match.group(0)
        if absolute not in seen:
            seen.add(absolute)
            links.append(absolute)

    return links


def csv_links_from_page(page: str, base_url: str) -> tuple[list[str], int]:
    links: list[str] = []
    blocked = 0
    for url in absolute_links(page, base_url):
        if is_private_reference(url):
            blocked += 1
            continue
        if not (".csv" in url.lower() or "csv" in url.lower() or "download" in url.lower()):
            continue
        if is_public_csv_or_download_candidate(url):
            links.append(url)
        else:
            blocked += 1
    return sorted(set(links)), blocked


def load_race_contexts() -> tuple[list[RaceContext], int, int]:
    contexts: list[RaceContext] = []
    candidate_rows_loaded = 0
    source_files_found = 0
    seen: set[tuple[str, str, str]] = set()

    for path in SOURCE_FILES:
        rows = read_csv(path)
        if rows:
            source_files_found += 1
        candidate_rows_loaded += len(rows)

        for row in rows:
            date = race_date(first(row, ["race_date", "date", "meeting_date"]))
            track = first(row, ["track", "track_name", "venue", "venueName"])
            rn = race_no(first(row, ["race_no", "race_number", "race"]))
            if not date or not track or not rn:
                continue

            key = (date, clean(track).upper(), rn)
            if key in seen:
                continue
            seen.add(key)
            contexts.append(
                RaceContext(
                    input_source=path.name,
                    race_date=date,
                    track=track,
                    race_no=rn,
                )
            )

    contexts.sort(key=lambda item: (item.race_date, item.track.upper(), int(item.race_no)))
    return contexts[:MAX_RACES], candidate_rows_loaded, source_files_found


def row_for_context(
    context: RaceContext,
    fetch_status: str,
    http_status: int,
    page_public_status: str,
    csv_url: str,
    csv_links_found: int,
    discovery_status: str,
    safety_flag: str,
    captured_at: str,
) -> dict[str, Any]:
    track_slug = normalise_track_for_slug(context.track)
    return {
        "input_source": context.input_source,
        "race_date": context.race_date,
        "track": context.track,
        "track_slug": track_slug,
        "race_no": context.race_no,
        "form_url": form_url(context),
        "speed_data_url": speed_data_url(context),
        "fetch_status": fetch_status,
        "http_status": http_status,
        "page_public_status": page_public_status,
        "csv_links_found": csv_links_found,
        "csv_url": csv_url,
        "discovery_status": discovery_status,
        "safety_flag": safety_flag,
        "captured_at": captured_at,
    }


def main() -> None:
    captured_at = datetime.now(timezone.utc).isoformat()
    contexts, candidate_rows_loaded, source_files_found = load_race_contexts()
    output_rows: list[dict[str, Any]] = []

    graphql_used = False
    api_key_extracted = False
    private_endpoint_used = False
    safety_blocked = 0
    speed_pages_attempted = 0
    speed_pages_fetched = 0
    unique_csv_links: set[str] = set()

    log(f"loaded {len(contexts)} unique race contexts from known local sources")

    for context in contexts:
        url = speed_data_url(context)
        if not is_public_racingcom_page(url):
            safety_blocked += 1
            output_rows.append(
                row_for_context(
                    context,
                    "NOT_FETCHED",
                    0,
                    "SAFETY_BLOCKED_NON_PUBLIC_URL",
                    "",
                    0,
                    "SAFETY_BLOCKED",
                    "SAFETY_BLOCKED",
                    captured_at,
                )
            )
            continue

        speed_pages_attempted += 1
        time.sleep(SLEEP_SECONDS)
        page, fetch_status, http_status = fetch_public_page(url)
        if fetch_status != "FETCHED":
            output_rows.append(
                row_for_context(
                    context,
                    fetch_status,
                    http_status,
                    "PUBLIC_PAGE_FETCH_FAILED",
                    "",
                    0,
                    fetch_status,
                    "PUBLIC_PAGE_ONLY",
                    captured_at,
                )
            )
            continue

        speed_pages_fetched += 1
        csv_links, blocked_links = csv_links_from_page(page, url)
        if blocked_links:
            safety_blocked += blocked_links
        if csv_links:
            for csv_url in csv_links:
                unique_csv_links.add(csv_url)
                output_rows.append(
                    row_for_context(
                        context,
                        fetch_status,
                        http_status,
                        "PUBLIC_SPEED_DATA_PAGE_FETCHED",
                        csv_url,
                        len(csv_links),
                        "CSV_LINK_FOUND",
                        "PUBLIC_PAGE_ONLY",
                        captured_at,
                    )
                )
        else:
            output_rows.append(
                row_for_context(
                    context,
                    fetch_status,
                    http_status,
                    "PUBLIC_SPEED_DATA_PAGE_FETCHED",
                    "",
                    0,
                    "SPEED_DATA_FOUND_NO_CSV_LINKS",
                    "PUBLIC_PAGE_ONLY",
                    captured_at,
                )
            )

    if safety_blocked:
        final_status = "SAFETY_BLOCKED"
    elif unique_csv_links:
        final_status = "CSV_LINKS_FOUND"
    elif speed_pages_fetched:
        final_status = "SPEED_DATA_FOUND_NO_CSV_LINKS"
    else:
        final_status = "NO_VALID_SPEED_DATA_FOUND"

    summary_row = {
        "source_files_checked": len(SOURCE_FILES),
        "source_files_found": source_files_found,
        "candidate_rows_loaded": candidate_rows_loaded,
        "unique_race_contexts": len(contexts),
        "speed_data_pages_attempted": speed_pages_attempted,
        "speed_data_pages_fetched": speed_pages_fetched,
        "csv_links_found": len(unique_csv_links),
        "graphql_used": str(graphql_used).upper(),
        "api_key_extracted": str(api_key_extracted).upper(),
        "private_endpoint_used": str(private_endpoint_used).upper(),
        "final_status": final_status,
    }

    write_csv(OUTPUT, output_rows, OUTPUT_COLUMNS)
    write_csv(SUMMARY, [summary_row], SUMMARY_COLUMNS)

    log(f"wrote {OUTPUT.relative_to(ROOT)} rows={len(output_rows)}")
    log(f"wrote {SUMMARY.relative_to(ROOT)} final_status={final_status}; csv_links_found={len(unique_csv_links)}")


if __name__ == "__main__":
    main()
