from pathlib import Path
import pandas as pd
import re

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_live_form_source_locator_v1.csv"

LIVE = DATA / "edgeiq_execution_board_live.csv"

SEARCH_FILES = [
    DATA / "form_card_summary.csv",
    DATA / "form_card_runs.csv",
    DATA / "edgeiq_official_runs_master_v1.csv",
    DATA / "race_fields.csv",
    DATA / "runner_form_history.csv",
    DATA / "race_card_report.csv",
    DATA / "race_card_active.csv",
    DATA / "edgeiq_results_master.csv",
    DATA / "race_results.csv",
]

def clean_key(x):
    s = str(x or "").upper()
    s = s.replace("’", "").replace("'", "")
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s.strip()

def find_horse_cols(df):
    cols = []
    for c in df.columns:
        lc = str(c).lower()
        if "horse" in lc or "runner" in lc or "selection" in lc:
            cols.append(c)
    return cols

live = pd.read_csv(LIVE, low_memory=False)
live_keys = set(live["horse_key"].map(clean_key).tolist())
live_horses = dict(zip(live["horse_key"].map(clean_key), live["horse"].astype(str)))

rows = []

for path in SEARCH_FILES:
    if not path.exists():
        continue

    df = pd.read_csv(path, low_memory=False)
    horse_cols = find_horse_cols(df)

    for col in horse_cols:
        temp = df[[col]].copy()
        temp["_key"] = temp[col].map(clean_key)
        matches = temp[temp["_key"].isin(live_keys)]

        for key in live_keys:
            key_matches = matches[matches["_key"].eq(key)]
            rows.append({
                "source_file": path.name,
                "column": col,
                "live_horse": live_horses.get(key, ""),
                "horse_key": key,
                "match_rows": len(key_matches),
                "sample_values": " | ".join(key_matches[col].astype(str).drop_duplicates().head(5).tolist())
            })

out = pd.DataFrame(rows)
out = out.sort_values(["live_horse", "match_rows"], ascending=[True, False])
out.to_csv(OUT, index=False)

print(out[out["match_rows"].gt(0)].to_string(index=False))
print()
print("SAVED:", OUT)
