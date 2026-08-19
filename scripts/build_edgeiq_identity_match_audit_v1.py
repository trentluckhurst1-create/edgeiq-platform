from pathlib import Path
import pandas as pd
import re

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_identity_match_audit_v1.csv"
SUMMARY = DATA / "edgeiq_identity_match_audit_summary_v1.csv"

FILES = {
    "live": DATA / "edgeiq_execution_board_live.csv",
    "official": DATA / "edgeiq_official_runs_master_v1.csv",
    "sectionals": DATA / "edgeiq_sectional_master_v1.csv",
    "race_fields": DATA / "race_fields.csv",
    "form_runs": DATA / "form_card_runs.csv",
    "form_summary": DATA / "form_card_summary.csv",
}

def read(path):
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)

def clean_key(x):
    s = str(x or "").upper()
    s = s.replace("’", "").replace("'", "")
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s.strip()

def find_col(df, names):
    if df.empty:
        return None
    m = {str(c).lower().strip(): c for c in df.columns}
    for n in names:
        if n.lower() in m:
            return m[n.lower()]
    return None

dfs = {k: read(v) for k, v in FILES.items()}

live = dfs["live"].copy()
if live.empty:
    raise SystemExit("NO LIVE FILE FOUND")

live_horse_col = find_col(live, ["horse", "runner", "horse_name", "selection"])
live_track_col = find_col(live, ["track", "venue"])
live_date_col = find_col(live, ["race_date", "date"])
live_race_col = find_col(live, ["race_no", "race_number"])

live["audit_horse"] = live[live_horse_col].astype(str) if live_horse_col else ""
live["audit_horse_key"] = live["audit_horse"].map(clean_key)
live["audit_track"] = live[live_track_col].astype(str) if live_track_col else ""
live["audit_date"] = live[live_date_col].astype(str) if live_date_col else ""
live["audit_race_no"] = pd.to_numeric(live[live_race_col], errors="coerce") if live_race_col else None

rows = []

for _, r in live.iterrows():
    horse = r["audit_horse"]
    key = r["audit_horse_key"]
    track = str(r["audit_track"])
    date = str(r["audit_date"])
    race_no = r["audit_race_no"]

    row = {
        "horse": horse,
        "horse_key": key,
        "track": track,
        "race_date": date,
        "race_no": race_no,
    }

    for name, df in dfs.items():
        if name == "live" or df.empty:
            continue

        hcol = find_col(df, ["horse_key", "runner_key", "clean_horse_key"])
        raw_hcol = find_col(df, ["horse", "runner", "horse_name", "selection"])
        tcol = find_col(df, ["track", "venue"])
        dcol = find_col(df, ["race_date", "date", "run_date"])
        rcol = find_col(df, ["race_no", "race_number"])

        temp = df.copy()

        if hcol:
            temp["_key"] = temp[hcol].map(clean_key)
        elif raw_hcol:
            temp["_key"] = temp[raw_hcol].map(clean_key)
        else:
            temp["_key"] = ""

        horse_only = temp[temp["_key"].eq(key)]
        row[f"{name}_horse_only_rows"] = len(horse_only)

        exact = horse_only.copy()

        if tcol and track:
            exact = exact[exact[tcol].astype(str).str.upper().str.strip().eq(track.upper().strip())]

        if dcol and date and date.lower() not in {"nan", "none", ""}:
            exact = exact[exact[dcol].astype(str).str[:10].eq(date[:10])]

        if rcol and pd.notna(race_no):
            exact_race = pd.to_numeric(exact[rcol], errors="coerce")
            exact = exact[exact_race.eq(float(race_no))]

        row[f"{name}_exact_rows"] = len(exact)

        if len(horse_only) == 0:
            row[f"{name}_status"] = "NO_HORSE_KEY_MATCH"
        elif len(exact) == 0:
            row[f"{name}_status"] = "HORSE_MATCH_ONLY_CONTEXT_FAIL"
        else:
            row[f"{name}_status"] = "EXACT_MATCH"

    rows.append(row)

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary_rows = []
for name in ["official", "sectionals", "race_fields", "form_runs", "form_summary"]:
    status_col = f"{name}_status"
    if status_col in out.columns:
        counts = out[status_col].value_counts(dropna=False).to_dict()
        summary_rows.append({
            "source": name,
            "exact_match": counts.get("EXACT_MATCH", 0),
            "horse_only_context_fail": counts.get("HORSE_MATCH_ONLY_CONTEXT_FAIL", 0),
            "no_horse_key_match": counts.get("NO_HORSE_KEY_MATCH", 0),
            "live_runners": len(out),
            "exact_match_pct": round(counts.get("EXACT_MATCH", 0) / max(len(out), 1) * 100, 2),
        })

summary = pd.DataFrame(summary_rows)
summary.to_csv(SUMMARY, index=False)

print("SAVED:", OUT)
print("SAVED:", SUMMARY)
print(summary.to_string(index=False))
