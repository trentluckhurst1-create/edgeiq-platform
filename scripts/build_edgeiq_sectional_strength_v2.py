from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PROFILES = DATA / "edgeiq_sectional_profiles_v2.csv"
RACE_STRENGTH = DATA / "edgeiq_race_strength_v1.csv"
RESULTS = DATA / "edgeiq_racingcom_results_warehouse_v1.csv"

OUTPUT = DATA / "edgeiq_sectional_strength_v2.csv"
AUDIT = DATA / "edgeiq_sectional_strength_v2_audit.csv"

STRENGTH_COL = "field_strength_score"

def clean_key(v):
    if pd.isna(v):
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(v).upper().strip())

def normalize_race_key(v):
    if pd.isna(v):
        return ""
    s = str(v).strip().upper()
    parts = s.split("|")
    if len(parts) < 3:
        return s
    last = parts[-1].strip()
    if re.fullmatch(r"\d+", last):
        parts[-1] = "R" + last
    elif re.fullmatch(r"R\d+", last):
        parts[-1] = last
    return "|".join(parts)

def num(v, default=np.nan):
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

def clip_speed(v):
    if pd.isna(v):
        return np.nan
    return round(max(0, min(100, float(v))), 3)

def band(v):
    v = num(v, 0)
    if v >= 73:
        return "ELITE"
    if v >= 70:
        return "STRONG"
    if v >= 66:
        return "ABOVE_AVERAGE"
    if v >= 62:
        return "AVERAGE"
    if v >= 58:
        return "BELOW_AVERAGE"
    return "POOR"

def main():
    for p in [PROFILES, RACE_STRENGTH, RESULTS]:
        if not p.exists():
            raise FileNotFoundError(f"Missing input: {p}")

    prof = pd.read_csv(PROFILES)
    rs = pd.read_csv(RACE_STRENGTH)
    res = pd.read_csv(RESULTS)

    if STRENGTH_COL not in rs.columns:
        raise ValueError(f"Missing required race strength column: {STRENGTH_COL}")

    prof_horse_key = first_col(prof, ["horse_key", "horseKey"])
    prof_horse = first_col(prof, ["horse_name", "horse", "horseName"])

    if prof_horse_key is None:
        if prof_horse is None:
            raise ValueError("Profiles missing horse key/name")
        prof["horse_key_join"] = prof[prof_horse].apply(clean_key)
    else:
        prof["horse_key_join"] = prof[prof_horse_key].apply(clean_key)

    res_horse_key = first_col(res, ["horseKey", "horse_key"])
    res_horse = first_col(res, ["horseName", "horse_name", "horse"])

    if res_horse_key is None:
        if res_horse is None:
            raise ValueError("Results missing horse key/name")
        res["horse_key_join"] = res[res_horse].apply(clean_key)
    else:
        res["horse_key_join"] = res[res_horse_key].apply(clean_key)

    rs_race_key = first_col(rs, ["race_key"])
    res_race_key = first_col(res, ["race_key"])

    if rs_race_key is None or res_race_key is None:
        raise ValueError("Both race strength and results must contain race_key")

    rs["race_key_join"] = rs[rs_race_key].apply(normalize_race_key)
    res["race_key_join"] = res[res_race_key].apply(normalize_race_key)

    rs_small = rs[["race_key_join", STRENGTH_COL]].copy()
    rs_small[STRENGTH_COL] = pd.to_numeric(rs_small[STRENGTH_COL], errors="coerce")
    rs_small = rs_small.dropna(subset=[STRENGTH_COL]).drop_duplicates("race_key_join")

    global_strength = float(rs_small[STRENGTH_COL].mean())

    res_strength = res[["horse_key_join", "race_key_join"]].merge(
        rs_small,
        on="race_key_join",
        how="left"
    )

    matched_result_rows = int(res_strength[STRENGTH_COL].notna().sum())

    horse_strength = (
        res_strength
        .dropna(subset=[STRENGTH_COL])
        .groupby("horse_key_join")
        .agg(
            avg_race_strength=(STRENGTH_COL, "mean"),
            starts_with_strength=(STRENGTH_COL, "count"),
            max_race_strength=(STRENGTH_COL, "max"),
            min_race_strength=(STRENGTH_COL, "min"),
        )
        .reset_index()
    )

    out = prof.merge(horse_strength, on="horse_key_join", how="left")

    out["avg_race_strength"] = out["avg_race_strength"].fillna(global_strength)
    out["starts_with_strength"] = out["starts_with_strength"].fillna(0).astype(int)

    out["strength_factor_raw_v2"] = out["avg_race_strength"] / global_strength
    out["strength_factor_capped_v2"] = out["strength_factor_raw_v2"].clip(lower=0.85, upper=1.15)

    speed_cols = {
        "avg_early_speed": "strength_adjusted_early_speed",
        "avg_mid_speed": "strength_adjusted_mid_speed",
        "avg_late_speed": "strength_adjusted_late_speed",
        "avg_peak_speed": "strength_adjusted_peak_speed",
        "avg_speed": "strength_adjusted_avg_speed",
    }

    for raw, adj in speed_cols.items():
        if raw in out.columns:
            out[raw] = pd.to_numeric(out[raw], errors="coerce")
            out[adj] = (out[raw] * out["strength_factor_capped_v2"]).apply(clip_speed)
        else:
            out[adj] = np.nan

    out["sectional_strength_rating"] = (
        out["strength_adjusted_peak_speed"].fillna(0) * 0.30
        + out["strength_adjusted_late_speed"].fillna(0) * 0.30
        + out["strength_adjusted_avg_speed"].fillna(0) * 0.25
        + out["strength_adjusted_early_speed"].fillna(0) * 0.15
    )

    valid_parts = (
        out[[
            "strength_adjusted_peak_speed",
            "strength_adjusted_late_speed",
            "strength_adjusted_avg_speed",
            "strength_adjusted_early_speed",
        ]]
        .notna()
        .sum(axis=1)
    )

    out.loc[valid_parts == 0, "sectional_strength_rating"] = np.nan
    out["sectional_strength_rating"] = out["sectional_strength_rating"].apply(clip_speed)

    out["sectional_strength_band"] = out["sectional_strength_rating"].apply(band)

    out["sectional_strength_confidence"] = np.where(
        out["starts_with_strength"] >= 5,
        "HIGH",
        np.where(out["starts_with_strength"] >= 2, "MEDIUM", "LOW")
    )

    out["sectional_strength_engine"] = "SECTIONAL_STRENGTH_V2"
    out["sectional_strength_global_avg"] = round(global_strength, 3)
    out["sectional_strength_input_profiles"] = PROFILES.name
    out["sectional_strength_input_race_strength"] = RACE_STRENGTH.name
    out["sectional_strength_input_results"] = RESULTS.name

    preferred = [
        "horse_key_join",
        "horse_name",
        "horse_key",
        "avg_race_strength",
        "starts_with_strength",
        "max_race_strength",
        "min_race_strength",
        "strength_factor_raw_v2",
        "strength_factor_capped_v2",
        "avg_early_speed",
        "avg_mid_speed",
        "avg_late_speed",
        "avg_peak_speed",
        "avg_speed",
        "strength_adjusted_early_speed",
        "strength_adjusted_mid_speed",
        "strength_adjusted_late_speed",
        "strength_adjusted_peak_speed",
        "strength_adjusted_avg_speed",
        "sectional_strength_rating",
        "sectional_strength_band",
        "sectional_strength_confidence",
        "sectional_archetype",
        "profile_depth_status",
        "sectional_evidence_type",
    ]

    preferred = [c for c in preferred if c in out.columns]
    remaining = [c for c in out.columns if c not in preferred]
    out = out[preferred + remaining]

    out.to_csv(OUTPUT, index=False)

    audit = pd.DataFrame([{
        "profile_rows": len(prof),
        "output_rows": len(out),
        "race_strength_rows": len(rs),
        "results_rows": len(res),
        "global_avg_strength": round(global_strength, 3),
        "matched_result_rows_to_strength": matched_result_rows,
        "horses_with_strength": int((out["starts_with_strength"] > 0).sum()),
        "horses_without_strength": int((out["starts_with_strength"] == 0).sum()),
        "elite": int((out["sectional_strength_band"] == "ELITE").sum()),
        "strong": int((out["sectional_strength_band"] == "STRONG").sum()),
        "above_average": int((out["sectional_strength_band"] == "ABOVE_AVERAGE").sum()),
        "average": int((out["sectional_strength_band"] == "AVERAGE").sum()),
        "below_average": int((out["sectional_strength_band"] == "BELOW_AVERAGE").sum()),
        "poor": int((out["sectional_strength_band"] == "POOR").sum()),
        "high_confidence": int((out["sectional_strength_confidence"] == "HIGH").sum()),
        "medium_confidence": int((out["sectional_strength_confidence"] == "MEDIUM").sum()),
        "low_confidence": int((out["sectional_strength_confidence"] == "LOW").sum()),
        "strength_column_used": STRENGTH_COL,
        "output": str(OUTPUT),
    }])

    audit.to_csv(AUDIT, index=False)

    print("[SECTIONAL_STRENGTH_V2] COMPLETE")
    print(f"profile_rows={len(prof)}")
    print(f"output_rows={len(out)}")
    print(f"global_avg_strength={round(global_strength, 3)}")
    print(f"matched_result_rows_to_strength={matched_result_rows}")
    print(f"horses_with_strength={int((out['starts_with_strength'] > 0).sum())}")
    print(f"wrote={OUTPUT}")
    print(f"audit={AUDIT}")
    print(out["sectional_strength_band"].value_counts(dropna=False).to_string())

if __name__ == "__main__":
    main()

