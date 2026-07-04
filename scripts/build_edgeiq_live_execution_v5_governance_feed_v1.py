from __future__ import annotations

import os
from datetime import datetime

import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "public", "data")

IN_LIVE = os.path.join(DATA, "edgeiq_live_terminal_feed_v1.csv")
IN_RELIABILITY = os.path.join(DATA, "edgeiq_live_race_reliability_v1_feed.csv")

OUT = os.path.join(DATA, "edgeiq_live_execution_v5_governance_feed_v1.csv")
OUT_SUMMARY = os.path.join(DATA, "edgeiq_live_execution_v5_governance_feed_v1_summary.csv")
OUT_UNMATCHED = os.path.join(DATA, "edgeiq_live_execution_v5_governance_feed_v1_unmatched.csv")


def safe_str(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def num(x):
    return pd.to_numeric(x, errors="coerce")


def clean_track(x):
    return (
        safe_str(x)
        .upper()
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
        .replace(".", "")
        .replace("'", "")
        .replace("’", "")
        .replace("SPORTSBET", "")
        .replace("LADBROKES", "")
        .replace("BET365", "")
        .replace("TABPARK", "")
        .replace("PICKLEBETPARK", "")
        .replace("APIAM", "")
    )


def clean_race_no(x):
    s = safe_str(x).upper().replace("R", "")
    try:
        return str(int(float(s)))
    except Exception:
        return s


def make_race_key(df):
    date_col = None
    for c in ["meeting_date", "race_date", "date"]:
        if c in df.columns:
            date_col = c
            break

    if date_col is None:
        return pd.Series([""] * len(df), index=df.index)

    return (
        df[date_col].astype(str).str.strip()
        + "|"
        + df["track"].map(clean_track)
        + "|"
        + df["race_no"].map(clean_race_no)
    )


def governance_from_score(score):
    try:
        s = float(score)
    except Exception:
        s = 0.0

    if s >= 5:
        return "V5_ENVIRONMENT_STRONG"
    if s >= 3:
        return "V5_ENVIRONMENT_APPROVED"
    return "V5_ENVIRONMENT_REJECT"


def action_from_score(score):
    try:
        s = float(score)
    except Exception:
        s = 0.0

    if s >= 5:
        return "EXECUTE_STRONG_ENVIRONMENT"
    if s >= 3:
        return "EXECUTE_ENVIRONMENT_APPROVED"
    return "NO_LIVE_LOW_ENVIRONMENT"


def band_from_score(score):
    try:
        s = float(score)
    except Exception:
        s = 0.0

    if s >= 8:
        return "ELITE"
    if s >= 6:
        return "POSITIVE"
    if s >= 4:
        return "NEUTRAL"
    if s >= 2:
        return "NEGATIVE"
    return "POOR"


def reason(row):
    score = row.get("v5_environment_score_v1", "")
    band = row.get("v5_environment_band_v1", "")
    rel_band = row.get("race_reliability_band_v1", "")
    rel_hint = row.get("race_reliability_hint_v1", "")
    rel_reason = row.get("race_reliability_reason_v1", "")

    try:
        s = float(score)
    except Exception:
        s = 0.0

    if s >= 5:
        prefix = "Strong V5 live environment"
    elif s >= 3:
        prefix = "Approved V5 live environment"
    else:
        prefix = "Rejected by V5 live environment governance"

    parts = [
        f"{prefix}: score {score}, band {band}.",
        f"Race Reliability: {rel_band}."
    ]

    if safe_str(rel_hint):
        parts.append(str(rel_hint))

    if safe_str(rel_reason):
        parts.append(str(rel_reason))

    return " ".join(parts)


def score_from_live_reliability(row):
    score_candidates = [
        "environment_score_v1",
        "environment_score_v2",
        "race_reliability_score_v1",
        "race_reliability_score",
    ]

    for c in score_candidates:
        if c in row.index:
            v = num(pd.Series([row.get(c)])).iloc[0]
            if pd.notna(v):
                return float(v)

    band = safe_str(row.get("race_reliability_band_v1")).upper()

    if band == "ELITE":
        return 5.0
    if band == "POSITIVE":
        return 3.0
    if band == "NEUTRAL":
        return 2.0
    if band == "NEGATIVE":
        return 1.0
    if band == "POOR":
        return 0.0

    return 0.0


def main():
    if not os.path.exists(IN_LIVE):
        raise FileNotFoundError(IN_LIVE)

    if not os.path.exists(IN_RELIABILITY):
        raise FileNotFoundError(IN_RELIABILITY)

    live = pd.read_csv(IN_LIVE, low_memory=False)
    reliability = pd.read_csv(IN_RELIABILITY, low_memory=False)

    live["race_key_fixed_v5"] = make_race_key(live)
    reliability["race_key_fixed_v5"] = make_race_key(reliability)

    reliability["v5_environment_score_v1"] = reliability.apply(score_from_live_reliability, axis=1)
    reliability["v5_environment_band_v1"] = reliability["v5_environment_score_v1"].map(band_from_score)

    keep = [
        "race_key_fixed_v5",
        "race_reliability_score_v1",
        "race_reliability_band_v1",
        "race_reliability_label_v1",
        "race_reliability_hint_v1",
        "race_reliability_reason_v1",
        "v5_environment_score_v1",
        "v5_environment_band_v1",
    ]

    keep = [c for c in keep if c in reliability.columns]

    reliability2 = reliability[keep].drop_duplicates("race_key_fixed_v5").copy()

    out = live.merge(
        reliability2,
        on="race_key_fixed_v5",
        how="left",
        indicator="v5_reliability_match_status",
    )

    out["v5_live_governance_matched_v1"] = out["v5_reliability_match_status"].eq("both")

    out["v5_environment_score_v1"] = num(out.get("v5_environment_score_v1")).fillna(0)
    out["v5_environment_band_v1"] = out["v5_environment_band_v1"].fillna(out["v5_environment_score_v1"].map(band_from_score))

    out["v5_environment_governance_v1"] = out["v5_environment_score_v1"].map(governance_from_score)
    out["v5_environment_execution_action_v1"] = out["v5_environment_score_v1"].map(action_from_score)
    out["v5_environment_governance_reason_v1"] = out.apply(reason, axis=1)

    out["v5_governance_is_advisory_only_v1"] = True

    unmatched = out[~out["v5_live_governance_matched_v1"]].copy()

    summary_rows = [
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "live_rows", "value": len(out)},
        {"metric": "race_reliability_rows", "value": len(reliability)},
        {"metric": "matched_rows", "value": int(out["v5_live_governance_matched_v1"].sum())},
        {"metric": "unmatched_rows", "value": int((~out["v5_live_governance_matched_v1"]).sum())},
        {"metric": "match_rate_pct", "value": round(float(out["v5_live_governance_matched_v1"].mean()) * 100.0, 2) if len(out) else 0},
        {"metric": "reject_rows", "value": int((out["v5_environment_governance_v1"] == "V5_ENVIRONMENT_REJECT").sum())},
        {"metric": "approved_rows", "value": int((out["v5_environment_governance_v1"] == "V5_ENVIRONMENT_APPROVED").sum())},
        {"metric": "strong_rows", "value": int((out["v5_environment_governance_v1"] == "V5_ENVIRONMENT_STRONG").sum())},
        {"metric": "advisory_only", "value": True},
    ]

    if len(out) and out["v5_live_governance_matched_v1"].mean() >= 0.98:
        verdict = "LIVE_V5_GOVERNANCE_READY"
    elif len(out) and out["v5_live_governance_matched_v1"].mean() >= 0.90:
        verdict = "LIVE_V5_GOVERNANCE_READY_WITH_MATCH_WARNINGS"
    else:
        verdict = "LIVE_V5_GOVERNANCE_NOT_READY"

    summary_rows.append({"metric": "verdict", "value": verdict})

    summary = pd.DataFrame(summary_rows)

    out.to_csv(OUT, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    unmatched.to_csv(OUT_UNMATCHED, index=False)

    print("[LIVE_EXECUTION_V5_GOVERNANCE_FEED_V1] COMPLETE")
    print(f"verdict={verdict}")
    print(f"live_rows={len(out)}")
    print(f"matched_rows={int(out['v5_live_governance_matched_v1'].sum())}")
    print(f"unmatched_rows={int((~out['v5_live_governance_matched_v1']).sum())}")
    print(f"wrote={OUT}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_UNMATCHED}")


if __name__ == "__main__":
    main()
