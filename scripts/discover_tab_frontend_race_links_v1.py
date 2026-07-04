from pathlib import Path
from playwright.sync_api import sync_playwright
import json
import re

OUT = Path("public/data/tab_page_links_today_racing.json")
TXT = Path("public/data/tab_today_racing_links_text.txt")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={"width": 1500, "height": 950})

    page.goto(
        "https://www.tab.com.au/racing/meetings/today/R",
        wait_until="domcontentloaded",
        timeout=30000
    )

    page.wait_for_timeout(20000)

    links = page.locator("a").evaluate_all("""
        els => els.map(a => ({
            text: (a.innerText || a.textContent || '').trim(),
            href: a.href || ''
        })).filter(x =>
            x.href.includes('/racing') ||
            x.text.match(/race|r\\d+|taree|shepparton|melton|today|horse|greyhound|harness/i)
        )
    """)

    body = page.locator("body").inner_text(timeout=10000)

    OUT.write_text(json.dumps(links, indent=2), encoding="utf-8")
    TXT.write_text(body, encoding="utf-8", errors="ignore")

    print("[links] count", len(links))
    for x in links[:120]:
        print("TEXT=", x["text"][:80].replace("\n", " "), "HREF=", x["href"])

    browser.close()
