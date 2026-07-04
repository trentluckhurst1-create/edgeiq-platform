
from pathlib import Path
import pandas as pd
import time
import re
from playwright.sync_api import sync_playwright

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"
if not DATA.exists():
    DATA = ROOT / "public" / "data"

PROFILE_DIR = ROOT / "edgeiq_ra_browser_profile"
if not PROFILE_DIR.exists():
    PROFILE_DIR = ROOT.parent.parent / "edgeiq_ra_browser_profile"

OUT_DIR = ROOT / "outputs" / "ra_persistent_browser_test"
if not OUT_DIR.exists():
    OUT_DIR = ROOT.parent.parent / "outputs" / "ra_persistent_browser_test"

OUT_DIR.mkdir(parents=True, exist_ok=True)

TARGETS = DATA / "edgeiq_active_ra_profile_backfill_targets_v1.csv"
DIAG = DATA / "edgeiq_ra_persistent_browser_test_diagnostics_v1.csv"

targets = pd.read_csv(TARGETS)

def safe_name(x):
    return re.sub(r"[^A-Z0-9]", "", str(x).upper())

rows = []

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=False,
        viewport={"width": 1400, "height": 900},
    )

    page = context.new_page()

    print("=" * 100)
    print("MANUAL STEP")
    print("=" * 100)
    print("A browser is open.")
    print("If Racing Australia asks for verification, complete it manually.")
    print("Then return here and press ENTER.")
    input("PRESS ENTER WHEN READY: ")

    for _, r in targets.iterrows():
        horse = str(r["horse"])
        horse_key = safe_name(r["horse_key"])
        url = str(r["profile_url"])

        try:
            page.goto(url, wait_until="networkidle", timeout=90000)
            time.sleep(5)

            html = page.content()
            title = page.title()

            out_html = OUT_DIR / f"{horse_key}.html"
            out_html.write_text(html, encoding="utf-8", errors="ignore")

            lower = html.lower()

            status = "REAL_FORM_CAPTURED" if (
                "horse not found" not in lower
                and (
                    "horsefullform" in lower
                    or "career" in lower
                    or "all form" in lower
                    or "barrier" in lower
                )
            ) else "STILL_BLOCKED_OR_NOT_FOUND"

            rows.append({
                "horse": horse,
                "horse_key": horse_key,
                "status": status,
                "html_len": len(html),
                "title": title,
                "contains_horse_not_found": "horse not found" in lower,
                "contains_zenedge": "zenedge" in lower or "__zenedge" in lower,
                "contains_career": "career" in lower,
                "contains_barrier": "barrier" in lower,
                "contains_all_form": "all form" in lower,
                "saved_html": str(out_html),
            })

            pd.DataFrame(rows).to_csv(DIAG, index=False)
            print(pd.DataFrame([rows[-1]]).to_string(index=False))

        except Exception as e:
            rows.append({
                "horse": horse,
                "horse_key": horse_key,
                "status": "FAILED",
                "html_len": 0,
                "title": "",
                "contains_horse_not_found": "",
                "contains_zenedge": "",
                "contains_career": "",
                "contains_barrier": "",
                "contains_all_form": "",
                "saved_html": "",
                "error": repr(e),
            })
            pd.DataFrame(rows).to_csv(DIAG, index=False)

    context.close()

pd.DataFrame(rows).to_csv(DIAG, index=False)

print("=" * 100)
print("PERSISTENT RA BROWSER TEST COMPLETE")
print("=" * 100)
print(pd.DataFrame(rows).to_string(index=False))
print("SAVED:", DIAG)
print("PROFILE:", PROFILE_DIR)
print("HTML:", OUT_DIR)
