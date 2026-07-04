from pathlib import Path
import csv
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUTPUT = DATA / "EDGEIQ_MASTER_CANDIDATE_OPERATING_GUIDE_V1.txt"
SUMMARY = DATA / "edgeiq_master_candidate_operating_guide_v1_summary.csv"


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(rows)


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    text = """EDGEiQ Master Candidate Operating Guide V1
==========================================

Purpose
-------
EDGEiQ_RACING_MASTER_CANDIDATE is the clean operational reference and future working-app candidate. It is not the live working folder yet. The original racing-dashboard remains the current working application until a separate explicit cutover is approved.

Current Working Rule
--------------------
- Current live working folder: C:\\Users\\trent\\OneDrive\\Documents\\horse_racing_model\\dashboard\\racing-dashboard
- Clean staging mirror: C:\\Users\\trent\\OneDrive\\Documents\\horse_racing_model\\dashboard\\EDGEiQ_RACING_STAGING_CLEAN_V1
- Master candidate: C:\\Users\\trent\\OneDrive\\Documents\\horse_racing_model\\dashboard\\EDGEiQ_RACING_MASTER_CANDIDATE
- Do not point the app, scripts, browser, or production workflow at the master candidate until explicit cutover approval.

Active File Discipline
----------------------
Do not add research files, candidate feeds, checkpoints, screenshots, scratch files, or one-off audit outputs directly into active folders in the clean structure. The active folders should contain only files that have been accepted into the active manifest.

Source Of Truth
---------------
- Active file manifest: public/data/edgeiq_master_candidate_promotion_plan_v1_manifest.csv
- Active build chain manifest: public/data/edgeiq_active_build_chain_manifest_v1.csv

The active file manifest defines what belongs in staging and master. The active build chain manifest defines the run order and operational dependencies. If a file is not in the active manifest, it is not part of the clean master candidate.

How To Add A New Production Engine
----------------------------------
1. Build as research/audit first inside the original racing-dashboard.
2. Output CSV, summary, and report files.
3. Validate data quality, joins, leakage, counts, and build safety.
4. If approved for active use, add the script to the active build chain manifest.
5. Add required active outputs and dependencies to the active file manifest.
6. Rebuild staging and master candidate from the manifest.
7. Re-run standalone validation before any cutover consideration.

Research And Candidate Outputs
------------------------------
Research outputs remain in the original working folder unless promoted. Candidate feeds must not become active simply because they exist. Promotion requires an audit result, explicit approval, manifest update, and clean rebuild.

Checkpoints And Backups
-----------------------
Checkpoints remain useful for development safety but should not be carried into the clean active folders unless explicitly classified as active migration documentation. Avoid copying checkpoint feeds into master candidate active folders.

Gear Source Blocker
-------------------
Historical Gear Intelligence backend is built, but current gear live feed remains blocked because the June 25-27 current gear source is missing or stale. Do not treat NO_GEAR as a negative horse signal. It is a source availability state.

When current gear source is refreshed, rerun:
python .\\scripts\\build_edgeiq_current_gear_live_join_v1.py
python .\\scripts\\apply_edgeiq_current_gear_to_governed_board_v1.py
python .\\scripts\\build_edgeiq_gear_profile_engine_v1.py
python .\\scripts\\build_edgeiq_gear_signal_engine_v1.py
python .\\scripts\\build_edgeiq_intelligence_mode_engine_v2.py
python .\\scripts\\build_edgeiq_runner_drawer_feed_v3.py

Market Source Blocker
---------------------
Current live market rows are missing or sparse for most races. Market alignment can remain safe, but current NO_MARKET_DATA should be treated as source missing, not as a negative market signal.

Avoiding Stale Files
--------------------
- Never append recovery rows to active feeds.
- Never rely on stale candidates when a governed source has changed.
- Rebuild from active source manifests instead of copying folder contents by habit.
- Any master candidate rebuild must be copy-only from the clean manifest and hash-validated.

Operational Recommendation
--------------------------
Keep racing-dashboard as the active working folder for now. Use EDGEiQ_RACING_MASTER_CANDIDATE as the clean reference mirror and future working-app candidate. Promote to a new working app only after repeated validation passes and explicit cutover approval.

Safety Confirmations
--------------------
Production changed: NO
Pricing changed: NO
Probability changed: NO
V6.1 changed: NO
V7.2G2 changed: NO
UI changed: NO
App pointed at master: NO
"""
    OUTPUT.write_text(text, encoding="utf-8")
    write_csv(SUMMARY, [
        {"metric": "status", "value": "MASTER_CANDIDATE_OPERATING_GUIDE_CREATED"},
        {"metric": "output", "value": str(OUTPUT)},
        {"metric": "original_racing_dashboard_remains_working_folder", "value": "YES"},
        {"metric": "master_candidate_is_reference_only", "value": "YES"},
        {"metric": "app_pointed_to_master", "value": "NO"},
        {"metric": "production_changed", "value": "NO"},
        {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
    ])
    print("MASTER_CANDIDATE_OPERATING_GUIDE_CREATED")


if __name__ == "__main__":
    main()
