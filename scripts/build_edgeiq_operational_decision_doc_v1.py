from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

DATA = Path("public/data")
BUILD_CHAIN = DATA / "edgeiq_active_build_chain_manifest_v1.csv"
READINESS_SUMMARY = DATA / "edgeiq_master_promotion_readiness_v1_summary.csv"
PROMOTION_SUMMARY = DATA / "edgeiq_master_candidate_promotion_plan_v1_summary.csv"
OUT = DATA / "EDGEIQ_OPERATIONAL_DECISION_DOC_V1.txt"


def metric(path):
    if not path.exists():
        return {}
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    if "metric" in df.columns and "value" in df.columns:
        return {str(r["metric"]): str(r["value"]) for _, r in df.iterrows()}
    return {}


def main():
    readiness = metric(READINESS_SUMMARY)
    promotion = metric(PROMOTION_SUMMARY)
    chain = pd.read_csv(BUILD_CHAIN, dtype=str, keep_default_na=False) if BUILD_CHAIN.exists() else pd.DataFrame()
    chain_lines = []
    if not chain.empty:
        for _, r in chain.iterrows():
            chain_lines.append(f"{r.get('step_no')}. {r.get('script')} - {r.get('purpose')}")
    else:
        chain_lines.append("Active build chain manifest missing; rebuild edgeiq_active_build_chain_manifest_v1.csv before operational promotion.")

    lines = [
        "EDGEIQ_OPERATIONAL_DECISION_DOC_V1",
        "==================================",
        "Status: DECISION_DOCUMENT_ONLY_NO_PRODUCTION_CHANGE",
        "",
        "Current validated state:",
        "- EDGEiQ_RACING_STAGING_CLEAN_V1 exists and validated as a standalone staging mirror.",
        "- Staging validation status: EDGEIQ_RACING_STAGING_CLEAN_V1_VALIDATION_PASS.",
        f"- Master promotion readiness verdict: {readiness.get('verdict', 'MISSING')}",
        f"- Master candidate creation approved: {promotion.get('master_candidate_creation_approved', 'NO')}",
        "- App is still not pointed at staging or master candidate.",
        "",
        "Recommended future workflow:",
        "Option A - Recommended first:",
        "Keep racing-dashboard as the working app and use EDGEiQ_RACING_MASTER_CANDIDATE as a clean reference mirror once explicitly approved and created.",
        "This keeps existing /data fetches, public/data paths, npm workflow, and script relative paths stable while giving Codex a clean operational reference.",
        "",
        "Option B - Later only after repeated successful builds:",
        "Promote EDGEiQ_RACING_MASTER_CANDIDATE to the new working app after path/config validation, repeated npm builds, active script compile checks, and data hash validation.",
        "Do not switch to Option B until the master candidate has survived more than one full build/refresh cycle without path drift.",
        "",
        "Recommendation:",
        "Use Option A first. Move to Option B only after repeated successful builds and explicit approval.",
        "",
        "Where future Codex work should happen:",
        "- Short term: continue work in the original racing-dashboard workspace.",
        "- Treat EDGEiQ_RACING_STAGING_CLEAN_V1 and future EDGEiQ_RACING_MASTER_CANDIDATE as clean mirrors/reference structures, not the live working app.",
        "- If a task asks to update active manifests or promote files, update the planning/audit manifests first and do not copy/move until approved.",
        "",
        "How to avoid stale candidate files:",
        "- Never add files with CANDIDATE, STAGING, PREVIEW, RECOVERY, BACKUP, CHECKPOINT, PRE_, or BEFORE to the active manifest unless explicitly promoted.",
        "- Keep research outputs in research/audit buckets until a separate promotion gate passes.",
        "- Use hash validation to prove active copies match their source manifest.",
        "- Do not use broad filename matching as a deletion rule; unknown files require manual review.",
        "",
        "Active build chain source of truth:",
        "- The active build chain is public/data/edgeiq_active_build_chain_manifest_v1.csv.",
        "- Current active chain steps:",
        *chain_lines,
        "",
        "How to handle research outputs:",
        "- Research outputs stay outside active production manifests by default.",
        "- Every research build should produce CSV + summary + report.",
        "- Promote research only after leakage, calibration, build, and UI/path gates are passed.",
        "- Do not wire research outputs to UI or pricing without a dedicated approved promotion task.",
        "",
        "How to handle checkpoints/backups:",
        "- Keep checkpoints/backups for traceability, but exclude them from active mirror manifests.",
        "- Archive them only after a separate archive plan is approved.",
        "- Do not delete checkpoints automatically.",
        "",
        "How to add new engines:",
        "1. Build as research/audit first.",
        "2. Produce CSV + summary + report.",
        "3. Add to active build chain only after readiness gates pass.",
        "4. Update edgeiq_active_build_chain_manifest_v1.csv and the V2 active copy manifest generator.",
        "5. Rebuild staging/master planning manifests and hash-validate.",
        "6. Only then consider UI wiring or production promotion if explicitly approved.",
        "",
        "How to update the active manifest:",
        "- Update the manifest generator script, not the CSV by hand.",
        "- Rebuild edgeiq_repository_safe_migration_plan_v2_active_copy_manifest.csv.",
        "- Confirm no checkpoint/candidate/backup-like names enter the active manifest.",
        "- Confirm expected active file count and hashes before copying.",
        "",
        "Keeping old racing-dashboard as legacy/archive after promotion:",
        "- If Option B is later approved, keep the old racing-dashboard read-only as a legacy/archive workspace for at least one full successful master-candidate cycle.",
        "- Do not delete the old workspace until a separate archive/delete approval exists.",
        "- Keep a handover note pointing to the promoted root, active build manifest, and latest validation reports.",
        "",
        "Current gear live blocker:",
        "- Historical Gear Intelligence backend is built.",
        "- Current gear feed is blocked because no June 25-27 gear source exists.",
        "- Do not treat NO_GEAR as negative.",
        "- Gear activates only once current gear source is refreshed.",
        "- Required rerun sequence after gear refresh:",
        "  python .\\scripts\\build_edgeiq_current_gear_live_join_v1.py",
        "  python .\\scripts\\apply_edgeiq_current_gear_to_governed_board_v1.py",
        "  python .\\scripts\\build_edgeiq_gear_profile_engine_v1.py",
        "  python .\\scripts\\build_edgeiq_gear_signal_engine_v1.py",
        "  python .\\scripts\\build_edgeiq_intelligence_mode_engine_v2.py",
        "  python .\\scripts\\build_edgeiq_runner_drawer_feed_v3.py",
        "",
        "Operational boundaries:",
        "- Production changed: NO",
        "- Original racing-dashboard changed: NO except planning scripts/reports",
        "- Staging changed: NO",
        "- Files moved/deleted: NO",
        "- App pointed at staging/master: NO",
        "- Pricing/probability/V6.1/V7.2G2/UI changed: NO",
        f"Built at: {datetime.now(timezone.utc).isoformat()}",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("OPERATIONAL_DECISION_DOC_CREATED", OUT)


if __name__ == "__main__":
    main()
