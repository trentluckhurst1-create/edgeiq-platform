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

OUT = DATA / "racingcom_calendar_speed_data_csv_links_v1.csv"
AUDIT = DATA / "racingcom_calendar_speed_data_csv_links_v1_audit.csv"

CALENDAR_URL = "https://www.racing.com/calendar"
PUBLIC_HOST = "www.racing.com"
USER_AGENT = "EDGEiQ-Racing/1.0 public-calendar-speed-csv-discovery (public pages only; no private API)"
SLEEP_SECONDS = float(os.environ.get("EDGEIQ_RACINGCOM_CSV_DISCOVERY_SLEEP_SECONDS", "0.75"))
MAX_MEETINGS = int(os.environ.get("EDGEIQ_RACINGCOM_CSV_DISCOVERY_MAX_MEETINGS", "30"))
MAX_RACES_PER_MEETING = int(os.environ.get("EDGEIQ_RACINGCOM_CSV_DISCOVERY_MAX_RACES_PER_MEETING", "12"))

PRIVATE_ENDPOINT_PATTERNS = (
    "graphql",
    "graphql.rmdprod",
    "rmdprod",
    "x-api-key",
    "headerapikey",
    "headerapikey",
    "/api/",
    "/services/",
)

JUMPOUT_TRIAL_PATTERNS = (
    "jumpout",
    "jump out",
    "jump-outs",
    "jump-outs",
    "trial",
    "trials",
    "official trial",
    "official trials",
)

PICNIC_PATTERNS = (
    "picnic",
    "picnics",
)

OUTPUT_COLUMNS = [
    "meeting_date",
    "track",
    "meeting_url",
    "meeting_type",
    "excluded_flag",
    "excluded_reason",
    "speed_data_url",
    "race_no",
    "race_name",
    "csv_url",
    "discovery_status",
    "safety_flag",
]

AUDIT_COLUMNS = [
    "calendar_pages_checked",
    "meetings_found",
    "meetings_excluded_jumpouts_trials",
    "meetings_excluded_picnics",
    "valid_meetings_checked",
    "speed_data_pages_found",
    "csv_links_found",
    "graphql_used",
    "api_key_extracted",
    "private_endpoint_used",
    "final_status",
]


@dataclass(frozen=True)
class Meeting:
    meeting_date: str
    track_slug: str
    track: str
    meeting_url: str
    meeting_type: str
    excluded_flag: str
    excluded_reason: str


@dataclass(frozen=True)
class Race:
    race_no: str
    race_name: str
    race_url: str
    speed_data_url: str


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return "" if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-"} else text


def log(message: str) -> None:
    print(f"[racingcom_csv_discovery_v1] {message}")


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    tmp.replace(path)


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
    path = parsed.path.lower()
    return path == "/calendar" or path.startswith("/form/")


def is_public_racingcom_csv_candidate(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    if parsed.netloc.lower() != PUBLIC_HOST:
        return False
    if is_private_reference(url):
        return False
    path = parsed.path.lower()
    query = parsed.query.lower()
    return ".csv" in path or "csv" in query or "download" in query


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
    except Exception as exc:  # noqa: BLE001 - discovery should audit failures per URL.
        return "", f"ERROR_{exc.__class__.__name__}", 0


def absolute_links(page: str, base_url: str) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"""(?:href|src|action)\s*=\s*["']([^"']+)["']""", page, flags=re.IGNORECASE):
        raw = clean(match.group(1))
        if not raw or raw.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        absolute = urljoin(base_url, raw)
        if absolute not in seen:
            seen.add(absolute)
            links.append(absolute)
    return links


def html_for_embedded_links(page: str) -> str:
    text = html.unescape(page)
    text = text.replace("\\u002F", "/")
    text = text.replace("\\/", "/")
    return text


def embedded_form_meeting_links(page: str) -> list[str]:
    decoded = html_for_embedded_links(page)
    links: list[str] = []
    seen: set[str] = set()
    pattern = r"""(?:https://www\.racing\.com)?(/form/\d{4}-\d{2}-\d{2}/[A-Za-z0-9-]+)(?=[/?#"' <>\]\\]|$)"""
    for match in re.finditer(pattern, decoded, flags=re.IGNORECASE):
        absolute = urljoin("https://www.racing.com", match.group(1))
        if absolute not in seen:
            seen.add(absolute)
            links.append(absolute)
    return links


def embedded_form_race_links(page: str, meeting: Meeting) -> list[str]:
    decoded = html_for_embedded_links(page)
    links: list[str] = []
    seen: set[str] = set()
    pattern = rf"""(?:https://www\.racing\.com)?(/form/{re.escape(meeting.meeting_date)}/{re.escape(meeting.track_slug)}/race/\d+(?:/speed-data)?)(?=[/?#"' <>\]\\]|$)"""
    for match in re.finditer(pattern, decoded, flags=re.IGNORECASE):
        absolute = urljoin("https://www.racing.com", match.group(1))
        if absolute not in seen:
            seen.add(absolute)
            links.append(absolute)
    return links


def tag_text_near_link(page: str, url: str) -> str:
    target_parts = [url]
    parsed = urlparse(url)
    if parsed.path:
        target_parts.append(parsed.path)
    for target in target_parts:
        index = page.find(target)
        if index >= 0:
            start = max(0, index - 750)
            end = min(len(page), index + 1250)
            return visible_text(page[start:end])
    return ""


def visible_text(page: str) -> str:
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", page)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?is)<noscript[^>]*>.*?</noscript>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    return clean(text)


def title_from_slug(slug: str) -> str:
    words = [part for part in re.split(r"[-_]+", slug) if part]
    return " ".join(word.upper() for word in words)


def classify_meeting(context: str, meeting_url: str) -> tuple[str, str, str]:
    combined = f"{context} {meeting_url}".lower()
    if any(pattern in combined for pattern in JUMPOUT_TRIAL_PATTERNS):
        return "JUMPOUT_TRIAL", "TRUE", "JUMPOUT_TRIAL_MEETING"
    if any(pattern in combined for pattern in PICNIC_PATTERNS):
        return "PICNIC", "TRUE", "PICNIC_MEETING"
    return "STANDARD_RACE_MEETING", "FALSE", ""


def discover_meetings(calendar_page: str) -> list[Meeting]:
    meetings: dict[str, Meeting] = {}
    candidate_links = absolute_links(calendar_page, CALENDAR_URL) + embedded_form_meeting_links(calendar_page)
    for url in candidate_links:
        parsed = urlparse(url)
        if parsed.netloc.lower() != PUBLIC_HOST:
            continue
        if is_private_reference(url):
            continue
        match = re.fullmatch(r"/form/(\d{4}-\d{2}-\d{2})/([^/?#]+)/*", parsed.path)
        if not match:
            continue
        meeting_date, slug = match.groups()
        context = tag_text_near_link(calendar_page, parsed.path)
        meeting_type, excluded_flag, excluded_reason = classify_meeting(context, url)
        meetings[url] = Meeting(
            meeting_date=meeting_date,
            track_slug=slug,
            track=title_from_slug(slug),
            meeting_url=url,
            meeting_type=meeting_type,
            excluded_flag=excluded_flag,
            excluded_reason=excluded_reason,
        )
    return sorted(meetings.values(), key=lambda item: (item.meeting_date, item.track, item.meeting_url))


def extract_link_label(page: str, link_path: str) -> str:
    escaped = re.escape(link_path)
    patterns = [
        rf"""<a\b[^>]*href=["'][^"']*{escaped}[^"']*["'][^>]*>(.*?)</a>""",
        rf"""<a\b[^>]*href=["'][^"']*/race/\d+[^"']*["'][^>]*>(.*?)</a>""",
    ]
    for pattern in patterns:
        match = re.search(pattern, page, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return visible_text(match.group(1))
    return ""


def discover_races(meeting: Meeting, meeting_page: str) -> list[Race]:
    races: dict[str, Race] = {}
    candidate_links = absolute_links(meeting_page, meeting.meeting_url) + embedded_form_race_links(meeting_page, meeting)
    for url in candidate_links:
        parsed = urlparse(url)
        if parsed.netloc.lower() != PUBLIC_HOST:
            continue
        if is_private_reference(url):
            continue
        pattern = rf"/form/{re.escape(meeting.meeting_date)}/{re.escape(meeting.track_slug)}/race/(\d+)(?:/speed-data)?/*"
        match = re.fullmatch(pattern, parsed.path)
        if not match:
            continue
        race_no = str(int(match.group(1)))
        race_url = f"https://www.racing.com/form/{meeting.meeting_date}/{meeting.track_slug}/race/{race_no}"
        speed_data_url = f"{race_url}/speed-data"
        label = extract_link_label(meeting_page, parsed.path)
        races[race_no] = Race(
            race_no=race_no,
            race_name=label,
            race_url=race_url,
            speed_data_url=speed_data_url,
        )

    def sort_key(item: Race) -> int:
        try:
            return int(item.race_no)
        except ValueError:
            return 999

    return sorted(races.values(), key=sort_key)[:MAX_RACES_PER_MEETING]


def csv_links_from_speed_page(speed_page: str, speed_data_url: str) -> tuple[list[str], list[str]]:
    csv_links: list[str] = []
    blocked: list[str] = []
    for url in absolute_links(speed_page, speed_data_url):
        lower = url.lower()
        if is_private_reference(url):
            blocked.append(url)
            continue
        if ".csv" not in lower and "csv" not in lower and "download" not in lower:
            continue
        if is_public_racingcom_csv_candidate(url):
            csv_links.append(url)
        else:
            blocked.append(url)
    return sorted(set(csv_links)), sorted(set(blocked))


def empty_output_row(meeting: Meeting, status: str, safety_flag: str = "PUBLIC_PAGE_ONLY") -> dict[str, Any]:
    return {
        "meeting_date": meeting.meeting_date,
        "track": meeting.track,
        "meeting_url": meeting.meeting_url,
        "meeting_type": meeting.meeting_type,
        "excluded_flag": meeting.excluded_flag,
        "excluded_reason": meeting.excluded_reason,
        "speed_data_url": "",
        "race_no": "",
        "race_name": "",
        "csv_url": "",
        "discovery_status": status,
        "safety_flag": safety_flag,
    }


def output_row(
    meeting: Meeting,
    race: Race,
    csv_url: str,
    status: str,
    safety_flag: str = "PUBLIC_PAGE_ONLY",
) -> dict[str, Any]:
    return {
        "meeting_date": meeting.meeting_date,
        "track": meeting.track,
        "meeting_url": meeting.meeting_url,
        "meeting_type": meeting.meeting_type,
        "excluded_flag": meeting.excluded_flag,
        "excluded_reason": meeting.excluded_reason,
        "speed_data_url": race.speed_data_url,
        "race_no": race.race_no,
        "race_name": race.race_name,
        "csv_url": csv_url,
        "discovery_status": status,
        "safety_flag": safety_flag,
    }


def final_status(csv_links_found: int, speed_pages_found: int, safety_blocked: int) -> str:
    if safety_blocked:
        return "SAFETY_BLOCKED"
    if csv_links_found:
        return "CSV_LINKS_FOUND"
    if speed_pages_found:
        return "SPEED_DATA_FOUND_NO_CSV_LINKS"
    return "NO_VALID_SPEED_DATA_FOUND"


def main() -> None:
    graphql_used = False
    api_key_extracted = False
    private_endpoint_used = False
    safety_blocked = 0
    calendar_pages_checked = 0
    valid_meetings_checked = 0
    speed_data_pages_found = 0
    unique_csv_links: set[str] = set()
    output_rows: list[dict[str, Any]] = []

    log(f"fetching public calendar: {CALENDAR_URL}")
    calendar_page, calendar_status, calendar_http = fetch_public_page(CALENDAR_URL)
    calendar_pages_checked = 1

    if calendar_status != "FETCHED":
        log(f"calendar fetch failed: {calendar_status} http={calendar_http}")
        audit_row = {
            "calendar_pages_checked": calendar_pages_checked,
            "meetings_found": 0,
            "meetings_excluded_jumpouts_trials": 0,
            "meetings_excluded_picnics": 0,
            "valid_meetings_checked": 0,
            "speed_data_pages_found": 0,
            "csv_links_found": 0,
            "graphql_used": str(graphql_used).upper(),
            "api_key_extracted": str(api_key_extracted).upper(),
            "private_endpoint_used": str(private_endpoint_used).upper(),
            "final_status": "NO_VALID_SPEED_DATA_FOUND",
        }
        write_csv(OUT, [], OUTPUT_COLUMNS)
        write_csv(AUDIT, [audit_row], AUDIT_COLUMNS)
        return

    if is_private_reference(calendar_page):
        # The page may reference application code, but this script must not follow private/API URLs.
        log("calendar HTML contains private/API-looking references; they will not be followed")

    meetings = discover_meetings(calendar_page)
    meetings_found = len(meetings)
    excluded_jumpouts_trials = sum(1 for meeting in meetings if meeting.excluded_reason == "JUMPOUT_TRIAL_MEETING")
    excluded_picnics = sum(1 for meeting in meetings if meeting.excluded_reason == "PICNIC_MEETING")
    valid_meetings = [meeting for meeting in meetings if meeting.excluded_flag != "TRUE"][:MAX_MEETINGS]

    for meeting in meetings:
        if meeting.excluded_flag == "TRUE":
            output_rows.append(empty_output_row(meeting, "EXCLUDED_MEETING", "PUBLIC_PAGE_ONLY"))

    log(f"meetings found={meetings_found}; valid meetings to check={len(valid_meetings)}")

    for meeting in valid_meetings:
        if not is_public_racingcom_page(meeting.meeting_url):
            safety_blocked += 1
            output_rows.append(empty_output_row(meeting, "SAFETY_BLOCKED_MEETING_URL", "SAFETY_BLOCKED"))
            continue

        time.sleep(SLEEP_SECONDS)
        meeting_page, meeting_status, meeting_http = fetch_public_page(meeting.meeting_url)
        valid_meetings_checked += 1
        if meeting_status != "FETCHED":
            output_rows.append(empty_output_row(meeting, f"MEETING_PAGE_{meeting_status}", "PUBLIC_PAGE_ONLY"))
            log(f"meeting page failed {meeting.meeting_url}: {meeting_status} http={meeting_http}")
            continue

        races = discover_races(meeting, meeting_page)
        if not races:
            output_rows.append(empty_output_row(meeting, "NO_RACE_LINKS_VISIBLE_ON_PUBLIC_MEETING_PAGE", "PUBLIC_PAGE_ONLY"))
            continue

        for race in races:
            if not is_public_racingcom_page(race.speed_data_url):
                safety_blocked += 1
                output_rows.append(output_row(meeting, race, "", "SAFETY_BLOCKED_SPEED_DATA_URL", "SAFETY_BLOCKED"))
                continue

            time.sleep(SLEEP_SECONDS)
            speed_page, speed_status, speed_http = fetch_public_page(race.speed_data_url)
            if speed_status != "FETCHED":
                output_rows.append(output_row(meeting, race, "", f"SPEED_DATA_PAGE_{speed_status}", "PUBLIC_PAGE_ONLY"))
                log(f"speed-data page failed {race.speed_data_url}: {speed_status} http={speed_http}")
                continue

            speed_data_pages_found += 1
            csv_links, blocked_links = csv_links_from_speed_page(speed_page, race.speed_data_url)
            if blocked_links:
                safety_blocked += len(blocked_links)

            if csv_links:
                for csv_url in csv_links:
                    unique_csv_links.add(csv_url)
                    output_rows.append(output_row(meeting, race, csv_url, "CSV_LINK_FOUND", "PUBLIC_PAGE_ONLY"))
            else:
                output_rows.append(output_row(meeting, race, "", "SPEED_DATA_FOUND_NO_CSV_LINKS", "PUBLIC_PAGE_ONLY"))

    status = final_status(len(unique_csv_links), speed_data_pages_found, safety_blocked)
    audit_row = {
        "calendar_pages_checked": calendar_pages_checked,
        "meetings_found": meetings_found,
        "meetings_excluded_jumpouts_trials": excluded_jumpouts_trials,
        "meetings_excluded_picnics": excluded_picnics,
        "valid_meetings_checked": valid_meetings_checked,
        "speed_data_pages_found": speed_data_pages_found,
        "csv_links_found": len(unique_csv_links),
        "graphql_used": str(graphql_used).upper(),
        "api_key_extracted": str(api_key_extracted).upper(),
        "private_endpoint_used": str(private_endpoint_used).upper(),
        "final_status": status,
    }

    write_csv(OUT, output_rows, OUTPUT_COLUMNS)
    write_csv(AUDIT, [audit_row], AUDIT_COLUMNS)

    log(f"wrote {OUT.relative_to(ROOT)} rows={len(output_rows)}")
    log(f"wrote {AUDIT.relative_to(ROOT)} final_status={status}; csv_links_found={len(unique_csv_links)}")


if __name__ == "__main__":
    main()
