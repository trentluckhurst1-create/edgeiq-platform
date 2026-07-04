from pathlib import Path
import pandas as pd
import re
from urllib.parse import parse_qs
from playwright.sync_api import sync_playwright

ROOT = Path.cwd()

PUBLIC = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"
PUBLIC.mkdir(parents=True, exist_ok=True)

OUT = PUBLIC / "edgeiq_vic_dom_sectional_warehouse_v1.csv"
DIAG = PUBLIC / "edgeiq_vic_dom_sectional_warehouse_diagnostics_v1.csv"

records = []
diagnostics = []

def clean(x):
    if x is None:
        return ""
    return re.sub(r"\s+", " ", str(x)).strip()

def horse_key(x):
    return re.sub(r'[^A-Z0-9]', '', str(x).upper())

with sync_playwright() as p:

    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    context = browser.contexts[0]

    pages = []

    for pg in context.pages:
        try:
            if "racing.com/form/" in pg.url and "speed-data" in pg.url:
                pages.append(pg)
        except:
            pass

    print("=" * 100)
    print("VISIBLE SPEED DATA PAGES:", len(pages))
    print("=" * 100)

    for page in pages:

        try:

            page.bring_to_front()
            page.wait_for_timeout(3000)

            page_url = page.url

            print("PROCESSING:", page_url)

            m = re.search(
                r'/form/(\d{4}-\d{2}-\d{2})/([^/]+)/race/(\d+)/speed-data',
                page_url
            )

            if not m:
                continue

            race_date = m.group(1)
            track = m.group(2)
            race_no = int(m.group(3))

            sectional_frame = None

            for fr in page.frames:
                try:
                    if "dxp-static.racing.com/sectionals" in fr.url:
                        sectional_frame = fr
                        break
                except:
                    pass

            if sectional_frame is None:
                continue

            frame_url = sectional_frame.url

            meet_code = ""

            if "#?" in frame_url:

                frag = frame_url.split("#?", 1)[1]

                qs = parse_qs(frag)

                meet_code = qs.get("meetCode", [""])[0]

            body_text = sectional_frame.locator("body").inner_text()

            lines = [clean(x) for x in body_text.splitlines()]
            lines = [x for x in lines if x]

            horses = []

            for idx, line in enumerate(lines):

                pos_match = re.match(r'^(\d+)(?:st|nd|rd|th)$', line)

                if pos_match and idx + 1 < len(lines):

                    horse_line = lines[idx + 1]

                    horse_match = re.match(
                        r'^\d+\.\s(.+?)\s\(\d+\)$',
                        horse_line
                    )

                    if horse_match:

                        horses.append({
                            "position": int(pos_match.group(1)),
                            "horse": horse_match.group(1).strip()
                        })

            metrics = []

            i = 0

            while i < len(lines):

                line = lines[i]

                if re.match(r'^\d+(?:\(\+?-?\d+\))?$', line):

                    try:

                        distance = re.search(r'(\d+)', line).group(1)

                        early = re.search(r'([\d\.]+)', lines[i + 2]).group(1)
                        mid   = re.search(r'([\d\.]+)', lines[i + 4]).group(1)
                        late  = re.search(r'([\d\.]+)', lines[i + 6]).group(1)
                        peak  = re.search(r'([\d\.]+)', lines[i + 8]).group(1)
                        avg   = re.search(r'([\d\.]+)', lines[i + 10]).group(1)

                        metrics.append({
                            "distance_ran_m": int(distance),
                            "early_speed_kmh": float(early),
                            "mid_speed_kmh": float(mid),
                            "late_speed_kmh": float(late),
                            "peak_speed_kmh": float(peak),
                            "avg_speed_kmh": float(avg)
                        })

                        i += 11
                        continue

                    except:
                        pass

                i += 1

            row_count = min(len(horses), len(metrics))

            print("HORSES:", len(horses))
            print("METRICS:", len(metrics))
            print("ROWS:", row_count)

            for idx in range(row_count):

                row = {
                    "race_date": race_date,
                    "track": track,
                    "race_no": race_no,
                    "meet_code": meet_code,
                    **horses[idx],
                    **metrics[idx]
                }

                row["horse_key"] = horse_key(row["horse"])

                row["late_vs_mid_delta"] = round(
                    row["late_speed_kmh"] - row["mid_speed_kmh"],
                    2
                )

                row["peak_vs_avg_delta"] = round(
                    row["peak_speed_kmh"] - row["avg_speed_kmh"],
                    2
                )

                row["fast_finisher_flag"] = (
                    row["late_speed_kmh"] > row["mid_speed_kmh"]
                )

                row["sustained_speed_flag"] = (
                    row["avg_speed_kmh"] >= 60
                )

                row["source"] = "RACINGCOM_DOM_WAREHOUSE_V1"

                records.append(row)

            diagnostics.append({
                "page_url": page_url,
                "race_date": race_date,
                "track": track,
                "race_no": race_no,
                "meet_code": meet_code,
                "horses_found": len(horses),
                "metrics_found": len(metrics),
                "rows_created": row_count
            })

        except Exception as e:

            diagnostics.append({
                "page_url": page.url if 'page' in locals() else "",
                "error": repr(e)
            })

    browser.close()

df = pd.DataFrame(records)

if len(df):

    df = df.drop_duplicates(
        subset=[
            "race_date",
            "track",
            "race_no",
            "horse_key"
        ]
    )

    df = df.sort_values(
        [
            "race_date",
            "track",
            "race_no",
            "position"
        ]
    )

df.to_csv(OUT, index=False)

diag = pd.DataFrame(diagnostics)
diag.to_csv(DIAG, index=False)

print("=" * 100)
print("EDGEIQ VIC DOM SECTIONAL WAREHOUSE V1")
print("=" * 100)
print("TOTAL ROWS:", len(df))

if len(df):

    print(df.head(30).to_string(index=False))

print("=" * 100)
print("SAVED:", OUT)
print("SAVED:", DIAG)
