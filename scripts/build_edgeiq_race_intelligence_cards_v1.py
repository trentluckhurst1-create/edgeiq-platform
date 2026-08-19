from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(".")
DATA = ROOT / "public" / "data"

RUNNER = DATA / "edgeiq_live_runner_board_v1.csv"
BETQ = DATA / "edgeiq_live_bet_quality_v1_1.csv"
RELIABILITY = DATA / "edgeiq_live_race_reliability_v1_feed.csv"
SPEED = DATA / "edgeiq_real_speed_map_positions.csv"

OUT = DATA / "edgeiq_race_intelligence_cards_v1.csv"
SUMMARY = DATA / "edgeiq_race_intelligence_cards_v1_summary.csv"

def read(path):
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, low_memory=False)

def text(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def num_series(s):
    return pd.to_numeric(s, errors="coerce")

def num_value(x):
    return pd.to_numeric(pd.Series([x]), errors="coerce").iloc[0]

def clean_track(x):
    return re.sub(r"[^A-Z0-9]", "", text(x).upper())

def ensure_col(df, col):
    if col not in df.columns:
        df[col] = ""
    return df

def add_race_key(df):
    if df.empty:
        df["_race_key"] = pd.Series(dtype=str)
        return df

    df = df.copy()
    for c in ["race_date", "track", "race_no"]:
        ensure_col(df, c)

    df["_race_key"] = (
        df["race_date"].map(text) + "|" +
        df["track"].map(clean_track) + "|" +
        df["race_no"].map(text)
    )
    return df

runner = add_race_key(read(RUNNER))
betq = add_race_key(read(BETQ))
rel = add_race_key(read(RELIABILITY))
speed = add_race_key(read(SPEED))

if runner.empty:
    raise SystemExit("NO_RUNNER_BOARD")

for c in ["edge_pct", "overlay_pct", "fair_price", "rated_price", "live_price", "sportsbet_price"]:
    if c in runner.columns:
        runner[c] = num_series(runner[c])

for c in ["bet_quality_score_v1_1", "edge_pct", "bet_quality_overlay_pct_v1_1"]:
    if c in betq.columns:
        betq[c] = num_series(betq[c])

rows = []

for key, g in runner.groupby("_race_key", dropna=False):
    first = g.iloc[0]
    race_date = text(first.get("race_date"))
    track = text(first.get("track"))
    race_no = text(first.get("race_no"))

    field_size = len(g)

    edge_col = "edge_pct" if "edge_pct" in g.columns else "overlay_pct" if "overlay_pct" in g.columns else None
    edges = g[edge_col].dropna() if edge_col else pd.Series(dtype=float)
    positive_edges = int((edges > 0).sum()) if len(edges) else 0
    strong_edges = int((edges >= 10).sum()) if len(edges) else 0

    fair_col = "fair_price" if "fair_price" in g.columns else "rated_price" if "rated_price" in g.columns else None
    fair = g[fair_col].dropna() if fair_col else pd.Series(dtype=float)
    fair_sorted = sorted([x for x in fair if x > 0])

    if len(fair_sorted) >= 4:
        top4_spread = fair_sorted[3] - fair_sorted[0]
    elif len(fair_sorted) >= 2:
        top4_spread = fair_sorted[-1] - fair_sorted[0]
    else:
        top4_spread = np.nan

    bq = betq[betq["_race_key"] == key] if not betq.empty else pd.DataFrame()
    bq_scores = num_series(bq["bet_quality_score_v1_1"]) if not bq.empty and "bet_quality_score_v1_1" in bq.columns else pd.Series(dtype=float)
    avg_betq = bq_scores.mean() if len(bq_scores) else np.nan
    high_betq = int((bq_scores >= 60).sum()) if len(bq_scores) else 0

    rr = None
    if not rel.empty and "_race_key" in rel.columns:
      rel_match = rel[rel["_race_key"] == key]
      if not rel_match.empty:
          rr = rel_match.iloc[0]

    reliability_band = text(rr.get("race_reliability_band_v1")) if rr is not None else ""
    reliability_score = num_value(rr.get("race_reliability_score_v1")) if rr is not None and "race_reliability_score_v1" in rel.columns else np.nan

    spd = speed[speed["_race_key"] == key] if not speed.empty and "_race_key" in speed.columns else pd.DataFrame()

    role_values = []
    for c in ["tempo_role", "run_style", "pace", "speed_map_role", "tactical_dna"]:
        if c in spd.columns:
            role_values += spd[c].map(text).str.upper().tolist()

    roles = " ".join(role_values)
    leaders = roles.count("LEADER")
    onpace = roles.count("ON PACE") + roles.count("ONPACE") + roles.count("PRESS")
    pressure_score = leaders * 22 + onpace * 8 + max(field_size - 8, 0) * 3

    if pressure_score >= 75:
        tempo_band = "EXTREME"
    elif pressure_score >= 52:
        tempo_band = "FAST"
    elif pressure_score >= 34:
        tempo_band = "EVEN"
    elif pressure_score >= 18:
        tempo_band = "MODERATE"
    else:
        tempo_band = "SLOW"

    clarity_score = 50

    if field_size <= 8:
        clarity_score += 10
    elif field_size >= 13:
        clarity_score -= 12

    if positive_edges <= 2:
        clarity_score += 8
    elif positive_edges >= 6:
        clarity_score -= 8

    if not pd.isna(top4_spread):
        if top4_spread >= 8:
            clarity_score += 10
        elif top4_spread <= 3:
            clarity_score -= 8

    rb = reliability_band.upper()
    if rb in ["ELITE", "POSITIVE", "HIGH", "STRONG"]:
        clarity_score += 10
    if rb in ["NEGATIVE", "POOR", "LOW", "WEAK"]:
        clarity_score -= 10

    if tempo_band == "EXTREME":
        clarity_score -= 8

    clarity_score = max(0, min(100, clarity_score))

    if clarity_score >= 80:
        clarity_band = "VERY_CLEAR"
    elif clarity_score >= 65:
        clarity_band = "CLEAR"
    elif clarity_score >= 50:
        clarity_band = "BALANCED"
    elif clarity_score >= 35:
        clarity_band = "OPEN"
    else:
        clarity_band = "WIDE_OPEN"

    betting_score = 45
    betting_score += (clarity_score - 50) * 0.30
    betting_score += min(strong_edges * 8, 24)

    if not pd.isna(avg_betq):
        betting_score += (avg_betq - 40) * 0.25

    if rb in ["ELITE", "POSITIVE", "HIGH", "STRONG"]:
        betting_score += 10
    if rb in ["NEGATIVE", "POOR", "LOW", "WEAK"]:
        betting_score -= 10

    betting_score = max(0, min(100, betting_score))

    if betting_score >= 80:
        betting_band = "VERY_HIGH"
    elif betting_score >= 65:
        betting_band = "HIGH"
    elif betting_score >= 50:
        betting_band = "MEDIUM"
    elif betting_score >= 35:
        betting_band = "LOW"
    else:
        betting_band = "VERY_LOW"

    story = f"{tempo_band.replace('_',' ')} tempo expected. Race clarity is {clarity_band.replace('_',' ')}. Betting confidence is {betting_band.replace('_',' ')}."

    rows.append({
        "race_date": race_date,
        "track": track,
        "race_no": race_no,
        "race_key": key,
        "field_size": field_size,
        "positive_edges": positive_edges,
        "strong_edges": strong_edges,
        "avg_bet_quality_score": round(avg_betq, 2) if not pd.isna(avg_betq) else "",
        "race_reliability_band": reliability_band,
        "race_clarity_score_v1": round(clarity_score, 2),
        "race_clarity_band_v1": clarity_band,
        "expected_tempo_score_v1": round(pressure_score, 2),
        "expected_tempo_band_v1": tempo_band,
        "betting_confidence_score_v1": round(betting_score, 2),
        "betting_confidence_band_v1": betting_band,
        "race_story_v1": story,
    })

out = pd.DataFrame(rows)

if not out.empty:
    out["_race_no_num"] = pd.to_numeric(out["race_no"], errors="coerce")
    out = out.sort_values(["race_date", "track", "_race_no_num"]).drop(columns=["_race_no_num"])

out.to_csv(OUT, index=False)

summary = pd.DataFrame([
    ["status", "COMPLETE"],
    ["races", len(out)],
    ["rows_source_runner_board", len(runner)],
    ["betq_rows", len(betq)],
    ["reliability_rows", len(rel)],
    ["speed_rows", len(speed)],
])
summary.columns = ["metric", "value"]
summary.to_csv(SUMMARY, index=False)

print("[RACE_INTELLIGENCE_CARDS_V1] COMPLETE")
print(f"races={len(out)}")
print(f"wrote={OUT}")
print(f"summary={SUMMARY}")
