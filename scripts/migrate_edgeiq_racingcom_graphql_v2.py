from __future__ import annotations
import argparse, csv, hashlib, json, shutil
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DOCS=ROOT/"docs/performance-intelligence/racingcom-ingestion-v2"
PROD=ROOT/"public/data/edgeiq_racingcom_performance_warehouse_v2.csv"
CAND=ROOT/"public/data/edgeiq_racingcom_performance_warehouse_v2_RUNNER_CANDIDATE.csv"
DRY=DOCS/"edgeiq_racingcom_graphql_migration_dry_run_v1.csv"
MANIFEST=DOCS/"edgeiq_racingcom_graphql_migration_manifest_preview_v1.json"
REPORT=DOCS/"edgeiq_racingcom_graphql_migration_dry_run_report_v1.md"
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""
def write_csv(rows):
    with DRY.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["item","value","status","detail"]); w.writeheader(); w.writerows(rows)
def gates_pass():
    p=DOCS/"edgeiq_racingcom_graphql_human_migration_review_audit_summary_v1.json"
    return p.exists() and json.loads(p.read_text(encoding="utf-8")).get("decision")=="HUMAN_MIGRATION_REVIEW_PACKAGE_PASS"
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--execute",action="store_true"); args=ap.parse_args()
    ts=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup=DOCS/"migration-backups"/f"edgeiq_racingcom_performance_warehouse_v2_{ts}.csv"
    manifest={"mode":"EXECUTE" if args.execute else "DRY_RUN","source_candidate":str(CAND.relative_to(ROOT)),"target_production_path":str(PROD.relative_to(ROOT)),"backup_destination":str(backup.relative_to(ROOT)),"candidate_sha256":sha(CAND),"current_production_sha256":sha(PROD),"expected_promoted_sha256":sha(CAND),"files_to_modify":[str(PROD.relative_to(ROOT))],"files_to_preserve":["production orchestration","legacy ingestion scripts"],"orchestration_changes_proposed":[],"post_migration_checks":["hash promoted file","rerun production audits","validate historical retention"],"rollback_trigger_conditions":["hash mismatch","audit failure","schema/grain incompatibility"]}
    rows=[{"item":k,"value":json.dumps(v) if isinstance(v,(list,dict)) else v,"status":"DRY_RUN" if not args.execute else "PENDING","detail":"Preview only; no migration performed by default."} for k,v in manifest.items()]
    if args.execute and not gates_pass():
        rows.append({"item":"execute_refused","value":"GATES_NOT_APPROVED","status":"BLOCKED","detail":"Human review gate or explicit approval missing."}); write_csv(rows); MANIFEST.write_text(json.dumps(manifest,indent=2),encoding="utf-8"); REPORT.write_text("# Migration dry run\n\nExecute refused or preview generated.\n",encoding="utf-8"); return 2
    if args.execute:
        backup.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(PROD,backup); tmp=PROD.with_suffix(".csv.tmp"); shutil.copy2(CAND,tmp); tmp.replace(PROD)
        rows.append({"item":"execute_result","value":"PROMOTED","status":"EXECUTED","detail":"Promotion executed after gates passed."})
    write_csv(rows); MANIFEST.write_text(json.dumps(manifest,indent=2),encoding="utf-8"); REPORT.write_text("# Migration dry run\n\nDefault mode is DRY RUN. No migration executed unless --execute is supplied and gates pass.\n",encoding="utf-8"); print(json.dumps({"status":"DRY_RUN_COMPLETE" if not args.execute else "EXECUTE_ATTEMPTED","production_changed":"NO" if not args.execute else "SEE_RESULT"})); return 0
if __name__=="__main__": raise SystemExit(main())
