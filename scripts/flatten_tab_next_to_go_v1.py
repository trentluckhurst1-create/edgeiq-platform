import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "public" / "data" / "tab_next_to_go_full.json"
OUT_ALL = ROOT / "public" / "data" / "edgeiq_tab_next_to_go_all_v1.csv"
OUT_VIC_R = ROOT / "public" / "data" / "edgeiq_tab_next_to_go_vic_thoroughbred_v1.csv"

data = json.loads(SRC.read_text(encoding="utf-8"))

rows = []

for r in data.get("races", []):
    m = r.get("meeting", {}) or {}
    links = r.get("_links", {}) or {}

    rows.append({
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
        "sell_code_meeting_code": ((m.get("sellCode") or {}).get("meetingCode")),
        "sell_code_scheduled_type": ((m.get("sellCode") or {}).get("scheduledType")),
        "race_details_url": links.get("self"),
        "race_form_url": links.get("form"),
        "big_bets_url": links.get("bigBets"),
    })

df = pd.DataFrame(rows)

if not df.empty:
    df = df.sort_values(["race_start_time_utc", "location", "meeting_name", "race_no"])

df.to_csv(OUT_ALL, index=False)

vic_r = df[
    (df["location"].astype(str).str.upper() == "VIC") &
    (df["race_type"].astype(str).str.upper() == "R")
].copy()

vic_r.to_csv(OUT_VIC_R, index=False)

print("[tab_feed_flatten] all_rows=", len(df))
print("[tab_feed_flatten] vic_thoroughbred_rows=", len(vic_r))
print("[tab_feed_flatten] wrote", OUT_ALL)
print("[tab_feed_flatten] wrote", OUT_VIC_R)

if not vic_r.empty:
    print(vic_r.head(20).to_string(index=False))
else:
    print("[tab_feed_flatten] No VIC thoroughbred rows in this next-to-go snapshot.")
