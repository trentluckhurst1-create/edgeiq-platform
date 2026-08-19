from pathlib import Path
import pandas as pd
import re

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_execution_board_live.csv"
RUNS = DATA / "form_card_runs.csv"
OUT = DATA / "edgeiq_live_form_match_debug_v1.csv"

def clean_key(x):
    s = str(x or "").upper()
    s = s.replace("’", "").replace("'", "")
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s.strip()

live = pd.read_csv(LIVE, low_memory=False)
runs = pd.read_csv(RUNS, low_memory=False)

live["_hk"] = live["horse_key"].map(clean_key)
runs["_hk"] = runs["horse_key"].map(clean_key)

debug_rows = []

for _, r in live.iterrows():

    hk = r["_hk"]
    horse = r["horse"]

    matched = runs[runs["_hk"] == hk].copy()

    debug_rows.append({
        "horse": horse,
        "horse_key": hk,
        "matched_rows": len(matched),
        "sample_run_dates": " | ".join(matched["run_date"].astype(str).head(5).tolist()) if len(matched) else "",
        "sample_tracks": " | ".join(matched["track"].astype(str).head(5).tolist()) if len(matched) else "",
        "sample_ratings": " | ".join(matched["run_rating"].astype(str).head(5).tolist()) if len(matched) else "",
        "sample_horse_names": " | ".join(matched["horse"].astype(str).head(5).tolist()) if len(matched) else "",
    })

debug = pd.DataFrame(debug_rows)

debug.to_csv(OUT, index=False)

print(debug.to_string(index=False))
print()
print("SAVED:", OUT)
