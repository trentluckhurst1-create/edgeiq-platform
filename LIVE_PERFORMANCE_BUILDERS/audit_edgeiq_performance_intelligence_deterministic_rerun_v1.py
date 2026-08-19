from __future__ import annotations
import csv, hashlib, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
DOC=ROOT/'docs'/'performance-intelligence'
MG=DOC/'horse-performance-rating'/'method-governance'
OUT=MG/'edgeiq_performance_intelligence_deterministic_rerun_v1.json'
FILES=[
 DATA/'edgeiq_performance_normalisation_fact_v1.csv',
 DATA/'edgeiq_performance_rating_base_fact_v1.csv',
 DATA/'edgeiq_horse_performance_observation_fact_v1.csv',
 DATA/'edgeiq_horse_performance_aggregate_fact_v1.csv',
 DATA/'edgeiq_horse_performance_rating_fact_v1.csv',
 DATA/'edgeiq_race_entry_projected_performance_fact_v1.csv',
 DATA/'edgeiq_race_entry_epi_fact_v1.csv',
]
BUILDERS=[
 'build_edgeiq_performance_normalisation_fact_v1.py',
 'build_edgeiq_performance_rating_base_fact_v1.py',
 'build_edgeiq_horse_performance_observation_fact_v1.py',
 'build_edgeiq_horse_performance_aggregate_fact_v1.py',
 'build_edgeiq_horse_performance_rating_fact_v1.py',
 'build_edgeiq_race_entry_projected_performance_fact_v1.py',
 'build_edgeiq_race_entry_epi_fact_v1.py',
]
def canonical_hash(path: Path):
    if not path.exists(): return ''
    if path.suffix.lower()=='.csv':
        with path.open(newline='', encoding='utf-8-sig') as f:
            r=csv.DictReader(f); fields=[x for x in (r.fieldnames or []) if x!='built_at_utc']; rows=[]
            for row in r:
                rows.append('\x1f'.join(str(row.get(k,'')).strip() for k in fields))
        return hashlib.sha256('\n'.join(rows).encode('utf-8')).hexdigest()
    return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    before={p.name:canonical_hash(p) for p in FILES}
    runs=[]
    for b in BUILDERS:
        proc=subprocess.run([sys.executable,'-u',str(ROOT/'scripts'/b)],cwd=ROOT,text=True,capture_output=True)
        runs.append({'builder':b,'returncode':proc.returncode,'last_stdout_line':(proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ''),'stderr':proc.stderr.strip()[-500:]})
    after={p.name:canonical_hash(p) for p in FILES}
    result={'status':'PASS' if before==after and all(r['returncode']==0 for r in runs) else 'FAIL','before':before,'after':after,'runs':runs,'excluded_fields':['built_at_utc']}
    OUT.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'status':result['status'],'files':len(FILES)},indent=2))
if __name__=='__main__': main()
