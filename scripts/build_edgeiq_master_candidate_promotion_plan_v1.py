from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
READINESS_SUMMARY = DATA / "edgeiq_master_promotion_readiness_v1_summary.csv"
V2_MANIFEST = DATA / "edgeiq_repository_safe_migration_plan_v2_active_copy_manifest.csv"
STAGING_ROOT = ROOT.parent / "EDGEiQ_RACING_STAGING_CLEAN_V1"
MASTER_ROOT = ROOT.parent / "EDGEiQ_RACING_MASTER_CANDIDATE"
OUT_TXT = DATA / "EDGEIQ_MASTER_CANDIDATE_PROMOTION_PLAN_V1.txt"
OUT_SUMMARY = DATA / "edgeiq_master_candidate_promotion_plan_v1_summary.csv"
OUT_MANIFEST = DATA / "edgeiq_master_candidate_promotion_plan_v1_manifest.csv"

VALIDATION_ARTIFACT_PATTERNS = ["node_modules", "dist", "tsconfig.tsbuildinfo", "__pycache__"]


def load_metric(path):
    if not path.exists():
        return {}
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    if "metric" in df.columns and "value" in df.columns:
        return {str(r["metric"]): str(r["value"]) for _, r in df.iterrows()}
    return {}


def staging_path_from_copy_to(copy_to):
    parts = [p for p in str(copy_to).replace("\\", "/").split("/") if p]
    if parts and parts[0].upper() == "EDGEIQ_RACING":
        parts = parts[1:]
    return STAGING_ROOT.joinpath(*parts)


def master_path_from_copy_to(copy_to):
    parts = [p for p in str(copy_to).replace("\\", "/").split("/") if p]
    if parts and parts[0].upper() == "EDGEIQ_RACING":
        parts = parts[1:]
    return MASTER_ROOT.joinpath(*parts)


def main():
    readiness = load_metric(READINESS_SUMMARY)
    ready = readiness.get("verdict") == "READY_FOR_MASTER_CANDIDATE_PLAN"
    v2 = pd.read_csv(V2_MANIFEST, dtype=str, keep_default_na=False)
    rows = []
    for i, r in v2.iterrows():
        staging_src = staging_path_from_copy_to(r.get("copy_to", ""))
        master_dst = master_path_from_copy_to(r.get("copy_to", ""))
        rows.append({
            "step_no": i + 1,
            "staging_source_path": str(staging_src),
            "master_candidate_target_path": str(master_dst),
            "source_manifest_path": r.get("source_path", ""),
            "keep_reason": r.get("keep_reason", ""),
            "expected_sha256": r.get("source_sha256", ""),
            "copy_action": "PLAN_ONLY_COPY_AFTER_APPROVAL",
            "preserve_directory_structure": "YES",
            "exclude_validation_artifacts": "YES",
            "master_candidate_creation_approved": "NO",
        })
    manifest = pd.DataFrame(rows)
    manifest.to_csv(OUT_MANIFEST, index=False)
    reasons = manifest["keep_reason"].value_counts().to_dict()
    summary_rows = [
        {"metric": "status", "value": "MASTER_CANDIDATE_PROMOTION_PLAN_CREATED"},
        {"metric": "readiness_verdict", "value": readiness.get("verdict", "MISSING")},
        {"metric": "ready_for_plan", "value": "YES" if ready else "NO"},
        {"metric": "master_candidate_creation_approved", "value": "NO"},
        {"metric": "future_master_path", "value": str(MASTER_ROOT)},
        {"metric": "staging_source_path", "value": str(STAGING_ROOT)},
        {"metric": "planned_active_file_count", "value": len(manifest)},
        {"metric": "expected_hash_validation", "value": f"{len(manifest)}/{len(manifest)}"},
        {"metric": "expected_extra_active_files", "value": 0},
        {"metric": "copy_only", "value": "YES"},
        {"metric": "production_changed", "value": "NO"},
        {"metric": "original_racing_dashboard_changed", "value": "NO_EXCEPT_PLANNING_OUTPUTS"},
        {"metric": "staging_changed", "value": "NO"},
        {"metric": "files_moved", "value": "NO"},
        {"metric": "files_deleted", "value": "NO"},
        {"metric": "app_pointed_to_master", "value": "NO"},
        {"metric": "pricing_changed", "value": "NO"},
        {"metric": "probability_changed", "value": "NO"},
        {"metric": "v6_1_changed", "value": "NO"},
        {"metric": "v7_2g2_changed", "value": "NO"},
        {"metric": "ui_changed", "value": "NO"},
        {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
    ]
    for k, v in sorted(reasons.items()):
        summary_rows.append({"metric": f"manifest_{k}", "value": int(v)})
    pd.DataFrame(summary_rows).to_csv(OUT_SUMMARY, index=False)

    lines = [
        "EDGEIQ_MASTER_CANDIDATE_PROMOTION_PLAN_V1",
        "=========================================",
        "Status: PLAN_ONLY_MASTER_CANDIDATE_NOT_CREATED",
        "",
        "Future master path:",
        str(MASTER_ROOT),
        "",
        "Source staging path:",
        str(STAGING_ROOT),
        "",
        "Readiness basis:",
        f"- Readiness verdict: {readiness.get('verdict', 'MISSING')}",
        "- Staging validation already passed.",
        "- Corrected V2 manifest contains 145 active files.",
        "- Staging active payload hash validation passed 145/145.",
        "",
        "Promotion approach:",
        "- Copy-only from EDGEiQ_RACING_STAGING_CLEAN_V1.",
        "- Do not modify original racing-dashboard.",
        "- Do not delete existing staging folders.",
        "- Do not point app at master candidate until separately approved.",
        "- Preserve directory structure exactly from the corrected V2 manifest.",
        "- Preserve these top-level folders: 01_app, 02_scripts_active, 03_data_active, 08_docs.",
        "- Exclude validation artifacts: node_modules, dist, tsconfig.tsbuildinfo, __pycache__.",
        "- Optionally allow a later validation script to regenerate node_modules/dist inside master candidate.",
        "",
        "Exact copy sequence after approval:",
        "1. Confirm EDGEiQ_RACING_MASTER_CANDIDATE does not already exist, or stop for manual decision.",
        "2. Create the empty master candidate folder.",
        "3. Read edgeiq_master_candidate_promotion_plan_v1_manifest.csv.",
        "4. For each manifest row, copy staging_source_path to master_candidate_target_path.",
        "5. Preserve timestamps and directory structure with Copy-Item / shutil.copy2 semantics.",
        "6. Do not copy any file outside the manifest.",
        "7. Do not copy node_modules, dist, tsconfig.tsbuildinfo, or __pycache__.",
        "8. Hash validate every copied file against expected_sha256.",
        "9. Confirm expected file count is exactly 145.",
        "10. Confirm extra active files count is 0.",
        "",
        "Expected results:",
        "- Expected file count: 145 active files.",
        "- Expected hash validation: 145/145.",
        "- Expected extra active files: 0.",
        "- Master candidate is not production until separately validated and approved.",
        "",
        "Post-copy validation steps:",
        "1. Validate package/config files under 01_app.",
        "2. Run npm install inside master candidate 01_app only if node_modules is absent and package/package-lock exist.",
        "3. Run npm run build inside master candidate 01_app.",
        "4. Run python -m py_compile on all scripts in 02_scripts_active.",
        "5. Validate 03_data_active files exist.",
        "6. Compare all 145 hashes against this promotion manifest.",
        "7. Confirm unexpected extra active files remain 0, excluding validation artifacts created by install/build/compile.",
        "8. Write validation outputs back to original racing-dashboard public/data unless otherwise approved.",
        "",
        "Rollback/no-op safety strategy:",
        "- Because this is copy-only, rollback is simply to stop using the master candidate.",
        "- Do not delete the master candidate automatically if validation fails; report failures for review.",
        "- Keep original racing-dashboard untouched as the working app.",
        "- Keep EDGEiQ_RACING_STAGING_CLEAN_V1 untouched as the validated source mirror.",
        "",
        "Risks:",
        "- If master candidate is flattened or paths are rewritten too early, app /data fetches and scripts using public/data can break.",
        "- node_modules and dist are validation artifacts, not active source files.",
        "- Research/candidate/checkpoint files should not enter the active master without a new manifest update.",
        "- Gear live feed remains blocked until current gear source refresh is available.",
        "",
        "Approval gates:",
        "Gate 1: Explicit approval to create EDGEiQ_RACING_MASTER_CANDIDATE.",
        "Gate 2: Master candidate copy hash validation 145/145.",
        "Gate 3: Master candidate npm build passes.",
        "Gate 4: Active scripts compile 13/13.",
        "Gate 5: App is still not pointed at master until explicit promotion approval.",
        "",
        "Boundaries:",
        "- Master candidate creation approved: NO",
        "- Production changed: NO",
        "- Original racing-dashboard changed: NO except new planning scripts/reports",
        "- Staging changed: NO",
        "- Files moved/deleted: NO",
        "- Pricing/probability/V6.1/V7.2G2/UI changed: NO",
        f"Built at: {datetime.now(timezone.utc).isoformat()}",
    ]
    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("MASTER_CANDIDATE_PROMOTION_PLAN_CREATED", len(manifest), ready)


if __name__ == "__main__":
    main()
