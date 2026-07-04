from pathlib import Path
import pandas as pd
import shutil
from playwright.sync_api import sync_playwright

ROOT = Path.cwd()

OUTDIR = ROOT / "outputs" / "sectionals" / "raw" / "VIC" / "racingcom_manual_visible_csv"
OUTDIR.mkdir(parents=True, exist_ok=True)

DOWNLOADS = Path.home() / "Downloads"

with sync_playwright() as p:

    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    context = browser.contexts[0]

    target = None

    for pg in context.pages:
        try:
            if "racing.com/form/" in pg.url and "speed-data" in pg.url:
                target = pg
                break
        except:
            pass

    if target is None:
        raise RuntimeError("NO SPEED DATA PAGE FOUND")

    target.bring_to_front()
    target.wait_for_timeout(2000)

    print("ACTIVE PAGE:", target.url)

    try:
        target.locator("text=Accept All Cookies").click(timeout=3000)
        target.wait_for_timeout(2000)
        print("COOKIE BANNER ACCEPTED")
    except:
        print("NO COOKIE BANNER CLICKED")

    before = {f.name for f in DOWNLOADS.glob("*")}

    box = target.viewport_size
    print("VIEWPORT:", box)

    # bottom-right CSV area from your screenshot
    target.mouse.click(1120, 672)

    print("CLICKED CSV AREA")

    target.wait_for_timeout(12000)

    after = [
        f for f in DOWNLOADS.glob("*")
        if f.name not in before
        and not f.name.endswith(".crdownload")
    ]

    if not after:
        print("NO DOWNLOAD DETECTED")
    else:
        latest = sorted(after, key=lambda x: x.stat().st_mtime, reverse=True)[0]

        target_path = OUTDIR / latest.name
        shutil.copy2(latest, target_path)

        print("DOWNLOADED:", target_path)

        try:
            df = pd.read_csv(target_path, low_memory=False)

            print("=" * 80)
            print("CSV SUCCESS")
            print("=" * 80)
            print("ROWS:", len(df))
            print("COLUMNS:")
            print(list(df.columns))

            out = ROOT / "dashboard" / "racing-dashboard" / "public" / "data" / "edgeiq_manual_csv_success_v1.csv"
            df.to_csv(out, index=False)

            print("SAVED PARSED CSV:", out)

        except Exception as e:
            print("CSV PARSE FAILED:", repr(e))

    browser.close()
