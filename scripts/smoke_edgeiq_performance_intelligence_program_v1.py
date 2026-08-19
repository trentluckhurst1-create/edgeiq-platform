from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'public'/'data'/'edgeiq_performance_intelligence_trust_manifest_v1.json'
OUT=ROOT/'docs'/'performance-intelligence'/'horse-performance-rating'/'method-governance'/'edgeiq_performance_intelligence_program_smoke_v1.json'
def main():
    m=json.loads(MANIFEST.read_text(encoding='utf-8'))
    checks=[]
    def add(name, ok, detail): checks.append({'check':name,'status':'PASS' if ok else 'FAIL','detail':detail})
    rc=m['row_counts_by_stage']; lc=m['live_coverage']
    add('manifest_exists', MANIFEST.exists(), MANIFEST.as_posix())
    add('normalisation_rows_168', rc.get('normalisation')==168, rc.get('normalisation'))
    add('rating_base_rows_168', rc.get('rating_base')==168, rc.get('rating_base'))
    add('horse_rating_rows_24', rc.get('horse_rating')==24, rc.get('horse_rating'))
    add('active_entries_188', lc.get('active_entries')==188, lc.get('active_entries'))
    add('partial_coverage_explicit', m.get('program_status')=='EDGEIQ_PERFORMANCE_INTELLIGENCE_LIVE_PARTIAL_HISTORICAL_COVERAGE', m.get('program_status'))
    add('epi_unavailable_explicit', lc.get('epi_rows')==0, lc.get('epi_rows'))
    add('deterministic_pass', m.get('deterministic_rerun_result')=='PASS', m.get('deterministic_rerun_result'))
    result={'status':'PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL','checks':checks}
    OUT.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    if result['status']!='PASS': raise SystemExit(1)
if __name__=='__main__': main()
