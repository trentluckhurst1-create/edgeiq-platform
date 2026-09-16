from __future__ import annotations
import hashlib, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = [
 'scripts/build_edgeiq_results_elapsed_time_observations_v1.py',
 'scripts/build_edgeiq_standard_time_performance_facts_from_results_v1.py',
 'scripts/build_edgeiq_results_standard_time_eligibility_v1.py',
 'scripts/build_edgeiq_results_standard_times_v1.py',
 'scripts/build_edgeiq_canonical_surface_registry_v1.py',
 'scripts/audit_edgeiq_canonical_surface_registry_v1.py',
 'scripts/test_edgeiq_length_conversion_method_v1.py',
 'scripts/build_edgeiq_results_lengths_v_standard_v2.py',
 'scripts/audit_edgeiq_results_lengths_v_standard_v2.py',
 'scripts/build_edgeiq_runner_sectional_performance_v2.py',
 'scripts/build_edgeiq_results_early_late_speed_v2.py',
]

def run(script: str) -> None:
 print(f'::group::EDGEiQ bootstrap: {script}', flush=True)
 p=subprocess.run([sys.executable,'-u',str(ROOT/script)],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240)
 print(p.stdout or '',end='' if (p.stdout or '').endswith('\n') else '\n',flush=True)
 print(f'return_code={p.returncode}',flush=True); print('::endgroup::',flush=True)
 if p.returncode: raise SystemExit(p.returncode)

def main() -> int:
 for s in STAGES: run(s)
 candidate=ROOT/'public/data/edgeiq_results_lengths_v_standard_v2_CANDIDATE.csv'
 if not candidate.exists(): raise SystemExit('LVS candidate missing after bootstrap')
 first=hashlib.sha256(candidate.read_bytes()).hexdigest()
 run('scripts/build_edgeiq_results_lengths_v_standard_v2.py')
 second=hashlib.sha256(candidate.read_bytes()).hexdigest()
 if first != second: raise SystemExit('LVS deterministic hash mismatch')
 print(f'EDGEIQ_PERFORMANCE_BOOTSTRAP_V3_PASS hash={second}')
 return 0
if __name__=='__main__': raise SystemExit(main())
