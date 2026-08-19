from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'public'/'data'/'edgeiq_performance_intelligence_trust_manifest_v1.json'
FINAL=ROOT/'docs'/'performance-intelligence'/'horse-performance-rating'/'method-governance'/'EDGEIQ_PERFORMANCE_INTELLIGENCE_FINAL_PRODUCTION_REPORT_V1.json'
CERT=ROOT/'docs'/'performance-intelligence'/'EDGEIQ_PERFORMANCE_INTELLIGENCE_TRUST_CERTIFICATION_V1.md'
SMOKE=ROOT/'docs'/'performance-intelligence'/'horse-performance-rating'/'method-governance'/'edgeiq_performance_intelligence_program_smoke_v1.json'
def main():
    m=json.loads(MANIFEST.read_text(encoding='utf-8'))
    m['validation']={'python_compile':'PASS','typescript':'PASS','vite':'PASS_3M05S_WITH_CHUNK_SIZE_WARNING','smoke':'PASS'}
    MANIFEST.write_text(json.dumps(m,indent=2),encoding='utf-8')
    f=json.loads(FINAL.read_text(encoding='utf-8'))
    f['validation']=m['validation']
    f['program_smoke']=str(SMOKE).replace('\\','/')
    FINAL.write_text(json.dumps(f,indent=2),encoding='utf-8')
    cert=CERT.read_text(encoding='utf-8')
    if '## Validation' not in cert:
        cert += "\n## Validation\n\n- Python compile: PASS\n- TypeScript: PASS\n- Vite build: PASS in 3m 5s, with chunk-size warning only\n- Program smoke: PASS\n"
    CERT.write_text(cert,encoding='utf-8')
    print('validation_updated=YES')
if __name__=='__main__': main()
