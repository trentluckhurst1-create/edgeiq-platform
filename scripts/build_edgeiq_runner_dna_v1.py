from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_live_runner_board_governed_v1.csv"
PROFILE = DATA / "edgeiq_live_horse_profile_current.csv"
WAREHOUSE = DATA / "edgeiq_racingcom_results_warehouse_full_v1.csv"

OUT = DATA / "edgeiq_runner_dna_v1.csv"
SUMMARY = DATA / "edgeiq_runner_dna_v1_summary.csv"

def key(x):
    s = str(x or "").strip().upper()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s

def text(x):
    return str(x or "").strip()

def num(x):
    return pd.to_numeric(x, errors="coerce")

def finish_num(x):
    m = re.search(r"\d+", str(x or ""))
    return float(m.group(0)) if m else np.nan

def pct(wins, starts):
    if starts and starts > 0:
        return round((wins / starts) * 100, 2)
    return ""

def score_from_win_pct(win_pct, baseline=10):
    try:
        v = float(win_pct)
        return max(0, min(100, round(50 + ((v - baseline) * 3), 1)))
    except Exception:
        return ""

def score_from_place_pct(place_pct, baseline=30):
    try:
        v = float(place_pct)
        return max(0, min(100, round(50 + ((v - baseline) * 1.5), 1)))
    except Exception:
        return ""

def score_from_band(band):
    b = str(band or "").upper().replace("_", " ")
    if b in ["ELITE"]:
        return 92
    if b in ["STRONG", "ABOVE AVERAGE"]:
        return 78
    if b in ["POSITIVE"]:
        return 68
    if b in ["AVERAGE", "NEUTRAL"]:
        return 55
    if b in ["NEGATIVE", "BELOW AVERAGE"]:
        return 40
    if b in ["POOR"]:
        return 25
    return ""

def main():
    live = pd.read_csv(LIVE, dtype=str, keep_default_na=False, low_memory=False)
    profile = pd.read_csv(PROFILE, dtype=str, keep_default_na=False, low_memory=False)
    wh = pd.read_csv(WAREHOUSE, dtype=str, keep_default_na=False, low_memory=False)

    live["horse_key_dna"] = live["horse"].map(key)
    profile["horse_key_dna"] = profile["horse"].map(key)
    wh["horse_key_dna"] = wh["horseName"].map(key)

    wh["finish_num"] = num(wh.get("finishPosition", ""))
    wh["is_win"] = wh["finish_num"].eq(1)
    wh["is_place"] = wh["finish_num"].between(1, 3, inclusive="both")
    wh["distance_num"] = num(wh.get("distance", "").astype(str).str.replace("m", "", regex=False))
    wh["track_clean"] = wh.get("track", "").astype(str).str.upper().str.strip()
    wh["class_clean"] = wh.get("raceClass", "").astype(str).str.upper().str.strip()
    wh["condition_clean"] = wh.get("trackCondition", "").astype(str).str.upper().str.strip()
    wh["jockey_clean"] = wh.get("jockey", "").astype(str).str.upper().str.strip()
    wh["trainer_clean"] = wh.get("trainer", "").astype(str).str.upper().str.strip()
    wh["barrier_num"] = num(wh.get("barrier", ""))

    prof_cols = [
        "horse_key_dna",
        "profile_quality",
        "career_starts_profile",
        "career_wins_profile",
        "career_places_profile",
        "career_win_pct_profile",
        "career_place_pct_profile",
        "last_5_form_profile",
        "last_start_date_profile",
        "days_since_last_start_profile",
        "latest_v6_rating_profile",
        "avg_v6_rating_last_5_profile",
        "peak_v6_rating_profile",
        "dominant_run_style",
        "movement_profile",
        "style_confidence",
        "sectional_strength_rating",
        "sectional_strength_band",
        "sectional_strength_confidence",
        "sectional_archetype",
        "runs_with_sectionals",
    ]
    prof_small = profile[[c for c in prof_cols if c in profile.columns]].drop_duplicates("horse_key_dna")

    rows = []
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for _, r in live.iterrows():
        hk = r["horse_key_dna"]
        hist = wh[wh["horse_key_dna"].eq(hk)].copy()

        track_now = text(r.get("track", "")).upper()
        class_now = text(r.get("race_class", "")).upper()
        condition_now = text(r.get("track_condition", "")).upper()
        jockey_now = text(r.get("jockey", "")).upper()
        trainer_now = text(r.get("trainer", "")).upper()
        barrier_now = pd.to_numeric(r.get("barrier", ""), errors="coerce")
        distance_now = pd.to_numeric(r.get("distance", ""), errors="coerce")

        distance_low = distance_now - 100 if pd.notna(distance_now) else np.nan
        distance_high = distance_now + 100 if pd.notna(distance_now) else np.nan

        track_hist = hist[hist["track_clean"].eq(track_now)] if len(hist) else hist
        class_hist = hist[hist["class_clean"].str.contains(re.escape(class_now), na=False)] if class_now and len(hist) else hist.iloc[0:0]
        condition_hist = hist[hist["condition_clean"].str.contains("SOFT|HEAVY", regex=True, na=False)] if ("SOFT" in condition_now or "HEAVY" in condition_now) and len(hist) else hist[hist["condition_clean"].str.contains("GOOD|FIRM|FAST", regex=True, na=False)] if len(hist) else hist
        jockey_hist = hist[hist["jockey_clean"].eq(jockey_now)] if len(hist) else hist
        trainer_hist = hist[hist["trainer_clean"].eq(trainer_now)] if len(hist) else hist

        if pd.notna(distance_now) and len(hist):
            distance_hist = hist[(hist["distance_num"] >= distance_low) & (hist["distance_num"] <= distance_high)]
        else:
            distance_hist = hist.iloc[0:0]

        if pd.notna(barrier_now) and len(hist):
            if barrier_now <= 4:
                barrier_hist = hist[hist["barrier_num"].between(1, 4, inclusive="both")]
                barrier_bucket = "INSIDE"
            elif barrier_now <= 8:
                barrier_hist = hist[hist["barrier_num"].between(5, 8, inclusive="both")]
                barrier_bucket = "MIDDLE"
            else:
                barrier_hist = hist[hist["barrier_num"] >= 9]
                barrier_bucket = "WIDE"
        else:
            barrier_hist = hist.iloc[0:0]
            barrier_bucket = ""

        def stat_block(prefix, df):
            starts = len(df)
            wins = int(df["is_win"].sum()) if starts else 0
            places = int(df["is_place"].sum()) if starts else 0
            win_pct = pct(wins, starts)
            place_pct = pct(places, starts)
            return {
                f"{prefix}_starts": starts,
                f"{prefix}_wins": wins,
                f"{prefix}_places": places,
                f"{prefix}_win_pct": win_pct,
                f"{prefix}_place_pct": place_pct,
                f"{prefix}_score": score_from_place_pct(place_pct),
            }

        row = {
            "race_date": r.get("race_date", ""),
            "track": r.get("track", ""),
            "race_no": r.get("race_no", ""),
            "horse": r.get("horse", ""),
            "horse_key": hk,
            "barrier": r.get("barrier", ""),
            "barrier_bucket": barrier_bucket,
            "jockey": r.get("jockey", ""),
            "trainer": r.get("trainer", ""),
            "race_class": r.get("race_class", ""),
            "distance": r.get("distance", ""),
            "track_condition": r.get("track_condition", ""),
        }

        row.update(stat_block("track_fit", track_hist))
        row.update(stat_block("distance_fit", distance_hist))
        row.update(stat_block("class_fit", class_hist))
        row.update(stat_block("condition_fit", condition_hist))
        row.update(stat_block("barrier_fit", barrier_hist))
        row.update(stat_block("jockey_fit", jockey_hist))
        row.update(stat_block("trainer_fit", trainer_hist))

        rows.append(row)

    out = pd.DataFrame(rows)
    out = out.merge(prof_small, left_on="horse_key", right_on="horse_key_dna", how="left") if "horse_key_dna" in prof_small.columns else out

    # after merge, normalize key column if present
    if "horse_key_dna" in out.columns:
        out = out.rename(columns={"horse_key_dna": "profile_join_key"})

    for col in ["sectional_strength_band", "profile_quality"]:
        if col not in out.columns:
            out[col] = ""

    out["sectional_fit_score"] = out["sectional_strength_band"].map(score_from_band)
    out["profile_quality_score"] = out["profile_quality"].map({
        "HIGH": 85,
        "MEDIUM": 68,
        "LOW": 48,
        "RATING_ONLY": 35,
        "BACKFILLED_ONLY_LOW_CONFIDENCE": 20,
        "NO_PROFILE": 10,
    }).fillna(35)

    score_cols = [
        "track_fit_score",
        "distance_fit_score",
        "class_fit_score",
        "condition_fit_score",
        "barrier_fit_score",
        "jockey_fit_score",
        "trainer_fit_score",
        "sectional_fit_score",
        "profile_quality_score",
    ]

    def avg_score(row):
        vals = []
        for c in score_cols:
            try:
                v = float(row.get(c, np.nan))
                if not np.isnan(v):
                    vals.append(v)
            except Exception:
                pass
        return round(sum(vals) / len(vals), 1) if vals else ""

    out["runner_dna_score"] = out.apply(avg_score, axis=1)

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

    out["runner_dna_band"] = out["runner_dna_score"].map(band_from_score)
    out["built_at_runner_dna_v1"] = built_at

    out.to_csv(OUT, index=False)

    summary_rows = [
        {"metric": "status", "value": "RUNNER_DNA_V1_BUILT"},
        {"metric": "rows", "value": len(out)},
        {"metric": "with_runner_dna_score", "value": int(out["runner_dna_score"].astype(str).ne("").sum())},
    ]

    for k, v in out["runner_dna_band"].value_counts().items():
        summary_rows.append({"metric": f"runner_dna_band_{k}", "value": int(v)})

    pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)

    print("[RUNNER_DNA_V1] COMPLETE")
    print(pd.DataFrame(summary_rows).to_string(index=False))
    print(f"out={OUT}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
