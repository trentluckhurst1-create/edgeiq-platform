from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SPEEDMAP = DATA / "edgeiq_tactical_dna_speed_map_v2.csv"
RACESHAPE = DATA / "edgeiq_race_shape_engine_v1.csv"
SECTIONALS = DATA / "edgeiq_sectional_profiles_v2.csv"

OUTPUT = DATA / "edgeiq_pace_advantage_v3.csv"
AUDIT = DATA / "edgeiq_pace_advantage_v3_audit.csv"

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

def dna_style(row):
    for c in ["speed_map_bucket", "settling_band", "run_style", "tactical_dna", "dna_style", "pace_profile"]:
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

MATRIX = {
    "LONE_LEADER": {
        "LEADER": 5,
        "ON_PACE": 3,
        "MIDFIELD": -1,
        "BACKMARKER": -5,
        "UNKNOWN": 0,
    },
    "CONTROLLED_TEMPO": {
        "LEADER": 4,
        "ON_PACE": 2,
        "MIDFIELD": 0,
        "BACKMARKER": -3,
        "UNKNOWN": 0,
    },
    "SIT_AND_SPRINT": {
        "LEADER": 3,
        "ON_PACE": 2,
        "MIDFIELD": -1,
        "BACKMARKER": -4,
        "UNKNOWN": 0,
    },
    "GENUINE_PRESSURE": {
        "LEADER": 0,
        "ON_PACE": 1,
        "MIDFIELD": 2,
        "BACKMARKER": 2,
        "UNKNOWN": 0,
    },
    "LEADER_BATTLE": {
        "LEADER": -3,
        "ON_PACE": -1,
        "MIDFIELD": 2,
        "BACKMARKER": 4,
        "UNKNOWN": 0,
    },
    "CHAOTIC_SPEED": {
        "LEADER": -5,
        "ON_PACE": -2,
        "MIDFIELD": 2,
        "BACKMARKER": 5,
        "UNKNOWN": 0,
    },
}

def sectional_bonus(style, shape, row):
    early = num(row.get("avg_early_speed"))
    late = num(row.get("avg_late_speed"))
    peak = num(row.get("avg_peak_speed"))
    avg = num(row.get("avg_speed"))

    bonus = 0
    reasons = []

    if style == "LEADER" and shape in ["LONE_LEADER", "CONTROLLED_TEMPO", "SIT_AND_SPRINT"]:
        if early >= 90 or peak >= 90:
            bonus += 2
            reasons.append("elite early/peak speed suits control")
        elif early >= 80 or peak >= 80:
            bonus += 1
            reasons.append("solid early/peak speed suits control")

    if style in ["MIDFIELD", "BACKMARKER"] and shape in ["LEADER_BATTLE", "CHAOTIC_SPEED", "GENUINE_PRESSURE"]:
        if late >= 90:
            bonus += 2
            reasons.append("elite late speed suits pressure")
        elif late >= 80:
            bonus += 1
            reasons.append("solid late speed suits pressure")

    if style == "BACKMARKER" and shape in ["LONE_LEADER", "SIT_AND_SPRINT"]:
        if late < 80:
            bonus -= 1
            reasons.append("lacks late-speed edge for tempo disadvantage")

    if avg >= 90:
        bonus += 1
        reasons.append("elite overall sectional profile")

    return bonus, reasons

def band(score):
    if score >= 6:
        return "ELITE_ADVANTAGE"
    if score >= 4:
        return "STRONG_ADVANTAGE"
    if score >= 2:
        return "POSITIVE"
    if score > -2:
        return "NEUTRAL"
    if score > -5:
        return "NEGATIVE"
    return "SEVERE_NEGATIVE"

def main():
    for p in [SPEEDMAP, RACESHAPE]:
        if not p.exists():
            raise FileNotFoundError(f"Missing required input: {p}")

    sm = pd.read_csv(SPEEDMAP)
    rs = pd.read_csv(RACESHAPE)

    sec = pd.read_csv(SECTIONALS) if SECTIONALS.exists() else pd.DataFrame()

    sm_race_key = first_col(sm, ["race_key"])
    rs_race_key = first_col(rs, ["race_key"])

    if sm_race_key is None or rs_race_key is None:
        raise ValueError("race_key is required in speed map and race shape files")

    horse_col = first_col(sm, ["horse", "horseName", "horse_name", "runner", "runner_name"])
    horse_key_col = first_col(sm, ["horse_key", "horseKey"])

    if horse_col is None:
        raise ValueError("Could not find horse column in speed map file")

    if horse_key_col is None:
        sm["horse_key"] = sm[horse_col].apply(clean_key)
        horse_key_col = "horse_key"

    sm["horse_key_join"] = sm[horse_key_col].apply(clean_key)

    if not sec.empty:
        sec_horse_key = first_col(sec, ["horse_key", "horseKey"])
        sec_horse = first_col(sec, ["horse", "horseName", "horse_name"])

        if sec_horse_key is None:
            if sec_horse is not None:
                sec["horse_key_join"] = sec[sec_horse].apply(clean_key)
            else:
                sec["horse_key_join"] = ""
        else:
            sec["horse_key_join"] = sec[sec_horse_key].apply(clean_key)

        keep_sec = [
            "horse_key_join",
            "avg_early_speed",
            "avg_mid_speed",
            "avg_late_speed",
            "avg_peak_speed",
            "avg_speed",
            "sectional_archetype",
        ]
        keep_sec = [c for c in keep_sec if c in sec.columns]
        sec = sec[keep_sec].drop_duplicates("horse_key_join")

        joined = sm.merge(sec, on="horse_key_join", how="left")
    else:
        joined = sm.copy()

    rs_keep = [
        rs_race_key,
        "race_shape_v1",
        "race_shape_confidence_v1",
        "pace_pressure_v3",
        "pace_pressure_score_v3",
    ]
    rs_keep = [c for c in rs_keep if c in rs.columns]
    rs_small = rs[rs_keep].drop_duplicates(rs_race_key)

    out = joined.merge(
        rs_small,
        left_on=sm_race_key,
        right_on=rs_race_key,
        how="left",
        suffixes=("", "_race_shape")
    )

    rows = []
    for _, r in out.iterrows():
        style = dna_style(r)
        shape = str(r.get("race_shape_v1", "")).upper().strip()
        base = MATRIX.get(shape, {}).get(style, 0)

        bonus, bonus_reasons = sectional_bonus(style, shape, r)
        score = base + bonus

        reasons = [
            f"{style} in {shape}",
            f"base={base}",
        ]

        if bonus:
            reasons.append(f"sectional_bonus={bonus}")
        reasons.extend(bonus_reasons)

        rows.append({
            "dna_style_v3": style,
            "pace_advantage_score_v3": score,
            "pace_advantage_band_v3": band(score),
            "pace_advantage_reason_v3": "; ".join(reasons),
        })

    calc = pd.DataFrame(rows)
    out = pd.concat([out.reset_index(drop=True), calc], axis=1)

    out["pace_advantage_engine"] = "PACE_ADVANTAGE_V3"
    out["pace_advantage_input_speedmap"] = SPEEDMAP.name
    out["pace_advantage_input_raceshape"] = RACESHAPE.name
    out["pace_advantage_input_sectionals"] = SECTIONALS.name if SECTIONALS.exists() else ""

    preferred = [
        "race_key",
        "meeting_date",
        "track",
        "race_no",
        horse_col,
        horse_key_col,
        "dna_style_v3",
        "race_shape_v1",
        "pace_pressure_v3",
        "pace_advantage_score_v3",
        "pace_advantage_band_v3",
        "pace_advantage_reason_v3",
        "avg_early_speed",
        "avg_mid_speed",
        "avg_late_speed",
        "avg_peak_speed",
        "avg_speed",
        "sectional_archetype",
        "dna_source",
        "dna_source_v2",
        "dna_confidence_v2",
        "race_shape_confidence_v1",
    ]

    preferred = [c for c in preferred if c in out.columns]
    remaining = [c for c in out.columns if c not in preferred]
    out = out[preferred + remaining]

    out.to_csv(OUTPUT, index=False)

    audit = pd.DataFrame([{
        "input_speedmap_rows": len(sm),
        "output_rows": len(out),
        "unique_races": out["race_key"].nunique() if "race_key" in out.columns else "",
        "sectional_profiles_loaded": len(sec) if not sec.empty else 0,
        "sectional_matched": int(out["avg_speed"].notna().sum()) if "avg_speed" in out.columns else 0,
        "elite_advantage": int((out["pace_advantage_band_v3"] == "ELITE_ADVANTAGE").sum()),
        "strong_advantage": int((out["pace_advantage_band_v3"] == "STRONG_ADVANTAGE").sum()),
        "positive": int((out["pace_advantage_band_v3"] == "POSITIVE").sum()),
        "neutral": int((out["pace_advantage_band_v3"] == "NEUTRAL").sum()),
        "negative": int((out["pace_advantage_band_v3"] == "NEGATIVE").sum()),
        "severe_negative": int((out["pace_advantage_band_v3"] == "SEVERE_NEGATIVE").sum()),
        "speedmap_input": str(SPEEDMAP),
        "raceshape_input": str(RACESHAPE),
        "sectionals_input": str(SECTIONALS),
        "output": str(OUTPUT),
    }])

    audit.to_csv(AUDIT, index=False)

    print("[PACE_ADVANTAGE_V3] COMPLETE")
    print(f"speedmap_rows={len(sm)}")
    print(f"output_rows={len(out)}")
    print(f"wrote={OUTPUT}")
    print(f"audit={AUDIT}")
    print(out["pace_advantage_band_v3"].value_counts(dropna=False).to_string())

if __name__ == "__main__":
    main()
