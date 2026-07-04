from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

OUT = Path("public/data/tab_meetings_today_full.json")
URL_PART = "tab-info-service/racing/dates/2026-06-06/meetings"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    print("[capture_meetings_page] waiting for meetings response from TAB page")

    try:
        with page.expect_response(lambda r: URL_PART in r.url and r.status == 200, timeout=60000) as resp_info:
            page.goto(
                "https://www.tab.com.au/racing/meetings/today/R",
                wait_until="domcontentloaded",
                timeout=30000
            )

        resp = resp_info.value
        body = resp.text()
        OUT.write_text(body, encoding="utf-8")

        print("[capture_meetings_page] found", resp.url)
        print("[capture_meetings_page] bytes", len(body))
        print(body[:2000])

    except PlaywrightTimeoutError:
        print("[capture_meetings_page] TIMEOUT: meetings response not captured")

    browser.close()
