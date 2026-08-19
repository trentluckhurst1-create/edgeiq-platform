from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import re

DATA = Path("public/data")
VALIDATION_SUMMARY = DATA / "edgeiq_racing_staging_clean_v1_validation_summary.csv"
HASH_VALIDATION = DATA / "edgeiq_racing_staging_clean_v1_hash_validation.csv"
ACTIVE_MANIFEST = DATA / "edgeiq_repository_safe_migration_plan_v2_active_copy_manifest.csv"
BUILD_CHAIN = DATA / "edgeiq_active_build_chain_manifest_v1.csv"
COPY_SUMMARY = DATA / "edgeiq_racing_staging_clean_v1_summary.csv"
OUT = DATA / "edgeiq_master_promotion_readiness_v1.csv"
SUMMARY = DATA / "edgeiq_master_promotion_readiness_v1_summary.csv"
REPORT = DATA / "edgeiq_master_promotion_readiness_v1_report.txt"

BLOCKED_NAME_TOKENS = ["CHECKPOINT", "CANDIDATE", "BACKUP", "PRE_", "RECOVERY", "STAGING", "PREVIEW", "BEFORE"]


def load_metric(path):
    if not path.exists():
        return {}
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    if "metric" in df.columns and "value" in df.columns:
        return {str(r["metric"]): str(r["value"]) for _, r in df.iterrows()}
    return {}


def as_int(v, default=0):
    try:
        return int(float(str(v).strip()))
    except Exception:
        return default


def yes(status):
    return "PASS" if status else "FAIL"


def check_row(check, expected, actual, passed, details=""):
    return {
        "check": check,
        "expected": expected,
        "actual": actual,
        "status": yes(passed),
        "details": details,
    }


def manifest_has_blocked_names(df):
    bad = []
    for _, row in df.iterrows():
        fields = "|".join(str(row.get(c, "")) for c in ["source_path", "file_name", "copy_to"])
        upper = fields.upper()
        if any(tok in upper for tok in BLOCKED_NAME_TOKENS):
            bad.append(str(row.get("source_path", row.get("file_name", ""))))
    return bad


def main():
    validation = load_metric(VALIDATION_SUMMARY)
    copy_summary = load_metric(COPY_SUMMARY)
    rows = []
    rows.append(check_row("staging_validation_pass_exists", "EDGEIQ_RACING_STAGING_CLEAN_V1_VALIDATION_PASS", validation.get("status", "MISSING"), validation.get("status") == "EDGEIQ_RACING_STAGING_CLEAN_V1_VALIDATION_PASS", str(VALIDATION_SUMMARY)))
    rows.append(check_row("hash_pass_145_of_145", "145 pass / 0 fail", f"{validation.get('manifest_hash_pass', 'MISSING')} pass / {validation.get('manifest_hash_fail', 'MISSING')} fail", as_int(validation.get("manifest_hash_pass")) == 145 and as_int(validation.get("manifest_hash_fail")) == 0, str(HASH_VALIDATION)))
    rows.append(check_row("active_scripts_compile_passed", "13", validation.get("python_scripts_checked", "MISSING"), as_int(validation.get("python_scripts_checked")) == 13 and as_int(validation.get("fail_rows")) == 0, "Validation summary reported all rows passing."))
    rows.append(check_row("active_data_files_present", "15", validation.get("active_data_files_checked", "MISSING"), as_int(validation.get("active_data_files_checked")) == 15, "Active data files were hash-checked in validation."))
    rows.append(check_row("npm_build_passed", "PASS", validation.get("npm_build_status", "MISSING"), validation.get("npm_build_status") == "PASS", "Staging app build passed."))
    rows.append(check_row("extra_active_files_zero", "0", validation.get("unexpected_extra_files_excluding_validation_artifacts", "MISSING"), as_int(validation.get("unexpected_extra_files_excluding_validation_artifacts")) == 0, "Validation artifacts are excluded by design."))
    rows.append(check_row("source_missing_rows_zero", "0", copy_summary.get("source_missing_rows", validation.get("source_missing_rows", "0")), as_int(copy_summary.get("source_missing_rows", validation.get("source_missing_rows", 0))) == 0, str(COPY_SUMMARY)))
    rows.append(check_row("hash_failures_zero", "0", validation.get("manifest_hash_fail", "MISSING"), as_int(validation.get("manifest_hash_fail")) == 0, str(HASH_VALIDATION)))

    hash_df = pd.read_csv(HASH_VALIDATION, dtype=str, keep_default_na=False) if HASH_VALIDATION.exists() else pd.DataFrame()
    hash_pass_count = int((hash_df.get("validation_status", pd.Series(dtype=str)) == "PASS").sum()) if not hash_df.empty else 0
    hash_fail_count = int((hash_df.get("validation_status", pd.Series(dtype=str)) != "PASS").sum()) if not hash_df.empty else 999
    rows.append(check_row("hash_validation_file_145_pass", "145 PASS rows", f"{hash_pass_count} PASS / {hash_fail_count} non-pass", hash_pass_count == 145 and hash_fail_count == 0, str(HASH_VALIDATION)))

    manifest_df = pd.read_csv(ACTIVE_MANIFEST, dtype=str, keep_default_na=False) if ACTIVE_MANIFEST.exists() else pd.DataFrame()
    rows.append(check_row("active_manifest_exists", "145 rows", str(len(manifest_df)) if ACTIVE_MANIFEST.exists() else "MISSING", ACTIVE_MANIFEST.exists() and len(manifest_df) == 145, str(ACTIVE_MANIFEST)))
    blocked = manifest_has_blocked_names(manifest_df) if not manifest_df.empty else []
    rows.append(check_row("no_checkpoint_candidate_backup_files_in_active_manifest", "0 blocked-name rows", str(len(blocked)), len(blocked) == 0, "Examples: " + "|".join(blocked[:10]) if blocked else "No blocked names found."))

    chain_df = pd.read_csv(BUILD_CHAIN, dtype=str, keep_default_na=False) if BUILD_CHAIN.exists() else pd.DataFrame()
    missing_scripts = []
    if not chain_df.empty and "script_exists" in chain_df.columns:
        missing_scripts = chain_df[chain_df["script_exists"] != "YES"]["script"].tolist()
    rows.append(check_row("active_build_chain_manifest_exists", "13 rows / 0 missing scripts", f"{len(chain_df)} rows / {len(missing_scripts)} missing scripts" if BUILD_CHAIN.exists() else "MISSING", BUILD_CHAIN.exists() and len(chain_df) == 13 and len(missing_scripts) == 0, str(BUILD_CHAIN)))

    pass_count = sum(1 for r in rows if r["status"] == "PASS")
    fail_count = len(rows) - pass_count
    verdict = "READY_FOR_MASTER_CANDIDATE_PLAN" if fail_count == 0 else "NOT_READY"
    pd.DataFrame(rows).to_csv(OUT, index=False)
    summary_rows = [
        {"metric": "verdict", "value": verdict},
        {"metric": "checks", "value": len(rows)},
        {"metric": "pass_count", "value": pass_count},
        {"metric": "fail_count", "value": fail_count},
        {"metric": "staging_validation_status", "value": validation.get("status", "MISSING")},
        {"metric": "hash_pass", "value": validation.get("manifest_hash_pass", "")},
        {"metric": "hash_fail", "value": validation.get("manifest_hash_fail", "")},
        {"metric": "active_manifest_rows", "value": len(manifest_df)},
        {"metric": "active_build_chain_rows", "value": len(chain_df)},
        {"metric": "master_candidate_creation_approved", "value": "NO"},
        {"metric": "production_changed", "value": "NO"},
        {"metric": "pricing_changed", "value": "NO"},
        {"metric": "probability_changed", "value": "NO"},
        {"metric": "v6_1_changed", "value": "NO"},
        {"metric": "v7_2g2_changed", "value": "NO"},
        {"metric": "ui_changed", "value": "NO"},
        {"metric": "files_moved", "value": "NO"},
        {"metric": "files_deleted", "value": "NO"},
        {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
    ]
    pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)
    lines = [
        "EDGEIQ_MASTER_PROMOTION_READINESS_V1",
        "======================================",
        f"Verdict: {verdict}",
        f"Checks: {len(rows)}",
        f"Pass: {pass_count}",
        f"Fail: {fail_count}",
        "",
        "Check details:",
    ]
    for r in rows:
        lines.append(f"- {r['check']}: {r['status']} ({r['actual']})")
    lines.extend([
        "",
        "Boundary confirmations:",
        "- Master candidate creation approved: NO",
        "- Production changed: NO",
        "- Pricing/probability/V6.1/V7.2G2/UI changed: NO",
        "- Files moved/deleted: NO",
    ])
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("MASTER_PROMOTION_READINESS", verdict, pass_count, fail_count)


if __name__ == "__main__":
    main()
