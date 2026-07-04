import re
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HISTORY = DATA / "edgeiq_signal_history_v1.csv"
TAB = DATA / "edgeiq_tab_vic_racecards_v1.csv"

OUT = DATA / "edgeiq_signal_history_v1.csv"
AUDIT = DATA / "edgeiq_signal_history_v1_date_repair_audit.csv"

def canon(x):
    s = "" if pd.isna(x) else str(x).upper().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]+", "", s)
    return s

def norm_track(x):
    return "" if pd.isna(x) else str(x).upper().strip()

def main():
    hist = pd.read_csv(HISTORY)
    tab = pd.read_csv(TAB)

    hist["join_track"] = hist["track"].map(norm_track)
    hist["join_race_no"] = pd.to_numeric(hist["race_no"], errors="coerce").astype("Int64")
    hist["join_horse"] = hist["horse"].map(canon)

    tab["join_track"] = tab["meeting_name"].map(norm_track)
    tab["join_race_no"] = pd.to_numeric(tab["race_no"], errors="coerce").astype("Int64")
    tab["join_horse"] = tab["horse"].map(canon)

    map_df = tab[[
        "meeting_date",
        "join_track",
        "join_race_no",
        "join_horse",
    ]].drop_duplicates(["join_track", "join_race_no", "join_horse"], keep="last")

    out = hist.merge(
        map_df,
        on=["join_track", "join_race_no", "join_horse"],
        how="left"
    )

    if "event_date" not in out.columns:
        out["event_date"] = ""

    out["event_date"] = out["event_date"].replace("", np.nan)
    out["event_date"] = out["event_date"].fillna(out["meeting_date"])
    out["event_date"] = out["event_date"].fillna(out["signal_date"])
    out["event_date"] = out["event_date"].astype(str).str.slice(0, 10)

    out["signal_id"] = (
        out["event_date"].astype(str) + "|" +
        out["track"].astype(str).str.upper().str.strip() + "|" +
        out["race_no"].astype(str).str.strip() + "|" +
        out["horse_canon"].astype(str)
    )

    out = out.drop(columns=[c for c in ["meeting_date", "join_track", "join_race_no", "join_horse"] if c in out.columns])

    out.to_csv(OUT, index=False)

    pd.DataFrame([
        {"metric": "rows", "value": len(out)},
        {"metric": "event_date_populated", "value": int(out["event_date"].notna().sum())},
        {"metric": "event_dates", "value": ",".join(sorted(out["event_date"].dropna().unique()))},
    ]).to_csv(AUDIT, index=False)

    print("[SIGNAL_HISTORY_DATE_REPAIR] COMPLETE")
    print(f"rows={len(out)}")
    print(f"event_dates={','.join(sorted(out['event_date'].dropna().unique()))}")
    print(f"wrote={OUT}")
    print(f"audit={AUDIT}")

if __name__ == "__main__":
    main()
