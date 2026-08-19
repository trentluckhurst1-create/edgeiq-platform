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

    resp = page.goto(url, wait_until="domcontentloaded", timeout=60000)

    print("[capture_meetings] status", resp.status if resp else "NO_RESPONSE")

    body = page.locator("body").inner_text(timeout=10000)
    OUT.write_text(body, encoding="utf-8")

    print("[capture_meetings] bytes", len(body))
    print(body[:2000])

    browser.close()
