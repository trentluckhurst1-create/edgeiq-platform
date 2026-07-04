import pandas as pd
from pathlib import Path
import re

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

form_path = DATA / "edgeiq_form_enrichment_feed_v2.csv"
board_path = DATA / "edgeiq_live_runner_board_v1.csv"
backup = DATA / "edgeiq_form_enrichment_feed_v2_BACKUP_BEFORE_RUNNER_KEY_FIX_20260628.csv"
summary_out = DATA / "edgeiq_form_runner_key_fix_v1_summary.csv"

def clean(v):
    return str(v).strip().upper() if pd.notna(v) else ""

def horsekey(v):
    return "".join(ch for ch in clean(v) if ch.isalnum())

def norm_race(v):
    s = clean(v).replace("R", "")
    return s

form = pd.read_csv(form_path, low_memory=False)
board = pd.read_csv(board_path, low_memory=False)
form.to_csv(backup, index=False)

board_map = {}
for _, r in board.iterrows():
    k = (clean(r.get("race_date","")), clean(r.get("track","")), norm_race(r.get("race_no","")), horsekey(r.get("horse_key","") or r.get("horse","")))
    board_map[k] = r.get("runner_key","")

fixed = 0
missing = 0

for idx, r in form.iterrows():
    k = (clean(r.get("race_date","")), clean(r.get("track","")), norm_race(r.get("race_no","")), horsekey(r.get("horse_key","") or r.get("horse","")))
    rk = board_map.get(k, "")
    if rk:
        if "runner_key" not in form.columns or str(form.at[idx, "runner_key"]).strip() != str(rk).strip():
            form.at[idx, "runner_key"] = rk
            fixed += 1
    else:
        missing += 1

form.to_csv(form_path, index=False)

summary = pd.DataFrame([{
    "status": "EDGEIQ_FORM_RUNNER_KEY_FIXED",
    "form_rows": len(form),
    "runner_key_populated": int(form["runner_key"].astype(str).str.strip().ne("").sum()),
    "fixed_rows": fixed,
    "missing_runner_key": missing,
    "pricing_maths_changed": "NO",
    "v6_1_changed": "NO",
    "v7_2g2_changed": "NO",
}])
summary.to_csv(summary_out, index=False)
print(summary.to_string(index=False))
