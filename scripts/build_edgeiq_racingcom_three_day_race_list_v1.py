from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_vic_three_day_race_list_v1.csv"
SUMMARY = DATA / "edgeiq_vic_three_day_race_list_v1_summary.csv"
RAW = DATA / "edgeiq_racingcom_three_day_raw_meetings_v1.json"

CALENDAR_URL = "https://www.racing.com/services/appv2/GetMeetsByMonth/{year}/{month}"

FIELDS = [
    "race_date","day_bucket","track","normalised_track","meeting_key",
    "meet_code","track_code","meet_status","full_status","url_segment","form_url",
    "race_id","race_no","race_name","race_class","distance","race_time_utc",
    "race_status","track_condition","track_rating","rail_position",
    "weather","weather_wind_direction","weather_wind_speed","weather_rain",
    "weather_min","weather_max","rainfall","source","built_at"
]

def clean(v):
    return "" if v is None else str(v).strip()

def norm_track(v):
    s = clean(v).upper()
    for x in ["SPORTSBET-", "SPORTSBET ", "LADBROKES ", "BET365 ", "BET365-", "SOUTHSIDE "]:
        s = s.replace(x, "")
    s = s.replace(" SYN", " SYNTHETIC")
    s = re.sub(r"\s+", " ", s).strip()
    if "SANDOWN LAKESIDE" in s:
        return "SANDOWN LAKESIDE"
    if "SANDOWN HILLSIDE" in s:
        return "SANDOWN HILLSIDE"
    if "BALLARAT" in s and "SYNTHETIC" in s:
        return "BALLARAT SYNTHETIC"
    if "TRARALGON" in s:
        return "TRARALGON"
    if s == "MOE":
        return "MOE"
    if "WARRACKNABEAL" in s:
        return "WARRACKNABEAL"
    return s

def day_bucket(d):
    today = datetime.now().date()
    try:
        dd = datetime.fromisoformat(d[:10]).date()
    except Exception:
        return ""
    delta = (dd - today).days
    if delta == 0:
        return "TODAY"
    if delta == 1:
        return "TOMORROW"
    if delta == 2:
        return "DAY+2"
    return ""

def fetch_json(url):
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json,text/html,*/*",
        "Referer": "https://www.racing.com/calendar",
    })
    with urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))

def month_targets():
    today = datetime.now().date()
    days = [today, today + timedelta(days=1), today + timedelta(days=2)]
    keys = []
    for d in days:
        key = (d.year, d.month)
        if key not in keys:
            keys.append(key)
    return keys

def extract_calendar_meetings():
    all_entries = []
    for y, m in month_targets():
        url = CALENDAR_URL.format(year=y, month=m)
        payload = fetch_json(url)
        all_entries.append({"url": url, "payload": payload})

    RAW.write_text(json.dumps(all_entries, indent=2), encoding="utf-8")

    wanted = {}
    for bundle in all_entries:
        payload = bundle["payload"]
        months = payload.get("Months") or []
        for month in months:
            entries = month.get("CalendarEntries") or []
            for e in entries:
                state = clean(e.get("State")).upper()
                if state != "VIC":
                    continue
                if e.get("IsTrial") or e.get("IsJumpout"):
                    continue
                if not e.get("HasRaceInformation"):
                    continue
                race_date = clean(e.get("Date"))[:10]
                bucket = day_bucket(race_date)
                if bucket not in {"TODAY","TOMORROW","DAY+2"}:
                    continue

                track = norm_track(e.get("Track") or e.get("Venue"))
                key = f"{race_date}_{track}"
                wanted[key] = {
                    "race_date": race_date,
                    "day_bucket": bucket,
                    "track": clean(e.get("Track") or e.get("Venue")),
                    "normalised_track": track,
                    "meeting_key": key,
                    "meet_code": clean(e.get("MeetCode")),
                    "track_code": clean(e.get("TrackCode")),
                    "meet_status": clean(e.get("MeetStatus")),
                    "full_status": clean(e.get("FullStatus")),
                    "url_segment": clean(e.get("UrlSegment")),
                    "form_url": "https://www.racing.com/form/" + clean(e.get("UrlSegment")),
                }
    return list(wanted.values())

def gql_url_for_race_list(meet_code):
    query = """
query getRaceNumberList_CD($meetCode: ID!) {
  getNoCacheRacesForMeet(meetCode: $meetCode) {
    id
    raceNumber
    raceStatus
    distance
    time
    name
    nameForm
    trackCondition
    trackRating
    rdcClass
    isTrial
    isJumpOut
    trackCode
    formRaceEntries { horseName }
    meet {
      venue
      meetUrl
      meetUrlSegment
    }
  }
}
"""
    import urllib.parse
    return "https://graphql.rmdprod.racing.com/?" + urllib.parse.urlencode({
        "query": query,
        "variables": json.dumps({"meetCode": str(meet_code)}),
    })

def fetch_races_browser(meetings):
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise SystemExit(f"PLAYWRIGHT_NOT_AVAILABLE: {e}")

    rows = []
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0",
            viewport={"width": 1280, "height": 900},
        )

        for m in meetings:
            page = context.new_page()
            payloads = []

            def handle_response(resp):
                if "graphql.rmdprod.racing.com" not in resp.url:
                    return
                if "getRaceNumberList_CD" not in resp.url and "getNoCacheRacesForMeet" not in resp.url:
                    return
                try:
                    txt = resp.text()
                    data = json.loads(txt)
                    races = ((data.get("data") or {}).get("getNoCacheRacesForMeet") or [])
                    if races:
                        payloads.append(races)
                except Exception:
                    pass

            page.on("response", handle_response)
            try:
                page.goto(m["form_url"], wait_until="networkidle", timeout=45000)
                page.wait_for_timeout(3000)
            except Exception:
                pass
            page.close()

            races = payloads[-1] if payloads else []

            if not races and m.get("meet_code"):
                page = context.new_page()
                try:
                    page.goto(gql_url_for_race_list(m["meet_code"]), wait_until="networkidle", timeout=45000)
                    body = page.locator("body").inner_text(timeout=10000)
                    data = json.loads(body)
                    races = ((data.get("data") or {}).get("getNoCacheRacesForMeet") or [])
                except Exception:
                    races = []
                page.close()

            for r in races:
                if r.get("isTrial") or r.get("isJumpOut"):
                    continue
                race_no = clean(r.get("raceNumber"))
                if not race_no:
                    continue
                rows.append({
                    **m,
                    "race_id": clean(r.get("id")),
                    "race_no": race_no,
                    "race_name": clean(r.get("name")),
                    "race_class": clean(r.get("rdcClass") or r.get("nameForm")),
                    "distance": clean(r.get("distance")),
                    "race_time_utc": clean(r.get("time")),
                    "race_status": clean(r.get("raceStatus")),
                    "track_condition": clean(r.get("trackCondition")),
                    "track_rating": clean(r.get("trackRating")),
                    "rail_position": "",
                    "weather": "",
                    "weather_wind_direction": "",
                    "weather_wind_speed": "",
                    "weather_rain": "",
                    "weather_min": "",
                    "weather_max": "",
                    "rainfall": "",
                    "source": "RACING_COM_GETMEETSBYMONTH_PLUS_GETRACENUMBERLIST",
                    "built_at": built_at,
                })

        context.close()
        browser.close()

    return rows

def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

def main():
    meetings = extract_calendar_meetings()
    rows = fetch_races_browser(meetings)

    rows.sort(key=lambda r: (
        {"TODAY":0,"TOMORROW":1,"DAY+2":2}.get(r.get("day_bucket",""), 9),
        r.get("race_date",""),
        r.get("normalised_track",""),
        int(r.get("race_no") or 999)
    ))

    write_csv(OUT, rows, FIELDS)

    summary = [
        {"metric":"status","value":"EDGEIQ_VIC_THREE_DAY_RACE_LIST_V1_BUILT"},
        {"metric":"meetings","value":len(meetings)},
        {"metric":"races","value":len(rows)},
        {"metric":"meetings_with_races","value":len(set(r["meeting_key"] for r in rows))},
        {"metric":"output","value":str(OUT)},
        {"metric":"built_at","value":datetime.now(timezone.utc).isoformat(timespec="seconds")},
    ]
    write_csv(SUMMARY, summary, ["metric","value"])

    print("[EDGEIQ_VIC_THREE_DAY_RACE_LIST_V1] COMPLETE")
    print("meetings=", len(meetings))
    print("races=", len(rows))
    print("meetings_with_races=", len(set(r["meeting_key"] for r in rows)))
    print("out=", OUT)
    print("summary=", SUMMARY)

if __name__ == "__main__":
    main()
