from pathlib import Path
import pandas as pd
import re

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_execution_board_live.csv"
OUT = DATA / "edgeiq_active_ra_profile_backfill_targets_v1.csv"

def clean_key(x):
    s = str(x or "").upper()
    s = s.replace("’", "").replace("'", "")
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s.strip()

live = pd.read_csv(LIVE, low_memory=False).copy()

rows = []

for _, r in live.iterrows():
    horse = str(r.get("horse", "")).strip()
    horse_key = clean_key(r.get("horse_key", horse))
    profile_url = str(r.get("profile_url", "") or r.get("horse_url", "")).strip()
    horse_url = str(r.get("horse_url", "")).strip()

    rows.append({
        "horse": horse,
        "horse_key": horse_key,
        "track": r.get("track", ""),
        "race_date": r.get("race_date", ""),
        "race_no": r.get("race_no", ""),
        "profile_url": profile_url,
        "horse_url": horse_url,
        "has_ra_profile_url": bool(profile_url.startswith("http")),
        "target_status": "READY_TO_BACKFILL" if profile_url.startswith("http") else "MISSING_PROFILE_URL",
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

print(out.to_string(index=False))
print()
print("SAVED:", OUT)
