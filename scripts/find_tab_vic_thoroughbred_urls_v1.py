from pathlib import Path
import json
import re
import sys
import time
from datetime import datetime, timedelta
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUT_MEETINGS = DATA / "edgeiq_tab_vic_thoroughbred_meetings_v1.csv"
OUT_URLS = DATA / "edgeiq_tab_vic_thoroughbred_urls_v1.csv"
OUT_FILTERED = DATA / "edgeiq_tab_vic_thoroughbred_urls_filtered_v1.csv"
RAW_DIR = DATA / "tab_vic_meetings_raw_v1"
RAW_DIR.mkdir(parents=True, exist_ok=True)

VIC_TRACKS = {
    "BAIRNSDALE", "BALLARAT", "BENDIGO", "CAULFIELD", "CAULFIELD HEATH",
    "CRANBOURNE", "ECHUCA", "FLEMINGTON", "GEELONG", "KILMORE",
    "KYNETON", "MOE", "MORNINGTON", "MOONEE VALLEY", "PAKENHAM",
    "SALE", "SANDOWN", "SANDOWN HILLSIDE", "SANDOWN LAKESIDE",
    "SEYMOUR", "SWAN HILL", "WANGARATTA", "WARRNAMBOOL", "WODONGA",
    "STAWELL", "HORSHAM", "CASTERTON", "COLAC", "HAMILTON", "ARARAT",
    "TERANG", "BENALLA", "MILDURA", "DONALD", "BENDIGO"
}

def arg_value(flag, default=""):
    if flag in sys.argv:
        i = sys.argv.index(flag)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default

def dates():
    start = arg_value("--start-date", "")
    end = arg_value("--end-date", "")

    if not start:
        start = datetime.now().strftime("%Y-%m-%d")
    if not end:
        end = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    s = datetime.strptime(start, "%Y-%m-%d").date()
    e = datetime.strptime(end, "%Y-%m-%d").date()

    out = []
    d = s
    while d <= e:
        out.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)
    return out

def safe(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def norm_track(x):
    s = safe(x).upper()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("SANDOWN HILLSIDE", "SANDOWN")
    return s.strip()

def is_vic_track(name):
    n = norm_track(name)
    if n in VIC_TRACKS:
        return True
    if "VIC" in safe(name).upper():
        return True
    return False

def fetch_meetings(d):
    url = f"https://api.beta.tab.com.au/v1/tab-info-service/racing/dates/{d}/meetings?jurisdiction=VIC"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json,text/plain,*/*",
        "Referer": f"https://www.tab.com.au/racing/meetings/{d}/R",
    }

    r = requests.get(url, headers=headers, timeout=25)
    raw_path = RAW_DIR / f"meetings_{d}.json"

    if r.status_code != 200:
        raw_path.write_text(r.text, encoding="utf-8")
        print("[find_vic_tab]", d, "HTTP", r.status_code, url)
        return []

    data = r.json()
    raw_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    meetings = data.get("meetings", []) or []
    print("[find_vic_tab]", d, "meetings", len(meetings))
    return meetings

def meeting_code(m):
    for k in ["meetingName", "venueMnemonic", "location", "track", "venueName", "name"]:
        v = safe(m.get(k))
        if v:
            return v
    return ""

def race_list(m):
    for k in ["races", "raceList"]:
        v = m.get(k)
        if isinstance(v, list):
            return v
    return []

def main():
    meeting_rows = []
    url_rows = []

    for d in dates():
        meetings = fetch_meetings(d)
        for m in meetings:
            meeting_name = meeting_code(m)
            code = safe(m.get("venueMnemonic")) or safe(m.get("meetingCode")) or safe(m.get("location")) or meeting_name
            race_type = safe(m.get("raceType")) or safe(m.get("code")) or safe(m.get("meetingType"))

            is_racing = race_type.upper() in {"R", "THOROUGHBRED", "HORSE_RACING", ""}

            if not is_racing:
                continue

            if not is_vic_track(meeting_name) and not is_vic_track(code):
                continue

            meeting_rows.append({
                "meeting_date": d,
                "track": meeting_name,
                "venue_code": code,
                "race_type": race_type,
                "source": "TAB_API",
            })

            races = race_list(m)
            for race in races:
                race_no = safe(race.get("raceNumber")) or safe(race.get("race_no")) or safe(race.get("number"))
                if not race_no:
                    continue

                url_rows.append({
                    "meeting_date": d,
                    "track": meeting_name,
                    "venue_code": code,
                    "race_no": race_no,
                    "tab_url": f"https://www.tab.com.au/racing/{d}/{code}/R/{race_no}",
                    "source": "TAB_API",
                })

    meetings_df = pd.DataFrame(meeting_rows)
    urls_df = pd.DataFrame(url_rows)

    meetings_df.to_csv(OUT_MEETINGS, index=False)
    urls_df.to_csv(OUT_URLS, index=False)
    urls_df.to_csv(OUT_FILTERED, index=False)

    print("[find_vic_tab] dates", ",".join(dates()))
    print("[find_vic_tab] vic_thoroughbred_meetings", len(meetings_df))
    print("[find_vic_tab] vic_thoroughbred_race_urls", len(urls_df))
    print("[find_vic_tab] wrote", OUT_MEETINGS)
    print("[find_vic_tab] wrote", OUT_URLS)

    if not meetings_df.empty:
        print(meetings_df.to_string(index=False))
    if not urls_df.empty:
        print(urls_df.head(40).to_string(index=False))

if __name__ == "__main__":
    main()
