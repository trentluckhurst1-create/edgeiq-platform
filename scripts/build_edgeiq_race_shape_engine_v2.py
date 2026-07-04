from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path.cwd()
DATA = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"

SRC = DATA / "live_speed_map_v3.csv"

OUT = DATA / "edgeiq_race_shape_engine_v2.csv"
DIAG = DATA / "edgeiq_race_shape_engine_v2_diagnostics.csv"

def safe(v):
    if pd.isna(v):
        return ""
    return str(v).strip()

def num(v, default=0):
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default

def norm_style(v):
    s = safe(v).upper()
    if "LEAD" in s:
        return "LEADER"
    if "ON" in s or "FORWARD" in s or "HANDY" in s:
        return "ON_PACE"
    if "MID" in s:
        return "MIDFIELD"
    if "BACK" in s or "CLOS" in s:
        return "BACKMARKER"
    if "FIRST" in s:
        return "UNKNOWN"
    return s or "UNKNOWN"

df = pd.read_csv(SRC, low_memory=False)
df.columns = [c.strip() for c in df.columns]

df["style_norm"] = df.get("map_style", "").apply(norm_style)
df["sectional_profile_norm"] = df.get("sectional_profile", "").astype(str).str.upper().str.strip()
df["run_style_cluster_norm"] = df.get("run_style_cluster", "").astype(str).str.upper().str.strip()

rows = []

for (race_date, track, race_no), grp in df.groupby(["race_date", "track", "race_no"], dropna=False):

    runners = len(grp)

    leaders = int((grp["style_norm"] == "LEADER").sum())
    onpace = int(grp["style_norm"].isin(["LEADER", "ON_PACE"]).sum())
    midfield = int((grp["style_norm"] == "MIDFIELD").sum())
    backmarkers = int((grp["style_norm"] == "BACKMARKER").sum())
    unknown = int((grp["style_norm"] == "UNKNOWN").sum())

    closers = int(
        grp["sectional_profile_norm"].str.contains("CLOSER", na=False).sum()
        + grp["run_style_cluster_norm"].str.contains("CLOSER", na=False).sum()
    )

    sustainers = int(
        grp["sectional_profile_norm"].str.contains("SUSTAIN", na=False).sum()
        + grp["run_style_cluster_norm"].str.contains("SUSTAIN", na=False).sum()
    )

    burst = int(
        grp["run_style_cluster_norm"].str.contains("BURST", na=False).sum()
        + grp["sectional_profile_norm"].str.contains("BURST", na=False).sum()
    )

    avg_fatigue = pd.to_numeric(grp.get("fatigue_risk_index"), errors="coerce").mean()
    avg_sustain = pd.to_numeric(grp.get("sustain_index"), errors="coerce").mean()
    avg_late = pd.to_numeric(grp.get("late_power_index"), errors="coerce").mean()

    avg_fatigue = 0 if pd.isna(avg_fatigue) else avg_fatigue
    avg_sustain = 0 if pd.isna(avg_sustain) else avg_sustain
    avg_late = 0 if pd.isna(avg_late) else avg_late

    leader_conflict = max(0, leaders - 1)

    pace_pressure_score = (
        leaders * 4.0
        + onpace * 2.2
        + leader_conflict * 5.0
        + burst * 0.8
        - backmarkers * 0.6
        - unknown * 0.2
    )

    collapse_risk_score = (
        pace_pressure_score * 0.75
        + avg_fatigue * 0.35
        - avg_sustain * 0.12
    )

    closer_setup_score = (
        collapse_risk_score * 0.65
        + closers * 1.6
        + avg_late * 0.08
    )

    leader_bias_score = (
        max(0, 8 - pace_pressure_score) * 1.5
        + leaders * 1.2
        - closers * 0.8
    )

    if pace_pressure_score >= 18 or collapse_risk_score >= 18:
        race_shape = "CHAOTIC_PACE"
    elif pace_pressure_score >= 13:
        race_shape = "HOT_TEMPO"
    elif pace_pressure_score >= 8:
        race_shape = "FAST_TEMPO"
    elif pace_pressure_score <= 3:
        race_shape = "SLOW_TEMPO"
    else:
        race_shape = "NEUTRAL"

    if closer_setup_score >= 18:
        race_shape_bias = "CLOSER_ADVANTAGE"
    elif leader_bias_score >= 10:
        race_shape_bias = "LEADER_ADVANTAGE"
    else:
        race_shape_bias = "BALANCED"

    for _, r in grp.iterrows():
        horse = safe(r.get("horse"))
        style = safe(r.get("style_norm"))
        sectional_profile = safe(r.get("sectional_profile")).upper()
        run_cluster = safe(r.get("run_style_cluster")).upper()
        late = num(r.get("late_power_index"))
        sustain = num(r.get("sustain_index"))
        fatigue = num(r.get("fatigue_risk_index"))
        weapon = num(r.get("sectional_weapon_score"))

        tempo_fit = "NEUTRAL"
        tempo_edge_score = 50.0

        if race_shape in ["HOT_TEMPO", "CHAOTIC_PACE"]:
            if "CLOSER" in sectional_profile or "CLOSER" in run_cluster:
                tempo_fit = "ADVANTAGED"
                tempo_edge_score += 18
            if sustain >= 75:
                tempo_edge_score += 10
            if fatigue >= 60:
                tempo_fit = "DISADVANTAGED"
                tempo_edge_score -= 20
            if style in ["LEADER", "ON_PACE"] and leaders >= 2:
                tempo_fit = "DISADVANTAGED"
                tempo_edge_score -= 15

        elif race_shape == "FAST_TEMPO":
            if sustain >= 75 or late >= 75:
                tempo_fit = "ADVANTAGED"
                tempo_edge_score += 12
            if fatigue >= 65:
                tempo_fit = "DISADVANTAGED"
                tempo_edge_score -= 15

        elif race_shape == "SLOW_TEMPO":
            if style in ["LEADER", "ON_PACE"]:
                tempo_fit = "ADVANTAGED"
                tempo_edge_score += 12
            if "CLOSER" in sectional_profile or "CLOSER" in run_cluster:
                tempo_fit = "DISADVANTAGED"
                tempo_edge_score -= 12

        tempo_edge_score += (weapon - 50) * 0.10
        tempo_edge_score = round(max(0, min(100, tempo_edge_score)), 2)

        if tempo_edge_score >= 70:
            tempo_edge_grade = "STRONG"
        elif tempo_edge_score >= 58:
            tempo_edge_grade = "POSITIVE"
        elif tempo_edge_score <= 38:
            tempo_edge_grade = "NEGATIVE"
        else:
            tempo_edge_grade = "NEUTRAL"

        rows.append({
            "race_date": race_date,
            "track": track,
            "race_no": race_no,
            "horse": horse,
            "horse_key": r.get("horse_key", ""),
            "map_style": r.get("map_style", ""),
            "speed_map_bucket": r.get("speed_map_bucket", ""),
            "projected_race_shape": race_shape,
            "race_shape_bias": race_shape_bias,
            "pace_pressure_score": round(pace_pressure_score, 2),
            "collapse_risk_score": round(collapse_risk_score, 2),
            "closer_setup_score": round(closer_setup_score, 2),
            "leader_bias_score": round(leader_bias_score, 2),
            "leaders": leaders,
            "onpace_runners": onpace,
            "midfield_runners": midfield,
            "backmarkers": backmarkers,
            "closers": closers,
            "sustainers": sustainers,
            "burst_runners": burst,
            "tempo_fit_v2": tempo_fit,
            "tempo_edge_score_v2": tempo_edge_score,
            "tempo_edge_grade_v2": tempo_edge_grade,
            "sectional_profile": r.get("sectional_profile", ""),
            "run_style_cluster": r.get("run_style_cluster", ""),
            "late_power_index": r.get("late_power_index", ""),
            "sustain_index": r.get("sustain_index", ""),
            "fatigue_risk_index": r.get("fatigue_risk_index", ""),
            "sectional_weapon_score": r.get("sectional_weapon_score", ""),
            "race_shape_note": (
                f"{race_shape} | bias={race_shape_bias} | pressure={round(pace_pressure_score,2)} | "
                f"collapse={round(collapse_risk_score,2)} | fit={tempo_fit} | tempo_edge={tempo_edge_score}"
            )
        })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "rows": len(out),
    "races": out[["race_date", "track", "race_no"]].drop_duplicates().shape[0],
    "chaotic": int((out["projected_race_shape"] == "CHAOTIC_PACE").sum()),
    "hot": int((out["projected_race_shape"] == "HOT_TEMPO").sum()),
    "fast": int((out["projected_race_shape"] == "FAST_TEMPO").sum()),
    "neutral": int((out["projected_race_shape"] == "NEUTRAL").sum()),
    "slow": int((out["projected_race_shape"] == "SLOW_TEMPO").sum()),
    "advantaged": int((out["tempo_fit_v2"] == "ADVANTAGED").sum()),
    "disadvantaged": int((out["tempo_fit_v2"] == "DISADVANTAGED").sum()),
    "strong_tempo_edges": int((out["tempo_edge_grade_v2"] == "STRONG").sum()),
}])

diag.to_csv(DIAG, index=False)

print("=" * 100)
print("EDGEIQ RACE SHAPE ENGINE V2")
print("=" * 100)
print(diag.to_string(index=False))

print()
print("=" * 100)
print("TOP TEMPO EDGES")
print("=" * 100)

cols = [
    "race_date","track","race_no","horse","map_style",
    "projected_race_shape","race_shape_bias",
    "tempo_fit_v2","tempo_edge_score_v2","tempo_edge_grade_v2",
    "pace_pressure_score","collapse_risk_score","race_shape_note"
]

print(
    out.sort_values(["tempo_edge_score_v2","pace_pressure_score"], ascending=False)
    [cols]
    .head(40)
    .to_string(index=False)
)

print()
print("SAVED:")
print(OUT)
print(DIAG)
