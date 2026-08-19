from pathlib import Path
import pandas as pd
import re

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"
SCRIPT = DATA / "edgeiq_form_gap_priority_v1.csv"

LIVE = DATA / "edgeiq_execution_board_live.csv"
SUMMARY = DATA / "form_card_summary.csv"
FORM_RUNS = DATA / "form_card_runs.csv"
OFFICIAL = DATA / "edgeiq_official_runs_master_v1.csv"
RACE_FIELDS = DATA / "race_fields.csv"

def clean_key(x):
    s = str(x or "").upper()
    s = s.replace("’", "").replace("'", "")
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s.strip()

live = pd.read_csv(LIVE, low_memory=False)
summary = pd.read_csv(SUMMARY, low_memory=False)
form_runs = pd.read_csv(FORM_RUNS, low_memory=False)
official = pd.read_csv(OFFICIAL, low_memory=False)
race_fields = pd.read_csv(RACE_FIELDS, low_memory=False)

for df in [live, summary, form_runs, official, race_fields]:
    if "horse_key" in df.columns:
        df["_hk"] = df["horse_key"].map(clean_key)
    elif "horse" in df.columns:
        df["_hk"] = df["horse"].map(clean_key)
    else:
        df["_hk"] = ""

rows = []

for _, r in live.iterrows():
    hk = r["_hk"]
    horse = r["horse"]

    rows.append({
        "horse": horse,
        "horse_key": hk,
        "live_track": r.get("track", ""),
        "live_race_date": r.get("race_date", ""),
        "live_race_no": r.get("race_no", ""),
        "has_form_summary": int(summary["_hk"].eq(hk).any()),
        "form_summary_rows": int(summary["_hk"].eq(hk).sum()),
        "form_runs_rows": int(form_runs["_hk"].eq(hk).sum()),
        "official_runs_rows": int(official["_hk"].eq(hk).sum()),
        "race_fields_rows": int(race_fields["_hk"].eq(hk).sum()),
        "gap_type": (
            "SUMMARY_ONLY_NEEDS_RAW_FORM_RUNS"
            if summary["_hk"].eq(hk).any() and not form_runs["_hk"].eq(hk).any()
            else "OFFICIAL_ARCHIVE_ONLY"
            if official["_hk"].eq(hk).any() and not form_runs["_hk"].eq(hk).any()
            else "NO_FORM_SOURCE"
        ),
        "recommended_next_action": (
            "BACKFILL FORM_CARD_RUNS FROM RA PROFILE_URL"
            if summary["_hk"].eq(hk).any() and not form_runs["_hk"].eq(hk).any()
            else "EXTRACT RAW RUNS FROM OFFICIAL_MASTER"
            if official["_hk"].eq(hk).any() and not form_runs["_hk"].eq(hk).any()
            else "FETCH HORSE PROFILE FROM ACTIVE LIVE BOARD URL"
        )
    })

out = pd.DataFrame(rows)
out.to_csv(SCRIPT, index=False)

print(out.to_string(index=False))
print()
print("SAVED:", SCRIPT)
