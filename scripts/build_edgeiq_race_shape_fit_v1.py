from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "edgeiq_pace_advantage_v4.csv"

OUTPUT = DATA / "edgeiq_race_shape_fit_v1.csv"
AUDIT = DATA / "edgeiq_race_shape_fit_v1_audit.csv"

def num(v, default=0.0):
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default

def conf_score(v):
    v = str(v).upper().strip()
    if v in ["VERY_HIGH"]:
        return 100
    if v in ["HIGH"]:
        return 90
    if v in ["MEDIUM"]:
        return 70
    if v in ["LOW"]:
        return 45
    return 25

def combined_confidence(dna_conf, shape_conf):
    dna = str(dna_conf).upper().strip()
    shape = str(shape_conf).upper().strip()

    if dna == "HIGH" and shape == "HIGH":
        return "VERY_HIGH"
    if dna == "HIGH" and shape in ["MEDIUM", ""]:
        return "HIGH"
    if dna == "MEDIUM" and shape == "HIGH":
        return "HIGH"
    if dna == "MEDIUM" and shape == "MEDIUM":
        return "MEDIUM"
    if dna in ["HIGH", "MEDIUM"] and shape == "LOW":
        return "MEDIUM"
    if dna == "LOW" and shape in ["HIGH", "MEDIUM"]:
        return "LOW"
    if dna == "UNKNOWN":
        return "LOW"
    return "LOW"

def pace_component(score):
    score = num(score)
    return max(0, min(100, 50 + score * 6))

def band(score):
    score = num(score)
    if score >= 85:
        return "ELITE_FIT"
    if score >= 75:
        return "STRONG_FIT"
    if score >= 65:
        return "POSITIVE_FIT"
    if score >= 55:
        return "NEUTRAL_FIT"
    if score >= 45:
        return "NEGATIVE_FIT"
    return "POOR_FIT"

def reason(row, final_score, fit_band, conf):
    ability = str(row.get("ability_dna_v3", "")).strip()
    shape = str(row.get("race_shape_v1", "")).strip()
    adv_band = str(row.get("pace_advantage_band_v4", "")).strip()
    adv_score = num(row.get("pace_advantage_score_v4"))
    power = num(row.get("dna_power_rating_v3"))
    sectional = num(row.get("sectional_strength_rating"))

    parts = []

    if ability and shape:
        parts.append(f"{ability} mapped against {shape}")

    if adv_score >= 8:
        parts.append("elite pace/shape advantage")
    elif adv_score >= 5:
        parts.append("strong pace/shape advantage")
    elif adv_score >= 2:
        parts.append("positive pace/shape setup")
    elif adv_score <= -5:
        parts.append("severe shape disadvantage")
    elif adv_score <= -2:
        parts.append("negative shape setup")
    else:
        parts.append("neutral shape setup")

    if power >= 72:
        parts.append("elite DNA power")
    elif power >= 68:
        parts.append("strong DNA power")
    elif power >= 63:
        parts.append("solid DNA power")
    elif power > 0:
        parts.append("limited DNA power")
    else:
        parts.append("no DNA power evidence")

    if sectional >= 73:
        parts.append("elite sectional strength")
    elif sectional >= 70:
        parts.append("strong sectional strength")
    elif sectional >= 66:
        parts.append("above-average sectional strength")
    elif sectional > 0:
        parts.append("modest sectional strength")
    else:
        parts.append("no sectional strength evidence")

    parts.append(f"fit={fit_band}")
    parts.append(f"confidence={conf}")

    return "; ".join(parts)

def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing input: {INPUT}")

    df = pd.read_csv(INPUT)

    required = [
        "race_key",
        "pace_advantage_score_v4",
        "dna_power_rating_v3",
        "sectional_strength_rating",
        "dna_v3_confidence",
        "race_shape_confidence_v1",
    ]

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    out = df.copy()

    out["shape_fit_confidence_v1"] = out.apply(
        lambda r: combined_confidence(r.get("dna_v3_confidence"), r.get("race_shape_confidence_v1")),
        axis=1
    )

    out["shape_fit_pace_component_v1"] = out["pace_advantage_score_v4"].apply(pace_component)
    out["shape_fit_power_component_v1"] = pd.to_numeric(out["dna_power_rating_v3"], errors="coerce").fillna(0).clip(0, 100)
    out["shape_fit_sectional_component_v1"] = pd.to_numeric(out["sectional_strength_rating"], errors="coerce").fillna(0).clip(0, 100)
    out["shape_fit_confidence_component_v1"] = out["shape_fit_confidence_v1"].apply(conf_score)

    out["race_shape_fit_score_v1"] = (
        out["shape_fit_pace_component_v1"] * 0.40
        + out["shape_fit_power_component_v1"] * 0.30
        + out["shape_fit_sectional_component_v1"] * 0.20
        + out["shape_fit_confidence_component_v1"] * 0.10
    ).round(3)

    out["race_shape_fit_band_v1"] = out["race_shape_fit_score_v1"].apply(band)

    out["shape_fit_rank_in_race"] = (
        out.groupby("race_key")["race_shape_fit_score_v1"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    out["shape_fit_field_size"] = out.groupby("race_key")["race_key"].transform("count").astype(int)

    out["shape_fit_percentile_in_race"] = np.where(
        out["shape_fit_field_size"] <= 1,
        100.0,
        (
            1
            - ((out["shape_fit_rank_in_race"] - 1) / (out["shape_fit_field_size"] - 1))
        ) * 100
    ).round(1)

    out["shape_fit_reason_v1"] = out.apply(
        lambda r: reason(
            r,
            r.get("race_shape_fit_score_v1"),
            r.get("race_shape_fit_band_v1"),
            r.get("shape_fit_confidence_v1"),
        ),
        axis=1
    )

    out["race_shape_fit_engine"] = "RACE_SHAPE_FIT_V1"
    out["race_shape_fit_input"] = INPUT.name

    preferred = [
        "race_key",
        "meeting_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "horse_key_join",
        "race_shape_v1",
        "pace_pressure_v3",
        "positional_dna_v3",
        "ability_dna_v3",
        "run_style_quality_v3",
        "dna_power_rating_v3",
        "sectional_strength_rating",
        "sectional_strength_band",
        "pace_advantage_score_v4",
        "pace_advantage_band_v4",
        "race_shape_fit_score_v1",
        "race_shape_fit_band_v1",
        "shape_fit_rank_in_race",
        "shape_fit_field_size",
        "shape_fit_percentile_in_race",
        "shape_fit_confidence_v1",
        "shape_fit_reason_v1",
        "dna_v3_confidence",
        "race_shape_confidence_v1",
    ]

    preferred = [c for c in preferred if c in out.columns]
    remaining = [c for c in out.columns if c not in preferred]
    out = out[preferred + remaining]

    out.to_csv(OUTPUT, index=False)

    audit = pd.DataFrame([{
        "input_rows": len(df),
        "output_rows": len(out),
        "unique_races": out["race_key"].nunique(),
        "avg_shape_fit_score": round(float(out["race_shape_fit_score_v1"].mean()), 3),
        "elite_fit": int((out["race_shape_fit_band_v1"] == "ELITE_FIT").sum()),
        "strong_fit": int((out["race_shape_fit_band_v1"] == "STRONG_FIT").sum()),
        "positive_fit": int((out["race_shape_fit_band_v1"] == "POSITIVE_FIT").sum()),
        "neutral_fit": int((out["race_shape_fit_band_v1"] == "NEUTRAL_FIT").sum()),
        "negative_fit": int((out["race_shape_fit_band_v1"] == "NEGATIVE_FIT").sum()),
        "poor_fit": int((out["race_shape_fit_band_v1"] == "POOR_FIT").sum()),
        "very_high_confidence": int((out["shape_fit_confidence_v1"] == "VERY_HIGH").sum()),
        "high_confidence": int((out["shape_fit_confidence_v1"] == "HIGH").sum()),
        "medium_confidence": int((out["shape_fit_confidence_v1"] == "MEDIUM").sum()),
        "low_confidence": int((out["shape_fit_confidence_v1"] == "LOW").sum()),
        "output": str(OUTPUT),
    }])

    audit.to_csv(AUDIT, index=False)

    print("[RACE_SHAPE_FIT_V1] COMPLETE")
    print(f"input_rows={len(df)}")
    print(f"output_rows={len(out)}")
    print(f"unique_races={out['race_key'].nunique()}")
    print(f"wrote={OUTPUT}")
    print(f"audit={AUDIT}")
    print(out["race_shape_fit_band_v1"].value_counts(dropna=False).to_string())

if __name__ == "__main__":
    main()

