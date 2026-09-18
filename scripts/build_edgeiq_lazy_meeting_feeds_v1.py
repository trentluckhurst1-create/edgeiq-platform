from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
RA_TRACK = DATA / "edgeiq_racing_australia_track_conditions_v1.json"
SUMMARY = DATA / "edgeiq_meetings_summary_feed_v1.json"
MEETINGS_DIR = DATA / "meetings"


def text(value, fallback="Not supplied"):
    if value is None:
        return fallback
    value = str(value).strip()
    return value if value else fallback


def slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value or "meeting"


def source_value(source, *keys):
    if not isinstance(source, dict): return None
    lowered = {str(k).lower(): k for k in source}
    for key in keys:
        actual = key if key in source else lowered.get(key.lower())
        if actual is not None and source.get(actual) not in (None, ""):
            return source.get(actual)
    return None


def canonical_track(value) -> str:
    raw = text(value, "").upper()
    for prefix in ("LADBROKES ","SPORTSBET-","SPORTSBET ","BET365 ","BETDELUXE ","PICKLEBET PARK "):
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
            break
    aliases = {"CAULFIELD HEATH":"CAULFIELD","SANDOWN HILLSIDE":"SANDOWN","SANDOWN LAKESIDE":"SANDOWN","LADBROKES PARK":"SANDOWN","LADBROKES PARK HILLSIDE":"SANDOWN","LADBROKES PARK LAKESIDE":"SANDOWN","BALLARAT SYNTHETIC":"BALLARAT","SPORTSBET-BALLARAT SYNTHETIC":"BALLARAT","GEELONG SYNTHETIC":"GEELONG","PAKENHAM SYNTHETIC":"PAKENHAM","SOUTHSIDE PAKENHAM SYNTHETIC":"PAKENHAM","BELMONT PARK":"BELMONT"}
    return aliases.get(raw, raw).replace(" ", "_")

def main() -> None:
    if not CATALOG.exists(): raise SystemExit(f"Missing catalogue: {CATALOG}")
    catalog = json.loads(CATALOG.read_text(encoding="utf-8-sig"))
    meetings = catalog.get("meetings") or []
    ra_payload = json.loads(RA_TRACK.read_text(encoding="utf-8-sig")) if RA_TRACK.exists() else {"records":[]}
    ra_index = {(text(r.get("race_date"),""), canonical_track(r.get("meeting_display"))): r for r in ra_payload.get("records",[])}
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    day_labels = catalog.get("dayLabels") or {}
    dates = catalog.get("dates") or []
    MEETINGS_DIR.mkdir(parents=True, exist_ok=True)
    days = []
    for date_value in dates[:3]:
        day_meetings = []
        for meeting in meetings:
            if meeting.get("date") != date_value: continue
            meeting_key = text(meeting.get("meetingKey"), "")
            meeting_name = text(meeting.get("meeting"), "")
            meeting_source = meeting.get("source") or {}
            official = ra_index.get((date_value, canonical_track(meeting_name)), {})
            race_summaries = []
            declared = 0
            for race in meeting.get("races") or []:
                race_source = race.get("source") or {}
                runners = race.get("runners") or []
                declared += len(runners)
                race_summaries.append({"raceKey":text(race.get("raceKey"),""),"raceNumber":int(race.get("raceNumber") or 0),"time":text(race.get("raceTime")),"distance":text(race.get("distance")),"name":text(race.get("raceName")),"raceClass":text(race.get("raceClass")),"restriction":text(source_value(race_source,"restriction")),"fieldSize":len(runners),"status":text(source_value(race_source,"raceStatus","race_status","status"))})
            state = text(source_value(meeting_source,"State","state"),"VIC")
            scratches = int(source_value(meeting_source,"scratchings","scratchingCount") or 0)
            row={"meetingKey":meeting_key,"meeting":meeting_name,"venue":meeting_name,"providerMeetingKey":text(meeting.get("providerMeetingKey"),""),"date":date_value,"state":state,"track":text(official.get("track_condition")) if official else text(meeting.get("trackCondition")),"rail":text(official.get("rail")) if official else text(meeting.get("rail")),"weather":text(source_value(meeting_source,"weather"),"Awaiting Weather Feed"),"wind":text(source_value(meeting_source,"wind")),"temp":text(source_value(meeting_source,"temp","temperature")),"rain24h":text(source_value(meeting_source,"rain24h")),"irrigation24h":text(source_value(meeting_source,"irrigation24h")),"officialUpdate":text(source_value(meeting_source,"officialUpdate")),"races":len(race_summaries),"declared":declared,"scratchings":scratches,"first":race_summaries[0]["time"] if race_summaries else "Not supplied","last":race_summaries[-1]["time"] if race_summaries else "Not supplied","status":"READY","raceSummaries":race_summaries}
            day_meetings.append(row)
            detail_meeting = dict(meeting)
            detail_meeting["trackCondition"] = row["track"]
            detail_meeting["rail"] = row["rail"]
            detail_meeting["races"] = [dict(r, trackCondition=(r.get("trackCondition") or row["track"]), rail=(r.get("rail") or row["rail"])) for r in (meeting.get("races") or [])]
            detail={"schemaVersion":"edgeiq_meeting_detail_feed_v1","generatedAt":generated_at,"date":date_value,"meetingKey":meeting_key,"meeting":detail_meeting}
            (MEETINGS_DIR/f"{date_value}_{slug(meeting_key)}.json").write_text(json.dumps(detail,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
        tracks=[str(m.get("track","")).lower() for m in day_meetings]
        totals={"meetings":len(day_meetings),"races":sum(m["races"] for m in day_meetings),"declared":sum(m["declared"] for m in day_meetings),"scratchings":sum(m["scratchings"] for m in day_meetings),"heavyTracks":sum("heavy" in t for t in tracks),"softTracks":sum("soft" in t for t in tracks),"goodTracks":sum("good" in t for t in tracks),"weatherAlerts":0}
        raw_key=str(day_labels.get(date_value,date_value)).upper().replace(" ","_").replace("+","PLUS_")
        key="TODAY" if "TODAY" in raw_key else "TOMORROW" if "TOMORROW" in raw_key else "DAY_PLUS_2"
        days.append({"key":key,"date":date_value,"generatedAt":generated_at,"totals":totals,"meetings":day_meetings})
    summary={"schemaVersion":"edgeiq_meetings_summary_feed_v1","timezone":"Australia/Melbourne","generatedAt":generated_at,"days":days}
    SUMMARY.write_text(json.dumps(summary,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    total_meetings=sum(d["totals"]["meetings"] for d in days); total_races=sum(d["totals"]["races"] for d in days); total_runners=sum(d["totals"]["declared"] for d in days)
    print(f"[EDGEIQ] dashboard feeds PASS days={len(days)} meetings={total_meetings} races={total_races} runners={total_runners}")
    if len(days)<3 or total_meetings<=0 or total_races<=0 or total_runners<=0: raise SystemExit("Dashboard feed failed population gate")
    today = next((d for d in days if d["key"]=="TODAY"), None)
    if today:
        missing_track=[m["meeting"] for m in today["meetings"] if m.get("track") in ("Not supplied","—","")]
        missing_rail=[m["meeting"] for m in today["meetings"] if m.get("rail") in ("Not supplied","—","")]
        if missing_track: raise SystemExit(f"Meetings feed missing full track rating: {missing_track}")
        if missing_rail: raise SystemExit(f"Meetings feed missing rail: {missing_rail}")
        missing_time=[m["meeting"] for m in today["meetings"] if m.get("first") in ("Not supplied","—","",None)]
        if missing_time: raise SystemExit(f"Meetings feed missing first race time: {missing_time}")

if __name__ == "__main__": main()
