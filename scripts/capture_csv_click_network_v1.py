from pathlib import Path
import pandas as pd
from playwright.sync_api import sync_playwright

ROOT = Path.cwd()

OUT = ROOT / "dashboard" / "racing-dashboard" / "public" / "data" / "edgeiq_csv_click_network_capture_v1.csv"

network = []

with sync_playwright() as p:

    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    context = browser.contexts[0]

    page = None

    for pg in context.pages:
        try:
            if "racing.com/form/" in pg.url and "speed-data" in pg.url:
                page = pg
                break
        except:
            pass

    if page is None:
        raise RuntimeError("NO SPEED DATA PAGE FOUND")

    def capture_response(resp):

        try:

            url = resp.url.lower()

            interesting = any(x in url for x in [
                "csv",
                "download",
                "section",
                "speed",
                "export",
                "race",
                "split",
                "api"
            ])

            if interesting:

                entry = {
                    "url": resp.url,
                    "status": resp.status,
                    "content_type": resp.headers.get("content-type", ""),
                    "content_disposition": resp.headers.get("content-disposition", ""),
                }

                try:
                    txt = resp.text()
                    entry["preview"] = txt[:400]
                except:
                    entry["preview"] = ""

                network.append(entry)

                print("=" * 80)
                print(resp.url)
                print("STATUS:", resp.status)
                print("TYPE:", resp.headers.get("content-type", ""))

        except:
            pass

    page.on("response", capture_response)

    page.bring_to_front()
    page.wait_for_timeout(2000)

    try:
        page.locator("text=Accept All Cookies").click(timeout=2000)
    except:
        pass

    page.mouse.click(1120, 672)

    print("WAITING FOR NETWORK EVENTS...")
    page.wait_for_timeout(15000)

    browser.close()

df = pd.DataFrame(network)

if len(df):
    df.to_csv(OUT, index=False)

print("=" * 80)
print("NETWORK ROWS:", len(df))
print("SAVED:", OUT)
