from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

OUT = Path("public/data/tab_next_to_go_full.json")
URL_PART = "tab-info-service/racing/next-to-go/races"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    print("[capture_body] waiting for next-to-go response")

    try:
        with page.expect_response(lambda r: URL_PART in r.url and r.status == 200, timeout=60000) as resp_info:
            page.goto(
                "https://www.tab.com.au/racing/meetings/today/R",
                wait_until="domcontentloaded",
                timeout=30000
            )

        resp = resp_info.value
        print("[capture_body] found", resp.url)

        body = resp.text()
        OUT.write_text(body, encoding="utf-8")

        print("[capture_body] saved", OUT)
        print("[capture_body] bytes", len(body))
        print(body[:1000])

    except PlaywrightTimeoutError:
        print("[capture_body] TIMEOUT: no matching next-to-go body captured")

    browser.close()
