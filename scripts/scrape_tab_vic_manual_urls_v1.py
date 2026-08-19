from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
URLS = DATA / "edgeiq_tab_vic_thoroughbred_urls_v1.csv"
OUT = DATA / "edgeiq_tab_vic_racecards_v1.csv"
SUMMARY = DATA / "edgeiq_tab_vic_racecards_summary_v1.csv"
RAW = DATA / "tab_vic_race_raw_v1"
RAW.mkdir(parents=True, exist_ok=True)

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
            "race_status": payload.get("raceStatus"),
            "odds_update_time": payload.get("oddsUpdateTime"),
            "fixed_odds_update_time": payload.get("fixedOddsUpdateTime"),

            "runner_no": r.get("runnerNumber"),
            "horse": clean(r.get("runnerName")).upper(),
            "barrier": r.get("barrierNumber"),
            "jockey": r.get("riderDriverFullName") or r.get("riderDriverName"),
            "trainer": r.get("trainerFullName") or r.get("trainerName"),
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

            "runner_form_url": links.get("form"),
            "silk_url": r.get("silkURL"),
            "flucs_json": json.dumps(fixed.get("flucs", []), ensure_ascii=False),
            "return_history_json": json.dumps(fixed.get("returnHistory", []), ensure_ascii=False),
            "market_movers_json": json.dumps(tote.get("marketMovers", []), ensure_ascii=False),
            "fast_form_json": json.dumps(r.get("fastForm", []), ensure_ascii=False),
        })

    return rows

urls = pd.read_csv(URLS)

all_rows = []
captured = 0
timeouts = 0
errors = 0

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    for _, t in urls.iterrows():
        url = str(t["tab_frontend_url"])
        date = str(t["meeting_date"])
        venue = str(t["venue_mnemonic"])
        race_type = str(t["race_type"])
        race_no = str(t["race_no"])

        expected = f"/dates/{date}/meetings/{race_type}/{venue}/races/{race_no}"

        print("[vic_harvest] open", url)

        page = browser.new_page(viewport={"width": 1500, "height": 950})

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
                page.goto(url, wait_until="domcontentloaded", timeout=45000)

            resp = resp_info.value
            txt = resp.text()
            payload = json.loads(txt)

            if "runners" not in payload:
                print("[vic_harvest] no runners")
                page.close()
                continue

            m = payload.get("meeting", {}) or {}
            raw_name = f"{m.get('meetingDate')}_{m.get('location')}_{m.get('venueMnemonic')}_R{payload.get('raceNumber')}.json"
            (RAW / raw_name).write_text(txt, encoding="utf-8")

            rows = flatten(payload, resp.url)
            all_rows.extend(rows)
            captured += 1

            temp_df = pd.DataFrame(all_rows)
            if not temp_df.empty:
                temp_df = temp_df.drop_duplicates(subset=["meeting_date", "venue_mnemonic", "race_no", "runner_no"])
                temp_df = temp_df.sort_values(["meeting_name", "race_no", "runner_no"])
            temp_df.to_csv(OUT, index=False)

            temp_summary = pd.DataFrame([{
                "scraped_at": datetime.now().isoformat(timespec="seconds"),
                "target_races": len(urls),
                "captured_races": captured,
                "timeouts": timeouts,
                "errors": errors,
                "runner_rows": len(temp_df),
                "status": "IN_PROGRESS"
            }])
            temp_summary.to_csv(SUMMARY, index=False)

            print("[vic_harvest] CAPTURED", m.get("meetingName"), "R" + str(payload.get("raceNumber")), "runners", len(rows), "saved_rows", len(temp_df))

        except PlaywrightTimeoutError:
            timeouts += 1
            print("[vic_harvest] TIMEOUT", expected)
        except Exception as e:
            errors += 1
            print("[vic_harvest] ERROR", e)

        try:
            page.close()
        except Exception:
            pass

    browser.close()

df = pd.DataFrame(all_rows)

if not df.empty:
    df = df.drop_duplicates(subset=["meeting_date", "venue_mnemonic", "race_no", "runner_no"])
    df = df.sort_values(["meeting_name", "race_no", "runner_no"])

df.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "scraped_at": datetime.now().isoformat(timespec="seconds"),
    "target_races": len(urls),
    "captured_races": captured,
    "timeouts": timeouts,
    "errors": errors,
    "runner_rows": len(df),
}])
summary.to_csv(SUMMARY, index=False)

print("[vic_harvest] captured_races", captured)
print("[vic_harvest] timeouts", timeouts)
print("[vic_harvest] errors", errors)
print("[vic_harvest] runner_rows", len(df))
print("[vic_harvest] wrote", OUT)

if not df.empty:
    print(df[[
        "meeting_name","location","race_no","runner_no","horse",
        "barrier","jockey","trainer","tab_fixed_win",
        "tab_fixed_betting_status","early_speed_band","dfs_form_rating"
    ]].head(120).to_string(index=False))

