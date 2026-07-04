from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import json
import pandas as pd
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "public" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RAW_OUT = OUT_DIR / "tab_next_to_go_full.json"
CSV_ALL = OUT_DIR / "edgeiq_tab_next_to_go_all_v1.csv"
CSV_VIC = OUT_DIR / "edgeiq_tab_next_to_go_vic_v1.csv"
CSV_VIC_R = OUT_DIR / "edgeiq_tab_next_to_go_vic_thoroughbred_v1.csv"

URL_PART = "tab-info-service/racing/next-to-go/races"

def flatten(data):
    rows = []
    for r in data.get("races", []):
        m = r.get("meeting", {}) or {}
        links = r.get("_links", {}) or {}
        rows.append({
            "scraped_at": datetime.now().isoformat(timespec="seconds"),
            "source": "TAB",
            "race_start_time_utc": r.get("raceStartTime"),
            "race_no": r.get("raceNumber"),
            "race_name": r.get("raceName"),
            "race_distance": r.get("raceDistance"),
            "broadcast_channel": r.get("broadcastChannel"),
            "race_type": m.get("raceType"),
            "meeting_name": m.get("meetingName"),
            "location": m.get("location"),
            "venue_mnemonic": m.get("venueMnemonic"),
            "meeting_date": m.get("meetingDate"),
            "track_condition": m.get("trackCondition"),
            "weather_condition": m.get("weatherCondition"),
            "rail_position": m.get("railPosition"),
            "race_details_url": links.get("self"),
            "race_form_url": links.get("form"),
            "big_bets_url": links.get("bigBets"),
        })
    return pd.DataFrame(rows)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    print("[tab_next_to_go] capturing TAB next-to-go feed")

    try:
        with page.expect_response(lambda r: URL_PART in r.url and r.status == 200, timeout=60000) as resp_info:
            page.goto(
                "https://www.tab.com.au/racing/meetings/today/R",
                wait_until="domcontentloaded",
                timeout=30000
            )

        resp = resp_info.value
        body = resp.text()
        RAW_OUT.write_text(body, encoding="utf-8")

        print("[tab_next_to_go] found", resp.url)
        print("[tab_next_to_go] raw_bytes", len(body))

    except PlaywrightTimeoutError:
        print("[tab_next_to_go] ERROR: next-to-go response not captured")
        browser.close()
        raise SystemExit(1)

    browser.close()

data = json.loads(RAW_OUT.read_text(encoding="utf-8"))
df = flatten(data)

if not df.empty:
    df = df.sort_values(["race_start_time_utc", "location", "meeting_name", "race_no"])

df.to_csv(CSV_ALL, index=False)

vic = df[df["location"].astype(str).str.upper() == "VIC"].copy()
vic.to_csv(CSV_VIC, index=False)

vic_r = vic[vic["race_type"].astype(str).str.upper() == "R"].copy()
vic_r.to_csv(CSV_VIC_R, index=False)

print("[tab_next_to_go] all_rows", len(df))
print("[tab_next_to_go] vic_rows", len(vic))
print("[tab_next_to_go] vic_thoroughbred_rows", len(vic_r))
print("[tab_next_to_go] wrote", CSV_ALL)
print("[tab_next_to_go] wrote", CSV_VIC)
print("[tab_next_to_go] wrote", CSV_VIC_R)

if len(vic):
    print(vic[["race_start_time_utc","meeting_name","race_type","race_no","race_name","venue_mnemonic"]].to_string(index=False))
