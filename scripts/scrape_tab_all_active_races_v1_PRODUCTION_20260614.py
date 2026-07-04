from pathlib import Path
from datetime import datetime
import pandas as pd
import subprocess
import sys
import re
import time

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

TODAY_SOURCE = DATA / "edgeiq_vic_live_terminal_feed_v1_TODAY_ONLY.csv"
FALLBACK_SOURCE = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"

OUT = DATA / "edgeiq_tab_live_prices_direct_v1.csv"
AUDIT = DATA / "edgeiq_tab_all_active_races_scrape_audit_v1.csv"
SCRAPER = ROOT / "scripts" / "scrape_tab_single_race_v1.py"

TODAY = datetime.now().strftime("%Y-%m-%d")

VIC_TRACKS = {
    "WANGARATTA",
    "WARRNAMBOOL",
}

VENUE_CODES = {
    "WANGARATTA": "WAN",
    "WARRNAMBOOL": "WBO",
}

def s(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def race_num(x):
    return re.sub(r"[^0-9]", "", s(x))

def slug_for_track(track):
    return s(track).replace(" ", "-").title()

def venue_code(track):
    return VENUE_CODES.get(s(track).upper(), "")

src = TODAY_SOURCE if TODAY_SOURCE.exists() else FALLBACK_SOURCE
if not src.exists():
    raise SystemExit(f"Missing source: {src}")

board = pd.read_csv(src, dtype=str).fillna("")

board["track_norm"] = board["track"].astype(str).str.upper().str.strip()
board = board[
    (board["race_date"].astype(str).str[:10] == TODAY) &
    (board["track_norm"].isin(VIC_TRACKS))
].copy()

races = (
    board[["race_date","track","race_no"]]
    .drop_duplicates()
    .sort_values(["race_date","track","race_no"])
)

all_rows = []
audit = []

print(f"[TAB_ALL_ACTIVE] source={src}")
print(f"[TAB_ALL_ACTIVE] today={TODAY}")
print(f"[TAB_ALL_ACTIVE] races={len(races)}")

for _, r in races.iterrows():
    date = s(r["race_date"])[:10]
    track = s(r["track"]).upper()
    rn = race_num(r["race_no"])
    venue = venue_code(track)
    slug = slug_for_track(track)

    if not venue:
        audit.append([date, track, rn, "NO_VENUE_CODE", 0, ""])
        continue

    url = f"https://www.tab.com.au/racing/{date}/{slug}/{venue}/R/{rn}"
    print("SCRAPE", url)

    try:
        p = subprocess.run(
            [sys.executable, str(SCRAPER), "--url", url],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            timeout=90,
        )
    except subprocess.TimeoutExpired:
        audit.append([date, track, rn, "SCRAPER_TIMEOUT", 0, url])
        continue

    print(p.stdout)

    if p.returncode != 0:
        audit.append([date, track, rn, "SCRAPER_FAIL", 0, p.stdout[-500:] + p.stderr[-500:]])
        continue

    single = DATA / "edgeiq_tab_single_race_v1.csv"
    if not single.exists():
        audit.append([date, track, rn, "NO_SINGLE_FILE", 0, url])
        continue

    df = pd.read_csv(single, dtype=str).fillna("")
    if len(df):
        df["race_date"] = date
        df["meeting_date"] = date
        df["track"] = track
        df["race_no"] = rn
        all_rows.append(df)
        audit.append([date, track, rn, "OK", len(df), url])
    else:
        audit.append([date, track, rn, "ZERO_ROWS", 0, url])

    time.sleep(0.25)

if all_rows:
    out = pd.concat(all_rows, ignore_index=True)
    out.to_csv(OUT, index=False)
else:
    pd.DataFrame().to_csv(OUT, index=False)

pd.DataFrame(
    audit,
    columns=["race_date","track","race_no","status","rows","url_or_note"]
).to_csv(AUDIT, index=False)

print("[TAB_ALL_ACTIVE] COMPLETE")
print(f"rows={sum(a[4] for a in audit if isinstance(a[4], int))}")
print(f"out={OUT}")
print(f"audit={AUDIT}")
