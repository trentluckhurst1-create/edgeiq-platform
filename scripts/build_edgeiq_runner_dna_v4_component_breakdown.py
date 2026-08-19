from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import math

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

DNA3 = DATA / "edgeiq_runner_dna_v3.csv"
BOARD = DATA / "edgeiq_live_runner_board_governed_v1.csv"

OUT = DATA / "edgeiq_runner_dna_v4_component_breakdown.csv"
SUMMARY = DATA / "edgeiq_runner_dna_v4_component_breakdown_summary.csv"
CURRENT = DATA / "edgeiq_runner_dna_current.csv"

def num(x):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return np.nan
        return float(str(x).replace(",", "").strip())
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

def fmt(v):
    x = num(v)
    if math.isnan(x):
        return ""
    return round(x, 1)

def top_factors(row, mode):
    factors = [
        ("FORM", row.get("form_score", "")),
        ("RATING", row.get("rating_score", "")),
        ("DISTANCE", row.get("distance_score", "")),
        ("TRACK", row.get("track_score", "")),
        ("CONDITION", row.get("condition_score", "")),
        ("CLASS", row.get("class_score", "")),
        ("BARRIER", row.get("barrier_score", "")),
        ("JOCKEY", row.get("jockey_score", "")),
        ("TRAINER", row.get("trainer_score", "")),
        ("SECTIONALS", row.get("sectional_score", "")),
        ("RUN STYLE", row.get("run_style_score", "")),
        ("FITNESS", row.get("fitness_score", "")),
        ("PROFILE", row.get("profile_score", "")),
    ]
    vals = []
    for name, value in factors:
        x = num(value)
        if not math.isnan(x):
            vals.append((name, x))
    vals = sorted(vals, key=lambda x: x[1], reverse=(mode == "strong"))
    return " | ".join([f"{name} {value:.1f}" for name, value in vals[:3]])

def main():
    dna = pd.read_csv(DNA3, dtype=str, keep_default_na=False, low_memory=False)
    board = pd.read_csv(BOARD, dtype=str, keep_default_na=False, low_memory=False)

    rows = []
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for _, r in dna.iterrows():
        score = fmt(r.get("runner_dna_v3_score", ""))

        row = {
            "race_date": r.get("race_date", ""),
            "track": r.get("track", ""),
            "race_no": r.get("race_no", ""),
            "horse": r.get("horse", ""),
            "horse_key": r.get("horse_key", ""),

            "runner_dna_score": score,
            "runner_dna_band": band(score),

            "form_score": fmt(r.get("form_score", "")),
            "rating_score": fmt(r.get("rating_score", "")),
            "distance_score": fmt(r.get("distance_score", "")),
            "track_score": fmt(r.get("track_score", "")),
            "condition_score": fmt(r.get("condition_score", "")),
            "class_score": fmt(r.get("class_score", "")),
            "barrier_score": fmt(r.get("barrier_score", "")),
            "jockey_score": fmt(r.get("jockey_score", "")),
            "trainer_score": fmt(r.get("trainer_score", "")),
            "sectional_score": fmt(r.get("sectional_score", "")),
            "run_style_score": fmt(r.get("run_style_score", "")),
            "fitness_score": fmt(r.get("fitness_score", "")),
            "profile_score": fmt(r.get("profile_score", "")),

            "profile_quality": r.get("profile_quality", ""),
            "career_starts_profile": r.get("career_starts_profile", ""),
            "career_wins_profile": r.get("career_wins_profile", ""),
            "career_places_profile": r.get("career_places_profile", ""),
            "career_win_pct_profile": r.get("career_win_pct_profile", ""),
            "career_place_pct_profile": r.get("career_place_pct_profile", ""),
            "last_5_form_profile": r.get("last_5_form_profile", ""),
            "last_start_date_profile": r.get("last_start_date_profile", ""),
            "days_since_last_start_profile": r.get("days_since_last_start_profile", ""),

            "dominant_run_style": r.get("dominant_run_style", ""),
            "sectional_strength_rating": r.get("sectional_strength_rating", ""),
            "sectional_strength_band": r.get("sectional_strength_band", ""),
            "sectional_archetype": r.get("sectional_archetype", ""),

            "track_family": r.get("track_family", ""),
            "distance_bucket": r.get("distance_bucket", ""),
            "condition_bucket": r.get("condition_bucket", ""),
            "barrier_bucket": r.get("barrier_bucket", ""),

            "track_fit_starts": r.get("track_fit_starts", ""),
            "track_fit_place_pct": r.get("track_fit_place_pct", ""),
            "distance_fit_starts": r.get("distance_fit_starts", ""),
            "distance_fit_place_pct": r.get("distance_fit_place_pct", ""),
            "condition_fit_starts": r.get("condition_fit_starts", ""),
            "condition_fit_place_pct": r.get("condition_fit_place_pct", ""),
            "barrier_fit_starts": r.get("barrier_fit_starts", ""),
            "barrier_fit_place_pct": r.get("barrier_fit_place_pct", ""),

            "strongest_factors": top_factors(r, "strong"),
            "weakest_factors": top_factors(r, "weak"),

            "runner_dna_customer_summary": (
                f"DNA {score if score != '' else '—'} {band(score)} | "
                f"Form {fmt(r.get('form_score', '')) if fmt(r.get('form_score', '')) != '' else '—'} | "
                f"Distance {fmt(r.get('distance_score', '')) if fmt(r.get('distance_score', '')) != '' else '—'} | "
                f"Sectionals {fmt(r.get('sectional_score', '')) if fmt(r.get('sectional_score', '')) != '' else '—'}"
            ),

            "built_at_runner_dna_v4": now,
        }

        rows.append(row)

    out = pd.DataFrame(rows)

    def join_key(df):
        return (
            df["race_date"].astype(str).str.strip() + "|" +
            df["track"].astype(str).str.strip().str.upper() + "|" +
            df["race_no"].astype(str).str.strip() + "|" +
            df["horse"].astype(str).str.strip().str.upper()
        )

    out["join_key"] = join_key(out)
    board["join_key"] = join_key(board)

    board_keep = [
        "join_key",
        "fair_price",
        "live_price",
        "edge_pct",
        "win_pct",
        "V6_1_RESEARCH_price_rank",
        "projection_band_V6_1_RESEARCH",
        "projection_gap_V6_1_RESEARCH",
        "execution_action_governed",
    ]
    out = out.merge(board[[c for c in board_keep if c in board.columns]], on="join_key", how="left")

    out["runner_dna_rank_in_race"] = (
        pd.to_numeric(out["runner_dna_score"], errors="coerce")
        .groupby([out["race_date"], out["track"], out["race_no"]])
        .rank(method="first", ascending=False)
    )

    out.to_csv(OUT, index=False)
    out.to_csv(CURRENT, index=False)

    summary_rows = [
        {"metric": "status", "value": "RUNNER_DNA_V4_COMPONENT_BREAKDOWN_BUILT"},
        {"metric": "rows", "value": len(out)},
        {"metric": "current_feed", "value": CURRENT.name},
        {"metric": "with_score", "value": int(out["runner_dna_score"].astype(str).ne("").sum())},
    ]

    for k, v in out["runner_dna_band"].value_counts().items():
        summary_rows.append({"metric": f"runner_dna_band_{k}", "value": int(v)})

    pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)

    print("[RUNNER_DNA_V4_COMPONENT_BREAKDOWN] COMPLETE")
    print(pd.DataFrame(summary_rows).to_string(index=False))
    print(f"out={OUT}")
    print(f"current={CURRENT}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
