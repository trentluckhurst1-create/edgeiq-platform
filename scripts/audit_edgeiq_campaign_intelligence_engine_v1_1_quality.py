from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCE_PATH = DATA / "edgeiq_campaign_intelligence_engine_v1_1.csv"
LIVE_PATH = DATA / "edgeiq_live_runner_board_v1.csv"

OUT_AUDIT_PATH = DATA / "edgeiq_campaign_intelligence_engine_v1_1_quality_audit.csv"
OUT_SUMMARY_PATH = DATA / "edgeiq_campaign_intelligence_engine_v1_1_quality_summary.csv"

BUILT_AT = datetime.now(timezone.utc).isoformat()

ALLOWED_RISK_BANDS = {"LOW", "MODERATE", "HIGH", "UNKNOWN"}
ALLOWED_PROFILES = {
    "FRESH_SPECIALIST",
    "FITNESS_BUILDER",
    "TOUGH_CAMPAIGNER",
    "PEAK_AND_DROP",
    "DEEP_PREP_HORSE",
    "MIXED_PROFILE",
    "UNPROVEN_PROFILE",
}
ALLOWED_EVIDENCE = {
    "STRONG_PROFILE",
    "DEVELOPING_PROFILE",
    "LIMITED_HISTORY",
    "UNRATED_HISTORY",
    "NO_HISTORY",
}
REQUIRED_COLUMNS = [
    "track",
    "race_no",
    "horse",
    "current_race_date",
    "current_prep_stage",
    "prep_stage_label",
    "historical_peak_prep_stage",
    "peak_window_start",
    "peak_window_end",
    "campaign_profile",
    "campaign_profile_band",
    "campaign_risk_score",
    "campaign_risk_band",
    "campaign_narrative",
    "history_runs_used",
    "prep_stage_sample_count",
    "evidence_status",
    "history_source_used",
    "history_source_count",
    "strict_match_flag",
    "loose_match_flag",
]


def first_existing(columns, candidates):
    column_map = {str(column).strip().lower(): str(column) for column in columns}
    for candidate in candidates:
        if candidate.lower() in column_map:
            return column_map[candidate.lower()]
    return None


def clean_text(series):
    return series.fillna("").astype(str).str.strip()


def to_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def serialise_counter(counter):
    if not counter:
        return ""
    return "; ".join(f"{key}={counter[key]}" for key in sorted(counter))


def active_live_rows(live_df):
    scratched_mask = pd.Series([False] * len(live_df), index=live_df.index)
    if "runner_status" in live_df.columns:
        scratched_mask = scratched_mask | clean_text(live_df["runner_status"]).str.upper().eq("SCRATCHED")
    if "is_scratched" in live_df.columns:
        scratched_mask = scratched_mask | clean_text(live_df["is_scratched"]).str.upper().isin({"TRUE", "1", "YES"})
    return live_df.loc[~scratched_mask].copy()


def add_check(rows, name, status, count=0, details="", sample_rows=None):
    rows.append(
        {
            "record_type": "CHECK",
            "check_name": name,
            "status": status,
            "count": int(count) if pd.notna(count) else 0,
            "details": details,
            "sample_group": "",
            "track": "",
            "race_no": "",
            "horse": "",
            "current_prep_stage": "",
            "prep_stage_label": "",
            "historical_peak_prep_stage": "",
            "peak_window_start": "",
            "peak_window_end": "",
            "campaign_profile": "",
            "campaign_risk_band": "",
            "history_runs_used": "",
            "prep_stage_sample_count": "",
            "evidence_status": "",
            "campaign_narrative": "",
        }
    )
    if sample_rows is not None and not sample_rows.empty:
        for _, row in sample_rows.iterrows():
            rows.append(
                {
                    "record_type": "CHECK_SAMPLE",
                    "check_name": name,
                    "status": status,
                    "count": int(count) if pd.notna(count) else 0,
                    "details": details,
                    "sample_group": name,
                    "track": row.get("track", ""),
                    "race_no": row.get("race_no", ""),
                    "horse": row.get("horse", ""),
                    "current_prep_stage": row.get("current_prep_stage", ""),
                    "prep_stage_label": row.get("prep_stage_label", ""),
                    "historical_peak_prep_stage": row.get("historical_peak_prep_stage", ""),
                    "peak_window_start": row.get("peak_window_start", ""),
                    "peak_window_end": row.get("peak_window_end", ""),
                    "campaign_profile": row.get("campaign_profile", ""),
                    "campaign_risk_band": row.get("campaign_risk_band", ""),
                    "history_runs_used": row.get("history_runs_used", ""),
                    "prep_stage_sample_count": row.get("prep_stage_sample_count", ""),
                    "evidence_status": row.get("evidence_status", ""),
                    "campaign_narrative": row.get("campaign_narrative", ""),
                }
            )


def add_sample_group(rows, sample_group, sample_rows):
    if sample_rows.empty:
        rows.append(
            {
                "record_type": "SAMPLE",
                "check_name": "",
                "status": "INFO",
                "count": 0,
                "details": "No rows found for sample group.",
                "sample_group": sample_group,
                "track": "",
                "race_no": "",
                "horse": "",
                "current_prep_stage": "",
                "prep_stage_label": "",
                "historical_peak_prep_stage": "",
                "peak_window_start": "",
                "peak_window_end": "",
                "campaign_profile": "",
                "campaign_risk_band": "",
                "history_runs_used": "",
                "prep_stage_sample_count": "",
                "evidence_status": "",
                "campaign_narrative": "",
            }
        )
        return

    for _, row in sample_rows.iterrows():
        rows.append(
            {
                "record_type": "SAMPLE",
                "check_name": "",
                "status": "INFO",
                "count": 0,
                "details": "",
                "sample_group": sample_group,
                "track": row.get("track", ""),
                "race_no": row.get("race_no", ""),
                "horse": row.get("horse", ""),
                "current_prep_stage": row.get("current_prep_stage", ""),
                "prep_stage_label": row.get("prep_stage_label", ""),
                "historical_peak_prep_stage": row.get("historical_peak_prep_stage", ""),
                "peak_window_start": row.get("peak_window_start", ""),
                "peak_window_end": row.get("peak_window_end", ""),
                "campaign_profile": row.get("campaign_profile", ""),
                "campaign_risk_band": row.get("campaign_risk_band", ""),
                "history_runs_used": row.get("history_runs_used", ""),
                "prep_stage_sample_count": row.get("prep_stage_sample_count", ""),
                "evidence_status": row.get("evidence_status", ""),
                "campaign_narrative": row.get("campaign_narrative", ""),
            }
        )


def main():
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(f"Missing campaign intelligence source: {SOURCE_PATH}")
    if not LIVE_PATH.exists():
        raise FileNotFoundError(f"Missing live runner board: {LIVE_PATH}")

    engine = pd.read_csv(SOURCE_PATH, low_memory=False)
    live = pd.read_csv(LIVE_PATH, low_memory=False)
    active_live = active_live_rows(live)

    audit_rows = []
    check_statuses = []

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in engine.columns]
    status = "PASS" if not missing_columns else "FAIL"
    add_check(
        audit_rows,
        "required_columns_exist",
        status,
        count=len(missing_columns),
        details="All required columns present." if not missing_columns else f"Missing columns: {', '.join(missing_columns)}",
    )
    check_statuses.append(status)

    row_count_delta = len(engine) - len(active_live)
    status = "PASS" if len(engine) == len(active_live) else "FAIL"
    add_check(
        audit_rows,
        "active_runner_row_count_matches",
        status,
        count=abs(row_count_delta),
        details=f"Campaign rows={len(engine)}; active live rows={len(active_live)}.",
    )
    check_statuses.append(status)

    duplicate_mask = engine.duplicated(subset=["track", "race_no", "horse"], keep=False) if {"track", "race_no", "horse"}.issubset(engine.columns) else pd.Series([False] * len(engine))
    duplicate_rows = engine.loc[duplicate_mask].copy()
    status = "PASS" if duplicate_rows.empty else "FAIL"
    add_check(
        audit_rows,
        "no_duplicate_track_race_horse_rows",
        status,
        count=len(duplicate_rows),
        details="No duplicate track/race/horse rows." if duplicate_rows.empty else "Duplicate track/race_no/horse rows detected.",
        sample_rows=duplicate_rows.head(10),
    )
    check_statuses.append(status)

    prep_stage_num = to_numeric(engine["current_prep_stage"]) if "current_prep_stage" in engine.columns else pd.Series([pd.NA] * len(engine))
    prep_stage_text = clean_text(engine["current_prep_stage"]) if "current_prep_stage" in engine.columns else pd.Series([""] * len(engine))
    valid_prep_mask = prep_stage_num.isna() | prep_stage_num.isin([1, 2, 3, 4, 5, 6]) | prep_stage_text.eq("") | prep_stage_text.str.upper().eq("UNKNOWN")
    invalid_prep_rows = engine.loc[~valid_prep_mask].copy()
    status = "PASS" if invalid_prep_rows.empty else "FAIL"
    add_check(
        audit_rows,
        "current_prep_stage_valid",
        status,
        count=len(invalid_prep_rows),
        details="Prep stage values are valid." if invalid_prep_rows.empty else "Found invalid current_prep_stage values outside 1-6/blank.",
        sample_rows=invalid_prep_rows.head(10),
    )
    check_statuses.append(status)

    peak_start = to_numeric(engine["peak_window_start"]) if "peak_window_start" in engine.columns else pd.Series([pd.NA] * len(engine))
    peak_end = to_numeric(engine["peak_window_end"]) if "peak_window_end" in engine.columns else pd.Series([pd.NA] * len(engine))
    invalid_peak_mask = peak_start.notna() & peak_end.notna() & (peak_start > peak_end)
    invalid_peak_rows = engine.loc[invalid_peak_mask].copy()
    status = "PASS" if invalid_peak_rows.empty else "FAIL"
    add_check(
        audit_rows,
        "peak_window_start_lte_end",
        status,
        count=len(invalid_peak_rows),
        details="Peak windows are ordered correctly." if invalid_peak_rows.empty else "Found peak windows where start exceeds end.",
        sample_rows=invalid_peak_rows.head(10),
    )
    check_statuses.append(status)

    risk_band = clean_text(engine["campaign_risk_band"]).str.upper() if "campaign_risk_band" in engine.columns else pd.Series([""] * len(engine))
    invalid_risk_rows = engine.loc[~risk_band.isin(ALLOWED_RISK_BANDS)].copy()
    status = "PASS" if invalid_risk_rows.empty else "FAIL"
    add_check(
        audit_rows,
        "campaign_risk_band_allowed",
        status,
        count=len(invalid_risk_rows),
        details="Risk bands all allowed." if invalid_risk_rows.empty else "Found campaign_risk_band outside LOW/MODERATE/HIGH/UNKNOWN.",
        sample_rows=invalid_risk_rows.head(10),
    )
    check_statuses.append(status)

    profile = clean_text(engine["campaign_profile"]).str.upper() if "campaign_profile" in engine.columns else pd.Series([""] * len(engine))
    invalid_profile_rows = engine.loc[~profile.isin(ALLOWED_PROFILES)].copy()
    status = "PASS" if invalid_profile_rows.empty else "FAIL"
    add_check(
        audit_rows,
        "campaign_profile_allowed",
        status,
        count=len(invalid_profile_rows),
        details="Campaign profiles all allowed." if invalid_profile_rows.empty else "Found campaign_profile outside allowed values.",
        sample_rows=invalid_profile_rows.head(10),
    )
    check_statuses.append(status)

    evidence = clean_text(engine["evidence_status"]).str.upper() if "evidence_status" in engine.columns else pd.Series([""] * len(engine))
    invalid_evidence_rows = engine.loc[~evidence.isin(ALLOWED_EVIDENCE)].copy()
    status = "PASS" if invalid_evidence_rows.empty else "FAIL"
    add_check(
        audit_rows,
        "evidence_status_allowed",
        status,
        count=len(invalid_evidence_rows),
        details="Evidence statuses all allowed." if invalid_evidence_rows.empty else "Found evidence_status outside allowed values.",
        sample_rows=invalid_evidence_rows.head(10),
    )
    check_statuses.append(status)

    high_no_history_rows = engine.loc[(evidence.eq("NO_HISTORY")) & (risk_band.eq("HIGH"))].copy()
    status = "PASS" if high_no_history_rows.empty else "WARN"
    add_check(
        audit_rows,
        "no_high_risk_when_no_history",
        status,
        count=len(high_no_history_rows),
        details="No NO_HISTORY rows marked HIGH risk." if high_no_history_rows.empty else "NO_HISTORY rows marked HIGH risk should be justified before UI use.",
        sample_rows=high_no_history_rows.head(10),
    )
    check_statuses.append(status)

    non_no_history_mask = ~evidence.eq("NO_HISTORY")
    narrative = clean_text(engine["campaign_narrative"]) if "campaign_narrative" in engine.columns else pd.Series([""] * len(engine))
    missing_narrative_rows = engine.loc[non_no_history_mask & narrative.eq("")].copy()
    status = "PASS" if missing_narrative_rows.empty else "WARN"
    add_check(
        audit_rows,
        "narrative_populated_when_evidence_exists",
        status,
        count=len(missing_narrative_rows),
        details="Narratives populated for evidential rows." if missing_narrative_rows.empty else "Missing campaign narrative on rows that are not NO_HISTORY.",
        sample_rows=missing_narrative_rows.head(10),
    )
    check_statuses.append(status)

    history_runs = to_numeric(engine["history_runs_used"]) if "history_runs_used" in engine.columns else pd.Series([pd.NA] * len(engine))
    invalid_history_runs_rows = engine.loc[history_runs.isna() | (history_runs < 0)].copy()
    status = "PASS" if invalid_history_runs_rows.empty else "FAIL"
    add_check(
        audit_rows,
        "history_runs_used_numeric_non_negative",
        status,
        count=len(invalid_history_runs_rows),
        details="history_runs_used is numeric and non-negative." if invalid_history_runs_rows.empty else "Invalid history_runs_used values detected.",
        sample_rows=invalid_history_runs_rows.head(10),
    )
    check_statuses.append(status)

    prep_stage_sample = to_numeric(engine["prep_stage_sample_count"]) if "prep_stage_sample_count" in engine.columns else pd.Series([pd.NA] * len(engine))
    invalid_prep_sample_rows = engine.loc[prep_stage_sample.isna() | (prep_stage_sample < 0)].copy()
    status = "PASS" if invalid_prep_sample_rows.empty else "FAIL"
    add_check(
        audit_rows,
        "prep_stage_sample_count_numeric_non_negative",
        status,
        count=len(invalid_prep_sample_rows),
        details="prep_stage_sample_count is numeric and non-negative." if invalid_prep_sample_rows.empty else "Invalid prep_stage_sample_count values detected.",
        sample_rows=invalid_prep_sample_rows.head(10),
    )
    check_statuses.append(status)

    high_unproven_rows = engine.loc[(profile.eq("UNPROVEN_PROFILE")) & (risk_band.eq("HIGH"))].copy()
    status = "PASS" if high_unproven_rows.empty else "WARN"
    add_check(
        audit_rows,
        "suspicious_unproven_profile_high_risk",
        status,
        count=len(high_unproven_rows),
        details="No UNPROVEN_PROFILE rows marked HIGH risk." if high_unproven_rows.empty else "UNPROVEN_PROFILE + HIGH risk rows should be reviewed before UI exposure.",
        sample_rows=high_unproven_rows.head(10),
    )
    check_statuses.append(status)

    low_history_high_risk_rows = engine.loc[(history_runs.fillna(0) < 3) & (risk_band.eq("HIGH"))].copy()
    status = "PASS" if low_history_high_risk_rows.empty else "WARN"
    add_check(
        audit_rows,
        "suspicious_low_history_high_risk",
        status,
        count=len(low_history_high_risk_rows),
        details="No sub-3-history runners marked HIGH risk." if low_history_high_risk_rows.empty else "history_runs_used < 3 with HIGH risk should be reviewed.",
        sample_rows=low_history_high_risk_rows.head(10),
    )
    check_statuses.append(status)

    low_missing_peak_rows = engine.loc[(peak_start.isna() | peak_end.isna()) & (risk_band.eq("LOW"))].copy()
    status = "PASS" if low_missing_peak_rows.empty else "WARN"
    add_check(
        audit_rows,
        "suspicious_low_risk_missing_peak_window",
        status,
        count=len(low_missing_peak_rows),
        details="All LOW risk rows have a peak window." if low_missing_peak_rows.empty else "LOW risk rows missing peak window should be reviewed.",
        sample_rows=low_missing_peak_rows.head(10),
    )
    check_statuses.append(status)

    sample_fields = [
        "track",
        "race_no",
        "horse",
        "current_prep_stage",
        "prep_stage_label",
        "historical_peak_prep_stage",
        "peak_window_start",
        "peak_window_end",
        "campaign_profile",
        "campaign_risk_band",
        "history_runs_used",
        "prep_stage_sample_count",
        "evidence_status",
        "campaign_narrative",
    ]
    sample_frame = engine[sample_fields].copy()
    add_sample_group(audit_rows, "HIGH_RISK_SAMPLE", sample_frame.loc[risk_band.eq("HIGH")].head(10))
    add_sample_group(audit_rows, "LOW_RISK_SAMPLE", sample_frame.loc[risk_band.eq("LOW")].head(10))
    add_sample_group(audit_rows, "FRESH_SPECIALIST_SAMPLE", sample_frame.loc[profile.eq("FRESH_SPECIALIST")].head(10))
    add_sample_group(audit_rows, "FITNESS_BUILDER_SAMPLE", sample_frame.loc[profile.eq("FITNESS_BUILDER")].head(10))
    add_sample_group(audit_rows, "PEAK_AND_DROP_SAMPLE", sample_frame.loc[profile.eq("PEAK_AND_DROP")].head(10))
    add_sample_group(audit_rows, "DEEP_PREP_HORSE_SAMPLE", sample_frame.loc[profile.eq("DEEP_PREP_HORSE")].head(10))
    add_sample_group(audit_rows, "NO_HISTORY_SAMPLE", sample_frame.loc[evidence.eq("NO_HISTORY")].head(10))

    audit_df = pd.DataFrame(audit_rows)
    audit_df.to_csv(OUT_AUDIT_PATH, index=False)

    profile_counts = Counter(clean_text(engine["campaign_profile"]))
    risk_counts = Counter(clean_text(engine["campaign_risk_band"]))
    evidence_counts = Counter(clean_text(engine["evidence_status"]))
    suspicious_counts = Counter(
        {
            "UNPROVEN_PROFILE_HIGH": int(len(high_unproven_rows)),
            "NO_HISTORY_HIGH": int(len(high_no_history_rows)),
            "LOW_HISTORY_LT3_HIGH": int(len(low_history_high_risk_rows)),
            "LOW_RISK_MISSING_PEAK_WINDOW": int(len(low_missing_peak_rows)),
        }
    )

    pass_checks = sum(1 for status in check_statuses if status == "PASS")
    warn_checks = sum(1 for status in check_statuses if status == "WARN")
    fail_checks = sum(1 for status in check_statuses if status == "FAIL")

    if fail_checks > 0:
        readiness_verdict = "NOT_READY"
    elif warn_checks > 0:
        readiness_verdict = "READY_WITH_WARNINGS"
    else:
        readiness_verdict = "READY_FOR_UI_WIRE"

    summary_df = pd.DataFrame(
        [
            {
                "status": "EDGEIQ_CAMPAIGN_INTELLIGENCE_ENGINE_V1_1_QUALITY_AUDITED",
                "total_rows": int(len(engine)),
                "active_runner_rows": int(len(active_live)),
                "pass_checks": int(pass_checks),
                "warn_checks": int(warn_checks),
                "fail_checks": int(fail_checks),
                "profile_counts": serialise_counter(profile_counts),
                "risk_counts": serialise_counter(risk_counts),
                "evidence_counts": serialise_counter(evidence_counts),
                "suspicious_combination_counts": serialise_counter(suspicious_counts),
                "missing_required_columns": int(len(missing_columns)),
                "duplicate_rows": int(len(duplicate_rows)),
                "invalid_prep_stage_rows": int(len(invalid_prep_rows)),
                "invalid_peak_window_rows": int(len(invalid_peak_rows)),
                "invalid_risk_band_rows": int(len(invalid_risk_rows)),
                "invalid_campaign_profile_rows": int(len(invalid_profile_rows)),
                "invalid_evidence_status_rows": int(len(invalid_evidence_rows)),
                "no_history_high_risk_rows": int(len(high_no_history_rows)),
                "unproven_profile_high_risk_rows": int(len(high_unproven_rows)),
                "low_history_high_risk_rows": int(len(low_history_high_risk_rows)),
                "low_risk_missing_peak_window_rows": int(len(low_missing_peak_rows)),
                "missing_narrative_non_no_history_rows": int(len(missing_narrative_rows)),
                "history_runs_invalid_rows": int(len(invalid_history_runs_rows)),
                "prep_stage_sample_invalid_rows": int(len(invalid_prep_sample_rows)),
                "readiness_verdict": readiness_verdict,
                "built_at": BUILT_AT,
            }
        ]
    )
    summary_df.to_csv(OUT_SUMMARY_PATH, index=False)

    print("[CAMPAIGN_INTELLIGENCE_V1_1_QUALITY] COMPLETE")
    print(f"audit={OUT_AUDIT_PATH}")
    print(f"summary={OUT_SUMMARY_PATH}")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
