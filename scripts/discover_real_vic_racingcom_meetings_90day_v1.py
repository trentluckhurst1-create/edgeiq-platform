from pathlib import Path
import pandas as pd
import requests
from datetime import datetime, timedelta
from urllib.parse import quote
import json

ROOT = Path.cwd()
PUBLIC = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"
PUBLIC.mkdir(parents=True, exist_ok=True)

OUT = PUBLIC / "edgeiq_vic_real_racingcom_meetings_90day_v1.csv"
URLS_OUT = PUBLIC / "edgeiq_vic_real_speed_data_urls_90day_v1.csv"

END_DATE = datetime(2026, 5, 13)
START_DATE = END_DATE - timedelta(days=90)

GQL = "https://graphql.rmdprod.racing.com/"

query = """
query GetRaceMeetingsByStateNew_CD($states: String!, $daysBack: Int!, $daysForward: Int!, $userDate: String!) {
  GetRaceMeetingsByStateNew(states: $states, daysBack: $daysBack, daysForward: $daysForward, userDate: $userDate) {
    id
    venue
    date
    state
    isTrial
    isJumpOut
    meetUrl
    sortOrder
  }
}
"""

params = {
    "query": query,
    "variables": json.dumps({
        "states": "VIC",
        "daysBack": 90,
        "daysForward": 0,
        "userDate": END_DATE.strftime("%Y-%m-%d")
    })
}

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://www.racing.com/calendar"
}

r = requests.get(GQL, params=params, headers=headers, timeout=60)
print("STATUS:", r.status_code)
print("LEN:", len(r.text))

data = r.json()

meetings = data.get("data", {}).get("GetRaceMeetingsByStateNew", [])

rows = []

for m in meetings:
    d = str(m.get("date", ""))[:10]
    try:
        dd = datetime.fromisoformat(d)
    except:
        continue

    if dd < START_DATE or dd > END_DATE:
        continue

    if str(m.get("state", "")).upper() != "VIC":
        continue

    if m.get("isTrial") or m.get("isJumpOut"):
        continue

    meet_url = m.get("meetUrl", "")

    rows.append({
        "meet_id": m.get("id", ""),
        "race_date": d,
        "venue": m.get("venue", ""),
        "state": m.get("state", ""),
        "meet_url": meet_url,
        "track_slug": str(meet_url).strip("/").split("/")[-1] if meet_url else "",
        "sort_order": m.get("sortOrder", "")
    })

df = pd.DataFrame(rows).drop_duplicates()

df = df.sort_values(["race_date", "venue"])

df.to_csv(OUT, index=False)

url_rows = []

for _, row in df.iterrows():
    track_slug = row["track_slug"]
    race_date = row["race_date"]

    if not track_slug:
        continue

    for race_no in range(1, 13):
        url_rows.append({
            "race_date": race_date,
            "venue": row["venue"],
            "track_slug": track_slug,
            "race_no": race_no,
            "speed_data_url": f"https://www.racing.com/form/{race_date}/{track_slug}/race/{race_no}/speed-data"
        })

urls = pd.DataFrame(url_rows)
urls.to_csv(URLS_OUT, index=False)

print("=" * 100)
print("REAL VIC RACING.COM MEETINGS DISCOVERED")
print("=" * 100)
print("MEETINGS:", len(df))
print("SPEED URLS:", len(urls))
print(df.to_string(index=False))
print("=" * 100)
print("SAVED:", OUT)
print("SAVED:", URLS_OUT)
