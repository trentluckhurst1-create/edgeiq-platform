from pathlib import Path
import pandas as pd
import re
from datetime import datetime
from urllib.parse import parse_qs
from playwright.sync_api import sync_playwright

ROOT = Path.cwd()
PUBLIC = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"
PUBLIC.mkdir(parents=True, exist_ok=True)

MEETINGS_OUT = PUBLIC / "edgeiq_vic_real_meetings_mar_apr_may_2026_v1.csv"
URLS_OUT = PUBLIC / "edgeiq_vic_real_speed_urls_mar_apr_may_2026_v1.csv"
WAREHOUSE_OUT = PUBLIC / "edgeiq_vic_90day_sectional_warehouse_final_v1.csv"
DIAG_OUT = PUBLIC / "edgeiq_vic_90day_sectional_warehouse_final_diagnostics_v1.csv"

COMPLETED_CUTOFF = datetime(2026, 5, 13)

records = []
diagnostics = []
meetings = []

def clean(x):
    return re.sub(r"\s+", " ", str(x or "")).strip()

def slugify_venue(x):
    s = str(x or "").lower().strip()
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")

def horse_key(x):
    return re.sub(r"[^A-Z0-9]", "", str(x or "").upper())

def extract_visible_calendar_meetings(page):
    text = page.locator("body").inner_text()
    lines = [clean(x) for x in text.splitlines()]
    lines = [x for x in lines if x]

    month = ""
    for line in lines:
        if re.search(r"(March|April|May)\s+2026", line):
            month = re.search(r"(March|April|May)\s+2026", line).group(0)
            break

    rows = []
    current_day = ""

    for i, line in enumerate(lines):
        if re.fullmatch(r"\d{2}", line):
            current_day = line
            continue

        if i + 1 < len(lines) and lines[i + 1] == "VIC" and current_day:
            rows.append({
                "calendar_month": month,
                "day": current_day,
                "venue": line,
                "state": "VIC"
            })

    return rows

def parse_sectionals(page):
    page.wait_for_timeout(5500)

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

    if len(body_text) < 500:
        return []

    lines = [clean(x) for x in body_text.splitlines()]
    lines = [x for x in lines if x]

    horses = []

    for idx, line in enumerate(lines):
        pos_match = re.match(r"^(\d+)(?:st|nd|rd|th)$", line)

        if pos_match and idx + 1 < len(lines):
            horse_line = lines[idx + 1]
            horse_match = re.match(r"^\d+\.\s(.+?)\s\(\d+\)$", horse_line)

            if horse_match:
                horses.append({
                    "position": int(pos_match.group(1)),
                    "horse": horse_match.group(1).strip()
                })

    metrics = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if re.match(r"^\d+(?:\(\+?-?\d+\))?$", line):
            try:
                distance = re.search(r"(\d+)", line).group(1)
                early = re.search(r"([\d\.]+)", lines[i + 2]).group(1)
                mid = re.search(r"([\d\.]+)", lines[i + 4]).group(1)
                late = re.search(r"([\d\.]+)", lines[i + 6]).group(1)
                peak = re.search(r"([\d\.]+)", lines[i + 8]).group(1)
                avg = re.search(r"([\d\.]+)", lines[i + 10]).group(1)

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
        row = {**horses[idx], **metrics[idx]}
        row["horse_key"] = horse_key(row["horse"])
        row["late_vs_mid_delta"] = round(row["late_speed_kmh"] - row["mid_speed_kmh"], 2)
        row["peak_vs_avg_delta"] = round(row["peak_speed_kmh"] - row["avg_speed_kmh"], 2)
        row["fast_finisher_flag"] = row["late_speed_kmh"] > row["mid_speed_kmh"]
        row["sustained_speed_flag"] = row["avg_speed_kmh"] >= 60
        rows.append(row)

    return rows

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
        page = context.new_page()
        page.goto("https://www.racing.com/calendar", wait_until="domcontentloaded", timeout=90000)

    page.bring_to_front()
    page.wait_for_timeout(6000)

    for wanted in ["May 2026", "April 2026", "March 2026"]:
        for _ in range(8):
            body = page.locator("body").inner_text()
            if wanted in body:
                break
            page.mouse.click(70, 326)
            page.wait_for_timeout(3500)

        found = extract_visible_calendar_meetings(page)
        print("MONTH:", wanted, "MEETINGS:", len(found))
        meetings.extend(found)

        if wanted != "March 2026":
            page.mouse.click(70, 326)
            page.wait_for_timeout(3500)

    mdf = pd.DataFrame(meetings).drop_duplicates()

    month_map = {"March 2026": 3, "April 2026": 4, "May 2026": 5}

    if len(mdf):
        mdf["month_num"] = mdf["calendar_month"].map(month_map)
        mdf["race_date"] = mdf.apply(lambda r: f"2026-{int(r['month_num']):02d}-{int(r['day']):02d}", axis=1)
        mdf["track_slug"] = mdf["venue"].apply(slugify_venue)
        mdf = mdf[pd.to_datetime(mdf["race_date"]) <= COMPLETED_CUTOFF]
        mdf = mdf.sort_values(["race_date", "venue"])
        mdf.to_csv(MEETINGS_OUT, index=False)

    url_rows = []

    for _, r in mdf.iterrows():
        for race_no in range(1, 13):
            url_rows.append({
                "race_date": r["race_date"],
                "venue": r["venue"],
                "track_slug": r["track_slug"],
                "race_no": race_no,
                "speed_data_url": f"https://www.racing.com/form/{r['race_date']}/{r['track_slug']}/race/{race_no}/speed-data"
            })

    urls = pd.DataFrame(url_rows)
    urls.to_csv(URLS_OUT, index=False)

    work = context.new_page()

    for idx, r in urls.iterrows():
        url = r["speed_data_url"]

        print("=" * 100)
        print("ATTEMPT:", idx + 1, "/", len(urls))
        print(url)

        try:
            work.goto(url, wait_until="domcontentloaded", timeout=60000)
            rows = parse_sectionals(work)

            if not rows:
                diagnostics.append({
                    "race_date": r["race_date"],
                    "venue": r["venue"],
                    "track": r["track_slug"],
                    "race_no": r["race_no"],
                    "status": "NO_DATA"
                })
                continue

            print("ROWS:", len(rows))

            for row in rows:
                row["race_date"] = r["race_date"]
                row["venue"] = r["venue"]
                row["track"] = r["track_slug"]
                row["race_no"] = int(r["race_no"])
                row["source"] = "RACINGCOM_REAL_VIC_90DAY_V1"
                records.append(row)

            diagnostics.append({
                "race_date": r["race_date"],
                "venue": r["venue"],
                "track": r["track_slug"],
                "race_no": r["race_no"],
                "status": "SUCCESS",
                "rows": len(rows)
            })

            df_live = pd.DataFrame(records)
            if len(df_live):
                df_live = df_live.drop_duplicates(["race_date", "track", "race_no", "horse_key"])
                df_live = df_live.sort_values(["race_date", "track", "race_no", "position"])
                df_live.to_csv(WAREHOUSE_OUT, index=False)

            pd.DataFrame(diagnostics).to_csv(DIAG_OUT, index=False)

        except Exception as e:
            diagnostics.append({
                "race_date": r["race_date"],
                "venue": r["venue"],
                "track": r["track_slug"],
                "race_no": r["race_no"],
                "status": "FAILED",
                "error": repr(e)
            })
            pd.DataFrame(diagnostics).to_csv(DIAG_OUT, index=False)

df = pd.DataFrame(records)

if len(df):
    df = df.drop_duplicates(["race_date", "track", "race_no", "horse_key"])
    df = df.sort_values(["race_date", "track", "race_no", "position"])

df.to_csv(WAREHOUSE_OUT, index=False)
pd.DataFrame(diagnostics).to_csv(DIAG_OUT, index=False)

print("=" * 100)
print("EDGEIQ VIC 90 DAY REAL MEETING SECTIONAL WAREHOUSE")
print("=" * 100)
print("MEETINGS:", len(mdf))
print("URLS:", len(urls))
print("ROWS:", len(df))
print("SAVED:", MEETINGS_OUT)
print("SAVED:", URLS_OUT)
print("SAVED:", WAREHOUSE_OUT)
print("SAVED:", DIAG_OUT)
