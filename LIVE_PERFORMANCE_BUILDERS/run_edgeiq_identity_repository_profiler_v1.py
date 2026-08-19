from __future__ import annotations
import subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LOG=ROOT/'docs'/'performance-intelligence'/'identity-profiler-v1-run-logs'
LOG.mkdir(parents=True,exist_ok=True)
CANONICAL=ROOT/'build_edgeiq_identity_repository_profiler_v1.py'
def main():
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    log=LOG/f'edgeiq_identity_repository_profiler_v1_run_{run_id}.log'
    cp=subprocess.run([sys.executable,str(CANONICAL),'--no-resume'],cwd=ROOT,text=True,capture_output=True)
    log.write_text('STDOUT\n======\n'+(cp.stdout or '')+'\nSTDERR\n======\n'+(cp.stderr or '')+f'\nEXIT_CODE={cp.returncode}\n',encoding='utf-8')
    if cp.stdout: print(cp.stdout[-4000:])
    if cp.stderr: print(cp.stderr[-2000:],file=sys.stderr)
    print(f'RUN_LOG: {log.relative_to(ROOT).as_posix()}')
    return cp.returncode
if __name__=='__main__': raise SystemExit(main())
