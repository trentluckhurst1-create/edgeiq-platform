from pathlib import Path
import pandas as pd
import numpy as np
import math

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_live_runner_board_research_replay_v1.csv"
OUT = DATA / "edgeiq_live_bet_quality_research_replay_v1.csv"
SUMMARY = DATA / "edgeiq_live_bet_quality_research_replay_v1_summary.csv"

def num(x, default=math.nan):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return default
        return float(str(x).replace(",", "").strip())
    except Exception:
        return default

def grade(score):
    if score >= 85:
        return "A+"
    if score >= 75:
        return "A"
    if score >= 65:
        return "B"
    if score >= 55:
        return "C"
    if score >= 45:
        return "D"
    return "PASS"

def overlay_score(edge):
    x = num(edge, 0)
    if x <= 0:
        return 0.0
    if x <= 20:
        return x * 0.85
    if x <= 60:
        return 17.0 + ((x - 20) * 0.25)
    return 27.0

def sectional_score(row):
    sw = num(row.get("sectional_weapon_score", ""), math.nan)
    lp = num(row.get("late_power_index", ""), math.nan)
    ps = num(row.get("projected_spd", ""), math.nan)

    score = 0.0
    if not math.isnan(sw):
        if sw >= 70:
            score += 8
        elif sw >= 64:
            score += 6
        elif sw >= 58:
            score += 4

    if not math.isnan(lp):
        if lp >= 70:
            score += 6
        elif lp >= 63:
            score += 4
        elif lp >= 58:
            score += 2

    if not math.isnan(ps):
        if 4.5 <= ps <= 7.5:
            score += 2

    return min(15.0, score)

def projection_score(row):
    gap = num(row.get("research_gap", ""), math.nan)
    band = str(row.get("research_band", "")).strip().upper()

    if math.isnan(gap):
        return 0.0

    score = 0.0
    if band == "ELITE":
        score += 14
    elif band == "STRONG":
        score += 10
    elif band == "POSITIVE":
        score += 6
    elif band == "NEUTRAL":
        score += 3

    if gap >= 10:
        score += 4
    elif gap >= 6:
        score += 2

    return min(18.0, score)

def market_score(row):
    edge = num(row.get("research_edge_pct", ""), math.nan)
    if math.isnan(edge):
        return 0.0
    if edge >= 50:
        return 7.0
    if edge >= 18:
        return 5.0
    if edge >= 6:
        return 2.0
    return 0.0

def guardrail_penalty(row):
    status = str(row.get("research_status", "")).strip().upper()
    guard = str(row.get("research_guardrail", "")).strip().upper()

    penalty = 0.0

    if status != "RESEARCH_RATED":
        penalty += 30.0

    if guard == "WEAK_RACE_DAMPED":
        penalty += 8.0

    return penalty

def main():
    df = pd.read_csv(SRC, dtype=str, keep_default_na=False, low_memory=False)

    rows = []

    for _, r in df.iterrows():
        os = overlay_score(r.get("research_edge_pct", ""))
        ps = projection_score(r)
        ss = sectional_score(r)
        ms = market_score(r)
        gp = guardrail_penalty(r)

        total = max(0.0, min(100.0, os + ps + ss + ms - gp))

        out = r.to_dict()
        out.update({
            "research_overlay_score_v1": round(os, 2),
            "research_projection_score_v1": round(ps, 2),
            "research_sectional_score_v1": round(ss, 2),
            "research_market_score_v1": round(ms, 2),
            "research_guardrail_penalty_v1": round(gp, 2),
            "research_bet_quality_score_v1": round(total, 2),
            "research_bet_quality_grade_v1": grade(total),
            "research_bet_quality_status_v1": "RESEARCH_ONLY",
        })
        rows.append(out)

    out_df = pd.DataFrame(rows)
    out_df.to_csv(OUT, index=False)

    summary = pd.DataFrame([
        {"metric": "status", "value": "COMPLETE"},
        {"metric": "rows", "value": len(out_df)},
        {"metric": "scored_rows", "value": int(pd.to_numeric(out_df["research_bet_quality_score_v1"], errors="coerce").notna().sum())},
        {"metric": "avg_score", "value": round(float(pd.to_numeric(out_df["research_bet_quality_score_v1"], errors="coerce").mean()), 4)},
        {"metric": "max_score", "value": round(float(pd.to_numeric(out_df["research_bet_quality_score_v1"], errors="coerce").max()), 4)},
        {"metric": "a_plus", "value": int(out_df["research_bet_quality_grade_v1"].eq("A+").sum())},
        {"metric": "a", "value": int(out_df["research_bet_quality_grade_v1"].eq("A").sum())},
        {"metric": "b", "value": int(out_df["research_bet_quality_grade_v1"].eq("B").sum())},
        {"metric": "c", "value": int(out_df["research_bet_quality_grade_v1"].eq("C").sum())},
        {"metric": "d", "value": int(out_df["research_bet_quality_grade_v1"].eq("D").sum())},
        {"metric": "pass", "value": int(out_df["research_bet_quality_grade_v1"].eq("PASS").sum())},
        {"metric": "official_fair_price_replaced", "value": "NO"},
        {"metric": "edge_execution_staking_changed", "value": "NO"},
        {"metric": "verdict", "value": "RESEARCH_REPLAY_ONLY"},
    ])

    summary.to_csv(SUMMARY, index=False)

    print("[LIVE_BET_QUALITY_RESEARCH_REPLAY_V1] COMPLETE")
    print(summary.to_string(index=False))
    print(f"wrote={OUT}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
