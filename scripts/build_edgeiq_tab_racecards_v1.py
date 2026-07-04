from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime
import json
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DEBUG = DATA / "tab_racecards_debug_v1"
RAW = DEBUG / "raw_races"
DEBUG.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)

LINKS = DATA / "tab_page_links_today_racing.json"

OUT_CSV = DATA / "edgeiq_tab_racecards_v1.csv"
OUT_VIC_CSV = DATA / "edgeiq_tab_racecards_vic_v1.csv"
OUT_VIC_R_CSV = DATA / "edgeiq_tab_racecards_vic_thoroughbred_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_tab_racecards_summary_v1.csv"

RACE_API_RE = re.compile(
    r"tab-info-service/racing/dates/([^/]+)/meetings/([^/]+)/([^/]+)/races/(\d+)"
)

FRONTEND_RE = re.compile(
    r"/racing/(\d{4}-\d{2}-\d{2})/([^/]+)/([^/]+)/([RGH])/(\d+)$"
)

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
            "prize_money": payload.get("prizeMoney"),
            "race_status": payload.get("raceStatus"),
            "odds_update_time": payload.get("oddsUpdateTime"),
            "fixed_odds_update_time": payload.get("fixedOddsUpdateTime"),
            "runner_no": r.get("runnerNumber"),
            "horse": clean(r.get("runnerName")).upper(),
            "barrier": r.get("barrierNumber"),
            "trainer": r.get("trainerFullName") or r.get("trainerName"),
            "jockey": r.get("riderDriverFullName") or r.get("riderDriverName"),
            "weight": r.get("handicapWeight"),
            "claim": r.get("claimAmount"),
            "last5": r.get("last5Starts"),
            "tcdw": r.get("tcdwIndicators"),
            "tab_fixed_win": fixed.get("returnWin"),
            "tab_fixed_place": fixed.get("returnPlace"),
            "tab_fixed_open_win": fixed.get("returnWinOpen"),
            "tab_fixed_open_daily_win": fixed.get("returnWinOpenDaily"),
            "tab_fixed_betting_status": fixed.get("bettingStatus"),
            "tab_fixed_percentage_change": fixed.get("percentageChange"),
            "tab_fixed_is_fav_win": fixed.get("isFavouriteWin"),
            "tab_fixed_is_fav_place": fixed.get("isFavouritePlace"),
            "scratched_time": fixed.get("scratchedTime"),
            "tab_win_deduction": fixed.get("winDeduction"),
            "tab_place_deduction": fixed.get("placeDeduction"),
            "tab_tote_win": tote.get("returnWin"),
            "tab_tote_place": tote.get("returnPlace"),
            "tab_tote_betting_status": tote.get("bettingStatus"),
            "tab_tote_percentage_change": tote.get("percentageChange"),
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

links = json.loads(LINKS.read_text(encoding="utf-8"))

targets = []
for x in links:
    href = str(x.get("href", ""))
    text = str(x.get("text", ""))
    m = FRONTEND_RE.search(href)
    if not m:
        continue
    date, _slug, venue, race_type, race_no = m.groups()
    if race_type != "R":
        continue
    targets.append({
        "href": href,
        "text": text.replace("\n", " "),
        "date": date,
        "venue": venue,
        "race_type": race_type,
        "race_no": int(race_no),
    })

targets = targets[:80]
print("[tab_harvester] race_targets", len(targets))

race_payloads = {}
all_rows = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={"width": 1500, "height": 950})

    for i, t in enumerate(targets, start=1):
        print("[tab_harvester] open", i, "/", len(targets), t["text"], t["href"])

        expected = f"/dates/{t['date']}/meetings/{t['race_type']}/{t['venue']}/races/{t['race_no']}"

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
                timeout=25000
            ) as resp_info:
                page.goto(t["href"], wait_until="domcontentloaded", timeout=45000)

            resp = resp_info.value
            txt = resp.text()
            payload = json.loads(txt)

            if "runners" not in payload:
                print("[tab_harvester] no runners in payload")
                continue

            key = resp.url.split("?")[0]
            race_payloads[key] = {"url": resp.url, "payload": payload}

            m = payload.get("meeting", {}) or {}
            name = f"{m.get('meetingDate','')}_{m.get('location','')}_{m.get('raceType','')}_{m.get('venueMnemonic','')}_R{payload.get('raceNumber','')}.json"
            (RAW / name).write_text(txt, encoding="utf-8")

            print(
                "[tab_harvester] captured",
                m.get("meetingName"),
                m.get("location"),
                m.get("raceType"),
                payload.get("raceNumber"),
                "runners",
                len(payload.get("runners", []))
            )

        except PlaywrightTimeoutError:
            print("[tab_harvester] TIMEOUT waiting for race API", expected)
        except Exception as e:
            print("[tab_harvester] ERROR", e)

        page.wait_for_timeout(1500)

    browser.close()

for item in race_payloads.values():
    all_rows.extend(flatten(item["payload"], item["url"]))

df = pd.DataFrame(all_rows)

if not df.empty:
    df = df.drop_duplicates(subset=["meeting_date", "race_type", "venue_mnemonic", "race_no", "runner_no"])
    df = df.sort_values(["meeting_date", "location", "meeting_name", "race_no", "runner_no"])

df.to_csv(OUT_CSV, index=False)

vic = df[df["location"].astype(str).str.upper() == "VIC"].copy() if not df.empty else df.copy()
vic.to_csv(OUT_VIC_CSV, index=False)

vic_r = vic[vic["race_type"].astype(str).str.upper() == "R"].copy() if not vic.empty else vic.copy()
vic_r.to_csv(OUT_VIC_R_CSV, index=False)

summary = pd.DataFrame([{
    "scraped_at": datetime.now().isoformat(timespec="seconds"),
    "race_targets": len(targets),
    "race_payloads": len(race_payloads),
    "runner_rows": len(df),
    "vic_runner_rows": len(vic),
    "vic_thoroughbred_runner_rows": len(vic_r),
}])
summary.to_csv(OUT_SUMMARY, index=False)

print("[tab_harvester] race_payloads", len(race_payloads))
print("[tab_harvester] runner_rows", len(df))
print("[tab_harvester] vic_runner_rows", len(vic))
print("[tab_harvester] vic_thoroughbred_runner_rows", len(vic_r))
print("[tab_harvester] wrote", OUT_CSV)

if not df.empty:
    print(df[[
        "meeting_name","location","race_type","race_no","runner_no","horse",
        "barrier","jockey","trainer","tab_fixed_win","tab_fixed_place",
        "tab_fixed_betting_status","early_speed_band","dfs_form_rating"
    ]].head(80).to_string(index=False))
