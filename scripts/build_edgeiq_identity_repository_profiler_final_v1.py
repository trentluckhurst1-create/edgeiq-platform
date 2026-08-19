from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CANONICAL=ROOT/'build_edgeiq_identity_repository_profiler_v1.py'
OUT=ROOT/'docs'/'performance-intelligence'/'identity-profiler-v1'
def main():
    report=OUT/'edgeiq_identity_repository_profiler_final_builder_v1_report.json'
    ok=CANONICAL.exists() and CANONICAL.stat().st_size>0
    payload={'status':'CANONICAL_PROFILER_PRESENT' if ok else 'CANONICAL_PROFILER_MISSING','canonical':str(CANONICAL),'note':'Final canonical profiler is generated/promoted and maintained at repository root. This builder records the governed final state.'}
    report.write_text(json.dumps(payload,indent=2),encoding='utf-8')
    print(json.dumps(payload,indent=2))
    return 0 if ok else 2
if __name__=='__main__': raise SystemExit(main())
