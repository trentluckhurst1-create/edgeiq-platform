import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

STRENGTH_V3_FILE = DATA / "edgeiq_strength_adjusted_ratings_v3.csv"
LIVE_RACE_STRENGTH_FILE = DATA / "edgeiq_live_race_strength_v2.csv"

OUT_FILE = DATA / "edgeiq_strength_adjusted_ratings_v4.csv"
AUDIT_FILE = DATA / "edgeiq_strength_adjusted_ratings_v4_audit.csv"


def num(v, default=np.nan):
    try:
        if pd.isna(v):
            return default
        if str(v).strip() == "":
            return default
        return float(v)
    except Exception:
        return default


def norm_track(v):
    if pd.isna(v):
        return ""
    return str(v).upper().strip()


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


def band_from_percentile(p):
    p = num(p, 0)
    if p >= 98:
        return "ELITE"
    if p >= 90:
        return "STRONG"
    if p >= 70:
        return "POSITIVE"
    if p >= 40:
        return "NEUTRAL"
    return "POOR"


def confidence_band(v):
    v = num(v, 0)
    if v >= 80:
        return "HIGH"
    if v >= 65:
        return "MEDIUM"
    if v >= 50:
        return "LOW"
    return "VERY_LOW"


def race_strength_adjustment(score):
    score = num(score, 50)

    if score >= 70:
        return 1.06
    if score >= 62:
        return 1.03
    if score >= 52:
        return 1.00
    if score >= 42:
        return 0.97
    return 0.93


def reason(row):
    parts = []

    if str(row.get("projection_status_v6", "")) == "PROVEN":
        parts.append("proven runner")
    elif str(row.get("projection_status_v6", "")).startswith("LIMITED"):
        parts.append("limited-data governance")
    else:
        parts.append("unknown-runner governance")

    rs = num(row.get("field_strength_score_live_v2"), 50)
    if rs >= 70:
        parts.append("elite live race strength")
    elif rs >= 62:
        parts.append("strong live race strength")
    elif rs < 42:
        parts.append("weak live race strength")

    if num(row.get("sectional_strength_rating"), 0) >= 68:
        parts.append("strong sectionals")
    if num(row.get("horse_genome_score_v3"), 50) < 35:
        parts.append("weak genome")
    if num(row.get("predictability_score_v1"), 50) < 35:
        parts.append("volatile profile")

    return "; ".join(parts)


def main():
    if not STRENGTH_V3_FILE.exists():
        raise FileNotFoundError(f"Missing {STRENGTH_V3_FILE}")

    if not LIVE_RACE_STRENGTH_FILE.exists():
        raise FileNotFoundError(f"Missing {LIVE_RACE_STRENGTH_FILE}")

    out = pd.read_csv(STRENGTH_V3_FILE)
    live = pd.read_csv(LIVE_RACE_STRENGTH_FILE)

    out["race_key_join"] = build_race_key(out)
    live["race_key_join"] = build_race_key(live)

    live_cols = [
        "race_key_join",
        "field_strength_score_live_v2",
        "field_strength_percentile_live_v2",
        "race_strength_band_live_v2",
        "field_depth_score_live_v2",
        "field_reliability_score_live_v2",
        "field_competitiveness_score_live_v2",
        "field_competitiveness_band_live_v2",
        "proven_runners",
        "limited_runners",
        "unknown_runners",
        "proven_ratio",
        "unknown_ratio",
        "top_runner_rating",
        "top3_avg_rating",
        "field_avg_rating",
    ]

    live_cols = [c for c in live_cols if c in live.columns]

    out = out.merge(
        live[live_cols].drop_duplicates("race_key_join"),
        on="race_key_join",
        how="left",
    )

    out["live_race_strength_norm_v4"] = pd.to_numeric(
        out.get("field_strength_score_live_v2"),
        errors="coerce",
    ).fillna(50.0)

    out["live_race_strength_adjustment_v4"] = out["live_race_strength_norm_v4"].map(race_strength_adjustment)

    out["base_strength_rating_v4"] = pd.to_numeric(
        out.get("strength_adjusted_rating_v3"),
        errors="coerce",
    ).fillna(40.0)

    out["strength_adjusted_rating_v4"] = (
        out["base_strength_rating_v4"] * 0.88
        + out["live_race_strength_norm_v4"] * 0.12
    ) * out["live_race_strength_adjustment_v4"]

    out["strength_adjusted_rating_v4"] = out["strength_adjusted_rating_v4"].round(3)

    out["strength_adjusted_percentile_v4"] = (
        out["strength_adjusted_rating_v4"].rank(pct=True, method="max") * 100
    ).round(3)

    out["strength_adjusted_band_v4"] = out["strength_adjusted_percentile_v4"].map(band_from_percentile)

    conf = pd.to_numeric(out.get("strength_confidence_score_v3"), errors="coerce").fillna(45)

    conf += np.where(pd.to_numeric(out.get("field_strength_score_live_v2"), errors="coerce").notna(), 8, 0)
    conf += np.where(pd.to_numeric(out.get("proven_ratio"), errors="coerce").fillna(0) >= 0.5, 5, 0)
    conf -= np.where(pd.to_numeric(out.get("unknown_ratio"), errors="coerce").fillna(1) >= 0.5, 8, 0)
    conf -= np.where(out.get("race_strength_band_live_v2", "").astype(str).isin(["VERY_WEAK"]), 5, 0)

    out["strength_confidence_score_v4"] = conf.clip(0, 92).round(1)
    out["strength_confidence_band_v4"] = out["strength_confidence_score_v4"].map(confidence_band)

    out["strength_adjusted_reason_v4"] = out.apply(reason, axis=1)

    out["strength_adjusted_engine"] = "STRENGTH_ADJUSTED_RATINGS_V4"
    out["strength_adjusted_inputs_v4"] = "strength_v3|live_race_strength_v2|projection_governance_v6"

    audit = pd.DataFrame([{
        "rows": len(out),
        "unique_races": out["race_key_join"].nunique(),
        "unique_horses": out["horse_key_join"].nunique() if "horse_key_join" in out.columns else 0,
        "live_race_strength_matched": int(out["field_strength_score_live_v2"].notna().sum()),
        "avg_rating_v4": round(float(out["strength_adjusted_rating_v4"].mean()), 3),
        "min_rating_v4": round(float(out["strength_adjusted_rating_v4"].min()), 3),
        "max_rating_v4": round(float(out["strength_adjusted_rating_v4"].max()), 3),
        "elite": int((out["strength_adjusted_band_v4"] == "ELITE").sum()),
        "strong": int((out["strength_adjusted_band_v4"] == "STRONG").sum()),
        "positive": int((out["strength_adjusted_band_v4"] == "POSITIVE").sum()),
        "neutral": int((out["strength_adjusted_band_v4"] == "NEUTRAL").sum()),
        "poor": int((out["strength_adjusted_band_v4"] == "POOR").sum()),
        "high_confidence": int((out["strength_confidence_band_v4"] == "HIGH").sum()),
        "medium_confidence": int((out["strength_confidence_band_v4"] == "MEDIUM").sum()),
        "low_confidence": int((out["strength_confidence_band_v4"] == "LOW").sum()),
        "very_low_confidence": int((out["strength_confidence_band_v4"] == "VERY_LOW").sum()),
        "output": str(OUT_FILE),
    }])

    out.to_csv(OUT_FILE, index=False)
    audit.to_csv(AUDIT_FILE, index=False)

    print("[STRENGTH_ADJUSTED_RATINGS_V4] COMPLETE")
    print(f"rows={len(out)}")
    print(f"races={out['race_key_join'].nunique()}")
    print(f"live_race_strength_matched={int(out['field_strength_score_live_v2'].notna().sum())}")
    print(f"wrote={OUT_FILE}")
    print(f"audit={AUDIT_FILE}")
    print(out["strength_adjusted_band_v4"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
