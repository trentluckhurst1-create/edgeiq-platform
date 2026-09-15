from __future__ import annotations

import csv
import html
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
RACE_LIST = DATA / "edgeiq_vic_three_day_race_list_v1.csv"
SUMMARY = DATA / "edgeiq_meetings_summary_feed_v1.json"
MEETINGS = DATA / "meetings"
MELBOURNE = ZoneInfo("Australia/Melbourne")
csv.field_size_limit(1024 * 1024 * 128)


def clean(value):
    return str(value or "").strip()


def meeting_slug(value: str) -> str:
    text = clean(value).lower()
    text = re.sub(r"^(sportsbet|ladbrokes|bet365|picklebet)[- ]+", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    aliases = {
        "caulfield": "caulfield-heath",
        "caulfield-heath": "caulfield-heath",
        "sportsbet-ballarat": "ballarat",
        "ballarat-synthetic": "ballarat-synthetic",
        "the-valley": "moonee-valley",
    }
    return aliases.get(text, text)


def local_time(value: str) -> str | None:
    text = clean(value)
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt.astimezone(MELBOURNE).strftime("%H:%M")
    except Exception:
        return None


def full_track(condition: str, rating: str) -> str | None:
    c = clean(condition)
    r = clean(rating)
    if not c and not r:
        return None
    if re.search(r"\d", c) or c.lower() == "synthetic":
        return c
    if c and r and re.fullmatch(r"\d{1,2}", r):
        return f"{c} {r}"
    if r and re.search(r"\b(?:Firm|Good|Soft|Heavy)\s*\d{1,2}\b", r, re.I):
        return re.search(r"\b(?:Firm|Good|Soft|Heavy)\s*\d{1,2}\b", r, re.I).group(0).title()
    return c or r


def fetch_rail(meeting: str, race_date: str) -> str | None:
    slug = meeting_slug(meeting)
    url = f"https://www.racingandsports.com.au/form-guide/thoroughbred/australia/{slug}/{race_date}"
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 (EDGEiQ Racing Intelligence)"})
        raw = urlopen(req, timeout=20).read().decode("utf-8", errors="replace")
        text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
        text = re.sub(r"\s+", " ", text)
        patterns = (
            r"Rail:\s*Rail:\s*(.+?)(?:Track Details|Trainer Statistics|Weather|$)",
            r"Rail:\s*(True Entire Circuit\.?|True\.?|Out\s+\d+(?:\.\d+)?m[^.]*\.?|\+?\d+(?:\.\d+)?m[^.]*\.?)",
        )
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                value = clean(match.group(1)).strip(" .")
                if value and len(value) <= 80:
                    return value
    except Exception as exc:
        print(f"RAIL_LOOKUP_WARN meeting={meeting!r} date={race_date} error={exc}")
    return None


def load_races():
    if not RACE_LIST.exists():
        return []
    with RACE_LIST.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def same_meeting(row, date, meeting):
    if clean(row.get("race_date"))[:10] != date:
        return False
    a = re.sub(r"[^A-Z0-9]", "", clean(row.get("normalised_track") or row.get("track")).upper())
    b = re.sub(r"[^A-Z0-9]", "", clean(meeting).upper())
    if a == b:
        return True
    return ("CAULFIELD" in a and "CAULFIELD" in b) or ("BALLARAT" in a and "BALLARAT" in b)


def enrich_meeting_obj(obj, source_rows, rail):
    races = obj.get("races") or []
    by_no = {int(float(clean(r.get("race_no")))): r for r in source_rows if clean(r.get("race_no"))}
    for race in races:
        try:
            no = int(race.get("raceNumber"))
        except Exception:
            continue
        src = by_no.get(no)
        if not src:
            continue
        time = local_time(src.get("race_time_utc"))
        track = full_track(src.get("track_condition"), src.get("track_rating"))
        if time:
            race["raceTime"] = time
        if track:
            race["trackCondition"] = track
        if rail:
            race["rail"] = rail
        source = race.get("source") if isinstance(race.get("source"), dict) else {}
        source.update({"advertised_time_local": time, "official_track_rating": track, "rail_position": rail})
        race["source"] = source
    if races:
        tracks = [clean(r.get("trackCondition")) for r in races if clean(r.get("trackCondition"))]
        if tracks:
            obj["trackCondition"] = tracks[0]
    if rail:
        obj["rail"] = rail
    return obj


def main() -> int:
    rows = load_races()
    if not rows or not SUMMARY.exists():
        print("EDGEIQ_RUNTIME_MEETING_ENRICHMENT SKIP")
        return 0
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    rail_cache = {}
    enriched = 0
    for day in summary.get("days", []):
        date = clean(day.get("date"))[:10]
        for meeting in day.get("meetings", []):
            name = clean(meeting.get("meeting") or meeting.get("venue"))
            source_rows = [r for r in rows if same_meeting(r, date, name)]
            if not source_rows:
                continue
            key = (date, name.upper())
            rail = rail_cache.setdefault(key, fetch_rail(name, date))
            source_rows.sort(key=lambda r: int(float(clean(r.get("race_no")) or 999)))
            first_time = local_time(source_rows[0].get("race_time_utc"))
            last_time = local_time(source_rows[-1].get("race_time_utc"))
            track = full_track(source_rows[0].get("track_condition"), source_rows[0].get("track_rating"))
            if first_time: meeting["first"] = first_time
            if last_time: meeting["last"] = last_time
            if track: meeting["track"] = track
            if rail: meeting["rail"] = rail
            for rs in meeting.get("raceSummaries", []):
                try: src = next((r for r in source_rows if int(float(clean(r.get("race_no")))) == int(rs.get("raceNumber"))), None)
                except Exception: src = None
                if src:
                    t = local_time(src.get("race_time_utc"))
                    if t: rs["time"] = t
            shard = MEETINGS / f"{date}_{date}-{re.sub(r'[^a-z0-9]+','-', clean(meeting.get('providerMeetingKey') or name).lower()).strip('-')}.json"
            if shard.exists():
                payload = json.loads(shard.read_text(encoding="utf-8"))
                if isinstance(payload.get("meeting"), dict):
                    payload["meeting"] = enrich_meeting_obj(payload["meeting"], source_rows, rail)
                    shard.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
            enriched += 1
    SUMMARY.write_text(json.dumps(summary, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"EDGEIQ_RUNTIME_MEETING_ENRICHMENT PASS MEETINGS={enriched}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
