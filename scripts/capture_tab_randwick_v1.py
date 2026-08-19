from pathlib import Path
from playwright.sync_api import sync_playwright
import json

DEBUG = Path("public/data/tab_randwick_capture_v1")
DEBUG.mkdir(parents=True, exist_ok=True)

events = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    page = browser.new_page(
        viewport={"width": 1500, "height": 950}
    )

    def handle_response(resp):
        url = resp.url

        if (
            "api.beta.tab.com.au" in url.lower()
            or "tab-info-service" in url.lower()
            or "bff-racing" in url.lower()
        ):
            item = {
                "status": resp.status,
                "url": url
            }

            try:
                txt = resp.text()

                item["preview"] = txt[:1000]

                fname = (
                    "resp_" +
                    str(len(events)).zfill(3) +
                    ".txt"
                )

                (DEBUG / fname).write_text(
                    txt[:250000],
                    encoding="utf-8",
                    errors="ignore"
                )

            except Exception as e:
                item["preview"] = str(e)

            events.append(item)

            print(resp.status, url)

    page.on("response", handle_response)

    page.goto(
        "https://www.tab.com.au/racing/2026-06-06/RANDWICK/RAN/R/1",
        wait_until="domcontentloaded",
        timeout=45000
    )

    page.wait_for_timeout(30000)

    browser.close()

(Path(DEBUG / "network.json")).write_text(
    json.dumps(events, indent=2),
    encoding="utf-8"
)

print("events=", len(events))
