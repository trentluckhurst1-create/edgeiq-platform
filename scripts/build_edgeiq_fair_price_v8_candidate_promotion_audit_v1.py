from pathlib import Path
import json
import re
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
V8_FEED = DATA / "edgeiq_live_fair_price_v8_interaction_candidate_feed.csv"

OUT = DATA / "edgeiq_fair_price_v8_candidate_promotion_audit_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_fair_price_v8_candidate_promotion_audit_v1_summary.csv"
OUT_CHANGES = DATA / "edgeiq_fair_price_v8_candidate_promotion_audit_decision_changes_v1.csv"
OUT_FALLBACK = DATA / "edgeiq_fair_price_v8_candidate_promotion_audit_fallback_rows_v1.csv"
OUT_JSON = DATA / "edgeiq_fair_price_v8_candidate_promotion_audit_v1.json"

def norm(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper()

def horse_key(x):
    return re.sub(r"[^A-Z0-9]+", "", norm(x))

def clean_track(x):
    return re.sub(r"[^A-Z0-9]+", " ", norm(x)).strip()

def first_existing(df, names):
    for n in names:
        if n in df.columns:
            return n
    return None

def num(x):
    return pd.to_numeric(x, errors="coerce")

def join_key(df):
    track_col = first_existing(df, ["track", "track_x", "track_y"])
    race_col = first_existing(df, ["race_no", "race_number", "race"])
    horse_col = first_existing(df, ["horse", "horse_name", "horseName"])

    if not track_col or not race_col or not horse_col:
        raise ValueError(f"Cannot build join key. Available columns: {list(df.columns)}")

    return (
        df[track_col].map(clean_track)
        + "|R"
        + df[race_col].astype(str).str.extract(r"(\d+)")[0].fillna("")
        + "|"
        + df[horse_col].map(horse_key)
    )

def action_from(edge, confidence):
    e = pd.to_numeric(edge, errors="coerce")
    c = pd.to_numeric(confidence, errors="coerce")

    if pd.isna(e):
        return "PASS"
    if pd.isna(c):
        c = 35.0

    if e >= 18 and c >= 70:
        return "EXECUTE"
    if e >= 10 and c >= 55:
        return "STRONG_WATCH"
    if e >= 6:
        return "WATCH"
    return "PASS"

def boolish(x):
    return str(x).strip().upper() in ["TRUE", "1", "YES", "Y"]

def main():
    missing = [str(p) for p in [LIVE_BOARD, V8_FEED] if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required input files: {missing}")

    live = pd.read_csv(LIVE_BOARD, low_memory=False)
    v8 = pd.read_csv(V8_FEED, low_memory=False)

    live["join_key_v8_promo"] = join_key(live)
    v8["join_key_v8_promo"] = join_key(v8)

    live_track_col = first_existing(live, ["track"])
    live_race_col = first_existing(live, ["race_no", "race_number"])
    live_horse_col = first_existing(live, ["horse", "horse_name", "horseName"])
    live_price_col = first_existing(live, ["live_price", "market_price", "fixed_win", "tab_fixed_win", "sportsbet_price"])
    fair_col = first_existing(live, ["fair_price", "current_fair_price", "official_fair_price", "edgeiq_fair_price", "fair_price_v6"])
    edge_col = first_existing(live, ["edge_pct", "current_edge_pct"])
    action_col = first_existing(live, ["execution_action", "current_execution_action", "post_v3_execution_action"])
    confidence_col = first_existing(live, ["confidence_score", "model_confidence_score", "confidence"])

    v8_price_col = first_existing(v8, ["v8_interaction_candidate_price"])
    v8_status_col = first_existing(v8, ["v8_candidate_status"])
    v8_match_col = first_existing(v8, ["brc_match_level_v8"])
    v8_adj_col = first_existing(v8, ["v8_interaction_adjustment_pct"])
    v8_delta_col = first_existing(v8, ["v8_interaction_price_delta"])

    needed = {
        "live_price_col": live_price_col,
        "fair_col": fair_col,
        "v8_price_col": v8_price_col,
    }
    missing_needed = [k for k, v in needed.items() if v is None]
    if missing_needed:
        raise ValueError(f"Missing required columns: {missing_needed}. Live columns={list(live.columns)} V8 columns={list(v8.columns)}")

    v8_keep = ["join_key_v8_promo", v8_price_col]
    for c in [v8_status_col, v8_match_col, v8_adj_col, v8_delta_col]:
        if c and c not in v8_keep:
            v8_keep.append(c)

    v8_small = v8[v8_keep].drop_duplicates("join_key_v8_promo").copy()
    rename = {v8_price_col: "v8_candidate_fair_price_audit_v1"}
    if v8_status_col:
        rename[v8_status_col] = "v8_candidate_status_audit_v1"
    if v8_match_col:
        rename[v8_match_col] = "brc_match_level_audit_v1"
    if v8_adj_col:
        rename[v8_adj_col] = "v8_interaction_adjustment_pct_audit_v1"
    if v8_delta_col:
        rename[v8_delta_col] = "v8_interaction_price_delta_source_v1"

    v8_small = v8_small.rename(columns=rename)

    out = live.merge(v8_small, on="join_key_v8_promo", how="left", validate="many_to_one")

    out["live_price_audit_v1"] = num(out[live_price_col])
    out["current_fair_price_audit_v1"] = num(out[fair_col])
    out["v8_candidate_fair_price_audit_v1"] = num(out["v8_candidate_fair_price_audit_v1"])

    if edge_col:
        out["current_edge_pct_audit_v1"] = num(out[edge_col])
    else:
        out["current_edge_pct_audit_v1"] = np.where(
            out["current_fair_price_audit_v1"] > 0,
            ((out["live_price_audit_v1"] / out["current_fair_price_audit_v1"]) - 1.0) * 100.0,
            np.nan,
        )

    out["candidate_edge_pct_audit_v1"] = np.where(
        out["v8_candidate_fair_price_audit_v1"] > 0,
        ((out["live_price_audit_v1"] / out["v8_candidate_fair_price_audit_v1"]) - 1.0) * 100.0,
        np.nan,
    )

    out["current_edge_pct_audit_v1"] = out["current_edge_pct_audit_v1"].round(4)
    out["candidate_edge_pct_audit_v1"] = out["candidate_edge_pct_audit_v1"].round(4)
    out["edge_delta_pct_audit_v1"] = (out["candidate_edge_pct_audit_v1"] - out["current_edge_pct_audit_v1"]).round(4)

    out["fair_price_delta_audit_v1"] = (
        out["v8_candidate_fair_price_audit_v1"] - out["current_fair_price_audit_v1"]
    ).round(4)
    out["fair_price_abs_delta_audit_v1"] = out["fair_price_delta_audit_v1"].abs().round(4)

    if confidence_col:
        out["confidence_score_audit_v1"] = num(out[confidence_col])
    else:
        out["confidence_score_audit_v1"] = 35.0

    if action_col:
        out["current_execution_action_audit_v1"] = out[action_col].astype(str).str.strip().str.upper()
    else:
        out["current_execution_action_audit_v1"] = [
            action_from(e, c) for e, c in zip(out["current_edge_pct_audit_v1"], out["confidence_score_audit_v1"])
        ]

    out["candidate_execution_action_audit_v1"] = [
        action_from(e, c) for e, c in zip(out["candidate_edge_pct_audit_v1"], out["confidence_score_audit_v1"])
    ]

    out["decision_changed_flag_audit_v1"] = (
        out["current_execution_action_audit_v1"].fillna("") != out["candidate_execution_action_audit_v1"].fillna("")
    )

    out["fallback_used_flag_audit_v1"] = (
        out.get("brc_match_level_audit_v1", "").astype(str).str.upper().ne("EXACT")
        if "brc_match_level_audit_v1" in out.columns
        else False
    )

    rank_cols = [live_track_col, live_race_col]
    out["current_price_rank_audit_v1"] = out.groupby(rank_cols)["current_fair_price_audit_v1"].rank(method="min", ascending=True)
    out["candidate_price_rank_audit_v1"] = out.groupby(rank_cols)["v8_candidate_fair_price_audit_v1"].rank(method="min", ascending=True)
    out["rank_changed_flag_audit_v1"] = out["current_price_rank_audit_v1"] != out["candidate_price_rank_audit_v1"]

    out["execute_added_flag_audit_v1"] = (
        out["current_execution_action_audit_v1"].ne("EXECUTE")
        & out["candidate_execution_action_audit_v1"].eq("EXECUTE")
    )
    out["execute_removed_flag_audit_v1"] = (
        out["current_execution_action_audit_v1"].eq("EXECUTE")
        & out["candidate_execution_action_audit_v1"].ne("EXECUTE")
    )
    out["watch_added_flag_audit_v1"] = (
        ~out["current_execution_action_audit_v1"].isin(["EXECUTE", "STRONG_WATCH", "WATCH"])
        & out["candidate_execution_action_audit_v1"].isin(["EXECUTE", "STRONG_WATCH", "WATCH"])
    )
    out["watch_removed_flag_audit_v1"] = (
        out["current_execution_action_audit_v1"].isin(["EXECUTE", "STRONG_WATCH", "WATCH"])
        & ~out["candidate_execution_action_audit_v1"].isin(["EXECUTE", "STRONG_WATCH", "WATCH"])
    )

    live_rows = len(out)
    rows_with_v8 = int(out["v8_candidate_fair_price_audit_v1"].notna().sum())
    rows_with_price_change = int((out["fair_price_abs_delta_audit_v1"].fillna(0) > 0).sum())
    decision_changes = int(out["decision_changed_flag_audit_v1"].sum())
    rank_changes = int(out["rank_changed_flag_audit_v1"].sum())
    execute_added = int(out["execute_added_flag_audit_v1"].sum())
    execute_removed = int(out["execute_removed_flag_audit_v1"].sum())
    watch_added = int(out["watch_added_flag_audit_v1"].sum())
    watch_removed = int(out["watch_removed_flag_audit_v1"].sum())
    fallback_rows = int(out["fallback_used_flag_audit_v1"].sum())
    fallback_decision_changes = int((out["fallback_used_flag_audit_v1"] & out["decision_changed_flag_audit_v1"]).sum())

    decision_change_rate = decision_changes / live_rows if live_rows else 0.0

    if rows_with_v8 != live_rows:
        verdict = "V8_CANDIDATE_PROMOTION_REVIEW_MISSING_ROWS"
    elif decision_change_rate <= 0.05 and execute_added <= 2 and fallback_decision_changes <= 1:
        verdict = "V8_CANDIDATE_PROMOTION_READY"
    else:
        verdict = "V8_CANDIDATE_PROMOTION_REVIEW"

    export_cols = []
    for c in [
        live_track_col,
        live_race_col,
        live_horse_col,
        live_price_col,
        fair_col,
        edge_col,
        action_col,
        confidence_col,
        "live_price_audit_v1",
        "current_fair_price_audit_v1",
        "v8_candidate_fair_price_audit_v1",
        "current_edge_pct_audit_v1",
        "candidate_edge_pct_audit_v1",
        "edge_delta_pct_audit_v1",
        "fair_price_delta_audit_v1",
        "fair_price_abs_delta_audit_v1",
        "confidence_score_audit_v1",
        "current_execution_action_audit_v1",
        "candidate_execution_action_audit_v1",
        "decision_changed_flag_audit_v1",
        "current_price_rank_audit_v1",
        "candidate_price_rank_audit_v1",
        "rank_changed_flag_audit_v1",
        "fallback_used_flag_audit_v1",
        "brc_match_level_audit_v1",
        "v8_candidate_status_audit_v1",
        "v8_interaction_adjustment_pct_audit_v1",
        "execute_added_flag_audit_v1",
        "execute_removed_flag_audit_v1",
        "watch_added_flag_audit_v1",
        "watch_removed_flag_audit_v1",
    ]:
        if c and c in out.columns and c not in export_cols:
            export_cols.append(c)

    out[export_cols].to_csv(OUT, index=False)

    changes = out[out["decision_changed_flag_audit_v1"] == True].copy()
    changes[export_cols].to_csv(OUT_CHANGES, index=False)

    fallback = out[out["fallback_used_flag_audit_v1"] == True].copy()
    fallback[export_cols].to_csv(OUT_FALLBACK, index=False)

    summary_rows = [
        ["status", "COMPLETE"],
        ["verdict", verdict],
        ["live_rows", live_rows],
        ["rows_with_v8_candidate_price", rows_with_v8],
        ["rows_with_price_change", rows_with_price_change],
        ["decision_changes", decision_changes],
        ["decision_change_rate", round(decision_change_rate, 6)],
        ["rank_changes", rank_changes],
        ["execute_added", execute_added],
        ["execute_removed", execute_removed],
        ["watch_added", watch_added],
        ["watch_removed", watch_removed],
        ["fallback_rows", fallback_rows],
        ["fallback_rows_with_decision_change", fallback_decision_changes],
        ["mean_abs_price_delta", round(float(out["fair_price_abs_delta_audit_v1"].dropna().mean()), 6)],
        ["max_abs_price_delta", round(float(out["fair_price_abs_delta_audit_v1"].dropna().max()), 6)],
        ["mean_edge_delta_pct", round(float(out["edge_delta_pct_audit_v1"].dropna().mean()), 6)],
        ["max_abs_edge_delta_pct", round(float(out["edge_delta_pct_audit_v1"].dropna().abs().max()), 6)],
        ["official_fair_price_replaced", "NO"],
        ["edge_execution_staking_changed", "NO"],
    ]

    pd.DataFrame(summary_rows, columns=["metric", "value"]).to_csv(OUT_SUMMARY, index=False)

    payload = {
        "status": "COMPLETE",
        "verdict": verdict,
        "live_rows": live_rows,
        "rows_with_v8_candidate_price": rows_with_v8,
        "rows_with_price_change": rows_with_price_change,
        "decision_changes": decision_changes,
        "decision_change_rate": round(decision_change_rate, 6),
        "rank_changes": rank_changes,
        "execute_added": execute_added,
        "execute_removed": execute_removed,
        "watch_added": watch_added,
        "watch_removed": watch_removed,
        "fallback_rows": fallback_rows,
        "fallback_rows_with_decision_change": fallback_decision_changes,
        "official_fair_price_replaced": False,
        "edge_execution_staking_changed": False,
        "outputs": {
            "audit": str(OUT),
            "summary": str(OUT_SUMMARY),
            "decision_changes": str(OUT_CHANGES),
            "fallback_rows": str(OUT_FALLBACK),
        },
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("[V8_CANDIDATE_PROMOTION_AUDIT_V1] COMPLETE")
    print(f"verdict={verdict}")
    print(f"live_rows={live_rows}")
    print(f"rows_with_v8_candidate_price={rows_with_v8}")
    print(f"rows_with_price_change={rows_with_price_change}")
    print(f"decision_changes={decision_changes}")
    print(f"rank_changes={rank_changes}")
    print(f"execute_added={execute_added}")
    print(f"execute_removed={execute_removed}")
    print(f"watch_added={watch_added}")
    print(f"watch_removed={watch_removed}")
    print(f"fallback_rows={fallback_rows}")
    print(f"fallback_rows_with_decision_change={fallback_decision_changes}")
    print("official_fair_price_replaced=NO")
    print("edge_execution_staking_changed=NO")

if __name__ == "__main__":
    main()
