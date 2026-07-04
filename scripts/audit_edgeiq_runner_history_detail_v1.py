from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DETAIL_PATH = DATA / "edgeiq_runner_history_detail_v1.csv"
AUDIT_PATH = DATA / "edgeiq_runner_history_detail_v1_audit.csv"
SUMMARY_PATH = DATA / "edgeiq_runner_history_detail_v1_audit_summary.csv"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def pct(series: pd.Series) -> float:
    return 0.0 if len(series) == 0 else round(float(series.mean()) * 100.0, 2)


def main() -> None:
    built_at = now_iso()
    if not DETAIL_PATH.exists():
        pd.DataFrame([{"status": "FAIL", "reason": "missing_detail_file", "built_at": built_at}]).to_csv(SUMMARY_PATH, index=False)
        pd.DataFrame(columns=["status", "reason", "built_at"]).to_csv(AUDIT_PATH, index=False)
        raise SystemExit("[EDGEIQ_RUNNER_HISTORY_DETAIL_AUDIT_V1] missing input file")
    df = pd.read_csv(DETAIL_PATH, dtype=str).fillna("")
    if df.empty:
        pd.DataFrame([{"status": "FAIL", "reason": "empty_detail_file", "built_at": built_at}]).to_csv(SUMMARY_PATH, index=False)
        pd.DataFrame(columns=["status", "reason", "built_at"]).to_csv(AUDIT_PATH, index=False)
        raise SystemExit("[EDGEIQ_RUNNER_HISTORY_DETAIL_AUDIT_V1] empty detail file")

    audit_df = df.copy()
    audit_df["has_horse"] = audit_df["horse"].astype(str).str.strip().ne("")
    audit_df["has_horse_key"] = audit_df["horse_key"].astype(str).str.strip().ne("")
    audit_df["has_run_date_iso"] = audit_df["run_date_iso"].astype(str).str.strip().ne("")
    audit_df["has_track"] = audit_df["track"].astype(str).str.strip().ne("")
    audit_df["has_run_rating"] = audit_df.get("run_rating", "").astype(str).str.strip().ne("")
    audit_df["has_performance_rating"] = audit_df.get("performance_rating", "").astype(str).str.strip().ne("")
    audit_df["has_recovered_rating"] = audit_df.get("recovered_rating", "").astype(str).str.strip().ne("")
    audit_df["has_run_rating_final"] = audit_df.get("run_rating_final", "").astype(str).str.strip().ne("")
    audit_df["has_finish_pos"] = audit_df["finish_pos"].astype(str).str.strip().ne("")
    audit_df["has_distance"] = audit_df["distance"].astype(str).str.strip().ne("")
    audit_df["has_sp"] = audit_df["sp"].astype(str).str.strip().ne("")
    audit_df["has_race_no"] = audit_df["race_no"].astype(str).str.strip().ne("")
    audit_df["has_condition"] = audit_df["condition"].astype(str).str.strip().ne("")
    audit_df["has_barrier"] = audit_df["barrier"].astype(str).str.strip().ne("")
    audit_df["has_jockey"] = audit_df["jockey"].astype(str).str.strip().ne("")
    audit_df["has_weight"] = audit_df["weight"].astype(str).str.strip().ne("")
    audit_df["has_race_strength"] = audit_df.get("race_strength", "").astype(str).str.strip().ne("")
    audit_df["duplicate_key_v1"] = audit_df[["horse_key", "run_date_iso", "track", "distance", "race_no"]].astype(str).agg("|".join, axis=1)
    dup_counts = audit_df["duplicate_key_v1"].value_counts()
    audit_df["duplicate_key_count"] = audit_df["duplicate_key_v1"].map(dup_counts).fillna(0).astype(int)
    audit_df["duplicate_key_flag"] = audit_df["duplicate_key_count"] > 1
    audit_df["row_status"] = audit_df.apply(lambda row: "FAIL_DUPLICATE" if row["duplicate_key_flag"] else "PASS_CORE" if row["has_horse"] and row["has_run_date_iso"] and row["has_track"] else "WARN_CORE_GAPS", axis=1)
    audit_df.to_csv(AUDIT_PATH, index=False)

    pct_final = pct(audit_df["has_run_rating_final"])
    pct_strength = pct(audit_df["has_race_strength"])
    duplicate_rows = int(audit_df["duplicate_key_flag"].sum())
    if duplicate_rows > 0 or pct(audit_df["has_horse"]) < 95 or pct(audit_df["has_run_date_iso"]) < 95 or pct(audit_df["has_track"]) < 95:
        status = "FAIL"
    elif pct_final >= 85 and pct_strength >= 60:
        status = "PASS"
    else:
        status = "WARN"

    summary = pd.DataFrame([{
        "status": status,
        "rows": int(len(audit_df)),
        "unique_horses": int(audit_df["horse_key"].astype(str).str.strip().replace("", pd.NA).dropna().nunique()),
        "duplicate_key_rows": duplicate_rows,
        "pct_horse_populated": pct(audit_df["has_horse"]),
        "pct_horse_key_populated": pct(audit_df["has_horse_key"]),
        "pct_run_date_iso_populated": pct(audit_df["has_run_date_iso"]),
        "pct_track_populated": pct(audit_df["has_track"]),
        "pct_original_run_rating_populated": pct(audit_df["has_run_rating"]),
        "pct_performance_rating_populated": pct(audit_df["has_performance_rating"]),
        "pct_recovered_rating_populated": pct(audit_df["has_recovered_rating"]),
        "pct_run_rating_final_populated": pct_final,
        "pct_finish_pos_populated": pct(audit_df["has_finish_pos"]),
        "pct_distance_populated": pct(audit_df["has_distance"]),
        "pct_sp_populated": pct(audit_df["has_sp"]),
        "pct_race_no_populated": pct(audit_df["has_race_no"]),
        "pct_condition_populated": pct(audit_df["has_condition"]),
        "pct_barrier_populated": pct(audit_df["has_barrier"]),
        "pct_jockey_populated": pct(audit_df["has_jockey"]),
        "pct_weight_populated": pct(audit_df["has_weight"]),
        "pct_race_strength_populated": pct_strength,
        "warnings": "; ".join(w for w in [
            "final_rating_below_85" if pct_final < 85 else "",
            "race_strength_sparse" if pct_strength < 60 else "",
            "sp_sparse" if pct(audit_df["has_sp"]) < 50 else "",
        ] if w),
        "built_at": built_at,
    }])
    summary.to_csv(SUMMARY_PATH, index=False)
    print("[EDGEIQ_RUNNER_HISTORY_DETAIL_AUDIT_V1]", status)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
