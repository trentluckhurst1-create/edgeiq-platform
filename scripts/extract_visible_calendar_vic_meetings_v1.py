from pathlib import Path
import pandas as pd
import re
from playwright.sync_api import sync_playwright

ROOT = Path.cwd()
PUBLIC = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"
PUBLIC.mkdir(parents=True, exist_ok=True)

OUT = PUBLIC / "edgeiq_visible_calendar_vic_meetings_v1.csv"

rows = []

with sync_playwright() as p:

    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    context = browser.contexts[0]

    page = None

    for pg in context.pages:
        try:
            if "racing.com/calendar" in pg.url:
                page = pg
                break
        except:
            pass

    if page is None:
        raise RuntimeError("OPEN THE RACING.COM CALENDAR TAB FIRST")

    page.bring_to_front()
    page.wait_for_timeout(3000)

    month = ""
    try:
        month = page.locator("text=/[A-Za-z]+ 2026/").first.inner_text(timeout=3000)
    except:
        pass

    text = page.locator("body").inner_text()

    lines = [x.strip() for x in text.splitlines()]
    lines = [x for x in lines if x]

    current_date = ""

    for i, line in enumerate(lines):

        if re.fullmatch(r"\d{2}", line):
            current_date = line
            continue

        if i + 1 < len(lines) and lines[i + 1] == "VIC":

            venue = line

            rows.append({
                "calendar_month": month,
                "day": current_date,
                "venue": venue,
                "state": "VIC"
            })

df = pd.DataFrame(rows).drop_duplicates()

df.to_csv(OUT, index=False)

print("=" * 100)
print("VISIBLE VIC MEETINGS FOUND")
print("=" * 100)
print("ROWS:", len(df))

if len(df):
    print(df.to_string(index=False))

print("=" * 100)
print("SAVED:", OUT)

browser.close()
