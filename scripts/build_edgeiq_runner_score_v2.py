import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

STRENGTH_V4_FILE = DATA / "edgeiq_strength_adjusted_ratings_v4.csv"
PACE_FILE = DATA / "edgeiq_pace_advantage_v4.csv"
SHAPE_FILE = DATA / "edgeiq_race_shape_fit_v1.csv"
HIDDEN_FILE = DATA / "edgeiq_hidden_runner_v2.csv"
VULN_FILE = DATA / "edgeiq_vulnerability_v1.csv"

OUT_FILE = DATA / "edgeiq_runner_score_v2.csv"
AUDIT_FILE = DATA / "edgeiq_runner_score_v2_audit.csv"


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


def merge_optional(base, path, cols, suffix_name):
    if not path.exists():
        for c in cols:
            if c not in base.columns:
                base[c] = np.nan
        return base, 0

    df = pd.read_csv(path)

    key_col = first_existing(df, ["horse_key", "horse_match_key_v5_2", "horse"])
    if key_col is None:
        return base, 0

    df["horse_key_join"] = df[key_col].map(clean_key)
    df["race_key_join"] = build_race_key(df)

    use_cols = ["race_key_join", "horse_key_join"] + [c for c in cols if c in df.columns]
    df = df[use_cols].drop_duplicates(["race_key_join", "horse_key_join"])

    before = len(base)
    base = base.merge(df, on=["race_key_join", "horse_key_join"], how="left", suffixes=("", f"_{suffix_name}"))

    if len(base) != before:
        print(f"[WARN] row count changed after {suffix_name}: before={before} after={len(base)}")

    matched = 0
    for c in cols:
        if c in base.columns:
            matched = max(matched, int(base[c].notna().sum()))

    return base, matched


def race_scale(series):
    s = pd.to_numeric(series, errors="coerce")
    lo = s.min()
    hi = s.max()

    if pd.isna(lo) or pd.isna(hi):
        return pd.Series([50.0] * len(series), index=series.index)

    if hi == lo:
        return pd.Series([50.0] * len(series), index=series.index)

    return (((s - lo) / (hi - lo)) * 100.0).clip(0, 100)


def runner_band(v):
    v = num(v, 0)
    if v >= 95:
        return "ELITE"
    if v >= 85:
        return "STRONG"
    if v >= 70:
        return "POSITIVE"
    if v >= 50:
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

    if num(row.get("runner_score_v2"), 0) >= 95:
        parts.append("elite race-relative rank")
    elif num(row.get("runner_score_v2"), 0) >= 85:
        parts.append("strong race-relative rank")
    elif num(row.get("runner_score_v2"), 0) >= 70:
        parts.append("positive race-relative rank")

    if num(row.get("strength_adjusted_rating_v4"), 0) >= 65:
        parts.append("strong governed strength")
    if num(row.get("pace_advantage_score_v4"), 50) >= 65:
        parts.append("pace advantage")
    if num(row.get("race_shape_fit_score_v1"), 50) >= 70:
        parts.append("race-shape fit")
    if num(row.get("hidden_runner_score_v2"), 0) >= 65:
        parts.append("hidden-runner signal")
    if num(row.get("vulnerability_score_v1"), 0) >= 65:
        parts.append("vulnerability drag")
    if num(row.get("field_strength_score_live_v2"), 50) >= 65:
        parts.append("strong live race")
    if str(row.get("projection_status_v6", "")).upper() != "PROVEN":
        parts.append("governance caution")

    if not parts:
        parts.append("neutral race-relative profile")

    return "; ".join(parts)


def main():
    if not STRENGTH_V4_FILE.exists():
        raise FileNotFoundError(f"Missing {STRENGTH_V4_FILE}")

    out = pd.read_csv(STRENGTH_V4_FILE)

    key_col = first_existing(out, ["horse_key", "horse_match_key_v5_2", "horse"])
    out["horse_key_join"] = out[key_col].map(clean_key)
    out["race_key_join"] = build_race_key(out)

    out, pace_matched = merge_optional(
        out,
        PACE_FILE,
        [
            "pace_advantage_score_v4",
            "pace_advantage_band_v4",
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

    strength = pd.to_numeric(out.get("strength_adjusted_rating_v4"), errors="coerce").fillna(40)
    pace = pd.to_numeric(out.get("pace_advantage_score_v4"), errors="coerce").fillna(50)
    shape = pd.to_numeric(out.get("race_shape_fit_score_v1"), errors="coerce").fillna(50)
    hidden = pd.to_numeric(out.get("hidden_runner_score_v2"), errors="coerce").fillna(50)
    predict = pd.to_numeric(out.get("predictability_score_v1"), errors="coerce").fillna(50)
    live_strength = pd.to_numeric(out.get("field_strength_score_live_v2"), errors="coerce").fillna(50)
    vuln = pd.to_numeric(out.get("vulnerability_score_v1"), errors="coerce").fillna(0)

    out["runner_raw_score_v2"] = (
        strength * 0.40
        + pace * 0.18
        + shape * 0.12
        + hidden * 0.10
        + predict * 0.10
        + live_strength * 0.05
        - vuln * 0.05
    ).round(3)

    out["runner_score_v2"] = out.groupby("race_key_join")["runner_raw_score_v2"].transform(race_scale).round(3)

    out["runner_rank_v2"] = out.groupby("race_key_join")["runner_score_v2"].rank(
        ascending=False,
        method="min"
    ).astype(int)

    out["runner_percentile_v2"] = (
        out.groupby("race_key_join")["runner_score_v2"].rank(pct=True, method="max") * 100
    ).round(3)

    out["runner_band_v2"] = out["runner_score_v2"].map(runner_band)

    conf = pd.to_numeric(out.get("strength_confidence_score_v4"), errors="coerce").fillna(45)
    conf += np.where(pd.to_numeric(out.get("pace_advantage_score_v4"), errors="coerce").notna(), 5, 0)
    conf += np.where(pd.to_numeric(out.get("race_shape_fit_score_v1"), errors="coerce").notna(), 5, 0)
    conf += np.where(pd.to_numeric(out.get("hidden_runner_score_v2"), errors="coerce").notna(), 3, 0)
    conf += np.where(pd.to_numeric(out.get("predictability_score_v1"), errors="coerce").notna(), 3, 0)
    conf += np.where(pd.to_numeric(out.get("field_strength_score_live_v2"), errors="coerce").notna(), 3, 0)
    conf -= np.where(pd.to_numeric(out.get("vulnerability_score_v1"), errors="coerce").fillna(0) >= 75, 5, 0)
    conf -= np.where(out["runner_score_v2"] < 25, 4, 0)

    out["runner_confidence_score_v2"] = conf.clip(0, 95).round(1)
    out["runner_confidence_band_v2"] = out["runner_confidence_score_v2"].map(confidence_band)

    out["runner_reason_v2"] = out.apply(reason, axis=1)

    out["runner_score_engine"] = "RUNNER_SCORE_V2"
    out["runner_score_inputs_v2"] = "strength_v4|pace_advantage_v4|shape_fit_v1|hidden_v2|predictability_v1|live_race_strength_v2|vulnerability_v1"

    audit = pd.DataFrame([{
        "rows": len(out),
        "unique_races": out["race_key_join"].nunique(),
        "unique_horses": out["horse_key_join"].nunique(),
        "pace_matched": pace_matched,
        "shape_matched": shape_matched,
        "hidden_matched": hidden_matched,
        "vulnerability_matched": vuln_matched,
        "avg_runner_score": round(float(out["runner_score_v2"].mean()), 3),
        "min_runner_score": round(float(out["runner_score_v2"].min()), 3),
        "max_runner_score": round(float(out["runner_score_v2"].max()), 3),
        "elite": int((out["runner_band_v2"] == "ELITE").sum()),
        "strong": int((out["runner_band_v2"] == "STRONG").sum()),
        "positive": int((out["runner_band_v2"] == "POSITIVE").sum()),
        "neutral": int((out["runner_band_v2"] == "NEUTRAL").sum()),
        "poor": int((out["runner_band_v2"] == "POOR").sum()),
        "high_confidence": int((out["runner_confidence_band_v2"] == "HIGH").sum()),
        "medium_confidence": int((out["runner_confidence_band_v2"] == "MEDIUM").sum()),
        "low_confidence": int((out["runner_confidence_band_v2"] == "LOW").sum()),
        "very_low_confidence": int((out["runner_confidence_band_v2"] == "VERY_LOW").sum()),
        "output": str(OUT_FILE),
    }])

    out.to_csv(OUT_FILE, index=False)
    audit.to_csv(AUDIT_FILE, index=False)

    print("[RUNNER_SCORE_V2] COMPLETE")
    print(f"rows={len(out)}")
    print(f"races={out['race_key_join'].nunique()}")
    print(f"wrote={OUT_FILE}")
    print(f"audit={AUDIT_FILE}")
    print(out["runner_band_v2"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
