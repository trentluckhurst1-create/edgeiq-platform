from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SPEEDMAP = DATA / "edgeiq_tactical_dna_speed_map_v2.csv"
RACESHAPE = DATA / "edgeiq_race_shape_engine_v1.csv"
DNA_V3 = DATA / "edgeiq_tactical_dna_v3.csv"

OUTPUT = DATA / "edgeiq_pace_advantage_v4.csv"
AUDIT = DATA / "edgeiq_pace_advantage_v4_audit.csv"

def clean_key(v):
    if pd.isna(v):
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(v).upper().strip())

def num(v, default=0.0):
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default

def first_col(df, names):
    lower = {c.lower(): c for c in df.columns}
    for n in names:
        if n in df.columns:
            return n
        if n.lower() in lower:
            return lower[n.lower()]
    return None

BASE_MATRIX = {
    "LONE_LEADER": {
        "EXPLOSIVE_LEADER": 8,
        "PRESSURE_LEADER": 6,
        "WEAK_LEADER": 3,
        "STRONG_ONPACE": 4,
        "NEUTRAL_ONPACE": 3,
        "WEAK_ONPACE": 1,
        "EXPLOSIVE_MIDFIELD": 0,
        "TRACKING_MIDFIELD": -1,
        "ONE_PACE_MIDFIELD": -2,
        "POWER_BACKMARKER": -3,
        "RUN_ON_BACKMARKER": -5,
        "WEAK_BACKMARKER": -7,
    },
    "CONTROLLED_TEMPO": {
        "EXPLOSIVE_LEADER": 7,
        "PRESSURE_LEADER": 5,
        "WEAK_LEADER": 2,
        "STRONG_ONPACE": 4,
        "NEUTRAL_ONPACE": 2,
        "WEAK_ONPACE": 0,
        "EXPLOSIVE_MIDFIELD": 1,
        "TRACKING_MIDFIELD": 0,
        "ONE_PACE_MIDFIELD": -2,
        "POWER_BACKMARKER": -1,
        "RUN_ON_BACKMARKER": -3,
        "WEAK_BACKMARKER": -5,
    },
    "SIT_AND_SPRINT": {
        "EXPLOSIVE_LEADER": 5,
        "PRESSURE_LEADER": 3,
        "WEAK_LEADER": 1,
        "STRONG_ONPACE": 3,
        "NEUTRAL_ONPACE": 2,
        "WEAK_ONPACE": 0,
        "EXPLOSIVE_MIDFIELD": 2,
        "TRACKING_MIDFIELD": -1,
        "ONE_PACE_MIDFIELD": -3,
        "POWER_BACKMARKER": -1,
        "RUN_ON_BACKMARKER": -4,
        "WEAK_BACKMARKER": -6,
    },
    "GENUINE_PRESSURE": {
        "EXPLOSIVE_LEADER": 1,
        "PRESSURE_LEADER": 0,
        "WEAK_LEADER": -2,
        "STRONG_ONPACE": 2,
        "NEUTRAL_ONPACE": 1,
        "WEAK_ONPACE": -1,
        "EXPLOSIVE_MIDFIELD": 4,
        "TRACKING_MIDFIELD": 2,
        "ONE_PACE_MIDFIELD": 0,
        "POWER_BACKMARKER": 4,
        "RUN_ON_BACKMARKER": 2,
        "WEAK_BACKMARKER": 0,
    },
    "LEADER_BATTLE": {
        "EXPLOSIVE_LEADER": -1,
        "PRESSURE_LEADER": -3,
        "WEAK_LEADER": -5,
        "STRONG_ONPACE": 0,
        "NEUTRAL_ONPACE": -1,
        "WEAK_ONPACE": -3,
        "EXPLOSIVE_MIDFIELD": 5,
        "TRACKING_MIDFIELD": 3,
        "ONE_PACE_MIDFIELD": 1,
        "POWER_BACKMARKER": 7,
        "RUN_ON_BACKMARKER": 4,
        "WEAK_BACKMARKER": 1,
    },
    "CHAOTIC_SPEED": {
        "EXPLOSIVE_LEADER": -3,
        "PRESSURE_LEADER": -5,
        "WEAK_LEADER": -8,
        "STRONG_ONPACE": -1,
        "NEUTRAL_ONPACE": -3,
        "WEAK_ONPACE": -5,
        "EXPLOSIVE_MIDFIELD": 6,
        "TRACKING_MIDFIELD": 3,
        "ONE_PACE_MIDFIELD": 1,
        "POWER_BACKMARKER": 8,
        "RUN_ON_BACKMARKER": 5,
        "WEAK_BACKMARKER": 1,
    },
}

FALLBACK_BY_POSITION = {
    "LEADER": {
        "LONE_LEADER": 5,
        "CONTROLLED_TEMPO": 4,
        "SIT_AND_SPRINT": 3,
        "GENUINE_PRESSURE": 0,
        "LEADER_BATTLE": -3,
        "CHAOTIC_SPEED": -5,
    },
    "ON_PACE": {
        "LONE_LEADER": 3,
        "CONTROLLED_TEMPO": 2,
        "SIT_AND_SPRINT": 2,
        "GENUINE_PRESSURE": 1,
        "LEADER_BATTLE": -1,
        "CHAOTIC_SPEED": -2,
    },
    "MIDFIELD": {
        "LONE_LEADER": -1,
        "CONTROLLED_TEMPO": 0,
        "SIT_AND_SPRINT": -1,
        "GENUINE_PRESSURE": 2,
        "LEADER_BATTLE": 2,
        "CHAOTIC_SPEED": 2,
    },
    "BACKMARKER": {
        "LONE_LEADER": -5,
        "CONTROLLED_TEMPO": -3,
        "SIT_AND_SPRINT": -4,
        "GENUINE_PRESSURE": 2,
        "LEADER_BATTLE": 4,
        "CHAOTIC_SPEED": 5,
    },
    "UNKNOWN": {
        "LONE_LEADER": 0,
        "CONTROLLED_TEMPO": 0,
        "SIT_AND_SPRINT": 0,
        "GENUINE_PRESSURE": 0,
        "LEADER_BATTLE": 0,
        "CHAOTIC_SPEED": 0,
    },
}

def band(score):
    if score >= 8:
        return "ELITE_ADVANTAGE"
    if score >= 5:
        return "STRONG_ADVANTAGE"
    if score >= 2:
        return "POSITIVE"
    if score > -2:
        return "NEUTRAL"
    if score > -5:
        return "NEGATIVE"
    return "SEVERE_NEGATIVE"

def fit_score(score, confidence):
    base = 50 + score * 6
    if confidence == "HIGH":
        base += 5
    elif confidence == "LOW":
        base -= 5
    elif confidence == "UNKNOWN":
        base -= 10
    return round(max(0, min(100, base)), 1)

def main():
    for p in [SPEEDMAP, RACESHAPE, DNA_V3]:
        if not p.exists():
            raise FileNotFoundError(f"Missing input: {p}")

    sm = pd.read_csv(SPEEDMAP)
    rs = pd.read_csv(RACESHAPE)
    dna = pd.read_csv(DNA_V3)

    sm_race_key = first_col(sm, ["race_key"])
    rs_race_key = first_col(rs, ["race_key"])
    sm_horse_key = first_col(sm, ["horse_key", "horseKey"])
    sm_horse = first_col(sm, ["horse", "horse_name", "horseName", "runner"])
    dna_horse_key = first_col(dna, ["horse_key_join", "horse_key", "horseKey"])

    if sm_race_key is None or rs_race_key is None:
        raise ValueError("race_key required in speed map and race shape")

    if sm_horse_key is None:
        if sm_horse is None:
            raise ValueError("Speed map missing horse key/name")
        sm["horse_key_join"] = sm[sm_horse].apply(clean_key)
    else:
        sm["horse_key_join"] = sm[sm_horse_key].apply(clean_key)

    if dna_horse_key is None:
        raise ValueError("DNA V3 missing horse key")

    dna["horse_key_join"] = dna[dna_horse_key].apply(clean_key)

    dna_keep = [
        "horse_key_join",
        "positional_dna_v3",
        "ability_dna_v3",
        "run_style_quality_v3",
        "dna_power_rating_v3",
        "dna_v3_confidence",
        "sectional_strength_rating",
        "sectional_strength_band",
        "strength_adjusted_early_speed",
        "strength_adjusted_late_speed",
        "strength_adjusted_peak_speed",
        "sectional_archetype",
    ]
    dna_keep = [c for c in dna_keep if c in dna.columns]
    dna_small = dna[dna_keep].drop_duplicates("horse_key_join")

    rs_keep = [
        rs_race_key,
        "race_shape_v1",
        "race_shape_confidence_v1",
        "pace_pressure_v3",
        "pace_pressure_score_v3",
        "field_size_v3",
        "leader_count_v3",
        "onpace_count_v3",
        "expected_leaders_v3",
    ]
    rs_keep = [c for c in rs_keep if c in rs.columns]
    rs_small = rs[rs_keep].drop_duplicates(rs_race_key)

    out = sm.merge(dna_small, on="horse_key_join", how="left")
    out = out.merge(
        rs_small,
        left_on=sm_race_key,
        right_on=rs_race_key,
        how="left",
        suffixes=("", "_race")
    )

    scores = []
    bands = []
    fits = []
    reasons = []
    benefit_scores = []
    penalty_scores = []

    for _, r in out.iterrows():
        shape = str(r.get("race_shape_v1", "")).upper().strip()
        ability = str(r.get("ability_dna_v3", "")).upper().strip()
        position = str(r.get("positional_dna_v3", "UNKNOWN")).upper().strip()
        conf = str(r.get("dna_v3_confidence", "UNKNOWN")).upper().strip()
        power = num(r.get("dna_power_rating_v3"))

        if shape in BASE_MATRIX and ability in BASE_MATRIX[shape]:
            base = BASE_MATRIX[shape][ability]
            source = "ability_dna_matrix"
        else:
            base = FALLBACK_BY_POSITION.get(position, FALLBACK_BY_POSITION["UNKNOWN"]).get(shape, 0)
            source = "position_fallback"

        power_adj = 0
        if power >= 72 and base > 0:
            power_adj = 1
        elif power >= 72 and base < 0:
            power_adj = 1
        elif power < 58 and base > 0:
            power_adj = -1
        elif power < 58 and base < 0:
            power_adj = -1

        score = base + power_adj

        benefit = max(0, score)
        penalty = min(0, score)

        scores.append(score)
        bands.append(band(score))
        fits.append(fit_score(score, conf))
        benefit_scores.append(benefit)
        penalty_scores.append(penalty)

        reasons.append(
            f"{ability or position} in {shape}; base={base}; power={power}; power_adj={power_adj}; source={source}"
        )

    out["pace_advantage_score_v4"] = scores
    out["pace_advantage_band_v4"] = bands
    out["race_shape_fit_score_v1"] = fits
    out["shape_benefit_score_v4"] = benefit_scores
    out["shape_penalty_score_v4"] = penalty_scores
    out["pace_advantage_reason_v4"] = reasons

    out["pace_advantage_engine"] = "PACE_ADVANTAGE_V4"
    out["pace_advantage_input_speedmap"] = SPEEDMAP.name
    out["pace_advantage_input_raceshape"] = RACESHAPE.name
    out["pace_advantage_input_dna_v3"] = DNA_V3.name

    preferred = [
        "race_key",
        "meeting_date",
        "track",
        "race_no",
        sm_horse if sm_horse else "",
        sm_horse_key if sm_horse_key else "",
        "horse_key_join",
        "race_shape_v1",
        "pace_pressure_v3",
        "positional_dna_v3",
        "ability_dna_v3",
        "run_style_quality_v3",
        "dna_power_rating_v3",
        "dna_v3_confidence",
        "pace_advantage_score_v4",
        "pace_advantage_band_v4",
        "race_shape_fit_score_v1",
        "shape_benefit_score_v4",
        "shape_penalty_score_v4",
        "pace_advantage_reason_v4",
        "sectional_strength_rating",
        "sectional_strength_band",
        "race_shape_confidence_v1",
    ]

    preferred = [c for c in preferred if c and c in out.columns]
    remaining = [c for c in out.columns if c not in preferred]
    out = out[preferred + remaining]

    out.to_csv(OUTPUT, index=False)

    audit = pd.DataFrame([{
        "speedmap_rows": len(sm),
        "output_rows": len(out),
        "unique_races": out["race_key"].nunique() if "race_key" in out.columns else "",
        "dna_v3_matched": int(out["ability_dna_v3"].notna().sum()),
        "elite_advantage": int((out["pace_advantage_band_v4"] == "ELITE_ADVANTAGE").sum()),
        "strong_advantage": int((out["pace_advantage_band_v4"] == "STRONG_ADVANTAGE").sum()),
        "positive": int((out["pace_advantage_band_v4"] == "POSITIVE").sum()),
        "neutral": int((out["pace_advantage_band_v4"] == "NEUTRAL").sum()),
        "negative": int((out["pace_advantage_band_v4"] == "NEGATIVE").sum()),
        "severe_negative": int((out["pace_advantage_band_v4"] == "SEVERE_NEGATIVE").sum()),
        "avg_shape_fit": round(float(out["race_shape_fit_score_v1"].mean()), 2),
        "output": str(OUTPUT),
    }])
    audit.to_csv(AUDIT, index=False)

    print("[PACE_ADVANTAGE_V4] COMPLETE")
    print(f"speedmap_rows={len(sm)}")
    print(f"output_rows={len(out)}")
    print(f"dna_v3_matched={int(out['ability_dna_v3'].notna().sum())}")
    print(f"wrote={OUTPUT}")
    print(f"audit={AUDIT}")
    print(out["pace_advantage_band_v4"].value_counts(dropna=False).to_string())

if __name__ == "__main__":
    main()
