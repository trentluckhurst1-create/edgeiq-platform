from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import re

DATA = Path("public/data")
FILES = [
    DATA / "gear_changes.csv",
    DATA / "edgeiq_vic_three_day_meeting_universe.csv",
    DATA / "edgeiq_live_terminal_feed_v1.csv",
    DATA / "edgeiq_live_runner_board_v1.csv",
    DATA / "edgeiq_live_runner_board_governed_v1.csv",
    DATA / "edgeiq_graphql_getRacesForMeet_meeting_warehouse_v1.csv",
    DATA / "edgeiq_graphql_master_v2.csv",
    DATA / "edgeiq_official_runs_master_v1.csv",
]
LIVE = DATA / "edgeiq_live_runner_board_governed_v1.csv"
GEAR = DATA / "gear_changes.csv"
OUT = DATA / "edgeiq_gear_pipeline_audit_v1.csv"
SUMMARY = DATA / "edgeiq_gear_pipeline_audit_v1_summary.csv"
REPORT = DATA / "edgeiq_gear_pipeline_audit_v1_report.txt"

def clean(v):
    return "" if pd.isna(v) else str(v).strip()

def norm_track(v):
    return re.sub(r"\s+", " ", clean(v).upper()).strip()

def norm_race(v):
    s = clean(v).upper().replace("R", "")
    try:
        return str(int(float(s)))
    except Exception:
        return s

def norm_horse(v):
    return re.sub(r"[^A-Z0-9]+", "", clean(v).upper())

def find_col(df, names):
    lower = {c.lower(): c for c in df.columns}
    for n in names:
        if n.lower() in lower:
            return lower[n.lower()]
    for c in df.columns:
        cl = c.lower()
        if any(n.lower() in cl for n in names):
            return c
    return None

def is_nonblank(s):
    return s.astype(str).str.strip().ne("") & s.notna()

def key_full(row, date_col, track_col, race_col, horse_col):
    return "|".join([clean(row.get(date_col, "")), norm_track(row.get(track_col, "")), norm_race(row.get(race_col, "")), norm_horse(row.get(horse_col, ""))])

def key_loose(row, track_col, race_col, horse_col):
    return "|".join([norm_track(row.get(track_col, "")), norm_race(row.get(race_col, "")), norm_horse(row.get(horse_col, ""))])

rows = []
summary = []
first_disappear = ""
seen_gear_source = False
for path in FILES:
    rec = {
        "file_name": path.name,
        "exists": "YES" if path.exists() else "NO",
        "rows": 0,
        "columns": 0,
        "gear_columns": "",
        "gear_column_count": 0,
        "gear_nonblank_columns": "",
        "gear_nonblank_rows_max": 0,
        "has_race_date": "NO",
        "has_track": "NO",
        "has_race_no": "NO",
        "has_horse_key": "NO",
        "has_horse": "NO",
        "role": "PIPELINE_FILE",
    }
    if path.exists():
        try:
            df = pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)
            rec["rows"] = len(df)
            rec["columns"] = len(df.columns)
            gear_cols = [c for c in df.columns if "gear" in c.lower()]
            rec["gear_columns"] = "|".join(gear_cols)
            rec["gear_column_count"] = len(gear_cols)
            nb = []
            max_nb = 0
            for c in gear_cols:
                cnt = int(is_nonblank(df[c]).sum())
                if cnt:
                    nb.append(f"{c}:{cnt}")
                    max_nb = max(max_nb, cnt)
            rec["gear_nonblank_columns"] = "|".join(nb)
            rec["gear_nonblank_rows_max"] = max_nb
            rec["has_race_date"] = "YES" if find_col(df, ["race_date", "date"]) else "NO"
            rec["has_track"] = "YES" if find_col(df, ["track", "venue"]) else "NO"
            rec["has_race_no"] = "YES" if find_col(df, ["race_no", "race_number"]) else "NO"
            rec["has_horse_key"] = "YES" if find_col(df, ["horse_key"]) else "NO"
            rec["has_horse"] = "YES" if find_col(df, ["horse", "horse_name", "runner_name"]) else "NO"
            if path.name == "gear_changes.csv":
                seen_gear_source = True
                rec["role"] = "RECOMMENDED_CURRENT_GEAR_SOURCE"
            elif seen_gear_source and not first_disappear and max_nb == 0:
                first_disappear = path.name
        except Exception as exc:
            rec["role"] = f"READ_ERROR: {exc}"
    rows.append(rec)

full_match = loose_match = live_rows = gear_rows = 0
current_date_tracks = ""
recommended = "gear_changes.csv"
if LIVE.exists() and GEAR.exists():
    live = pd.read_csv(LIVE, dtype=str, keep_default_na=False, low_memory=False)
    gear = pd.read_csv(GEAR, dtype=str, keep_default_na=False, low_memory=False)
    live_rows = len(live)
    gear_rows = len(gear)
    ldate = find_col(live, ["race_date", "date"])
    ltrack = find_col(live, ["track", "venue"])
    lrace = find_col(live, ["race_no", "race_number"])
    lhorse = find_col(live, ["horse_key", "horse", "horse_name"])
    gdate = find_col(gear, ["race_date", "date"])
    gtrack = find_col(gear, ["track", "venue"])
    grace = find_col(gear, ["race_no", "race_number"])
    ghorse = find_col(gear, ["horse_key", "horse", "horse_name"])
    if all([ldate, ltrack, lrace, lhorse, gdate, gtrack, grace, ghorse]):
        live_full = set(live.apply(lambda r: key_full(r, ldate, ltrack, lrace, lhorse), axis=1))
        gear_full = set(gear.apply(lambda r: key_full(r, gdate, gtrack, grace, ghorse), axis=1))
        live_loose = set(live.apply(lambda r: key_loose(r, ltrack, lrace, lhorse), axis=1))
        gear_loose = set(gear.apply(lambda r: key_loose(r, gtrack, grace, ghorse), axis=1))
        full_match = len(live_full & gear_full)
        loose_match = len(live_loose & gear_loose)
        current_date_tracks = "; ".join(sorted(set(live[ldate].astype(str) + " " + live[ltrack].astype(str))))

summary_rows = [
    {"metric": "files_audited", "value": len(rows)},
    {"metric": "live_rows", "value": live_rows},
    {"metric": "gear_changes_rows", "value": gear_rows},
    {"metric": "full_key_match_count", "value": full_match},
    {"metric": "loose_key_match_count", "value": loose_match},
    {"metric": "first_file_where_gear_disappears", "value": first_disappear or "NOT_IDENTIFIED"},
    {"metric": "recommended_permanent_join_source", "value": ("gear_changes.csv after refresh from upstream GraphQL/official gear fields" if loose_match == 0 else recommended)},
    {"metric": "current_live_date_track_scope", "value": current_date_tracks},
    {"metric": "status", "value": "GEAR_OVERLAP_FOUND" if loose_match else "NO_CURRENT_GEAR_OVERLAP_FOUND"},
    {"metric": "production_changed", "value": "NO"},
    {"metric": "pricing_changed", "value": "NO"},
]

pd.DataFrame(rows).to_csv(OUT, index=False)
pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)
REPORT.write_text("\n".join([
    "EDGEIQ_GEAR_PIPELINE_AUDIT_V1",
    "==============================",
    f"Live rows: {live_rows}",
    f"Gear changes rows: {gear_rows}",
    f"Full key match count: {full_match}",
    f"Loose key match count: {loose_match}",
    f"First file where gear disappears: {first_disappear or 'NOT_IDENTIFIED'}",
    f"Recommended permanent join source: {("gear_changes.csv after refresh from upstream GraphQL/official gear fields" if loose_match == 0 else recommended)}",
    "Production changed: NO",
    "Pricing changed: NO",
    f"Built at: {datetime.now(timezone.utc).isoformat()}",
]) + "\n", encoding="utf-8")
print("GEAR_PIPELINE_AUDIT_COMPLETE", full_match, loose_match)

