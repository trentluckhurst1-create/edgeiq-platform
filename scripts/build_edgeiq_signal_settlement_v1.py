import re
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HISTORY = DATA / "edgeiq_signal_history_v1.csv"
TAB_RESULTS = DATA / "edgeiq_tab_results_warehouse_v1.csv"
OUT = DATA / "edgeiq_signal_history_v1_settled.csv"
AUDIT = DATA / "edgeiq_signal_history_v1_settlement_summary.csv"

def canon(x):
    s = "" if pd.isna(x) else str(x).upper().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]+", "", s)
    return s

def norm_track(x):
    return "" if pd.isna(x) else str(x).upper().strip()

def main():
    hist = pd.read_csv(HISTORY).copy()

    if (not TAB_RESULTS.exists()) or TAB_RESULTS.stat().st_size == 0:
        hist.to_csv(OUT, index=False)
        pd.DataFrame([
            {"metric":"history_rows","value":len(hist)},
            {"metric":"tab_results_file_found","value":"NO_OR_EMPTY"},
            {"metric":"settled_rows","value":0},
            {"metric":"pending_rows","value":len(hist)},
            {"metric":"profit_1u_win","value":0},
            {"metric":"roi_1u_win","value":0},
        ]).to_csv(AUDIT, index=False)
        print("[SIGNAL_SETTLEMENT_V1] TAB results missing/empty")
        return

    try:
        tab = pd.read_csv(TAB_RESULTS)
    except Exception:
        tab = pd.DataFrame()

    if len(tab) == 0 or "finish_position" not in tab.columns:
        hist.to_csv(OUT, index=False)
        pd.DataFrame([
            {"metric":"history_rows","value":len(hist)},
            {"metric":"tab_results_file_found","value":"YES_EMPTY"},
            {"metric":"settled_rows","value":0},
            {"metric":"pending_rows","value":len(hist)},
            {"metric":"profit_1u_win","value":0},
            {"metric":"roi_1u_win","value":0},
        ]).to_csv(AUDIT, index=False)
        print("[SIGNAL_SETTLEMENT_V1] TAB results has no settlement rows yet")
        return

    hist["join_date"] = hist["signal_date"].astype(str).str.slice(0,10)
    hist["join_track"] = hist["track"].map(norm_track)
    hist["join_race_no"] = pd.to_numeric(hist["race_no"], errors="coerce").astype("Int64")
    hist["join_horse"] = hist["horse"].map(canon)

    tab["join_date"] = tab["meeting_date"].astype(str).str.slice(0,10)
    tab["join_track"] = tab["track"].map(norm_track)
    tab["join_race_no"] = pd.to_numeric(tab["race_no"], errors="coerce").astype("Int64")
    tab["join_horse"] = tab["horse"].map(canon)
    tab["finish_position_num"] = pd.to_numeric(tab["finish_position"], errors="coerce")

    tab = tab[tab["finish_position_num"].notna()].drop_duplicates(
        ["join_date","join_track","join_race_no","join_horse"],
        keep="last"
    )

    out = hist.merge(
        tab[["join_date","join_track","join_race_no","join_horse","finish_position_num"]],
        on=["join_date","join_track","join_race_no","join_horse"],
        how="left"
    )

    matched = out["finish_position_num"].notna()
    out.loc[matched, "settlement_source"] = "TAB"
    out.loc[matched, "result_status"] = "SETTLED"
    out.loc[matched, "finish_position"] = out.loc[matched, "finish_position_num"]
    out.loc[matched, "won"] = out.loc[matched, "finish_position_num"].eq(1).astype(int)
    out.loc[matched, "placed"] = out.loc[matched, "finish_position_num"].le(3).astype(int)

    market = pd.to_numeric(out["market_price_num"], errors="coerce")
    out.loc[matched, "profit_1u_win"] = np.where(out.loc[matched, "finish_position_num"].eq(1), market.loc[matched] - 1, -1)
    out.loc[matched, "settled_at"] = datetime.now().isoformat(timespec="seconds")

    out = out.drop(columns=[c for c in ["finish_position_num"] if c in out.columns])
    out.to_csv(OUT, index=False)

    settled = out[out["result_status"].astype(str).str.upper().eq("SETTLED")]
    profit = pd.to_numeric(settled["profit_1u_win"], errors="coerce").sum() if len(settled) else 0
    roi = profit / len(settled) if len(settled) else 0

    pd.DataFrame([
        {"metric":"history_rows","value":len(out)},
        {"metric":"tab_results_file_found","value":"YES"},
        {"metric":"settled_rows","value":len(settled)},
        {"metric":"pending_rows","value":int((out["result_status"].astype(str).str.upper()=="PENDING").sum())},
        {"metric":"wins","value":int(pd.to_numeric(settled.get("won", pd.Series(dtype=float)), errors="coerce").sum()) if len(settled) else 0},
        {"metric":"profit_1u_win","value":round(profit,2)},
        {"metric":"roi_1u_win","value":round(roi,4)},
    ]).to_csv(AUDIT, index=False)

    print("[SIGNAL_SETTLEMENT_V1] COMPLETE")
    print(f"settled_rows={len(settled)}")
    print(f"profit_1u_win={round(profit,2)}")

if __name__ == "__main__":
    main()
