from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
WINDOW = DATA / "edgeiq_three_day_window_v1.json"
OUTPUT = DATA / "edgeiq_meetings_summary_feed_v1.json"

def text(value: Any) -> str:
    if value is None:return ""
    value=str(value).replace("\n"," ").strip()
    if value.lower() in {"","-","none","null","undefined","n/a","na","pending"}:return ""
    return re.sub(r"\s+"," ",value)
def first(*values: Any)->str:
    for value in values:
        candidate=text(value)
        if candidate:return candidate
    return ""
def source(obj:dict[str,Any])->dict[str,Any]:return obj.get("source") if isinstance(obj.get("source"),dict) else {}
def scratched(runner:dict[str,Any])->bool:
    official=runner.get("official") if isinstance(runner.get("official"),dict) else {};s=source(runner)
    return official.get("scratched") is True or s.get("scratched") is True or s.get("is_scratched") is True or "scratch" in first(official.get("status"),s.get("status")).lower()
def race_status(race:dict[str,Any])->str:
    s=source(race);raw=first(s.get("race_status"),s.get("result_status"),s.get("full_status"),s.get("meet_status"));upper=raw.upper()
    if "FINAL" in upper:return "Final fields"
    if "ACCEPT" in upper:return "Acceptances"
    if "RESULT" in upper:return "Results"
    if "ABANDON" in upper:return "Abandoned"
    return raw or "Not supplied"
def meeting_status(meeting:dict[str,Any],races:list[dict[str,Any]])->str:
    ms=source(meeting);rs=source(races[0]) if races else {};raw=first(ms.get("FullStatus"),ms.get("MeetStatus"),ms.get("Status"),rs.get("full_status"),rs.get("meet_status"));upper=raw.upper()
    if "ACCEPT" in upper:return "Acceptances"
    if "FINAL" in upper:return "Final fields"
    if "RESULT" in upper:return "Results"
    if "ABANDON" in upper:return "Abandoned"
    return raw or "Not supplied"
def race_time(race:dict[str,Any])->str:
    s=source(race)
    return first(race.get("raceTime"),s.get("race_time"),s.get("race_time_local"),s.get("advertised_time"),s.get("advertisedTime"),s.get("start_time"),s.get("startTime"),s.get("raceStartTime"),s.get("RaceTime")) or "Not supplied"
def restriction(name:str)->str:
    match=re.search(r"(2YO|3YO\+?|Fillies|Mares|Colts|Geldings)",name,flags=re.I);return match.group(0) if match else "Not supplied"
def condition_kind(value:str)->str:
    lower=value.lower()
    if "heavy" in lower:return "heavy"
    if "soft" in lower:return "soft"
    if "good" in lower:return "good"
    return "other"
def track_rating(meeting:dict[str,Any],race:dict[str,Any])->str:
    ms=source(meeting);rs=source(race)
    return first(rs.get("official_track_rating"),ms.get("official_track_rating"),meeting.get("trackCondition"),race.get("trackCondition"),rs.get("track_rating_short"),ms.get("track_rating_short"),rs.get("going"),ms.get("going"),rs.get("track_condition"),ms.get("track_condition"),rs.get("track_rating"),ms.get("track_rating")) or "Not supplied"
def rail_position(meeting:dict[str,Any],race:dict[str,Any])->str:
    ms=source(meeting);rs=source(race)
    return first(meeting.get("rail"),race.get("rail"),rs.get("rail_position"),ms.get("rail_position"),rs.get("railPosition"),ms.get("railPosition"),rs.get("rail"),ms.get("rail"),rs.get("RailPosition"),ms.get("RailPosition")) or "Not supplied"
def weather_value(meeting:dict[str,Any],race:dict[str,Any])->str:
    ms=source(meeting);rs=source(race)
    return first(meeting.get("weather"),ms.get("weather"),rs.get("weather"),ms.get("weather_condition"),rs.get("weather_condition"),ms.get("forecast"),rs.get("forecast")) or "Awaiting Weather Feed"

def main()->int:
    if not CATALOG.exists() or not WINDOW.exists():print("EDGEIQ_MEETINGS_SUMMARY_FEED_V1 FAIL source_missing");return 1
    catalog=json.loads(CATALOG.read_text(encoding="utf-8"));window=json.loads(WINDOW.read_text(encoding="utf-8"));meetings=[m for m in catalog.get("meetings",[]) if isinstance(m,dict)];generated_at=first(catalog.get("generatedAt"),window.get("generatedAt"),datetime.now(timezone.utc).isoformat());days=[];total_meetings=0;total_races=0
    for window_day in window.get("dates",[]):
        if not isinstance(window_day,dict):continue
        date_value=text(window_day.get("date"))[:10];key=text(window_day.get("key"));day_meetings=[]
        for meeting in meetings:
            if text(meeting.get("date"))[:10]!=date_value:continue
            races=sorted([r for r in meeting.get("races",[]) if isinstance(r,dict)],key=lambda r:int(r.get("raceNumber") or 0));first_race=races[0] if races else {};fs=source(first_race);ms=source(meeting)
            track=track_rating(meeting,first_race);rail=rail_position(meeting,first_race);weather=weather_value(meeting,first_race)
            wind_direction=first(fs.get("weather_wind_direction"),ms.get("weather_wind_direction"));wind_speed=first(fs.get("weather_wind_speed"),ms.get("weather_wind_speed"));wind=f"{wind_direction} {wind_speed}".strip() if wind_direction or wind_speed else "Not supplied"
            temp_min=first(fs.get("weather_min"),ms.get("weather_min"));temp_max=first(fs.get("weather_max"),ms.get("weather_max"));temp=f"{temp_min}-{temp_max}" if temp_min and temp_max else temp_max or temp_min or "Not supplied";rain=first(fs.get("rainfall"),fs.get("weather_rain"),ms.get("rainfall"),ms.get("weather_rain")) or "Not supplied";irrigation=first(fs.get("irrigation"),ms.get("irrigation")) or "Not supplied";official_update=first(fs.get("built_at"),ms.get("built_at"),catalog.get("generatedAt")) or "Not supplied"
            race_summaries=[];declared=0;scratches=0
            for race in races:
                runners=[r for r in race.get("runners",[]) if isinstance(r,dict)];declared+=len(runners);scratches+=sum(1 for runner in runners if scratched(runner));race_name=first(race.get("raceName")) or "Unnamed race"
                race_summaries.append({"raceKey":text(race.get("raceKey")),"raceNumber":int(race.get("raceNumber") or 0),"time":race_time(race),"distance":first(race.get("distance")) or "Not supplied","name":race_name,"raceClass":first(race.get("raceClass")) or "Not supplied","restriction":restriction(race_name),"fieldSize":len(runners),"status":race_status(race)})
            day_meetings.append({"meetingKey":text(meeting.get("meetingKey")),"meeting":first(meeting.get("meeting")) or "Unnamed meeting","providerMeetingKey":first(meeting.get("providerMeetingKey")),"date":date_value,"venue":first(ms.get("Venue"),ms.get("venue"),ms.get("Track"),ms.get("track"),meeting.get("providerMeetingKey"),meeting.get("meeting")) or "Not supplied","state":first(ms.get("State"),ms.get("state"),fs.get("state")) or "Not supplied","track":track,"rail":rail,"weather":weather,"wind":wind,"temp":temp,"rain24h":rain,"irrigation24h":irrigation,"officialUpdate":official_update,"races":int(meeting.get("raceCount") or len(races)),"declared":declared,"scratchings":scratches,"first":race_time(races[0]) if races else "Not supplied","last":race_time(races[-1]) if races else "Not supplied","status":meeting_status(meeting,races),"raceSummaries":race_summaries})
        totals={"meetings":len(day_meetings),"races":sum(int(m.get("races") or 0) for m in day_meetings),"declared":sum(int(m.get("declared") or 0) for m in day_meetings),"scratchings":sum(int(m.get("scratchings") or 0) for m in day_meetings),"heavyTracks":sum(1 for m in day_meetings if condition_kind(text(m.get("track")))=="heavy"),"softTracks":sum(1 for m in day_meetings if condition_kind(text(m.get("track")))=="soft"),"goodTracks":sum(1 for m in day_meetings if condition_kind(text(m.get("track")))=="good"),"weatherAlerts":sum(1 for m in day_meetings if text(m.get("weather")) not in {"","Awaiting Weather Feed"})};days.append({"key":key,"date":date_value,"dayOffset":int(window_day.get("dayOffset") or 0),"generatedAt":generated_at,"totals":totals,"meetings":day_meetings});total_meetings+=len(day_meetings);total_races+=totals["races"]
    payload={"schemaVersion":"edgeiq_meetings_summary_feed_v1","timezone":"Australia/Melbourne","generatedAt":generated_at,"sourceCatalog":CATALOG.name,"sourceWindow":WINDOW.name,"purpose":"LIGHTWEIGHT_MEETINGS_ONLY","days":days};OUTPUT.write_text(json.dumps(payload,separators=(",",":"),ensure_ascii=False)+"\n",encoding="utf-8");print("EDGEIQ_MEETINGS_SUMMARY_FEED_V1 PASS");print(f"MEETINGS={total_meetings}");print(f"RACES={total_races}");print(f"BYTES={OUTPUT.stat().st_size}");return 0
if __name__=="__main__":raise SystemExit(main())
