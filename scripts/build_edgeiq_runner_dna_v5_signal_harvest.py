from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import re
import math

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

DNA4 = DATA / "edgeiq_runner_dna_current.csv"
RUNNER_INTEL = DATA / "edgeiq_runner_intelligence_v1.csv"
TRACK_INTEL = DATA / "edgeiq_live_track_intelligence_v2_1.csv"
TJ = DATA / "edgeiq_live_trainer_jockey_factor_feed_v3.csv"
BOARD = DATA / "edgeiq_live_runner_board_governed_v1.csv"

OUT = DATA / "edgeiq_runner_dna_v5_signal_harvest.csv"
CURRENT = DATA / "edgeiq_runner_dna_current.csv"
SUMMARY = DATA / "edgeiq_runner_dna_v5_signal_harvest_summary.csv"
COVERAGE = DATA / "edgeiq_runner_dna_v5_component_coverage.csv"

def key_horse(x):
    s = str(x or "").strip().upper()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s

def join_key(df):
    return (
        df["race_date"].astype(str).str.strip() + "|" +
        df["track"].astype(str).str.strip().str.upper() + "|" +
        df["race_no"].astype(str).str.strip() + "|" +
        df["horse"].astype(str).map(key_horse)
    )

def num(x):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return np.nan
        return float(str(x).replace(",", "").strip())
    except Exception:
        return np.nan

def clamp(x, lo=0, hi=100):
    try:
        return max(lo, min(hi, float(x)))
    except Exception:
        return np.nan

def band(v):
    x = num(v)
    if math.isnan(x):
        return "NO_SCORE"
    if x >= 80:
        return "ELITE"
    if x >= 70:
        return "STRONG"
    if x >= 60:
        return "POSITIVE"
    if x >= 50:
        return "NEUTRAL"
    if x >= 40:
        return "NEGATIVE"
    return "POOR"

def factor01_to_score(x):
    v = num(x)
    if math.isnan(v):
        return np.nan
    return round(clamp(50 + (v * 20)), 1)

def band_to_score(x):
    b = str(x or "").upper().replace("_", " ")
    if b == "ELITE":
        return 92
    if b == "STRONG":
        return 80
    if b in ["POSITIVE", "ABOVE AVERAGE"]:
        return 68
    if b in ["NEUTRAL", "AVERAGE"]:
        return 55
    if b in ["NEGATIVE", "BELOW AVERAGE"]:
        return 40
    if b == "POOR":
        return 25
    if b == "LOW SAMPLE":
        return 50
    return np.nan

def first_num(row, cols):
    for c in cols:
        if c in row.index:
            v = num(row.get(c, ""))
            if not math.isnan(v):
                return v
    return np.nan

def top_factors(row, mode):
    factors = [
        ("FORM", row.get("form_score", "")),
        ("RATING", row.get("rating_score", "")),
        ("DISTANCE", row.get("distance_score", "")),
        ("TRACK", row.get("track_score", "")),
        ("CONDITION", row.get("condition_score", "")),
        ("CLASS", row.get("class_score", "")),
        ("BARRIER", row.get("barrier_score", "")),
        ("PACE", row.get("pace_score", "")),
        ("TACTICAL", row.get("tactical_score", "")),
        ("LATE POWER", row.get("late_power_score", "")),
        ("TRAINER", row.get("trainer_score", "")),
        ("JOCKEY", row.get("jockey_score", "")),
        ("COMBO", row.get("combo_score", "")),
        ("SECTIONALS", row.get("sectional_score", "")),
        ("RUN STYLE", row.get("run_style_score", "")),
        ("FITNESS", row.get("fitness_score", "")),
        ("PROFILE", row.get("profile_score", "")),
    ]
    vals = []
    for name, value in factors:
        v = num(value)
        if not math.isnan(v):
            vals.append((name, v))
    vals = sorted(vals, key=lambda x: x[1], reverse=(mode == "strong"))
    return " | ".join([f"{n} {v:.1f}" for n, v in vals[:3]])

dna = pd.read_csv(DNA4, dtype=str, keep_default_na=False, low_memory=False)
board = pd.read_csv(BOARD, dtype=str, keep_default_na=False, low_memory=False)

dna["join_key"] = join_key(dna)
board["join_key"] = join_key(board)

out = dna.copy()

if RUNNER_INTEL.exists():
    ri = pd.read_csv(RUNNER_INTEL, dtype=str, keep_default_na=False, low_memory=False)
    ri["join_key"] = join_key(ri)
    keep = [
        "join_key",
        "projected_spd",
        "settling_band",
        "dna_confidence",
        "archetype",
        "run_style",
        "tactical_score",
        "late_power_index",
        "fatigue_risk_index",
        "sectional_weapon_score",
        "tempo_fit",
        "confidence_score",
        "peak_rating",
    ]
    out = out.merge(ri[[c for c in keep if c in ri.columns]].drop_duplicates("join_key"), on="join_key", how="left", suffixes=("", "_runnerintel"))

if TRACK_INTEL.exists():
    ti = pd.read_csv(TRACK_INTEL, dtype=str, keep_default_na=False, low_memory=False)
    ti["join_key"] = join_key(ti)
    keep = [
        "join_key",
        "track_fit_score",
        "track_fit_band",
        "run_style_alignment",
        "barrier_alignment",
        "movement_alignment",
        "track_profile_confidence",
        "track_profile_level",
        "historical_run_style",
        "historical_barrier_lane",
        "track_intelligence_label_v2_1",
    ]
    out = out.merge(ti[[c for c in keep if c in ti.columns]].drop_duplicates("join_key"), on="join_key", how="left", suffixes=("", "_trackintel"))

if TJ.exists():
    tj = pd.read_csv(TJ, dtype=str, keep_default_na=False, low_memory=False)
    tj["join_key"] = join_key(tj)
    keep = [
        "join_key",
        "trainer_factor_matched_v3",
        "jockey_factor_matched_v3",
        "combo_factor_matched_v3",
        "trainer_factor_band_v1",
        "trainer_factor_score_v1",
        "trainer_factor_starts_v1",
        "trainer_win_pct_v1",
        "trainer_place_pct_v1",
        "jockey_factor_band_v1",
        "jockey_factor_score_v1",
        "jockey_factor_starts_v1",
        "jockey_win_pct_v1",
        "jockey_place_pct_v1",
        "combo_factor_band_v1",
        "combo_factor_score_v1",
        "combo_factor_starts_v1",
        "combo_win_pct_v1",
        "combo_place_pct_v1",
        "trainer_jockey_blend_score_v3",
        "trainer_jockey_blend_band_v3",
        "tj_factor_verdict_v3",
    ]
    out = out.merge(tj[[c for c in keep if c in tj.columns]].drop_duplicates("join_key"), on="join_key", how="left", suffixes=("", "_tj"))

# Override / enrich scores with harvested current signals.
out["track_score"] = out.apply(
    lambda r: first_num(r, ["track_fit_score_trackintel", "track_fit_score", "track_score"]),
    axis=1
)

out["pace_score"] = out["tempo_fit"].map(lambda x: {
    "GOOD": 70,
    "NEUTRAL": 55,
    "POOR": 35,
    "BAD": 25,
}.get(str(x or "").upper(), np.nan))

out["tactical_score"] = out.apply(lambda r: first_num(r, ["tactical_score"]), axis=1)
out["late_power_score"] = out.apply(lambda r: first_num(r, ["late_power_index"]), axis=1)

# Sectional: prefer live runner-intel sectional weapon if present, else existing sectional_score.
out["sectional_score"] = out.apply(
    lambda r: first_num(r, ["sectional_weapon_score", "sectional_score"]),
    axis=1
)

# Run style: prefer live tactical/run-style confidence where present.
out["run_style_score"] = out.apply(
    lambda r: first_num(r, ["tactical_score", "run_style_score"]),
    axis=1
)

# Fitness: fatigue risk inverted, if available. Otherwise existing fitness.
out["fitness_score"] = out.apply(
    lambda r: round(clamp(100 - first_num(r, ["fatigue_risk_index"])), 1)
    if not math.isnan(first_num(r, ["fatigue_risk_index"])) else first_num(r, ["fitness_score"]),
    axis=1
)

out["trainer_score"] = out.apply(
    lambda r: factor01_to_score(r.get("trainer_factor_score_v1", "")) if str(r.get("trainer_factor_matched_v3", "")).upper() == "YES" else np.nan,
    axis=1
)
out["jockey_score"] = out.apply(
    lambda r: factor01_to_score(r.get("jockey_factor_score_v1", "")) if str(r.get("jockey_factor_matched_v3", "")).upper() == "YES" else np.nan,
    axis=1
)
out["combo_score"] = out.apply(
    lambda r: factor01_to_score(r.get("trainer_jockey_blend_score_v3", "")) if str(r.get("tj_factor_verdict_v3", "")).upper() == "COMPLETE" else np.nan,
    axis=1
)

weights = {
    "form_score": 1.20,
    "rating_score": 1.20,
    "distance_score": 1.05,
    "track_score": 1.05,
    "condition_score": 0.95,
    "class_score": 0.85,
    "barrier_score": 0.65,
    "pace_score": 0.80,
    "tactical_score": 0.80,
    "late_power_score": 0.90,
    "trainer_score": 0.60,
    "jockey_score": 0.60,
    "combo_score": 0.70,
    "sectional_score": 1.05,
    "run_style_score": 0.65,
    "fitness_score": 0.75,
    "profile_score": 0.60,
}

def weighted_score(r):
    total = 0
    wsum = 0
    for c, w in weights.items():
        v = num(r.get(c, ""))
        if not math.isnan(v):
            total += v * w
            wsum += w
    return round(total / wsum, 1) if wsum else ""

out["runner_dna_score"] = out.apply(weighted_score, axis=1)
out["runner_dna_band"] = out["runner_dna_score"].map(band)
out["runner_dna_rank_in_race"] = (
    pd.to_numeric(out["runner_dna_score"], errors="coerce")
    .groupby([out["race_date"], out["track"], out["race_no"]])
    .rank(method="first", ascending=False)
)

out["strongest_factors"] = out.apply(lambda r: top_factors(r, "strong"), axis=1)
out["weakest_factors"] = out.apply(lambda r: top_factors(r, "weak"), axis=1)

out["runner_dna_customer_summary"] = (
    "DNA " + out["runner_dna_score"].astype(str) + " " + out["runner_dna_band"].astype(str)
    + " | Strong: " + out["strongest_factors"].astype(str)
    + " | Risk: " + out["weakest_factors"].astype(str)
)

out["built_at_runner_dna_v5"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

out.to_csv(OUT, index=False)
out.to_csv(CURRENT, index=False)

components = list(weights.keys())
coverage_rows = []
for c in components:
    s = out[c].astype(str).str.strip() if c in out.columns else pd.Series([""] * len(out))
    covered = s.ne("") & s.str.lower().ne("nan")
    coverage_rows.append({
        "component": c,
        "covered_rows": int(covered.sum()),
        "missing_rows": int((~covered).sum()),
        "coverage_pct": round((covered.sum() / len(out)) * 100, 2),
    })
coverage = pd.DataFrame(coverage_rows)
coverage.to_csv(COVERAGE, index=False)

summary_rows = [
    {"metric": "status", "value": "RUNNER_DNA_V5_SIGNAL_HARVEST_BUILT"},
    {"metric": "rows", "value": len(out)},
    {"metric": "current_feed", "value": CURRENT.name},
    {"metric": "avg_component_coverage_pct", "value": round(float(coverage["coverage_pct"].mean()), 2)},
]

for k, v in out["runner_dna_band"].value_counts().items():
    summary_rows.append({"metric": f"runner_dna_band_{k}", "value": int(v)})

summary = pd.DataFrame(summary_rows)
summary.to_csv(SUMMARY, index=False)

print("[RUNNER_DNA_V5_SIGNAL_HARVEST] COMPLETE")
print(summary.to_string(index=False))
print(f"out={OUT}")
print(f"current={CURRENT}")
print(f"coverage={COVERAGE}")
print(f"summary={SUMMARY}")
