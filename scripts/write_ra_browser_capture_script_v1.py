from pathlib import Path
import pandas as pd

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"
SCRIPT = ROOT / "dashboard" / "racing-dashboard" / "scripts" / "run_edgeiq_active_ra_browser_capture_v1.py"

TARGETS = DATA / "edgeiq_active_ra_profile_backfill_targets_v1.csv"

targets = pd.read_csv(TARGETS)

urls = []
for _, r in targets.iterrows():
    urls.append({
        "horse": str(r["horse"]),
        "horse_key": str(r["horse_key"]),
        "profile_url": str(r["profile_url"]),
    })

script = r'''
from pathlib import Path
import pandas as pd
import time
import re

from playwright.sync_api import sync_playwright

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"
if not DATA.exists():
    DATA = ROOT / "public" / "data"

OUT_DIR = ROOT / "outputs" / "ra_active_profile_browser_capture"
if not OUT_DIR.exists():
    OUT_DIR = ROOT.parent.parent / "outputs" / "ra_active_profile_browser_capture"

OUT_DIR.mkdir(parents=True, exist_ok=True)

TARGETS = DATA / "edgeiq_active_ra_profile_backfill_targets_v1.csv"
DIAG = DATA / "edgeiq_active_ra_browser_capture_diagnostics_v1.csv"

targets = pd.read_csv(TARGETS)

def safe_name(x):
    return re.sub(r"[^A-Z0-9]", "", str(x).upper())

rows = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    for _, r in targets.iterrows():
        horse = str(r["horse"])
        horse_key = safe_name(r["horse_key"])
        url = str(r["profile_url"])

        status = "UNKNOWN"
        html_len = 0
        title = ""
        contains_zenedge = False
        contains_real_form = False

        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            time.sleep(4)

            html = page.content()
            html_len = len(html)
            title = page.title()

            contains_zenedge = "__zenedge" in html.lower() or "zenedge" in html.lower()
            contains_real_form = (
                "HorseFullForm" in html
                or "All Form" in html
                or "Barrier" in html
                or "Career" in html
                or "Jockey" in html
            )

            out_path = OUT_DIR / f"{horse_key}.html"
            out_path.write_text(html, encoding="utf-8", errors="ignore")

            status = "CAPTURED_REAL_FORM" if contains_real_form and not contains_zenedge else "CAPTURED_BUT_BLOCKED"

        except Exception as e:
            status = "FAILED_" + repr(e)[:160]

        rows.append({
            "horse": horse,
            "horse_key": horse_key,
            "profile_url": url,
            "status": status,
            "html_len": html_len,
            "title": title,
            "contains_zenedge": contains_zenedge,
            "contains_real_form": contains_real_form,
        })

        pd.DataFrame(rows).to_csv(DIAG, index=False)
        print(pd.DataFrame([rows[-1]]).to_string(index=False))

    browser.close()

pd.DataFrame(rows).to_csv(DIAG, index=False)

print("=" * 100)
print("EDGEIQ ACTIVE RA BROWSER CAPTURE COMPLETE")
print("=" * 100)
print(pd.DataFrame(rows).to_string(index=False))
print("SAVED:", DIAG)
print("RAW HTML:", OUT_DIR)
'''

SCRIPT.write_text(script, encoding="utf-8")

print("SAVED:", SCRIPT)
