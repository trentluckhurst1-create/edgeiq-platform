from pathlib import Path
import pandas as pd
import re
import time
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

ROOT = Path.cwd()
PUBLIC = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"

DOWNLOAD_DIR = ROOT / "outputs" / "sectionals" / "raw" / "VIC" / "racingcom_browser_csv_downloads"
PAGE_DIR = ROOT / "outputs" / "sectionals" / "raw" / "VIC" / "racingcom_real_chrome_pages"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
PAGE_DIR.mkdir(parents=True, exist_ok=True)

OUT = PUBLIC / "edgeiq_vic_real_chrome_csv_capture_v1.csv"
DIAG = PUBLIC / "edgeiq_vic_real_chrome_csv_capture_diagnostics_v1.csv"
NETWORK = PUBLIC / "edgeiq_vic_real_chrome_network_log_v1.csv"

CAL = PUBLIC / "edgeiq_racingcom_calendar_discovery_v1.csv"

def clean_slug(x):
    s = str(x or "").lower().strip()
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")

def find_col(df, terms):
    for c in df.columns:
        lc = str(c).lower()
        if all(t in lc for t in terms):
            return c
    return None

def load_urls():
    urls = []

    if CAL.exists():
        df = pd.read_csv(CAL, low_memory=False)

        url_cols = [c for c in df.columns if "url" in str(c).lower() and "speed" in str(c).lower()]
        for c in url_cols:
            for u in df[c].dropna().astype(str):
                if "racing.com/form/" in u and "/speed-data" in u:
                    urls.append(u)

        date_col = find_col(df, ["date"])
        track_col = find_col(df, ["track"])
        race_col = find_col(df, ["race"])

        if date_col and track_col and race_col:
            for _, r in df.iterrows():
                d = str(r.get(date_col, ""))[:10]
                t = clean_slug(r.get(track_col, ""))
                try:
                    rn = int(float(r.get(race_col, 0)))
                except Exception:
                    rn = 0
                if re.match(r"\d{4}-\d{2}-\d{2}", d) and t and rn > 0:
                    urls.append(f"https://www.racing.com/form/{d}/{t}/race/{rn}/speed-data")

    urls.append("https://www.racing.com/form/2026-05-01/southside-pakenham/race/1/speed-data")
    urls.append("https://www.racing.com/form/2026-05-01/ladbrokes-geelong/race/1/speed-data")

    seen = set()
    final = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            final.append(u)
    return final[:30]

def safe_file_name(url):
    p = urlparse(url).path.strip("/")
    p = p.replace("/", "_")
    p = re.sub(r"[^A-Za-z0-9_\-]+", "_", p)
    return p[:180]

def parse_csv(path):
    try:
        df = pd.read_csv(path, low_memory=False)
        cols = [str(c).lower() for c in df.columns]
        has_200 = any("200" in c for c in cols)
        has_400 = any("400" in c for c in cols)
        has_600 = any("600" in c for c in cols)
        return len(df), has_200, has_400, has_600, list(df.columns)
    except Exception:
        return 0, False, False, False, []

urls = load_urls()
rows = []
network_rows = []

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    context = browser.contexts[0] if browser.contexts else browser.new_context()
    page = context.pages[0] if context.pages else context.new_page()

    try:
        cdp = context.new_cdp_session(page)
        cdp.send("Browser.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": str(DOWNLOAD_DIR)
        })
    except Exception:
        pass

    def on_response(resp):
        u = resp.url
        lu = u.lower()
        if any(x in lu for x in ["csv", "download", "section", "speed", "race"]):
            try:
                network_rows.append({
                    "url": u,
                    "status": resp.status,
                    "content_type": resp.headers.get("content-type", ""),
                    "content_disposition": resp.headers.get("content-disposition", ""),
                })
            except Exception:
                pass

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
            page.wait_for_timeout(8000)

            for _ in range(6):
                page.mouse.wheel(0, 2500)
                page.wait_for_timeout(1000)

            html = page.content()
            page_file = PAGE_DIR / f"{idx:03d}_{safe_file_name(url)}.html"
            page_file.write_text(html, encoding="utf-8", errors="ignore")

            lower = html.lower()
            csv_visible = ("download race sectional data" in lower and "csv" in lower) or ">csv<" in lower or " csv" in lower

            clicked = False

            selectors = [
                "a:has-text('CSV')",
                "button:has-text('CSV')",
                "text=CSV",
            ]

            for sel in selectors:
                try:
                    loc = page.locator(sel)
                    if loc.count() > 0:
                        csv_visible = True
                        with page.expect_download(timeout=20000) as dl:
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
                    clicked = page.evaluate("""
                    () => {
                        const els = Array.from(document.querySelectorAll('a,button,span,div'));
                        const hit = els.reverse().find(e => (e.innerText || '').trim().toLowerCase() === 'csv');
                        if (hit) {
                            hit.click();
                            return true;
                        }
                        return false;
                    }
                    """)
                    if clicked:
                        csv_visible = True
                        page.wait_for_timeout(8000)
                except Exception:
                    clicked = False

            after_files = [f for f in DOWNLOAD_DIR.glob("*") if f.name not in before and not f.name.endswith(".crdownload")]
            if not download_success and after_files:
                latest = sorted(after_files, key=lambda x: x.stat().st_mtime, reverse=True)[0]
                saved_file = str(latest)
                download_success = True

            if download_success and saved_file:
                parsed_rows, has_200, has_400, has_600, cols = parse_csv(Path(saved_file))
                status = "DOWNLOADED_PARSED" if parsed_rows > 0 else "DOWNLOADED_PARSE_FAILED"
            else:
                status = "CSV_VISIBLE_NO_DOWNLOAD" if csv_visible else "CSV_CONTROL_NOT_FOUND"

        except Exception as e:
            status = "FAILED_" + repr(e)[:180]

        rows.append({
            "page_no": idx,
            "speed_data_url": url,
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
    "pages_attempted": len(result),
    "csv_control_visible": int(result["csv_control_visible"].sum()) if len(result) else 0,
    "downloads_successful": int(result["download_success"].sum()) if len(result) else 0,
    "csvs_parsed": int(result["parsed_rows"].fillna(0).gt(0).sum()) if len(result) else 0,
    "rows_parsed": int(result["parsed_rows"].fillna(0).sum()) if len(result) else 0,
    "network_rows": len(network),
    "network_csv_or_download_rows": int(network["url"].astype(str).str.lower().str.contains("csv|download", regex=True).sum()) if len(network) else 0,
}])

result.to_csv(OUT, index=False)
network.to_csv(NETWORK, index=False)
diag.to_csv(DIAG, index=False)

print("=" * 100)
print("EDGEIQ VIC REAL CHROME CSV CAPTURE COMPLETE")
print("=" * 100)
print(diag.to_string(index=False))
print("SAVED:", OUT)
print("SAVED:", DIAG)
print("SAVED:", NETWORK)
