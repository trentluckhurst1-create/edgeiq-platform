import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PROJECTION_FILE = DATA / "edgeiq_current_field_projection_v5_2.csv"
SECTIONAL_FILE = DATA / "edgeiq_sectional_strength_v2.csv"
GENOME_FILE = DATA / "edgeiq_horse_genome_v3.csv"
PREDICTABILITY_FILE = DATA / "edgeiq_predictability_v1.csv"
RACE_STRENGTH_FILE = DATA / "edgeiq_race_strength_v1.csv"

OUT_FILE = DATA / "edgeiq_strength_adjusted_ratings_v2.csv"
AUDIT_FILE = DATA / "edgeiq_strength_adjusted_ratings_v2_audit.csv"


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


def normalise_0_100(series, default=50.0):
    s = pd.to_numeric(series, errors="coerce")
    valid = s.dropna()
    if len(valid) == 0:
        return pd.Series([default] * len(series), index=series.index)
    lo = valid.quantile(0.05)
    hi = valid.quantile(0.95)
    if hi == lo:
        return pd.Series([default] * len(series), index=series.index)
    out = ((s - lo) / (hi - lo)) * 100.0
    out = out.clip(0, 100)
    return out.fillna(default)


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


def make_reason(row):
    parts = []

    vals = {
        "projection": num(row.get("projection_contribution_v2"), 0),
        "sectional strength": num(row.get("sectional_contribution_v2"), 0),
        "horse genome": num(row.get("genome_contribution_v2"), 0),
        "predictability": num(row.get("predictability_contribution_v2"), 0),
        "race strength": num(row.get("race_strength_contribution_v2"), 0),
    }

    main = max(vals, key=vals.get)
    parts.append(f"main driver={main}")

    if num(row.get("sectional_strength_rating"), 0) >= 68:
        parts.append("strong sectional support")
    if num(row.get("horse_genome_score_v3"), 50) < 35:
        parts.append("weak horse genome")
    if num(row.get("predictability_score_v1"), 50) < 35:
        parts.append("volatile or low-confidence profile")
    if num(row.get("projected_rating_v5_2"), 0) <= 0:
        parts.append("no projection; neutral fallback used")

    return "; ".join(parts)


def main():
    proj = pd.read_csv(PROJECTION_FILE)

    sectionals = pd.read_csv(SECTIONAL_FILE) if SECTIONAL_FILE.exists() else pd.DataFrame()
    genome = pd.read_csv(GENOME_FILE) if GENOME_FILE.exists() else pd.DataFrame()
    predict = pd.read_csv(PREDICTABILITY_FILE) if PREDICTABILITY_FILE.exists() else pd.DataFrame()
    race_strength = pd.read_csv(RACE_STRENGTH_FILE) if RACE_STRENGTH_FILE.exists() else pd.DataFrame()

    out = proj.copy()

    if "horse_key" not in out.columns:
        if "horse_match_key_v5_2" in out.columns:
            out["horse_key"] = out["horse_match_key_v5_2"]
        else:
            out["horse_key"] = out["horse"].map(clean_key)

    out["horse_key_join"] = out["horse_key"].map(clean_key)

    if len(sectionals):
        if "horse_key" not in sectionals.columns:
            sectionals["horse_key"] = sectionals.get("horse_name", "").map(clean_key)
        sectionals["horse_key_join"] = sectionals["horse_key"].map(clean_key)

        sec_cols = [
            "horse_key_join",
            "sectional_strength_rating",
            "sectional_strength_band",
            "sectional_strength_confidence",
        ]
        sec_cols = [c for c in sec_cols if c in sectionals.columns]
        out = out.merge(sectionals[sec_cols].drop_duplicates("horse_key_join"), on="horse_key_join", how="left")

    if len(genome):
        if "horse_key" not in genome.columns:
            genome["horse_key"] = genome.get("horse_name", "").map(clean_key)
        genome["horse_key_join"] = genome["horse_key"].map(clean_key)

        gen_cols = [
            "horse_key_join",
            "horse_genome_score_v3",
            "horse_genome_band_v3",
            "genome_confidence_v3",
        ]
        gen_cols = [c for c in gen_cols if c in genome.columns]
        out = out.merge(genome[gen_cols].drop_duplicates("horse_key_join"), on="horse_key_join", how="left")

    if len(predict):
        if "horse_key" not in predict.columns:
            predict["horse_key"] = predict.get("horse_name", "").map(clean_key)
        predict["horse_key_join"] = predict["horse_key"].map(clean_key)

        pred_cols = [
            "horse_key_join",
            "predictability_score_v1",
            "predictability_band_v1",
            "predictability_confidence_v1",
        ]
        pred_cols = [c for c in pred_cols if c in predict.columns]
        out = out.merge(predict[pred_cols].drop_duplicates("horse_key_join"), on="horse_key_join", how="left")

    if len(race_strength):
        date_col = "race_date" if "race_date" in race_strength.columns else "meeting_date" if "meeting_date" in race_strength.columns else None
        track_col = "track" if "track" in race_strength.columns else None
        race_col = "race_no" if "race_no" in race_strength.columns else None

        if date_col and track_col and race_col and "field_strength_score" in race_strength.columns:
            race_strength["race_key_join"] = (
                race_strength[date_col].astype(str).str.strip()
                + "|"
                + race_strength[track_col].map(norm_track)
                + "|R"
                + race_strength[race_col].astype(str).str.replace(".0", "", regex=False).str.strip()
            )

            if "race_date" in out.columns:
                live_date_col = "race_date"
            elif "meeting_date" in out.columns:
                live_date_col = "meeting_date"
            else:
                live_date_col = None

            if "track" in out.columns:
                live_track_col = "track"
            elif "meeting_name" in out.columns:
                live_track_col = "meeting_name"
            else:
                live_track_col = None

            if "race_no" in out.columns:
                live_race_col = "race_no"
            else:
                live_race_col = None

            if live_date_col and live_track_col and live_race_col:
                out["race_key_join"] = (
                    out[live_date_col].astype(str).str.strip()
                    + "|"
                    + out[live_track_col].map(norm_track)
                    + "|R"
                    + out[live_race_col].astype(str).str.replace(".0", "", regex=False).str.strip()
                )

                rs = race_strength[["race_key_join", "field_strength_score"]].drop_duplicates("race_key_join")
                out = out.merge(rs, on="race_key_join", how="left")

    if "race_key_join" not in out.columns:
        if "race_context_key_v5_2" in out.columns:
            out["race_key_join"] = out["race_context_key_v5_2"]
        else:
            out["race_key_join"] = ""

    out["projection_norm_v2"] = normalise_0_100(out.get("projected_rating_v5_2", pd.Series(index=out.index)), 50.0)
    out["sectional_norm_v2"] = pd.to_numeric(out.get("sectional_strength_rating", pd.Series(index=out.index)), errors="coerce").fillna(50.0)
    out["genome_norm_v2"] = pd.to_numeric(out.get("horse_genome_score_v3", pd.Series(index=out.index)), errors="coerce").fillna(50.0)
    out["predictability_norm_v2"] = pd.to_numeric(out.get("predictability_score_v1", pd.Series(index=out.index)), errors="coerce").fillna(50.0)
    out["race_strength_norm_v2"] = pd.to_numeric(out.get("field_strength_score", pd.Series(index=out.index)), errors="coerce").fillna(50.0)

    out["projection_contribution_v2"] = out["projection_norm_v2"] * 0.30
    out["sectional_contribution_v2"] = out["sectional_norm_v2"] * 0.25
    out["genome_contribution_v2"] = out["genome_norm_v2"] * 0.20
    out["predictability_contribution_v2"] = out["predictability_norm_v2"] * 0.15
    out["race_strength_contribution_v2"] = out["race_strength_norm_v2"] * 0.10

    out["strength_adjusted_rating_v2"] = (
        out["projection_contribution_v2"]
        + out["sectional_contribution_v2"]
        + out["genome_contribution_v2"]
        + out["predictability_contribution_v2"]
        + out["race_strength_contribution_v2"]
    ).round(3)

    out["strength_adjusted_percentile_v2"] = (
        out["strength_adjusted_rating_v2"].rank(pct=True, method="max") * 100
    ).round(3)

    out["strength_adjusted_band_v2"] = out["strength_adjusted_percentile_v2"].map(band_from_percentile)
    out["strength_adjusted_reason_v2"] = out.apply(make_reason, axis=1)

    out["strength_adjusted_engine"] = "STRENGTH_ADJUSTED_RATINGS_V2"
    out["strength_adjusted_inputs"] = "projection_v5_2|sectional_strength_v2|horse_genome_v3|predictability_v1|race_strength_v1"

    audit = pd.DataFrame([{
        "rows": len(out),
        "elite": int((out["strength_adjusted_band_v2"] == "ELITE").sum()),
        "strong": int((out["strength_adjusted_band_v2"] == "STRONG").sum()),
        "positive": int((out["strength_adjusted_band_v2"] == "POSITIVE").sum()),
        "neutral": int((out["strength_adjusted_band_v2"] == "NEUTRAL").sum()),
        "poor": int((out["strength_adjusted_band_v2"] == "POOR").sum()),
        "blank_rating_rows": int(out["strength_adjusted_rating_v2"].isna().sum()),
        "avg_rating": round(float(out["strength_adjusted_rating_v2"].mean()), 3),
        "min_rating": round(float(out["strength_adjusted_rating_v2"].min()), 3),
        "max_rating": round(float(out["strength_adjusted_rating_v2"].max()), 3),
        "sectional_matched": int(out["sectional_strength_rating"].notna().sum()) if "sectional_strength_rating" in out.columns else 0,
        "genome_matched": int(out["horse_genome_score_v3"].notna().sum()) if "horse_genome_score_v3" in out.columns else 0,
        "predictability_matched": int(out["predictability_score_v1"].notna().sum()) if "predictability_score_v1" in out.columns else 0,
        "race_strength_matched": int(out["field_strength_score"].notna().sum()) if "field_strength_score" in out.columns else 0,
        "output": str(OUT_FILE),
    }])

    out.to_csv(OUT_FILE, index=False)
    audit.to_csv(AUDIT_FILE, index=False)

    print("[STRENGTH_ADJUSTED_RATINGS_V2] COMPLETE")
    print(f"rows={len(out)}")
    print(f"blank_rating_rows={int(out['strength_adjusted_rating_v2'].isna().sum())}")
    print(f"wrote={OUT_FILE}")
    print(f"audit={AUDIT_FILE}")
    print(out["strength_adjusted_band_v2"].value_counts().to_string())


if __name__ == "__main__":
    main()
