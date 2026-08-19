from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
INPUT_PATH = DATA / "edgeiq_historical_figure_recovery_v1.csv"
AUDIT_PATH = DATA / "edgeiq_historical_figure_recovery_v1_audit.csv"
SUMMARY_PATH = DATA / "edgeiq_historical_figure_recovery_v1_audit_summary.csv"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def pct(series: pd.Series) -> float:
    return 0.0 if len(series) == 0 else round(float(series.mean()) * 100.0, 2)


def main() -> None:
    built_at = now_iso()
    if not INPUT_PATH.exists():
        pd.DataFrame([{"status": "FAIL", "reason": "missing_recovery_file", "built_at": built_at}]).to_csv(SUMMARY_PATH, index=False)
        pd.DataFrame(columns=["status", "reason", "built_at"]).to_csv(AUDIT_PATH, index=False)
        raise SystemExit("[EDGEIQ_HISTORICAL_FIGURE_RECOVERY_AUDIT_V1] missing input file")
    df = pd.read_csv(INPUT_PATH, dtype=str).fillna("")
    if df.empty:
        pd.DataFrame([{"status": "FAIL", "reason": "empty_recovery_file", "built_at": built_at}]).to_csv(SUMMARY_PATH, index=False)
        pd.DataFrame(columns=["status", "reason", "built_at"]).to_csv(AUDIT_PATH, index=False)
        raise SystemExit("[EDGEIQ_HISTORICAL_FIGURE_RECOVERY_AUDIT_V1] empty recovery file")

    audit_df = df.copy()
    audit_df["detail_exists"] = audit_df["detail_row_exists"].astype(str).str.upper().eq("YES")
    audit_df["has_original_run_rating"] = audit_df["original_run_rating"].astype(str).str.strip().ne("")
    audit_df["has_original_performance_rating"] = audit_df["original_performance_rating"].astype(str).str.strip().ne("")
    audit_df["has_recovered_rating"] = audit_df["recovered_rating"].astype(str).str.strip().ne("")
    audit_df["duplicate_key_flag"] = audit_df["detail_recovery_key"].astype(str).str.strip().duplicated(keep=False)
    audit_df.to_csv(AUDIT_PATH, index=False)

    existing = audit_df[audit_df["detail_exists"]].copy()
    coverage_before = pct(existing["has_original_run_rating"] | existing["has_original_performance_rating"])
    coverage_after = pct(existing["has_recovered_rating"])
    summary = pd.DataFrame([{
        "status": "PASS" if coverage_after >= 85 else "WARN" if coverage_after >= 55 else "FAIL",
        "rows": int(len(audit_df)),
        "detail_existing_rows": int(len(existing)),
        "new_safe_history_rows": int((~audit_df["detail_exists"]).sum()),
        "rows_recovered": int((existing["has_recovered_rating"] & ~(existing["has_original_run_rating"])).sum()),
        "coverage_before_pct": coverage_before,
        "coverage_after_pct": coverage_after,
        "new_rating_pct": round(coverage_after - coverage_before, 2),
        "duplicate_matches": int(audit_df["duplicate_key_flag"].sum()),
        "ambiguous_matches": int((audit_df["recovery_action"].astype(str) == "AMBIGUOUS").sum()),
        "built_at": built_at,
    }])
    summary.to_csv(SUMMARY_PATH, index=False)
    print("[EDGEIQ_HISTORICAL_FIGURE_RECOVERY_AUDIT_V1]")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
