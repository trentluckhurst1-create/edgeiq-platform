import csv, subprocess
from pathlib import Path
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
OUT=DATA/'edgeiq_command_v3_build_v1.csv'; SUMMARY=DATA/'edgeiq_command_v3_build_v1_summary.csv'; REPORT=DATA/'edgeiq_command_v3_build_v1_report.txt'
started=datetime.now()
proc=subprocess.run(['npm','run','build'],cwd=str(ROOT),capture_output=True,text=True,shell=True)
ended=datetime.now()
status='BUILD_SUCCESS' if proc.returncode==0 else 'BUILD_FAILED'
stdout=(proc.stdout or '')[-12000:]
stderr=(proc.stderr or '')[-12000:]
row={'status':status,'generated_at':ended.isoformat(timespec='seconds'),'returncode':proc.returncode,'duration_seconds':round((ended-started).total_seconds(),2)}
with OUT.open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['stream','content']); w.writeheader(); w.writerow({'stream':'stdout_tail','content':stdout}); w.writerow({'stream':'stderr_tail','content':stderr})
with SUMMARY.open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(row.keys())); w.writeheader(); w.writerow(row)
REPORT.write_text('\n'.join(['EDGEiQ Command V3 Build V1','='*30,f'Status: {status}',f'Return code: {proc.returncode}',f'Duration seconds: {row["duration_seconds"]}','','STDOUT tail:',stdout,'','STDERR tail:',stderr])+'\n',encoding='utf-8')
print(status)
