from __future__ import annotations
import csv,json,shutil
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs'/'performance-intelligence'/'identity-profiler-v1'
ARCH=ROOT/'docs'/'performance-intelligence'/'identity-profiler-v1-archive'/datetime.now(timezone.utc).strftime('legacy_%Y%m%dT%H%M%SZ')
CANONICAL={ROOT/'build_edgeiq_identity_repository_profiler_v1.py',ROOT/'scripts'/'run_edgeiq_identity_repository_profiler_v1.py',ROOT/'scripts'/'audit_edgeiq_identity_profiler_final_state_v1.py',ROOT/'scripts'/'build_edgeiq_identity_repository_profiler_final_v1.py',ROOT/'scripts'/'promote_edgeiq_identity_repository_profiler_v1.py',ROOT/'scripts'/'cleanup_edgeiq_identity_profiler_legacy_v1.py'}
PATTERNS=['build_edgeiq_identity_repository_profiler_v1_STEP*_CUMULATIVE.py','build_edgeiq_identity_repository_profiler_v1_STEP108_HEAVY_CHECKPOINT.py','patch_edgeiq_identity_profiler_step*.py','inspect_edgeiq_identity_profiler_step*.py','inspect_edgeiq_profiler_step*.py','diagnose_edgeiq_identity_profiler_step*.py']
STALE_OUTPUTS=['edgeiq_crosswalk_candidates_v1.csv','EDGEIQ_IDENTITY_REPOSITORY_PROFILER_V1_AUDIT.json','EDGEIQ_IDENTITY_REPOSITORY_PROFILER_V1_AUDIT.md','edgeiq_identity_column_profiles_v1.csv','edgeiq_identity_dataset_profiles_v1.csv','edgeiq_identity_relationships_v1.csv','edgeiq_identity_repository_checkpoint_v1.json']
def classify(p):
    n=p.name.lower()
    if 'patch' in n: return 'PATCH_GENERATOR'
    if 'inspect' in n or 'diagnose' in n: return 'FORENSIC_TOOL'
    if 'step' in n: return 'SUPERSEDED'
    if 'crosswalk_candidates_v1.csv' in n: return 'FAILED_RUN'
    return 'STALE_OUTPUT'
def main():
    audit=json.loads((OUT/'edgeiq_identity_repository_final_audit_v1.json').read_text(encoding='utf-8'))
    if audit.get('status')!='EDGEIQ_IDENTITY_REPOSITORY_PROFILER_V1_AUDIT_PASS':
        print('FINAL_AUDIT_NOT_PASS'); return 2
    ARCH.mkdir(parents=True,exist_ok=True); rows=[]
    for pat in PATTERNS:
        for p in ROOT.glob(pat):
            if p.resolve() in {x.resolve() for x in CANONICAL}: continue
            dst=ARCH/p.name; shutil.move(str(p),str(dst)); rows.append({'source':str(p),'archive':str(dst),'classification':classify(p),'action':'ARCHIVED'})
    for name in STALE_OUTPUTS:
        p=OUT/name
        if p.exists():
            if p.stat().st_size>500_000_000:
                size=p.stat().st_size; p.unlink(); rows.append({'source':str(p),'archive':'','classification':classify(p),'action':f'REMOVED_STALE_HUGE size={size}'})
            else:
                dst=ARCH/p.name; shutil.move(str(p),str(dst)); rows.append({'source':str(p),'archive':str(dst),'classification':classify(p),'action':'ARCHIVED'})
    manifest=OUT/'edgeiq_identity_profiler_legacy_cleanup_manifest_v1.csv'
    with manifest.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['source','archive','classification','action']); w.writeheader(); w.writerows(rows)
    report=OUT/'edgeiq_identity_profiler_legacy_cleanup_report_v1.txt'
    report.write_text('EDGEIQ_IDENTITY_PROFILER_LEGACY_CLEANUP_COMPLETE\nitems='+str(len(rows))+'\narchive='+str(ARCH)+'\n',encoding='utf-8')
    print(json.dumps({'status':'EDGEIQ_IDENTITY_PROFILER_LEGACY_CLEANUP_COMPLETE','items':len(rows),'manifest':str(manifest)},indent=2))
    return 0
if __name__=='__main__': raise SystemExit(main())
