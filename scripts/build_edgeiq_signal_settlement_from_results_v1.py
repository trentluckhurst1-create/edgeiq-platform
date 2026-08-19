import re
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HISTORY = DATA / "edgeiq_signal_history_v1.csv"
RESULTS = DATA / "edgeiq_racingcom_results_warehouse_v1.csv"

OUT = DATA / "edgeiq_signal_history_v1_settled.csv"
SUMMARY = DATA / "edgeiq_signal_settlement_from_results_v1_summary.csv"
BY_ACTION = DATA / "edgeiq_signal_performance_by_action_v1.csv"
BY_CONF = DATA / "edgeiq_signal_performance_by_confidence_v1.csv"
BY_GOV = DATA / "edgeiq_signal_performance_by_governance_v1.csv"

def canon(x):
    s = "" if pd.isna(x) else str(x).upper().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]+", "", s)
    return s

def norm_track(x):
    return "" if pd.isna(x) else str(x).upper().strip()

def pos_num(x):
    s = "" if pd.isna(x) else str(x).upper().strip()
    if s in ["", "NAN", "NONE", "SCR", "SCRATCHED"]:
        return np.nan
    m = re.search(r"\d+", s)
    return float(m.group(0)) if m else np.nan

def metric_group(df, col):
    if len(df) == 0 or col not in df.columns:
        return pd.DataFrame(columns=[col, "bets", "wins", "places", "profit_1u_win", "roi_1u_win", "strike_rate", "place_rate"])

    g = df.groupby(col, dropna=False).agg(
        bets=("signal_id", "count"),
        wins=("won", "sum"),
        places=("placed", "sum"),
        profit_1u_win=("profit_1u_win", "sum"),
    ).reset_index()

    g["roi_1u_win"] = (g["profit_1u_win"] / g["bets"]).round(4)
    g["strike_rate"] = (g["wins"] / g["bets"]).round(4)
    g["place_rate"] = (g["places"] / g["bets"]).round(4)
    g["profit_1u_win"] = g["profit_1u_win"].round(2)
    return g.sort_values("profit_1u_win", ascending=False)

def main():
    hist = pd.read_csv(HISTORY).copy()
    res = pd.read_csv(RESULTS).copy()

    date_source = "event_date" if "event_date" in hist.columns else "signal_date"

    hist["join_date"] = hist[date_source].astype(str).str.slice(0, 10)
    hist["join_track"] = hist["track"].map(norm_track)
    hist["join_race_no"] = pd.to_numeric(hist["race_no"], errors="coerce").astype("Int64")
    hist["join_horse"] = hist["horse"].map(canon)

    date_col = "meeting_date" if "meeting_date" in res.columns else "race_date"
    horse_col = "horseName" if "horseName" in res.columns else "horse"
    finish_col = "finishPosition" if "finishPosition" in res.columns else "finish_position"

    res["join_date"] = res[date_col].astype(str).str.slice(0, 10)
    res["join_track"] = res["track"].map(norm_track)
    res["join_race_no"] = pd.to_numeric(res["race_no"], errors="coerce").astype("Int64")
    res["join_horse"] = res[horse_col].map(canon)
    res["finish_position_result_v1"] = res[finish_col].apply(pos_num)

    keep = ["join_date", "join_track", "join_race_no", "join_horse", "finish_position_result_v1"]

    for c in ["sp", "margin", "raceTime", "raceClass", "trackCondition", "jockey", "trainer"]:
        if c in res.columns:
            keep.append(c)

    res_keep = res[keep].drop_duplicates(
        ["join_date", "join_track", "join_race_no", "join_horse"],
        keep="last"
    )

    out = hist.merge(
        res_keep,
        on=["join_date", "join_track", "join_race_no", "join_horse"],
        how="left",
        indicator=True
    )

    matched = out["_merge"].eq("both") & out["finish_position_result_v1"].notna()

    for c in ["settlement_source", "result_status", "finish_position", "won", "placed", "profit_1u_win", "profit_1u_place", "settled_at"]:
        if c not in out.columns:
            out[c] = ""

    for c in ["settlement_source", "result_status", "finish_position", "won", "placed", "profit_1u_win", "profit_1u_place", "settled_at"]:
        out[c] = out[c].astype("object")

    out.loc[matched, "settlement_source"] = "RACING_COM"
    out.loc[matched, "result_status"] = "SETTLED"
    out.loc[~matched, "result_status"] = out.loc[~matched, "result_status"].replace("", "PENDING")

    out.loc[matched, "finish_position"] = out.loc[matched, "finish_position_result_v1"]
    out.loc[matched, "won"] = out.loc[matched, "finish_position_result_v1"].eq(1).astype(int)
    out.loc[matched, "placed"] = out.loc[matched, "finish_position_result_v1"].le(3).astype(int)

    market = pd.to_numeric(out["market_price_num"], errors="coerce")
    out.loc[matched, "profit_1u_win"] = np.where(
        out.loc[matched, "finish_position_result_v1"].eq(1),
        market.loc[matched] - 1.0,
        -1.0
    )

    out.loc[matched, "settled_at"] = datetime.now().isoformat(timespec="seconds")
    out = out.drop(columns=[c for c in ["_merge"] if c in out.columns])
    out.to_csv(OUT, index=False)

    settled = out[out["result_status"].astype(str).str.upper().eq("SETTLED")].copy()
    settled["won"] = pd.to_numeric(settled["won"], errors="coerce").fillna(0)
    settled["placed"] = pd.to_numeric(settled["placed"], errors="coerce").fillna(0)
    settled["profit_1u_win"] = pd.to_numeric(settled["profit_1u_win"], errors="coerce").fillna(0)

    bets = len(settled)
    wins = int(settled["won"].sum()) if bets else 0
    places = int(settled["placed"].sum()) if bets else 0
    profit = settled["profit_1u_win"].sum() if bets else 0
    roi = profit / bets if bets else 0

    pd.DataFrame([
        {"metric": "signal_rows", "value": len(out)},
        {"metric": "date_source_used", "value": date_source},
        {"metric": "settled_rows", "value": bets},
        {"metric": "pending_rows", "value": int((out["result_status"].astype(str).str.upper() == "PENDING").sum())},
        {"metric": "wins", "value": wins},
        {"metric": "places", "value": places},
        {"metric": "profit_1u_win", "value": round(profit, 2)},
        {"metric": "roi_1u_win", "value": round(roi, 4)},
        {"metric": "strike_rate", "value": round(wins / bets, 4) if bets else 0},
        {"metric": "place_rate", "value": round(places / bets, 4) if bets else 0},
    ]).to_csv(SUMMARY, index=False)

    metric_group(settled, "action").to_csv(BY_ACTION, index=False)
    metric_group(settled, "confidence").to_csv(BY_CONF, index=False)
    metric_group(settled, "governance_band_v7_2").to_csv(BY_GOV, index=False)

    print("[SIGNAL_SETTLEMENT_FROM_RESULTS_V1] COMPLETE")
    print(f"date_source={date_source}")
    print(f"signals={len(out)}")
    print(f"settled={bets}")
    print(f"pending={(out['result_status'].astype(str).str.upper() == 'PENDING').sum()}")
    print(f"profit_1u_win={round(profit, 2)}")
    print(f"roi_1u_win={round(roi, 4)}")

if __name__ == "__main__":
    main()
