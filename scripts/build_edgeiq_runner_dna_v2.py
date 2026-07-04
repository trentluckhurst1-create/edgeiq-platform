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
V1 = DATA / "edgeiq_runner_dna_v1.csv"

OUT = DATA / "edgeiq_runner_dna_v2.csv"
SUMMARY = DATA / "edgeiq_runner_dna_v2_summary.csv"

def key(x):
    s = str(x or "").strip().upper()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s

def text(x):
    return str(x or "").strip()

def num(x):
    return pd.to_numeric(x, errors="coerce")

def pct(wins, starts):
    if starts and starts > 0:
        return round((wins / starts) * 100, 2)
    return ""

def score_from_place_pct(place_pct, baseline=30):
    try:
        v = float(place_pct)
        return max(0, min(100, round(50 + ((v - baseline) * 1.5), 1)))
    except Exception:
        return ""

def track_family(x):
    s = text(x).upper()
    s = s.replace("BET365 ", "")
    if "CAULFIELD" in s:
        return "CAULFIELD"
    if "SANDOWN" in s:
        return "SANDOWN"
    if "PAKENHAM" in s:
        return "PAKENHAM"
    if "BALLARAT" in s:
        return "BALLARAT"
    if "BENDIGO" in s:
        return "BENDIGO"
    if "GEELONG" in s:
        return "GEELONG"
    if "MORNINGTON" in s:
        return "MORNINGTON"
    if "CRANBOURNE" in s:
        return "CRANBOURNE"
    if "FLEMINGTON" in s:
        return "FLEMINGTON"
    if "MOONEE" in s:
        return "MOONEE VALLEY"
    return re.sub(r"[^A-Z0-9 ]", "", s).strip()

def distance_bucket(x):
    try:
        d = float(x)
    except Exception:
        return ""
    if d <= 1200:
        return "SPRINT"
    if d <= 1600:
        return "MILE"
    if d <= 2100:
        return "MIDDLE"
    return "STAYING"

def condition_bucket(x):
    s = text(x).upper()
    if "HEAVY" in s:
        return "HEAVY"
    if "SOFT" in s:
        return "SOFT"
    if "GOOD" in s or "FIRM" in s or "FAST" in s:
        return "GOOD"
    return ""

def barrier_bucket(x):
    try:
        b = float(x)
    except Exception:
        return ""
    if b <= 4:
        return "INSIDE"
    if b <= 8:
        return "MIDDLE"
    return "WIDE"

def stat_block(prefix, df):
    starts = len(df)
    wins = int(df["is_win"].sum()) if starts else 0
    places = int(df["is_place"].sum()) if starts else 0
    place_pct = pct(places, starts)
    return {
        f"{prefix}_starts": starts,
        f"{prefix}_wins": wins,
        f"{prefix}_places": places,
        f"{prefix}_win_pct": pct(wins, starts),
        f"{prefix}_place_pct": place_pct,
        f"{prefix}_score": score_from_place_pct(place_pct),
    }

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

def main():
    live = pd.read_csv(LIVE, dtype=str, keep_default_na=False, low_memory=False)
    profile = pd.read_csv(PROFILE, dtype=str, keep_default_na=False, low_memory=False)
    wh = pd.read_csv(WAREHOUSE, dtype=str, keep_default_na=False, low_memory=False)
    v1 = pd.read_csv(V1, dtype=str, keep_default_na=False, low_memory=False) if V1.exists() else pd.DataFrame()

    live["horse_key_dna"] = live["horse"].map(key)
    profile["horse_key_dna"] = profile["horse"].map(key)
    wh["horse_key_dna"] = wh["horseName"].map(key)

    wh["finish_num"] = num(wh.get("finishPosition", ""))
    wh["is_win"] = wh["finish_num"].eq(1)
    wh["is_place"] = wh["finish_num"].between(1, 3, inclusive="both")
    wh["distance_num"] = num(wh.get("distance", "").astype(str).str.replace("m", "", regex=False))
    wh["track_family"] = wh.get("track", "").map(track_family)
    wh["distance_bucket"] = wh["distance_num"].map(distance_bucket)
    wh["condition_bucket"] = wh.get("trackCondition", "").map(condition_bucket)
    wh["barrier_bucket"] = wh.get("barrier", "").map(barrier_bucket)
    wh["jockey_clean"] = wh.get("jockey", "").astype(str).str.upper().str.strip()
    wh["trainer_clean"] = wh.get("trainer", "").astype(str).str.upper().str.strip()
    wh["class_clean"] = wh.get("raceClass", "").astype(str).str.upper().str.strip()

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

        now_track_family = track_family(r.get("track", ""))
        now_distance_bucket = distance_bucket(r.get("distance", ""))
        now_condition_bucket = condition_bucket(r.get("track_condition", ""))
        now_barrier_bucket = barrier_bucket(r.get("barrier", ""))
        now_jockey = text(r.get("jockey", "")).upper()
        now_trainer = text(r.get("trainer", "")).upper()
        now_class = text(r.get("race_class", "")).upper()

        track_hist = hist[hist["track_family"].eq(now_track_family)] if len(hist) and now_track_family else hist.iloc[0:0]
        distance_hist = hist[hist["distance_bucket"].eq(now_distance_bucket)] if len(hist) and now_distance_bucket else hist.iloc[0:0]
        condition_hist = hist[hist["condition_bucket"].eq(now_condition_bucket)] if len(hist) and now_condition_bucket else hist.iloc[0:0]
        barrier_hist = hist[hist["barrier_bucket"].eq(now_barrier_bucket)] if len(hist) and now_barrier_bucket else hist.iloc[0:0]
        jockey_hist = hist[hist["jockey_clean"].eq(now_jockey)] if len(hist) and now_jockey else hist.iloc[0:0]
        trainer_hist = hist[hist["trainer_clean"].eq(now_trainer)] if len(hist) and now_trainer else hist.iloc[0:0]
        class_hist = hist[hist["class_clean"].str.contains(re.escape(now_class), na=False)] if len(hist) and now_class else hist.iloc[0:0]

        row = {
            "race_date": r.get("race_date", ""),
            "track": r.get("track", ""),
            "race_no": r.get("race_no", ""),
            "horse": r.get("horse", ""),
            "horse_key": hk,
            "track_family": now_track_family,
            "distance_bucket": now_distance_bucket,
            "condition_bucket": now_condition_bucket,
            "barrier_bucket": now_barrier_bucket,
            "jockey": r.get("jockey", ""),
            "trainer": r.get("trainer", ""),
            "race_class": r.get("race_class", ""),
            "distance": r.get("distance", ""),
            "track_condition": r.get("track_condition", ""),
        }

        row.update(stat_block("track_fit", track_hist))
        row.update(stat_block("distance_fit", distance_hist))
        row.update(stat_block("condition_fit", condition_hist))
        row.update(stat_block("barrier_fit", barrier_hist))
        row.update(stat_block("jockey_fit", jockey_hist))
        row.update(stat_block("trainer_fit", trainer_hist))
        row.update(stat_block("class_fit", class_hist))

        rows.append(row)

    out = pd.DataFrame(rows)
    out = out.merge(prof_small, left_on="horse_key", right_on="horse_key_dna", how="left")
    out = out.drop(columns=["horse_key_dna"], errors="ignore")

    if "sectional_strength_band" not in out.columns:
        out["sectional_strength_band"] = ""
    if "profile_quality" not in out.columns:
        out["profile_quality"] = ""

    section_band_score = {
        "ELITE": 92,
        "STRONG": 80,
        "ABOVE_AVERAGE": 74,
        "ABOVE AVERAGE": 74,
        "AVERAGE": 55,
        "BELOW_AVERAGE": 38,
        "BELOW AVERAGE": 38,
        "POOR": 25,
    }
    profile_score = {
        "HIGH": 85,
        "MEDIUM": 68,
        "LOW": 48,
        "RATING_ONLY": 35,
        "BACKFILLED_ONLY_LOW_CONFIDENCE": 20,
        "NO_PROFILE": 10,
    }

    out["sectional_fit_score"] = out["sectional_strength_band"].astype(str).str.upper().map(section_band_score).fillna(35)
    out["profile_quality_score"] = out["profile_quality"].astype(str).str.upper().map(profile_score).fillna(35)

    score_cols = [
        "track_fit_score",
        "distance_fit_score",
        "condition_fit_score",
        "barrier_fit_score",
        "jockey_fit_score",
        "trainer_fit_score",
        "class_fit_score",
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
    out["runner_dna_band"] = out["runner_dna_score"].map(band_from_score)
    out["built_at_runner_dna_v2"] = built_at

    out.to_csv(OUT, index=False)

    summary_rows = [
        {"metric": "status", "value": "RUNNER_DNA_V2_BUILT"},
        {"metric": "rows", "value": len(out)},
        {"metric": "with_runner_dna_score", "value": int(out["runner_dna_score"].astype(str).ne("").sum())},
        {"metric": "track_fit_nonzero", "value": int(pd.to_numeric(out["track_fit_starts"], errors="coerce").fillna(0).gt(0).sum())},
        {"metric": "distance_fit_nonzero", "value": int(pd.to_numeric(out["distance_fit_starts"], errors="coerce").fillna(0).gt(0).sum())},
        {"metric": "condition_fit_nonzero", "value": int(pd.to_numeric(out["condition_fit_starts"], errors="coerce").fillna(0).gt(0).sum())},
        {"metric": "barrier_fit_nonzero", "value": int(pd.to_numeric(out["barrier_fit_starts"], errors="coerce").fillna(0).gt(0).sum())},
    ]

    for k, v in out["runner_dna_band"].value_counts().items():
        summary_rows.append({"metric": f"runner_dna_band_{k}", "value": int(v)})

    pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)

    print("[RUNNER_DNA_V2] COMPLETE")
    print(pd.DataFrame(summary_rows).to_string(index=False))
    print(f"out={OUT}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
