import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_runner_profile_engine_v1_1.csv"
SUMMARY = DATA / "edgeiq_runner_profile_engine_v1_1_summary.csv"

def read_csv(name):
    path = DATA / name
    if not path.exists():
        print(f"[WARN] missing {name}")
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str).fillna("")

def norm(v):
    return str(v).strip().upper()

def pick(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

def to_num(v, default=0.0):
    try:
        if str(v).strip() == "":
            return default
        return float(v)
    except:
        return default

def best_context(rows, keywords):
    if rows.empty:
        return pd.Series(dtype=str)

    x = rows.copy()
    blob = (
        x.get("context_type", "").astype(str) + " " +
        x.get("context_value", "").astype(str) + " " +
        x.get("signal", "").astype(str) + " " +
        x.get("insight", "").astype(str)
    ).str.upper()

    mask = False
    for k in keywords:
        mask = mask | blob.str.contains(k.upper(), regex=False)

    y = x[mask].copy()
    if y.empty:
        return pd.Series(dtype=str)

    y["_starts_num"] = y.get("starts", "0").map(to_num)
    y["_win_pct_num"] = y.get("win_pct", "0").map(to_num)
    y["_place_pct_num"] = y.get("place_pct", "0").map(to_num)

    y = y.sort_values(
        ["_starts_num", "_win_pct_num", "_place_pct_num"],
        ascending=[False, False, False]
    )

    return y.iloc[0]

def context_label(row):
    if row is None or len(row) == 0:
        return "NO PROFILE"

    cv = str(row.get("context_value", "")).strip()
    ct = str(row.get("context_type", "")).strip()
    sig = str(row.get("signal", "")).strip()
    starts = str(row.get("starts", "")).strip()
    win_pct = str(row.get("win_pct", "")).strip()
    place_pct = str(row.get("place_pct", "")).strip()

    base = cv if cv else ct if ct else sig if sig else "PROFILE"
    detail = []

    if starts:
        detail.append(f"{starts} starts")
    if win_pct:
        detail.append(f"{win_pct}% win")
    if place_pct:
        detail.append(f"{place_pct}% place")

    if detail:
        return f"{base} ({', '.join(detail)})"
    return base

print("[RUNNER_PROFILE_ENGINE_V1_1] START")

live = read_csv("edgeiq_live_runner_board_v1.csv")
dna = read_csv("edgeiq_runner_dna_v6_2.csv")
ctx = read_csv("edgeiq_context_warehouse_v2_graphql.csv")

if live.empty:
    raise SystemExit("[FAIL] edgeiq_live_runner_board_v1.csv missing/empty")

if ctx.empty:
    raise SystemExit("[FAIL] edgeiq_context_warehouse_v2_graphql.csv missing/empty")

horse_col_live = pick(live, ["horse", "runner", "runner_name"])
track_col_live = pick(live, ["track"])
race_col_live = pick(live, ["race_no", "race_number"])
horse_col_dna = pick(dna, ["horse", "runner", "runner_name"])

live["_runner_key"] = live[horse_col_live].map(norm)

if not dna.empty and horse_col_dna:
    dna["_runner_key"] = dna[horse_col_dna].map(norm)

ctx["_entity_key"] = ctx["entity_name"].map(norm)
ctx["_entity_type_key"] = ctx["entity_type"].map(norm)

runner_ctx = ctx[
    ctx["_entity_type_key"].str.contains("RUNNER", na=False) |
    ctx["_entity_type_key"].str.contains("HORSE", na=False)
].copy()

rows = []

for _, r in live.iterrows():
    horse = r.get(horse_col_live, "")
    runner_key = r["_runner_key"]
    track = r.get(track_col_live, "")
    race_no = r.get(race_col_live, "")

    cr = runner_ctx[runner_ctx["_entity_key"] == runner_key].copy()

    career = best_context(cr, ["CAREER", "OVERALL", "RUNNER"])
    distance = best_context(cr, ["DISTANCE", "DIST"])
    track_profile = best_context(cr, ["TRACK"])
    condition = best_context(cr, ["CONDITION", "GOOD", "SOFT", "HEAVY", "FIRM", "SYNTHETIC"])
    class_profile = best_context(cr, ["CLASS", "GRADE", "BM", "MAIDEN", "MDN"])

    starts = int(to_num(career.get("starts", 0), 0)) if len(career) else 0
    wins = int(to_num(career.get("wins", 0), 0)) if len(career) else 0
    places = int(to_num(career.get("places", 0), 0)) if len(career) else 0
    win_pct = career.get("win_pct", "") if len(career) else ""
    place_pct = career.get("place_pct", "") if len(career) else ""

    dna_match = dna[dna["_runner_key"] == runner_key].head(1) if not dna.empty and "_runner_key" in dna.columns else pd.DataFrame()

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
    elif wins >= 3 and to_num(place_pct, 0) >= 50:
        archetype = "Proven Performer"
    elif starts >= 10 and wins == 0:
        archetype = "Exposed Maiden"
    elif starts <= 3:
        archetype = "Lightly Raced"
    elif to_num(place_pct, 0) >= 45:
        archetype = "Consistent Contender"
    else:
        archetype = "Established Runner"

    profile_strength = "LOW"
    if starts >= 10:
        profile_strength = "HIGH"
    elif starts >= 4:
        profile_strength = "MEDIUM"

    if starts:
        summary = f"{horse} has a {starts}-start EDGEiQ profile with {wins} wins and {places} placings."
    else:
        summary = f"{horse} has limited historical profile data available."

    rows.append({
        "track": track,
        "race_no": race_no,
        "horse": horse,
        "runner_key": runner_key,
        "horse_archetype": archetype,
        "profile_strength": profile_strength,
        "career_starts": starts,
        "career_wins": wins,
        "career_places": places,
        "career_win_pct": win_pct,
        "career_place_pct": place_pct,
        "distance_profile": context_label(distance),
        "track_profile": context_label(track_profile),
        "condition_profile": context_label(condition),
        "class_profile": context_label(class_profile),
        "profile_context_rows": len(cr),
        "dna_score": dna_score,
        "dna_band": dna_band,
        "dna_narrative": dna_narrative,
        "profile_summary": summary,
        "built_at": datetime.now(timezone.utc).isoformat()
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "RUNNER_PROFILE_ENGINE_V1_1_BUILT",
    "rows": len(out),
    "with_context_profile": int((out["profile_context_rows"].astype(int) > 0).sum()),
    "without_context_profile": int((out["profile_context_rows"].astype(int) == 0).sum()),
    "with_career_starts": int((out["career_starts"].astype(int) > 0).sum()),
    "with_dna_score": int((out["dna_score"].astype(str).str.strip() != "").sum()),
    "high_profile_strength": int((out["profile_strength"] == "HIGH").sum()),
    "medium_profile_strength": int((out["profile_strength"] == "MEDIUM").sum()),
    "low_profile_strength": int((out["profile_strength"] == "LOW").sum()),
    "unique_tracks": out["track"].nunique(),
    "built_at": datetime.now(timezone.utc).isoformat()
}])

summary.to_csv(SUMMARY, index=False)

print("[RUNNER_PROFILE_ENGINE_V1_1] COMPLETE")
print(summary.to_string(index=False))
print(f"out={OUT}")
print(f"summary={SUMMARY}")
