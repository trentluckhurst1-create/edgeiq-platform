from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import re
import math

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

DNA2 = DATA / "edgeiq_runner_dna_v2.csv"
BOARD = DATA / "edgeiq_live_runner_board_governed_v1.csv"

OUT = DATA / "edgeiq_runner_dna_v3.csv"
SUMMARY = DATA / "edgeiq_runner_dna_v3_summary.csv"
COMPARE = DATA / "edgeiq_runner_dna_v3_vs_price_rank_audit.csv"

def num(x, default=np.nan):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return default
        return float(str(x).replace(",", "").strip())
    except Exception:
        return default

def clamp(x, lo=0, hi=100):
    try:
        return max(lo, min(hi, float(x)))
    except Exception:
        return np.nan

def band_from_score(v):
    try:
        x = float(v)
    except Exception:
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

def place_fit_score(place_pct, starts):
    starts = num(starts, 0)
    place_pct = num(place_pct, np.nan)
    if starts <= 0 or math.isnan(place_pct):
        return np.nan
    confidence_cap = 55 if starts == 1 else 65 if starts == 2 else 80 if starts <= 4 else 100
    raw = 50 + ((place_pct - 30) * 1.4)
    return round(min(clamp(raw), confidence_cap), 1)

def win_fit_score(win_pct, starts):
    starts = num(starts, 0)
    win_pct = num(win_pct, np.nan)
    if starts <= 0 or math.isnan(win_pct):
        return np.nan
    confidence_cap = 55 if starts == 1 else 65 if starts == 2 else 80 if starts <= 4 else 100
    raw = 50 + ((win_pct - 10) * 2.4)
    return round(min(clamp(raw), confidence_cap), 1)

def score_from_band(band):
    b = str(band or "").upper().replace("_", " ")
    if b == "ELITE":
        return 92
    if b == "STRONG":
        return 80
    if b == "ABOVE AVERAGE":
        return 74
    if b == "POSITIVE":
        return 68
    if b in ["AVERAGE", "NEUTRAL"]:
        return 55
    if b in ["BELOW AVERAGE", "NEGATIVE"]:
        return 40
    if b == "POOR":
        return 25
    return np.nan

def profile_score(q):
    q = str(q or "").upper()
    return {
        "HIGH": 85,
        "MEDIUM": 68,
        "LOW": 48,
        "RATING_ONLY": 35,
        "BACKFILLED_ONLY_LOW_CONFIDENCE": 20,
        "NO_PROFILE": 10,
    }.get(q, 35)

def form_score(last5):
    vals = []
    for token in str(last5 or "").split("-"):
        token = token.strip()
        if not token or token == "?":
            continue
        try:
            pos = int(float(token))
            if pos == 1:
                vals.append(92)
            elif pos == 2:
                vals.append(82)
            elif pos == 3:
                vals.append(74)
            elif pos <= 5:
                vals.append(62)
            elif pos <= 8:
                vals.append(48)
            else:
                vals.append(32)
        except Exception:
            pass
    if not vals:
        return np.nan
    weights = [1.00, 0.85, 0.70, 0.55, 0.40]
    used = weights[:len(vals)]
    return round(sum(v*w for v,w in zip(vals, used)) / sum(used), 1)

def fitness_score(days):
    d = num(days, np.nan)
    if math.isnan(d):
        return np.nan
    if d <= 7:
        return 58
    if d <= 35:
        return 82
    if d <= 70:
        return 72
    if d <= 120:
        return 58
    if d <= 200:
        return 44
    return 32

def rating_score(latest, avg5, peak):
    vals = []
    for v in [latest, avg5, peak]:
        x = num(v, np.nan)
        if not math.isnan(x):
            vals.append(x)
    if not vals:
        return np.nan
    # V6 ratings generally sit around 50-85. Convert to 0-100-ish.
    raw = (sum(vals) / len(vals) - 50) * 2
    return round(clamp(raw), 1)

def run_style_score(style):
    s = str(style or "").upper().replace("_", " ")
    if s in ["LEADER", "ON PACE", "ONPACE"]:
        return 68
    if s == "MIDFIELD":
        return 58
    if s == "BACKMARKER":
        return 48
    return np.nan

def avg_weighted(row, weights):
    total = 0
    wsum = 0
    for col, w in weights.items():
        v = num(row.get(col, ""), np.nan)
        if not math.isnan(v):
            total += v * w
            wsum += w
    return round(total / wsum, 1) if wsum else ""

def main():
    dna = pd.read_csv(DNA2, dtype=str, keep_default_na=False, low_memory=False)
    board = pd.read_csv(BOARD, dtype=str, keep_default_na=False, low_memory=False)

    out = dna.copy()

    out["form_score"] = out["last_5_form_profile"].map(form_score)
    out["fitness_score"] = out["days_since_last_start_profile"].map(fitness_score)
    out["rating_score"] = out.apply(lambda r: rating_score(
        r.get("latest_v6_rating_profile", ""),
        r.get("avg_v6_rating_last_5_profile", ""),
        r.get("peak_v6_rating_profile", "")
    ), axis=1)

    out["track_score"] = out.apply(lambda r: place_fit_score(r.get("track_fit_place_pct", ""), r.get("track_fit_starts", "")), axis=1)
    out["distance_score"] = out.apply(lambda r: place_fit_score(r.get("distance_fit_place_pct", ""), r.get("distance_fit_starts", "")), axis=1)
    out["condition_score"] = out.apply(lambda r: place_fit_score(r.get("condition_fit_place_pct", ""), r.get("condition_fit_starts", "")), axis=1)
    out["barrier_score"] = out.apply(lambda r: place_fit_score(r.get("barrier_fit_place_pct", ""), r.get("barrier_fit_starts", "")), axis=1)
    out["jockey_score"] = out.apply(lambda r: place_fit_score(r.get("jockey_fit_place_pct", ""), r.get("jockey_fit_starts", "")), axis=1)
    out["trainer_score"] = out.apply(lambda r: place_fit_score(r.get("trainer_fit_place_pct", ""), r.get("trainer_fit_starts", "")), axis=1)
    out["class_score"] = out.apply(lambda r: place_fit_score(r.get("class_fit_place_pct", ""), r.get("class_fit_starts", "")), axis=1)

    out["sectional_score"] = out["sectional_strength_band"].map(score_from_band)
    out["profile_score"] = out["profile_quality"].map(profile_score)
    out["run_style_score"] = out["dominant_run_style"].map(run_style_score)

    weights = {
        "form_score": 1.25,
        "rating_score": 1.30,
        "distance_score": 1.10,
        "track_score": 0.95,
        "condition_score": 1.00,
        "class_score": 1.00,
        "barrier_score": 0.70,
        "jockey_score": 0.55,
        "trainer_score": 0.55,
        "sectional_score": 1.20,
        "run_style_score": 0.60,
        "fitness_score": 0.80,
        "profile_score": 0.75,
    }

    out["runner_dna_v3_score"] = out.apply(lambda r: avg_weighted(r, weights), axis=1)
    out["runner_dna_v3_band"] = out["runner_dna_v3_score"].map(band_from_score)

    out["strongest_factor"] = ""
    out["weakest_factor"] = ""

    factor_cols = list(weights.keys())
    for idx, r in out.iterrows():
        vals = []
        for c in factor_cols:
            v = num(r.get(c, ""), np.nan)
            if not math.isnan(v):
                vals.append((c, v))
        if vals:
            vals_sorted = sorted(vals, key=lambda x: x[1])
            out.at[idx, "weakest_factor"] = vals_sorted[0][0].replace("_score", "").replace("_", " ").upper()
            out.at[idx, "strongest_factor"] = vals_sorted[-1][0].replace("_score", "").replace("_", " ").upper()

    out["built_at_runner_dna_v3"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out.to_csv(OUT, index=False)

    summary_rows = [
        {"metric": "status", "value": "RUNNER_DNA_V3_BUILT"},
        {"metric": "rows", "value": len(out)},
        {"metric": "with_runner_dna_v3_score", "value": int(out["runner_dna_v3_score"].astype(str).ne("").sum())},
    ]

    for k, v in out["runner_dna_v3_band"].value_counts().items():
        summary_rows.append({"metric": f"runner_dna_v3_band_{k}", "value": int(v)})

    pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)

    board_small = board[[
        c for c in [
            "race_date","track","race_no","horse",
            "fair_price","live_price","edge_pct",
            "V6_1_RESEARCH_price_rank",
            "projection_band_V6_1_RESEARCH",
            "execution_action_governed"
        ] if c in board.columns
    ]].copy()

    def k(df):
        return (
            df["race_date"].astype(str).str.strip() + "|" +
            df["track"].astype(str).str.strip().str.upper() + "|" +
            df["race_no"].astype(str).str.strip() + "|" +
            df["horse"].astype(str).str.strip().str.upper()
        )

    out["join_key_compare"] = k(out)
    board_small["join_key_compare"] = k(board_small)

    cmp = out.merge(board_small, on="join_key_compare", how="left", suffixes=("", "_board"))
    cmp["dna_rank_in_race"] = (
        pd.to_numeric(cmp["runner_dna_v3_score"], errors="coerce")
        .groupby([cmp["race_date"], cmp["track"], cmp["race_no"]])
        .rank(method="first", ascending=False)
    )
    cmp.to_csv(COMPARE, index=False)

    print("[RUNNER_DNA_V3] COMPLETE")
    print(pd.DataFrame(summary_rows).to_string(index=False))
    print(f"out={OUT}")
    print(f"summary={SUMMARY}")
    print(f"compare={COMPARE}")

if __name__ == "__main__":
    main()
