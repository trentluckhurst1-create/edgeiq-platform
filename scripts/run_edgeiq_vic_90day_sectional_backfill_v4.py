from pathlib import Path
import pandas as pd
import re
from urllib.parse import parse_qs
from playwright.sync_api import sync_playwright

ROOT = Path.cwd()

PUBLIC = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"
PUBLIC.mkdir(parents=True, exist_ok=True)

OUT = PUBLIC / "edgeiq_vic_historical_sectional_warehouse_v4.csv"
DIAG = PUBLIC / "edgeiq_vic_historical_sectional_warehouse_v4_diagnostics.csv"
MEETINGS = PUBLIC / "edgeiq_vic_calendar_meetings_v1.csv"

records = []
diag_rows = []
meeting_rows = []

TARGET_MONTHS = [
    "March 2026",
    "April 2026",
    "May 2026"
]

def clean(x):
    if x is None:
        return ""
    return re.sub(r"\s+", " ", str(x)).strip()

def horse_key(x):
    return re.sub(r'[^A-Z0-9]', '', str(x).upper())

def parse_sectionals(page):

    page.wait_for_timeout(5000)

    sectional_frame = None

    for fr in page.frames:
        try:
            if "dxp-static.racing.com/sectionals" in fr.url:
                sectional_frame = fr
                break
        except:
            pass

    if sectional_frame is None:
        return []

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

    rows = []

    for idx in range(min(len(horses), len(metrics))):

        row = {
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

        rows.append(row)

    return rows

with sync_playwright() as p:

    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    context = browser.contexts[0]

    page = context.new_page()

    page.goto("https://www.racing.com/calendar")

    page.wait_for_timeout(6000)

    try:
        page.locator("text=Victoria").click(timeout=5000)
    except:
        pass

    for target_month in TARGET_MONTHS:

        print("=" * 100)
        print("TARGET MONTH:", target_month)

        for _ in range(12):

            try:

                current_month = clean(
                    page.locator("h1").inner_text()
                )

                print("CURRENT:", current_month)

                if target_month in current_month:
                    break

                page.locator("button").nth(0).click()

                page.wait_for_timeout(3000)

            except:
                pass

        html = page.content()

        meeting_matches = re.findall(
            r'/form/(\d{4}-\d{2}-\d{2})/([^/]+)/race/1',
            html
        )

        meeting_matches = sorted(list(set(meeting_matches)))

        print("MEETINGS:", len(meeting_matches))

        for race_date, track_slug in meeting_matches:

            meeting_rows.append({
                "race_date": race_date,
                "track_slug": track_slug
            })

            print(race_date, track_slug)

            for race_no in range(1, 11):

                url = f"https://www.racing.com/form/{race_date}/{track_slug}/race/{race_no}/speed-data"

                print(url)

                try:

                    page.goto(url, wait_until="domcontentloaded", timeout=90000)

                    rows = parse_sectionals(page)

                    if len(rows) == 0:

                        diag_rows.append({
                            "race_date": race_date,
                            "track_slug": track_slug,
                            "race_no": race_no,
                            "status": "NO_SECTIONALS"
                        })

                        continue

                    print("SECTIONAL ROWS:", len(rows))

                    for row in rows:

                        row["race_date"] = race_date
                        row["track"] = track_slug
                        row["race_no"] = race_no
                        row["source"] = "RACINGCOM_CALENDAR_TRAVERSAL_V4"

                        records.append(row)

                    diag_rows.append({
                        "race_date": race_date,
                        "track_slug": track_slug,
                        "race_no": race_no,
                        "status": "SUCCESS",
                        "rows": len(rows)
                    })

                    df_live = pd.DataFrame(records)

                    if len(df_live):

                        df_live = df_live.drop_duplicates(
                            subset=[
                                "race_date",
                                "track",
                                "race_no",
                                "horse_key"
                            ]
                        )

                        df_live.to_csv(OUT, index=False)

                    pd.DataFrame(diag_rows).to_csv(DIAG, index=False)

                except Exception as e:

                    diag_rows.append({
                        "race_date": race_date,
                        "track_slug": track_slug,
                        "race_no": race_no,
                        "status": "FAILED",
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

pd.DataFrame(diag_rows).to_csv(DIAG, index=False)
pd.DataFrame(meeting_rows).to_csv(MEETINGS, index=False)

print("=" * 100)
print("EDGEIQ VIC HISTORICAL SECTIONAL WAREHOUSE V4")
print("=" * 100)
print("TOTAL ROWS:", len(df))
print("MEETINGS:", len(pd.DataFrame(meeting_rows)))

if len(df):
    print(df.head(50).to_string(index=False))

print("=" * 100)
print("WAREHOUSE:", OUT)
print("DIAGNOSTICS:", DIAG)
print("MEETINGS:", MEETINGS)
