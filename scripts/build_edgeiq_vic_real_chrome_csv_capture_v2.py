from pathlib import Path
import pandas as pd
import re
import time
from datetime import date, timedelta
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

ROOT = Path.cwd()
PUBLIC = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"

DOWNLOAD_DIR = ROOT / "outputs" / "sectionals" / "raw" / "VIC" / "racingcom_real_chrome_csv_downloads"
PAGE_DIR = ROOT / "outputs" / "sectionals" / "raw" / "VIC" / "racingcom_real_chrome_completed_pages"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
PAGE_DIR.mkdir(parents=True, exist_ok=True)

OUT = PUBLIC / "edgeiq_vic_real_chrome_csv_capture_v2.csv"
DIAG = PUBLIC / "edgeiq_vic_real_chrome_csv_capture_diagnostics_v2.csv"
NETWORK = PUBLIC / "edgeiq_vic_real_chrome_network_log_v2.csv"

CAL = PUBLIC / "edgeiq_racingcom_calendar_discovery_v1.csv"

TODAY = date.today()
MIN_DATE = TODAY - timedelta(days=60)
MAX_DATE = TODAY - timedelta(days=2)

def clean_slug(x):
    s = str(x or "").lower().strip()
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")

def safe_file_name(url):
    p = urlparse(url).path.strip("/")
    p = p.replace("/", "_")
    return re.sub(r"[^A-Za-z0-9_\-]+", "_", p)[:180]

def parse_date_from_url(url):
    m = re.search(r"/form/(\d{4}-\d{2}-\d{2})/", str(url))
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(1))
    except Exception:
        return None

def is_completed_vic_url(url):
    d = parse_date_from_url(url)
    if d is None:
        return False
    if d < MIN_DATE or d > MAX_DATE:
        return False
    return "racing.com/form/" in url and "/speed-data" in url

def find_col(df, options):
    cols = list(df.columns)
    low = {str(c).lower(): c for c in cols}
    for opt in options:
        for lc, c in low.items():
            if opt in lc:
                return c
    return None

def load_completed_urls():
    urls = []

    for path in (ROOT / "outputs" / "sectionals" / "raw" / "VIC" / "racingcom_speed_data").glob("*.html"):
        m = re.match(r"(\d{4}-\d{2}-\d{2})_(.+)_R(\d+)\.html", path.name)
        if m:
            d, track, rn = m.groups()
            u = f"https://www.racing.com/form/{d}/{track}/race/{int(rn)}/speed-data"
            if is_completed_vic_url(u):
                urls.append(u)

    if CAL.exists():
        df = pd.read_csv(CAL, low_memory=False)

        for c in df.columns:
            if "url" in str(c).lower():
                for u in df[c].dropna().astype(str):
                    if is_completed_vic_url(u):
                        urls.append(u)

        date_col = find_col(df, ["race_date", "date"])
        track_col = find_col(df, ["track", "venue"])
        race_col = find_col(df, ["race_no", "race_number", "race"])

        if date_col and track_col and race_col:
            for _, r in df.iterrows():
                d = str(r.get(date_col, ""))[:10]
                try:
                    dd = date.fromisoformat(d)
                except Exception:
                    continue
                if dd < MIN_DATE or dd > MAX_DATE:
                    continue

                state = str(r.get("state", r.get("venue_state", "VIC"))).upper()
                if state and state != "VIC":
                    continue

                track = clean_slug(r.get(track_col, ""))
                try:
                    rn = int(float(r.get(race_col, 0)))
                except Exception:
                    rn = 0

                if track and rn > 0:
                    urls.append(f"https://www.racing.com/form/{d}/{track}/race/{rn}/speed-data")

    priority = [
        "https://www.racing.com/form/2026-05-01/ladbrokes-geelong/race/1/speed-data",
        "https://www.racing.com/form/2026-05-01/ladbrokes-geelong/race/2/speed-data",
        "https://www.racing.com/form/2026-05-01/ladbrokes-geelong/race/3/speed-data",
        "https://www.racing.com/form/2026-05-01/ladbrokes-geelong/race/4/speed-data",
        "https://www.racing.com/form/2026-05-01/ladbrokes-geelong/race/5/speed-data",
        "https://www.racing.com/form/2026-05-01/ladbrokes-geelong/race/6/speed-data",
        "https://www.racing.com/form/2026-05-01/ladbrokes-geelong/race/7/speed-data",
        "https://www.racing.com/form/2026-05-01/ladbrokes-geelong/race/8/speed-data",
        "https://www.racing.com/form/2026-05-13/bendigo/race/1/speed-data",
        "https://www.racing.com/form/2026-05-12/southside-pakenham/race/1/speed-data",
        "https://www.racing.com/form/2026-05-11/echuca/race/1/speed-data",
        "https://www.racing.com/form/2026-05-10/mornington/race/1/speed-data",
        "https://www.racing.com/form/2026-05-09/caulfield/race/1/speed-data",
        "https://www.racing.com/form/2026-05-08/flemington/race/1/speed-data",
    ]

    urls = priority + urls

    seen = set()
    final = []
    for u in urls:
        if is_completed_vic_url(u) and u not in seen:
            seen.add(u)
            final.append(u)

    return final[:40]

def parse_csv(path):
    try:
        df = pd.read_csv(path, low_memory=False)
        cols = [str(c).lower() for c in df.columns]
        has_200 = any("200" in c for c in cols)
        has_400 = any("400" in c for c in cols)
        has_600 = any("600" in c for c in cols)
        return len(df), has_200, has_400, has_600
    except Exception:
        return 0, False, False, False

urls = load_completed_urls()

rows = []
network_rows = []

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    context = browser.contexts[0] if browser.contexts else browser.new_context(accept_downloads=True)
    page = context.pages[0] if context.pages else context.new_page()

    try:
        cdp = context.new_cdp_session(page)
        cdp.send("Browser.setDownloadBehavior", {"behavior": "allow", "downloadPath": str(DOWNLOAD_DIR)})
    except Exception:
        pass

    def on_response(resp):
        u = resp.url
        lu = u.lower()
        if any(x in lu for x in ["csv", "download", "sectional", "speed-data", "getrace", "raceform"]):
            network_rows.append({
                "url": u,
                "status": resp.status,
                "content_type": resp.headers.get("content-type", ""),
                "content_disposition": resp.headers.get("content-disposition", ""),
            })

    page.on("response", on_response)

    for idx, url in enumerate(urls, start=1):
        before = {f.name for f in DOWNLOAD_DIR.glob("*")}
        status = "UNKNOWN"
        csv_visible = False
        download_success = False
        parsed_rows = 0
        has_200 = False
        has_400 = False
        has_600 = False
        saved_file = ""

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(12000)

            for _ in range(10):
                page.mouse.wheel(0, 1800)
                page.wait_for_timeout(700)

            html = page.content()
            (PAGE_DIR / f"{idx:03d}_{safe_file_name(url)}.html").write_text(html, encoding="utf-8", errors="ignore")

            lower = html.lower()
            csv_visible = "download race sectional data" in lower or ">csv<" in lower or "csv" in lower and "sectional" in lower

            selectors = [
                "a:has-text('CSV')",
                "button:has-text('CSV')",
                "text=CSV",
                "[href*='csv']",
                "[download]",
            ]

            clicked = False
            for sel in selectors:
                try:
                    loc = page.locator(sel)
                    if loc.count() > 0:
                        csv_visible = True
                        with page.expect_download(timeout=25000) as dl:
                            loc.last.click(force=True)
                        download = dl.value
                        suggested = download.suggested_filename or f"{idx:03d}_{safe_file_name(url)}.csv"
                        target = DOWNLOAD_DIR / suggested
                        download.save_as(target)
                        saved_file = str(target)
                        download_success = True
                        clicked = True
                        break
                except Exception:
                    pass

            if not clicked:
                try:
                    page.evaluate("""
                    () => {
                      const els = Array.from(document.querySelectorAll('a, button'));
                      const csv = els.find(e => (e.innerText || '').trim().toUpperCase() === 'CSV');
                      if (csv) csv.click();
                    }
                    """)
                    page.wait_for_timeout(8000)
                except Exception:
                    pass

            after_files = [f for f in DOWNLOAD_DIR.glob("*") if f.name not in before and not f.name.endswith(".crdownload")]
            if not download_success and after_files:
                latest = sorted(after_files, key=lambda x: x.stat().st_mtime, reverse=True)[0]
                saved_file = str(latest)
                download_success = True

            if download_success and saved_file:
                parsed_rows, has_200, has_400, has_600 = parse_csv(Path(saved_file))
                status = "DOWNLOADED_PARSED" if parsed_rows > 0 else "DOWNLOADED_PARSE_FAILED"
            else:
                status = "CSV_VISIBLE_NO_DOWNLOAD" if csv_visible else "CSV_CONTROL_NOT_FOUND"

        except Exception as e:
            status = "FAILED_" + repr(e)[:160]

        rows.append({
            "page_no": idx,
            "speed_data_url": url,
            "race_date": str(parse_date_from_url(url)),
            "status": status,
            "csv_control_visible": csv_visible,
            "download_success": download_success,
            "parsed_rows": parsed_rows,
            "has_last200_or_200": has_200,
            "has_last400_or_400": has_400,
            "has_last600_or_600": has_600,
            "saved_file": saved_file,
        })

        pd.DataFrame(rows).to_csv(OUT, index=False)
        pd.DataFrame(network_rows).to_csv(NETWORK, index=False)
        print(pd.DataFrame([rows[-1]]).to_string(index=False))

    browser.close()

result = pd.DataFrame(rows)
network = pd.DataFrame(network_rows)

diag = pd.DataFrame([{
    "today": str(TODAY),
    "min_date": str(MIN_DATE),
    "max_date": str(MAX_DATE),
    "urls_selected": len(urls),
    "pages_attempted": len(result),
    "future_urls_attempted": int((pd.to_datetime(result["race_date"], errors="coerce").dt.date > MAX_DATE).sum()) if len(result) else 0,
    "csv_control_visible": int(result["csv_control_visible"].sum()) if len(result) else 0,
    "downloads_successful": int(result["download_success"].sum()) if len(result) else 0,
    "csvs_parsed": int(result["parsed_rows"].fillna(0).gt(0).sum()) if len(result) else 0,
    "rows_parsed": int(result["parsed_rows"].fillna(0).sum()) if len(result) else 0,
    "network_rows": len(network),
}])

result.to_csv(OUT, index=False)
network.to_csv(NETWORK, index=False)
diag.to_csv(DIAG, index=False)

print("=" * 100)
print("EDGEIQ VIC REAL CHROME COMPLETED-RACE CSV CAPTURE V2 COMPLETE")
print("=" * 100)
print(diag.to_string(index=False))
print("SAVED:", OUT)
print("SAVED:", DIAG)
print("SAVED:", NETWORK)
