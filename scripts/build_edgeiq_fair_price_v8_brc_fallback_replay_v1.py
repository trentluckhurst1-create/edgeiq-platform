from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INFILE = DATA / "edgeiq_fair_price_v8_interaction_filter_replay_v1.csv"

OUT = DATA / "edgeiq_fair_price_v8_brc_fallback_replay_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_fair_price_v8_brc_fallback_replay_v1_summary.csv"
OUT_BY_LEVEL = DATA / "edgeiq_fair_price_v8_brc_fallback_replay_by_match_level.csv"
OUT_ADDED = DATA / "edgeiq_fair_price_v8_brc_fallback_replay_added_rows.csv"
OUT_JSON = DATA / "edgeiq_fair_price_v8_brc_fallback_replay_v1.json"

def num(x):
    return pd.to_numeric(x, errors="coerce")

def norm(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper()

def wide_bucket(x):
    s = norm(x)
    if s in ["11_12", "13_PLUS"]:
        return "WIDE"
    return s

def profit(odds, won):
    o = pd.to_numeric(odds, errors="coerce")
    w = pd.to_numeric(won, errors="coerce")
    if pd.isna(o) or o <= 1 or pd.isna(w):
        return np.nan
    return float(o - 1) if int(w) == 1 else -1.0

def boolish(x):
    return str(x).strip().upper() in ["TRUE", "1", "YES", "Y"]

def summarize(df, label):
    rows = len(df)
    bets_df = df[df["replay_is_bet_v1"] == True].copy()
    bets = len(bets_df)
    wins = int(num(bets_df["won"]).fillna(0).sum()) if bets else 0
    prof = float(num(bets_df["replay_profit_v1"]).dropna().sum()) if bets else 0.0
    roi = prof / bets if bets else 0.0
    avg_overlay = float(num(bets_df["v8_adjusted_overlay_pct_v1"]).dropna().mean()) if bets and "v8_adjusted_overlay_pct_v1" in bets_df.columns else 0.0

    return {
        "label": label,
        "rows": int(rows),
        "bets": int(bets),
        "wins": int(wins),
        "win_rate": round(wins / bets, 6) if bets else "",
        "profit": round(prof, 6) if bets else "",
        "roi": round(roi, 6) if bets else "",
        "pot": round(roi, 6) if bets else "",
        "avg_v8_overlay_pct": round(avg_overlay, 6) if bets else "",
    }

def main():
    if not INFILE.exists():
        raise FileNotFoundError(f"Missing input: {INFILE}")

    df = pd.read_csv(INFILE, low_memory=False)

    required = [
        "track",
        "barrier_bucket",
        "rail_bucket",
        "condition_group",
        "barrier_rail_condition_band_v1",
        "barrier_rail_condition_score_v1",
        "brc_state_v1",
        "interaction_bucket_v1",
        "market_proxy_fair_odds_v1",
        "won",
        "v8_adjusted_positive_overlay_flag_v1",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}. Available: {list(df.columns)}")

    out = df.copy()

    out["wide_barrier_bucket_fb_v1"] = out["barrier_bucket"].map(wide_bucket)

    # Historical exact baseline: this replay file already contains exact BRC state.
    out["brc_exact_available_v1"] = out["barrier_rail_condition_band_v1"].notna()
    out["brc_band_exact_only_v1"] = out["barrier_rail_condition_band_v1"]
    out["brc_score_exact_only_v1"] = num(out["barrier_rail_condition_score_v1"])

    # Build local fallback maps from the replay itself.
    # This is deliberately conservative:
    # 1. exact if present
    # 2. track + rail + condition + WIDE
    # 3. track + rail + condition
    base = out[
        [
            "track",
            "rail_bucket",
            "condition_group",
            "barrier_bucket",
            "wide_barrier_bucket_fb_v1",
            "barrier_rail_condition_band_v1",
            "barrier_rail_condition_score_v1",
        ]
    ].dropna(subset=["barrier_rail_condition_band_v1"]).copy()

    def mode_or_first(s):
        vals = s.dropna().astype(str)
        if vals.empty:
            return np.nan
        m = vals.mode()
        return m.iloc[0] if not m.empty else vals.iloc[0]

    wide_map = (
        base[base["wide_barrier_bucket_fb_v1"].eq("WIDE")]
        .groupby(["track", "rail_bucket", "condition_group", "wide_barrier_bucket_fb_v1"], dropna=False)
        .agg(
            fb_band=("barrier_rail_condition_band_v1", mode_or_first),
            fb_score=("barrier_rail_condition_score_v1", "mean"),
            fb_samples=("barrier_rail_condition_band_v1", "size"),
        )
        .reset_index()
    )

    trc_map = (
        base
        .groupby(["track", "rail_bucket", "condition_group"], dropna=False)
        .agg(
            fb_band=("barrier_rail_condition_band_v1", mode_or_first),
            fb_score=("barrier_rail_condition_score_v1", "mean"),
            fb_samples=("barrier_rail_condition_band_v1", "size"),
        )
        .reset_index()
    )

    wide_dict = {
        "|".join(map(str, [r.track, r.rail_bucket, r.condition_group, r.wide_barrier_bucket_fb_v1])): (r.fb_band, r.fb_score, int(r.fb_samples))
        for r in wide_map.itertuples(index=False)
    }

    trc_dict = {
        "|".join(map(str, [r.track, r.rail_bucket, r.condition_group])): (r.fb_band, r.fb_score, int(r.fb_samples))
        for r in trc_map.itertuples(index=False)
    }

    fb_band = []
    fb_score = []
    fb_samples = []
    fb_level = []

    for r in out.itertuples(index=False):
        exact_band = getattr(r, "barrier_rail_condition_band_v1")
        exact_score = getattr(r, "barrier_rail_condition_score_v1")

        if pd.notna(exact_band):
            fb_band.append(exact_band)
            fb_score.append(pd.to_numeric(exact_score, errors="coerce"))
            fb_samples.append(1)
            fb_level.append("EXACT")
            continue

        wide_key = "|".join(map(str, [
            getattr(r, "track"),
            getattr(r, "rail_bucket"),
            getattr(r, "condition_group"),
            getattr(r, "wide_barrier_bucket_fb_v1"),
        ]))

        if wide_key in wide_dict:
            b, s, n = wide_dict[wide_key]
            fb_band.append(b)
            fb_score.append(s)
            fb_samples.append(n)
            fb_level.append("TRACK_RAIL_CONDITION_WIDE")
            continue

        trc_key = "|".join(map(str, [
            getattr(r, "track"),
            getattr(r, "rail_bucket"),
            getattr(r, "condition_group"),
        ]))

        if trc_key in trc_dict:
            b, s, n = trc_dict[trc_key]
            fb_band.append(b)
            fb_score.append(s)
            fb_samples.append(n)
            fb_level.append("TRACK_RAIL_CONDITION")
            continue

        fb_band.append(np.nan)
        fb_score.append(np.nan)
        fb_samples.append(0)
        fb_level.append("NO_MATCH")

    out["brc_band_with_fallback_v1"] = fb_band
    out["brc_score_with_fallback_v1"] = fb_score
    out["brc_fallback_sample_rows_v1"] = fb_samples
    out["brc_match_level_fallback_v1"] = fb_level

    out["fallback_available_v1"] = out["brc_band_with_fallback_v1"].notna()
    out["fallback_added_row_v1"] = (~out["brc_exact_available_v1"]) & out["fallback_available_v1"]

    out["replay_is_bet_v1"] = out["v8_adjusted_positive_overlay_flag_v1"].map(boolish)
    out["replay_profit_v1"] = out.apply(lambda r: profit(r["market_proxy_fair_odds_v1"], r["won"]), axis=1)

    exact_df = out[out["brc_exact_available_v1"] == True].copy()
    fallback_df = out[out["fallback_available_v1"] == True].copy()
    added_df = out[out["fallback_added_row_v1"] == True].copy()

    out.to_csv(OUT, index=False)
    added_df.to_csv(OUT_ADDED, index=False)

    summary = pd.DataFrame([
        summarize(exact_df, "EXACT_ONLY"),
        summarize(fallback_df, "WITH_FALLBACK"),
        summarize(added_df, "FALLBACK_ADDED_ROWS"),
    ])

    rows_exact = int(out["brc_exact_available_v1"].sum())
    rows_fb = int(out["fallback_available_v1"].sum())
    rows_added = int(out["fallback_added_row_v1"].sum())

    roi_exact = pd.to_numeric(summary.loc[summary["label"].eq("EXACT_ONLY"), "roi"], errors="coerce").iloc[0]
    roi_fb = pd.to_numeric(summary.loc[summary["label"].eq("WITH_FALLBACK"), "roi"], errors="coerce").iloc[0]

    if rows_added == 0:
        verdict = "V8_FALLBACK_REPLAY_NO_ADDED_ROWS"
    elif pd.isna(roi_exact) or pd.isna(roi_fb):
        verdict = "V8_FALLBACK_REPLAY_COVERAGE_ONLY_PASS"
    elif roi_fb >= roi_exact - 0.01:
        verdict = "V8_FALLBACK_REPLAY_PASS"
    else:
        verdict = "V8_FALLBACK_REPLAY_REVIEW"

    meta = pd.DataFrame([
        {"label": "rows_exact_only", "rows": rows_exact},
        {"label": "rows_with_fallback", "rows": rows_fb},
        {"label": "fallback_rows_added", "rows": rows_added},
        {"label": "verdict", "rows": verdict},
        {"label": "official_fair_price_replaced", "rows": "NO"},
        {"label": "edge_execution_staking_changed", "rows": "NO"},
    ])

    pd.concat([summary, meta], ignore_index=True).to_csv(OUT_SUMMARY, index=False)

    by_level = []
    for level, g in out[out["fallback_available_v1"] == True].groupby("brc_match_level_fallback_v1"):
        by_level.append(summarize(g, level))
    pd.DataFrame(by_level).sort_values("rows", ascending=False).to_csv(OUT_BY_LEVEL, index=False)

    payload = {
        "status": "COMPLETE",
        "verdict": verdict,
        "rows_exact_only": rows_exact,
        "rows_with_fallback": rows_fb,
        "fallback_rows_added": rows_added,
        "official_fair_price_replaced": False,
        "edge_execution_staking_changed": False,
        "outputs": {
            "replay": str(OUT),
            "summary": str(OUT_SUMMARY),
            "by_match_level": str(OUT_BY_LEVEL),
            "added_rows": str(OUT_ADDED),
        },
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("[V8_BRC_FALLBACK_REPLAY_V1] COMPLETE")
    print(f"rows_exact_only={rows_exact}")
    print(f"rows_with_fallback={rows_fb}")
    print(f"fallback_rows_added={rows_added}")
    print(f"verdict={verdict}")
    print("official_fair_price_replaced=NO")
    print("edge_execution_staking_changed=NO")
    print(f"wrote={OUT}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_BY_LEVEL}")
    print(f"wrote={OUT_ADDED}")
    print(f"wrote={OUT_JSON}")

if __name__ == "__main__":
    main()
