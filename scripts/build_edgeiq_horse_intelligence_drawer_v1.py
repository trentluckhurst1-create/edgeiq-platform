from pathlib import Path
import pandas as pd
import numpy as np
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
TRACK_INTEL = DATA / "edgeiq_live_track_intelligence_v1.csv"
RUNNER_INTEL = DATA / "edgeiq_runner_intelligence_v1.csv"
BET_QUALITY = DATA / "edgeiq_live_bet_quality_v1_1.csv"
V8 = DATA / "edgeiq_live_v8_candidate_display_feed_v1.csv"

OUT = DATA / "edgeiq_horse_intelligence_drawer_v1.csv"
SUMMARY = DATA / "edgeiq_horse_intelligence_drawer_v1_summary.csv"


def safe(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def canon_track(x):
    return re.sub(r"[^A-Z0-9]", "", safe(x).upper())


def canon_horse(x):
    s = safe(x).upper()
    s = re.sub(r"\([^)]*\)", "", s)
    return re.sub(r"[^A-Z0-9]", "", s)


def race_no(x):
    try:
        return str(int(float(safe(x).replace("R", ""))))
    except Exception:
        return safe(x)


def first(row, keys, fallback=""):
    for k in keys:
        if k in row and safe(row[k]):
            return safe(row[k])
    return fallback


def first_num(row, keys):
    for k in keys:
        if k in row:
            n = pd.to_numeric(row[k], errors="coerce")
            if pd.notna(n):
                return float(n)
    return np.nan


def money(x):
    if pd.isna(x) or x <= 0:
        return "—"
    return f"${x:.2f}"


def pct(x):
    if pd.isna(x):
        return "—"
    return f"{x:.1f}%"


def score_label(value):
    score = first_num({"value": value}, ["value"])
    if pd.isna(score):
        return "UNKNOWN"
    if score >= 80:
        return "ELITE"
    if score >= 65:
        return "STRONG"
    if score >= 50:
        return "SOLID"
    if score >= 35:
        return "MIXED"
    return "WEAK"


def decision_band(row):
    decision = first(row, ["display_decision", "execution_action", "decision"], "")
    if decision:
        return decision.upper()
    edge = first_num(row, ["display_edge_pct", "edge_pct", "ui_edge_pct", "bet_quality_overlay_pct_v1_1"])
    if pd.notna(edge) and edge >= 18:
        return "WATCH"
    if pd.notna(edge) and edge >= 10:
        return "LEAN"
    if pd.notna(edge) and edge > 0:
        return "PASS"
    if pd.notna(edge) and edge <= 0:
        return "UNDERLAY"
    return "NO MARKET"


def join_key(df):
    df["join_track"] = df["track"].map(canon_track) if "track" in df.columns else ""
    df["join_race_no"] = df["race_no"].map(race_no) if "race_no" in df.columns else ""
    if "horse_canon" in df.columns:
        df["join_horse"] = df["horse_canon"].map(canon_horse)
    elif "horse_key" in df.columns:
        df["join_horse"] = df["horse_key"].map(canon_horse)
    elif "horse" in df.columns:
        df["join_horse"] = df["horse"].map(canon_horse)
    elif "runner" in df.columns:
        df["join_horse"] = df["runner"].map(canon_horse)
    else:
        df["join_horse"] = ""
    return df


def track_fit_sentence(row):
    fit = first(row, ["track_fit_band"], "UNKNOWN")
    score = first(row, ["track_fit_score"], "")
    style_align = first(row, ["run_style_alignment"], "UNKNOWN")
    barrier_align = first(row, ["barrier_alignment"], "UNKNOWN")
    dna_style = first(row, ["track_dna_dominant_run_style"], "UNKNOWN")
    dna_lane = first(row, ["track_dna_dominant_barrier_lane"], "UNKNOWN")
    runner_style = first(row, ["runner_dominant_run_style", "dominant_run_style", "run_style"], "UNKNOWN")
    runner_lane = first(row, ["runner_barrier_lane"], "UNKNOWN")
    return (
        f"Track fit is {fit}{f' ({score})' if score else ''}. "
        f"Track DNA favours {dna_style} runners from {dna_lane} lanes. "
        f"This runner profiles as {runner_style} from {runner_lane}: "
        f"style {style_align}, barrier {barrier_align}."
    )


def market_sentence(row):
    live = first_num(row, ["display_live_price", "live_price", "sportsbet_price", "fixed_win", "market_price", "bet_quality_live_price_used_v1_1"])
    fair = first_num(row, ["display_fair_price", "fair_price", "rated_price", "edgeiq_price", "bet_quality_fair_price_used_v1_1"])
    edge = first_num(row, ["display_edge_pct", "edge_pct", "ui_edge_pct", "bet_quality_overlay_pct_v1_1"])
    grade = first(row, ["bet_quality_grade_v1_1", "bet_quality_grade"], "")
    return (
        f"Market {money(live)}, EDGEiQ fair {money(fair)}, edge {pct(edge)}. "
        f"Bet quality {grade or '—'}. Current decision: {decision_band(row)}."
    )


def profile_sentence(row):
    archetype = first(row, ["archetype"], "UNKNOWN")
    run_style = first(row, ["run_style", "runner_dominant_run_style", "dominant_run_style"], "UNKNOWN")
    tempo_fit = first(row, ["tempo_fit"], "UNKNOWN")
    tactical_score = first(row, ["tactical_score"], "")
    return (
        f"Form profile {archetype}. "
        f"Projected run style {run_style}. "
        f"Tempo fit {tempo_fit}{f' with tactical score {tactical_score}' if tactical_score else ''}."
    )


def risk_sentence(row):
    risks = []
    fit = first(row, ["track_fit_band"], "").upper()
    if fit in ["POOR", "NEGATIVE"]:
        risks.append(f"track fit rates {fit}")
    edge = first_num(row, ["display_edge_pct", "edge_pct", "ui_edge_pct", "bet_quality_overlay_pct_v1_1"])
    if pd.notna(edge) and edge < 0:
        risks.append("market price is shorter than EDGEiQ fair")
    conf = first(row, ["style_confidence"], "").upper()
    if conf in ["LOW", "VERY_LOW", ""]:
        risks.append("runner-style confidence is limited")
    live = first_num(row, ["display_live_price", "live_price", "sportsbet_price", "fixed_win", "market_price"])
    if pd.isna(live) or live <= 0:
        risks.append("no reliable live market price")
    if not risks:
        return "No major intelligence-layer risk flags from current available data."
    return "Risk flags: " + "; ".join(risks) + "."


def why_sentence(row):
    fit = first(row, ["track_fit_band"], "UNKNOWN").upper()
    edge = first_num(row, ["display_edge_pct", "edge_pct", "ui_edge_pct", "bet_quality_overlay_pct_v1_1"])
    style_align = first(row, ["run_style_alignment"], "UNKNOWN")
    barrier_align = first(row, ["barrier_alignment"], "UNKNOWN")
    positives = []
    if fit in ["ELITE", "STRONG", "POSITIVE"]:
        positives.append(f"{fit.lower()} track-fit profile")
    if pd.notna(edge) and edge > 0:
        positives.append("positive market edge")
    if style_align == "MATCH":
        positives.append("run style matches Track DNA")
    if barrier_align == "MATCH":
        positives.append("barrier lane matches Track DNA")
    if positives:
        return f"EDGEiQ interest case: {', '.join(positives)}. Decision state: {decision_band(row)}."
    return f"EDGEiQ is not strongly positive here yet. Decision state: {decision_band(row)}."


def main():
    for path in [RUNNER_BOARD, TRACK_INTEL]:
        if not path.exists():
            raise FileNotFoundError(f"Missing required input: {path}")

    board = pd.read_csv(RUNNER_BOARD, dtype=str, low_memory=False)
    track = pd.read_csv(TRACK_INTEL, dtype=str, low_memory=False)

    board.columns = [c.strip() for c in board.columns]
    track.columns = [c.strip() for c in track.columns]

    board = join_key(board)
    track = join_key(track)

    out = board.merge(
        track.drop_duplicates(["join_track", "join_race_no", "join_horse"]),
        on=["join_track", "join_race_no", "join_horse"],
        how="left",
        suffixes=("", "_track"),
    )

    if RUNNER_INTEL.exists():
        runner_intel = pd.read_csv(RUNNER_INTEL, dtype=str, low_memory=False)
        runner_intel.columns = [c.strip() for c in runner_intel.columns]
        runner_intel = join_key(runner_intel)
        out = out.merge(
            runner_intel.drop_duplicates(["join_track", "join_race_no", "join_horse"]),
            on=["join_track", "join_race_no", "join_horse"],
            how="left",
            suffixes=("", "_runner_intel"),
        )

    if BET_QUALITY.exists():
        bet = pd.read_csv(BET_QUALITY, dtype=str, low_memory=False)
        bet.columns = [c.strip() for c in bet.columns]
        bet = join_key(bet)
        out = out.merge(
            bet.drop_duplicates(["join_track", "join_race_no", "join_horse"]),
            on=["join_track", "join_race_no", "join_horse"],
            how="left",
            suffixes=("", "_bet"),
        )

    if V8.exists():
        v8 = pd.read_csv(V8, dtype=str, low_memory=False)
        v8.columns = [c.strip() for c in v8.columns]
        v8 = join_key(v8)
        out = out.merge(
            v8.drop_duplicates(["join_track", "join_race_no", "join_horse"]),
            on=["join_track", "join_race_no", "join_horse"],
            how="left",
            suffixes=("", "_v8"),
        )

    rows = []
    for _, r in out.iterrows():
        row = r.to_dict()
        live = first_num(row, ["display_live_price", "live_price", "sportsbet_price", "fixed_win", "market_price", "bet_quality_live_price_used_v1_1"])
        fair = first_num(row, ["display_fair_price", "fair_price", "rated_price", "edgeiq_price", "bet_quality_fair_price_used_v1_1"])
        edge = first_num(row, ["display_edge_pct", "edge_pct", "ui_edge_pct", "bet_quality_overlay_pct_v1_1"])
        late_power = first(row, ["late_power_index"], "")
        sectional_weapon = first(row, ["sectional_weapon_score"], "")
        confidence_score = first(row, ["confidence_score"], "")

        drawer = {
            "race_date": first(row, ["race_date", "date", "meeting_date"]),
            "track": first(row, ["track"]),
            "race_no": first(row, ["race_no"]),
            "horse_no": first(row, ["horse_no", "runner_no", "saddlecloth"]),
            "horse": first(row, ["horse", "runner"]),
            "barrier": first(row, ["barrier", "bar"]),
            "jockey": first(row, ["jockey", "rider"]),
            "trainer": first(row, ["trainer"]),
            "edgeiq_fair": "" if pd.isna(fair) else round(fair, 4),
            "market_price": "" if pd.isna(live) else round(live, 4),
            "edge_pct": "" if pd.isna(edge) else round(edge, 2),
            "decision": decision_band(row),
            "run_style": first(row, ["run_style", "runner_dominant_run_style", "dominant_run_style"]),
            "movement_profile": first(row, ["movement_profile"]),
            "style_confidence": first(row, ["style_confidence"]),
            "form_profile": first(row, ["archetype", "movement_profile", "run_style"], "UNKNOWN"),
            "tempo_fit": first(row, ["tempo_fit"], ""),
            "tactical_score": first(row, ["tactical_score"], ""),
            "late_power_index": late_power,
            "late_power_band": score_label(late_power),
            "sectional_weapon_score": sectional_weapon,
            "sectional_weapon_band": score_label(sectional_weapon),
            "confidence_score": confidence_score,
            "confidence_band": score_label(confidence_score),
            "track_dna_style": first(row, ["track_dna_dominant_run_style"]),
            "track_dna_barrier": first(row, ["track_dna_dominant_barrier_lane"]),
            "track_dna_movement": first(row, ["track_dna_dominant_movement_profile"]),
            "track_fit_score": first(row, ["track_fit_score"]),
            "track_fit_band": first(row, ["track_fit_band"]),
            "run_style_alignment": first(row, ["run_style_alignment"]),
            "barrier_alignment": first(row, ["barrier_alignment"]),
            "bet_quality_score": first(row, ["bet_quality_score_v1_1", "bet_quality_score"]),
            "bet_quality_grade": first(row, ["bet_quality_grade_v1_1", "bet_quality_grade"]),
            "v8_fair": first(row, ["v8_candidate_price_display", "v8_interaction_candidate_price"]),
            "v8_confidence": first(row, ["brc_match_level_v8", "v8_confidence"]),
            "track_fit_comment": track_fit_sentence(row),
            "market_comment": market_sentence(row),
            "form_profile_comment": profile_sentence(row),
            "why_edgeiq_likes_this_horse": why_sentence(row),
            "risk_factors": risk_sentence(row),
        }

        drawer["horse_intelligence_summary"] = (
            f"{drawer['horse']} — {drawer['decision']}. "
            f"{drawer['track_fit_comment']} "
            f"{drawer['form_profile_comment']} "
            f"{drawer['market_comment']}"
        )
        rows.append(drawer)

    final = pd.DataFrame(rows)
    final.to_csv(OUT, index=False)

    summary = [
        ("status", "COMPLETE"),
        ("rows", len(final)),
        ("track_fit_matched_rows", int(final["track_fit_band"].astype(str).str.len().gt(0).sum())),
        ("positive_or_better_track_fit", int(final["track_fit_band"].isin(["POSITIVE", "STRONG", "ELITE"]).sum())),
        ("poor_or_negative_track_fit", int(final["track_fit_band"].isin(["POOR", "NEGATIVE"]).sum())),
        ("sectional_weapon_rows", int(final["sectional_weapon_score"].astype(str).str.len().gt(0).sum())),
        ("late_power_rows", int(final["late_power_index"].astype(str).str.len().gt(0).sum())),
        ("confidence_rows", int(final["confidence_score"].astype(str).str.len().gt(0).sum())),
    ]

    for key, value in final["decision"].value_counts(dropna=False).to_dict().items():
        summary.append((f"decision_{key}", value))

    for key, value in final["track_fit_band"].value_counts(dropna=False).to_dict().items():
        summary.append((f"track_fit_band_{key}", value))

    pd.DataFrame(summary, columns=["metric", "value"]).to_csv(SUMMARY, index=False)

    print("[HORSE_INTELLIGENCE_DRAWER_V1] COMPLETE")
    print(f"rows={len(final)}")
    print(f"wrote={OUT}")
    print(f"summary={SUMMARY}")


if __name__ == "__main__":
    main()
