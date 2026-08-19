from pathlib import Path
import pandas as pd
import re
from datetime import datetime, timedelta
from urllib.parse import parse_qs
from playwright.sync_api import sync_playwright

ROOT = Path.cwd()

PUBLIC = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"
PUBLIC.mkdir(parents=True, exist_ok=True)

OUT = PUBLIC / "edgeiq_vic_historical_sectional_warehouse_v3.csv"
DIAG = PUBLIC / "edgeiq_vic_historical_sectional_warehouse_v3_diagnostics.csv"
MEETINGS_OUT = PUBLIC / "edgeiq_vic_meeting_discovery_v1.csv"

records = []
diagnostics = []
meeting_rows = []

END_DATE = datetime(2026, 5, 13)
START_DATE = END_DATE - timedelta(days=60)

def clean(x):
    if x is None:
        return ""
    return re.sub(r"\s+", " ", str(x)).strip()

def horse_key(x):
    return re.sub(r'[^A-Z0-9]', '', str(x).upper())

def parse_visible_page(page):

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
        return {
            "meet_code": "",
            "rows": 0,
            "horses": [],
            "metrics": []
        }

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

    return {
        "meet_code": meet_code,
        "rows": min(len(horses), len(metrics)),
        "horses": horses,
        "metrics": metrics
    }

with sync_playwright() as p:

    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    context = browser.contexts[0]

    page = context.new_page()

    current = START_DATE

    while current <= END_DATE:

        race_date = current.strftime("%Y-%m-%d")

        calendar_url = "https://www.racing.com/calendar"

        print("=" * 100)
        print("CALENDAR:", race_date)

        try:

            page.goto(calendar_url, wait_until="domcontentloaded", timeout=90000)

            page.wait_for_timeout(5000)

            page.evaluate(f"""
                window.location.hash = '';
            """)

            body = page.locator("body").inner_text()

            html = page.content()

            meeting_matches = re.findall(
                r'/form/' + race_date + r'/([^/]+)/race/1',
                html
            )

            meeting_matches = sorted(list(set(meeting_matches)))

            print("MEETINGS FOUND:", len(meeting_matches))

            for track_slug in meeting_matches:

                meeting_rows.append({
                    "race_date": race_date,
                    "track_slug": track_slug
                })

                print("TRACK:", track_slug)

                for race_no in range(1, 11):

                    url = f"https://www.racing.com/form/{race_date}/{track_slug}/race/{race_no}/speed-data"

                    print(url)

                    try:

                        page.goto(url, wait_until="domcontentloaded", timeout=90000)

                        parsed = parse_visible_page(page)

                        if parsed["rows"] == 0:
                            continue

                        print("ROWS:", parsed["rows"])

                        for idx in range(parsed["rows"]):

                            horse = parsed["horses"][idx]
                            metric = parsed["metrics"][idx]

                            row = {
                                "race_date": race_date,
                                "track": track_slug,
                                "race_no": race_no,
                                "meet_code": parsed["meet_code"],
                                **horse,
                                **metric
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

                            row["source"] = "RACINGCOM_DOM_HISTORICAL_V3"

                            records.append(row)

                        diagnostics.append({
                            "race_date": race_date,
                            "track": track_slug,
                            "race_no": race_no,
                            "rows": parsed["rows"],
                            "status": "SUCCESS"
                        })

                    except Exception as e:

                        diagnostics.append({
                            "race_date": race_date,
                            "track": track_slug,
                            "race_no": race_no,
                            "status": "FAILED",
                            "error": repr(e)
                        })

        except Exception as e:

            diagnostics.append({
                "race_date": race_date,
                "status": "CALENDAR_FAILED",
                "error": repr(e)
            })

        current += timedelta(days=1)

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

pd.DataFrame(diagnostics).to_csv(DIAG, index=False)
pd.DataFrame(meeting_rows).to_csv(MEETINGS_OUT, index=False)

print("=" * 100)
print("EDGEIQ VIC HISTORICAL SECTIONAL WAREHOUSE V3")
print("=" * 100)
print("TOTAL ROWS:", len(df))
print("MEETINGS:", len(pd.DataFrame(meeting_rows)))

if len(df):
    print(df.head(50).to_string(index=False))

print("=" * 100)
print("WAREHOUSE:", OUT)
print("DIAGNOSTICS:", DIAG)
print("MEETINGS:", MEETINGS_OUT)
