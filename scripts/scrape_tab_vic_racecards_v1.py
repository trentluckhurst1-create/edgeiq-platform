from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime
import argparse
import json
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
RAW = DATA / "tab_vic_race_raw_v1"
RAW.mkdir(parents=True, exist_ok=True)

LINKS = DATA / "tab_page_links_today_racing.json"
OUT = DATA / "edgeiq_tab_vic_racecards_v1.csv"
SUMMARY = DATA / "edgeiq_tab_vic_racecards_summary_v1.csv"

FRONTEND_RE = re.compile(r"/racing/(\d{4}-\d{2}-\d{2})/([^/]+)/([^/]+)/([RGH])/(\d+)$")

def clean(x):
    return "" if x is None else str(x).strip()

def flatten(payload, api_url):
    rows = []
    m = payload.get("meeting", {}) or {}

    for r in payload.get("runners", []) or []:
        fixed = r.get("fixedOdds", {}) or {}
        tote = r.get("parimutuel", {}) or {}
        links = r.get("_links", {}) or {}

        rows.append({
            "scraped_at": datetime.now().isoformat(timespec="seconds"),
            "source": "TAB",
            "api_url": api_url,
            "meeting_date": m.get("meetingDate"),
            "location": m.get("location"),
            "meeting_name": m.get("meetingName"),
            "venue_mnemonic": m.get("venueMnemonic"),
            "race_type": m.get("raceType"),
            "race_no": payload.get("raceNumber"),
            "race_name": payload.get("raceName"),
            "race_distance": payload.get("raceDistance"),
            "race_start_time_utc": payload.get("raceStartTime"),
            "race_class_conditions": payload.get("raceClassConditions"),
            "track_condition": m.get("trackCondition"),
            "weather_condition": m.get("weatherCondition"),
            "track_direction": payload.get("trackDirection"),
            "race_status": payload.get("raceStatus"),
            "runner_no": r.get("runnerNumber"),
            "horse": clean(r.get("runnerName")).upper(),
            "barrier": r.get("barrierNumber"),
            "jockey": r.get("riderDriverFullName") or r.get("riderDriverName"),
            "trainer": r.get("trainerFullName") or r.get("trainerName"),
            "weight": r.get("handicapWeight"),
            "claim": r.get("claimAmount"),
            "last5": r.get("last5Starts"),
            "tab_fixed_win": fixed.get("returnWin"),
            "tab_fixed_place": fixed.get("returnPlace"),
            "tab_fixed_open_win": fixed.get("returnWinOpen"),
            "tab_fixed_betting_status": fixed.get("bettingStatus"),
            "scratched_time": fixed.get("scratchedTime"),
            "tab_tote_win": tote.get("returnWin"),
            "tab_tote_place": tote.get("returnPlace"),
            "tab_tote_betting_status": tote.get("bettingStatus"),
            "early_speed_rating": r.get("earlySpeedRating"),
            "early_speed_band": r.get("earlySpeedRatingBand"),
            "dfs_form_rating": r.get("dfsFormRating"),
            "tech_form_rating": r.get("techFormRating"),
            "total_rating_points": r.get("totalRatingPoints"),
            "silk_url": r.get("silkURL"),
            "runner_form_url": links.get("form"),
            "flucs_json": json.dumps(fixed.get("flucs", []), ensure_ascii=False),
            "return_history_json": json.dumps(fixed.get("returnHistory", []), ensure_ascii=False),
            "market_movers_json": json.dumps(tote.get("marketMovers", []), ensure_ascii=False),
            "fast_form_json": json.dumps(r.get("fastForm", []), ensure_ascii=False),
        })

    return rows

ap = argparse.ArgumentParser()
ap.add_argument("--include-non-thoroughbred", action="store_true")
ap.add_argument("--max-races", type=int, default=40)
args = ap.parse_args()

if not LINKS.exists():
    raise SystemExit("Missing tab_page_links_today_racing.json. Run discover_tab_frontend_race_links_v1.py first.")

links = json.loads(LINKS.read_text(encoding="utf-8"))

targets = []
for x in links:
    href = str(x.get("href", ""))
    text = str(x.get("text", "")).replace("\n", " ")

    m = FRONTEND_RE.search(href)
    if not m:
        continue

    date, slug, venue, race_type, race_no = m.groups()

    if "(VIC)" not in text.upper():
        continue

    if not args.include_non_thoroughbred and race_type != "R":
        continue

    targets.append({
        "url": href,
        "text": text,
        "date": date,
        "venue": venue,
        "race_type": race_type,
        "race_no": race_no,
    })

targets = targets[:args.max_races]

print("[tab_vic_multi] vic_targets", len(targets))
for t in targets:
    print("[tab_vic_multi] target", t["text"], t["url"])

all_rows = []
captured = 0

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={"width": 1500, "height": 950})

    for i, t in enumerate(targets, start=1):
        expected = f"/dates/{t['date']}/meetings/{t['race_type']}/{t['venue']}/races/{t['race_no']}"

        print("[tab_vic_multi] open", i, "/", len(targets), t["url"])

        try:
            with page.expect_response(
                lambda r, expected=expected: (
                    expected in r.url
                    and "api.beta.tab.com.au" in r.url
                    and "/form/" not in r.url
                    and "/pools/" not in r.url
                    and "/silk/" not in r.url
                    and r.status == 200
                ),
                timeout=45000
            ) as resp_info:
                page.goto(t["url"], wait_until="domcontentloaded", timeout=45000)

            resp = resp_info.value
            txt = resp.text()
            payload = json.loads(txt)

            if "runners" not in payload:
                print("[tab_vic_multi] skipped: no runners")
                continue

            m = payload.get("meeting", {}) or {}
            raw_name = f"{m.get('meetingDate')}_{m.get('location')}_{m.get('raceType')}_{m.get('venueMnemonic')}_R{payload.get('raceNumber')}.json"
            (RAW / raw_name).write_text(txt, encoding="utf-8")

            rows = flatten(payload, resp.url)
            all_rows.extend(rows)
            captured += 1

            print(
                "[tab_vic_multi] captured",
                m.get("meetingName"),
                m.get("location"),
                m.get("raceType"),
                payload.get("raceNumber"),
                "runners",
                len(rows)
            )

        except PlaywrightTimeoutError:
            print("[tab_vic_multi] TIMEOUT", expected)
        except Exception as e:
            print("[tab_vic_multi] ERROR", e)

        page.wait_for_timeout(1500)

    browser.close()

df = pd.DataFrame(all_rows)

if not df.empty:
    df = df.drop_duplicates(subset=["meeting_date", "race_type", "venue_mnemonic", "race_no", "runner_no"])
    df = df.sort_values(["meeting_date", "meeting_name", "race_no", "runner_no"])

df.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "scraped_at": datetime.now().isoformat(timespec="seconds"),
    "vic_targets": len(targets),
    "captured_races": captured,
    "runner_rows": len(df),
    "thoroughbred_only": not args.include_non_thoroughbred,
    "output": str(OUT),
}])
summary.to_csv(SUMMARY, index=False)

print("[tab_vic_multi] captured_races", captured)
print("[tab_vic_multi] runner_rows", len(df))
print("[tab_vic_multi] wrote", OUT)
print("[tab_vic_multi] wrote", SUMMARY)

if not df.empty:
    print(df[[
        "meeting_name","location","race_type","race_no","runner_no","horse",
        "barrier","jockey","trainer","tab_fixed_win","tab_fixed_betting_status",
        "early_speed_band","dfs_form_rating"
    ]].head(80).to_string(index=False))
