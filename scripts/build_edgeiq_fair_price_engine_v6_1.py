import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

BASE_FILE = DATA / "edgeiq_fair_price_v6.csv"

OUT_FILE = DATA / "edgeiq_fair_price_v6_1.csv"
AUDIT_FILE = DATA / "edgeiq_fair_price_v6_1_audit.csv"


def num(v, default=np.nan):
    try:
        if pd.isna(v):
            return default
        if str(v).strip() == "":
            return default
        return float(v)
    except Exception:
        return default


def band_edge(edge):
    edge = num(edge, 0)
    if edge >= 60:
        return "MAJOR_OVERLAY"
    if edge >= 30:
        return "STRONG_OVERLAY"
    if edge >= 12:
        return "OVERLAY"
    if edge >= 0:
        return "FAIR"
    if edge <= -25:
        return "BAD_UNDERLAY"
    return "UNDERLAY"


def confidence_band(v):
    v = num(v, 0)
    if v >= 80:
        return "HIGH"
    if v >= 65:
        return "MEDIUM"
    if v >= 50:
        return "LOW"
    return "VERY_LOW"


def market_rank_score(rank, field_size):
    r = num(rank, np.nan)
    f = num(field_size, np.nan)

    if pd.isna(r) or pd.isna(f) or f <= 1:
        return 50.0

    score = 100.0 - ((r - 1.0) / (f - 1.0)) * 100.0
    return max(0.0, min(100.0, score))


def pricing_reason(row):
    parts = []

    if num(row.get("strength_adjusted_rating_v2"), 0) >= 58:
        parts.append("strong base rating")
    if num(row.get("pace_advantage_score_v4"), 50) >= 65:
        parts.append("pace advantage")
    if num(row.get("race_shape_fit_score_v1"), 50) >= 70:
        parts.append("positive shape fit")
    if num(row.get("hidden_runner_score_v2"), 0) >= 65:
        parts.append("hidden-runner signal")
    if num(row.get("vulnerability_score_v1"), 0) >= 65:
        parts.append("vulnerability penalty")
    if num(row.get("market_rank_score_v6_1"), 50) >= 75:
        parts.append("market respect")
    if num(row.get("edge_pct_display_v6_1"), 0) >= 30:
        parts.append("overlay after calibration")
    if num(row.get("edge_pct_display_v6_1"), 0) < 0:
        parts.append("underlay after calibration")

    if not parts:
        parts.append("neutral calibrated profile")

    return "; ".join(parts)


def main():
    if not BASE_FILE.exists():
        raise FileNotFoundError(f"Missing {BASE_FILE}")

    out = pd.read_csv(BASE_FILE)

    out["market_rank_score_v6_1"] = out.apply(
        lambda r: market_rank_score(r.get("market_rank_v1"), r.get("market_field_size_v1")),
        axis=1,
    )

    strength = pd.to_numeric(out.get("strength_adjusted_rating_v2"), errors="coerce").fillna(50.0)
    pace = pd.to_numeric(out.get("pace_advantage_score_v4"), errors="coerce").fillna(50.0)
    shape = pd.to_numeric(out.get("race_shape_fit_score_v1"), errors="coerce").fillna(50.0)
    hidden = pd.to_numeric(out.get("hidden_runner_score_v2"), errors="coerce").fillna(50.0)
    predict = pd.to_numeric(out.get("predictability_score_v1"), errors="coerce").fillna(50.0)
    market_anchor = pd.to_numeric(out.get("market_rank_score_v6_1"), errors="coerce").fillna(50.0)
    vuln = pd.to_numeric(out.get("vulnerability_score_v1"), errors="coerce").fillna(0.0)

    out["strength_component_v6_1"] = strength * 0.35
    out["pace_component_v6_1"] = pace * 0.20
    out["shape_component_v6_1"] = shape * 0.15
    out["hidden_component_v6_1"] = hidden * 0.10
    out["predictability_component_v6_1"] = predict * 0.10
    out["market_anchor_component_v6_1"] = market_anchor * 0.05
    out["vulnerability_penalty_v6_1"] = vuln * 0.05

    out["fair_score_v6_1"] = (
        out["strength_component_v6_1"]
        + out["pace_component_v6_1"]
        + out["shape_component_v6_1"]
        + out["hidden_component_v6_1"]
        + out["predictability_component_v6_1"]
        + out["market_anchor_component_v6_1"]
        - out["vulnerability_penalty_v6_1"]
    ).clip(1, 99).round(3)

    out["fair_score_exp_v6_1"] = np.exp(out["fair_score_v6_1"] / 22.0)
    out["race_total_exp_v6_1"] = out.groupby("race_key_join")["fair_score_exp_v6_1"].transform("sum")

    out["fair_probability_raw_v6_1"] = out["fair_score_exp_v6_1"] / out["race_total_exp_v6_1"]
    out["fair_probability_v6_1"] = (out["fair_probability_raw_v6_1"] * 100).round(3)
    out["fair_price_v6_1"] = (1 / out["fair_probability_raw_v6_1"]).round(2)

    out["market_price_v6_1"] = pd.to_numeric(out.get("market_price_v6"), errors="coerce")

    out["edge_pct_raw_v6_1"] = np.where(
        out["market_price_v6_1"].notna() & (out["fair_price_v6_1"] > 0),
        ((out["market_price_v6_1"] / out["fair_price_v6_1"]) - 1.0) * 100.0,
        np.nan,
    )

    out["edge_pct_raw_v6_1"] = pd.to_numeric(out["edge_pct_raw_v6_1"], errors="coerce").round(1)
    out["edge_pct_display_v6_1"] = out["edge_pct_raw_v6_1"].clip(lower=-100, upper=100).round(1)
    out["overlay_pct_v6_1"] = out["edge_pct_display_v6_1"]

    out["fair_rank_v6_1"] = out.groupby("race_key_join")["fair_probability_v6_1"].rank(
        ascending=False,
        method="min",
    ).astype(int)

    out["fair_band_v6_1"] = out["edge_pct_display_v6_1"].map(band_edge)

    conf = pd.Series(35.0, index=out.index)

    conf += np.where(strength.notna(), 12, 0)
    conf += np.where(pd.to_numeric(out.get("sectional_strength_rating"), errors="coerce").notna(), 10, 0)
    conf += np.where(pd.to_numeric(out.get("horse_genome_score_v3"), errors="coerce").notna(), 8, 0)
    conf += np.where(pd.to_numeric(out.get("predictability_score_v1"), errors="coerce").notna(), 8, 0)
    conf += np.where(pd.to_numeric(out.get("pace_advantage_score_v4"), errors="coerce").notna(), 7, 0)
    conf += np.where(pd.to_numeric(out.get("race_shape_fit_score_v1"), errors="coerce").notna(), 7, 0)
    conf += np.where(pd.to_numeric(out.get("market_price_v6_1"), errors="coerce").notna(), 8, 0)

    conf -= np.where(strength < 35, 5, 0)
    conf -= np.where(pd.to_numeric(out.get("vulnerability_score_v1"), errors="coerce").fillna(0) >= 75, 5, 0)

    out["confidence_score_v6_1"] = conf.clip(0, 90).round(1)
    out["confidence_band_v6_1"] = out["confidence_score_v6_1"].map(confidence_band)

    out["pricing_reason_v6_1"] = out.apply(pricing_reason, axis=1)

    out["fair_price_engine"] = "FAIR_PRICE_ENGINE_V6_1"
    out["fair_price_inputs_v6_1"] = "strength_v2|pace_advantage_v4|shape_fit_v1|hidden_v2|predictability_v1|market_rank_v1|vulnerability_v1"

    audit = pd.DataFrame([{
        "rows": len(out),
        "unique_races": out["race_key_join"].nunique(),
        "unique_horses": out["horse_key_join"].nunique(),
        "market_prices": int(out["market_price_v6_1"].notna().sum()),
        "avg_fair_price": round(float(out["fair_price_v6_1"].mean()), 3),
        "min_fair_price": round(float(out["fair_price_v6_1"].min()), 3),
        "max_fair_price": round(float(out["fair_price_v6_1"].max()), 3),
        "avg_confidence": round(float(out["confidence_score_v6_1"].mean()), 3),
        "min_confidence": round(float(out["confidence_score_v6_1"].min()), 3),
        "max_confidence": round(float(out["confidence_score_v6_1"].max()), 3),
        "major_overlay": int((out["fair_band_v6_1"] == "MAJOR_OVERLAY").sum()),
        "strong_overlay": int((out["fair_band_v6_1"] == "STRONG_OVERLAY").sum()),
        "overlay": int((out["fair_band_v6_1"] == "OVERLAY").sum()),
        "fair": int((out["fair_band_v6_1"] == "FAIR").sum()),
        "underlay": int((out["fair_band_v6_1"] == "UNDERLAY").sum()),
        "bad_underlay": int((out["fair_band_v6_1"] == "BAD_UNDERLAY").sum()),
        "output": str(OUT_FILE),
    }])

    out.to_csv(OUT_FILE, index=False)
    audit.to_csv(AUDIT_FILE, index=False)

    print("[FAIR_PRICE_ENGINE_V6_1] COMPLETE")
    print(f"rows={len(out)}")
    print(f"races={out['race_key_join'].nunique()}")
    print(f"market_prices={int(out['market_price_v6_1'].notna().sum())}")
    print(f"wrote={OUT_FILE}")
    print(f"audit={AUDIT_FILE}")
    print(out["fair_band_v6_1"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
