from pathlib import Path
from playwright.sync_api import sync_playwright
import json

ROOT = Path(__file__).resolve().parents[1]
DATES = ROOT / "public" / "data" / "tab_racing_dates_full.json"
OUT = ROOT / "public" / "data" / "tab_meetings_today_full.json"

data = json.loads(DATES.read_text(encoding="utf-8"))
url = data["dates"][0]["_links"]["meetings"]

print("[capture_meetings] target", url)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    with page.expect_response(lambda r: url in r.url and r.status == 200, timeout=60000) as resp_info:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)

    resp = resp_info.value
    body = resp.text()
    OUT.write_text(body, encoding="utf-8")

    print("[capture_meetings] bytes", len(body))
    print(body[:2000])

    browser.close()
