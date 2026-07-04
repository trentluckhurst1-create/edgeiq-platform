from pathlib import Path
import json
import re
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
TJ_V3 = DATA / "edgeiq_live_trainer_jockey_factor_feed_v3.csv"
BRC_REPLAY = DATA / "edgeiq_barrier_rail_condition_bias_replay_v1.csv"

OUT = DATA / "edgeiq_live_fair_price_v8_interaction_candidate_feed.csv"
OUT_SUMMARY = DATA / "edgeiq_live_fair_price_v8_interaction_candidate_feed_summary.csv"
OUT_UNMATCHED = DATA / "edgeiq_live_fair_price_v8_interaction_candidate_feed_unmatched.csv"
OUT_JSON = DATA / "edgeiq_live_fair_price_v8_interaction_candidate_feed.json"

RULE_SET = "RULE_SET_C_FILTER_HEAVY"

RULES = {
    "TJ_POSITIVE + BRC_POSITIVE": 0.020,
    "TJ_POSITIVE + BRC_NEUTRAL": 0.005,
    "TJ_NEUTRAL + BRC_POSITIVE": 0.005,
    "TJ_POSITIVE + BRC_NEGATIVE": -0.005,
    "TJ_NEGATIVE + BRC_POSITIVE": -0.010,
    "TJ_NEGATIVE + BRC_NEUTRAL": -0.010,
    "TJ_NEUTRAL + BRC_NEGATIVE": -0.010,
    "TJ_NEGATIVE + BRC_NEGATIVE": -0.020,
}

def norm(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper()

def clean_track(x):
    s = norm(x)
    s = re.sub(r"[^A-Z0-9]+", " ", s).strip()
    return s

def horse_key(x):
    return re.sub(r"[^A-Z0-9]+", "", norm(x))

def first_existing(df, cols):
    for c in cols:
        if c in df.columns:
            return c
    return None

def num(s):
    return pd.to_numeric(s, errors="coerce")

def distance_bucket(x):
    d = pd.to_numeric(x, errors="coerce")
    if pd.isna(d):
        return "UNKNOWN"
    d = float(d)
    if d < 1000:
        return "<1000"
    if d < 1200:
        return "1000-1199"
    if d < 1400:
        return "1200-1399"
    if d < 1600:
        return "1400-1599"
    if d < 1800:
        return "1600-1799"
    if d < 2000:
        return "1800-1999"
    return "2000+"

def barrier_bucket(x):
    b = pd.to_numeric(x, errors="coerce")
    if pd.isna(b):
        return "UNKNOWN"
    b = int(float(b))
    if b <= 2:
        return "1_2"
    if b <= 4:
        return "3_4"
    if b <= 6:
        return "5_6"
    if b <= 8:
        return "7_8"
    if b <= 10:
        return "9_10"
    if b <= 12:
        return "11_12"
    return "13_PLUS"

def wide_bucket(x):
    s = norm(x)
    if s in ["11_12", "13_PLUS"]:
        return "WIDE"
    return s

def condition_group(x):
    s = norm(x)
    if "GOOD" in s:
        return "GOOD"
    if "SOFT" in s:
        return "SOFT"
    if "HEAVY" in s:
        return "HEAVY"
    return "UNKNOWN"

def rail_bucket_from_text(x):
    s = norm(x)
    if not s:
        return "UNKNOWN"
    if "TRUE" in s:
        return "TRUE"
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*M", s)
    if not m:
        return "UNKNOWN"
    v = float(m.group(1))
    if v <= 3:
        return "0_3M"
    if v <= 6:
        return "3_6M"
    if v <= 9:
        return "6_9M"
    if v <= 12:
        return "9_12M"
    return "12M_PLUS"

def tj_bucket(x):
    s = norm(x)
    if s in ["ELITE", "POSITIVE", "STRONG_POSITIVE"]:
        return "TJ_POSITIVE"
    if s in ["POOR", "NEGATIVE", "STRONG_NEGATIVE"]:
        return "TJ_NEGATIVE"
    return "TJ_NEUTRAL"

def brc_bucket(x):
    s = norm(x)
    if s in ["STRONG_POSITIVE", "POSITIVE"]:
        return "BRC_POSITIVE"
    if s in ["STRONG_NEGATIVE", "NEGATIVE"]:
        return "BRC_NEGATIVE"
    return "BRC_NEUTRAL"

def make_join_key(df):
    track_col = first_existing(df, ["track", "track_x", "track_y"])
    race_col = first_existing(df, ["race_no", "race_number", "race_key"])
    horse_col = first_existing(df, ["horse", "horseName", "horse_name"])

    if not track_col or not race_col or not horse_col:
        raise ValueError(f"Cannot build join key. Columns available: {list(df.columns)}")

    return (
        df[track_col].astype(str).map(clean_track)
        + "|R"
        + df[race_col].astype(str).str.extract(r"(\d+)")[0].fillna("")
        + "|"
        + df[horse_col].astype(str).map(horse_key)
    )

def lookup_key(parts):
    return "|".join([str(x) for x in parts])

def mode_or_first(series):
    vals = series.dropna().astype(str)
    if vals.empty:
        return np.nan
    m = vals.mode()
    return m.iloc[0] if not m.empty else vals.iloc[0]

def build_lookup(df, keys, band_col, score_col=None):
    agg = {band_col: mode_or_first}
    if score_col:
        agg[score_col] = "mean"
    return df.groupby(keys, dropna=False).agg(agg).reset_index()

def main():
    required = [LIVE_BOARD, TJ_V3, BRC_REPLAY]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required input files: {missing}")

    live = pd.read_csv(LIVE_BOARD, low_memory=False)
    tj = pd.read_csv(TJ_V3, low_memory=False)
    brc = pd.read_csv(BRC_REPLAY, low_memory=False)

    live["join_key_v8"] = make_join_key(live)
    tj["join_key_v8"] = make_join_key(tj)

    live_track_col = first_existing(live, ["track"])
    live_race_col = first_existing(live, ["race_no", "race_number"])
    live_horse_col = first_existing(live, ["horse"])
    live_distance_col = first_existing(live, ["distance", "distance_rated"])
    live_barrier_col = first_existing(live, ["barrier", "barrier_rated"])
    live_condition_col = first_existing(live, ["track_condition", "trackCondition", "track_condition_rated"])
    live_rail_col = first_existing(live, ["rail_position", "railPosition", "rail_position_rated"])
    fair_col = first_existing(live, ["fair_price", "current_fair_price", "official_fair_price", "edgeiq_fair_price", "fair_price_v6"])

    if not fair_col:
        raise ValueError(f"Could not find fair price column. Available: {list(live.columns)}")

    tj_band_col = first_existing(tj, [
        "tj_blend_band_v3",
        "trainer_jockey_blend_band_v3",
        "tj_band_v3",
        "tj_band",
        "blend_band_v3",
    ])
    tj_score_col = first_existing(tj, [
        "tj_blend_score_v3",
        "trainer_jockey_blend_score_v3",
        "tj_score_v3",
        "tj_score",
    ])
    tj_verdict_col = first_existing(tj, ["tj_verdict_v3", "verdict_v3", "tj_verdict"])
    tj_label_col = first_existing(tj, ["tj_label_v3", "label_v3", "tj_label"])

    if not tj_band_col:
        raise ValueError("Could not find TJ blend band column in TJ V3 feed.")

    tj_keep_cols = ["join_key_v8", tj_band_col]
    for c in [tj_score_col, tj_verdict_col, tj_label_col]:
        if c and c not in tj_keep_cols:
            tj_keep_cols.append(c)

    rename = {tj_band_col: "tj_band_live_v8"}
    if tj_score_col:
        rename[tj_score_col] = "tj_score_live_v8"
    if tj_verdict_col:
        rename[tj_verdict_col] = "tj_verdict_live_v8"
    if tj_label_col:
        rename[tj_label_col] = "tj_label_live_v8"

    tj_keep = tj[tj_keep_cols].drop_duplicates("join_key_v8").rename(columns=rename)
    out = live.merge(tj_keep, on="join_key_v8", how="left", validate="many_to_one")

    # HARD FIX: if live already contains an empty/stale tj_band_live_v8 column,
    # pandas suffixes the real merged TJ band as tj_band_live_v8_y.
    # Promote the populated merged column back to tj_band_live_v8.
    if "tj_band_live_v8_y" in out.columns:
        out["tj_band_live_v8"] = out["tj_band_live_v8_y"]
    elif "tj_band_live_v8_x" in out.columns:
        out["tj_band_live_v8"] = out["tj_band_live_v8_x"]

    if "tj_score_live_v8_y" in out.columns:
        out["tj_score_live_v8"] = out["tj_score_live_v8_y"]
    elif "tj_score_live_v8_x" in out.columns:
        out["tj_score_live_v8"] = out["tj_score_live_v8_x"]

    out["current_fair_price"] = num(out[fair_col])
    out["current_probability"] = np.where(out["current_fair_price"] > 0, 1.0 / out["current_fair_price"], np.nan)

    out["track_norm_v8"] = out[live_track_col].map(clean_track)
    out["distance_bucket_v8"] = out[live_distance_col].map(distance_bucket) if live_distance_col else "UNKNOWN"
    out["barrier_bucket_v8"] = out[live_barrier_col].map(barrier_bucket) if live_barrier_col else "UNKNOWN"
    out["wide_barrier_bucket_v8"] = out["barrier_bucket_v8"].map(wide_bucket)
    out["condition_group_v8"] = out[live_condition_col].map(condition_group) if live_condition_col else "UNKNOWN"
    out["rail_bucket_v8"] = out[live_rail_col].map(rail_bucket_from_text) if live_rail_col else "UNKNOWN"

    brc_track_col = first_existing(brc, ["track_norm", "normalized_track", "track"])
    brc_distance_col = first_existing(brc, ["distance_bucket", "distance_bucket_v1"])
    brc_rail_col = first_existing(brc, ["rail_bucket", "rail_bucket_v1"])
    brc_condition_col = first_existing(brc, ["condition_group", "condition_group_v1"])
    brc_barrier_col = first_existing(brc, ["barrier_bucket", "barrier_bucket_v1"])
    brc_band_col = first_existing(brc, [
        "barrier_rail_condition_band_v1",
        "barrier_rail_condition_bias_band_v1",
        "brc_band_v1",
    ])
    brc_score_col = first_existing(brc, [
        "barrier_rail_condition_score_v1",
        "barrier_rail_condition_bias_score_v1",
        "brc_score_v1",
    ])

    required_brc_cols = [brc_track_col, brc_distance_col, brc_rail_col, brc_condition_col, brc_barrier_col, brc_band_col]
    if any(c is None for c in required_brc_cols):
        raise ValueError(f"BRC replay missing expected lookup columns. Available: {list(brc.columns)}")

    brc_lookup = brc.copy()
    brc_lookup["track_norm_v8"] = brc_lookup[brc_track_col].map(clean_track)
    brc_lookup["distance_bucket_v8"] = brc_lookup[brc_distance_col].astype(str).str.strip()
    brc_lookup["rail_bucket_v8"] = brc_lookup[brc_rail_col].astype(str).str.strip()
    brc_lookup["condition_group_v8"] = brc_lookup[brc_condition_col].astype(str).str.strip()
    brc_lookup["barrier_bucket_v8"] = brc_lookup[brc_barrier_col].astype(str).str.strip()
    brc_lookup["wide_barrier_bucket_v8"] = brc_lookup["barrier_bucket_v8"].map(wide_bucket)

    base_cols = [
        "track_norm_v8",
        "distance_bucket_v8",
        "rail_bucket_v8",
        "condition_group_v8",
        "barrier_bucket_v8",
        "wide_barrier_bucket_v8",
        brc_band_col,
    ]
    if brc_score_col:
        base_cols.append(brc_score_col)

    brc_lookup = brc_lookup[base_cols].copy()

    exact = build_lookup(
        brc_lookup,
        ["track_norm_v8", "distance_bucket_v8", "rail_bucket_v8", "condition_group_v8", "barrier_bucket_v8"],
        brc_band_col,
        brc_score_col,
    )
    wide = build_lookup(
        brc_lookup[brc_lookup["wide_barrier_bucket_v8"].eq("WIDE")],
        ["track_norm_v8", "distance_bucket_v8", "rail_bucket_v8", "condition_group_v8", "wide_barrier_bucket_v8"],
        brc_band_col,
        brc_score_col,
    )
    track_dist_rail_cond = build_lookup(
        brc_lookup,
        ["track_norm_v8", "distance_bucket_v8", "rail_bucket_v8", "condition_group_v8"],
        brc_band_col,
        brc_score_col,
    )
    track_rail_cond_barrier = build_lookup(
        brc_lookup,
        ["track_norm_v8", "rail_bucket_v8", "condition_group_v8", "barrier_bucket_v8"],
        brc_band_col,
        brc_score_col,
    )
    state_dist_rail_cond_barrier = build_lookup(
        brc_lookup,
        ["distance_bucket_v8", "rail_bucket_v8", "condition_group_v8", "barrier_bucket_v8"],
        brc_band_col,
        brc_score_col,
    )
    state_dist_rail_cond = build_lookup(
        brc_lookup,
        ["distance_bucket_v8", "rail_bucket_v8", "condition_group_v8"],
        brc_band_col,
        brc_score_col,
    )

    def dict_from(df, keys):
        d = {}
        for _, r in df.iterrows():
            k = lookup_key([r[c] for c in keys])
            d[k] = (
                r[brc_band_col],
                float(r[brc_score_col]) if brc_score_col and pd.notna(r[brc_score_col]) else np.nan,
            )
        return d

    exact_d = dict_from(exact, ["track_norm_v8", "distance_bucket_v8", "rail_bucket_v8", "condition_group_v8", "barrier_bucket_v8"])
    wide_d = dict_from(wide, ["track_norm_v8", "distance_bucket_v8", "rail_bucket_v8", "condition_group_v8", "wide_barrier_bucket_v8"])
    tdrc_d = dict_from(track_dist_rail_cond, ["track_norm_v8", "distance_bucket_v8", "rail_bucket_v8", "condition_group_v8"])
    trcb_d = dict_from(track_rail_cond_barrier, ["track_norm_v8", "rail_bucket_v8", "condition_group_v8", "barrier_bucket_v8"])
    sdrb_d = dict_from(state_dist_rail_cond_barrier, ["distance_bucket_v8", "rail_bucket_v8", "condition_group_v8", "barrier_bucket_v8"])
    sdrc_d = dict_from(state_dist_rail_cond, ["distance_bucket_v8", "rail_bucket_v8", "condition_group_v8"])

    bands = []
    scores = []
    levels = []

    for _, r in out.iterrows():
        candidates = [
            (
                "EXACT",
                exact_d,
                [r["track_norm_v8"], r["distance_bucket_v8"], r["rail_bucket_v8"], r["condition_group_v8"], r["barrier_bucket_v8"]],
            ),
            (
                "TRACK_DISTANCE_RAIL_CONDITION_WIDE",
                wide_d,
                [r["track_norm_v8"], r["distance_bucket_v8"], r["rail_bucket_v8"], r["condition_group_v8"], r["wide_barrier_bucket_v8"]],
            ),
            (
                "TRACK_DISTANCE_RAIL_CONDITION",
                tdrc_d,
                [r["track_norm_v8"], r["distance_bucket_v8"], r["rail_bucket_v8"], r["condition_group_v8"]],
            ),
            (
                "TRACK_RAIL_CONDITION_BARRIER",
                trcb_d,
                [r["track_norm_v8"], r["rail_bucket_v8"], r["condition_group_v8"], r["barrier_bucket_v8"]],
            ),
            (
                "STATE_DISTANCE_RAIL_CONDITION_BARRIER",
                sdrb_d,
                [r["distance_bucket_v8"], r["rail_bucket_v8"], r["condition_group_v8"], r["barrier_bucket_v8"]],
            ),
            (
                "STATE_DISTANCE_RAIL_CONDITION",
                sdrc_d,
                [r["distance_bucket_v8"], r["rail_bucket_v8"], r["condition_group_v8"]],
            ),
        ]

        found = False
        for level, dct, parts in candidates:
            if "UNKNOWN" in [str(x) for x in parts]:
                continue
            k = lookup_key(parts)
            if k in dct:
                b, s = dct[k]
                bands.append(b)
                scores.append(s)
                levels.append(level)
                found = True
                break

        if not found:
            bands.append(np.nan)
            scores.append(np.nan)
            levels.append("NO_MATCH")

    out["brc_band_live_v8"] = bands
    out["brc_score_live_v8"] = scores
    out["brc_match_level_v8"] = levels

    out["tj_bucket_v8"] = out["tj_band_live_v8"].map(tj_bucket)
    out["brc_bucket_v8"] = out["brc_band_live_v8"].map(brc_bucket)
    out["interaction_bucket_v8"] = out["tj_bucket_v8"] + " + " + out["brc_bucket_v8"]

    out["v8_interaction_adjustment_pct"] = out["interaction_bucket_v8"].map(RULES).fillna(0.0)
    out["v8_rule_used"] = RULE_SET

    out["v8_adjusted_probability_raw"] = out["current_probability"] * (1.0 + out["v8_interaction_adjustment_pct"])

    race_group_cols = [live_track_col, live_race_col]
    prob_sum = out.groupby(race_group_cols)["v8_adjusted_probability_raw"].transform("sum")
    baseline_prob_sum = out.groupby(race_group_cols)["current_probability"].transform("sum")

    out["v8_adjusted_probability"] = np.where(
        (prob_sum > 0) & baseline_prob_sum.notna(),
        out["v8_adjusted_probability_raw"] / prob_sum * baseline_prob_sum,
        out["current_probability"],
    )

    out["v8_interaction_candidate_price"] = np.where(
        out["v8_adjusted_probability"] > 0,
        1.0 / out["v8_adjusted_probability"],
        np.nan,
    )

    out["v8_interaction_candidate_price"] = out["v8_interaction_candidate_price"].round(4)
    out["v8_interaction_price_delta"] = (out["v8_interaction_candidate_price"] - out["current_fair_price"]).round(4)
    out["v8_interaction_abs_price_delta"] = out["v8_interaction_price_delta"].abs().round(4)

    out["v8_candidate_note"] = (
        "RULE_SET_C_FILTER_HEAVY | "
        + out["interaction_bucket_v8"].fillna("UNKNOWN")
        + " | brc_match="
        + out["brc_match_level_v8"].fillna("UNKNOWN")
        + " | adj="
        + (out["v8_interaction_adjustment_pct"] * 100).round(2).astype(str)
        + "%"
    )

    out["v8_candidate_status"] = np.select(
        [
            out["current_fair_price"].isna(),
            out["brc_band_live_v8"].isna(),
            out["tj_band_live_v8"].isna(),
        ],
        [
            "NO_CURRENT_FAIR_PRICE",
            "NO_BRC_MATCH",
            "NO_TJ_MATCH",
        ],
        default="COMPLETE",
    )

    export_cols = []
    for c in [
        live_track_col,
        live_race_col,
        live_horse_col,
        live_distance_col,
        live_barrier_col,
        live_condition_col,
        live_rail_col,
        "current_fair_price",
        "current_probability",
        "track_norm_v8",
        "distance_bucket_v8",
        "condition_group_v8",
        "rail_bucket_v8",
        "barrier_bucket_v8",
        "wide_barrier_bucket_v8",
        "v8_interaction_candidate_price",
        "v8_interaction_adjustment_pct",
        "tj_band_live_v8",
        "brc_band_live_v8",
        "brc_score_live_v8",
        "brc_match_level_v8",
        "tj_bucket_v8",
        "brc_bucket_v8",
        "interaction_bucket_v8",
        "v8_rule_used",
        "v8_candidate_status",
        "v8_candidate_note",
        "v8_interaction_price_delta",
        "v8_interaction_abs_price_delta",
    ]:
        if c and c in out.columns and c not in export_cols:
            export_cols.append(c)

    out[export_cols].to_csv(OUT, index=False)

    unmatched = out[out["v8_candidate_status"] != "COMPLETE"].copy()
    unmatched[export_cols].to_csv(OUT_UNMATCHED, index=False)

    live_rows = len(out)
    complete_rows = int((out["v8_candidate_status"] == "COMPLETE").sum())
    active_rows = int((out["v8_interaction_adjustment_pct"] != 0).sum())
    price_rows = int(out["v8_interaction_candidate_price"].notna().sum())
    brc_rows = int(out["brc_band_live_v8"].notna().sum())
    tj_rows = int(out["tj_band_live_v8"].notna().sum())

    match_level_counts = (
        out.groupby("brc_match_level_v8", dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(["rows", "brc_match_level_v8"], ascending=[False, True])
    )

    summary_rows = [
        ["status", "COMPLETE"],
        ["live_rows", live_rows],
        ["tj_matched_rows", tj_rows],
        ["brc_matched_rows", brc_rows],
        ["complete_rows", complete_rows],
        ["active_v8_rows", active_rows],
        ["candidate_price_rows", price_rows],
        ["mean_abs_price_delta", round(float(out["v8_interaction_abs_price_delta"].dropna().mean()), 4) if price_rows else ""],
        ["max_abs_price_delta", round(float(out["v8_interaction_abs_price_delta"].dropna().max()), 4) if price_rows else ""],
        ["rule_set_used", RULE_SET],
        ["official_fair_price_replaced", "NO"],
        ["edge_execution_staking_changed", "NO"],
    ]

    for _, r in match_level_counts.iterrows():
        summary_rows.append([f"brc_match_level_{r['brc_match_level_v8']}", int(r["rows"])])

    pd.DataFrame(summary_rows, columns=["metric", "value"]).to_csv(OUT_SUMMARY, index=False)

    payload = {
        "status": "COMPLETE",
        "live_rows": int(live_rows),
        "tj_matched_rows": int(tj_rows),
        "brc_matched_rows": int(brc_rows),
        "complete_rows": int(complete_rows),
        "active_v8_rows": int(active_rows),
        "candidate_price_rows": int(price_rows),
        "mean_abs_price_delta": round(float(out["v8_interaction_abs_price_delta"].dropna().mean()), 4) if price_rows else None,
        "max_abs_price_delta": round(float(out["v8_interaction_abs_price_delta"].dropna().max()), 4) if price_rows else None,
        "rule_set_used": RULE_SET,
        "official_fair_price_replaced": False,
        "edge_execution_staking_changed": False,
        "brc_match_levels": {
            str(r["brc_match_level_v8"]): int(r["rows"])
            for _, r in match_level_counts.iterrows()
        },
        "outputs": {
            "candidate_feed": str(OUT),
            "summary": str(OUT_SUMMARY),
            "unmatched": str(OUT_UNMATCHED),
        },
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("[LIVE_FAIR_PRICE_V8_INTERACTION_CANDIDATE_FEED] COMPLETE")
    print(f"live_rows={live_rows}")
    print(f"tj_matched_rows={tj_rows}")
    print(f"brc_matched_rows={brc_rows}")
    print(f"complete_rows={complete_rows}")
    print(f"active_v8_rows={active_rows}")
    print(f"candidate_price_rows={price_rows}")
    print(f"official_fair_price_replaced=NO")
    print(f"edge_execution_staking_changed=NO")
    print("brc_match_levels=" + json.dumps(payload["brc_match_levels"], sort_keys=True))

if __name__ == "__main__":
    main()

