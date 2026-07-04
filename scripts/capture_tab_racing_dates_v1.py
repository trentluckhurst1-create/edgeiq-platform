from pathlib import Path
from playwright.sync_api import sync_playwright
import json

OUT = Path("public/data/tab_racing_dates_full.json")
URL_PART = "tab-info-service/racing/dates"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    print("[capture_dates] waiting for racing dates response")

    with page.expect_response(lambda r: URL_PART in r.url and r.status == 200, timeout=60000) as resp_info:
        page.goto(
            "https://www.tab.com.au/racing/meetings/today/R",
            wait_until="domcontentloaded",
            timeout=30000
        )

    resp = resp_info.value
    body = resp.text()
    OUT.write_text(body, encoding="utf-8")

    print("[capture_dates] found", resp.url)
    print("[capture_dates] bytes", len(body))
    print(body[:1500])

    browser.close()
