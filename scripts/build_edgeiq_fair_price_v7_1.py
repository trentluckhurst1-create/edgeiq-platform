import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER_FILE = DATA / "edgeiq_runner_score_v2.csv"
MARKET_FILE = DATA / "edgeiq_market_rank_v1.csv"

OUT_FILE = DATA / "edgeiq_fair_price_v7_1.csv"
AUDIT_FILE = DATA / "edgeiq_fair_price_v7_1_audit.csv"


def clean_key(v):
    if pd.isna(v):
        return ""
    return "".join(ch for ch in str(v).upper().strip() if ch.isalnum())


def norm_track(v):
    if pd.isna(v):
        return ""
    return str(v).upper().strip()


def num(v, default=np.nan):
    try:
        if pd.isna(v):
            return default
        if str(v).strip() == "":
            return default
        return float(v)
    except Exception:
        return default


def first_existing(df, cols):
    for c in cols:
        if c in df.columns:
            return c
    return None


def build_race_key(df):
    date_col = first_existing(df, ["race_date", "meeting_date", "date"])
    track_col = first_existing(df, ["track", "meeting_name", "location"])
    race_col = first_existing(df, ["race_no", "race_number"])

    if date_col and track_col and race_col:
        return (
            df[date_col].astype(str).str.strip()
            + "|"
            + df[track_col].map(norm_track)
            + "|R"
            + df[race_col].astype(str).str.replace(".0", "", regex=False).str.strip()
        )

    if "race_key_join" in df.columns:
        return df["race_key_join"].astype(str)

    if "race_key" in df.columns:
        return df["race_key"].astype(str)

    if "race_context_key_v5_2" in df.columns:
        return df["race_context_key_v5_2"].astype(str)

    return pd.Series([""] * len(df), index=df.index)


def uncertainty_multiplier(row):
    status = str(row.get("projection_status_v6", "")).upper().strip()
    conf = str(row.get("runner_confidence_band_v2", "")).upper().strip()

    m = 1.00

    if status == "PROVEN":
        m *= 1.00
    elif status == "LIMITED_DATA_3_4_STARTS":
        m *= 1.08
    elif status == "LIMITED_DATA_2_STARTS":
        m *= 1.15
    elif status == "LIMITED_DATA_1_START":
        m *= 1.25
    elif status == "IMPORT_UNKNOWN":
        m *= 1.35
    elif status == "FIRST_STARTER_OR_UNKNOWN":
        m *= 1.45
    else:
        m *= 1.20

    if conf == "HIGH":
        m *= 1.00
    elif conf == "MEDIUM":
        m *= 1.04
    elif conf == "LOW":
        m *= 1.10
    elif conf == "VERY_LOW":
        m *= 1.20
    else:
        m *= 1.10

    return m


def pricing_band(price):
    p = num(price, 999)

    if p < 3.0:
        return "FAVOURITE"
    if p < 6.0:
        return "CONTENDER"
    if p < 12.0:
        return "CHANCE"
    if p < 25.0:
        return "ROUGH_CHANCE"
    return "OUTSIDER"


def overlay_band(edge):
    e = num(edge, np.nan)

    if pd.isna(e):
        return "NO_MARKET"
    if e >= 40:
        return "MASSIVE_OVERLAY"
    if e >= 25:
        return "STRONG_OVERLAY"
    if e >= 12:
        return "OVERLAY"
    if e >= 0:
        return "FAIR"
    if e <= -15:
        return "SEVERE_UNDERLAY"
    return "UNDERLAY"


def cap_price_by_status(row):
    price = num(row.get("fair_price_pre_cap_v7_1"), 999)
    status = str(row.get("projection_status_v6", "")).upper().strip()
    score = num(row.get("runner_score_v2"), 0)

    # Prevent uncertain runners becoming extreme short-price favourites.
    min_price = 1.80

    if status == "LIMITED_DATA_3_4_STARTS":
        min_price = 3.20 if score >= 95 else 4.00
    elif status == "LIMITED_DATA_2_STARTS":
        min_price = 4.50
    elif status == "LIMITED_DATA_1_START":
        min_price = 6.00
    elif status == "IMPORT_UNKNOWN":
        min_price = 8.00
    elif status == "FIRST_STARTER_OR_UNKNOWN":
        min_price = 10.00
    elif status == "PROVEN":
        min_price = 1.80

    return round(max(price, min_price), 2)


def reason(row):
    parts = []

    if num(row.get("runner_score_v2"), 0) >= 85:
        parts.append("high runner score")
    elif num(row.get("runner_score_v2"), 0) >= 70:
        parts.append("positive runner score")

    status = str(row.get("projection_status_v6", "")).upper().strip()
    if status != "PROVEN":
        parts.append("uncertainty price penalty")

    if num(row.get("uncertainty_multiplier_v7_1"), 1) >= 1.25:
        parts.append("heavy governance inflation")

    if str(row.get("race_strength_band_live_v2", "")).upper() in ["ELITE", "STRONG"]:
        parts.append("strong live race context")
    elif str(row.get("race_strength_band_live_v2", "")).upper() in ["VERY_WEAK", "WEAK"]:
        parts.append("weak live race context")

    if num(row.get("edge_pct_v7_1"), 0) >= 25:
        parts.append("market overlay")
    elif num(row.get("edge_pct_v7_1"), 0) < 0:
        parts.append("market underlay")

    if not parts:
        parts.append("calibrated fair-price profile")

    return "; ".join(parts)


def main():
    if not RUNNER_FILE.exists():
        raise FileNotFoundError(f"Missing {RUNNER_FILE}")

    out = pd.read_csv(RUNNER_FILE)

    key_col = first_existing(out, ["horse_key", "horse_match_key_v5_2", "horse"])
    out["horse_key_join"] = out[key_col].map(clean_key)
    out["race_key_join"] = build_race_key(out)

    if MARKET_FILE.exists():
        market = pd.read_csv(MARKET_FILE)

        market_key_col = first_existing(market, ["horse_key", "horse_match_key_v5_2", "horse"])
        if market_key_col:
            market["horse_key_join"] = market[market_key_col].map(clean_key)
            market["race_key_join"] = build_race_key(market)

            market_cols = [
                "race_key_join",
                "horse_key_join",
                "market_price_v1",
                "market_rank_v1",
                "market_field_size_v1",
                "shape_edge_v1",
                "shape_edge_band_v1",
            ]

            market_cols = [c for c in market_cols if c in market.columns]

            out = out.merge(
                market[market_cols].drop_duplicates(["race_key_join", "horse_key_join"]),
                on=["race_key_join", "horse_key_join"],
                how="left",
            )

    score = pd.to_numeric(out.get("runner_score_v2"), errors="coerce").fillna(0).clip(0, 100)

    # Flatter curve than V7. V7 used /18 and was far too sharp.
    out["fair_weight_v7_1"] = np.exp(score / 38.0)
    out["race_total_weight_v7_1"] = out.groupby("race_key_join")["fair_weight_v7_1"].transform("sum")

    out["fair_probability_raw_v7_1"] = out["fair_weight_v7_1"] / out["race_total_weight_v7_1"]
    out["fair_probability_v7_1"] = (out["fair_probability_raw_v7_1"] * 100.0).round(3)

    out["raw_fair_price_v7_1"] = (1.0 / out["fair_probability_raw_v7_1"]).round(3)

    out["uncertainty_multiplier_v7_1"] = out.apply(uncertainty_multiplier, axis=1)

    out["fair_price_pre_cap_v7_1"] = (
        out["raw_fair_price_v7_1"] * out["uncertainty_multiplier_v7_1"]
    ).round(2)

    out["fair_price_v7_1"] = out.apply(cap_price_by_status, axis=1)

    out["fair_rank_v7_1"] = out.groupby("race_key_join")["fair_probability_raw_v7_1"].rank(
        ascending=False,
        method="min",
    ).astype(int)

    out["pricing_band_v7_1"] = out["fair_price_v7_1"].map(pricing_band)

    out["market_price_v7_1"] = pd.to_numeric(out.get("market_price_v1"), errors="coerce")

    out["edge_pct_v7_1"] = np.where(
        out["market_price_v7_1"].notna() & (out["fair_price_v7_1"] > 0),
        ((out["market_price_v7_1"] / out["fair_price_v7_1"]) - 1.0) * 100.0,
        np.nan,
    )

    out["edge_pct_v7_1"] = pd.to_numeric(out["edge_pct_v7_1"], errors="coerce").round(1)
    out["edge_pct_display_v7_1"] = out["edge_pct_v7_1"].clip(lower=-100, upper=100).round(1)
    out["overlay_band_v7_1"] = out["edge_pct_v7_1"].map(overlay_band)

    out["pricing_confidence_score_v7_1"] = pd.to_numeric(
        out.get("runner_confidence_score_v2"),
        errors="coerce",
    ).fillna(40)

    out["pricing_confidence_band_v7_1"] = out.get("runner_confidence_band_v2", "LOW")

    out["pricing_reason_v7_1"] = out.apply(reason, axis=1)

    out["fair_price_engine"] = "FAIR_PRICE_V7_1"
    out["fair_price_inputs_v7_1"] = "runner_score_v2|runner_rank_v2|runner_confidence_v2|projection_governance_v6|calibrated_exp_38"

    race_sums = (
        out.groupby("race_key_join")["fair_probability_v7_1"]
        .sum()
        .reset_index()
        .rename(columns={"fair_probability_v7_1": "race_probability_sum_v7_1"})
    )

    min_prob_sum = float(race_sums["race_probability_sum_v7_1"].min())
    max_prob_sum = float(race_sums["race_probability_sum_v7_1"].max())

    audit = pd.DataFrame([{
        "rows": len(out),
        "unique_races": out["race_key_join"].nunique(),
        "unique_horses": out["horse_key_join"].nunique(),
        "market_prices": int(out["market_price_v7_1"].notna().sum()),
        "avg_fair_price": round(float(out["fair_price_v7_1"].mean()), 3),
        "median_fair_price": round(float(out["fair_price_v7_1"].median()), 3),
        "min_fair_price": round(float(out["fair_price_v7_1"].min()), 3),
        "max_fair_price": round(float(out["fair_price_v7_1"].max()), 3),
        "min_race_probability_sum": round(min_prob_sum, 3),
        "max_race_probability_sum": round(max_prob_sum, 3),
        "favourite": int((out["pricing_band_v7_1"] == "FAVOURITE").sum()),
        "contender": int((out["pricing_band_v7_1"] == "CONTENDER").sum()),
        "chance": int((out["pricing_band_v7_1"] == "CHANCE").sum()),
        "rough_chance": int((out["pricing_band_v7_1"] == "ROUGH_CHANCE").sum()),
        "outsider": int((out["pricing_band_v7_1"] == "OUTSIDER").sum()),
        "massive_overlay": int((out["overlay_band_v7_1"] == "MASSIVE_OVERLAY").sum()),
        "strong_overlay": int((out["overlay_band_v7_1"] == "STRONG_OVERLAY").sum()),
        "overlay": int((out["overlay_band_v7_1"] == "OVERLAY").sum()),
        "fair": int((out["overlay_band_v7_1"] == "FAIR").sum()),
        "underlay": int((out["overlay_band_v7_1"] == "UNDERLAY").sum()),
        "severe_underlay": int((out["overlay_band_v7_1"] == "SEVERE_UNDERLAY").sum()),
        "no_market": int((out["overlay_band_v7_1"] == "NO_MARKET").sum()),
        "output": str(OUT_FILE),
    }])

    out.to_csv(OUT_FILE, index=False)
    audit.to_csv(AUDIT_FILE, index=False)

    print("[FAIR_PRICE_V7_1] COMPLETE")
    print(f"rows={len(out)}")
    print(f"races={out['race_key_join'].nunique()}")
    print(f"market_prices={int(out['market_price_v7_1'].notna().sum())}")
    print(f"probability_sum_range={min_prob_sum:.3f}-{max_prob_sum:.3f}")
    print(f"wrote={OUT_FILE}")
    print(f"audit={AUDIT_FILE}")
    print(out["pricing_band_v7_1"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
