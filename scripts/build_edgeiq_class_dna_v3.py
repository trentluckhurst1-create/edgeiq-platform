import pandas as pd
import numpy as np
import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_racingcom_results_warehouse_full_v1.csv"
LIVE = DATA / "edgeiq_live_runner_board_governed_v1.csv"

OUT_ALL = DATA / "edgeiq_class_dna_v3.csv"
OUT_LIVE = DATA / "edgeiq_live_class_dna_v3.csv"
OUT_SUMMARY = DATA / "edgeiq_class_dna_v3_summary.csv"
OUT_JSON = DATA / "edgeiq_class_dna_v3_summary.json"

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

def canon_horse(x):
    if pd.isna(x):
        return ""
    s = str(x).upper().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def class_group(x):
    if pd.isna(x):
        return "UNKNOWN"
    s = str(x).upper().strip()
    s = re.sub(r"\s+", " ", s)

    if s in ["MAIDEN", "MDN"] or "MAIDEN" in s:
        return "MDN"
    if "GROUP 1" in s or s == "G1":
        return "GROUP_1"
    if "GROUP 2" in s or s == "G2":
        return "GROUP_2"
    if "GROUP 3" in s or s == "G3":
        return "GROUP_3"
    if "LISTED" in s:
        return "LISTED"
    if "OPEN" in s:
        return "OPEN"
    if "CLASS 1" in s:
        return "CLASS_1"
    if "CLASS 2" in s:
        return "CLASS_2"
    if "CLASS 3" in s:
        return "CLASS_3"

    bm = re.search(r"(?:BM|BENCHMARK)\s*([0-9]{2,3})", s)
    if bm:
        n = int(bm.group(1))
        known = sorted([int(k.replace("BM","")) for k in CLASS_ORDER if k.startswith("BM")])
        closest = min(known, key=lambda z: abs(z - n))
        return f"BM{closest}"

    if "HANDICAP" in s:
        return "HANDICAP"

    return "UNKNOWN"

def finish_num(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip().upper()
    if s in ["SCR", "LR", "BD", "F", "FF", "DNF", "PU", ""]:
        return np.nan
    m = re.search(r"\d+", s)
    return float(m.group(0)) if m else np.nan

def base_score(starts, wins, places):
    starts = float(starts or 0)
    wins = float(wins or 0)
    places = float(places or 0)
    if starts <= 0:
        return 0
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
    return round(max(0, min(100, 35 + win_pct * 0.45 + place_pct * 0.35 + sample_bonus)), 1)

def score_band(score, starts):
    if starts <= 0 or pd.isna(score):
        return "NO_PROFILE"
    if starts < 2:
        return "LOW_SAMPLE"
    if score >= 82:
        return "ELITE"
    if score >= 70:
        return "STRONG"
    if score >= 58:
        return "POSITIVE"
    if score >= 45:
        return "NEUTRAL"
    if score >= 32:
        return "NEGATIVE"
    return "POOR"

hist = pd.read_csv(SRC, low_memory=False)
hist["horse_canon"] = hist.get("horseName", "").apply(canon_horse)
hist["horse_key_hist"] = hist.get("horseKey", "").astype(str).str.upper().str.strip()
hist["class_group"] = hist["raceClass"].apply(class_group)
hist["class_level"] = hist["class_group"].map(CLASS_ORDER).fillna(0)
hist["finish_num"] = hist["finishPosition"].apply(finish_num)

hist = hist[
    (hist["horse_canon"] != "") &
    (hist["class_group"] != "UNKNOWN") &
    (hist["finish_num"].notna())
].copy()

hist["win"] = (hist["finish_num"] == 1).astype(int)
hist["place"] = (hist["finish_num"] <= 3).astype(int)

exact = hist.groupby(["horse_canon", "class_group"], dropna=False).agg(
    exact_class_starts=("finish_num", "count"),
    exact_class_wins=("win", "sum"),
    exact_class_places=("place", "sum"),
    exact_avg_finish=("finish_num", "mean"),
    class_level=("class_level", "max"),
).reset_index()

exact["exact_class_win_pct"] = np.where(exact["exact_class_starts"] > 0, exact["exact_class_wins"] / exact["exact_class_starts"] * 100, 0)
exact["exact_class_place_pct"] = np.where(exact["exact_class_starts"] > 0, exact["exact_class_places"] / exact["exact_class_starts"] * 100, 0)
exact["exact_class_fit_score"] = exact.apply(lambda r: base_score(r["exact_class_starts"], r["exact_class_wins"], r["exact_class_places"]), axis=1)

career = hist.groupby("horse_canon").agg(
    career_class_starts=("finish_num", "count"),
    career_class_wins=("win", "sum"),
    career_class_places=("place", "sum"),
    career_best_class_level=("class_level", "max"),
    career_avg_class_level=("class_level", "mean"),
    career_min_class_level=("class_level", "min"),
).reset_index()

career["career_class_win_pct"] = np.where(career["career_class_starts"] > 0, career["career_class_wins"] / career["career_class_starts"] * 100, 0)
career["career_class_place_pct"] = np.where(career["career_class_starts"] > 0, career["career_class_places"] / career["career_class_starts"] * 100, 0)
career["career_class_score"] = career.apply(lambda r: base_score(r["career_class_starts"], r["career_class_wins"], r["career_class_places"]), axis=1)

all_out = exact.merge(career, on="horse_canon", how="left")
all_out.to_csv(OUT_ALL, index=False)

live = pd.read_csv(LIVE, low_memory=False)
live["horse_canon_join"] = live["horse"].apply(canon_horse)
live["class_group"] = live["race_class"].apply(class_group)
live["live_class_level"] = live["class_group"].map(CLASS_ORDER).fillna(0)

live_dna = live.merge(
    exact,
    left_on=["horse_canon_join", "class_group"],
    right_on=["horse_canon", "class_group"],
    how="left"
)

live_dna = live_dna.merge(
    career,
    left_on="horse_canon_join",
    right_on="horse_canon",
    how="left",
    suffixes=("", "_career")
)

for c in [
    "exact_class_starts","exact_class_wins","exact_class_places","exact_class_win_pct","exact_class_place_pct","exact_class_fit_score",
    "career_class_starts","career_class_wins","career_class_places","career_class_win_pct","career_class_place_pct","career_class_score",
    "career_best_class_level","career_avg_class_level","career_min_class_level","live_class_level"
]:
    if c in live_dna.columns:
        live_dna[c] = pd.to_numeric(live_dna[c], errors="coerce").fillna(0)

live_dna["class_profile_source"] = np.where(
    live_dna["exact_class_starts"] > 0,
    "EXACT_CLASS",
    np.where(live_dna["career_class_starts"] > 0, "CAREER_CLASS_FALLBACK", "NO_PROFILE")
)

live_dna["class_starts"] = np.where(live_dna["exact_class_starts"] > 0, live_dna["exact_class_starts"], live_dna["career_class_starts"])
live_dna["class_wins"] = np.where(live_dna["exact_class_starts"] > 0, live_dna["exact_class_wins"], live_dna["career_class_wins"])
live_dna["class_places"] = np.where(live_dna["exact_class_starts"] > 0, live_dna["exact_class_places"], live_dna["career_class_places"])
live_dna["class_win_pct"] = np.where(live_dna["exact_class_starts"] > 0, live_dna["exact_class_win_pct"], live_dna["career_class_win_pct"])
live_dna["class_place_pct"] = np.where(live_dna["exact_class_starts"] > 0, live_dna["exact_class_place_pct"], live_dna["career_class_place_pct"])

live_dna["class_level_gap_to_best"] = live_dna["live_class_level"] - live_dna["career_best_class_level"]

live_dna["raw_class_fit_score"] = np.where(
    live_dna["exact_class_starts"] > 0,
    live_dna["exact_class_fit_score"],
    live_dna["career_class_score"]
)

live_dna["class_adjustment"] = np.select(
    [
        live_dna["class_profile_source"].eq("NO_PROFILE"),
        live_dna["class_level_gap_to_best"] >= 15,
        live_dna["class_level_gap_to_best"] >= 8,
        live_dna["class_level_gap_to_best"] <= -10,
        live_dna["class_level_gap_to_best"] <= -5,
    ],
    [0, -16, -9, 8, 5],
    default=0
)

live_dna["class_fit_score"] = (live_dna["raw_class_fit_score"] + live_dna["class_adjustment"]).clip(0, 100).round(1)
live_dna["class_fit_band"] = live_dna.apply(lambda r: score_band(r["class_fit_score"], r["class_starts"]), axis=1)

live_dna["class_movement"] = np.select(
    [
        live_dna["class_profile_source"].eq("NO_PROFILE"),
        live_dna["class_level_gap_to_best"] >= 8,
        live_dna["class_level_gap_to_best"] <= -5,
    ],
    ["UNKNOWN", "CLASS_RISE", "CLASS_DROP"],
    default="CLASS_NEUTRAL"
)

live_dna["class_dna_summary"] = live_dna.apply(
    lambda r: (
        "NO CLASS PROFILE"
        if r["class_profile_source"] == "NO_PROFILE"
        else f'{r["class_fit_band"]}: {int(r["class_starts"])} starts, {int(r["class_wins"])} wins, {int(r["class_places"])} places; {r["class_profile_source"]}; {r["class_movement"]}'
    ),
    axis=1
)

keep_cols = [
    "race_date","track","race_no","horse","horse_key","runner_key","race_class","class_group",
    "class_profile_source","class_starts","class_wins","class_places","class_win_pct","class_place_pct",
    "class_fit_score","class_fit_band","career_best_class_level","career_avg_class_level",
    "live_class_level","class_level_gap_to_best","class_movement","class_dna_summary"
]
keep_cols = [c for c in keep_cols if c in live_dna.columns]
live_dna[keep_cols].to_csv(OUT_LIVE, index=False)

summary_rows = [
    {"metric": "status", "value": "CLASS_DNA_V3_BUILT"},
    {"metric": "historical_rows_used", "value": len(hist)},
    {"metric": "exact_class_profile_rows", "value": len(exact)},
    {"metric": "career_class_profile_rows", "value": len(career)},
    {"metric": "unique_horses", "value": career["horse_canon"].nunique()},
    {"metric": "live_rows", "value": len(live)},
    {"metric": "live_exact_class", "value": int((live_dna["class_profile_source"] == "EXACT_CLASS").sum())},
    {"metric": "live_career_fallback", "value": int((live_dna["class_profile_source"] == "CAREER_CLASS_FALLBACK").sum())},
    {"metric": "live_no_profile", "value": int((live_dna["class_profile_source"] == "NO_PROFILE").sum())},
    {"metric": "live_matched", "value": int((live_dna["class_profile_source"] != "NO_PROFILE").sum())},
    {"metric": "live_unmatched", "value": int((live_dna["class_profile_source"] == "NO_PROFILE").sum())},
    {"metric": "class_rise", "value": int((live_dna["class_movement"] == "CLASS_RISE").sum())},
    {"metric": "class_drop", "value": int((live_dna["class_movement"] == "CLASS_DROP").sum())},
    {"metric": "class_neutral", "value": int((live_dna["class_movement"] == "CLASS_NEUTRAL").sum())},
]
summary = pd.DataFrame(summary_rows)
summary.to_csv(OUT_SUMMARY, index=False)

OUT_JSON.write_text(json.dumps({r["metric"]: r["value"] for r in summary_rows}, indent=2), encoding="utf-8")

print("[CLASS_DNA_V3] COMPLETE")
print(summary.to_string(index=False))
print()
print(live_dna["class_profile_source"].value_counts(dropna=False).to_string())
print()
print(live_dna["class_fit_band"].value_counts(dropna=False).to_string())
print()
print(live_dna["class_movement"].value_counts(dropna=False).to_string())
