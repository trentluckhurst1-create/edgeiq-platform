from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_live_runner_board_v1.csv"
V8 = DATA / "edgeiq_live_v8_candidate_display_feed_v1.csv"
BET = DATA / "edgeiq_live_bet_quality_v1_1.csv"

OUT = DATA / "edgeiq_price_truth_audit_v1.csv"
SUMMARY = DATA / "edgeiq_price_truth_audit_v1_summary.csv"

def text(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def num(x):
    return pd.to_numeric(x, errors="coerce")

def key_cols(df):
    df["join_track"] = df["track"].astype(str).str.upper().str.replace(r"[^A-Z0-9]", "", regex=True)
    df["join_race_no"] = df["race_no"].astype(str).str.replace(r"[^0-9]", "", regex=True)
    if "horse_canon" in df.columns:
        df["join_horse"] = df["horse_canon"].astype(str).str.upper().str.replace(r"[^A-Z0-9]", "", regex=True)
    else:
        df["join_horse"] = df["horse"].astype(str).str.upper().str.replace(r"\([^)]*\)", "", regex=True).str.replace(r"[^A-Z0-9]", "", regex=True)
    return df

def band_price(p):
    if pd.isna(p): return "MISSING"
    if p <= 2: return "001_2"
    if p <= 5: return "002_5"
    if p <= 10: return "005_10"
    if p <= 20: return "010_20"
    if p <= 50: return "020_50"
    if p <= 100: return "050_100"
    if p < 400: return "100_399"
    if p == 400: return "400_CAP"
    return "400_PLUS"

def verdict(row):
    if row["was_capped_400"]:
        return "PRICE_CAPPED_400"
    if pd.notna(row["v8_fair_price"]) and pd.notna(row["base_fair_price"]):
        delta = abs(row["v8_vs_base_delta_pct"])
        if delta >= 50:
            return "V8_MAJOR_PRICE_SHIFT"
        if delta >= 20:
            return "V8_MODERATE_PRICE_SHIFT"
    return "PRICE_OK"

def main():
    if not LIVE.exists():
        raise FileNotFoundError(f"Missing {LIVE}")

    live = pd.read_csv(LIVE, dtype=str, low_memory=False)
    live.columns = [c.strip() for c in live.columns]
    live = key_cols(live)

    out = live.copy()

    out["v3_probability_num"] = num(out.get("v3_probability", np.nan))
    out["base_fair_price"] = num(out.get("fair_price", np.nan))
    out["market_price"] = num(out.get("live_price", np.nan))

    out["raw_fair_price_from_probability"] = np.where(
        out["v3_probability_num"] > 0,
        1.0 / out["v3_probability_num"],
        np.nan
    )

    out["price_cap_expected"] = np.minimum(
        400.0,
        np.maximum(1.01, out["raw_fair_price_from_probability"])
    )

    out["was_capped_400"] = (
        out["base_fair_price"].round(4).eq(400.0) |
        out["price_cap_expected"].round(4).eq(400.0)
    )

    out["base_price_matches_probability"] = (
        (out["base_fair_price"] - out["price_cap_expected"]).abs() <= 0.02
    )

    out["base_price_bucket"] = out["base_fair_price"].map(band_price)

    if V8.exists():
        v8 = pd.read_csv(V8, dtype=str, low_memory=False)
        v8.columns = [c.strip() for c in v8.columns]
        v8 = key_cols(v8)
        v8_keep = [
            "join_track","join_race_no","join_horse",
            "fair_price",
            "v8_interaction_candidate_price",
            "v8_interaction_adjustment_pct",
            "v8_candidate_price_display",
            "v8_candidate_display_status",
            "v8_candidate_badge",
            "brc_match_level_v8",
        ]
        v8_keep = [c for c in v8_keep if c in v8.columns]
        v8 = v8[v8_keep].drop_duplicates(["join_track","join_race_no","join_horse"])
        out = out.merge(v8, on=["join_track","join_race_no","join_horse"], how="left", suffixes=("", "_v8"))

    if "fair_price_v8" in out.columns:
        out["v8_fair_price"] = num(out["fair_price_v8"])
    else:
        out["v8_fair_price"] = np.nan

    out["v8_candidate_price_num"] = num(out.get("v8_interaction_candidate_price", np.nan))
    out["v8_display_price_num"] = num(out.get("v8_candidate_price_display", np.nan))

    out["v8_vs_base_delta"] = out["v8_fair_price"] - out["base_fair_price"]
    out["v8_vs_base_delta_pct"] = np.where(
        out["base_fair_price"] > 0,
        ((out["v8_fair_price"] / out["base_fair_price"]) - 1.0) * 100.0,
        np.nan
    )

    if BET.exists():
        bet = pd.read_csv(BET, dtype=str, low_memory=False)
        bet.columns = [c.strip() for c in bet.columns]
        bet = key_cols(bet)
        bet_keep = [
            "join_track","join_race_no","join_horse",
            "bet_quality_fair_price_used_v1_1",
            "bet_quality_live_price_used_v1_1",
            "bet_quality_overlay_pct_v1_1",
            "bet_quality_grade_v1_1",
            "official_fair_price_replaced",
        ]
        bet_keep = [c for c in bet_keep if c in bet.columns]
        bet = bet[bet_keep].drop_duplicates(["join_track","join_race_no","join_horse"])
        out = out.merge(bet, on=["join_track","join_race_no","join_horse"], how="left")

    out["bet_quality_fair_price_num"] = num(out.get("bet_quality_fair_price_used_v1_1", np.nan))
    out["bet_quality_uses_v8_price"] = (
        (out["bet_quality_fair_price_num"] - out["v8_fair_price"]).abs() <= 0.02
    )
    out["bet_quality_uses_base_price"] = (
        (out["bet_quality_fair_price_num"] - out["base_fair_price"]).abs() <= 0.02
    )

    out["price_truth_verdict"] = out.apply(verdict, axis=1)

    keep = [
        "race_date","track","race_no","horse_no","horse","barrier","jockey","trainer",
        "live_price","market_price",
        "v3_probability","v3_probability_num",
        "raw_fair_price_from_probability",
        "price_cap_expected",
        "fair_price","base_fair_price",
        "was_capped_400",
        "base_price_matches_probability",
        "base_price_bucket",
        "v8_fair_price",
        "v8_vs_base_delta",
        "v8_vs_base_delta_pct",
        "v8_interaction_candidate_price",
        "v8_interaction_adjustment_pct",
        "v8_candidate_price_display",
        "v8_candidate_display_status",
        "v8_candidate_badge",
        "brc_match_level_v8",
        "bet_quality_fair_price_used_v1_1",
        "bet_quality_fair_price_num",
        "bet_quality_uses_v8_price",
        "bet_quality_uses_base_price",
        "bet_quality_overlay_pct_v1_1",
        "bet_quality_grade_v1_1",
        "official_fair_price_replaced",
        "edge_pct",
        "execution_action",
        "v3_pricing_action",
        "v3_realism_grade",
        "price_truth_verdict",
    ]
    keep = [c for c in keep if c in out.columns]
    final = out[keep].copy()

    for c in [
        "raw_fair_price_from_probability",
        "price_cap_expected",
        "base_fair_price",
        "market_price",
        "v8_fair_price",
        "v8_vs_base_delta",
        "v8_vs_base_delta_pct",
        "bet_quality_fair_price_num",
    ]:
        if c in final.columns:
            final[c] = pd.to_numeric(final[c], errors="coerce").round(4)

    final.to_csv(OUT, index=False)

    summary = [
        ("status", "COMPLETE"),
        ("rows", len(final)),
        ("base_price_matches_probability", int(final["base_price_matches_probability"].eq(True).sum())),
        ("base_price_mismatch_probability", int(final["base_price_matches_probability"].eq(False).sum())),
        ("was_capped_400", int(final["was_capped_400"].eq(True).sum())),
        ("base_price_gt_100", int(pd.to_numeric(final["base_fair_price"], errors="coerce").gt(100).sum())),
        ("base_price_eq_400", int(pd.to_numeric(final["base_fair_price"], errors="coerce").eq(400).sum())),
        ("v8_price_available", int(pd.to_numeric(final["v8_fair_price"], errors="coerce").notna().sum())),
        ("v8_major_shift_50pct_plus", int(pd.to_numeric(final["v8_vs_base_delta_pct"], errors="coerce").abs().ge(50).sum())),
        ("v8_moderate_shift_20pct_plus", int(pd.to_numeric(final["v8_vs_base_delta_pct"], errors="coerce").abs().ge(20).sum())),
        ("bet_quality_uses_v8_price", int(final["bet_quality_uses_v8_price"].eq(True).sum())),
        ("bet_quality_uses_base_price", int(final["bet_quality_uses_base_price"].eq(True).sum())),
    ]

    for k, v in final["base_price_bucket"].value_counts(dropna=False).to_dict().items():
        summary.append((f"base_price_bucket_{k}", v))

    for k, v in final["price_truth_verdict"].value_counts(dropna=False).to_dict().items():
        summary.append((f"price_truth_verdict_{k}", v))

    pd.DataFrame(summary, columns=["metric","value"]).to_csv(SUMMARY, index=False)

    print("[PRICE_TRUTH_AUDIT_V1] COMPLETE")
    print(f"rows={len(final)}")
    print(f"was_capped_400={int(final['was_capped_400'].eq(True).sum())}")
    print(f"v8_major_shift_50pct_plus={int(pd.to_numeric(final['v8_vs_base_delta_pct'], errors='coerce').abs().ge(50).sum())}")
    print(f"wrote={OUT}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
