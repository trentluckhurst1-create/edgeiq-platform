import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

NEXT_TO_GO = ROOT / "public" / "data" / "tab_next_to_go_full.json"
OUT = ROOT / "public" / "data" / "tab_race_details_test.json"

data = json.loads(NEXT_TO_GO.read_text(encoding="utf-8"))

url = data["races"][0]["_links"]["self"]

print("[tab_race_test] url=", url)

with sync_playwright() as p:

    browser = p.chromium.launch(headless=False)

    page = browser.new_page()

    with page.expect_response(
        lambda r: url in r.url,
        timeout=60000
    ) as resp_info:

        page.goto(url, wait_until="domcontentloaded")

    resp = resp_info.value

    body = resp.text()

    OUT.write_text(body, encoding="utf-8")

    print("[tab_race_test] bytes=", len(body))
    print(body[:2000])

    browser.close()
