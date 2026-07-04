from playwright.sync_api import sync_playwright
import json
from pathlib import Path

out = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    page = browser.new_page()

    def resp(r):
        u = r.url.lower()

        if "api.beta.tab.com.au" in u:
            out.append({
                "status": r.status,
                "url": r.url
            })
            print(r.status, r.url)

    page.on("response", resp)

    page.goto(
        "https://www.tab.com.au/racing/meetings/today/R",
        wait_until="domcontentloaded",
        timeout=30000
    )

    page.wait_for_timeout(45000)

    Path("public/data/tab_meeting_capture.json").write_text(
        json.dumps(out, indent=2),
        encoding="utf-8"
    )

    browser.close()
