from __future__ import annotations

import csv
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_vic_historical_backfill_manifest_v1.csv"
SUMMARY = DATA / "edgeiq_vic_historical_backfill_manifest_v1_summary.csv"

START_YEAR = 2000
END_YEAR = datetime.now().year

TRACKS = {
    "FLEMINGTON",
    "CAULFIELD",
    "CAULFIELD HEATH",
    "MOONEE VALLEY",
    "SANDOWN",
    "SANDOWN HILLSIDE",
    "SANDOWN LAKESIDE",
    "CRANBOURNE",
    "BALLARAT",
    "BENDIGO",
    "GEELONG",
    "WARRNAMBOOL",
    "SALE",
    "PAKENHAM",
    "MORNINGTON",
    "SEYMOUR",
    "KYNETON",
    "WANGARATTA",
    "WODONGA",
    "ECHUCA",
    "SWAN HILL",
    "MILDURA",
    "TERANG",
    "COLAC",
    "HAMILTON",
    "ARARAT",
    "STAWELL",
    "CASTERTON",
    "MOE",
    "TRARALGON",
    "BAIRNSDALE",
}

HEADERS = {
    "User-Agent": "EDGEiQ-Racing/1.0 historical-manifest-builder",
    "Accept": "application/json,text/plain,*/*",
}


def clean(v):
    return "" if v is None else str(v).strip()


def upper(v):
    return clean(v).upper()


def slug(value):
    value = clean(value).lower()
    value = value.replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def date_yyyy_mm_dd(value):
    txt = clean(value)
    if not txt:
        return ""
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", txt)
    if m:
        return m.group(0)
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", txt)
    if m:
        d, mo, y = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
    return txt[:10]


def extract_entries(payload):
    entries = []
    for month in payload.get("Months", []) or []:
        for key in ["CalendarEntries", "CalendarEntriesList", "Meetings", "RaceMeetings"]:
            vals = month.get(key)
            if isinstance(vals, list):
                entries.extend(vals)
    if isinstance(payload.get("CalendarEntries"), list):
        entries.extend(payload["CalendarEntries"])
    return entries


def get_field(row, names):
    for n in names:
        if isinstance(row, dict) and n in row and clean(row.get(n)):
            return row.get(n)
    return ""


def track_from_entry(entry):
    return upper(get_field(entry, [
        "TrackName", "trackName", "Track", "track", "Venue", "venue",
        "MeetingName", "meetingName", "Name", "name"
    ]))


def race_count_from_entry(entry):
    for k in ["RaceCount", "raceCount", "NumberOfRaces", "numberOfRaces", "RacesCount"]:
        v = clean(entry.get(k)) if isinstance(entry, dict) else ""
        if v:
            try:
                return int(float(v))
            except Exception:
                pass

    races = entry.get("Races") if isinstance(entry, dict) else None
    if isinstance(races, list):
        return len(races)

    return 12


def meeting_url_from_entry(entry, meeting_date, track):
    existing = get_field(entry, ["Url", "url", "MeetingUrl", "meetingUrl"])
    if existing:
        if existing.startswith("http"):
            return existing
        return "https://www.racing.com" + existing

    return f"https://www.racing.com/form/{meeting_date}/{slug(track)}"


def race_url(meeting_date, track, race_no):
    return f"https://www.racing.com/form/{meeting_date}/{slug(track)}/race/{race_no}"


def fetch_month(year, month):
    url = f"https://www.racing.com/services/appv2/GetMeetsByMonth/{year}/{month}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=45)
        if r.status_code != 200:
            return url, None, f"HTTP_{r.status_code}"
        return url, r.json(), "OK"
    except Exception as e:
        return url, None, f"ERROR_{type(e).__name__}:{e}"


def main():
    built_at = datetime.now(timezone.utc).isoformat()
    DATA.mkdir(parents=True, exist_ok=True)

    rows = []
    seen = set()
    endpoint_status = []

    for year in range(START_YEAR, END_YEAR + 1):
        for month in range(1, 13):
            endpoint, payload, status = fetch_month(year, month)
            endpoint_status.append((year, month, status))

            if not payload:
                continue

            entries = extract_entries(payload)

            for entry in entries:
                track = track_from_entry(entry)
                if not track:
                    continue

                matched = track in TRACKS or any(t in track for t in TRACKS)
                if not matched:
                    continue

                meeting_date = date_yyyy_mm_dd(get_field(entry, [
                    "Date", "date", "MeetingDate", "meetingDate", "RaceDate", "raceDate"
                ]))

                if not meeting_date:
                    continue

                meeting_name = clean(get_field(entry, [
                    "MeetingName", "meetingName", "Name", "name", "DisplayName", "displayName"
                ])) or track

                meeting_url = meeting_url_from_entry(entry, meeting_date, track)
                race_count = race_count_from_entry(entry)

                races = entry.get("Races") if isinstance(entry, dict) else None

                if isinstance(races, list) and races:
                    race_nos = []
                    for rr in races:
                        rn = get_field(rr, ["RaceNumber", "raceNumber", "RaceNo", "raceNo", "Number", "number"])
                        try:
                            race_nos.append(int(float(rn)))
                        except Exception:
                            pass
                    race_nos = sorted(set(race_nos)) if race_nos else list(range(1, race_count + 1))
                else:
                    race_nos = list(range(1, race_count + 1))

                for rn in race_nos:
                    ru = race_url(meeting_date, track, rn)
                    key = ru.lower()
                    if key in seen:
                        continue
                    seen.add(key)

                    rows.append({
                        "meeting_date": meeting_date,
                        "track": track,
                        "meeting_name": meeting_name,
                        "meeting_url": meeting_url,
                        "race_no": rn,
                        "race_url": ru,
                        "year": year,
                        "month": month,
                        "source_endpoint": endpoint,
                        "harvest_status": "PENDING",
                        "built_at": built_at,
                    })

            time.sleep(0.05)

        print(f"[MANIFEST] {year} rows_so_far={len(rows)}")

    rows.sort(key=lambda r: (r["meeting_date"], r["track"], int(r["race_no"])))

    fields = [
        "meeting_date", "track", "meeting_name", "meeting_url", "race_no", "race_url",
        "year", "month", "source_endpoint", "harvest_status", "built_at"
    ]

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    by_year = {}
    by_track = {}
    for r in rows:
        y = r["year"]
        t = r["track"]
        by_year.setdefault(y, {"race_urls": 0, "meetings": set()})
        by_year[y]["race_urls"] += 1
        by_year[y]["meetings"].add((r["meeting_date"], r["track"]))

        by_track.setdefault(t, 0)
        by_track[t] += 1

    summary = [
        {"metric": "status", "value": "EDGEIQ_VIC_HISTORICAL_BACKFILL_MANIFEST_V1_BUILT"},
        {"metric": "start_year", "value": START_YEAR},
        {"metric": "end_year", "value": END_YEAR},
        {"metric": "total_race_urls", "value": len(rows)},
        {"metric": "unique_race_urls", "value": len(set(r["race_url"].lower() for r in rows))},
        {"metric": "unique_meetings", "value": len(set((r["meeting_date"], r["track"]) for r in rows))},
        {"metric": "tracks", "value": len(set(r["track"] for r in rows))},
        {"metric": "built_at", "value": built_at},
    ]

    for y in sorted(by_year):
        summary.append({"metric": f"year_{y}_meetings", "value": len(by_year[y]["meetings"])})
        summary.append({"metric": f"year_{y}_race_urls", "value": by_year[y]["race_urls"]})

    for t in sorted(by_track):
        summary.append({"metric": f"track_{t}_race_urls", "value": by_track[t]})

    status_counts = {}
    for _, _, s in endpoint_status:
        status_counts[s] = status_counts.get(s, 0) + 1
    for s, n in sorted(status_counts.items()):
        summary.append({"metric": f"endpoint_status_{s}", "value": n})

    with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("[EDGEIQ_VIC_HISTORICAL_BACKFILL_MANIFEST_V1] COMPLETE")
    print(f"rows={len(rows)}")
    print(f"output={OUT}")
    print(f"summary={SUMMARY}")


if __name__ == "__main__":
    main()
