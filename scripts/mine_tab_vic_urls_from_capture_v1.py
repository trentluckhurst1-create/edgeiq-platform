from pathlib import Path
import json
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_tab_vic_thoroughbred_urls_v1.csv"

search_files = list((DATA / "tab_randwick_capture_v1").glob("resp_*.txt"))
rows = []

for fp in search_files:
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        continue

    meetings = data.get("meetings", [])
    for m in meetings:
        if str(m.get("location", "")).upper() != "VIC":
            continue
        if str(m.get("raceType", "")).upper() != "R":
            continue

        meeting_date = m.get("meetingDate")
        meeting_name = m.get("meetingName")
        venue = m.get("venueMnemonic")
        race_type = m.get("raceType")
        races = m.get("races", []) or []

        print("[FOUND VIC]", meeting_date, meeting_name, venue, "races", len(races))

        for r in races:
            rn = r.get("raceNumber")
            if rn is None:
                continue

            slug = re.sub(r"[^A-Z0-9]+", "-", str(meeting_name).upper()).strip("-")
            rows.append({
                "meeting_date": meeting_date,
                "meeting_name": meeting_name,
                "location": "VIC",
                "race_type": race_type,
                "venue_mnemonic": venue,
                "race_no": int(rn),
                "tab_frontend_url": f"https://www.tab.com.au/racing/{meeting_date}/{slug}/{venue}/{race_type}/{int(rn)}",
            })

df = pd.DataFrame(rows).drop_duplicates() if rows else pd.DataFrame(columns=[
    "meeting_date","meeting_name","location","race_type","venue_mnemonic","race_no","tab_frontend_url"
])

df.to_csv(OUT, index=False)

print("[mine_vic_urls] rows", len(df))
print("[mine_vic_urls] wrote", OUT)

if not df.empty:
    print(df.to_string(index=False))
else:
    print("[mine_vic_urls] No VIC gallops found inside captured TAB meetings payloads.")
