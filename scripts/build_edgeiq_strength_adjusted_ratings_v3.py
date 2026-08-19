import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

GOV_FILE = DATA / "edgeiq_projection_governance_v6.csv"
SECTIONAL_FILE = DATA / "edgeiq_sectional_strength_v2.csv"
GENOME_FILE = DATA / "edgeiq_horse_genome_v3.csv"
PREDICTABILITY_FILE = DATA / "edgeiq_predictability_v1.csv"
RACE_STRENGTH_FILE = DATA / "edgeiq_race_strength_v1.csv"

OUT_FILE = DATA / "edgeiq_strength_adjusted_ratings_v3.csv"
AUDIT_FILE = DATA / "edgeiq_strength_adjusted_ratings_v3_audit.csv"


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
    return out.clip(0, 100).fillna(default)


def governance_multiplier(status):
    status = str(status).upper().strip()

    if status == "PROVEN":
        return 1.00
    if status == "PROVEN_UNCLEAR_HISTORY":
        return 0.95
    if status == "LIMITED_DATA_3_4_STARTS":
        return 0.92
    if status == "LIMITED_DATA_2_STARTS":
        return 0.82
    if status == "LIMITED_DATA_1_START":
        return 0.72
    if status == "IMPORT_UNKNOWN":
        return 0.60
    if status == "FIRST_STARTER_OR_UNKNOWN":
        return 0.45

    return 0.70


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


def reason(row):
    parts = []

    status = str(row.get("projection_status_v6", ""))

    if status == "PROVEN":
        parts.append("proven projection")
    elif status in ["LIMITED_DATA_3_4_STARTS", "LIMITED_DATA_2_STARTS", "LIMITED_DATA_1_START"]:
        parts.append("limited-data governance applied")
    elif status in ["FIRST_STARTER_OR_UNKNOWN", "IMPORT_UNKNOWN"]:
        parts.append("unknown-runner governance penalty")

    if num(row.get("sectional_strength_rating"), 0) >= 68:
        parts.append("strong sectional support")
    if num(row.get("horse_genome_score_v3"), 50) < 35:
        parts.append("weak horse genome")
    if num(row.get("predictability_score_v1"), 50) < 35:
        parts.append("volatile profile")

    if num(row.get("governance_multiplier_v3"), 1) < 0.75:
        parts.append("confidence suppressed")

    if not parts:
        parts.append("neutral strength profile")

    return "; ".join(parts)


def merge_horse_level(base, path, cols, suffix_name):
    if not path.exists():
        for c in cols:
            if c not in base.columns:
                base[c] = np.nan
        return base, 0

    df = pd.read_csv(path)

    key_col = first_existing(df, ["horse_key", "horse_match_key_v5_2", "horse_name", "horse"])
    if key_col is None:
        return base, 0

    df["horse_key_join"] = df[key_col].map(clean_key)

    use_cols = ["horse_key_join"] + [c for c in cols if c in df.columns]
    df = df[use_cols].drop_duplicates("horse_key_join")

    before = len(base)
    base = base.merge(df, on="horse_key_join", how="left", suffixes=("", f"_{suffix_name}"))

    if len(base) != before:
        print(f"[WARN] row count changed after {suffix_name}: before={before} after={len(base)}")

    matched = 0
    for c in cols:
        if c in base.columns:
            matched = max(matched, int(base[c].notna().sum()))

    return base, matched


def main():
    if not GOV_FILE.exists():
        raise FileNotFoundError(f"Missing {GOV_FILE}")

    out = pd.read_csv(GOV_FILE)

    if "horse_key" not in out.columns:
        if "horse_match_key_v5_2" in out.columns:
            out["horse_key"] = out["horse_match_key_v5_2"]
        else:
            out["horse_key"] = out["horse"].map(clean_key)

    out["horse_key_join"] = out["horse_key"].map(clean_key)
    out["race_key_join"] = build_race_key(out)

    out, sectional_matched = merge_horse_level(
        out,
        SECTIONAL_FILE,
        [
            "sectional_strength_rating",
            "sectional_strength_band",
            "sectional_strength_confidence",
        ],
        "sectional",
    )

    out, genome_matched = merge_horse_level(
        out,
        GENOME_FILE,
        [
            "horse_genome_score_v3",
            "horse_genome_band_v3",
            "genome_confidence_v3",
        ],
        "genome",
    )

    out, predictability_matched = merge_horse_level(
        out,
        PREDICTABILITY_FILE,
        [
            "predictability_score_v1",
            "predictability_band_v1",
            "predictability_confidence_v1",
        ],
        "predictability",
    )

    if RACE_STRENGTH_FILE.exists():
        race_strength = pd.read_csv(RACE_STRENGTH_FILE)

        date_col = first_existing(race_strength, ["race_date", "meeting_date", "date"])
        track_col = first_existing(race_strength, ["track", "meeting_name", "location"])
        race_col = first_existing(race_strength, ["race_no", "race_number"])

        if date_col and track_col and race_col and "field_strength_score" in race_strength.columns:
            race_strength["race_key_join"] = build_race_key(race_strength)
            rs = race_strength[["race_key_join", "field_strength_score"]].drop_duplicates("race_key_join")
            out = out.merge(rs, on="race_key_join", how="left")
        elif "field_strength_score" not in out.columns:
            out["field_strength_score"] = np.nan
    else:
        out["field_strength_score"] = np.nan

    out["governance_multiplier_v3"] = out["projection_status_v6"].map(governance_multiplier)

    out["projection_norm_v3"] = normalise_0_100(out.get("governed_projection_rating_v6", pd.Series(index=out.index)), 50.0)
    out["governance_norm_v3"] = pd.to_numeric(out.get("projection_governance_score_v6"), errors="coerce").fillna(40.0)
    out["sectional_norm_v3"] = pd.to_numeric(out.get("sectional_strength_rating"), errors="coerce").fillna(50.0)
    out["genome_norm_v3"] = pd.to_numeric(out.get("horse_genome_score_v3"), errors="coerce").fillna(50.0)
    out["predictability_norm_v3"] = pd.to_numeric(out.get("predictability_score_v1"), errors="coerce").fillna(50.0)
    out["race_strength_norm_v3"] = pd.to_numeric(out.get("field_strength_score"), errors="coerce").fillna(50.0)

    out["projection_contribution_v3"] = out["projection_norm_v3"] * 0.28
    out["governance_contribution_v3"] = out["governance_norm_v3"] * 0.17
    out["sectional_contribution_v3"] = out["sectional_norm_v3"] * 0.22
    out["genome_contribution_v3"] = out["genome_norm_v3"] * 0.15
    out["predictability_contribution_v3"] = out["predictability_norm_v3"] * 0.10
    out["race_strength_contribution_v3"] = out["race_strength_norm_v3"] * 0.08

    out["raw_strength_adjusted_rating_v3"] = (
        out["projection_contribution_v3"]
        + out["governance_contribution_v3"]
        + out["sectional_contribution_v3"]
        + out["genome_contribution_v3"]
        + out["predictability_contribution_v3"]
        + out["race_strength_contribution_v3"]
    )

    out["strength_adjusted_rating_v3"] = (
        out["raw_strength_adjusted_rating_v3"] * out["governance_multiplier_v3"]
    ).round(3)

    out["strength_adjusted_percentile_v3"] = (
        out["strength_adjusted_rating_v3"].rank(pct=True, method="max") * 100
    ).round(3)

    out["strength_adjusted_band_v3"] = out["strength_adjusted_percentile_v3"].map(band_from_percentile)

    conf = pd.Series(30.0, index=out.index)
    conf += np.where(out["projection_status_v6"] == "PROVEN", 25, 0)
    conf += np.where(out["projection_status_v6"] == "LIMITED_DATA_3_4_STARTS", 15, 0)
    conf += np.where(out["projection_status_v6"] == "LIMITED_DATA_2_STARTS", 10, 0)
    conf += np.where(out["projection_status_v6"] == "LIMITED_DATA_1_START", 5, 0)
    conf += np.where(pd.to_numeric(out.get("sectional_strength_rating"), errors="coerce").notna(), 10, 0)
    conf += np.where(pd.to_numeric(out.get("horse_genome_score_v3"), errors="coerce").notna(), 8, 0)
    conf += np.where(pd.to_numeric(out.get("predictability_score_v1"), errors="coerce").notna(), 7, 0)

    conf -= np.where(out["projection_status_v6"].isin(["FIRST_STARTER_OR_UNKNOWN", "IMPORT_UNKNOWN"]), 10, 0)

    out["strength_confidence_score_v3"] = conf.clip(0, 90).round(1)
    out["strength_confidence_band_v3"] = out["strength_confidence_score_v3"].map(confidence_band)

    out["strength_adjusted_reason_v3"] = out.apply(reason, axis=1)

    out["strength_adjusted_engine"] = "STRENGTH_ADJUSTED_RATINGS_V3"
    out["strength_adjusted_inputs_v3"] = "projection_governance_v6|governed_projection_v6|sectional_strength_v2|horse_genome_v3|predictability_v1|race_strength_v1"

    audit = pd.DataFrame([{
        "rows": len(out),
        "unique_races": out["race_key_join"].nunique(),
        "unique_horses": out["horse_key_join"].nunique(),
        "sectional_matched": sectional_matched,
        "genome_matched": genome_matched,
        "predictability_matched": predictability_matched,
        "race_strength_matched": int(out["field_strength_score"].notna().sum()) if "field_strength_score" in out.columns else 0,
        "avg_rating_v3": round(float(out["strength_adjusted_rating_v3"].mean()), 3),
        "min_rating_v3": round(float(out["strength_adjusted_rating_v3"].min()), 3),
        "max_rating_v3": round(float(out["strength_adjusted_rating_v3"].max()), 3),
        "elite": int((out["strength_adjusted_band_v3"] == "ELITE").sum()),
        "strong": int((out["strength_adjusted_band_v3"] == "STRONG").sum()),
        "positive": int((out["strength_adjusted_band_v3"] == "POSITIVE").sum()),
        "neutral": int((out["strength_adjusted_band_v3"] == "NEUTRAL").sum()),
        "poor": int((out["strength_adjusted_band_v3"] == "POOR").sum()),
        "proven": int((out["projection_status_v6"] == "PROVEN").sum()),
        "limited_or_unknown": int((out["projection_status_v6"] != "PROVEN").sum()),
        "output": str(OUT_FILE),
    }])

    out.to_csv(OUT_FILE, index=False)
    audit.to_csv(AUDIT_FILE, index=False)

    print("[STRENGTH_ADJUSTED_RATINGS_V3] COMPLETE")
    print(f"rows={len(out)}")
    print(f"races={out['race_key_join'].nunique()}")
    print(f"wrote={OUT_FILE}")
    print(f"audit={AUDIT_FILE}")
    print(out["strength_adjusted_band_v3"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
