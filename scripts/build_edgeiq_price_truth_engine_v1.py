from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_live_runner_board_v1.csv"
V8 = DATA / "edgeiq_live_v8_candidate_display_feed_v1.csv"

OUT = DATA / "edgeiq_price_truth_v1.csv"
SUMMARY = DATA / "edgeiq_price_truth_v1_summary.csv"

OFFICIAL_PRICE_MODE = "BASE"

def safe(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def num(x):
    return pd.to_numeric(x, errors="coerce")

def canon_track(x):
    return re.sub(r"[^A-Z0-9]", "", safe(x).upper())

def canon_horse(x):
    s = safe(x).upper()
    s = re.sub(r"\([^)]*\)", "", s)
    return re.sub(r"[^A-Z0-9]", "", s)

def race_no(x):
    try:
        return str(int(float(re.sub(r"[^0-9.]", "", safe(x)))))
    except Exception:
        return safe(x)

def key_cols(df):
    df["join_track"] = df["track"].map(canon_track) if "track" in df.columns else ""
    df["join_race_no"] = df["race_no"].map(race_no) if "race_no" in df.columns else ""

    if "horse_canon" in df.columns:
        df["join_horse"] = df["horse_canon"].map(canon_horse)
    elif "horse_key" in df.columns:
        df["join_horse"] = df["horse_key"].map(canon_horse)
    elif "horse" in df.columns:
        df["join_horse"] = df["horse"].map(canon_horse)
    else:
        df["join_horse"] = ""

    return df

def overlay_pct(market, fair):
    if pd.isna(market) or pd.isna(fair) or fair <= 0:
        return np.nan
    return ((market / fair) - 1.0) * 100.0

def price_bucket(p):
    if pd.isna(p): return "MISSING"
    if p <= 2: return "001_2"
    if p <= 5: return "002_5"
    if p <= 10: return "005_10"
    if p <= 20: return "010_20"
    if p <= 50: return "020_50"
    if p <= 100: return "050_100"
    if p < 400: return "100_399"
    if round(float(p), 4) == 400.0: return "400_CAP"
    return "400_PLUS"

def official_price(row):
    base = row.get("base_fair_price")
    v8 = row.get("v8_candidate_price")

    if OFFICIAL_PRICE_MODE == "V8" and pd.notna(v8) and v8 > 0:
        return v8, "V8_CANDIDATE_PRICE"

    return base, "BASE_V3_PROBABILITY_PRICE"

def main():
    if not LIVE.exists():
        raise FileNotFoundError(f"Missing required input: {LIVE}")

    live = pd.read_csv(LIVE, dtype=str, low_memory=False)
    live.columns = [c.strip() for c in live.columns]
    live = key_cols(live)

    out = pd.DataFrame()

    out["race_date"] = live.get("race_date", "")
    out["track"] = live.get("track", "")
    out["race_no"] = live.get("race_no", "")
    out["horse_no"] = live.get("horse_no", "")
    out["horse"] = live.get("horse", "")
    out["horse_canon"] = live.get("horse_canon", "")
    out["barrier"] = live.get("barrier", "")
    out["jockey"] = live.get("jockey", "")
    out["trainer"] = live.get("trainer", "")
    out["distance"] = live.get("distance", "")
    out["track_condition"] = live.get("track_condition", "")

    out["join_track"] = live["join_track"]
    out["join_race_no"] = live["join_race_no"]
    out["join_horse"] = live["join_horse"]

    out["base_probability"] = num(live.get("v3_probability", np.nan))
    out["base_fair_price"] = num(live.get("fair_price", np.nan))
    out["base_edge_pct_existing"] = num(live.get("edge_pct", np.nan))
    out["market_price"] = num(live.get("live_price", np.nan))
    out["market_state"] = live.get("market_state", "")
    out["base_execution_action"] = live.get("execution_action", "")
    out["base_pricing_action"] = live.get("v3_pricing_action", "")
    out["base_realism_grade"] = live.get("v3_realism_grade", "")

    out["base_raw_fair_price_from_probability"] = np.where(
        out["base_probability"] > 0,
        1.0 / out["base_probability"],
        np.nan
    )

    out["base_price_matches_probability"] = (
        (out["base_fair_price"] - np.minimum(400.0, np.maximum(1.01, out["base_raw_fair_price_from_probability"]))).abs() <= 0.02
    )

    out["base_price_capped_400"] = out["base_fair_price"].round(4).eq(400.0)
    out["base_price_bucket"] = out["base_fair_price"].map(price_bucket)

    if V8.exists():
        v8 = pd.read_csv(V8, dtype=str, low_memory=False)
        v8.columns = [c.strip() for c in v8.columns]
        v8 = key_cols(v8)

        v8_keep = [
            "join_track",
            "join_race_no",
            "join_horse",
            "fair_price",
            "v8_interaction_candidate_price",
            "v8_candidate_price_display",
            "v8_interaction_adjustment_pct",
            "v8_candidate_display_status",
            "v8_candidate_badge",
            "brc_match_level_v8",
            "tj_band_live_v8",
            "brc_band_live_v8",
        ]
        v8_keep = [c for c in v8_keep if c in v8.columns]
        v8 = v8[v8_keep].drop_duplicates(["join_track", "join_race_no", "join_horse"])
        v8 = v8.rename(columns={
            "fair_price": "v8_fair_price",
            "v8_interaction_candidate_price": "v8_interaction_candidate_price_raw",
            "v8_candidate_price_display": "v8_candidate_price_display_raw",
        })

        out = out.merge(v8, on=["join_track", "join_race_no", "join_horse"], how="left")
    else:
        out["v8_fair_price"] = np.nan

    out["v8_fair_price"] = num(out.get("v8_fair_price", np.nan))
    out["v8_interaction_candidate_price_raw"] = num(out.get("v8_interaction_candidate_price_raw", np.nan))
    out["v8_candidate_price_display_raw"] = num(out.get("v8_candidate_price_display_raw", np.nan))

    out["v8_candidate_price"] = out["v8_fair_price"]
    out["v8_price_available"] = out["v8_candidate_price"].notna()
    out["v8_vs_base_delta"] = out["v8_candidate_price"] - out["base_fair_price"]
    out["v8_vs_base_delta_pct"] = np.where(
        out["base_fair_price"] > 0,
        ((out["v8_candidate_price"] / out["base_fair_price"]) - 1.0) * 100.0,
        np.nan
    )
    out["v8_major_shift_flag"] = out["v8_vs_base_delta_pct"].abs().ge(50)
    out["v8_moderate_shift_flag"] = out["v8_vs_base_delta_pct"].abs().ge(20)

    official_values = out.apply(official_price, axis=1)
    out["official_fair_price"] = [x[0] for x in official_values]
    out["official_price_source"] = [x[1] for x in official_values]
    out["official_price_mode"] = OFFICIAL_PRICE_MODE

    out["official_overlay_pct"] = [
        overlay_pct(m, f) for m, f in zip(out["market_price"], out["official_fair_price"])
    ]

    out["base_overlay_pct_recomputed"] = [
        overlay_pct(m, f) for m, f in zip(out["market_price"], out["base_fair_price"])
    ]

    out["v8_overlay_pct_recomputed"] = [
        overlay_pct(m, f) for m, f in zip(out["market_price"], out["v8_candidate_price"])
    ]

    out["official_price_bucket"] = out["official_fair_price"].map(price_bucket)

    out["price_governance_status"] = np.select(
        [
            out["base_fair_price"].isna(),
            out["base_price_capped_400"],
            out["v8_major_shift_flag"].fillna(False),
            out["v8_moderate_shift_flag"].fillna(False),
        ],
        [
            "MISSING_BASE_PRICE",
            "BASE_PRICE_CAPPED_400",
            "V8_MAJOR_SHIFT_OBSERVATION",
            "V8_MODERATE_SHIFT_OBSERVATION",
        ],
        default="PRICE_GOVERNED_OK"
    )

    preferred = [
        "race_date","track","race_no","horse_no","horse","horse_canon","barrier","jockey","trainer",
        "distance","track_condition",
        "base_probability","base_raw_fair_price_from_probability","base_fair_price",
        "base_price_matches_probability","base_price_capped_400","base_price_bucket",
        "v8_candidate_price","v8_price_available","v8_vs_base_delta","v8_vs_base_delta_pct",
        "v8_major_shift_flag","v8_moderate_shift_flag",
        "v8_candidate_display_status","v8_candidate_badge","brc_match_level_v8","tj_band_live_v8","brc_band_live_v8",
        "official_fair_price","official_price_source","official_price_mode","official_price_bucket",
        "market_price","market_state","official_overlay_pct","base_overlay_pct_recomputed","v8_overlay_pct_recomputed",
        "base_edge_pct_existing","base_execution_action","base_pricing_action","base_realism_grade",
        "price_governance_status",
    ]
    preferred = [c for c in preferred if c in out.columns]
    final = out[preferred].copy()

    for c in [
        "base_probability",
        "base_raw_fair_price_from_probability",
        "base_fair_price",
        "v8_candidate_price",
        "v8_vs_base_delta",
        "v8_vs_base_delta_pct",
        "official_fair_price",
        "market_price",
        "official_overlay_pct",
        "base_overlay_pct_recomputed",
        "v8_overlay_pct_recomputed",
        "base_edge_pct_existing",
    ]:
        if c in final.columns:
            final[c] = pd.to_numeric(final[c], errors="coerce").round(4)

    final.to_csv(OUT, index=False)

    summary = [
        ("status", "COMPLETE"),
        ("official_price_mode", OFFICIAL_PRICE_MODE),
        ("rows", len(final)),
        ("base_price_matches_probability", int(final["base_price_matches_probability"].eq(True).sum())),
        ("base_price_capped_400", int(final["base_price_capped_400"].eq(True).sum())),
        ("v8_price_available", int(final["v8_price_available"].eq(True).sum())),
        ("v8_major_shift_flag", int(final["v8_major_shift_flag"].eq(True).sum())),
        ("v8_moderate_shift_flag", int(final["v8_moderate_shift_flag"].eq(True).sum())),
        ("official_price_rows", int(pd.to_numeric(final["official_fair_price"], errors="coerce").notna().sum())),
        ("official_overlay_rows", int(pd.to_numeric(final["official_overlay_pct"], errors="coerce").notna().sum())),
    ]

    for k, v in final["official_price_source"].value_counts(dropna=False).to_dict().items():
        summary.append((f"official_price_source_{k}", v))

    for k, v in final["official_price_bucket"].value_counts(dropna=False).to_dict().items():
        summary.append((f"official_price_bucket_{k}", v))

    for k, v in final["price_governance_status"].value_counts(dropna=False).to_dict().items():
        summary.append((f"price_governance_status_{k}", v))

    pd.DataFrame(summary, columns=["metric","value"]).to_csv(SUMMARY, index=False)

    print("[PRICE_TRUTH_ENGINE_V1] COMPLETE")
    print(f"official_price_mode={OFFICIAL_PRICE_MODE}")
    print(f"rows={len(final)}")
    print(f"wrote={OUT}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
