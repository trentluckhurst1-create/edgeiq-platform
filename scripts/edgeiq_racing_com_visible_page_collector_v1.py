from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw" / "racing-com-visible-v1"
OP_ROOT = ROOT / "data" / "operational" / "racing-com-visible-v1"
DOC_ROOT = ROOT / "docs" / "racing-com-public-data-v1" / "visible-page-ingestion"
UA = "EDGEiQ-visible-sectionals-collector-v1 (visible public page text only)"
APPV2_MEETS = "https://www.racing.com/services/appv2/GetMeetsByMonth/{year}/{month}"
COLLECTOR_VERSION = "EDGEIQ_RACING_COM_VISIBLE_PAGE_COLLECTOR_V1"
SELECTOR_VERSION = "VISIBLE_DOM_TEXT_TABLES_V1"
RACE_LIST_CSV = ROOT / "public" / "data" / "edgeiq_vic_three_day_race_list_v1.csv"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha_text(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()


def safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return value.strip("_") or "UNKNOWN"


def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or ["empty"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def resolve_date(value: str) -> datetime:
    if not value or value.upper() == "TODAY":
        return datetime.now()
    return datetime.fromisoformat(value[:10])


def http_json(url: str) -> object:
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8", "ignore"))



def read_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    csv.field_size_limit(min(sys.maxsize, 2147483647))
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def race_list_queue(target_date: datetime, state: str) -> list[dict]:
    target = target_date.date().isoformat()
    rows = []
    for row in read_csv_rows(RACE_LIST_CSV):
        if str(row.get("race_date", ""))[:10] != target:
            continue
        race_no = str(row.get("race_no", "")).strip()
        form_url = str(row.get("form_url", "")).strip().rstrip("/")
        if not race_no or not form_url:
            continue
        race_url = f"{form_url}/race/{race_no}/speed-data"
        rows.append({
            "meeting_date": target,
            "venue": row.get("normalised_track") or row.get("track") or "",
            "state": state,
            "meeting_url": form_url,
            "meeting_code": row.get("meet_code", ""),
            "race_number": race_no,
            "race_url": race_url,
            "queue_state": "QUEUED_FROM_PUBLIC_RACE_LIST",
        })
    return rows

def discover_meetings(target_date: datetime, state: str) -> list[dict]:
    data = http_json(APPV2_MEETS.format(year=target_date.year, month=target_date.month))
    rows: list[dict] = []
    target = target_date.date().isoformat()
    for month in data.get("Months") or []:
        for entry in month.get("CalendarEntries") or []:
            date = str(entry.get("Date") or "")[:10]
            if date != target:
                continue
            if state and str(entry.get("State") or "").upper() != state.upper():
                continue
            if entry.get("IsJumpout") or entry.get("IsTrial") or entry.get("IsAbandoned"):
                continue
            url_segment = entry.get("UrlSegment") or ""
            if not url_segment:
                continue
            rows.append({
                "meeting_date": date,
                "venue": entry.get("Venue") or entry.get("Track") or "",
                "track": entry.get("Track") or entry.get("Venue") or "",
                "state": entry.get("State") or "",
                "meeting_code": entry.get("MeetCode") or "",
                "url_segment": url_segment,
                "meeting_url": f"https://www.racing.com/form/{url_segment}#/racelist",
                "meet_status": entry.get("MeetStatus") or entry.get("FullStatus") or "",
                "is_results": "YES" if entry.get("IsResults") else "NO",
            })
    return rows


def base_queue_from_meetings(meetings: list[dict]) -> list[dict]:
    rows = []
    for meeting in meetings:
        rows.append({**meeting, "race_number": "", "race_url": "", "queue_state": "DISCOVERED"})
    return rows


def install_hint() -> str:
    return "Install if needed: python -m pip install playwright; python -m playwright install chromium"


def visible_table_rows(table: dict, url: str, view: str, race_meta: dict) -> list[dict]:
    rows = []
    headers = table.get("headers") or []
    for index, cells in enumerate(table.get("rows") or []):
        row = {"source_url": url, "view": view, "table_index": table.get("table_index", ""), "row_index": index}
        for i, cell in enumerate(cells):
            name = headers[i] if i < len(headers) and headers[i] else f"cell_{i}"
            row[name] = cell
        row.update(race_meta)
        rows.append(row)
    return rows


def sanitise_html(html: str) -> str:
    html = re.sub(r"(?is)<script\b[^>]*>.*?</script>", "<script>[REMOVED]</script>", html)
    html = re.sub(r"(?is)<style\b[^>]*>.*?</style>", "<style>[REMOVED]</style>", html)
    html = re.sub(r"(?i)(api[-_ ]?key|endpointkey|authorization|token|cookie)\s*[:=]\s*['\"]?[^'\"\s<>]+", r"\1=[REDACTED]", html)
    return html[:500000]


def extract_race_links(page, meeting_url: str) -> list[str]:
    page.goto(meeting_url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(3500)
    hrefs = page.evaluate("""() => Array.from(document.querySelectorAll('a[href]')).map(a => a.href).filter(Boolean)""")
    links = []
    for href in hrefs:
        if "/form/" not in href or "/race/" not in href:
            continue
        href = href.split("#")[0]
        if not href.endswith("/speed-data"):
            href = href.rstrip("/") + "/speed-data"
        if href not in links:
            links.append(href)
    return links


def click_visible_labels(page) -> list[str]:
    clicked = []
    candidates = ["Speed Data", "Overview", "Sectionals", "Splits", "Split Times", "Sectional Times"]
    for label in candidates:
        try:
            locator = page.get_by_text(label, exact=False).first
            if locator.count() > 0 and locator.is_visible(timeout=1000):
                locator.click(timeout=2000)
                page.wait_for_timeout(1200)
                clicked.append(label)
        except Exception:
            continue
    return clicked


def collect_race(page, race_url: str, output_root: Path, timeout_seconds: int, settle_seconds: float, dry_run: bool = False) -> dict:
    match = re.search(r"/form/(\d{4}-\d{2}-\d{2})/([^/#?]+)/race/(\d+)", race_url)
    race_date, venue_slug, race_number = (match.group(1), match.group(2), match.group(3)) if match else ("UNKNOWN_DATE", "UNKNOWN_VENUE", "UNKNOWN_RACE")
    race_dir = output_root / race_date / safe_name(venue_slug) / f"R{race_number}"
    race_dir.mkdir(parents=True, exist_ok=True)
    log = {"source_url": race_url, "retrieved_at": now_utc(), "collector_version": COLLECTOR_VERSION, "selector_version": SELECTOR_VERSION, "events": []}
    if dry_run:
        log["status"] = "DRY_RUN"
        write_json(race_dir / "collector_log.json", log)
        return {"race_url": race_url, "queue_state": "PAGE_READY", "row_count": 0, "section_count": 0, "raw_dir": str(race_dir.relative_to(ROOT))}
    try:
        page.goto(race_url, wait_until="domcontentloaded", timeout=timeout_seconds * 1000)
        page.wait_for_timeout(int(settle_seconds * 1000))
        page.wait_for_load_state("networkidle", timeout=timeout_seconds * 1000)
    except Exception as exc:
        log["status"] = "FAILED_TRANSIENT"
        log["error"] = type(exc).__name__ + ": " + str(exc)
        write_json(race_dir / "collector_log.json", log)
        return {"race_url": race_url, "queue_state": "FAILED_TRANSIENT", "row_count": 0, "section_count": 0, "raw_dir": str(race_dir.relative_to(ROOT)), "error": log["error"]}
    clicked = click_visible_labels(page)
    try:
        page.wait_for_timeout(int(settle_seconds * 1000))
    except Exception:
        pass
    extracted = page.evaluate("""() => {
      const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
      const tables = Array.from(document.querySelectorAll('table')).filter(visible).map((table, table_index) => {
        const headers = Array.from(table.querySelectorAll('thead th')).map(x => (x.innerText || '').trim()).filter(Boolean);
        const rows = Array.from(table.querySelectorAll('tbody tr')).filter(visible).map(tr => Array.from(tr.querySelectorAll('th,td')).map(td => (td.innerText || '').trim()));
        return {table_index, headers, rows};
      });
      const textBlocks = Array.from(document.querySelectorAll('button,[role=tab],h1,h2,h3,h4,[aria-label]')).filter(visible).map(el => (el.innerText || el.getAttribute('aria-label') || '').trim()).filter(Boolean);
      return {title: document.title, rendered_text: document.body ? document.body.innerText : '', tables, textBlocks, html: document.documentElement ? document.documentElement.outerHTML : ''};
    }""")
    text = extracted.get("rendered_text") or ""
    tables = extracted.get("tables") or []
    race_meta = {"meeting_date": race_date, "venue": venue_slug, "race_number": race_number, "page_title": extracted.get("title", "")}
    rows = []
    for table in tables:
        rows.extend(visible_table_rows(table, race_url, "VISIBLE_RENDERED_PAGE", race_meta))
    section_count = len(re.findall(r"\b\d{3,4}m\s*[\u2013\u2014-]\s*(?:\d{3,4}m|Finish)\b", text, flags=re.I))
    status = "SECTIONALS_COLLECTED" if rows and section_count else ("NO_SECTIONALS" if "section" not in text.lower() and "split" not in text.lower() else "PAGE_SCHEMA_CHANGED")
    screenshot_path = race_dir / "page_screenshot.png"
    try:
        page.screenshot(path=str(screenshot_path), full_page=True, timeout=15000)
    except Exception as exc:
        log["screenshot_error"] = type(exc).__name__
    write_json(race_dir / "page_metadata.json", {"source_url": race_url, "retrieved_at": now_utc(), "page_title": extracted.get("title", ""), "meeting_identity": venue_slug, "race_identity": f"R{race_number}", "collector_version": COLLECTOR_VERSION, "selector_version": SELECTOR_VERSION, "visible_table_hash": sha_text(json.dumps(tables, ensure_ascii=False)), "screenshot_hash": sha_text(screenshot_path.read_bytes().hex()) if screenshot_path.exists() else "", "row_count": len(rows), "section_count": section_count, "clicked_labels": clicked, "status": status})
    write_json(race_dir / "visible_table.json", {"source_url": race_url, "tables": tables, "textBlocks": extracted.get("textBlocks") or []})
    write_csv(race_dir / "visible_table.csv", rows)
    write_text(race_dir / "rendered_text.txt", text[:500000])
    write_text(race_dir / "source_html_sanitised.html", sanitise_html(extracted.get("html") or ""))
    log["status"] = status
    log["clicked_labels"] = clicked
    write_json(race_dir / "collector_log.json", log)
    return {"race_url": race_url, "queue_state": status, "row_count": len(rows), "section_count": section_count, "raw_dir": str(race_dir.relative_to(ROOT))}


def collect(args: argparse.Namespace) -> dict:
    OP_ROOT.mkdir(parents=True, exist_ok=True)
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    DOC_ROOT.mkdir(parents=True, exist_ok=True)
    target_date = resolve_date(args.date)
    meetings = []
    race_urls = []
    if args.race_url:
        race_urls = [args.race_url]
    elif args.meeting_url:
        meetings = [{"meeting_date": target_date.date().isoformat(), "venue": args.meeting_url, "state": args.state, "meeting_url": args.meeting_url, "meeting_code": args.meeting_code}]
    else:
        meetings = discover_meetings(target_date, args.state)
    race_list_fallback = [] if args.race_url else race_list_queue(target_date, args.state)
    if not race_urls and race_list_fallback:
        race_urls = [row["race_url"] for row in race_list_fallback if row.get("race_url")]
    queue = race_list_fallback if race_list_fallback else (base_queue_from_meetings(meetings) if meetings else [])
    write_csv(OP_ROOT / "race_queue.csv", queue)
    write_json(OP_ROOT / "race_queue.json", queue)
    if args.dry_run:
        summary = {"status": "DRY_RUN", "meetings_discovered": len(meetings), "races_discovered": len(race_urls), "races_opened": 0, "results": [], "install_hint": install_hint()}
        write_json(OP_ROOT / "collector_summary.json", summary)
        print(json.dumps(summary, indent=2))
        return summary
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        summary = {"status": "PLAYWRIGHT_MISSING", "error": str(exc), "install_hint": install_hint(), "meetings_discovered": len(meetings), "races_discovered": 0}
        write_json(OP_ROOT / "collector_summary.json", summary)
        print(json.dumps(summary, indent=2))
        return summary
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=bool(args.headless and not args.headed))
        context = browser.new_context(user_agent=UA, viewport={"width": 1440, "height": 1200})
        page = context.new_page()
        if not race_urls:
            for meeting in meetings:
                try:
                    links = extract_race_links(page, meeting["meeting_url"])
                except Exception as exc:
                    results.append({**meeting, "queue_state": "FAILED_TRANSIENT", "error": type(exc).__name__ + ": " + str(exc)})
                    continue
                for link in links:
                    if link not in race_urls:
                        race_urls.append(link)
        if args.max_races and args.max_races > 0:
            race_urls = race_urls[: args.max_races]
        for race_url in race_urls:
            result = collect_race(page, race_url, RAW_ROOT, args.timeout_seconds, args.settle_seconds, dry_run=False)
            results.append(result)
        context.close()
        browser.close()
    final_queue = []
    for result in results:
        match = re.search(r"/form/(\d{4}-\d{2}-\d{2})/([^/#?]+)/race/(\d+)", result.get("race_url", ""))
        final_queue.append({"meeting_date": match.group(1) if match else "", "venue": match.group(2) if match else "", "race_number": match.group(3) if match else "", "race_url": result.get("race_url", ""), "queue_state": result.get("queue_state", ""), "row_count": result.get("row_count", 0), "section_count": result.get("section_count", 0), "raw_dir": result.get("raw_dir", ""), "error": result.get("error", "")})
    write_csv(OP_ROOT / "race_queue.csv", final_queue)
    write_json(OP_ROOT / "race_queue.json", final_queue)
    summary = {"status": "PASS" if final_queue else "NO_ELIGIBLE_RACES", "meetings_discovered": len(meetings), "races_discovered": len(race_urls), "races_opened": len(final_queue), "races_with_visible_sectionals": sum(1 for r in final_queue if r.get("queue_state") == "SECTIONALS_COLLECTED"), "races_without_sectionals": sum(1 for r in final_queue if r.get("queue_state") == "NO_SECTIONALS"), "races_failed": sum(1 for r in final_queue if str(r.get("queue_state", "")).startswith("FAILED") or r.get("queue_state") in {"PAGE_SCHEMA_CHANGED", "ACCESS_BLOCKED"}), "results": results}
    write_json(OP_ROOT / "collector_summary.json", summary)
    print(json.dumps(summary, indent=2))
    return summary


def main() -> int:
    global RAW_ROOT
    parser = argparse.ArgumentParser()
    parser.add_argument("--meeting-url", default="")
    parser.add_argument("--race-url", default="")
    parser.add_argument("--meeting-code", default="")
    parser.add_argument("--race-number", default="")
    parser.add_argument("--date", default="TODAY")
    parser.add_argument("--state", default="VIC")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--output-root", default=str(RAW_ROOT))
    parser.add_argument("--timeout-seconds", type=int, default=45)
    parser.add_argument("--settle-seconds", type=float, default=4.0)
    parser.add_argument("--max-races", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.output_root:
        RAW_ROOT = Path(args.output_root)
    summary = collect(args)
    return 0 if summary.get("status") in {"PASS", "DRY_RUN", "NO_ELIGIBLE_RACES"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
