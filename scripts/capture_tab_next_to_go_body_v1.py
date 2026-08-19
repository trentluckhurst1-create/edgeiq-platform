from playwright.sync_api import sync_playwright
import json
from pathlib import Path

OUT = Path("public/data/tab_next_to_go_full.json")

TARGET = "tab-info-service/racing/next-to-go/races"

captured = None

with sync_playwright() as p:

    browser = p.chromium.launch(headless=True)

    page = browser.new_page()

    def handle_response(r):
        global captured

        try:
            if TARGET in r.url:
                print("[FOUND]")
                print(r.url)

                body = r.text()

                OUT.write_text(
                    body,
                    encoding="utf-8"
                )

                print("[SAVED]", OUT)
        except Exception as e:
            print("[ERROR]", e)

    page.on("response", handle_response)

    page.goto(
        "https://www.tab.com.au/racing/meetings/today/R",
        wait_until="networkidle",
        timeout=60000
    )

    page.wait_for_timeout(15000)

    browser.close()

print("DONE")
