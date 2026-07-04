from pathlib import Path
from playwright.sync_api import sync_playwright
import json

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "public" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT = OUT_DIR / "tab_next_to_go_browser_context_test.json"

URL = "https://api.beta.tab.com.au/v1/tab-info-service/racing/next-to-go/races?jurisdiction=VIC&includeFixedOdds=true&returnPromo=false&returnOffers=false"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(
        viewport={"width": 1500, "height": 950},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    )

    print("[tab_browser_api_test] opening TAB")
    page.goto("https://www.tab.com.au/racing-betting", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(10000)

    print("[tab_browser_api_test] calling API inside browser context")
    result = page.evaluate(
        """async (url) => {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 20000);

            try {
                const res = await fetch(url, {
                    method: "GET",
                    credentials: "include",
                    headers: {
                        "accept": "application/json",
                        "x-requested-with": "XMLHttpRequest"
                    },
                    signal: controller.signal
                });

                const text = await res.text();
                clearTimeout(timeout);

                return {
                    ok: res.ok,
                    status: res.status,
                    statusText: res.statusText,
                    url: res.url,
                    text: text.slice(0, 500000)
                };
            } catch (e) {
                clearTimeout(timeout);
                return {
                    ok: false,
                    status: 0,
                    statusText: String(e),
                    url: url,
                    text: ""
                };
            }
        }""",
        URL
    )

    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("[tab_browser_api_test] status=", result.get("status"))
    print("[tab_browser_api_test] statusText=", result.get("statusText"))
    print("[tab_browser_api_test] text_start=", result.get("text", "")[:1000])
    print("[tab_browser_api_test] wrote", OUT)

    browser.close()
