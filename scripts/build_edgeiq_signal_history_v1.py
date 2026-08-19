import re
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

BOARD_IN = DATA / "edgeiq_execution_board_v2_clean.csv"
HISTORY = DATA / "edgeiq_signal_history_v1.csv"
AUDIT = DATA / "edgeiq_signal_history_v1_summary.csv"

def canon(x):
    s = "" if pd.isna(x) else str(x).upper().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]+", "", s)
    return s

def money_num(x):
    try:
        return float(str(x).replace("$", "").strip())
    except Exception:
        return np.nan

def pct_num(x):
    try:
        return float(str(x).replace("%", "").strip())
    except Exception:
        return np.nan

def main():
    if not BOARD_IN.exists():
        raise FileNotFoundError(f"Missing board: {BOARD_IN}")

    board = pd.read_csv(BOARD_IN).copy()

    signal_date = datetime.now().strftime("%Y-%m-%d")
    archived_at = datetime.now().isoformat(timespec="seconds")

    board["signal_date"] = signal_date
    board["archived_at"] = archived_at
    board["horse_canon"] = board["horse"].apply(canon)
    board["fair_price_num"] = board["fair"].apply(money_num)
    board["market_price_num"] = board["market"].apply(money_num)
    board["overlay_pct_num"] = board["edge"].apply(pct_num)

    board["signal_id"] = (
        board["signal_date"].astype(str) + "|" +
        board["track"].astype(str).str.upper().str.strip() + "|" +
        board["race_no"].astype(str).str.strip() + "|" +
        board["horse_canon"]
    )

    board["settlement_source"] = ""
    board["result_status"] = "PENDING"
    board["finish_position"] = ""
    board["won"] = ""
    board["placed"] = ""
    board["profit_1u_win"] = ""
    board["profit_1u_place"] = ""

    keep = [
        "signal_id",
        "signal_date",
        "archived_at",
        "track",
        "race_no",
        "horse",
        "horse_canon",
        "action",
        "confidence",
        "execution_confidence_score_v1",
        "fair_price_num",
        "market_price_num",
        "overlay_pct_num",
        "runner_score_v3_1",
        "strength_adjusted_rating_v4",
        "runner_rank_v7_2",
        "governance_band_v7_2",
        "projection_status_v6",
        "live_race_strength_band_v2",
        "horse_quality_score_v1",
        "data_quality_score_v1",
        "race_quality_score_v1",
        "market_opportunity_score_v1",
        "decision_reason",
        "settlement_source",
        "result_status",
        "finish_position",
        "won",
        "placed",
        "profit_1u_win",
        "profit_1u_place",
    ]

    new_rows = board[[c for c in keep if c in board.columns]].copy()

    if HISTORY.exists():
        hist = pd.read_csv(HISTORY)
        existing_ids = set(hist["signal_id"].astype(str)) if "signal_id" in hist.columns else set()
        add = new_rows[~new_rows["signal_id"].astype(str).isin(existing_ids)].copy()
        combined = pd.concat([hist, add], ignore_index=True)
    else:
        add = new_rows.copy()
        combined = add.copy()

    combined.to_csv(HISTORY, index=False)

    summary = pd.DataFrame([
        {"metric": "current_board_rows", "value": len(board)},
        {"metric": "new_rows_appended", "value": len(add)},
        {"metric": "history_total_rows", "value": len(combined)},
        {"metric": "pending_rows", "value": int((combined["result_status"].astype(str) == "PENDING").sum()) if "result_status" in combined.columns else ""},
    ])
    summary.to_csv(AUDIT, index=False)

    print("[SIGNAL_HISTORY_V1] COMPLETE")
    print(f"current_board_rows={len(board)}")
    print(f"new_rows_appended={len(add)}")
    print(f"history_total_rows={len(combined)}")
    print(f"wrote={HISTORY}")
    print(f"audit={AUDIT}")

if __name__ == "__main__":
    main()
