import re
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

BOARD_IN = DATA / "edgeiq_execution_board_v2_clean.csv"
RESULTS_IN = DATA / "edgeiq_racingcom_results_warehouse_v1.csv"

OUT = DATA / "edgeiq_execution_outcome_audit_v1.csv"
SUMMARY = DATA / "edgeiq_execution_outcome_audit_v1_summary.csv"

def canon(x):
    s = "" if pd.isna(x) else str(x).upper().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]+", "", s)
    return s

def norm_track(x):
    return "" if pd.isna(x) else str(x).upper().strip()

def pos_num(x):
    try:
        s = str(x).strip().upper()
        if s in ["SCR", "SCRATCHED", ""]:
            return np.nan
        return float(s)
    except Exception:
        return np.nan

def money_num(x):
    try:
        return float(str(x).replace("$", "").strip())
    except Exception:
        return np.nan

def main():
    if not BOARD_IN.exists():
        raise FileNotFoundError(f"Missing board: {BOARD_IN}")
    if not RESULTS_IN.exists():
        raise FileNotFoundError(f"Missing results: {RESULTS_IN}")

    board = pd.read_csv(BOARD_IN)
    results = pd.read_csv(RESULTS_IN)

    board["join_track"] = board["track"].map(norm_track)
    board["join_race_no"] = pd.to_numeric(board["race_no"], errors="coerce").astype("Int64")
    board["join_horse"] = board["horse"].map(canon)

    if "race_date" in board.columns:
        board["join_date"] = board["race_date"].astype(str).str.slice(0, 10)
    else:
        board["join_date"] = "2026-06-07"

    date_col = "meeting_date" if "meeting_date" in results.columns else "race_date"
    track_col = "track"
    race_col = "race_no"
    horse_col = "horseName" if "horseName" in results.columns else "horse"

    results["join_date"] = results[date_col].astype(str).str.slice(0, 10)
    results["join_track"] = results[track_col].map(norm_track)
    results["join_race_no"] = pd.to_numeric(results[race_col], errors="coerce").astype("Int64")
    results["join_horse"] = results[horse_col].map(canon)

    finish_col = "finishPosition" if "finishPosition" in results.columns else "finish_position"
    sp_col = "sp" if "sp" in results.columns else None

    keep = [
        "join_date", "join_track", "join_race_no", "join_horse",
        finish_col,
    ]
    if sp_col:
        keep.append(sp_col)

    res = results[[c for c in keep if c in results.columns]].drop_duplicates(
        ["join_date", "join_track", "join_race_no", "join_horse"],
        keep="last"
    )

    out = board.merge(
        res,
        on=["join_date", "join_track", "join_race_no", "join_horse"],
        how="left",
        indicator=True
    )

    out["result_match_status_v1"] = np.where(out["_merge"].eq("both"), "RESULT_MATCHED", "RESULT_PENDING")
    out["finish_position_v1"] = out[finish_col].apply(pos_num) if finish_col in out.columns else np.nan
    out["won_v1"] = out["finish_position_v1"].eq(1).astype(int)

    out["market_decimal_v1"] = out["market"].apply(money_num) if "market" in out.columns else np.nan
    out["profit_1u_v1"] = np.where(
        out["won_v1"].eq(1),
        out["market_decimal_v1"] - 1.0,
        -1.0
    )
    out.loc[out["result_match_status_v1"].eq("RESULT_PENDING"), "profit_1u_v1"] = np.nan

    out.to_csv(OUT, index=False)

    settled = out[out["result_match_status_v1"].eq("RESULT_MATCHED")].copy()

    if len(settled) > 0:
        profit = settled["profit_1u_v1"].sum()
        bets = len(settled)
        wins = int(settled["won_v1"].sum())
        roi = profit / bets if bets else 0
    else:
        profit = 0
        bets = 0
        wins = 0
        roi = 0

    summary = pd.DataFrame([
        {"metric": "board_rows", "value": len(out)},
        {"metric": "settled_rows", "value": bets},
        {"metric": "pending_rows", "value": int((out["result_match_status_v1"] == "RESULT_PENDING").sum())},
        {"metric": "wins", "value": wins},
        {"metric": "profit_1u", "value": round(profit, 2)},
        {"metric": "roi_1u", "value": round(roi, 4)},
    ])

    summary.to_csv(SUMMARY, index=False)

    print("[EXECUTION_OUTCOME_AUDIT_V1] COMPLETE")
    print(f"board_rows={len(out)}")
    print(f"settled_rows={bets}")
    print(f"pending_rows={(out['result_match_status_v1'] == 'RESULT_PENDING').sum()}")
    print(f"wrote={OUT}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
