import csv, subprocess
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'
out=DATA/'edgeiq_counts_scores_build_v1.csv'; sumout=DATA/'edgeiq_counts_scores_build_v1_summary.csv'; report=DATA/'edgeiq_counts_scores_build_v1_report.txt'
start=datetime.now().isoformat(timespec='seconds')
proc=subprocess.run(['npm','run','build'],cwd=str(ROOT),capture_output=True,text=True,shell=True)
end=datetime.now().isoformat(timespec='seconds')
status='BUILD_SUCCESS' if proc.returncode==0 else 'BUILD_FAILED'
row={'status':status,'started_at':start,'ended_at':end,'return_code':proc.returncode,'stdout_tail':(proc.stdout or '')[-6000:],'stderr_tail':(proc.stderr or '')[-6000:]}
for p in [out,sumout]:
    with p.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=list(row.keys())); w.writeheader(); w.writerow(row)
report.write_text('\n'.join(['EDGEiQ Counts/Scores Build V1','='*34,f'Status: {status}',f'Return code: {proc.returncode}','','STDOUT TAIL:',(proc.stdout or '')[-9000:],'','STDERR TAIL:',(proc.stderr or '')[-9000:]])+'\n', encoding='utf-8')
print(status); print('return_code',proc.returncode); print(((proc.stderr or '')+(proc.stdout or ''))[-2500:])
