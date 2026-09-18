from __future__ import annotations

import csv
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from edgeiq_three_day_window_v1_common import build_three_day_window

csv.field_size_limit(1024 * 1024 * 128)
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_vic_three_day_race_list_v1.csv"
SUMMARY = DATA / "edgeiq_vic_three_day_race_list_v1_summary.csv"
RAW = DATA / "edgeiq_racingcom_three_day_raw_meetings_v1.json"
CALENDAR_URL = "https://www.racing.com/services/appv2/GetMeetsByMonth/{year}/{month}"
THREE_DAY_WINDOW = build_three_day_window()
TARGET_DATES = [datetime.fromisoformat(THREE_DAY_WINDOW.today).date(), datetime.fromisoformat(THREE_DAY_WINDOW.tomorrow).date(), datetime.fromisoformat(THREE_DAY_WINDOW.dayPlus2).date()]
FIELDS = ["race_date","day_bucket","track","normalised_track","meeting_key","meet_code","track_code","meet_status","full_status","state","url_segment","form_url","race_id","race_no","race_name","race_class","distance","race_time_utc","race_status","track_condition","track_rating","rail_position","weather","weather_wind_direction","weather_wind_speed","weather_rain","weather_min","weather_max","rainfall","form_entries_json","source","built_at"]

def clean(value): return "" if value is None else str(value).strip()
def norm_track(value):
    s=clean(value).upper()
    for token in ("SPORTSBET-","SPORTSBET ","LADBROKES ","BET365 ","BET365-","SOUTHSIDE ","PICKLEBET ","PICKLEBET-"): s=s.replace(token,"")
    s=re.sub(r"^PARK\s+","",s); s=s.replace(" SYN"," SYNTHETIC"); s=re.sub(r"\s+"," ",s).strip()
    if "WODONGA" in s:return "WODONGA"
    if "SANDOWN LAKESIDE" in s:return "SANDOWN LAKESIDE"
    if "SANDOWN HILLSIDE" in s:return "SANDOWN HILLSIDE"
    if "BALLARAT" in s and "SYNTHETIC" in s:return "BALLARAT SYNTHETIC"
    if "TRARALGON" in s:return "TRARALGON"
    if s=="MOE":return "MOE"
    if "WARRACKNABEAL" in s:return "WARRACKNABEAL"
    return s

def day_bucket(value):
    try: race_date=datetime.fromisoformat(value[:10]).date()
    except Exception:return ""
    return {0:"TODAY",1:"TOMORROW",2:"DAY+2"}.get((race_date-TARGET_DATES[0]).days,"")

def _decode_json_text(text, url, source):
    text=(text or "").lstrip("\ufeff").strip()
    if not text:
        raise RuntimeError(f"RACING_COM_EMPTY_RESPONSE source={source} url={url}")
    try:
        payload=json.loads(text)
    except json.JSONDecodeError as exc:
        preview=re.sub(r"\s+"," ",text[:240])
        raise RuntimeError(f"RACING_COM_NON_JSON_RESPONSE source={source} url={url} preview={preview!r}") from exc
    if not isinstance(payload,dict):
        raise RuntimeError(f"RACING_COM_UNEXPECTED_JSON source={source} url={url} type={type(payload).__name__}")
    return payload

def fetch_json(url):
    headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153.0.0.0 Safari/537.36","Accept":"application/json,text/plain,*/*","Referer":"https://www.racing.com/calendar","Origin":"https://www.racing.com"}
    urllib_error=None
    for attempt in range(3):
        try:
            request=Request(url,headers=headers)
            with urlopen(request,timeout=30) as response:
                return _decode_json_text(response.read().decode("utf-8",errors="replace"),url,f"urllib_attempt_{attempt+1}")
        except Exception as exc:
            urllib_error=exc
            if attempt<2: time.sleep(2*(attempt+1))
    try: from playwright.sync_api import sync_playwright
    except Exception: raise urllib_error
    last_error=urllib_error
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True)
        context=browser.new_context(user_agent=headers["User-Agent"],extra_http_headers={"Accept":headers["Accept"],"Referer":headers["Referer"]})
        page=context.new_page()
        try:
            # Establish first-party cookies/session before requesting the service endpoint.
            try: page.goto("https://www.racing.com/calendar",wait_until="domcontentloaded",timeout=45000); page.wait_for_timeout(1500)
            except Exception: pass
            for attempt in range(3):
                try:
                    response=context.request.get(url,headers={"Accept":headers["Accept"],"Referer":headers["Referer"]},timeout=45000)
                    if not response.ok:
                        raise RuntimeError(f"RACING_COM_CALENDAR_HTTP_{response.status}: {url}")
                    return _decode_json_text(response.text(),url,f"playwright_request_attempt_{attempt+1}")
                except Exception as exc:
                    last_error=exc
                    if attempt<2: page.wait_for_timeout(2000*(attempt+1))
        finally:
            context.close(); browser.close()
    raise RuntimeError(f"RACING_COM_CALENDAR_FETCH_FAILED: {url}: {last_error}") from last_error

def month_targets():
    keys=[]
    for item in TARGET_DATES:
        key=(item.year,item.month)
        if key not in keys:keys.append(key)
    return keys

def extract_calendar_meetings():
    all_entries=[]
    for year,month in month_targets():
        url=CALENDAR_URL.format(year=year,month=month); all_entries.append({"url":url,"payload":fetch_json(url)})
    RAW.write_text(json.dumps(all_entries,indent=2),encoding="utf-8")
    wanted={}
    for bundle in all_entries:
        for month in (bundle["payload"].get("Months") or []):
            for entry in (month.get("CalendarEntries") or []):
                state=clean(entry.get("State")).upper()
                if state!="VIC" or entry.get("IsTrial") or entry.get("IsJumpout"):continue
                race_date=clean(entry.get("Date"))[:10]; bucket=day_bucket(race_date)
                if bucket not in {"TODAY","TOMORROW","DAY+2"}:continue
                meet_code=clean(entry.get("MeetCode")); url_segment=clean(entry.get("UrlSegment"))
                if not (meet_code or url_segment):continue
                track_raw=clean(entry.get("Track") or entry.get("Venue")); track=norm_track(track_raw); key=f"{race_date}_{track}"
                wanted[key]={"race_date":race_date,"day_bucket":bucket,"track":track_raw,"normalised_track":track,"meeting_key":key,"meet_code":meet_code,"track_code":clean(entry.get("TrackCode")),"meet_status":clean(entry.get("MeetStatus")),"full_status":clean(entry.get("FullStatus")),"state":state,"url_segment":url_segment,"form_url":"https://www.racing.com/form/"+url_segment if url_segment else ""}
    return list(wanted.values())

def gql_url_for_race_list(meet_code):
    query="""query getRaceNumberList_CD($meetCode: ID!) { getNoCacheRacesForMeet(meetCode: $meetCode) { id raceNumber raceStatus distance time name nameForm trackCondition trackRating rdcClass isTrial isJumpOut trackCode formRaceEntries { horseName } meet { venue meetUrl meetUrlSegment } } }"""
    import urllib.parse
    return "https://graphql.rmdprod.racing.com/?"+urllib.parse.urlencode({"query":query,"variables":json.dumps({"meetCode":str(meet_code)})})

def _extract_page_meeting_metadata(page):
    """Read official rail/rating from rendered Racing.com form page when GraphQL race list omits it."""
    try:
        body=page.locator("body").inner_text(timeout=10000)
    except Exception:
        return {}
    meta={}
    # Racing.com labels vary slightly; capture the displayed official values.
    patterns={
        # Racing.com currently renders the label and value on separate lines:
        # "Track Rail\\nTrue Entire Circuit". Keep alternatives for older markup.
        "rail_position":[
            r"(?im)\\bTrack\\s+Rail\\s*[:\\-]?\\s*\\n?\\s*([^\\n|]+)",
            r"(?im)\\bRail(?: Position)?\\s*[:\\-]?\\s*\\n?\\s*([^\\n|]+)",
        ],
        "track_rating":[
            r"(?im)\\b((?:Firm|Good|Soft|Heavy)\\s*\\d+|Synthetic)\\b",
        ],
    }
    for key, pats in patterns.items():
        for pat in pats:
            m=re.search(pat,body)
            if m:
                value=clean(m.group(1))
                if value:
                    meta[key]=value
                    break
    return meta

def fetch_races_browser(meetings):
    try: from playwright.sync_api import sync_playwright
    except Exception as exc: raise SystemExit(f"PLAYWRIGHT_NOT_AVAILABLE: {exc}")
    rows=[]; built_at=datetime.now(timezone.utc).isoformat(timespec="seconds")
    def merge_race(base_race,detailed_race):
        if not isinstance(detailed_race,dict):return base_race
        merged=dict(base_race)
        for key,value in detailed_race.items():
            if value not in (None,"",[]):merged[key]=value
        venue=detailed_race.get("venue")
        if isinstance(venue,dict) and not merged.get("meet"):merged["meet"]={"venue":venue.get("venueName")}
        return merged
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True); context=browser.new_context(user_agent="Mozilla/5.0",viewport={"width":1280,"height":900})
        for meeting in meetings:
            race_list_payloads=[]; race_form_payloads={}
            def store_detail(detail):
                if not isinstance(detail,dict) or not detail.get("formRaceEntries"):return
                for key in {clean(detail.get("id")),clean(detail.get("raceCode")),clean(detail.get("raceNumber"))}:
                    if key:race_form_payloads[key]=detail
            def handle_response(response):
                if "graphql.rmdprod.racing.com" not in response.url:return
                try:
                    data_obj=(json.loads(response.text()).get("data") or {}); races=data_obj.get("getNoCacheRacesForMeet") or []
                    if races:race_list_payloads.append(races)
                    store_detail(data_obj.get("getRaceForm"))
                except Exception:pass
            if meeting.get("form_url"):
                page=context.new_page(); page.on("response",handle_response)
                try:
                    page.goto(meeting["form_url"],wait_until="domcontentloaded",timeout=45000); page.wait_for_timeout(8000)
                    meeting.update(_extract_page_meeting_metadata(page))
                except Exception:pass
                page.close()
            races=race_list_payloads[-1] if race_list_payloads else []
            if not races and meeting.get("meet_code"):
                page=context.new_page()
                try:
                    page.goto(gql_url_for_race_list(meeting["meet_code"]),wait_until="networkidle",timeout=45000); body=page.locator("body").inner_text(timeout=10000); races=((json.loads(body).get("data") or {}).get("getNoCacheRacesForMeet") or [])
                except Exception:races=[]
                page.close()
            def capture_race_detail(race_no_value):
                if not meeting.get("form_url"):return
                detail_page=context.new_page()
                def handle_detail_response(response):
                    if "graphql.rmdprod.racing.com" not in response.url:return
                    try:store_detail((json.loads(response.text()).get("data") or {}).get("getRaceForm"))
                    except Exception:pass
                detail_page.on("response",handle_detail_response)
                try:detail_page.goto(f"{meeting['form_url']}/race/{race_no_value}",wait_until="domcontentloaded",timeout=45000); detail_page.wait_for_timeout(6000)
                except Exception:pass
                detail_page.close()
            for race in races:
                race_no_value=clean(race.get("raceNumber"))
                if race_no_value and not (race_form_payloads.get(clean(race.get("id"))) or race_form_payloads.get(race_no_value)):capture_race_detail(race_no_value)
            for race in races:
                if race.get("isTrial") or race.get("isJumpOut"):continue
                race_no_value=clean(race.get("raceNumber"))
                if not race_no_value:continue
                detailed=race_form_payloads.get(clean(race.get("id"))) or race_form_payloads.get(race_no_value); merged=merge_race(race,detailed); entries=merged.get("formRaceEntries") or []
                rows.append({**meeting,"race_id":clean(merged.get("id")),"race_no":race_no_value,"race_name":clean(merged.get("name")),"race_class":clean(merged.get("rdcClass") or merged.get("class") or merged.get("nameForm")),"distance":clean(merged.get("distance")),"race_time_utc":clean(merged.get("time")),"race_status":clean(merged.get("raceStatus") or merged.get("status")),"track_condition":clean(merged.get("trackCondition") or merged.get("condition")),"track_rating":clean(merged.get("trackRating") or meeting.get("track_rating")),"rail_position":clean(merged.get("railPosition") or merged.get("rail") or merged.get("rail_position") or meeting.get("rail_position")),"weather":"","weather_wind_direction":"","weather_wind_speed":"","weather_rain":"","weather_min":"","weather_max":"","rainfall":"","form_entries_json":json.dumps(entries,ensure_ascii=False),"source":"RACING_COM_GETMEETSBYMONTH_PLUS_GETRACEFORM_COMPLETE","built_at":built_at})
        context.close(); browser.close()
    return rows

def write_csv(path,rows,fields):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8-sig",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=fields,extrasaction="ignore"); writer.writeheader(); writer.writerows(rows)

def main():
    meetings=extract_calendar_meetings(); rows=fetch_races_browser(meetings)
    rows.sort(key=lambda row:({"TODAY":0,"TOMORROW":1,"DAY+2":2}.get(row.get("day_bucket",""),9),row.get("race_date",""),row.get("normalised_track",""),int(row.get("race_no") or 999)))
    write_csv(OUT,rows,FIELDS)
    today_meeting_keys={row["meeting_key"] for row in rows if row.get("day_bucket")=="TODAY"}
    summary=[{"metric":"status","value":"EDGEIQ_VIC_THREE_DAY_RACE_LIST_V1_BUILT"},{"metric":"meetings","value":len(meetings)},{"metric":"races","value":len(rows)},{"metric":"meetings_with_races","value":len({row["meeting_key"] for row in rows})},{"metric":"today_meetings_with_races","value":len(today_meeting_keys)},{"metric":"today_races","value":sum(1 for row in rows if row.get("day_bucket")=="TODAY")},{"metric":"output","value":str(OUT)},{"metric":"built_at","value":datetime.now(timezone.utc).isoformat(timespec="seconds")}]
    write_csv(SUMMARY,summary,["metric","value"])
    print("[EDGEIQ_VIC_THREE_DAY_RACE_LIST_V1] COMPLETE")
    print("meetings=",len(meetings)); print("races=",len(rows)); print("meetings_with_races=",len({row["meeting_key"] for row in rows})); print("today_meetings_with_races=",len(today_meeting_keys)); print("today_races=",sum(1 for row in rows if row.get("day_bucket")=="TODAY")); print("out=",OUT); print("summary=",SUMMARY)

if __name__=="__main__":main()
