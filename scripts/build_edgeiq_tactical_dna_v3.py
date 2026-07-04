from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

DNA_V2 = DATA / "edgeiq_tactical_dna_v2.csv"
SECTIONAL_STRENGTH = DATA / "edgeiq_sectional_strength_v2.csv"

OUTPUT = DATA / "edgeiq_tactical_dna_v3.csv"
AUDIT = DATA / "edgeiq_tactical_dna_v3_audit.csv"

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

def positional_style(row):
    for c in ["run_style_v2", "run_style", "tactical_style", "settling_band", "speed_map_bucket", "dna_style"]:
        if c in row.index:
            v = str(row.get(c, "")).upper().strip()
            if v:
                if "LEADER" in v and "BACK" not in v:
                    return "LEADER"
                if "ON" in v and "PACE" in v:
                    return "ON_PACE"
                if "MID" in v:
                    return "MIDFIELD"
                if "BACK" in v:
                    return "BACKMARKER"

    leader = num(row.get("leader_pct_v2"))
    onpace = num(row.get("on_pace_pct_v2"))
    midfield = num(row.get("midfield_pct_v2"))
    back = num(row.get("backmarker_pct_v2"))

    vals = {
        "LEADER": leader,
        "ON_PACE": onpace,
        "MIDFIELD": midfield,
        "BACKMARKER": back,
    }

    best = max(vals, key=vals.get)
    if vals[best] <= 0:
        return "UNKNOWN"
    return best

def power_rating(style, row):
    early = num(row.get("strength_adjusted_early_speed"))
    mid = num(row.get("strength_adjusted_mid_speed"))
    late = num(row.get("strength_adjusted_late_speed"))
    peak = num(row.get("strength_adjusted_peak_speed"))
    avg = num(row.get("strength_adjusted_avg_speed"))
    sectional = num(row.get("sectional_strength_rating"))

    if style == "LEADER":
        rating = early * 0.35 + peak * 0.30 + avg * 0.20 + sectional * 0.15
    elif style == "ON_PACE":
        rating = early * 0.25 + mid * 0.20 + peak * 0.25 + avg * 0.15 + sectional * 0.15
    elif style == "MIDFIELD":
        rating = mid * 0.25 + late * 0.25 + peak * 0.20 + avg * 0.15 + sectional * 0.15
    elif style == "BACKMARKER":
        rating = late * 0.40 + peak * 0.25 + avg * 0.15 + sectional * 0.20
    else:
        rating = sectional

    return round(max(0, min(100, rating)), 3)

def quality_band(rating):
    if rating >= 72:
        return "ELITE"
    if rating >= 68:
        return "STRONG"
    if rating >= 63:
        return "SOLID"
    if rating >= 58:
        return "NEUTRAL"
    if rating > 0:
        return "WEAK"
    return "UNKNOWN"

def ability_dna(style, rating, row):
    early = num(row.get("strength_adjusted_early_speed"))
    late = num(row.get("strength_adjusted_late_speed"))
    peak = num(row.get("strength_adjusted_peak_speed"))

    if style == "LEADER":
        if rating >= 72 and early >= 70:
            return "EXPLOSIVE_LEADER"
        if rating >= 66:
            return "PRESSURE_LEADER"
        if rating > 0:
            return "WEAK_LEADER"
        return "UNKNOWN_LEADER"

    if style == "ON_PACE":
        if rating >= 70:
            return "STRONG_ONPACE"
        if rating >= 62:
            return "NEUTRAL_ONPACE"
        if rating > 0:
            return "WEAK_ONPACE"
        return "UNKNOWN_ONPACE"

    if style == "MIDFIELD":
        if rating >= 70 and late >= 68:
            return "EXPLOSIVE_MIDFIELD"
        if rating >= 62:
            return "TRACKING_MIDFIELD"
        if rating > 0:
            return "ONE_PACE_MIDFIELD"
        return "UNKNOWN_MIDFIELD"

    if style == "BACKMARKER":
        if rating >= 70 and late >= 68:
            return "POWER_BACKMARKER"
        if rating >= 62:
            return "RUN_ON_BACKMARKER"
        if rating > 0:
            return "WEAK_BACKMARKER"
        return "UNKNOWN_BACKMARKER"

    return "UNKNOWN"

def main():
    for p in [DNA_V2, SECTIONAL_STRENGTH]:
        if not p.exists():
            raise FileNotFoundError(f"Missing input: {p}")

    dna = pd.read_csv(DNA_V2)
    sec = pd.read_csv(SECTIONAL_STRENGTH)

    dna_horse_key = first_col(dna, ["horse_key", "horseKey"])
    dna_horse = first_col(dna, ["horse", "horse_name", "horseName"])

    sec_horse_key = first_col(sec, ["horse_key", "horse_key_join", "horseKey"])
    sec_horse = first_col(sec, ["horse_name", "horse", "horseName"])

    if dna_horse_key is None:
        if dna_horse is None:
            raise ValueError("DNA V2 missing horse key/name")
        dna["horse_key_join"] = dna[dna_horse].apply(clean_key)
    else:
        dna["horse_key_join"] = dna[dna_horse_key].apply(clean_key)

    if sec_horse_key is None:
        if sec_horse is None:
            raise ValueError("Sectional strength missing horse key/name")
        sec["horse_key_join"] = sec[sec_horse].apply(clean_key)
    else:
        sec["horse_key_join"] = sec[sec_horse_key].apply(clean_key)

    sec_keep = [
        "horse_key_join",
        "avg_race_strength",
        "starts_with_strength",
        "strength_adjusted_early_speed",
        "strength_adjusted_mid_speed",
        "strength_adjusted_late_speed",
        "strength_adjusted_peak_speed",
        "strength_adjusted_avg_speed",
        "sectional_strength_rating",
        "sectional_strength_band",
        "sectional_strength_confidence",
        "sectional_archetype",
    ]
    sec_keep = [c for c in sec_keep if c in sec.columns]
    sec_small = sec[sec_keep].drop_duplicates("horse_key_join")

    out = dna.merge(sec_small, on="horse_key_join", how="left")

    styles = []
    ratings = []
    qualities = []
    ability = []

    for _, row in out.iterrows():
        style = positional_style(row)
        rating = power_rating(style, row)
        quality = quality_band(rating)
        archetype = ability_dna(style, rating, row)

        styles.append(style)
        ratings.append(rating)
        qualities.append(quality)
        ability.append(archetype)

    out["positional_dna_v3"] = styles
    out["dna_power_rating_v3"] = ratings
    out["run_style_quality_v3"] = qualities
    out["ability_dna_v3"] = ability

    out["dna_v3_source"] = np.where(
        out["sectional_strength_rating"].notna(),
        "TACTICAL_DNA_V2_PLUS_STRENGTH_SECTIONALS",
        "TACTICAL_DNA_V2_ONLY"
    )

    out["dna_v3_confidence"] = np.where(
        (out["sectional_strength_confidence"] == "HIGH"),
        "HIGH",
        np.where(
            (out["sectional_strength_confidence"] == "MEDIUM"),
            "MEDIUM",
            np.where(out["positional_dna_v3"] != "UNKNOWN", "LOW", "UNKNOWN")
        )
    )

    out["dna_v3_engine"] = "TACTICAL_DNA_V3"
    out["dna_v3_input_dna"] = DNA_V2.name
    out["dna_v3_input_sectional_strength"] = SECTIONAL_STRENGTH.name

    preferred = [
        "horse_key_join",
        dna_horse if dna_horse else "",
        dna_horse_key if dna_horse_key else "",
        "positional_dna_v3",
        "ability_dna_v3",
        "run_style_quality_v3",
        "dna_power_rating_v3",
        "dna_v3_source",
        "dna_v3_confidence",
        "leader_pct_v2",
        "on_pace_pct_v2",
        "midfield_pct_v2",
        "backmarker_pct_v2",
        "dna_source",
        "dna_confidence_v2",
        "avg_race_strength",
        "starts_with_strength",
        "strength_adjusted_early_speed",
        "strength_adjusted_mid_speed",
        "strength_adjusted_late_speed",
        "strength_adjusted_peak_speed",
        "strength_adjusted_avg_speed",
        "sectional_strength_rating",
        "sectional_strength_band",
        "sectional_strength_confidence",
        "sectional_archetype",
    ]

    preferred = [c for c in preferred if c and c in out.columns]
    remaining = [c for c in out.columns if c not in preferred]
    out = out[preferred + remaining]

    out.to_csv(OUTPUT, index=False)

    audit = pd.DataFrame([{
        "dna_v2_rows": len(dna),
        "output_rows": len(out),
        "sectional_strength_rows": len(sec),
        "sectional_strength_matched": int(out["sectional_strength_rating"].notna().sum()),
        "high_confidence": int((out["dna_v3_confidence"] == "HIGH").sum()),
        "medium_confidence": int((out["dna_v3_confidence"] == "MEDIUM").sum()),
        "low_confidence": int((out["dna_v3_confidence"] == "LOW").sum()),
        "unknown_confidence": int((out["dna_v3_confidence"] == "UNKNOWN").sum()),
        "elite_quality": int((out["run_style_quality_v3"] == "ELITE").sum()),
        "strong_quality": int((out["run_style_quality_v3"] == "STRONG").sum()),
        "solid_quality": int((out["run_style_quality_v3"] == "SOLID").sum()),
        "neutral_quality": int((out["run_style_quality_v3"] == "NEUTRAL").sum()),
        "weak_quality": int((out["run_style_quality_v3"] == "WEAK").sum()),
        "unknown_quality": int((out["run_style_quality_v3"] == "UNKNOWN").sum()),
        "output": str(OUTPUT),
    }])
    audit.to_csv(AUDIT, index=False)

    print("[TACTICAL_DNA_V3] COMPLETE")
    print(f"dna_v2_rows={len(dna)}")
    print(f"output_rows={len(out)}")
    print(f"sectional_strength_matched={int(out['sectional_strength_rating'].notna().sum())}")
    print(f"wrote={OUTPUT}")
    print(f"audit={AUDIT}")
    print(out["ability_dna_v3"].value_counts(dropna=False).to_string())

if __name__ == "__main__":
    main()
