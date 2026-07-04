import pandas as pd
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER_DNA = DATA / "edgeiq_runner_dna_status_v1.csv"
TRACK = DATA / "edgeiq_live_track_intelligence_v2_1.csv"
OUT = DATA / "edgeiq_horse_intelligence_v2.csv"
SUMMARY = DATA / "edgeiq_horse_intelligence_v2_summary.csv"

def clean(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def canon(x):
    return re.sub(r"[^A-Z0-9]+", "", clean(x).upper())

def key_cols(df):
    df["track_key_join"] = df["track"].map(canon)
    df["race_no_key_join"] = df["race_no"].map(clean)
    if "horse_key" in df.columns:
        df["horse_key_join"] = df["horse_key"].map(canon)
    elif "horse_canon" in df.columns:
        df["horse_key_join"] = df["horse_canon"].map(canon)
    else:
        df["horse_key_join"] = df["horse"].map(canon)
    return df

def num(x):
    try:
        if clean(x) == "":
            return None
        return float(x)
    except Exception:
        return None

def advantage(row):
    dna = clean(row.get("runner_dna_status", ""))
    if dna != "HISTORICAL_PROFILE":
        return "TRACK_DNA_ONLY"

    rs = clean(row.get("run_style_alignment", ""))
    ba = clean(row.get("barrier_alignment", ""))
    ma = clean(row.get("movement_alignment", ""))

    matches = sum([rs == "MATCH", ba == "MATCH", ma == "MATCH"])
    mismatches = sum([rs == "NO_MATCH", ba == "NO_MATCH", ma == "NO_MATCH"])

    if matches == 3:
        return "STRONG_POSITIVE"
    if matches == 2:
        return "POSITIVE"
    if matches == 1 and mismatches <= 1:
        return "NEUTRAL"
    if mismatches >= 2:
        return "STRONG_NEGATIVE"
    return "NEGATIVE"

def headline(row):
    horse = clean(row.get("horse", ""))
    adv = clean(row.get("track_dna_advantage", ""))
    dna = clean(row.get("runner_dna_status", ""))

    if clean(row.get("track_dna_match_status_v2_1", "")) != "MATCHED":
        return f"{horse}: no Track DNA match available for this track/distance profile."

    if adv == "STRONG_POSITIVE":
        return f"{horse} strongly aligns with the historical Track DNA profile."
    if adv == "POSITIVE":
        return f"{horse} has a positive Track DNA alignment."
    if adv == "NEUTRAL":
        return f"{horse} has mixed Track DNA alignment."
    if adv == "STRONG_NEGATIVE":
        return f"{horse} conflicts with the historical Track DNA profile."
    if adv == "NEGATIVE":
        return f"{horse} has some conflict with the historical Track DNA profile."

    if dna == "IMPORT_NO_LOCAL_DNA":
        return f"{horse} has no reliable local Runner DNA; Track DNA leads the assessment."
    if dna == "INSUFFICIENT_HISTORY":
        return f"{horse} has insufficient Runner DNA; Track DNA leads the assessment."
    return f"{horse} requires manual intelligence review."

def primary_edge(row):
    adv = clean(row.get("track_dna_advantage", ""))
    edge = num(row.get("edge_pct", ""))

    positives = []
    if adv in ["STRONG_POSITIVE", "POSITIVE"]:
        positives.append("Track DNA Match")
    if clean(row.get("runner_dna_status", "")) == "HISTORICAL_PROFILE":
        positives.append("Historical Runner DNA")
    if edge is not None and edge >= 10:
        positives.append("Market Overlay")

    if len(positives) >= 2:
        return "Multiple Positive Factors"
    if positives:
        return positives[0]
    if adv == "TRACK_DNA_ONLY":
        return "Track DNA Only"
    return "No Clear Edge"

def primary_risk(row):
    if clean(row.get("track_dna_match_status_v2_1", "")) != "MATCHED":
        return "No Track DNA Match"

    dna = clean(row.get("runner_dna_status", ""))
    adv = clean(row.get("track_dna_advantage", ""))
    edge = num(row.get("edge_pct", ""))

    if dna == "IMPORT_NO_LOCAL_DNA":
        return "Import / No Local Runner DNA"
    if dna == "INSUFFICIENT_HISTORY":
        return "No Historical Runner DNA"
    if adv in ["NEGATIVE", "STRONG_NEGATIVE"]:
        return "Track DNA Mismatch"
    if edge is not None and edge < 0:
        return "Market Below Assessed Value"
    return "No Major Risk Flag"

def why(row):
    parts = [clean(row.get("horse_intelligence_headline", ""))]

    if clean(row.get("track_dna_match_status_v2_1", "")) == "MATCHED":
        parts.append(
            f"Track DNA used {clean(row.get('track_profile_level',''))} with "
            f"{clean(row.get('track_profile_sample_winners',''))} historical winners. "
            f"Historical profile: {clean(row.get('historical_run_style','UNKNOWN'))}, "
            f"{clean(row.get('historical_barrier_lane','UNKNOWN'))} lane, "
            f"{clean(row.get('historical_movement_profile','UNKNOWN'))} movement."
        )

    if clean(row.get("runner_dna_status", "")) == "HISTORICAL_PROFILE":
        parts.append(
            f"Runner DNA: {clean(row.get('dominant_run_style','UNKNOWN'))}, "
            f"{clean(row.get('movement_profile','UNKNOWN'))}, "
            f"{clean(row.get('style_confidence','UNKNOWN'))} confidence."
        )

    parts.append(f"Primary edge reason: {clean(row.get('primary_edge_reason',''))}.")
    return " ".join([p for p in parts if p])

def risk_text(row):
    risks = []
    pr = clean(row.get("primary_risk_reason", ""))
    if pr and pr != "No Major Risk Flag":
        risks.append(pr)

    for col, msg in [
        ("run_style_alignment", "Runner style does not match the historical winning style."),
        ("barrier_alignment", "Barrier lane does not match the historical winning lane."),
        ("movement_alignment", "Movement pattern does not match the historical winning movement profile."),
    ]:
        if clean(row.get(col, "")) == "NO_MATCH":
            risks.append(msg)

    if clean(row.get("track_fit_band", "")) == "POOR":
        risks.append("Track fit is poor on current Track DNA alignment.")

    if not risks:
        return "No major intelligence risk flagged."

    seen = []
    for r in risks:
        if r not in seen:
            seen.append(r)
    return " ".join(seen)

def main():
    base = key_cols(pd.read_csv(RUNNER_DNA, dtype=str).fillna(""))
    track = key_cols(pd.read_csv(TRACK, dtype=str).fillna(""))

    track_cols = [
        "track_key_join","race_no_key_join","horse_key_join",
        "track_dna_match_status_v2_1","track_condition","condition_group","season","distance_bucket",
        "track_profile_level","track_profile_sample_winners","track_profile_confidence",
        "historical_run_style","historical_barrier_lane","historical_movement_profile",
        "run_style_alignment","barrier_alignment","movement_alignment",
        "track_fit_score","track_fit_band",
        "track_intelligence_label_v2_1","track_intelligence_comment_v2_1"
    ]
    track_cols = [c for c in track_cols if c in track.columns]

    df = base.merge(
        track[track_cols].drop_duplicates(["track_key_join","race_no_key_join","horse_key_join"]),
        on=["track_key_join","race_no_key_join","horse_key_join"],
        how="left"
    )

    df["track_dna_advantage"] = df.apply(advantage, axis=1)
    df["horse_intelligence_headline"] = df.apply(headline, axis=1)
    df["primary_edge_reason"] = df.apply(primary_edge, axis=1)
    df["primary_risk_reason"] = df.apply(primary_risk, axis=1)
    df["why_edgeiq_likes_this_horse_v2"] = df.apply(why, axis=1)
    df["risk_factors_v2"] = df.apply(risk_text, axis=1)

    preferred = [
        "race_date","track","race_no","horse_no","horse","horse_canon","horse_key",
        "barrier","distance","track_condition","condition_group","season","distance_bucket",
        "jockey","trainer","live_price","fair_price","edge_pct",
        "runner_dna_status","runner_dna_comment",
        "starts","dominant_run_style","movement_profile","style_confidence",
        "track_dna_match_status_v2_1",
        "track_profile_level","track_profile_sample_winners","track_profile_confidence",
        "historical_run_style","historical_barrier_lane","historical_movement_profile",
        "run_style_alignment","barrier_alignment","movement_alignment",
        "track_fit_score","track_fit_band",
        "track_dna_advantage",
        "horse_intelligence_headline",
        "primary_edge_reason",
        "primary_risk_reason",
        "why_edgeiq_likes_this_horse_v2",
        "risk_factors_v2",
        "track_intelligence_comment_v2_1"
    ]

    cols = [c for c in preferred if c in df.columns]
    out = df[cols].copy()
    out.to_csv(OUT, index=False)

    pd.DataFrame([
        ["status", "COMPLETE"],
        ["rows", len(out)],
        ["date_breakdown", "; ".join([f"{k}:{v}" for k,v in out["race_date"].value_counts().to_dict().items()])],
        ["track_match_breakdown", "; ".join([f"{k}:{v}" for k,v in out["track_dna_match_status_v2_1"].value_counts().to_dict().items()])],
        ["advantage_breakdown", "; ".join([f"{k}:{v}" for k,v in out["track_dna_advantage"].value_counts().to_dict().items()])],
        ["risk_reason_breakdown", "; ".join([f"{k}:{v}" for k,v in out["primary_risk_reason"].value_counts().to_dict().items()])],
        ["output", OUT.name],
    ], columns=["metric", "value"]).to_csv(SUMMARY, index=False)

    print("[HORSE_INTELLIGENCE_V2] COMPLETE")
    print(f"rows={len(out)}")
    print("dates=" + "; ".join([f"{k}:{v}" for k,v in out["race_date"].value_counts().to_dict().items()]))
    print("track_matches=" + "; ".join([f"{k}:{v}" for k,v in out["track_dna_match_status_v2_1"].value_counts().to_dict().items()]))
    print(f"wrote={OUT}")

if __name__ == "__main__":
    main()
