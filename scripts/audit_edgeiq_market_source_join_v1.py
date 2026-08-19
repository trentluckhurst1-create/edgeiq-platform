from pathlib import Path
import pandas as pd
import re
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

BOARD = DATA / "edgeiq_live_runner_board_governed_v1.csv"
OUT = DATA / "edgeiq_market_source_join_audit_v1.csv"
SUMMARY = DATA / "edgeiq_market_source_join_audit_v1_summary.csv"

def key(x):
    return re.sub(r"[^A-Z0-9]+", "", str(x).upper())

board = pd.read_csv(BOARD, dtype=str, keep_default_na=False, low_memory=False)
board["horse_key"] = board["horse"].map(key)
board["track_key"] = board["track"].map(key)
board["race_no_key"] = board["race_no"].astype(str).str.extract(r"(\d+)")[0].fillna(board["race_no"].astype(str))

sources = [
    "edgeiq_market_tape.csv",
    "edgeiq_market_tape_v2.csv",
    "sportsbet_live_market_v1.csv",
    "edgeiq_bookmaker_board_v1.csv",
]

rows = []

for f in sources:
    p = DATA / f
    if not p.exists():
        rows.append({"source": f, "exists": "NO"})
        continue

    src = pd.read_csv(p, dtype=str, keep_default_na=False, low_memory=False)
    src_cols = list(src.columns)

    horse_col = next((c for c in ["horse","runner","runner_name","horse_name"] if c in src_cols), "")
    track_col = next((c for c in ["track","venue","meeting_track"] if c in src_cols), "")
    race_col = next((c for c in ["race_no","race_number","race"] if c in src_cols), "")
    price_col = next((c for c in ["live_price","sportsbet_price","price_win","fixed_win","market_price"] if c in src_cols), "")

    if not horse_col or not price_col:
        rows.append({
            "source": f,
            "exists": "YES",
            "rows": len(src),
            "status": "MISSING_HORSE_OR_PRICE_COL",
            "horse_col": horse_col,
            "track_col": track_col,
            "race_col": race_col,
            "price_col": price_col,
        })
        continue

    src["horse_key"] = src[horse_col].map(key)
    if track_col:
        src["track_key"] = src[track_col].map(key)
    else:
        src["track_key"] = ""

    if race_col:
        src["race_no_key"] = src[race_col].astype(str).str.extract(r"(\d+)")[0].fillna(src[race_col].astype(str))
    else:
        src["race_no_key"] = ""

    price_num = pd.to_numeric(
        src[price_col].astype(str)
        .str.replace("$","",regex=False)
        .str.replace(",","",regex=False)
        .str.strip()
        .replace({"":"nan","-":"nan","SCR":"nan"}),
        errors="coerce"
    )
    src["_price_num"] = price_num

    numeric = src[src["_price_num"].notna()].copy()

    loose_horse_matches = board["horse_key"].isin(set(numeric["horse_key"])).sum()

    if track_col and race_col:
        full_keys = set(zip(numeric["track_key"], numeric["race_no_key"], numeric["horse_key"]))
        full_matches = sum((r.track_key, r.race_no_key, r.horse_key) in full_keys for r in board.itertuples())
    else:
        full_matches = 0

    track_matches = board["track_key"].isin(set(numeric["track_key"])).sum() if track_col else 0

    rows.append({
        "source": f,
        "exists": "YES",
        "rows": len(src),
        "numeric_price_rows": len(numeric),
        "horse_col": horse_col,
        "track_col": track_col,
        "race_col": race_col,
        "price_col": price_col,
        "board_loose_horse_matches": int(loose_horse_matches),
        "board_full_track_race_horse_matches": int(full_matches),
        "board_track_matches": int(track_matches),
        "sample_tracks": " | ".join(sorted(numeric["track_key"].dropna().unique())[:12]),
        "status": "AUDITED"
    })

audit = pd.DataFrame(rows)
audit.to_csv(OUT, index=False)

pd.DataFrame([{
    "status": "EDGEIQ_MARKET_SOURCE_JOIN_AUDIT_V1_BUILT",
    "sources_audited": len(rows),
    "best_full_matches": int(audit.get("board_full_track_race_horse_matches", pd.Series([0])).fillna(0).astype(int).max()),
    "best_loose_horse_matches": int(audit.get("board_loose_horse_matches", pd.Series([0])).fillna(0).astype(int).max()),
    "built_at": datetime.now(timezone.utc).isoformat()
}]).to_csv(SUMMARY, index=False)

print("[EDGEIQ_MARKET_SOURCE_JOIN_AUDIT_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
