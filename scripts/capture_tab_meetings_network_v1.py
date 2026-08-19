from pathlib import Path
from playwright.sync_api import sync_playwright
import json
import re
from datetime import datetime

ROOT = Path(".")
DATA = ROOT / "public/data"
OUT = DATA / "tab_network_meetings_capture_v1.json"
TXT = DATA / "tab_network_meetings_capture_v1.txt"

TARGETS = [
    "https://www.tab.com.au/racing/meetings/today/R",
    "https://www.tab.com.au/racing/meetings/tomorrow/R",
    "https://www.tab.com.au/racing/meetings/2026-06-19/R",
]

hits = []

def looks_useful(url):
    u = url.lower()
    return (
        "api.beta.tab.com.au" in u
        and "tab-info-service/racing" in u
        and (
            "/meetings" in u
            or "/dates/" in u
            or "racing/meetings" in u
        )
    )

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={"width": 1500, "height": 950})

    def on_response(resp):
        url = resp.url
        if not looks_useful(url):
            return
        try:
            status = resp.status
            txt = resp.text()
            hits.append({
                "captured_at": datetime.now().isoformat(timespec="seconds"),
                "url": url,
                "status": status,
                "length": len(txt),
                "text": txt[:200000],
            })
            print("[CAPTURE]", status, len(txt), url)
        except Exception as e:
            hits.append({
                "captured_at": datetime.now().isoformat(timespec="seconds"),
                "url": url,
                "status": "ERR",
                "error": repr(e),
            })
            print("[CAPTURE_ERR]", repr(e), url)

    page.on("response", on_response)

    for url in TARGETS:
        print("[OPEN]", url)
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(15000)

    browser.close()

DATA.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(hits, indent=2), encoding="utf-8")

lines = []
for h in hits:
    lines.append(f"{h.get('status')} {h.get('length')} {h.get('url')}")
TXT.write_text("\n".join(lines), encoding="utf-8")

print("[DONE] hits", len(hits))
print("[WROTE]", OUT)
print("[WROTE]", TXT)
