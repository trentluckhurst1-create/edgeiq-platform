from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

CURRENT = DATA / "edgeiq_current_field_projection_v5_2.csv"
RESEARCH = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"
RISK = DATA / "edgeiq_v6_1_backfilled_live_risk_v1.csv"

OUT = DATA / "edgeiq_current_field_projection_V6_1_RESEARCH_replay.csv"
SUMMARY = DATA / "edgeiq_current_field_projection_V6_1_RESEARCH_replay_summary.csv"
MIGRATION = DATA / "edgeiq_current_field_projection_V6_1_RESEARCH_band_migration.csv"

def horse_key(x):
    import re
    return re.sub(r"[^A-Z0-9]", "", re.sub(r"\([^)]*\)", "", str(x or "").upper()))

def risk_key(x):
    return str(x or "").strip().upper()

def num(x):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return np.nan
        return float(str(x).replace(",", "").strip())
    except Exception:
        return np.nan

def band(gap):
    if pd.isna(gap):
        return "NO_PROJECTION"
    if gap >= 10:
        return "ELITE"
    if gap >= 6:
        return "STRONG"
    if gap >= 2:
        return "POSITIVE"
    if gap >= -2:
        return "NEUTRAL"
    if gap >= -6:
        return "NEGATIVE"
    return "POOR"

def project(vals):
    if len(vals) == 0:
        return np.nan, "NO_HISTORY"
    last = vals[0]
    avg3 = float(np.mean(vals[:3]))
    avg5 = float(np.mean(vals[:5]))
    peak6 = float(np.max(vals[:6]))

    if len(vals) >= 5:
        return (
            (0.35 * last) + (0.35 * avg3) + (0.20 * peak6) + (0.10 * avg5),
            "0.35 last + 0.35 avg3 + 0.20 peak6 + 0.10 avg5 / RESEARCH_RATING"
        )
    if len(vals) >= 3:
        return (
            (0.45 * last) + (0.40 * avg3) + (0.15 * peak6),
            "0.45 last + 0.40 avg3 + 0.15 peak / RESEARCH_RATING"
        )

    return float(np.mean(vals)), "average available research ratings"

def main():
    curr = pd.read_csv(CURRENT, dtype=str, keep_default_na=False, low_memory=False)
    hist = pd.read_csv(RESEARCH, dtype=str, keep_default_na=False, low_memory=False)

    risk_map = {}
    if RISK.exists():
        risk = pd.read_csv(RISK, dtype=str, keep_default_na=False, low_memory=False)
        for _, rr in risk.iterrows():
            risk_map[risk_key(rr.get("horse", ""))] = str(rr.get("v6_1_backfilled_live_risk", ""))

    hist["horse_match_key"] = hist["horse"].map(horse_key)
    hist["race_date_dt"] = pd.to_datetime(hist["race_date"], errors="coerce")
    hist["research_rating"] = pd.to_numeric(hist["performance_rating_v6_1_research"], errors="coerce")

    curr["horse_match_key"] = curr["horse"].map(horse_key)
    curr["race_date_dt"] = pd.to_datetime(curr["race_date"], errors="coerce")

    hist = hist.sort_values(["horse_match_key", "race_date_dt"], ascending=[True, False])
    history = {k: g for k, g in hist.groupby("horse_match_key", dropna=False)}

    rows = []
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for _, r in curr.iterrows():
        h = history.get(r["horse_match_key"], hist.iloc[0:0])
        if len(h) and pd.notna(r["race_date_dt"]):
            h = h[h["race_date_dt"] < r["race_date_dt"]]

        vals = h["research_rating"].dropna().head(6).tolist()
        projected, method = project(vals)

        target = num(r.get("race_target_rating_v5_2", ""))
        gap = projected - target if pd.notna(projected) and pd.notna(target) else np.nan

        out = r.to_dict()
        out["starts_found_research"] = len(vals)
        out["projected_rating_V6_1_RESEARCH"] = round(projected, 2) if pd.notna(projected) else ""
        out["projection_gap_V6_1_RESEARCH"] = round(gap, 2) if pd.notna(gap) else ""
        out["projection_band_V6_1_RESEARCH"] = band(gap)
        out["projection_method_research"] = method
        out["built_at_research_replay"] = built_at

        old_gap = num(r.get("projection_gap_v5_2", ""))
        out["projection_gap_delta_research_minus_v5_2"] = round(gap - old_gap, 2) if pd.notna(gap) and pd.notna(old_gap) else ""

        out["V6_1_governance_action"] = "KEEP_V6_1_RESEARCH"
        out["V6_1_governance_reason"] = ""

        risk_status = risk_map.get(risk_key(r.get("horse", "")), "")
        if risk_status == "CRITICAL":
            out["original_projected_rating_V6_1_RESEARCH"] = out["projected_rating_V6_1_RESEARCH"]
            out["original_projection_gap_V6_1_RESEARCH"] = out["projection_gap_V6_1_RESEARCH"]
            out["original_projection_band_V6_1_RESEARCH"] = out["projection_band_V6_1_RESEARCH"]

            out["projected_rating_V6_1_RESEARCH"] = r.get("projected_rating_v5_2", "")
            out["projection_gap_V6_1_RESEARCH"] = r.get("projection_gap_v5_2", "")
            out["projection_band_V6_1_RESEARCH"] = r.get("projection_band_v5_2", "")
            out["projection_method_research"] = str(r.get("projection_method_v5_2", "")) + " | BACKFILLED_CRITICAL_GOVERNANCE_FALLBACK_TO_V5_2"
            out["projection_gap_delta_research_minus_v5_2"] = 0
            out["V6_1_governance_action"] = "FALLBACK_TO_V5_2"
            out["V6_1_governance_reason"] = "CRITICAL_BACKFILLED_V6_1_INFLATION"

        rows.append(out)

    out_df = pd.DataFrame(rows)
    out_df.to_csv(OUT, index=False)

    summary_rows = []
    fallback = out_df["V6_1_governance_action"].eq("FALLBACK_TO_V5_2")

    summary_rows.append({"section":"overall","metric":"rows","value":len(out_df)})
    summary_rows.append({"section":"overall","metric":"fallback_to_v5_2_rows","value":int(fallback.sum())})
    summary_rows.append({"section":"overall","metric":"fallback_horses","value":", ".join(out_df.loc[fallback, "horse"].astype(str).tolist())})

    for col in ["projection_band_v5_2", "projection_band_V6_1_RESEARCH"]:
        vc = out_df[col].value_counts(dropna=False).to_dict()
        for k, v in vc.items():
            summary_rows.append({"section":col,"metric":k,"count":v})

    old_gaps = pd.to_numeric(out_df["projection_gap_v5_2"], errors="coerce")
    new_gaps = pd.to_numeric(out_df["projection_gap_V6_1_RESEARCH"], errors="coerce")

    summary_rows.extend([
        {"section":"gap_stats","metric":"old_avg_gap","value":round(float(old_gaps.mean()),4)},
        {"section":"gap_stats","metric":"research_avg_gap","value":round(float(new_gaps.mean()),4)},
        {"section":"gap_stats","metric":"old_max_gap","value":round(float(old_gaps.max()),4)},
        {"section":"gap_stats","metric":"research_max_gap","value":round(float(new_gaps.max()),4)},
        {"section":"gap_stats","metric":"old_ge_10_count","count":int((old_gaps >= 10).sum())},
        {"section":"gap_stats","metric":"research_ge_10_count","count":int((new_gaps >= 10).sum())},
    ])

    pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)

    mig = (
        out_df
        .groupby(["projection_band_v5_2", "projection_band_V6_1_RESEARCH"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    mig.to_csv(MIGRATION, index=False)

    print("[PROJECTION_V6_1_RESEARCH_REPLAY_GOVERNED] COMPLETE")
    print(f"rows={len(out_df)}")
    print(f"fallback_to_v5_2_rows={int(fallback.sum())}")
    print(f"fallback_horses={', '.join(out_df.loc[fallback, 'horse'].astype(str).tolist())}")
    print(f"out={OUT}")
    print(f"summary={SUMMARY}")
    print(f"migration={MIGRATION}")

if __name__ == "__main__":
    main()
