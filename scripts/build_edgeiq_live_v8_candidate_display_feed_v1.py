from pathlib import Path
import json
import re
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_live_runner_board_v1.csv"
V8 = DATA / "edgeiq_live_fair_price_v8_interaction_candidate_feed.csv"

OUT = DATA / "edgeiq_live_v8_candidate_display_feed_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_live_v8_candidate_display_feed_v1_summary.csv"
OUT_JSON = DATA / "edgeiq_live_v8_candidate_display_feed_v1.json"

def norm(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper()

def clean_track(x):
    return re.sub(r"[^A-Z0-9]+", " ", norm(x)).strip()

def horse_key(x):
    return re.sub(r"[^A-Z0-9]+", "", norm(x))

def first_existing(df, cols):
    for c in cols:
        if c in df.columns:
            return c
    return None

def join_key(df):
    track_col = first_existing(df, ["track"])
    race_col = first_existing(df, ["race_no", "race_number"])
    horse_col = first_existing(df, ["horse", "horse_name", "horseName"])

    if not track_col or not race_col or not horse_col:
        raise ValueError(f"Cannot build join key. Columns: {list(df.columns)}")

    return (
        df[track_col].map(clean_track)
        + "|R"
        + df[race_col].astype(str).str.extract(r"(\d+)")[0].fillna("")
        + "|"
        + df[horse_col].map(horse_key)
    )

def num(x):
    return pd.to_numeric(x, errors="coerce")

def main():
    missing = [str(p) for p in [LIVE, V8] if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Missing inputs: {missing}")

    live = pd.read_csv(LIVE, low_memory=False)
    v8 = pd.read_csv(V8, low_memory=False)

    live["join_key_v8_display"] = join_key(live)
    v8["join_key_v8_display"] = join_key(v8)

    live_cols = [
        c for c in [
            "track", "race_no", "runner_no", "horse", "barrier", "jockey", "trainer",
            "live_price", "fair_price", "edge_pct", "execution_action",
            "market_state", "confidence_score"
        ]
        if c in live.columns
    ]

    v8_cols = [
        c for c in [
            "join_key_v8_display",
            "v8_interaction_candidate_price",
            "v8_interaction_price_delta",
            "v8_interaction_abs_price_delta",
            "v8_interaction_adjustment_pct",
            "brc_match_level_v8",
            "brc_band_live_v8",
            "tj_band_live_v8",
            "interaction_bucket_v8",
            "v8_candidate_status",
            "v8_candidate_note",
        ]
        if c in v8.columns
    ]

    out = live[live_cols + ["join_key_v8_display"]].merge(
        v8[v8_cols].drop_duplicates("join_key_v8_display"),
        on="join_key_v8_display",
        how="left",
        validate="many_to_one",
    )

    out["v8_candidate_display_status"] = np.where(
        out["v8_candidate_status"].astype(str).str.upper().eq("COMPLETE"),
        "OBSERVATION_ONLY",
        "NO_V8"
    )

    out["v8_candidate_badge"] = np.where(
        out["brc_match_level_v8"].astype(str).str.upper().eq("EXACT"),
        "V8 EXACT",
        np.where(out["brc_match_level_v8"].notna(), "V8 FALLBACK", "NO V8")
    )

    out["v8_candidate_price_display"] = num(out["v8_interaction_candidate_price"]).round(2)
    out["v8_delta_display"] = num(out["v8_interaction_price_delta"]).round(2)
    out["v8_adjustment_pct_display"] = (num(out["v8_interaction_adjustment_pct"]) * 100).round(2)

    out = out.drop(columns=["join_key_v8_display"], errors="ignore")
    out.to_csv(OUT, index=False)

    summary = [
        ["status", "COMPLETE"],
        ["rows", len(out)],
        ["v8_rows", int(out["v8_interaction_candidate_price"].notna().sum())],
        ["observation_only_rows", int(out["v8_candidate_display_status"].eq("OBSERVATION_ONLY").sum())],
        ["fallback_rows", int(out["v8_candidate_badge"].eq("V8 FALLBACK").sum())],
        ["official_fair_price_replaced", "NO"],
        ["edge_execution_staking_changed", "NO"],
    ]

    pd.DataFrame(summary, columns=["metric", "value"]).to_csv(OUT_SUMMARY, index=False)

    OUT_JSON.write_text(json.dumps({
        "status": "COMPLETE",
        "rows": int(len(out)),
        "v8_rows": int(out["v8_interaction_candidate_price"].notna().sum()),
        "fallback_rows": int(out["v8_candidate_badge"].eq("V8 FALLBACK").sum()),
        "official_fair_price_replaced": False,
        "edge_execution_staking_changed": False,
        "outputs": {
            "display_feed": str(OUT),
            "summary": str(OUT_SUMMARY)
        }
    }, indent=2), encoding="utf-8")

    print("[LIVE_V8_CANDIDATE_DISPLAY_FEED_V1] COMPLETE")
    print(f"rows={len(out)}")
    print(f"v8_rows={int(out['v8_interaction_candidate_price'].notna().sum())}")
    print(f"fallback_rows={int(out['v8_candidate_badge'].eq('V8 FALLBACK').sum())}")
    print("official_fair_price_replaced=NO")
    print("edge_execution_staking_changed=NO")

if __name__ == "__main__":
    main()
