import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

STRENGTH_FILE = DATA / "edgeiq_strength_adjusted_ratings_v2.csv"
PACE_FILE = DATA / "edgeiq_pace_advantage_v4.csv"
SHAPE_FILE = DATA / "edgeiq_race_shape_fit_v1.csv"
HIDDEN_FILE = DATA / "edgeiq_hidden_runner_v2.csv"
VULN_FILE = DATA / "edgeiq_vulnerability_v1.csv"
PREDICT_FILE = DATA / "edgeiq_predictability_v1.csv"
MARKET_FILE = DATA / "edgeiq_market_rank_v1.csv"

OUT_FILE = DATA / "edgeiq_fair_price_v6.csv"
AUDIT_FILE = DATA / "edgeiq_fair_price_v6_audit.csv"


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

    if "race_context_key_v5_2" in df.columns:
        return df["race_context_key_v5_2"].astype(str)

    return pd.Series([""] * len(df), index=df.index)


def band_score(v, mapping, default=50):
    if pd.isna(v):
        return default
    return mapping.get(str(v).upper().strip(), default)


def confidence_band(v):
    v = num(v, 0)
    if v >= 80:
        return "HIGH"
    if v >= 65:
        return "MEDIUM"
    if v >= 50:
        return "LOW"
    return "VERY_LOW"


def fair_band(edge):
    edge = num(edge, 0)
    if edge >= 25:
        return "MAJOR_OVERLAY"
    if edge >= 15:
        return "STRONG_OVERLAY"
    if edge >= 8:
        return "OVERLAY"
    if edge >= 0:
        return "FAIR"
    if edge <= -20:
        return "BAD_UNDERLAY"
    return "UNDERLAY"


def reason(row):
    parts = []

    if num(row.get("strength_adjusted_rating_v2"), 0) >= 58:
        parts.append("strong base rating")
    if num(row.get("pace_advantage_score_v4"), 50) >= 65:
        parts.append("pace advantage")
    if num(row.get("race_shape_fit_score_v1"), 50) >= 70:
        parts.append("positive race-shape fit")
    if num(row.get("hidden_runner_score_v2"), 0) >= 65:
        parts.append("hidden-runner signal")
    if num(row.get("vulnerability_score_v1"), 0) >= 65:
        parts.append("vulnerability penalty")
    if num(row.get("edge_pct_v6"), 0) >= 15:
        parts.append("market overlay")
    if num(row.get("edge_pct_v6"), 0) < 0:
        parts.append("market underlay")

    if not parts:
        parts.append("neutral composite profile")

    return "; ".join(parts)


def merge_optional(base, path, score_cols, suffix_name):
    if not path.exists():
        for c in score_cols:
            if c not in base.columns:
                base[c] = np.nan
        return base, 0

    df = pd.read_csv(path)
    df["horse_key_join"] = df[first_existing(df, ["horse_key", "horse_match_key_v5_2", "horse"])].map(clean_key)
    df["race_key_join"] = build_race_key(df)

    cols = ["race_key_join", "horse_key_join"] + [c for c in score_cols if c in df.columns]
    df = df[cols].drop_duplicates(["race_key_join", "horse_key_join"])

    before = len(base)
    base = base.merge(df, on=["race_key_join", "horse_key_join"], how="left", suffixes=("", f"_{suffix_name}"))
    matched = 0

    for c in score_cols:
        if c in base.columns:
            matched = max(matched, int(base[c].notna().sum()))

    if len(base) != before:
        print(f"[WARN] row count changed after {suffix_name}: before={before} after={len(base)}")

    return base, matched


def main():
    if not STRENGTH_FILE.exists():
        raise FileNotFoundError(f"Missing {STRENGTH_FILE}")

    out = pd.read_csv(STRENGTH_FILE)

    out["horse_key_join"] = out[first_existing(out, ["horse_key", "horse_match_key_v5_2", "horse"])].map(clean_key)
    out["race_key_join"] = build_race_key(out)

    out, pace_matched = merge_optional(
        out,
        PACE_FILE,
        [
            "pace_advantage_score_v4",
            "pace_advantage_band_v4",
            "race_shape_fit_score_v1",
            "shape_benefit_score_v4",
            "shape_penalty_score_v4",
            "pace_advantage_reason_v4",
        ],
        "pace",
    )

    out, shape_matched = merge_optional(
        out,
        SHAPE_FILE,
        [
            "race_shape_fit_score_v1",
            "race_shape_fit_band_v1",
            "shape_fit_rank_in_race",
            "shape_fit_percentile_in_race",
            "shape_fit_confidence_v1",
            "shape_fit_reason_v1",
        ],
        "shape",
    )

    out, hidden_matched = merge_optional(
        out,
        HIDDEN_FILE,
        [
            "hidden_runner_score_v2",
            "hidden_runner_band_v2",
            "hidden_runner_reason_v2",
            "shape_edge_score_v1",
        ],
        "hidden",
    )

    out, vuln_matched = merge_optional(
        out,
        VULN_FILE,
        [
            "vulnerability_score_v1",
            "vulnerability_band_v1",
            "vulnerability_reason_v1",
        ],
        "vuln",
    )

    out, market_matched = merge_optional(
        out,
        MARKET_FILE,
        [
            "market_price_v1",
            "market_rank_v1",
            "market_field_size_v1",
            "shape_edge_v1",
            "shape_edge_band_v1",
        ],
        "market",
    )

    out["strength_component_v6"] = pd.to_numeric(out.get("strength_adjusted_rating_v2"), errors="coerce").fillna(50) * 0.40
    out["pace_component_v6"] = pd.to_numeric(out.get("pace_advantage_score_v4"), errors="coerce").fillna(50) * 0.20
    out["shape_component_v6"] = pd.to_numeric(out.get("race_shape_fit_score_v1"), errors="coerce").fillna(50) * 0.15
    out["hidden_component_v6"] = pd.to_numeric(out.get("hidden_runner_score_v2"), errors="coerce").fillna(50) * 0.10
    out["predictability_component_v6"] = pd.to_numeric(out.get("predictability_score_v1"), errors="coerce").fillna(50) * 0.10

    vuln_raw = pd.to_numeric(out.get("vulnerability_score_v1"), errors="coerce").fillna(0)
    out["vulnerability_penalty_v6"] = vuln_raw * 0.05

    out["fair_score_v6"] = (
        out["strength_component_v6"]
        + out["pace_component_v6"]
        + out["shape_component_v6"]
        + out["hidden_component_v6"]
        + out["predictability_component_v6"]
        - out["vulnerability_penalty_v6"]
    ).clip(1, 99).round(3)

    out["fair_score_exp_v6"] = np.exp(out["fair_score_v6"] / 14.0)

    out["race_total_exp_v6"] = out.groupby("race_key_join")["fair_score_exp_v6"].transform("sum")
    out["fair_probability_v6"] = (out["fair_score_exp_v6"] / out["race_total_exp_v6"]).clip(0.001, 0.85)

    out["fair_price_v6"] = (1 / out["fair_probability_v6"]).round(2)
    out["fair_probability_v6"] = (out["fair_probability_v6"] * 100).round(3)

    if "market_price_v1" in out.columns:
        out["market_price_v6"] = pd.to_numeric(out["market_price_v1"], errors="coerce")
    else:
        out["market_price_v6"] = np.nan

    out["edge_pct_v6"] = np.where(
        out["market_price_v6"].notna() & (out["fair_price_v6"] > 0),
        ((out["market_price_v6"] / out["fair_price_v6"]) - 1) * 100,
        np.nan,
    )
    out["edge_pct_v6"] = pd.to_numeric(out["edge_pct_v6"], errors="coerce").round(1)

    out["overlay_pct_v6"] = out["edge_pct_v6"]

    out["fair_rank_v6"] = out.groupby("race_key_join")["fair_probability_v6"].rank(
        ascending=False,
        method="min"
    ).astype(int)

    out["fair_band_v6"] = out["edge_pct_v6"].map(fair_band)

    confidence = 40.0
    confidence += np.where(pd.to_numeric(out.get("strength_adjusted_rating_v2"), errors="coerce").notna(), 15, 0)
    confidence += np.where(pd.to_numeric(out.get("pace_advantage_score_v4"), errors="coerce").notna(), 10, 0)
    confidence += np.where(pd.to_numeric(out.get("race_shape_fit_score_v1"), errors="coerce").notna(), 10, 0)
    confidence += np.where(pd.to_numeric(out.get("hidden_runner_score_v2"), errors="coerce").notna(), 5, 0)
    confidence += np.where(pd.to_numeric(out.get("vulnerability_score_v1"), errors="coerce").notna(), 5, 0)
    confidence += np.where(pd.to_numeric(out.get("market_price_v6"), errors="coerce").notna(), 15, 0)

    out["confidence_score_v6"] = pd.Series(confidence, index=out.index).clip(0, 100).round(1)
    out["confidence_band_v6"] = out["confidence_score_v6"].map(confidence_band)

    out["pricing_reason_v6"] = out.apply(reason, axis=1)

    out["fair_price_engine"] = "FAIR_PRICE_ENGINE_V6"
    out["fair_price_inputs"] = "strength_v2|pace_advantage_v4|race_shape_fit_v1|hidden_v2|vulnerability_v1|predictability_v1|market_rank_v1"

    audit = pd.DataFrame([{
        "rows": len(out),
        "unique_races": out["race_key_join"].nunique(),
        "unique_horses": out["horse_key_join"].nunique(),
        "pace_matched": pace_matched,
        "shape_matched": shape_matched,
        "hidden_matched": hidden_matched,
        "vulnerability_matched": vuln_matched,
        "market_matched": market_matched,
        "market_prices": int(out["market_price_v6"].notna().sum()),
        "avg_fair_price": round(float(out["fair_price_v6"].mean()), 3),
        "min_fair_price": round(float(out["fair_price_v6"].min()), 3),
        "max_fair_price": round(float(out["fair_price_v6"].max()), 3),
        "major_overlay": int((out["fair_band_v6"] == "MAJOR_OVERLAY").sum()),
        "strong_overlay": int((out["fair_band_v6"] == "STRONG_OVERLAY").sum()),
        "overlay": int((out["fair_band_v6"] == "OVERLAY").sum()),
        "fair": int((out["fair_band_v6"] == "FAIR").sum()),
        "underlay": int((out["fair_band_v6"] == "UNDERLAY").sum()),
        "bad_underlay": int((out["fair_band_v6"] == "BAD_UNDERLAY").sum()),
        "output": str(OUT_FILE),
    }])

    out.to_csv(OUT_FILE, index=False)
    audit.to_csv(AUDIT_FILE, index=False)

    print("[FAIR_PRICE_ENGINE_V6] COMPLETE")
    print(f"rows={len(out)}")
    print(f"races={out['race_key_join'].nunique()}")
    print(f"market_prices={int(out['market_price_v6'].notna().sum())}")
    print(f"wrote={OUT_FILE}")
    print(f"audit={AUDIT_FILE}")
    print(out["fair_band_v6"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
