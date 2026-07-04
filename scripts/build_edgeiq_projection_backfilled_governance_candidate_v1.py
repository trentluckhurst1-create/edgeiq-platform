from pathlib import Path
import pandas as pd
import math

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PROJ = DATA / "edgeiq_current_field_projection_V6_1_RESEARCH_replay.csv"
RISK = DATA / "edgeiq_v6_1_backfilled_live_risk_v1.csv"

OUT = DATA / "edgeiq_current_field_projection_V6_1_RESEARCH_BACKFILLED_GOVERNED_CANDIDATE_20260617.csv"
SUMMARY = DATA / "edgeiq_current_field_projection_V6_1_RESEARCH_BACKFILLED_GOVERNED_CANDIDATE_20260617_summary.csv"

def canon(x):
    return str(x or "").strip().upper()

def num(x, default=math.nan):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return default
        return float(str(x).strip())
    except Exception:
        return default

proj = pd.read_csv(PROJ, dtype=str, keep_default_na=False, low_memory=False)
risk = pd.read_csv(RISK, dtype=str, keep_default_na=False, low_memory=False)

proj["horse_key"] = proj["horse"].map(canon)
risk["horse_key"] = risk["horse"].map(canon)

risk_cols = [
    "horse_key",
    "v6_1_backfilled_live_risk",
    "backfilled_rows",
    "backfilled_82_4_rows",
    "backfilled_base82_rows",
]
risk_small = risk[[c for c in risk_cols if c in risk.columns]].copy()

out = proj.merge(risk_small, on="horse_key", how="left")

out["V6_1_governance_action"] = "KEEP_V6_1_RESEARCH"
out["V6_1_governance_reason"] = ""

critical_mask = out["v6_1_backfilled_live_risk"].astype(str).eq("CRITICAL")

for col in [
    "projected_rating_V6_1_RESEARCH",
    "projection_gap_V6_1_RESEARCH",
    "projection_band_V6_1_RESEARCH",
    "projection_confidence_V6_1_RESEARCH",
    "projection_method_V6_1_RESEARCH",
]:
    if col not in out.columns:
        out[col] = ""

# Preserve original V6.1 fields
out["original_projected_rating_V6_1_RESEARCH"] = out["projected_rating_V6_1_RESEARCH"]
out["original_projection_gap_V6_1_RESEARCH"] = out["projection_gap_V6_1_RESEARCH"]
out["original_projection_band_V6_1_RESEARCH"] = out["projection_band_V6_1_RESEARCH"]

# Candidate rule:
# For CRITICAL backfilled contamination, use V5.2 projection fields as the governed V6.1 fields.
out.loc[critical_mask, "projected_rating_V6_1_RESEARCH"] = out.loc[critical_mask, "projected_rating_v5_2"]
out.loc[critical_mask, "projection_gap_V6_1_RESEARCH"] = out.loc[critical_mask, "projection_gap_v5_2"]
out.loc[critical_mask, "projection_band_V6_1_RESEARCH"] = out.loc[critical_mask, "projection_band_v5_2"]
out.loc[critical_mask, "projection_confidence_V6_1_RESEARCH"] = out.loc[critical_mask, "projection_confidence_v5_2"]
out.loc[critical_mask, "projection_method_V6_1_RESEARCH"] = (
    out.loc[critical_mask, "projection_method_v5_2"].astype(str)
    + " | BACKFILLED_CRITICAL_GOVERNANCE_FALLBACK_TO_V5_2"
)

out.loc[critical_mask, "V6_1_governance_action"] = "FALLBACK_TO_V5_2"
out.loc[critical_mask, "V6_1_governance_reason"] = "CRITICAL_BACKFILLED_V6_1_INFLATION"

out.to_csv(OUT, index=False)

summary_rows = [
    {"metric": "status", "value": "BACKFILLED_PROJECTION_GOVERNANCE_CANDIDATE_BUILT"},
    {"metric": "rows", "value": len(out)},
    {"metric": "fallback_to_v5_2_rows", "value": int(critical_mask.sum())},
    {"metric": "fallback_horses", "value": ", ".join(out.loc[critical_mask, "horse"].astype(str).tolist())},
]

summary = pd.DataFrame(summary_rows)
summary.to_csv(SUMMARY, index=False)

print("[BACKFILLED_PROJECTION_GOVERNANCE_CANDIDATE] COMPLETE")
print(summary.to_string(index=False))
print(f"out={OUT}")
print(f"summary={SUMMARY}")
