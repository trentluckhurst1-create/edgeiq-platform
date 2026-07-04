from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(".")
DATA = ROOT / "public" / "data"

CARDS = DATA / "edgeiq_race_intelligence_cards_v1.csv"
RUNNER = DATA / "edgeiq_live_runner_board_v1.csv"
BETQ = DATA / "edgeiq_live_bet_quality_v1_1.csv"
V8 = DATA / "edgeiq_live_v8_candidate_display_feed_v1.csv"

OUT_BRIEF = DATA / "edgeiq_race_briefing_v1.csv"
OUT_MARKET = DATA / "edgeiq_market_intelligence_v1.csv"
OUT_VERDICT = DATA / "edgeiq_race_verdict_v1.csv"
SUMMARY = DATA / "edgeiq_intelligence_terminal_v1_summary.csv"

def read(path):
    if not path.exists():
        print(f"[MISS] {path.name}")
        return pd.DataFrame()
    print(f"[READ] {path.name}")
    return pd.read_csv(path, dtype=str, low_memory=False)

def text(x):
    if pd.isna(x):
        return ""
    s = str(x).strip()
    if s.lower() in ["nan", "none", "null"]:
        return ""
    return s

def num(x):
    return pd.to_numeric(x, errors="coerce")

def clean_track(x):
    return re.sub(r"[^A-Z0-9]", "", text(x).upper())

def clean_horse(x):
    return re.sub(r"[^A-Z0-9]", "", re.sub(r"\([^)]*\)", "", text(x).upper()))

def add_key(df):
    if df.empty:
        df["_race_key"] = pd.Series(dtype=str)
        df["_horse_key_clean"] = pd.Series(dtype=str)
        return df

    df = df.copy()
    for c in ["race_date", "track", "race_no"]:
        if c not in df.columns:
            df[c] = ""

    horse_col = None
    for c in ["horse", "horseName", "runner", "runner_name", "horse_key", "horse_canon"]:
        if c in df.columns:
            horse_col = c
            break

    df["_race_key"] = df["race_date"].map(text) + "|" + df["track"].map(clean_track) + "|" + df["race_no"].map(text)
    df["_horse_key_clean"] = df[horse_col].map(clean_horse) if horse_col else ""
    return df

def first_num(row, cols):
    for c in cols:
        if c in row.index:
            v = pd.to_numeric(pd.Series([row[c]]), errors="coerce").iloc[0]
            if not pd.isna(v):
                return float(v)
    return np.nan

def first_text(row, cols):
    for c in cols:
        if c in row.index:
            v = text(row[c])
            if v:
                return v
    return ""

cards = add_key(read(CARDS))
runner = add_key(read(RUNNER))
betq = add_key(read(BETQ))
v8 = add_key(read(V8))

if cards.empty:
    raise SystemExit("NO_RACE_INTELLIGENCE_CARDS_V1")

brief_rows = []
market_rows = []
verdict_rows = []

for key, card_group in cards.groupby("_race_key", dropna=False):
    card = card_group.iloc[0]
    rg = runner[runner["_race_key"] == key] if not runner.empty else pd.DataFrame()
    bq = betq[betq["_race_key"] == key] if not betq.empty else pd.DataFrame()
    vg = v8[v8["_race_key"] == key] if not v8.empty else pd.DataFrame()

    race_date = text(card.get("race_date"))
    track = text(card.get("track"))
    race_no = text(card.get("race_no"))

    race_clarity = text(card.get("race_clarity_band_v1")).replace("_", " ")
    tempo = text(card.get("expected_tempo_band_v1")).replace("_", " ")
    betting_conf = text(card.get("betting_confidence_band_v1")).replace("_", " ")

    work = rg.copy()
    if not work.empty:
        for c in ["edge_pct", "ui_edge_pct", "fair_price", "rated_price", "live_price", "sportsbet_price"]:
            if c in work.columns:
                work[c] = num(work[c])

        edge_col = "edge_pct" if "edge_pct" in work.columns else "ui_edge_pct" if "ui_edge_pct" in work.columns else None
        fair_col = "fair_price" if "fair_price" in work.columns else "rated_price" if "rated_price" in work.columns else None
        live_col = "live_price" if "live_price" in work.columns else "sportsbet_price" if "sportsbet_price" in work.columns else None

        work["_edge"] = work[edge_col] if edge_col else np.nan
        work["_fair"] = work[fair_col] if fair_col else np.nan
        work["_live"] = work[live_col] if live_col else np.nan

        if work["_edge"].isna().all() and not work["_fair"].isna().all() and not work["_live"].isna().all():
            mask = work["_fair"].gt(0) & work["_live"].gt(0)
            work.loc[mask, "_edge"] = ((work.loc[mask, "_live"] / work.loc[mask, "_fair"]) - 1) * 100

        horse_col = "horse" if "horse" in work.columns else "runner" if "runner" in work.columns else "horse_key"
        top_value = work.sort_values("_edge", ascending=False).iloc[0] if "_edge" in work.columns and work["_edge"].notna().any() else work.iloc[0]
        top_value_runner = text(top_value.get(horse_col))
        top_value_edge = first_num(top_value, ["_edge"])

        likely = work[work["_fair"].gt(0)].sort_values("_fair").iloc[0] if work["_fair"].gt(0).any() else work.iloc[0]
        most_likely_winner = text(likely.get(horse_col))
        most_likely_fair = first_num(likely, ["_fair"])

        overlay_count = int((work["_edge"] > 0).sum()) if "_edge" in work.columns else 0
        strong_overlay_count = int((work["_edge"] >= 10).sum()) if "_edge" in work.columns else 0
    else:
        top_value_runner = ""
        top_value_edge = np.nan
        most_likely_winner = ""
        most_likely_fair = np.nan
        overlay_count = 0
        strong_overlay_count = 0

    if not bq.empty and "bet_quality_score_v1_1" in bq.columns:
        bq_scores = num(bq["bet_quality_score_v1_1"])
        avg_bq = bq_scores.mean()
    else:
        avg_bq = np.nan

    if overlay_count >= 4:
        market_efficiency = "LOOSE"
    elif overlay_count >= 2:
        market_efficiency = "FAIR"
    else:
        market_efficiency = "TIGHT"

    if not rg.empty and "_edge" in work.columns and work["_edge"].notna().any():
        strongest_firmer = ""
        largest_drifter = ""
        if "market_move" in work.columns:
            firmers = work[work["market_move"].astype(str).str.upper().str.contains("FIRM", na=False)]
            drifters = work[work["market_move"].astype(str).str.upper().str.contains("DRIFT", na=False)]
            strongest_firmer = text(firmers.iloc[0].get(horse_col)) if not firmers.empty else ""
            largest_drifter = text(drifters.iloc[0].get(horse_col)) if not drifters.empty else ""
    else:
        strongest_firmer = ""
        largest_drifter = ""

    best_bet = "NONE"
    confidence = betting_conf
    if strong_overlay_count > 0 and betting_conf in ["HIGH", "VERY HIGH"] and race_clarity in ["CLEAR", "VERY CLEAR", "BALANCED"]:
        best_bet = top_value_runner
    elif strong_overlay_count > 0 and betting_conf in ["MEDIUM"]:
        best_bet = "WATCH"

    briefing = (
        f"{tempo} tempo expected. "
        f"Race clarity is {race_clarity}. "
        f"Betting confidence is {betting_conf}. "
    )

    if most_likely_winner:
        briefing += f"Most likely winner is {most_likely_winner}"
        if not pd.isna(most_likely_fair):
            briefing += f" at an EDGEiQ fair of ${most_likely_fair:.2f}"
        briefing += ". "

    if top_value_runner and not pd.isna(top_value_edge):
        if top_value_edge > 0:
            briefing += f"Best current value is {top_value_runner} at +{top_value_edge:.1f}% edge."
        else:
            briefing += "No clear positive value runner currently identified."

    market_comment = (
        f"Market looks {market_efficiency.lower()} with {overlay_count} positive overlays "
        f"and {strong_overlay_count} strong overlays."
    )

    verdict = (
        f"{track} R{race_no}: {race_clarity} race, {tempo} tempo, "
        f"{betting_conf} betting confidence. "
        f"Most likely winner: {most_likely_winner or 'unknown'}. "
        f"Best value: {top_value_runner or 'none'}. "
        f"Best bet: {best_bet}."
    )

    brief_rows.append({
        "race_date": race_date,
        "track": track,
        "race_no": race_no,
        "race_key": key,
        "race_clarity": race_clarity,
        "expected_tempo": tempo,
        "betting_confidence": betting_conf,
        "top_value_runner": top_value_runner,
        "top_value_edge": "" if pd.isna(top_value_edge) else round(top_value_edge, 2),
        "most_likely_winner": most_likely_winner,
        "most_likely_fair": "" if pd.isna(most_likely_fair) else round(most_likely_fair, 2),
        "race_briefing_text": briefing,
    })

    market_rows.append({
        "race_date": race_date,
        "track": track,
        "race_no": race_no,
        "race_key": key,
        "strongest_firmer": strongest_firmer,
        "largest_drifter": largest_drifter,
        "market_efficiency": market_efficiency,
        "overlay_count": overlay_count,
        "strong_overlay_count": strong_overlay_count,
        "avg_bet_quality_score": "" if pd.isna(avg_bq) else round(avg_bq, 2),
        "market_comment": market_comment,
    })

    verdict_rows.append({
        "race_date": race_date,
        "track": track,
        "race_no": race_no,
        "race_key": key,
        "race_clarity": race_clarity,
        "expected_tempo": tempo,
        "track_profile": "PENDING_TRACK_PROFILE_ENGINE",
        "most_likely_winner": most_likely_winner,
        "best_value_runner": top_value_runner,
        "best_bet": best_bet,
        "confidence": confidence,
        "verdict_text": verdict,
    })

brief = pd.DataFrame(brief_rows)
market = pd.DataFrame(market_rows)
verdict = pd.DataFrame(verdict_rows)

for df in [brief, market, verdict]:
    if not df.empty:
        df["_race_no_num"] = pd.to_numeric(df["race_no"], errors="coerce")
        df.sort_values(["race_date", "track", "_race_no_num"], inplace=True)
        df.drop(columns=["_race_no_num"], inplace=True)

brief.to_csv(OUT_BRIEF, index=False)
market.to_csv(OUT_MARKET, index=False)
verdict.to_csv(OUT_VERDICT, index=False)

summary = pd.DataFrame([
    ["status", "COMPLETE"],
    ["races", len(brief)],
    ["briefing_rows", len(brief)],
    ["market_rows", len(market)],
    ["verdict_rows", len(verdict)],
    ["runner_rows", len(runner)],
    ["bet_quality_rows", len(betq)],
    ["v8_rows", len(v8)],
])
summary.columns = ["metric", "value"]
summary.to_csv(SUMMARY, index=False)

print("[INTELLIGENCE_TERMINAL_V1] COMPLETE")
print(f"briefing={OUT_BRIEF}")
print(f"market={OUT_MARKET}")
print(f"verdict={OUT_VERDICT}")
print(f"summary={SUMMARY}")
