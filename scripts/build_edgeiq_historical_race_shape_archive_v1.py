from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RESULTS = DATA / "edgeiq_racingcom_results_warehouse_v1.csv"
DNA = DATA / "edgeiq_tactical_dna_v2.csv"
SECTIONAL_STRENGTH = DATA / "edgeiq_sectional_strength_v2.csv"
RACE_STRENGTH = DATA / "edgeiq_race_strength_v1.csv"

OUTPUT = DATA / "edgeiq_historical_race_shape_archive_v1.csv"
AUDIT = DATA / "edgeiq_historical_race_shape_archive_v1_audit.csv"

def clean_key(v):
    if pd.isna(v):
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(v).upper().strip())

def normalise_race_key(v):
    if pd.isna(v):
        return ""
    s = str(v).upper().strip()
    parts = s.split("|")
    if len(parts) >= 3:
        last = parts[-1].strip()
        if re.fullmatch(r"\d+", last):
            parts[-1] = "R" + last
        return "|".join(parts)
    return s

def num(v, default=np.nan):
    try:
        if pd.isna(v):
            return default
        x = float(str(v).replace("$", "").replace(",", "").strip())
        return x
    except Exception:
        return default

def finish_num(v):
    try:
        s = str(v).upper().strip()
        if s in ["", "SCR", "SCRATCHED", "NAN", "NA"]:
            return np.nan
        x = re.sub(r"[^0-9.]", "", s)
        if x == "":
            return np.nan
        return float(x)
    except Exception:
        return np.nan

def first_col(df, names):
    lower = {c.lower(): c for c in df.columns}
    for n in names:
        if n in df.columns:
            return n
        if n.lower() in lower:
            return lower[n.lower()]
    return None

def profile_style(row):
    leader = num(row.get("leader_pct_v2"), 0)
    onpace = num(row.get("on_pace_pct_v2"), 0)
    midfield = num(row.get("midfield_pct_v2"), 0)
    back = num(row.get("backmarker_pct_v2"), 0)

    values = {
        "LEADER": leader,
        "ON_PACE": onpace,
        "MIDFIELD": midfield,
        "BACKMARKER": back,
    }

    best = max(values, key=values.get)

    if values[best] <= 0:
        return "UNKNOWN"

    return best

def race_shape_from_counts(leader_count, onpace_count, field_size):
    leader_count = num(leader_count, 0)
    onpace_count = num(onpace_count, 0)
    field_size = max(num(field_size, 0), 1)

    pressure = leader_count + (onpace_count * 0.55)
    pressure_ratio = pressure / field_size

    if leader_count <= 1 and pressure_ratio <= 0.20:
        return "LONE_LEADER"

    if leader_count <= 1 and pressure_ratio <= 0.32:
        return "CONTROLLED_TEMPO"

    if leader_count <= 2 and pressure_ratio <= 0.38:
        return "SIT_AND_SPRINT"

    if pressure_ratio <= 0.48:
        return "GENUINE_PRESSURE"

    if leader_count >= 3 and pressure_ratio <= 0.58:
        return "LEADER_BATTLE"

    return "CHAOTIC_SPEED"

def pace_pressure_band(leader_count, onpace_count, field_size):
    leader_count = num(leader_count, 0)
    onpace_count = num(onpace_count, 0)
    field_size = max(num(field_size, 0), 1)

    score = ((leader_count * 1.0) + (onpace_count * 0.55)) / field_size

    if score < 0.18:
        return "VERY_SLOW"
    if score < 0.26:
        return "SLOW"
    if score < 0.34:
        return "MODERATE"
    if score < 0.44:
        return "GENUINE"
    if score < 0.55:
        return "FAST"
    return "EXTREME"

def advantage_score(shape, style):
    matrix = {
        "LONE_LEADER": {
            "LEADER": 6,
            "ON_PACE": 3,
            "MIDFIELD": -1,
            "BACKMARKER": -5,
            "UNKNOWN": 0,
        },
        "CONTROLLED_TEMPO": {
            "LEADER": 5,
            "ON_PACE": 3,
            "MIDFIELD": 0,
            "BACKMARKER": -3,
            "UNKNOWN": 0,
        },
        "SIT_AND_SPRINT": {
            "LEADER": 4,
            "ON_PACE": 2,
            "MIDFIELD": -1,
            "BACKMARKER": -4,
            "UNKNOWN": 0,
        },
        "GENUINE_PRESSURE": {
            "LEADER": -1,
            "ON_PACE": 1,
            "MIDFIELD": 2,
            "BACKMARKER": 2,
            "UNKNOWN": 0,
        },
        "LEADER_BATTLE": {
            "LEADER": -4,
            "ON_PACE": -1,
            "MIDFIELD": 3,
            "BACKMARKER": 5,
            "UNKNOWN": 0,
        },
        "CHAOTIC_SPEED": {
            "LEADER": -6,
            "ON_PACE": -2,
            "MIDFIELD": 3,
            "BACKMARKER": 6,
            "UNKNOWN": 0,
        },
    }

    return matrix.get(shape, {}).get(style, 0)

def shape_fit(score, sectional_strength):
    base = 50 + (num(score, 0) * 6)
    ss = num(sectional_strength, 0)
    if ss > 0:
        base = (base * 0.70) + (ss * 0.30)
    return round(max(0, min(100, base)), 3)

def main():
    for p in [RESULTS, DNA, SECTIONAL_STRENGTH, RACE_STRENGTH]:
        if not p.exists():
            raise FileNotFoundError(f"Missing input: {p}")

    res = pd.read_csv(RESULTS)
    dna = pd.read_csv(DNA)
    sec = pd.read_csv(SECTIONAL_STRENGTH)
    rs = pd.read_csv(RACE_STRENGTH)

    print("[HISTORICAL_SHAPE_ARCHIVE_V1] results columns:")
    print(", ".join(res.columns))

    if "race_key" in res.columns:
        res["race_key_join"] = res["race_key"].apply(normalise_race_key)
    else:
        res["race_key_join"] = (
            res["meeting_date"].astype(str).str.strip()
            + "|"
            + res["track"].astype(str).str.upper().str.strip()
            + "|R"
            + res["race_no"].astype(str).str.replace(".0", "", regex=False).str.strip()
        )

    if "horseKey" in res.columns:
        res["horse_key_join"] = res["horseKey"].apply(clean_key)
    elif "horse_key" in res.columns:
        res["horse_key_join"] = res["horse_key"].apply(clean_key)
    elif "horseName" in res.columns:
        res["horse_key_join"] = res["horseName"].apply(clean_key)
    else:
        raise ValueError("Results missing horse key/name")

    if "horse_key" in dna.columns:
        dna["horse_key_join"] = dna["horse_key"].apply(clean_key)
    elif "horseKey" in dna.columns:
        dna["horse_key_join"] = dna["horseKey"].apply(clean_key)
    elif "horse" in dna.columns:
        dna["horse_key_join"] = dna["horse"].apply(clean_key)
    else:
        raise ValueError("DNA missing horse key/name")

    if "horse_key_join" not in sec.columns:
        if "horse_key" in sec.columns:
            sec["horse_key_join"] = sec["horse_key"].apply(clean_key)
        elif "horse_name" in sec.columns:
            sec["horse_key_join"] = sec["horse_name"].apply(clean_key)
        else:
            raise ValueError("Sectional strength missing horse key/name")
    else:
        sec["horse_key_join"] = sec["horse_key_join"].apply(clean_key)

    rs["race_key_join"] = rs["race_key"].apply(normalise_race_key)

    strength_col = "field_strength_score"
    if strength_col not in rs.columns:
        raise ValueError("Race strength missing field_strength_score")

    finish_col = "finishPosition" if "finishPosition" in res.columns else "finish_position"
    horse_name_col = "horseName" if "horseName" in res.columns else "horse"

    res["finish_position_num"] = res[finish_col].apply(finish_num)
    res["won"] = np.where(res["finish_position_num"] == 1, 1, 0)
    res["placed"] = np.where(res["finish_position_num"].between(1, 3), 1, 0)
    res["is_scratched"] = np.where(res["finish_position_num"].isna(), 1, 0)

    dna_keep = [
        "horse_key_join",
        "leader_pct_v2",
        "on_pace_pct_v2",
        "midfield_pct_v2",
        "backmarker_pct_v2",
        "dna_source",
        "dna_confidence_v2",
    ]
    dna_keep = [c for c in dna_keep if c in dna.columns]
    dna_small = dna[dna_keep].drop_duplicates("horse_key_join")

    sec_keep = [
        "horse_key_join",
        "sectional_strength_rating",
        "sectional_strength_band",
        "sectional_strength_confidence",
        "strength_adjusted_early_speed",
        "strength_adjusted_late_speed",
        "strength_adjusted_peak_speed",
        "strength_adjusted_avg_speed",
    ]
    sec_keep = [c for c in sec_keep if c in sec.columns]
    sec_small = sec[sec_keep].drop_duplicates("horse_key_join")

    rs_small = rs[["race_key_join", strength_col]].copy()
    rs_small[strength_col] = pd.to_numeric(rs_small[strength_col], errors="coerce")
    rs_small = rs_small.drop_duplicates("race_key_join")

    out = res.merge(dna_small, on="horse_key_join", how="left")
    out = out.merge(sec_small, on="horse_key_join", how="left")
    out = out.merge(rs_small, on="race_key_join", how="left")

    out["historical_position_style_v1"] = out.apply(profile_style, axis=1)

    race_counts = (
        out[out["is_scratched"] == 0]
        .groupby("race_key_join")
        .agg(
            field_size=("horse_key_join", "count"),
            leader_count=("historical_position_style_v1", lambda s: int((s == "LEADER").sum())),
            onpace_count=("historical_position_style_v1", lambda s: int((s == "ON_PACE").sum())),
            midfield_count=("historical_position_style_v1", lambda s: int((s == "MIDFIELD").sum())),
            backmarker_count=("historical_position_style_v1", lambda s: int((s == "BACKMARKER").sum())),
            unknown_count=("historical_position_style_v1", lambda s: int((s == "UNKNOWN").sum())),
        )
        .reset_index()
    )

    race_counts["historical_race_shape_v1"] = race_counts.apply(
        lambda r: race_shape_from_counts(r["leader_count"], r["onpace_count"], r["field_size"]),
        axis=1
    )

    race_counts["historical_pace_pressure_v1"] = race_counts.apply(
        lambda r: pace_pressure_band(r["leader_count"], r["onpace_count"], r["field_size"]),
        axis=1
    )

    out = out.merge(race_counts, on="race_key_join", how="left")

    out["historical_pace_advantage_score_v1"] = out.apply(
        lambda r: advantage_score(
            r.get("historical_race_shape_v1", "UNKNOWN"),
            r.get("historical_position_style_v1", "UNKNOWN")
        ),
        axis=1
    )

    out["historical_shape_fit_score_v1"] = out.apply(
        lambda r: shape_fit(
            r.get("historical_pace_advantage_score_v1"),
            r.get("sectional_strength_rating")
        ),
        axis=1
    )

    out["historical_shape_fit_rank_in_race_v1"] = (
        out.groupby("race_key_join")["historical_shape_fit_score_v1"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    out["historical_shape_fit_percentile_v1"] = np.where(
        out["field_size"] <= 1,
        100,
        (
            1
            - ((out["historical_shape_fit_rank_in_race_v1"] - 1) / (out["field_size"] - 1))
        ) * 100
    ).round(1)

    out["historical_shape_archive_engine"] = "HISTORICAL_RACE_SHAPE_ARCHIVE_V1"

    preferred = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "race_key_join",
        horse_name_col,
        "horse_key_join",
        finish_col,
        "finish_position_num",
        "won",
        "placed",
        "is_scratched",
        "sp",
        "barrier",
        "jockey",
        "trainer",
        "distance",
        "raceClass",
        "trackCondition",
        strength_col,
        "historical_position_style_v1",
        "historical_race_shape_v1",
        "historical_pace_pressure_v1",
        "historical_pace_advantage_score_v1",
        "historical_shape_fit_score_v1",
        "historical_shape_fit_rank_in_race_v1",
        "historical_shape_fit_percentile_v1",
        "field_size",
        "leader_count",
        "onpace_count",
        "midfield_count",
        "backmarker_count",
        "unknown_count",
        "leader_pct_v2",
        "on_pace_pct_v2",
        "midfield_pct_v2",
        "backmarker_pct_v2",
        "sectional_strength_rating",
        "sectional_strength_band",
        "sectional_strength_confidence",
        "dna_source",
        "dna_confidence_v2",
    ]

    preferred = [c for c in preferred if c in out.columns]
    remaining = [c for c in out.columns if c not in preferred]
    out = out[preferred + remaining]

    out.to_csv(OUTPUT, index=False)

    audit = pd.DataFrame([{
        "results_rows": len(res),
        "output_rows": len(out),
        "unique_races": out["race_key_join"].nunique(),
        "unique_horses": out["horse_key_join"].nunique(),
        "dna_matched_rows": int(out["dna_source"].notna().sum()) if "dna_source" in out.columns else 0,
        "sectional_strength_matched_rows": int(out["sectional_strength_rating"].notna().sum()) if "sectional_strength_rating" in out.columns else 0,
        "race_strength_matched_rows": int(out[strength_col].notna().sum()),
        "non_scratched_rows": int((out["is_scratched"] == 0).sum()),
        "scratched_rows": int((out["is_scratched"] == 1).sum()),
        "wins": int(out["won"].sum()),
        "places": int(out["placed"].sum()),
        "lone_leader_races": int((race_counts["historical_race_shape_v1"] == "LONE_LEADER").sum()),
        "controlled_tempo_races": int((race_counts["historical_race_shape_v1"] == "CONTROLLED_TEMPO").sum()),
        "sit_and_sprint_races": int((race_counts["historical_race_shape_v1"] == "SIT_AND_SPRINT").sum()),
        "genuine_pressure_races": int((race_counts["historical_race_shape_v1"] == "GENUINE_PRESSURE").sum()),
        "leader_battle_races": int((race_counts["historical_race_shape_v1"] == "LEADER_BATTLE").sum()),
        "chaotic_speed_races": int((race_counts["historical_race_shape_v1"] == "CHAOTIC_SPEED").sum()),
        "output": str(OUTPUT),
    }])

    audit.to_csv(AUDIT, index=False)

    print("[HISTORICAL_RACE_SHAPE_ARCHIVE_V1] COMPLETE")
    print(f"results_rows={len(res)}")
    print(f"output_rows={len(out)}")
    print(f"unique_races={out['race_key_join'].nunique()}")
    print(f"unique_horses={out['horse_key_join'].nunique()}")
    print(f"wrote={OUTPUT}")
    print(f"audit={AUDIT}")
    print(out["historical_race_shape_v1"].value_counts(dropna=False).to_string())

if __name__ == "__main__":
    main()
