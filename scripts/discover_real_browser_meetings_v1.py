from pathlib import Path
import pandas as pd
import re
from playwright.sync_api import sync_playwright

ROOT = Path.cwd()

PUBLIC = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"
PUBLIC.mkdir(parents=True, exist_ok=True)

OUT = PUBLIC / "edgeiq_real_vic_meetings_from_browser_v1.csv"

rows = []

with sync_playwright() as p:

    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")

    context = browser.contexts[0]

    page = context.new_page()

    page.goto("https://www.racing.com/calendar", wait_until="domcontentloaded")

    page.wait_for_timeout(8000)

    html = page.content()

    matches = re.findall(
        r'/form/(\d{4}-\d{2}-\d{2})/([^/]+)/race/1',
        html
    )

    matches = sorted(list(set(matches)))

    for race_date, track_slug in matches:

        rows.append({
            "race_date": race_date,
            "track_slug": track_slug
        })

    browser.close()

df = pd.DataFrame(rows)

if len(df):

    df = df.sort_values(
        ["race_date", "track_slug"]
    )

df.to_csv(OUT, index=False)

print("=" * 100)
print("REAL MEETINGS DISCOVERED")
print("=" * 100)
print("ROWS:", len(df))

if len(df):
    print(df.to_string(index=False))

print("=" * 100)
print("SAVED:", OUT)
