from pathlib import Path
from datetime import datetime
import argparse
import json
import re
import pandas as pd
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
RAW = DATA / "tab_single_race_raw_v1"
RAW.mkdir(parents=True, exist_ok=True)

OUT = DATA / "edgeiq_tab_single_race_v1.csv"

FRONTEND_RE = re.compile(r"/racing/(\d{4}-\d{2}-\d{2})/([^/]+)/([^/]+)/([RGH])/(\d+)$")

def clean(x):
    return "" if x is None else str(x).strip()

def pick(d, names):
    if not isinstance(d, dict):
        return ""
    for n in names:
        if d.get(n) not in [None, ""]:
            return d.get(n)
    return ""

def fixed_block(r):
    return pick(r, ["fixedOdds", "fixed", "fixedOddsPrice"]) or {}

def tote_block(r):
    return pick(r, ["parimutuel", "tote"]) or {}

def flatten(payload, api_url):
    rows = []
    meeting = payload.get("meeting") or {}
    runners = payload.get("runners") or []

    for r in runners:
        fixed = fixed_block(r)
        tote = tote_block(r)

        rows.append({
            "scraped_at": datetime.now().isoformat(timespec="seconds"),
            "source": "TAB",
            "api_url": api_url,
            "meeting_date": clean(payload.get("meetingDate") or meeting.get("meetingDate")),
            "race_date": clean(payload.get("meetingDate") or meeting.get("meetingDate")),
            "location": clean(payload.get("location") or meeting.get("location")),
            "meeting_name": clean(payload.get("meetingName") or meeting.get("meetingName")),
            "venue_mnemonic": clean(payload.get("venueMnemonic") or meeting.get("venueMnemonic")),
            "race_type": clean(payload.get("raceType") or meeting.get("raceType")),
            "race_no": clean(payload.get("raceNumber") or payload.get("raceNo")),
            "runner_no": clean(pick(r, ["runnerNumber", "runner_no", "number"])),
            "horse": clean(pick(r, ["runnerName", "name", "runner_name"])),
            "barrier": clean(pick(r, ["barrierNumber", "barrier"])),
            "jockey": clean(pick(r, ["riderName", "jockey"])),
            "trainer": clean(pick(r, ["trainerName", "trainer"])),
            "weight": clean(r.get("handicapWeight")),
            "claim": clean(r.get("claimAmount")),
            "last5": clean(r.get("last5Starts")),
            "tab_fixed_win": clean(pick(fixed, ["returnWin"])),
            "tab_fixed_place": clean(pick(fixed, ["returnPlace"])),
            "tab_fixed_open_win": clean(pick(fixed, ["returnWinOpen"])),
            "tab_fixed_betting_status": clean(pick(fixed, ["bettingStatus"])),
            "scratched_time": clean(pick(fixed, ["scratchedTime"])),
            "tab_tote_win": clean(pick(tote, ["returnWin"])),
            "tab_tote_place": clean(pick(tote, ["returnPlace"])),
            "tab_tote_betting_status": clean(pick(tote, ["bettingStatus"])),
            "early_speed_rating": clean(r.get("earlySpeedRating")),
            "early_speed_band": clean(r.get("earlySpeedRatingBand")),
            "dfs_form_rating": clean(r.get("dfsFormRating")),
            "tech_form_rating": clean(r.get("techFormRating")),
            "total_rating_points": clean(r.get("totalRatingPoints")),
            "silk_url": clean(r.get("silkURL")),
        })

    return pd.DataFrame(rows)

def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))

ap = argparse.ArgumentParser()
ap.add_argument("--url", required=True)
args = ap.parse_args()

m = FRONTEND_RE.search(args.url)
if not m:
    raise SystemExit("Bad TAB race URL shape: " + args.url)

date, slug, venue, race_type, race_no = m.groups()

api_url = (
    f"https://api.beta.tab.com.au/v1/tab-info-service/racing/"
    f"dates/{date}/meetings/{race_type}/{venue}/races/{race_no}"
    f"?returnPromo=true&returnOffers=true&jurisdiction=NSW"
)

print("[tab_single] url", args.url)
print("[tab_single] api", api_url)

try:
    payload = fetch_json(api_url)
except Exception as e:
    print("[tab_single] API_FETCH_FAIL", repr(e))
    raise SystemExit(1)

if not isinstance(payload, dict) or not isinstance(payload.get("runners"), list) or len(payload.get("runners")) == 0:
    print("[tab_single] NO_RUNNERS")
    raise SystemExit(1)

raw_name = f"{date}_{venue}_{race_type}_{race_no}.json"
(RAW / raw_name).write_text(json.dumps(payload, indent=2), encoding="utf-8")

df = flatten(payload, api_url)
df.to_csv(OUT, index=False)

print("[tab_single] captured", api_url)
print("[tab_single] runners", len(df))
print("[tab_single] wrote", OUT)
print(df[["meeting_name","location","race_type","race_no","runner_no","horse","barrier","jockey","trainer","tab_fixed_win","tab_fixed_place","tab_fixed_betting_status"]].to_string(index=False))
