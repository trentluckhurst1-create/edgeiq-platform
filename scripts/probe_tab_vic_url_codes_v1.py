from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import pandas as pd
import json
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT = DATA / "tab_vic_url_probe_results_v1.csv"
DATA.mkdir(parents=True, exist_ok=True)

date = "2026-06-06"

candidates = [
    # Flemington possibilities
    ("FLEMINGTON", "FLEMINGTON", "FLE"),
    ("FLEMINGTON", "FLEMINGTON", "FLM"),
    ("FLEMINGTON", "FLEMINGTON", "FLEM"),
    ("FLEMINGTON", "FLEMINGTON", "MEL"),
    ("FLEMINGTON", "FLEMINGTON", "VRC"),

    # Swan Hill possibilities
    ("SWAN HILL", "SWAN-HILL", "SWH"),
    ("SWAN HILL", "SWAN-HILL", "SHL"),
    ("SWAN HILL", "SWAN-HILL", "SWN"),
    ("SWAN HILL", "SWAN-HILL", "SWA"),
    ("SWAN HILL", "SWAN-HILL", "SWHL"),

    # Bet365 Swan Hill naming possibilities
    ("SWAN HILL", "BET365-SWAN-HILL", "SWH"),
    ("SWAN HILL", "BET365-SWAN-HILL", "SHL"),
    ("SWAN HILL", "BET365-SWAN-HILL", "SWN"),
]

rows = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={"width": 1500, "height": 950})

    for meeting_name, slug, venue in candidates:
        for race_no in range(1, 10):
            url = f"https://www.tab.com.au/racing/{date}/{slug}/{venue}/R/{race_no}"
            expected = f"/dates/{date}/meetings/R/{venue}/races/{race_no}"

            print("[probe]", url)

            api_hit = ""
            status = ""
            runner_count = ""
            page_text = ""

            try:
                with page.expect_response(
                    lambda r, expected=expected: (
                        expected in r.url
                        and "api.beta.tab.com.au" in r.url
                        and "/form/" not in r.url
                        and "/pools/" not in r.url
                        and "/silk/" not in r.url
                        and r.status == 200
                    ),
                    timeout=12000
                ) as resp_info:
                    page.goto(url, wait_until="domcontentloaded", timeout=25000)

                resp = resp_info.value
                txt = resp.text()
                payload = json.loads(txt)

                api_hit = resp.url
                status = "API_OK"
                runner_count = len(payload.get("runners", []) or [])

                print("[FOUND]", url, "runners", runner_count)

            except PlaywrightTimeoutError:
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    page.wait_for_timeout(2500)
                    page_text = page.locator("body").inner_text(timeout=5000)[:250].replace("\n", " ")
                    if "doesn" in page_text.lower() or "uh oh" in page_text.lower():
                        status = "PAGE_NOT_FOUND"
                    else:
                        status = "NO_API_BUT_PAGE"
                except Exception as e:
                    status = "ERROR"
                    page_text = str(e)[:250]

            except Exception as e:
                status = "ERROR"
                page_text = str(e)[:250]

            rows.append({
                "meeting_name": meeting_name,
                "slug": slug,
                "venue_mnemonic": venue,
                "race_no": race_no,
                "status": status,
                "runner_count": runner_count,
                "url": url,
                "api_hit": api_hit,
                "page_text": page_text,
            })

            if status == "API_OK":
                break

    browser.close()

df = pd.DataFrame(rows)
df.to_csv(OUT, index=False)

print("[probe] wrote", OUT)
print(df[df["status"] == "API_OK"].to_string(index=False))

if df[df["status"] == "API_OK"].empty:
    print("[probe] NO VIC TAB API URL FOUND from candidate list.")
