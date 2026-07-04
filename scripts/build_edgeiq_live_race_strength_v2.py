import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

STRENGTH_V3_FILE = DATA / "edgeiq_strength_adjusted_ratings_v3.csv"

OUT_FILE = DATA / "edgeiq_live_race_strength_v2.csv"
AUDIT_FILE = DATA / "edgeiq_live_race_strength_v2_audit.csv"


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

    if "race_context_key_v5_2" in df.columns:
        return df["race_context_key_v5_2"].astype(str)

    return pd.Series([""] * len(df), index=df.index)


def band_from_percentile(p):
    p = num(p, 0)

    if p >= 90:
        return "ELITE"
    if p >= 75:
        return "STRONG"
    if p >= 55:
        return "SOLID"
    if p >= 35:
        return "WEAK"
    return "VERY_WEAK"


def competitiveness_band(v):
    v = num(v, 0)

    if v >= 80:
        return "DEEP_COMPETITIVE"
    if v >= 65:
        return "COMPETITIVE"
    if v >= 45:
        return "NORMAL"
    if v >= 25:
        return "THIN"
    return "VERY_THIN"


def status_counts(group):
    statuses = group.get("projection_status_v6", pd.Series([], dtype=str)).astype(str).str.upper()

    return {
        "proven_runners": int((statuses == "PROVEN").sum()),
        "limited_runners": int(statuses.str.contains("LIMITED", na=False).sum()),
        "unknown_runners": int(statuses.isin(["FIRST_STARTER_OR_UNKNOWN", "IMPORT_UNKNOWN"]).sum()),
    }


def main():
    if not STRENGTH_V3_FILE.exists():
        raise FileNotFoundError(f"Missing {STRENGTH_V3_FILE}")

    df = pd.read_csv(STRENGTH_V3_FILE)
    df["race_key"] = build_race_key(df)

    rows = []

    for race_key, g in df.groupby("race_key", dropna=False):
        g = g.copy()

        date_col = first_existing(g, ["race_date", "meeting_date", "date"])
        track_col = first_existing(g, ["track", "meeting_name", "location"])
        race_col = first_existing(g, ["race_no", "race_number"])

        ratings = pd.to_numeric(g.get("strength_adjusted_rating_v3"), errors="coerce")
        raw_ratings = pd.to_numeric(g.get("raw_strength_adjusted_rating_v3"), errors="coerce")
        governance = pd.to_numeric(g.get("projection_governance_score_v6"), errors="coerce")
        confidence = pd.to_numeric(g.get("strength_confidence_score_v3"), errors="coerce")

        clean = ratings.dropna()
        raw_clean = raw_ratings.dropna()

        field_size = len(g)
        rated_field_size = int(clean.notna().sum())

        if len(clean) == 0:
            top_runner_rating = 50.0
            top3_avg_rating = 50.0
            top5_avg_rating = 50.0
            field_avg_rating = 50.0
            field_median_rating = 50.0
            field_rating_stddev = 0.0
        else:
            sorted_r = clean.sort_values(ascending=False)
            top_runner_rating = float(sorted_r.iloc[0])
            top3_avg_rating = float(sorted_r.head(3).mean())
            top5_avg_rating = float(sorted_r.head(5).mean())
            field_avg_rating = float(clean.mean())
            field_median_rating = float(clean.median())
            field_rating_stddev = float(clean.std(ddof=0)) if len(clean) > 1 else 0.0

        counts = status_counts(g)

        proven_ratio = counts["proven_runners"] / field_size if field_size else 0
        unknown_ratio = counts["unknown_runners"] / field_size if field_size else 1

        confidence_avg = float(confidence.dropna().mean()) if confidence.dropna().shape[0] else 40.0
        governance_avg = float(governance.dropna().mean()) if governance.dropna().shape[0] else 40.0

        depth_score = (
            top_runner_rating * 0.25
            + top3_avg_rating * 0.30
            + top5_avg_rating * 0.20
            + field_avg_rating * 0.15
            + governance_avg * 0.10
        )

        reliability_score = (
            proven_ratio * 100.0 * 0.55
            + (1.0 - unknown_ratio) * 100.0 * 0.25
            + confidence_avg * 0.20
        )

        competitiveness_score = (
            max(0.0, 100.0 - min(field_rating_stddev * 5.0, 50.0)) * 0.45
            + min(field_size / 16.0 * 100.0, 100.0) * 0.25
            + top5_avg_rating * 0.30
        )

        field_strength_score_live_v2 = (
            depth_score * 0.60
            + reliability_score * 0.25
            + competitiveness_score * 0.15
        )

        rows.append({
            "race_key": race_key,
            "race_date": str(g[date_col].iloc[0]) if date_col else "",
            "track": str(g[track_col].iloc[0]) if track_col else "",
            "race_no": str(g[race_col].iloc[0]) if race_col else "",
            "distance": g["distance"].iloc[0] if "distance" in g.columns else "",
            "race_class": g["race_class_raw_current_v5_2"].iloc[0] if "race_class_raw_current_v5_2" in g.columns else "",
            "track_condition": g["track_condition"].iloc[0] if "track_condition" in g.columns else "",
            "field_size": field_size,
            "rated_field_size": rated_field_size,
            "proven_runners": counts["proven_runners"],
            "limited_runners": counts["limited_runners"],
            "unknown_runners": counts["unknown_runners"],
            "proven_ratio": round(proven_ratio, 3),
            "unknown_ratio": round(unknown_ratio, 3),
            "top_runner_rating": round(top_runner_rating, 3),
            "top3_avg_rating": round(top3_avg_rating, 3),
            "top5_avg_rating": round(top5_avg_rating, 3),
            "field_avg_rating": round(field_avg_rating, 3),
            "field_median_rating": round(field_median_rating, 3),
            "field_rating_stddev": round(field_rating_stddev, 3),
            "field_depth_score_live_v2": round(depth_score, 3),
            "field_reliability_score_live_v2": round(reliability_score, 3),
            "field_competitiveness_score_live_v2": round(competitiveness_score, 3),
            "field_competitiveness_band_live_v2": competitiveness_band(competitiveness_score),
            "field_strength_score_live_v2": round(field_strength_score_live_v2, 3),
        })

    out = pd.DataFrame(rows)

    out["field_strength_percentile_live_v2"] = (
        out["field_strength_score_live_v2"].rank(pct=True, method="max") * 100
    ).round(3)

    out["race_strength_band_live_v2"] = out["field_strength_percentile_live_v2"].map(band_from_percentile)

    out["live_race_strength_engine"] = "LIVE_RACE_STRENGTH_V2"
    out["live_race_strength_inputs"] = "strength_adjusted_ratings_v3|projection_governance_v6"

    audit = pd.DataFrame([{
        "rows": len(out),
        "unique_races": out["race_key"].nunique(),
        "avg_field_size": round(float(out["field_size"].mean()), 3),
        "avg_field_strength_score": round(float(out["field_strength_score_live_v2"].mean()), 3),
        "min_field_strength_score": round(float(out["field_strength_score_live_v2"].min()), 3),
        "max_field_strength_score": round(float(out["field_strength_score_live_v2"].max()), 3),
        "elite": int((out["race_strength_band_live_v2"] == "ELITE").sum()),
        "strong": int((out["race_strength_band_live_v2"] == "STRONG").sum()),
        "solid": int((out["race_strength_band_live_v2"] == "SOLID").sum()),
        "weak": int((out["race_strength_band_live_v2"] == "WEAK").sum()),
        "very_weak": int((out["race_strength_band_live_v2"] == "VERY_WEAK").sum()),
        "output": str(OUT_FILE),
    }])

    out.to_csv(OUT_FILE, index=False)
    audit.to_csv(AUDIT_FILE, index=False)

    print("[LIVE_RACE_STRENGTH_V2] COMPLETE")
    print(f"races={len(out)}")
    print(f"wrote={OUT_FILE}")
    print(f"audit={AUDIT_FILE}")
    print(out["race_strength_band_live_v2"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
