from pathlib import Path
from playwright.sync_api import sync_playwright
import json
import re

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "public" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT = OUT_DIR / "tab_real_racing_network_capture_v1.json"
TEXT_OUT = OUT_DIR / "tab_real_racing_visible_text_v1.txt"

events = []

def keep_url(url):
    u = url.lower()
    return (
        "api.beta.tab.com.au" in u
        and (
            "racing" in u
            or "next-to-go" in u
            or "tab-info-service" in u
            or "bff-racing" in u
        )
    )

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        viewport={"width": 1500, "height": 950},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    )
    page = context.new_page()

    def on_response(resp):
        url = resp.url
        if not keep_url(url):
            return

        item = {
            "status": resp.status,
            "url": url,
            "content_type": resp.headers.get("content-type", ""),
            "text_start": "",
        }

        try:
            txt = resp.text()
            item["text_start"] = txt[:3000]
        except Exception as e:
            item["text_start"] = "READ_ERROR: " + str(e)

        events.append(item)
        print("[capture]", resp.status, url)

    page.on("response", on_response)

    print("[capture] opening TAB racing-betting")
    page.goto("https://www.tab.com.au/racing-betting", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(15000)

    try:
        TEXT_OUT.write_text(page.locator("body").inner_text(timeout=10000), encoding="utf-8")
    except Exception:
        pass

    click_patterns = [
        "Next To Go",
        "Horse Racing",
        "Racing",
        "Today",
        "Win",
        "Fixed",
        "Race 1",
        "R1",
    ]

    for pat in click_patterns:
        print("[capture] trying clicks for", pat)
        loc = page.get_by_text(pat, exact=False)
        try:
            count = min(loc.count(), 8)
        except Exception:
            count = 0

        for i in range(count):
            try:
                loc.nth(i).click(timeout=3000)
                page.wait_for_timeout(6000)
            except Exception:
                pass

    # Click race-looking links/buttons/cards by text content.
    candidates = page.locator("a, button, [role=button]").evaluate_all("""
        els => els.map((el, i) => ({
            i,
            text: (el.innerText || el.textContent || '').trim().slice(0, 120),
            href: el.href || ''
        })).filter(x =>
            /race|r\\d+|horse|greyhound|harness|next|go|today/i.test(x.text + ' ' + x.href)
        ).slice(0, 80)
    """)

    print("[capture] candidates", len(candidates))

    for c in candidates[:40]:
        try:
            handle = page.locator("a, button, [role=button]").nth(c["i"])
            print("[capture] click candidate:", c["text"], c["href"])
            handle.click(timeout=3000)
            page.wait_for_timeout(7000)
        except Exception:
            pass

    try:
        TEXT_OUT.write_text(page.locator("body").inner_text(timeout=10000), encoding="utf-8")
    except Exception:
        pass

    browser.close()

OUT.write_text(json.dumps(events, indent=2), encoding="utf-8")

print("[capture] racing_api_events=", len(events))
print("[capture] wrote", OUT)
print("[capture] wrote", TEXT_OUT)
