from __future__ import annotations

import csv
import html
import json
import os
import re
import time
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_FEED = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
RACE_STATUS = DATA / "edgeiq_race_status_safety_audit_v1.csv"

OUT = DATA / "racingcom_public_sectionals_v1.csv"
AUDIT = DATA / "racingcom_public_sectionals_v1_audit.csv"
RAW_PAGES = DATA / "racingcom_public_sectionals_raw_pages_v1.json"

BASE = "https://www.racing.com"
USER_AGENT = "EDGEiQ-Racing/1.0 public-sectionals-research (public HTML only; no private API)"
SLEEP_SECONDS = float(os.environ.get("EDGEIQ_PUBLIC_SECTIONALS_SLEEP_SECONDS", "0.75"))
MAX_URLS = int(os.environ.get("EDGEIQ_PUBLIC_SECTIONALS_MAX_URLS", "24"))
RAW_HTML_MAX_CHARS = int(os.environ.get("EDGEIQ_PUBLIC_SECTIONALS_RAW_HTML_MAX_CHARS", "500000"))

TRACK_SLUGS = {
    "SANDOWN LAKESIDE": "sandown-lakeside",
    "SANDOWN HILLSIDE": "sandown-hillside",
    "SANDOWN": "sandown",
    "KILMORE": "kilmore",
    "ECHUCA": "echuca",
    "CAULFIELD": "caulfield",
    "FLEMINGTON": "flemington",
    "BENDIGO": "bendigo",
    "BALLARAT": "ballarat",
    "PAKENHAM": "pakenham",
    "GEELONG": "geelong",
    "MOONEE VALLEY": "moonee-valley",
    "MORNINGTON": "mornington",
    "WARRNAMBOOL": "warrnambool",
    "SALE": "sale",
    "SEYMOUR": "seymour",
}

PRIVATE_ENDPOINT_PATTERNS = (
    "graphql.rmdprod.racing.com",
    "x-api-key",
    "headerapikey",
)

SECTIONAL_TERMS = (
    "sectional",
    "sectionals",
    "splits",
    "split time",
    "cumulative",
    "position in running",
    "speed data",
)

OUTPUT_FIELDS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key",
    "sectional_distance",
    "split_time",
    "cumulative_time",
    "position_in_running",
    "source_url",
    "capture_status",
    "capture_note",
    "captured_at",
]

AUDIT_FIELDS = ["metric", "value", "notes"]


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return "" if text.lower() in {"nan", "none", "null", "n/a", "-"} else text


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as handle:
            return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    tmp.replace(path)


def first(row: dict[str, str], names: list[str]) -> str:
    for name in names:
        value = clean(row.get(name))
        if value:
            return value
    return ""


def canonical_horse(value: Any) -> str:
    text = clean(value).upper()
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def normalise_track(value: Any) -> str:
    text = clean(value).upper()
    text = re.sub(r"^(SPORTSBET|SPORTS BET|BET365|LADBROKES|TABTOUCH|TAB)\s+", "", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def race_no(value: Any) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def track_slug(track: str) -> str:
    key = normalise_track(track)
    if key in TRACK_SLUGS:
        return TRACK_SLUGS[key]
    return re.sub(r"[^a-z0-9]+", "-", clean(track).lower()).strip("-")


def speed_data_url(race_date: str, track: str, race_number: str) -> str:
    return f"{BASE}/form/{race_date}/{track_slug(track)}/race/{race_no(race_number)}/speed-data"


def is_public_speed_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    if parsed.netloc.lower() != "www.racing.com":
        return False
    return bool(re.fullmatch(r"/form/\d{4}-\d{2}-\d{2}/[^/]+/race/\d+/speed-data", parsed.path))


def build_status_lookup() -> dict[tuple[str, str, str], str]:
    lookup: dict[tuple[str, str, str], str] = {}
    if not RACE_STATUS.exists():
        return lookup
    for row in read_csv(RACE_STATUS):
        key = (
            first(row, ["race_date"]),
            normalise_track(first(row, ["track"])),
            race_no(first(row, ["race_no"])),
        )
        if all(key) and key not in lookup:
            lookup[key] = first(row, ["race_status"])
    return lookup


def build_candidates() -> list[dict[str, str]]:
    status_lookup = build_status_lookup()
    seen: set[tuple[str, str, str]] = set()
    rows: list[dict[str, str]] = []
    for row in read_csv(LIVE_FEED):
        date = first(row, ["race_date", "date"])
        track = first(row, ["track"])
        rn = race_no(first(row, ["race_no"]))
        key = (date, normalise_track(track), rn)
        if not all(key) or key in seen:
            continue
        seen.add(key)
        url = speed_data_url(date, track, rn)
        rows.append(
            {
                "race_date": date,
                "track": track,
                "race_no": rn,
                "race_status": status_lookup.get(key, ""),
                "source_url": url,
            }
        )
    rows.sort(key=lambda item: (item["race_date"], normalise_track(item["track"]), int(item["race_no"])))
    return rows[:MAX_URLS]


def fetch_public_html(url: str) -> tuple[str, str, int, dict[str, str]]:
    if not is_public_speed_url(url):
        return "", "REJECTED_NON_PUBLIC_SPEED_URL", 0, {}
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=25) as response:
            body = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            headers = {
                "content_type": response.headers.get("content-type", ""),
                "final_url": response.geturl(),
            }
            return body.decode(charset, errors="replace"), "FETCHED", int(response.status), headers
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return body, f"HTTP_{exc.code}", int(exc.code), {"content_type": exc.headers.get("content-type", "") if exc.headers else ""}
    except URLError as exc:
        return "", f"URL_ERROR_{clean(exc.reason)}", 0, {}
    except Exception as exc:  # noqa: BLE001 - capture audit must fail per URL, not globally.
        return "", f"ERROR_{exc.__class__.__name__}", 0, {}


class VisibleTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._in_script_like = False
        self._in_table = False
        self._in_cell = False
        self._current_table: list[list[str]] = []
        self._current_row: list[str] = []
        self._current_cell: list[str] = []
        self.visible_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"}:
            self._in_script_like = True
            return
        if tag == "table":
            self._in_table = True
            self._current_table = []
        elif self._in_table and tag == "tr":
            self._current_row = []
        elif self._in_table and tag in {"td", "th"}:
            self._in_cell = True
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"}:
            self._in_script_like = False
            return
        if self._in_table and tag in {"td", "th"} and self._in_cell:
            self._current_row.append(clean(" ".join(self._current_cell)))
            self._current_cell = []
            self._in_cell = False
        elif self._in_table and tag == "tr":
            if any(self._current_row):
                self._current_table.append(self._current_row)
            self._current_row = []
        elif tag == "table" and self._in_table:
            if self._current_table:
                self.tables.append(self._current_table)
            self._current_table = []
            self._in_table = False

    def handle_data(self, data: str) -> None:
        if self._in_script_like:
            return
        text = clean(html.unescape(data))
        if not text:
            return
        self.visible_text.append(text)
        if self._in_cell:
            self._current_cell.append(text)


def public_visible_content(page: str) -> tuple[str, list[list[list[str]]]]:
    parser = VisibleTableParser()
    parser.feed(page)
    return " ".join(parser.visible_text), parser.tables


def header_index(headers: list[str], needles: list[str]) -> int | None:
    normalised = [re.sub(r"[^a-z0-9]+", "", header.lower()) for header in headers]
    for idx, header in enumerate(normalised):
        for needle in needles:
            if needle in header:
                return idx
    return None


def table_has_sectional_headers(headers: list[str]) -> bool:
    text = " ".join(headers).lower()
    return any(term in text for term in ["sectional", "split", "cumulative", "position", "running", "last 200", "last 400", "last 600"])


def parse_visible_tables(page: str, context: dict[str, str], captured_at: str) -> tuple[list[dict[str, str]], str]:
    visible_text, tables = public_visible_content(page)
    rows: list[dict[str, str]] = []
    notes: list[str] = []
    for table in tables:
        if len(table) < 2:
            continue
        headers = table[0]
        if not table_has_sectional_headers(headers):
            continue
        horse_idx = header_index(headers, ["horse", "runner", "name"])
        distance_idx = header_index(headers, ["sectionaldistance", "distance", "split", "marker"])
        split_idx = header_index(headers, ["splittime", "sectionaltime", "last200", "last400", "last600"])
        cumulative_idx = header_index(headers, ["cumulativetime", "cumulative", "elapsed"])
        position_idx = header_index(headers, ["positioninrunning", "position", "running", "pos"])
        notes.append(f"headers={'|'.join(headers)}")
        for record in table[1:]:
            def value(index: int | None) -> str:
                if index is None or index >= len(record):
                    return ""
                return clean(record[index])

            horse = value(horse_idx)
            row = {
                "race_date": context["race_date"],
                "track": context["track"],
                "race_no": context["race_no"],
                "horse": horse,
                "horse_key": canonical_horse(horse),
                "sectional_distance": value(distance_idx),
                "split_time": value(split_idx),
                "cumulative_time": value(cumulative_idx),
                "position_in_running": value(position_idx),
                "source_url": context["source_url"],
                "capture_status": "PUBLIC_HTML_SECTIONAL_ROW",
                "capture_note": "Extracted from visible public HTML table.",
                "captured_at": captured_at,
            }
            if horse or row["sectional_distance"] or row["split_time"] or row["cumulative_time"] or row["position_in_running"]:
                rows.append(row)

    if rows:
        return rows, "; ".join(notes[:5])
    if any(term in visible_text.lower() for term in SECTIONAL_TERMS):
        return [], "Visible page contains speed/sectional words but no extractable sectional table."
    return [], "No visible sectional/split table found in public HTML."


def page_title(page: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", page, flags=re.IGNORECASE | re.DOTALL)
    return clean(html.unescape(match.group(1))) if match else ""


def private_endpoint_visible(page: str) -> bool:
    lower = page.lower()
    return any(pattern in lower for pattern in PRIVATE_ENDPOINT_PATTERNS)


def main() -> int:
    captured_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    candidates = build_candidates()
    sectionals: list[dict[str, str]] = []
    raw_pages: list[dict[str, Any]] = []
    fetch_records: list[dict[str, str]] = []

    for index, candidate in enumerate(candidates, start=1):
        url = candidate["source_url"]
        html_text, fetch_status, http_status, headers = fetch_public_html(url)
        contains_private_marker = private_endpoint_visible(html_text)
        extracted_rows: list[dict[str, str]] = []
        parse_note = ""
        capture_status = fetch_status

        if fetch_status == "FETCHED" and http_status == 200 and html_text:
            extracted_rows, parse_note = parse_visible_tables(html_text, candidate, captured_at)
            sectionals.extend(extracted_rows)
            if extracted_rows:
                capture_status = "PUBLIC_HTML_SECTIONALS_EXTRACTED"
            else:
                capture_status = "SECTIONALS_NOT_VISIBLE_IN_PUBLIC_HTML"
            raw_pages.append(
                {
                    "race_date": candidate["race_date"],
                    "track": candidate["track"],
                    "race_no": candidate["race_no"],
                    "source_url": url,
                    "http_status": http_status,
                    "fetch_status": fetch_status,
                    "capture_status": capture_status,
                    "content_type": headers.get("content_type", ""),
                    "final_url": headers.get("final_url", url),
                    "title": page_title(html_text),
                    "content_length": len(html_text),
                    "private_endpoint_marker_present": contains_private_marker,
                    "raw_html_truncated": len(html_text) > RAW_HTML_MAX_CHARS,
                    "raw_html": html_text[:RAW_HTML_MAX_CHARS],
                }
            )
        else:
            parse_note = "Public HTML was not fetched with HTTP 200."

        fetch_records.append(
            {
                "url": url,
                "race_date": candidate["race_date"],
                "track": candidate["track"],
                "race_no": candidate["race_no"],
                "race_status": candidate.get("race_status", ""),
                "http_status": str(http_status),
                "fetch_status": fetch_status,
                "capture_status": capture_status,
                "rows_extracted": str(len(extracted_rows)),
                "private_endpoint_marker_present": "TRUE" if contains_private_marker else "FALSE",
                "note": parse_note,
            }
        )

        print(f"{index}/{len(candidates)} {fetch_status} {capture_status} rows={len(extracted_rows)} {url}")
        if index < len(candidates):
            time.sleep(SLEEP_SECONDS)

    status_counts = Counter(record["capture_status"] for record in fetch_records)
    pages_fetched = sum(1 for record in fetch_records if record["fetch_status"] == "FETCHED" and record["http_status"] == "200")
    pages_failed = len(fetch_records) - pages_fetched
    races_with_sectionals = len({(row["race_date"], row["track"], row["race_no"]) for row in sectionals})
    races_without_visible = status_counts.get("SECTIONALS_NOT_VISIBLE_IN_PUBLIC_HTML", 0)

    if sectionals:
        overall_status = "PUBLIC_SECTIONAL_CAPTURE_BUILT"
    elif pages_fetched and races_without_visible:
        overall_status = "SECTIONALS_NOT_VISIBLE_IN_PUBLIC_HTML"
    else:
        overall_status = "PUBLIC_CAPTURE_BLOCKED_OR_UNAVAILABLE"

    audit_rows = [
        {"metric": "urls_attempted", "value": str(len(fetch_records)), "notes": ""},
        {"metric": "pages_fetched", "value": str(pages_fetched), "notes": "HTTP 200 public HTML responses."},
        {"metric": "pages_failed", "value": str(pages_failed), "notes": ""},
        {"metric": "sectional_rows_extracted", "value": str(len(sectionals)), "notes": ""},
        {"metric": "races_with_sectionals", "value": str(races_with_sectionals), "notes": ""},
        {"metric": "races_without_visible_sectionals", "value": str(races_without_visible), "notes": ""},
        {"metric": "private_endpoint_used", "value": "FALSE", "notes": "Only www.racing.com public speed-data HTML URLs were requested."},
        {"metric": "api_key_extracted", "value": "FALSE", "notes": "No X-Api-Key/headerAPIKey extraction attempted."},
        {"metric": "graphql_endpoint_used", "value": "FALSE", "notes": "No graphql.rmdprod.racing.com requests made."},
        {"metric": "user_agent", "value": USER_AGENT, "notes": ""},
        {"metric": "sleep_seconds", "value": str(SLEEP_SECONDS), "notes": "Polite delay between public HTML requests."},
        {"metric": "status", "value": overall_status, "notes": "; ".join(f"{key}:{value}" for key, value in sorted(status_counts.items()))},
    ]
    for record in fetch_records:
        audit_rows.append(
            {
                "metric": "FETCH",
                "value": record["url"],
                "notes": f"race={record['race_date']} {record['track']} R{record['race_no']}; race_status={record['race_status']}; http_status={record['http_status']}; fetch_status={record['fetch_status']}; capture_status={record['capture_status']}; rows={record['rows_extracted']}; private_marker={record['private_endpoint_marker_present']}; {record['note']}",
            }
        )

    write_csv(OUT, sectionals, OUTPUT_FIELDS)
    write_csv(AUDIT, audit_rows, ["metric", "value", "notes"])
    RAW_PAGES.write_text(json.dumps(raw_pages, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"status: {overall_status}")
    print(f"urls attempted: {len(fetch_records)}")
    print(f"pages fetched: {pages_fetched}")
    print(f"sectional rows extracted: {len(sectionals)}")
    print(f"output: {OUT}")
    print(f"audit: {AUDIT}")
    print(f"raw pages: {RAW_PAGES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
