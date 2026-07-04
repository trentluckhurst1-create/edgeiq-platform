import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCE_FILE = DATA / "edgeiq_runner_score_v2.csv"

OUT_FILE = DATA / "edgeiq_runner_score_v3_1.csv"
AUDIT_FILE = DATA / "edgeiq_runner_score_v3_1_audit.csv"


def num(v, default=np.nan):
    try:
        if pd.isna(v):
            return default
        if str(v).strip() == "":
            return default
        return float(v)
    except Exception:
        return default


def band(v):
    v = num(v, 0)
    if v >= 90:
        return "ELITE"
    if v >= 80:
        return "STRONG"
    if v >= 68:
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


def compress_relative_score(x):
    x = num(x, 50)
    # Pull race-relative 100s back toward a realistic absolute ceiling.
    return 50 + ((x - 50) * 0.85)


def status_penalty(status):
    status = str(status).upper().strip()
    if status == "PROVEN":
        return 0.0
    if status == "LIMITED_DATA_3_4_STARTS":
        return 1.0
    if status == "LIMITED_DATA_2_STARTS":
        return 2.0
    if status == "LIMITED_DATA_1_START":
        return 3.0
    if status == "IMPORT_UNKNOWN":
        return 5.0
    if status == "FIRST_STARTER_OR_UNKNOWN":
        return 6.0
    return 4.0


def reason(row):
    parts = []

    if num(row.get("runner_score_v3"), 0) >= 90:
        parts.append("elite calibrated runner score")
    elif num(row.get("runner_score_v3"), 0) >= 80:
        parts.append("strong calibrated runner score")
    elif num(row.get("runner_score_v3"), 0) >= 68:
        parts.append("positive calibrated runner score")

    if str(row.get("projection_status_v6", "")).upper() != "PROVEN":
        parts.append("governance penalty applied")

    if num(row.get("strength_adjusted_rating_v4"), 0) >= 70:
        parts.append("strong strength base")

    if num(row.get("field_strength_score_live_v2"), 50) >= 65:
        parts.append("strong race context")

    if num(row.get("vulnerability_score_v1"), 0) >= 65:
        parts.append("vulnerability drag")

    if not parts:
        parts.append("calibrated neutral profile")

    return "; ".join(parts)


def main():
    if not SOURCE_FILE.exists():
        raise FileNotFoundError(f"Missing {SOURCE_FILE}")

    out = pd.read_csv(SOURCE_FILE)

    strength = pd.to_numeric(out.get("strength_adjusted_rating_v4"), errors="coerce").fillna(40)
    rel = pd.to_numeric(out.get("runner_score_v2"), errors="coerce").fillna(50)
    pace = pd.to_numeric(out.get("pace_advantage_score_v4"), errors="coerce").fillna(50)
    shape = pd.to_numeric(out.get("race_shape_fit_score_v1"), errors="coerce").fillna(50)
    hidden = pd.to_numeric(out.get("hidden_runner_score_v2"), errors="coerce").fillna(50)
    predict = pd.to_numeric(out.get("predictability_score_v1"), errors="coerce").fillna(50)
    vuln = pd.to_numeric(out.get("vulnerability_score_v1"), errors="coerce").fillna(0)
    live_strength = pd.to_numeric(out.get("field_strength_score_live_v2"), errors="coerce").fillna(50)

    rel_compressed = rel.map(compress_relative_score)

    out["runner_score_v3_status_penalty"] = out.get("projection_status_v6", "").map(status_penalty)

    out["runner_raw_score_v3"] = (
        strength * 0.42
        + rel_compressed * 0.25
        + pace * 0.12
        + shape * 0.08
        + hidden * 0.06
        + predict * 0.05
        + live_strength * 0.04
        - vuln * 0.04
        - out["runner_score_v3_status_penalty"]
    ).round(3)

    # Do NOT force top horse to 100. Keep absolute calibrated score.
    out["runner_score_v3"] = out["runner_raw_score_v3"].clip(0, 100).round(3)

    out["runner_rank_v3"] = out.groupby("race_key_join")["runner_score_v3"].rank(
        ascending=False,
        method="min"
    ).astype(int)

    out["runner_percentile_v3"] = (
        out.groupby("race_key_join")["runner_score_v3"].rank(pct=True, method="max") * 100
    ).round(3)

    out["runner_band_v3"] = out["runner_score_v3"].map(band)

    conf = pd.to_numeric(out.get("runner_confidence_score_v2"), errors="coerce").fillna(45)
    conf -= np.where(out.get("projection_status_v6", "").astype(str).str.upper() == "FIRST_STARTER_OR_UNKNOWN", 10, 0)
    conf -= np.where(out.get("projection_status_v6", "").astype(str).str.upper() == "LIMITED_DATA_1_START", 6, 0)
    conf -= np.where(out.get("projection_status_v6", "").astype(str).str.upper() == "LIMITED_DATA_2_STARTS", 4, 0)
    conf -= np.where(out["runner_score_v3"] < 45, 4, 0)

    out["runner_confidence_score_v3"] = conf.clip(0, 95).round(1)
    out["runner_confidence_band_v3"] = out["runner_confidence_score_v3"].map(confidence_band)

    out["runner_reason_v3"] = out.apply(reason, axis=1)

    out["runner_score_engine"] = "RUNNER_SCORE_V3_1"
    out["runner_score_inputs_v3_1"] = "strength_v4|runner_score_v2_compressed_085|pace|shape|hidden|predictability|live_race_strength|vulnerability|lighter_governance_penalty"

    audit = pd.DataFrame([{
        "rows": len(out),
        "unique_races": out["race_key_join"].nunique(),
        "unique_horses": out["horse_key_join"].nunique() if "horse_key_join" in out.columns else 0,
        "avg_runner_score_v3": round(float(out["runner_score_v3"].mean()), 3),
        "min_runner_score_v3": round(float(out["runner_score_v3"].min()), 3),
        "max_runner_score_v3": round(float(out["runner_score_v3"].max()), 3),
        "elite": int((out["runner_band_v3"] == "ELITE").sum()),
        "strong": int((out["runner_band_v3"] == "STRONG").sum()),
        "positive": int((out["runner_band_v3"] == "POSITIVE").sum()),
        "neutral": int((out["runner_band_v3"] == "NEUTRAL").sum()),
        "poor": int((out["runner_band_v3"] == "POOR").sum()),
        "score_100_count": int((out["runner_score_v3"] >= 99.9).sum()),
        "high_confidence": int((out["runner_confidence_band_v3"] == "HIGH").sum()),
        "medium_confidence": int((out["runner_confidence_band_v3"] == "MEDIUM").sum()),
        "low_confidence": int((out["runner_confidence_band_v3"] == "LOW").sum()),
        "very_low_confidence": int((out["runner_confidence_band_v3"] == "VERY_LOW").sum()),
        "output": str(OUT_FILE),
    }])

    out.to_csv(OUT_FILE, index=False)
    audit.to_csv(AUDIT_FILE, index=False)

    print("[RUNNER_SCORE_V3_1] COMPLETE")
    print(f"rows={len(out)}")
    print(f"races={out['race_key_join'].nunique()}")
    print(f"wrote={OUT_FILE}")
    print(f"audit={AUDIT_FILE}")
    print(out["runner_band_v3"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()

