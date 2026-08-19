import csv, subprocess
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'
out=DATA/'edgeiq_evidence_ui_build_v1.csv'; sumout=DATA/'edgeiq_evidence_ui_build_v1_summary.csv'; report=DATA/'edgeiq_evidence_ui_build_v1_report.txt'
started=datetime.now().isoformat(timespec='seconds')
proc=subprocess.run(['npm','run','build'], cwd=str(ROOT), capture_output=True, text=True, shell=True)
ended=datetime.now().isoformat(timespec='seconds')
status='BUILD_SUCCESS' if proc.returncode==0 else 'BUILD_FAILED'
stdout=proc.stdout or ''; stderr=proc.stderr or ''
row={'status':status,'started_at':started,'ended_at':ended,'return_code':proc.returncode,'stdout_tail':stdout[-4000:],'stderr_tail':stderr[-4000:]}
for p in [out,sumout]:
    with p.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=list(row.keys())); w.writeheader(); w.writerow(row)
report.write_text('\n'.join(['EDGEiQ Evidence UI Build V1','='*32,f'Status: {status}',f'Started: {started}',f'Ended: {ended}',f'Return code: {proc.returncode}','','STDOUT TAIL:',stdout[-8000:],'','STDERR TAIL:',stderr[-8000:]])+'\n', encoding='utf-8')
print(status); print('return_code',proc.returncode)
print((stderr or stdout)[-2000:])
