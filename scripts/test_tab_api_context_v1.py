from pathlib import Path
from playwright.sync_api import sync_playwright
import json

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "public" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT = OUT_DIR / "tab_next_to_go_api_context_test.json"

URLS = [
    "https://api.beta.tab.com.au/v1/tab-info-service/racing/next-to-go/races?jurisdiction=VIC",
    "https://api.beta.tab.com.au/v1/tab-info-service/racing/next-to-go/races?jurisdiction=NSW",
    "https://api.beta.tab.com.au/v1/bff-racing/next-to-go?jurisdiction=VIC&platform=web&version=20260601-34-RELEASE",
    "https://api.beta.tab.com.au/v1/bff-racing/home?jurisdiction=VIC&platform=web&version=20260601-34-RELEASE",
]

results = []

with sync_playwright() as p:
    req = p.request.new_context(
        extra_http_headers={
            "accept": "application/json, text/plain, */*",
            "origin": "https://www.tab.com.au",
            "referer": "https://www.tab.com.au/racing-betting",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
        },
        timeout=20000,
    )

    for url in URLS:
        print("[tab_api_context] trying", url)
        try:
            r = req.get(url)
            txt = r.text()
            results.append({
                "url": url,
                "status": r.status,
                "ok": r.ok,
                "text_start": txt[:2000],
            })
            print("[tab_api_context] status=", r.status, "len=", len(txt))
        except Exception as e:
            results.append({
                "url": url,
                "status": 0,
                "ok": False,
                "error": str(e),
                "text_start": "",
            })
            print("[tab_api_context] error=", str(e))

    req.dispose()

OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
print("[tab_api_context] wrote", OUT)
