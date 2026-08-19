from __future__ import annotations
import argparse, csv, hashlib, json
from pathlib import Path
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DOCS=ROOT/"docs/performance-intelligence/racingcom-ingestion-v2"
OUT=DOCS/"edgeiq_racingcom_graphql_rollback_dry_run_v1.csv"
REPORT=DOCS/"edgeiq_racingcom_graphql_rollback_report_v1.md"
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--manifest",required=True); ap.add_argument("--execute",action="store_true"); args=ap.parse_args()
    mp=ROOT/args.manifest if not Path(args.manifest).is_absolute() else Path(args.manifest)
    rows=[]; status="DRY_RUN_READY"
    if not mp.exists(): status="BLOCKED_MANIFEST_MISSING"; manifest={}
    else: manifest=json.loads(mp.read_text(encoding="utf-8"))
    backup=ROOT/manifest.get("backup_destination","") if manifest else Path("")
    rows.append({"item":"manifest","value":str(mp),"status":"PASS" if mp.exists() else "BLOCKED","detail":"Explicit manifest required; no guessing."})
    rows.append({"item":"backup","value":str(backup),"status":"PENDING_APPROVED_BACKUP" if not backup.exists() else "PASS","detail":"Dry run does not require backup to exist before migration."})
    rows.append({"item":"execute","value":str(args.execute),"status":"DRY_RUN" if not args.execute else "BLOCKED","detail":"Rollback execute not performed in review package."})
    with OUT.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["item","value","status","detail"]); w.writeheader(); w.writerows(rows)
    REPORT.write_text("# Rollback dry run\n\nRollback requires an explicit backup manifest and does not guess backup files. No rollback executed.\n",encoding="utf-8")
    print(json.dumps({"status":status,"rollback_executed":"NO"})); return 0 if not args.execute else 2
if __name__=="__main__": raise SystemExit(main())
