from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import re
import subprocess
import sys

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SCRIPTS = ROOT / "scripts"

LIVE_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
RESULTS = DATA / "edgeiq_racingcom_results_warehouse_full_v1.csv"

HORSE_PROFILE_LIVE_V3 = DATA / "edgeiq_live_horse_profile_v3.csv"
HORSE_PROFILE_LIVE_CURRENT = DATA / "edgeiq_live_horse_profile_current.csv"
HORSE_PROFILE_V3 = DATA / "edgeiq_horse_profile_v3.csv"
HORSE_PROFILE_CURRENT = DATA / "edgeiq_horse_profile_current.csv"

LIVE_DISTANCE = DATA / "edgeiq_live_distance_dna_v1.csv"
LIVE_CONDITION = DATA / "edgeiq_live_condition_dna_v1.csv"
LIVE_CLASS = DATA / "edgeiq_live_class_dna_v3.csv"
LIVE_DNA_V62 = DATA / "edgeiq_live_runner_dna_v6_2.csv"
LIVE_DNA_ALIAS = DATA / "edgeiq_runner_dna_v6_2.csv"

SUMMARY = DATA / "edgeiq_live_runner_dna_v6_2_refresh_v1_summary.csv"
DETAIL = DATA / "edgeiq_live_runner_dna_v6_2_refresh_v1_detail.csv"

TRUTHY = {"1", "TRUE", "YES", "Y"}


def safe_text(value: object) -> str:
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return str(value).strip()


def clean_track(value: object) -> str:
    text = safe_text(value).upper()
    text = text.replace("SPORTSBET-", "SPORTSBET ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_horse(value: object) -> str:
    text = safe_text(value).upper()
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"[^A-Z0-9]+", "", text)
    return text


def build_key(frame: pd.DataFrame, horse_col: str = "horse", horse_key_col: str | None = "horse_key") -> pd.Series:
    horse_key_series = frame.get(horse_key_col, pd.Series("", index=frame.index)) if horse_key_col else pd.Series("", index=frame.index)
    cleaned_key = horse_key_series.map(clean_horse)
    fallback = frame.get(horse_col, pd.Series("", index=frame.index)).map(clean_horse)
    cleaned_horse = cleaned_key.where(cleaned_key != "", fallback)
    return (
        frame.get("race_date", pd.Series("", index=frame.index)).map(safe_text).str[:10]
        + "|"
        + frame.get("track", pd.Series("", index=frame.index)).map(clean_track)
        + "|"
        + frame.get("race_no", pd.Series("", index=frame.index)).map(safe_text)
        + "|"
        + cleaned_horse
    )


def truthy(value: object) -> bool:
    return safe_text(value).upper() in TRUTHY


def load_active_universe() -> pd.DataFrame:
    if not LIVE_BOARD.exists():
        raise FileNotFoundError(f"Missing live runner board: {LIVE_BOARD}")
    frame = pd.read_csv(LIVE_BOARD, dtype=str, keep_default_na=False, low_memory=False)
    if "runner_status" in frame.columns:
        frame = frame[frame["runner_status"].astype(str).str.upper().ne("SCRATCHED")].copy()
    if "is_scratched" in frame.columns:
        frame = frame[~frame["is_scratched"].map(truthy)].copy()
    frame["refresh_key"] = build_key(frame)
    return frame


def run_python(script_name: str) -> None:
    script_path = SCRIPTS / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"Missing script: {script_path}")
    print(f"[RUN] {script_name}")
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    if result.returncode != 0:
        raise RuntimeError(f"Script failed: {script_name}")


def band(score: object, starts: object) -> str:
    score_num = pd.to_numeric(pd.Series([score]), errors="coerce").iloc[0]
    starts_num = pd.to_numeric(pd.Series([starts]), errors="coerce").fillna(0).iloc[0]
    if pd.isna(score_num):
        return "NO_PROFILE"
    if starts_num < 2:
        return "LOW_SAMPLE" if starts_num > 0 else "NO_PROFILE"
    if score_num >= 82:
        return "ELITE"
    if score_num >= 70:
        return "STRONG"
    if score_num >= 58:
        return "POSITIVE"
    if score_num >= 45:
        return "NEUTRAL"
    if score_num >= 32:
        return "NEGATIVE"
    return "POOR"


def base_score(starts: float, wins: float, places: float) -> float:
    if starts <= 0:
        return 0.0
    win_pct = wins / starts * 100
    place_pct = places / starts * 100
    if starts >= 8:
        sample_bonus = 8
    elif starts >= 5:
        sample_bonus = 5
    elif starts >= 3:
        sample_bonus = 3
    elif starts >= 2:
        sample_bonus = 1
    else:
        sample_bonus = -8
    return round(max(0.0, min(100.0, 35 + win_pct * 0.45 + place_pct * 0.35 + sample_bonus)), 1)


def class_group(value: object) -> str:
    text = safe_text(value).upper()
    text = re.sub(r"\s+", " ", text)

    if text in {"MAIDEN", "MDN"} or "MAIDEN" in text:
        return "MDN"
    if "GROUP 1" in text or text == "G1":
        return "GROUP_1"
    if "GROUP 2" in text or text == "G2":
        return "GROUP_2"
    if "GROUP 3" in text or text == "G3":
        return "GROUP_3"
    if "LISTED" in text:
        return "LISTED"
    if "OPEN" in text:
        return "OPEN"
    if "CLASS 1" in text:
        return "CLASS_1"
    if "CLASS 2" in text:
        return "CLASS_2"
    if "CLASS 3" in text:
        return "CLASS_3"

    benchmark_match = re.search(r"(?:BM|BENCHMARK)\s*([0-9]{2,3})", text)
    if benchmark_match:
        value_num = int(benchmark_match.group(1))
        known = [52, 56, 58, 62, 64, 66, 70, 74, 78, 84, 90, 100]
        closest = min(known, key=lambda item: abs(item - value_num))
        return f"BM{closest}"

    if "HANDICAP" in text:
        return "HANDICAP"
    return "UNKNOWN"


CLASS_ORDER = {
    "MDN": 10,
    "CLASS_1": 20,
    "CLASS_2": 25,
    "CLASS_3": 30,
    "BM52": 35,
    "BM56": 38,
    "BM58": 40,
    "BM62": 45,
    "BM64": 50,
    "BM66": 55,
    "BM70": 60,
    "BM74": 65,
    "BM78": 70,
    "BM84": 75,
    "BM90": 80,
    "BM100": 85,
    "OPEN": 88,
    "LISTED": 92,
    "GROUP_3": 95,
    "GROUP_2": 97,
    "GROUP_1": 100,
    "HANDICAP": 55,
    "UNKNOWN": 0,
}


def distance_bucket(distance_value: object) -> str:
    distance = pd.to_numeric(pd.Series([distance_value]), errors="coerce").iloc[0]
    if pd.isna(distance):
        return "UNKNOWN"
    distance = float(distance)
    if distance <= 1100:
        return "1000_1100"
    if distance <= 1300:
        return "1200_1300"
    if distance <= 1500:
        return "1301_1500"
    if distance <= 1800:
        return "1501_1800"
    if distance <= 2000:
        return "1801_2000"
    if distance <= 2400:
        return "2001_2400"
    return "2401_PLUS"


def condition_group(condition_value: object, track_value: object) -> str:
    condition = safe_text(condition_value).upper()
    track = clean_track(track_value)
    if "SYNTH" in condition or "SYNTH" in track:
        return "SYNTHETIC"
    if "HEAVY" in condition:
        return "HEAVY"
    if "SOFT" in condition:
        return "SOFT"
    if "GOOD" in condition or "FIRM" in condition or "FAST" in condition:
        return "GOOD"
    return "UNKNOWN"


def prepare_results() -> pd.DataFrame:
    if not RESULTS.exists():
        raise FileNotFoundError(f"Missing historical results source: {RESULTS}")
    results = pd.read_csv(RESULTS, dtype=str, keep_default_na=False, low_memory=False)
    results["horse_match"] = results.get("horseKey", pd.Series("", index=results.index)).map(clean_horse)
    results["horse_match"] = results["horse_match"].where(results["horse_match"] != "", results.get("horseName", pd.Series("", index=results.index)).map(clean_horse))
    results["distance_bucket"] = results.get("distance", pd.Series("", index=results.index)).map(distance_bucket)
    results["condition_group"] = results.apply(lambda row: condition_group(row.get("trackCondition"), row.get("track")), axis=1)
    results["class_group"] = results.get("raceClass", pd.Series("", index=results.index)).map(class_group)
    results["class_level"] = results["class_group"].map(CLASS_ORDER).fillna(0)
    finish = pd.to_numeric(results.get("finishPosition", pd.Series("", index=results.index)), errors="coerce")
    results["is_win"] = finish.eq(1)
    results["is_place"] = finish.between(1, 3, inclusive="both")
    return results


def build_live_distance_from_results(active: pd.DataFrame, results: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    active_small = active[["refresh_key", "runner_key", "race_date", "track", "race_no", "horse", "horse_key", "distance"]].drop_duplicates("refresh_key").copy()
    active_small["horse_match"] = active_small["horse_key"].map(clean_horse).where(active_small["horse_key"].map(clean_horse) != "", active_small["horse"].map(clean_horse))
    active_small["distance_bucket"] = active_small["distance"].map(distance_bucket)

    grouped = (
        results[(results["horse_match"] != "") & (results["distance_bucket"] != "UNKNOWN")]
        .groupby(["horse_match", "distance_bucket"], dropna=False)
        .agg(
            distance_starts=("horse_match", "count"),
            distance_wins=("is_win", "sum"),
            distance_places=("is_place", "sum"),
        )
        .reset_index()
    )

    merged = active_small.merge(grouped, on=["horse_match", "distance_bucket"], how="left")
    for column in ["distance_starts", "distance_wins", "distance_places"]:
        merged[column] = pd.to_numeric(merged[column], errors="coerce").fillna(0)

    merged["distance_win_pct"] = np.where(merged["distance_starts"] > 0, merged["distance_wins"] / merged["distance_starts"] * 100, 0)
    merged["distance_place_pct"] = np.where(merged["distance_starts"] > 0, merged["distance_places"] / merged["distance_starts"] * 100, 0)
    merged["distance_fit_score"] = merged.apply(
        lambda row: base_score(float(row["distance_starts"]), float(row["distance_wins"]), float(row["distance_places"])),
        axis=1,
    )
    merged["distance_fit_band"] = merged.apply(lambda row: band(row.get("distance_fit_score"), row.get("distance_starts")), axis=1)

    def build_summary(row: pd.Series) -> str:
        starts = int(row["distance_starts"])
        wins = int(row["distance_wins"])
        places = int(row["distance_places"])
        fit_band = safe_text(row.get("distance_fit_band"))
        if starts <= 0:
            return "NO DISTANCE PROFILE"
        return f"{fit_band}: {starts} starts, {wins} wins, {places} places at this distance bucket"

    out = pd.DataFrame(
        {
            "race_date": merged["race_date"],
            "track": merged["track"],
            "race_no": merged["race_no"],
            "horse": merged["horse"],
            "horse_key": merged["horse_key"],
            "runner_key": merged["runner_key"],
            "distance": merged["distance"],
            "distance_bucket": merged["distance_bucket"],
            "distance_starts": merged["distance_starts"].astype(float),
            "distance_wins": merged["distance_wins"].astype(float),
            "distance_places": merged["distance_places"].astype(float),
            "distance_win_pct": merged["distance_win_pct"].astype(float),
            "distance_place_pct": merged["distance_place_pct"].astype(float),
            "distance_fit_score": merged["distance_fit_score"].astype(float).round(1),
            "distance_fit_band": merged["distance_fit_band"],
        }
    )

    out["distance_dna_summary"] = merged.apply(build_summary, axis=1)
    out = out.drop_duplicates(subset=["race_date", "track", "race_no", "horse_key", "horse"])
    out.to_csv(LIVE_DISTANCE, index=False)

    stats = {
        "rows": len(out),
        "with_distance_score": int(out["distance_fit_score"].notna().sum()),
    }
    print(f"[WRITE] {LIVE_DISTANCE.name} rows={len(out)}")
    return out, stats


def build_live_condition_from_results(active: pd.DataFrame, results: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    active_small = active[["refresh_key", "runner_key", "race_date", "track", "race_no", "horse", "horse_key", "track_condition"]].copy()
    active_small["horse_match"] = active_small["horse_key"].map(clean_horse).where(active_small["horse_key"].map(clean_horse) != "", active_small["horse"].map(clean_horse))
    active_small["condition_group"] = active_small.apply(lambda row: condition_group(row.get("track_condition"), row.get("track")), axis=1)

    grouped = (
        results[results["horse_match"] != ""]
        .groupby(["horse_match", "condition_group"], dropna=False)
        .agg(
            condition_starts=("horse_match", "count"),
            condition_wins=("is_win", "sum"),
            condition_places=("is_place", "sum"),
        )
        .reset_index()
    )

    merged = active_small.merge(grouped, on=["horse_match", "condition_group"], how="left")
    for column in ["condition_starts", "condition_wins", "condition_places"]:
        merged[column] = pd.to_numeric(merged[column], errors="coerce").fillna(0)

    merged["condition_win_pct"] = np.where(merged["condition_starts"] > 0, merged["condition_wins"] / merged["condition_starts"] * 100, 0)
    merged["condition_place_pct"] = np.where(merged["condition_starts"] > 0, merged["condition_places"] / merged["condition_starts"] * 100, 0)
    merged["condition_fit_score"] = merged.apply(
        lambda row: base_score(float(row["condition_starts"]), float(row["condition_wins"]), float(row["condition_places"])),
        axis=1,
    )
    merged["condition_fit_band"] = merged.apply(lambda row: band(row.get("condition_fit_score"), row.get("condition_starts")), axis=1)

    def build_summary(row: pd.Series) -> str:
        starts = int(row["condition_starts"])
        wins = int(row["condition_wins"])
        places = int(row["condition_places"])
        group = safe_text(row.get("condition_group"))
        fit_band = safe_text(row.get("condition_fit_band"))
        if starts <= 0:
            return "NO CONDITION PROFILE"
        return f"{fit_band}: {starts} starts, {wins} wins, {places} places on {group}"

    out = pd.DataFrame(
        {
            "race_date": merged["race_date"],
            "track": merged["track"],
            "race_no": merged["race_no"],
            "horse": merged["horse"],
            "horse_key": merged["horse_key"],
            "runner_key": merged["runner_key"],
            "track_condition": merged["track_condition"],
            "condition_group": merged["condition_group"],
            "condition_starts": merged["condition_starts"].astype(float),
            "condition_wins": merged["condition_wins"].astype(float),
            "condition_places": merged["condition_places"].astype(float),
            "condition_win_pct": merged["condition_win_pct"].astype(float),
            "condition_place_pct": merged["condition_place_pct"].astype(float),
            "condition_fit_score": merged["condition_fit_score"].astype(float).round(1),
            "condition_fit_band": merged["condition_fit_band"],
        }
    )
    out["condition_dna_summary"] = merged.apply(build_summary, axis=1)
    out = out.drop_duplicates(subset=["race_date", "track", "race_no", "horse_key", "horse"])
    out.to_csv(LIVE_CONDITION, index=False)

    stats = {
        "rows": len(out),
        "with_condition_score": int((out["condition_starts"] > 0).sum()),
    }
    print(f"[WRITE] {LIVE_CONDITION.name} rows={len(out)}")
    return out, stats


def build_live_class_from_results(active: pd.DataFrame, results: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    hist = results[
        (results["horse_match"] != "")
        & (results["class_group"] != "UNKNOWN")
    ].copy()

    exact = (
        hist.groupby(["horse_match", "class_group"], dropna=False)
        .agg(
            exact_class_starts=("horse_match", "count"),
            exact_class_wins=("is_win", "sum"),
            exact_class_places=("is_place", "sum"),
            class_level=("class_level", "max"),
        )
        .reset_index()
    )
    exact["exact_class_win_pct"] = np.where(exact["exact_class_starts"] > 0, exact["exact_class_wins"] / exact["exact_class_starts"] * 100, 0)
    exact["exact_class_place_pct"] = np.where(exact["exact_class_starts"] > 0, exact["exact_class_places"] / exact["exact_class_starts"] * 100, 0)
    exact["exact_class_fit_score"] = exact.apply(
        lambda row: base_score(float(row["exact_class_starts"]), float(row["exact_class_wins"]), float(row["exact_class_places"])),
        axis=1,
    )

    career = (
        hist.groupby(["horse_match"], dropna=False)
        .agg(
            career_class_starts=("horse_match", "count"),
            career_class_wins=("is_win", "sum"),
            career_class_places=("is_place", "sum"),
            career_best_class_level=("class_level", "max"),
            career_avg_class_level=("class_level", "mean"),
            career_min_class_level=("class_level", "min"),
        )
        .reset_index()
    )
    career["career_class_win_pct"] = np.where(career["career_class_starts"] > 0, career["career_class_wins"] / career["career_class_starts"] * 100, 0)
    career["career_class_place_pct"] = np.where(career["career_class_starts"] > 0, career["career_class_places"] / career["career_class_starts"] * 100, 0)
    career["career_class_score"] = career.apply(
        lambda row: base_score(float(row["career_class_starts"]), float(row["career_class_wins"]), float(row["career_class_places"])),
        axis=1,
    )

    active_small = active[["refresh_key", "runner_key", "race_date", "track", "race_no", "horse", "horse_key", "race_class"]].copy()
    active_small["horse_match"] = active_small["horse_key"].map(clean_horse).where(active_small["horse_key"].map(clean_horse) != "", active_small["horse"].map(clean_horse))
    active_small["class_group"] = active_small["race_class"].map(class_group)
    active_small["live_class_level"] = active_small["class_group"].map(CLASS_ORDER).fillna(0)

    merged = active_small.merge(exact, on=["horse_match", "class_group"], how="left")
    merged = merged.merge(career, on=["horse_match"], how="left", suffixes=("", "_career"))

    numeric_cols = [
        "exact_class_starts",
        "exact_class_wins",
        "exact_class_places",
        "exact_class_win_pct",
        "exact_class_place_pct",
        "exact_class_fit_score",
        "career_class_starts",
        "career_class_wins",
        "career_class_places",
        "career_class_win_pct",
        "career_class_place_pct",
        "career_class_score",
        "career_best_class_level",
        "career_avg_class_level",
        "career_min_class_level",
        "live_class_level",
    ]
    for column in numeric_cols:
        merged[column] = pd.to_numeric(merged.get(column, pd.Series("", index=merged.index)), errors="coerce").fillna(0)

    merged["class_profile_source"] = np.where(
        merged["exact_class_starts"] > 0,
        "EXACT_CLASS",
        np.where(merged["career_class_starts"] > 0, "CAREER_CLASS_FALLBACK", "NO_PROFILE"),
    )
    merged["class_starts"] = np.where(merged["exact_class_starts"] > 0, merged["exact_class_starts"], merged["career_class_starts"])
    merged["class_wins"] = np.where(merged["exact_class_starts"] > 0, merged["exact_class_wins"], merged["career_class_wins"])
    merged["class_places"] = np.where(merged["exact_class_starts"] > 0, merged["exact_class_places"], merged["career_class_places"])
    merged["class_win_pct"] = np.where(merged["exact_class_starts"] > 0, merged["exact_class_win_pct"], merged["career_class_win_pct"])
    merged["class_place_pct"] = np.where(merged["exact_class_starts"] > 0, merged["exact_class_place_pct"], merged["career_class_place_pct"])
    merged["class_level_gap_to_best"] = merged["live_class_level"] - merged["career_best_class_level"]
    merged["raw_class_fit_score"] = np.where(merged["exact_class_starts"] > 0, merged["exact_class_fit_score"], merged["career_class_score"])
    merged["class_adjustment"] = np.select(
        [
            merged["class_profile_source"].eq("NO_PROFILE"),
            merged["class_level_gap_to_best"] >= 15,
            merged["class_level_gap_to_best"] >= 8,
            merged["class_level_gap_to_best"] <= -10,
            merged["class_level_gap_to_best"] <= -5,
        ],
        [0, -16, -9, 8, 5],
        default=0,
    )
    merged["class_fit_score"] = (merged["raw_class_fit_score"] + merged["class_adjustment"]).clip(0, 100).round(1)
    merged["class_fit_band"] = merged.apply(lambda row: band(row.get("class_fit_score"), row.get("class_starts")), axis=1)
    merged["class_movement"] = np.select(
        [
            merged["class_profile_source"].eq("NO_PROFILE"),
            merged["class_level_gap_to_best"] >= 8,
            merged["class_level_gap_to_best"] <= -5,
        ],
        ["UNKNOWN", "CLASS_RISE", "CLASS_DROP"],
        default="CLASS_NEUTRAL",
    )
    merged["class_dna_summary"] = merged.apply(
        lambda row: (
            "NO CLASS PROFILE"
            if row["class_profile_source"] == "NO_PROFILE"
            else f'{row["class_fit_band"]}: {int(row["class_starts"])} starts, {int(row["class_wins"])} wins, {int(row["class_places"])} places; {row["class_profile_source"]}; {row["class_movement"]}'
        ),
        axis=1,
    )

    out = pd.DataFrame(
        {
            "race_date": merged["race_date"],
            "track": merged["track"],
            "race_no": merged["race_no"],
            "horse": merged["horse"],
            "horse_key": merged["horse_key"],
            "runner_key": merged["runner_key"],
            "race_class": merged["race_class"],
            "class_group": merged["class_group"],
            "class_profile_source": merged["class_profile_source"],
            "class_starts": merged["class_starts"].astype(float),
            "class_wins": merged["class_wins"].astype(float),
            "class_places": merged["class_places"].astype(float),
            "class_win_pct": merged["class_win_pct"].astype(float),
            "class_place_pct": merged["class_place_pct"].astype(float),
            "class_fit_score": merged["class_fit_score"].astype(float).round(1),
            "class_fit_band": merged["class_fit_band"],
            "career_best_class_level": merged["career_best_class_level"].astype(float),
            "career_avg_class_level": merged["career_avg_class_level"].astype(float),
            "live_class_level": merged["live_class_level"].astype(float),
            "class_level_gap_to_best": merged["class_level_gap_to_best"].astype(float),
            "class_movement": merged["class_movement"],
            "class_dna_summary": merged["class_dna_summary"],
        }
    )
    out = out.drop_duplicates(subset=["race_date", "track", "race_no", "horse_key", "horse"])
    out.to_csv(LIVE_CLASS, index=False)
    stats = {
        "rows": len(out),
        "with_class_score": int((pd.to_numeric(out["class_starts"], errors="coerce") > 0).sum()),
    }
    print(f"[WRITE] {LIVE_CLASS.name} rows={len(out)}")
    return out, stats


def tj_score_to_100(value: object) -> float | None:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return None
    return max(0.0, min(100.0, 50 + float(numeric) * 25))


def dna_band(score: object) -> str:
    numeric = pd.to_numeric(pd.Series([score]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "NO_PROFILE"
    if numeric >= 85:
        return "ELITE"
    if numeric >= 72:
        return "STRONG"
    if numeric >= 58:
        return "POSITIVE"
    if numeric >= 45:
        return "NEUTRAL"
    if numeric >= 30:
        return "NEGATIVE"
    return "POOR"


def build_live_runner_dna_v62(active: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    if not LIVE_DISTANCE.exists() or not LIVE_CONDITION.exists() or not LIVE_CLASS.exists():
        raise FileNotFoundError("One or more live DNA factor feeds are missing.")

    tj = pd.read_csv(DATA / "edgeiq_live_trainer_jockey_factor_feed_v3.csv", dtype=str, keep_default_na=False, low_memory=False)
    dist = pd.read_csv(LIVE_DISTANCE, dtype=str, keep_default_na=False, low_memory=False)
    cond = pd.read_csv(LIVE_CONDITION, dtype=str, keep_default_na=False, low_memory=False)
    cls = pd.read_csv(LIVE_CLASS, dtype=str, keep_default_na=False, low_memory=False)

    for frame in [tj, dist, cond, cls]:
        frame["refresh_key"] = build_key(frame)

    keep_live_cols = [
        "race_date",
        "day_bucket",
        "meeting_type",
        "meeting_status",
        "dashboard_ready",
        "track",
        "race_no",
        "race_key",
        "meeting_key",
        "runner_key",
        "source",
        "terminal_scope",
        "horse",
        "horse_key",
        "horse_no",
        "saddlecloth",
        "barrier",
        "jockey",
        "trainer",
        "race_time",
        "distance",
        "race_class",
        "track_condition",
        "rail_position",
        "live_price",
        "tab_fixed_win",
        "tab_fixed_place",
        "tab_fixed_betting_status",
        "tab_tote_win",
        "tab_tote_place",
        "tab_tote_betting_status",
        "tab_live_price_source",
        "live_price_source",
        "projected_rating_V6_1_RESEARCH",
        "projection_gap_V6_1_RESEARCH",
        "projection_band_V6_1_RESEARCH",
        "V6_1_RESEARCH_probability",
        "V6_1_RESEARCH_fair_price",
        "V6_1_RESEARCH_price_status",
        "V6_1_RESEARCH_price_bucket",
        "V6_1_RESEARCH_price_rank",
        "win_pct",
        "fair_price",
        "rated_price",
        "ui_fair_price",
        "edge_pct",
        "ui_edge_pct",
        "execution_action",
        "display_source",
        "display_decision",
        "display_edge_pct",
        "display_live_price",
        "display_fair_price",
        "run_style",
        "speed_map_bucket",
        "settling_band",
        "map_x_pct",
        "map_y_px",
        "early_speed_rating",
        "early_speed_band",
        "projected_spd",
    ]
    active_base = active[[column for column in keep_live_cols if column in active.columns] + ["refresh_key"]].copy()

    dna = active_base.merge(
        dist[["refresh_key", "distance_fit_score", "distance_fit_band", "distance_starts", "distance_wins", "distance_places", "distance_dna_summary"]].drop_duplicates("refresh_key"),
        on="refresh_key",
        how="left",
    )
    dna = dna.merge(
        cond[["refresh_key", "condition_fit_score", "condition_fit_band", "condition_starts", "condition_wins", "condition_places", "condition_dna_summary"]].drop_duplicates("refresh_key"),
        on="refresh_key",
        how="left",
    )
    dna = dna.merge(
        cls[["refresh_key", "class_fit_score", "class_fit_band", "class_starts", "class_wins", "class_places", "class_profile_source", "class_movement", "class_dna_summary"]].drop_duplicates("refresh_key"),
        on="refresh_key",
        how="left",
    )

    tj_keep = [
        "refresh_key",
        "trainer_factor_score_v1",
        "jockey_factor_score_v1",
        "combo_factor_score_v1",
        "trainer_jockey_blend_score_v3",
        "trainer_factor_band_v1",
        "jockey_factor_band_v1",
        "combo_factor_band_v1",
        "trainer_jockey_blend_band_v3",
        "trainer_factor_matched_v3",
        "jockey_factor_matched_v3",
        "combo_factor_matched_v3",
        "tj_factor_verdict_v3",
    ]
    dna = dna.merge(
        tj[[column for column in tj_keep if column in tj.columns]].drop_duplicates("refresh_key"),
        on="refresh_key",
        how="left",
    )

    dna["trainer_score"] = dna.get("trainer_factor_score_v1", pd.Series("", index=dna.index)).map(tj_score_to_100)
    dna["jockey_score"] = dna.get("jockey_factor_score_v1", pd.Series("", index=dna.index)).map(tj_score_to_100)
    dna["combo_score"] = dna.get("combo_factor_score_v1", pd.Series("", index=dna.index)).map(tj_score_to_100)
    dna["tj_blend_score"] = dna.get("trainer_jockey_blend_score_v3", pd.Series("", index=dna.index)).map(tj_score_to_100)

    weighted_columns = {
        "distance_fit_score": 1.00,
        "condition_fit_score": 1.00,
        "class_fit_score": 1.00,
        "trainer_score": 0.30,
        "jockey_score": 0.30,
        "combo_score": 0.40,
    }

    for column in weighted_columns:
        dna[column] = pd.to_numeric(dna.get(column, pd.Series("", index=dna.index)), errors="coerce")

    dna["dna_v6_2_component_count"] = dna[list(weighted_columns.keys())].notna().sum(axis=1)

    weighted_sum = pd.Series(0.0, index=dna.index)
    weight_sum = pd.Series(0.0, index=dna.index)
    for column, weight in weighted_columns.items():
        valid = dna[column].notna()
        weighted_sum.loc[valid] += dna.loc[valid, column] * weight
        weight_sum.loc[valid] += weight

    dna["dna_v6_2_score"] = np.where(weight_sum > 0, (weighted_sum / weight_sum).round(1), np.nan)
    dna["dna_v6_2_band"] = dna["dna_v6_2_score"].map(dna_band)

    def factor_series(row: pd.Series) -> list[tuple[str, float]]:
        factors = [
            ("DISTANCE", row.get("distance_fit_score")),
            ("CONDITION", row.get("condition_fit_score")),
            ("CLASS", row.get("class_fit_score")),
            ("TRAINER", row.get("trainer_score")),
            ("JOCKEY", row.get("jockey_score")),
            ("COMBO", row.get("combo_score")),
        ]
        usable: list[tuple[str, float]] = []
        for name, value in factors:
            numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
            if not pd.isna(numeric):
                usable.append((name, round(float(numeric), 1)))
        return usable

    strongest_factor = []
    strongest_value = []
    weakest_factor = []
    weakest_value = []
    narratives = []

    for _, row in dna.iterrows():
        usable = factor_series(row)
        if not usable:
            strongest_factor.append("UNKNOWN")
            strongest_value.append(0.0)
            weakest_factor.append("UNKNOWN")
            weakest_value.append(0.0)
            narratives.append("Limited DNA evidence available.")
            continue
        ordered = sorted(usable, key=lambda item: item[1])
        weak_name, weak_score = ordered[0]
        strong_name, strong_score = ordered[-1]
        strongest_factor.append(strong_name)
        strongest_value.append(strong_score)
        weakest_factor.append(weak_name)
        weakest_value.append(weak_score)

        notes: list[str] = []
        if safe_text(row.get("distance_fit_band")) in {"ELITE", "STRONG"}:
            notes.append("Strong distance profile")
        if safe_text(row.get("condition_fit_band")) in {"ELITE", "STRONG"}:
            notes.append("Strong condition profile")
        if safe_text(row.get("class_movement")) == "CLASS_DROP":
            notes.append("Class drop positive")
        elif safe_text(row.get("class_movement")) == "CLASS_RISE":
            notes.append("Class rise risk")
        if safe_text(row.get("trainer_jockey_blend_band_v3")) == "ELITE":
            notes.append("Elite trainer-jockey edge")
        elif safe_text(row.get("trainer_jockey_blend_band_v3")) in {"POSITIVE", "STRONG"}:
            notes.append("Trainer-jockey edge positive")
        if not notes:
            notes.append("DNA driven by current fit profiles")
        narratives.append(". ".join(notes[:4]) + ".")

    dna["strongest_factor_v6_2"] = strongest_factor
    dna["strongest_factor_score_v6_2"] = strongest_value
    dna["weakest_factor_v6_2"] = weakest_factor
    dna["weakest_factor_score_v6_2"] = weakest_value
    dna["runner_dna_v6_2_narrative"] = narratives
    dna["runner_dna_v6_2_rank_in_race"] = (
        pd.to_numeric(dna["dna_v6_2_score"], errors="coerce")
        .groupby([dna["race_date"], dna["track"], dna["race_no"]])
        .rank(method="first", ascending=False)
    )

    dna["built_at_runner_dna_v6_2_refresh_v1"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    dna = dna.drop_duplicates(subset=["refresh_key"], keep="first")
    dna = dna.drop(columns=["refresh_key"], errors="ignore")
    dna.to_csv(LIVE_DNA_V62, index=False)
    stats = {
        "rows": len(dna),
        "with_dna_score": int(pd.to_numeric(dna["dna_v6_2_score"], errors="coerce").notna().sum()),
    }
    print(f"[WRITE] {LIVE_DNA_V62.name} rows={len(dna)}")
    return dna, stats


def write_summary(step_rows: list[dict[str, object]]) -> None:
    pd.DataFrame(step_rows).to_csv(DETAIL, index=False)

    summary_rows = [
        {"metric": "status", "value": "EDGEIQ_LIVE_RUNNER_DNA_V6_2_REFRESH_V1_BUILT"},
        {"metric": "active_universe_rows", "value": next((row["value"] for row in step_rows if row["metric"] == "active_universe_rows"), "")},
        {"metric": "live_distance_rows", "value": next((row["value"] for row in step_rows if row["metric"] == "live_distance_rows"), "")},
        {"metric": "live_condition_rows", "value": next((row["value"] for row in step_rows if row["metric"] == "live_condition_rows"), "")},
        {"metric": "live_class_rows_after_filter", "value": next((row["value"] for row in step_rows if row["metric"] == "live_class_rows_after_filter"), "")},
        {"metric": "live_runner_dna_v62_rows_after_filter", "value": next((row["value"] for row in step_rows if row["metric"] == "live_runner_dna_v62_rows_after_filter"), "")},
        {"metric": "dna_alias_synced", "value": "YES" if LIVE_DNA_ALIAS.exists() else "NO"},
        {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat(timespec="seconds")},
    ]
    pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)


def main() -> None:
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    active = load_active_universe()
    step_rows: list[dict[str, object]] = [{"metric": "active_universe_rows", "value": len(active), "built_at": built_at}]
    results = prepare_results()
    run_python("build_edgeiq_live_trainer_jockey_factor_feed_v3.py")

    live_distance, live_distance_stats = build_live_distance_from_results(active, results)
    step_rows.append({"metric": "live_distance_rows", "value": len(live_distance), "built_at": built_at})
    step_rows.append({"metric": "live_distance_rows_with_score", "value": live_distance_stats["with_distance_score"], "built_at": built_at})

    live_condition, live_condition_stats = build_live_condition_from_results(active, results)
    step_rows.append({"metric": "live_condition_rows", "value": len(live_condition), "built_at": built_at})
    step_rows.append({"metric": "live_condition_rows_with_score", "value": live_condition_stats["with_condition_score"], "built_at": built_at})

    live_class, live_class_stats = build_live_class_from_results(active, results)
    step_rows.append({"metric": "live_class_rows_after_filter", "value": len(live_class), "built_at": built_at})
    step_rows.append({"metric": "live_class_rows_with_score", "value": live_class_stats["with_class_score"], "built_at": built_at})

    live_dna, live_dna_stats = build_live_runner_dna_v62(active)
    step_rows.append({"metric": "live_runner_dna_v62_rows_after_filter", "value": len(live_dna), "built_at": built_at})
    step_rows.append({"metric": "live_runner_dna_v62_rows_with_score", "value": live_dna_stats["with_dna_score"], "built_at": built_at})

    LIVE_DNA_ALIAS.write_bytes(LIVE_DNA_V62.read_bytes())
    step_rows.append({"metric": "dna_alias_synced", "value": "YES", "built_at": built_at})

    write_summary(step_rows)

    print("[EDGEIQ_LIVE_RUNNER_DNA_V6_2_REFRESH_V1] COMPLETE")
    print(pd.DataFrame(step_rows).to_string(index=False))
    print(f"detail={DETAIL}")
    print(f"summary={SUMMARY}")


if __name__ == "__main__":
    main()
