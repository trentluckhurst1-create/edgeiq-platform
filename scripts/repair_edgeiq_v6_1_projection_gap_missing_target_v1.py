from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_current_field_projection_V6_1_RESEARCH_replay.csv"
OUT = DATA / "edgeiq_current_field_projection_V6_1_RESEARCH_replay_GAP_REPAIR_CANDIDATE_V1.csv"
AUDIT = DATA / "edgeiq_v6_1_projection_gap_missing_target_repair_v1_audit.csv"
SUMMARY = DATA / "edgeiq_v6_1_projection_gap_missing_target_repair_v1_summary.csv"
REPORT = DATA / "edgeiq_v6_1_projection_gap_missing_target_repair_v1_report.txt"

def num(x):
    try:
        s = str(x).replace(",", "").strip()
        if s == "" or s.lower() == "nan":
            return np.nan
        return float(s)
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

df = pd.read_csv(SRC, dtype=str, keep_default_na=False, low_memory=False)

required = ["race_date", "track", "race_no", "horse", "projected_rating_V6_1_RESEARCH", "projection_gap_V6_1_RESEARCH", "projection_band_V6_1_RESEARCH"]
missing = [c for c in required if c not in df.columns]
if missing:
    raise RuntimeError(f"Missing required columns: {missing}")

df["_projected_num"] = pd.to_numeric(df["projected_rating_V6_1_RESEARCH"], errors="coerce")
df["_gap_num"] = pd.to_numeric(df["projection_gap_V6_1_RESEARCH"], errors="coerce")

target_col = "race_target_rating_v5_2" if "race_target_rating_v5_2" in df.columns else None
if target_col:
    df["_target_num"] = pd.to_numeric(df[target_col], errors="coerce")
else:
    df["_target_num"] = np.nan

audit_rows = []
fixed_rows = 0
fixed_races = 0

for key, g in df.groupby(["race_date", "track", "race_no"], dropna=False):
    idx = g.index
    projected = pd.to_numeric(g["projected_rating_V6_1_RESEARCH"], errors="coerce")
    gaps = pd.to_numeric(g["projection_gap_V6_1_RESEARCH"], errors="coerce")

    projected_count = int(projected.notna().sum())
    gap_count_before = int(gaps.notna().sum())
    missing_gap_with_projection = int((projected.notna() & gaps.isna()).sum())

    if projected_count <= 0 or missing_gap_with_projection <= 0:
        audit_rows.append({
            "race_date": key[0],
            "track": key[1],
            "race_no": key[2],
            "projected_count": projected_count,
            "gap_count_before": gap_count_before,
            "missing_gap_with_projection": missing_gap_with_projection,
            "repair_action": "NO_REPAIR_REQUIRED",
            "fallback_target_used": "",
            "rows_fixed": 0
        })
        continue

    race_targets = pd.to_numeric(g[target_col], errors="coerce") if target_col else pd.Series(np.nan, index=g.index)
    existing_target = race_targets.dropna()

    if len(existing_target) > 0:
        fallback_target = float(existing_target.median())
        action = "REPAIRED_USING_EXISTING_RACE_TARGET"
    else:
        fallback_target = float(projected.dropna().median())
        action = "REPAIRED_USING_FIELD_MEDIAN_PROJECTED_TARGET"

    repair_mask = projected.notna() & gaps.isna()
    repair_idx = g.loc[repair_mask].index

    repaired_gap = projected.loc[repair_idx] - fallback_target

    df.loc[repair_idx, "projection_gap_V6_1_RESEARCH"] = repaired_gap.round(2).astype(str)
    df.loc[repair_idx, "projection_band_V6_1_RESEARCH"] = repaired_gap.map(band)

    if "V6_1_governance_action" in df.columns:
        df.loc[repair_idx, "V6_1_governance_action"] = "REPAIRED_MISSING_GAP_TARGET"
    if "V6_1_governance_reason" in df.columns:
        df.loc[repair_idx, "V6_1_governance_reason"] = action

    fixed_rows += len(repair_idx)
    fixed_races += 1

    audit_rows.append({
        "race_date": key[0],
        "track": key[1],
        "race_no": key[2],
        "projected_count": projected_count,
        "gap_count_before": gap_count_before,
        "missing_gap_with_projection": missing_gap_with_projection,
        "repair_action": action,
        "fallback_target_used": round(fallback_target, 4),
        "rows_fixed": len(repair_idx)
    })

df = df.drop(columns=["_projected_num", "_gap_num", "_target_num"], errors="ignore")
df.to_csv(OUT, index=False)

audit = pd.DataFrame(audit_rows)
audit.to_csv(AUDIT, index=False)

summary = pd.DataFrame([{
    "status": "EDGEIQ_V6_1_PROJECTION_GAP_REPAIR_CANDIDATE_BUILT",
    "source": SRC.name,
    "output": OUT.name,
    "rows": len(df),
    "fixed_rows": fixed_rows,
    "fixed_races": fixed_races,
    "remaining_no_projection_with_projected_rating": int(
        (
            pd.to_numeric(df["projected_rating_V6_1_RESEARCH"], errors="coerce").notna()
            &
            pd.to_numeric(df["projection_gap_V6_1_RESEARCH"], errors="coerce").isna()
        ).sum()
    ),
    "production_changed": "NO",
    "pricing_changed": "NO",
    "built_at": datetime.now(timezone.utc).isoformat()
}])
summary.to_csv(SUMMARY, index=False)

REPORT.write_text(
    "EDGEIQ V6.1 PROJECTION GAP MISSING TARGET REPAIR V1\n"
    "Production changed: NO\n"
    "Pricing changed: NO\n"
    f"Source: {SRC.name}\n"
    f"Output: {OUT.name}\n"
    f"Fixed rows: {fixed_rows}\n"
    f"Fixed races: {fixed_races}\n",
    encoding="utf-8"
)

print("[EDGEIQ_V6_1_PROJECTION_GAP_REPAIR_CANDIDATE_V1] COMPLETE")
print(f"out={OUT}")
print(f"audit={AUDIT}")
print(f"summary={SUMMARY}")
print(f"report={REPORT}")
