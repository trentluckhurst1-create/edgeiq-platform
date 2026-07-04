import pandas as pd
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER_DNA = DATA / "edgeiq_runner_dna_status_v1.csv"
TRACK_INTEL = DATA / "edgeiq_live_track_intelligence_v1.csv"
BET_QUALITY = DATA / "edgeiq_live_bet_quality_v1_1.csv"
V8 = DATA / "edgeiq_live_v8_candidate_display_feed_v1.csv"

OUT = DATA / "edgeiq_horse_intelligence_v1.csv"
SUMMARY = DATA / "edgeiq_horse_intelligence_v1_summary.csv"

def clean(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def canon(x):
    return re.sub(r"[^A-Z0-9]+", "", clean(x).upper())

def num(x):
    try:
        if clean(x) == "":
            return None
        return float(x)
    except Exception:
        return None

def key_cols(df):
    df["track_key_join"] = df["track"].map(canon) if "track" in df.columns else ""
    df["race_no_key_join"] = df["race_no"].map(lambda x: clean(x))
    if "horse_key" in df.columns:
        df["horse_key_join"] = df["horse_key"].map(canon)
    elif "horse_canon" in df.columns:
        df["horse_key_join"] = df["horse_canon"].map(canon)
    elif "horse" in df.columns:
        df["horse_key_join"] = df["horse"].map(canon)
    else:
        df["horse_key_join"] = ""
    return df

def pick(row, cols):
    for c in cols:
        if c in row and clean(row.get(c, "")) != "":
            return clean(row.get(c, ""))
    return ""

def make_status(row):
    edge = num(pick(row, ["edge_pct", "edge_pct_bq", "edge_pct_v8"]))
    track_band = pick(row, ["track_fit_band"])
    dna = pick(row, ["runner_dna_status"])

    positives = 0
    if dna == "HISTORICAL_PROFILE":
        positives += 1
    if track_band in ["ELITE", "ELITE_MATCH", "STRONG", "STRONG_MATCH", "POSITIVE", "POSITIVE_MATCH"]:
        positives += 1
    if edge is not None and edge >= 10:
        positives += 1

    if positives >= 3:
        return "HIGH_INTEREST"
    if positives == 2:
        return "INTEREST"
    if positives == 1:
        return "WATCH"
    return "LOW_INFORMATION"

def why_like(row):
    horse = pick(row, ["horse"])
    parts = []

    dna = pick(row, ["runner_dna_status"])
    if dna == "HISTORICAL_PROFILE":
        parts.append(
            f"{horse} has historical Runner DNA available: {pick(row,['dominant_run_style'])} style, "
            f"{pick(row,['movement_profile'])} movement, from {pick(row,['starts'])} runs."
        )
    elif dna == "IMPORT_NO_LOCAL_DNA":
        parts.append(
            f"{horse} has no reliable local Runner DNA yet and is flagged as an import/no-local-DNA runner."
        )
    else:
        parts.append(
            f"{horse} has insufficient Runner DNA, so Track DNA and market behaviour should carry more weight."
        )

    hist_style = pick(row, ["historical_run_style"])
    hist_barrier = pick(row, ["historical_barrier_lane"])
    hist_move = pick(row, ["historical_movement_profile"])
    sample = pick(row, ["track_profile_sample_winners"])

    if hist_style:
        parts.append(
            f"Track DNA for this race shape points to {hist_style} winners, "
            f"{hist_barrier} barrier lanes, and {hist_move} movement profiles"
            + (f" from {sample} historical winners." if sample else ".")
        )

    rsa = pick(row, ["run_style_alignment"])
    ba = pick(row, ["barrier_alignment"])

    if rsa == "MATCH":
        parts.append("Runner style aligns with the historical Track DNA profile.")
    if ba == "MATCH":
        parts.append("Barrier lane aligns with the historical Track DNA profile.")

    edge = num(pick(row, ["edge_pct", "edge_pct_bq", "edge_pct_v8"]))
    if edge is not None:
        if edge >= 18:
            parts.append(f"Market edge is strong at {edge:.1f}%.")
        elif edge >= 10:
            parts.append(f"Market edge is positive at {edge:.1f}%.")
        elif edge >= 6:
            parts.append(f"Market edge is watchable at {edge:.1f}%.")
        else:
            parts.append(f"Market edge is not currently compelling at {edge:.1f}%.")

    decision = pick(row, ["decision", "bet_quality_decision", "edge_execution_decision", "v8_candidate_status"])
    if decision:
        parts.append(f"Current decision signal: {decision}.")

    return " ".join(parts)

def risks(row):
    risks = []

    dna = pick(row, ["runner_dna_status"])
    if dna == "IMPORT_NO_LOCAL_DNA":
        risks.append("No reliable local Runner DNA; import profile needs manual review.")
    elif dna == "INSUFFICIENT_HISTORY":
        risks.append("Insufficient Runner DNA; confidence depends more heavily on Track DNA and market read.")

    if pick(row, ["run_style_alignment"]) in ["NO_MATCH", "MISMATCH"]:
        risks.append("Runner style does not align with the dominant historical Track DNA style.")

    if pick(row, ["barrier_alignment"]) in ["NO_MATCH", "MISMATCH"]:
        risks.append("Barrier lane does not align with the dominant historical Track DNA draw zone.")

    band = pick(row, ["track_fit_band"])
    if band in ["POOR", "POOR_MATCH", "WEAK"]:
        risks.append("Track fit is currently weak/poor.")

    edge = num(pick(row, ["edge_pct", "edge_pct_bq", "edge_pct_v8"]))
    if edge is not None and edge < 0:
        risks.append(f"Market price is below assessed value by {abs(edge):.1f}%.")

    if not risks:
        risks.append("No major intelligence risk flagged from available data.")

    return " ".join(risks)

def summary_comment(row):
    horse = pick(row, ["horse"])
    status = pick(row, ["horse_intelligence_status"])
    track_band = pick(row, ["track_fit_band"])
    dna = pick(row, ["runner_dna_status"])

    return (
        f"{horse}: {status}. Runner DNA status is {dna}. "
        f"Track fit band is {track_band if track_band else 'UNKNOWN'}. "
        f"{pick(row, ['runner_dna_comment'])}"
    )

def main():
    runner = key_cols(pd.read_csv(RUNNER_DNA, dtype=str).fillna(""))
    track = key_cols(pd.read_csv(TRACK_INTEL, dtype=str).fillna(""))
    bet = key_cols(pd.read_csv(BET_QUALITY, dtype=str).fillna("")) if BET_QUALITY.exists() else pd.DataFrame()
    v8 = key_cols(pd.read_csv(V8, dtype=str).fillna("")) if V8.exists() else pd.DataFrame()

    base = runner.copy()

    base = base.merge(
        track.drop_duplicates(["track_key_join","race_no_key_join","horse_key_join"]),
        on=["track_key_join","race_no_key_join","horse_key_join"],
        how="left",
        suffixes=("", "_track")
    )

    if len(bet):
        base = base.merge(
            bet.drop_duplicates(["track_key_join","race_no_key_join","horse_key_join"]),
            on=["track_key_join","race_no_key_join","horse_key_join"],
            how="left",
            suffixes=("", "_bq")
        )

    if len(v8):
        base = base.merge(
            v8.drop_duplicates(["track_key_join","race_no_key_join","horse_key_join"]),
            on=["track_key_join","race_no_key_join","horse_key_join"],
            how="left",
            suffixes=("", "_v8")
        )

    base["horse_intelligence_status"] = base.apply(make_status, axis=1)
    base["why_edgeiq_likes_this_horse"] = base.apply(why_like, axis=1)
    base["risk_factors"] = base.apply(risks, axis=1)
    base["horse_intelligence_comment"] = base.apply(summary_comment, axis=1)

    preferred = [
        "race_date","track","race_no","horse_no","horse","horse_canon","horse_key",
        "barrier","distance","jockey","trainer","live_price","fair_price","edge_pct",
        "runner_dna_status","runner_dna_comment",
        "starts","dominant_run_style","movement_profile","style_confidence",
        "historical_run_style","historical_barrier_lane","historical_movement_profile",
        "run_style_alignment","barrier_alignment",
        "track_fit_score","track_fit_band",
        "track_profile_sample_winners","track_profile_confidence",
        "leader_winner_share","on_pace_winner_share","midfield_winner_share","backmarker_winner_share",
        "inside_winner_share","middle_winner_share","outside_winner_share",
        "track_intelligence_label_v2","track_intelligence_comment",
        "horse_intelligence_status",
        "why_edgeiq_likes_this_horse",
        "risk_factors",
        "horse_intelligence_comment"
    ]

    cols = []
    seen = set()
    for c in preferred:
        if c in base.columns and c not in seen:
            cols.append(c)
            seen.add(c)

    out = base[cols].copy()
    out.to_csv(OUT, index=False)

    summary = pd.DataFrame([
        ["status", "COMPLETE"],
        ["rows", len(out)],
        ["high_interest_rows", int((out["horse_intelligence_status"] == "HIGH_INTEREST").sum())],
        ["interest_rows", int((out["horse_intelligence_status"] == "INTEREST").sum())],
        ["watch_rows", int((out["horse_intelligence_status"] == "WATCH").sum())],
        ["low_information_rows", int((out["horse_intelligence_status"] == "LOW_INFORMATION").sum())],
        ["output", OUT.name],
    ], columns=["metric", "value"])

    summary.to_csv(SUMMARY, index=False)

    print("[HORSE_INTELLIGENCE_V1] COMPLETE")
    print(f"rows={len(out)}")
    print(f"high_interest={(out['horse_intelligence_status'] == 'HIGH_INTEREST').sum()}")
    print(f"interest={(out['horse_intelligence_status'] == 'INTEREST').sum()}")
    print(f"watch={(out['horse_intelligence_status'] == 'WATCH').sum()}")
    print(f"low_information={(out['horse_intelligence_status'] == 'LOW_INFORMATION').sum()}")
    print(f"wrote={OUT}")

if __name__ == "__main__":
    main()
