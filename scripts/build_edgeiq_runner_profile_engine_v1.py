import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_runner_profile_engine_v1.csv"
SUMMARY = DATA / "edgeiq_runner_profile_engine_v1_summary.csv"

def read_csv(name):
    path = DATA / name
    if not path.exists():
        print(f"[WARN] missing {name}")
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str).fillna("")

def norm(s):
    return str(s).strip().upper()

def first_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

def safe_float(v):
    try:
        return float(v)
    except:
        return None

print("[RUNNER_PROFILE_ENGINE_V1] START")

live = read_csv("edgeiq_live_runner_board_v1.csv")
dna = read_csv("edgeiq_runner_dna_v6_2.csv")
hist = read_csv("edgeiq_results_warehouse_full_v1.csv")

if live.empty:
    raise SystemExit("[FAIL] edgeiq_live_runner_board_v1.csv missing/empty")

horse_col_live = first_col(live, ["horse", "runner", "runner_name"])
track_col_live = first_col(live, ["track"])
race_col_live = first_col(live, ["race_no", "race_number"])

horse_col_hist = first_col(hist, ["horse", "runner", "runner_name"])
track_col_hist = first_col(hist, ["track"])
dist_col_hist = first_col(hist, ["distance", "distance_m"])
cond_col_hist = first_col(hist, ["condition", "track_condition"])
class_col_hist = first_col(hist, ["race_class_clean", "race_class", "class"])
finish_col_hist = first_col(hist, ["finish_position", "finish", "placing", "position"])

horse_col_dna = first_col(dna, ["horse", "runner", "runner_name"])

live["_horse_key"] = live[horse_col_live].map(norm)

if not dna.empty and horse_col_dna:
    dna["_horse_key"] = dna[horse_col_dna].map(norm)
else:
    dna["_horse_key"] = ""

rows = []

for _, r in live.iterrows():
    horse_key = r["_horse_key"]
    horse = r.get(horse_col_live, "")
    track = r.get(track_col_live, "")
    race_no = r.get(race_col_live, "")

    h = hist[hist[horse_col_hist].map(norm) == horse_key].copy() if not hist.empty and horse_col_hist else pd.DataFrame()

    starts = len(h)
    wins = 0
    places = 0

    if not h.empty and finish_col_hist:
        finish_vals = h[finish_col_hist].astype(str).str.extract(r"(\d+)")[0]
        finish_nums = pd.to_numeric(finish_vals, errors="coerce")
        wins = int((finish_nums == 1).sum())
        places = int((finish_nums <= 3).sum())

    win_pct = round((wins / starts) * 100, 1) if starts else ""
    place_pct = round((places / starts) * 100, 1) if starts else ""

    distance_profile = "NO PROFILE"
    condition_profile = "NO PROFILE"
    track_profile = "NO PROFILE"
    class_profile = "NO PROFILE"

    if not h.empty:
        if dist_col_hist:
            distance_profile = h[dist_col_hist].astype(str).mode().iloc[0] if not h[dist_col_hist].empty else "NO PROFILE"
        if cond_col_hist:
            condition_profile = h[cond_col_hist].astype(str).mode().iloc[0] if not h[cond_col_hist].empty else "NO PROFILE"
        if track_col_hist:
            track_profile = h[track_col_hist].astype(str).mode().iloc[0] if not h[track_col_hist].empty else "NO PROFILE"
        if class_col_hist:
            class_profile = h[class_col_hist].astype(str).mode().iloc[0] if not h[class_col_hist].empty else "NO PROFILE"

    dna_match = dna[dna["_horse_key"] == horse_key].head(1) if not dna.empty else pd.DataFrame()

    dna_score = ""
    dna_band = ""
    dna_narrative = ""

    for c in ["dna_v6_2_score", "dna_score", "runner_dna_score"]:
        if not dna_match.empty and c in dna_match.columns:
            dna_score = dna_match.iloc[0][c]
            break

    for c in ["dna_v6_2_band", "dna_band", "runner_dna_band"]:
        if not dna_match.empty and c in dna_match.columns:
            dna_band = dna_match.iloc[0][c]
            break

    for c in ["dna_v6_2_narrative", "dna_narrative", "narrative"]:
        if not dna_match.empty and c in dna_match.columns:
            dna_narrative = dna_match.iloc[0][c]
            break

    if starts == 0:
        archetype = "Limited Profile"
    elif wins >= 3 and place_pct != "" and place_pct >= 50:
        archetype = "Proven Performer"
    elif starts >= 10 and wins == 0:
        archetype = "Exposed Maiden"
    elif starts <= 3:
        archetype = "Lightly Raced"
    elif place_pct != "" and place_pct >= 45:
        archetype = "Consistent Contender"
    else:
        archetype = "Established Runner"

    profile_summary = (
        f"{horse} has {starts} historical starts in the EDGEiQ warehouse"
        if starts else
        f"{horse} has limited historical profile data available."
    )

    rows.append({
        "track": track,
        "race_no": race_no,
        "horse": horse,
        "runner_key": horse_key,
        "horse_archetype": archetype,
        "career_starts": starts,
        "career_wins": wins,
        "career_places": places,
        "career_win_pct": win_pct,
        "career_place_pct": place_pct,
        "most_common_distance": distance_profile,
        "most_common_condition": condition_profile,
        "most_common_track": track_profile,
        "most_common_class": class_profile,
        "dna_score": dna_score,
        "dna_band": dna_band,
        "dna_narrative": dna_narrative,
        "profile_summary": profile_summary,
        "built_at": datetime.now(timezone.utc).isoformat()
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "RUNNER_PROFILE_ENGINE_V1_BUILT",
    "rows": len(out),
    "with_historical_profile": int((out["career_starts"].astype(int) > 0).sum()),
    "without_historical_profile": int((out["career_starts"].astype(int) == 0).sum()),
    "with_dna_score": int((out["dna_score"].astype(str).str.strip() != "").sum()),
    "unique_tracks": out["track"].nunique(),
    "built_at": datetime.now(timezone.utc).isoformat()
}])

summary.to_csv(SUMMARY, index=False)

print("[RUNNER_PROFILE_ENGINE_V1] COMPLETE")
print(summary.to_string(index=False))
print(f"out={OUT}")
print(f"summary={SUMMARY}")
