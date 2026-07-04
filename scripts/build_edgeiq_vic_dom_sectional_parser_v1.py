from pathlib import Path
import pandas as pd
import re
from playwright.sync_api import sync_playwright

ROOT = Path.cwd()

OUT_DIR = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

WAREHOUSE_OUT = OUT_DIR / "edgeiq_vic_dom_sectionals_v1.csv"
DIAG_OUT = OUT_DIR / "edgeiq_vic_dom_sectionals_diagnostics_v1.csv"

records = []
diagnostics = []

def clean(x):
    if x is None:
        return ""
    return re.sub(r"\s+", " ", str(x)).strip()

with sync_playwright() as p:

    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    context = browser.contexts[0]

    target_page = None

    for pg in context.pages:
        try:
            if "racing.com/form/" in pg.url and "speed-data" in pg.url:
                target_page = pg
                break
        except:
            pass

    if target_page is None:
        raise RuntimeError("NO SPEED DATA PAGE FOUND")

    sectional_frame = None

    for fr in target_page.frames:
        try:
            if "dxp-static.racing.com/sectionals" in fr.url:
                sectional_frame = fr
                break
        except:
            pass

    if sectional_frame is None:
        raise RuntimeError("SECTIONALS FRAME NOT FOUND")

    print("=" * 80)
    print("CONNECTED TO SECTIONALS FRAME")
    print(sectional_frame.url)

    target_page.wait_for_timeout(5000)

    body_text = sectional_frame.locator("body").inner_text()

    body_path = OUT_DIR / "edgeiq_vic_dom_sectionals_raw_body_v1.txt"
    body_path.write_text(body_text, encoding="utf-8")

    print("=" * 80)
    print("RAW BODY SAVED")
    print(body_path)

    lines = [clean(x) for x in body_text.splitlines()]
    lines = [x for x in lines if x]

    current_horse = None

    horse_pattern = re.compile(
        r'^\d+\.\s(.+?)\s\(\d+\)\sT:'
    )

    speed_pattern = re.compile(
        r'([\d\.]+)\s*km/h'
    )

    metre_pattern = re.compile(
        r'(\d+)(?:\(\+?-?\d+\))?\s*metres'
    )

    for idx, line in enumerate(lines):

        horse_match = horse_pattern.search(line)

        if horse_match:

            current_horse = clean(horse_match.group(1))

            diagnostics.append({
                "type": "HORSE_FOUND",
                "line_no": idx,
                "value": current_horse
            })

            continue

        if current_horse is None:
            continue

        if "km/h" in line and "metres" in line:

            speeds = speed_pattern.findall(line)
            metres = metre_pattern.findall(line)

            diagnostics.append({
                "type": "SECTIONAL_LINE",
                "line_no": idx,
                "value": line
            })

            if len(speeds) >= 5 and len(metres) >= 1:

                records.append({
                    "horse": current_horse,
                    "distance_ran_m": metres[0],
                    "early_speed_kmh": speeds[0],
                    "mid_speed_kmh": speeds[1],
                    "late_speed_kmh": speeds[2],
                    "peak_speed_kmh": speeds[3],
                    "avg_speed_kmh": speeds[4],
                    "source": "RACINGCOM_DOM_IFRAME_V1"
                })

    df = pd.DataFrame(records)

    if len(df):

        df["horse_key"] = (
            df["horse"]
            .astype(str)
            .str.upper()
            .str.replace(r'[^A-Z0-9]', '', regex=True)
        )

        df.to_csv(WAREHOUSE_OUT, index=False)

    diag = pd.DataFrame(diagnostics)
    diag.to_csv(DIAG_OUT, index=False)

    print("=" * 80)
    print("EDGEIQ VIC DOM SECTIONAL PARSER")
    print("=" * 80)
    print("ROWS:", len(df))

    if len(df):
        print(df.head(20).to_string(index=False))

    print("=" * 80)
    print("WAREHOUSE:", WAREHOUSE_OUT)
    print("DIAGNOSTICS:", DIAG_OUT)

    browser.close()
