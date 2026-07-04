import csv, shutil
from pathlib import Path
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'; CP=DATA/'checkpoints'
MERGE_SUM=DATA/'edgeiq_command_v3_merge_v1_summary.csv'
SRC_GOV=DATA/'edgeiq_live_runner_board_governed_v1_COMMAND_V3_MERGED.csv'
SRC_V3=DATA/'edgeiq_command_enrichment_feed_v3.csv'
TGT_GOV=DATA/'edgeiq_live_runner_board_governed_v1.csv'
TGT_V2=DATA/'edgeiq_command_enrichment_feed_v2.csv'
OUT=DATA/'edgeiq_command_v3_apply_v1.csv'; SUMMARY=DATA/'edgeiq_command_v3_apply_v1_summary.csv'; REPORT=DATA/'edgeiq_command_v3_apply_v1_report.txt'

def read_csv(p):
    if not p.exists(): return [],[]
    with p.open('r',newline='',encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return list(r), list(r.fieldnames or [])
def write_csv(p,rows,fields):
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def clean(v): return ' '.join(str(v or '').strip().upper().replace('\u00a0',' ').split())
def clean_horse(v): return ''.join(ch for ch in clean(v) if ch.isalnum())
def race_no(v):
    s=clean(v).replace('RACE ','').replace('R','')
    return s.lstrip('0') or s
def key(r): return (clean(r.get('race_date') or r.get('current_race_date')),clean(r.get('track')),race_no(r.get('race_no')),clean_horse(r.get('horse') or r.get('horse_key')))
def rkey(r): return key(r)[:3]
def validate():
    gov,gf=read_csv(TGT_GOV); v2,vf=read_csv(TGT_V2)
    caul=('2026-06-27','CAULFIELD','7')
    checks=[]
    checks.append(('governed_rows_383',len(gov)==383,len(gov)))
    checks.append(('governed_races_25',len(set(rkey(r) for r in gov))==25,len(set(rkey(r) for r in gov))))
    checks.append(('feed_rows_383',len(v2)==383,len(v2)))
    checks.append(('feed_races_25',len(set(rkey(r) for r in v2))==25,len(set(rkey(r) for r in v2))))
    checks.append(('caulfield_r7_governed_19',sum(1 for r in gov if rkey(r)==caul)==19,sum(1 for r in gov if rkey(r)==caul)))
    checks.append(('caulfield_r7_feed_19',sum(1 for r in v2 if rkey(r)==caul)==19,sum(1 for r in v2 if rkey(r)==caul)))
    checks.append(('v3_fields_in_governed','edgeiq_connection_evidence_available_v3' in gf,'edgeiq_connection_evidence_available_v3' in gf))
    checks.append(('v3_fields_in_v2_feed','edgeiq_connection_evidence_available_v3' in vf,'edgeiq_connection_evidence_available_v3' in vf))
    checks.append(('no_duplicate_governed',len(set(key(r) for r in gov))==len(gov),len(gov)-len(set(key(r) for r in gov))))
    checks.append(('no_duplicate_feed',len(set(key(r) for r in v2))==len(v2),len(v2)-len(set(key(r) for r in v2))))
    return checks,gov,v2
status='BLOCKED_ROLLED_BACK'; err=''; audits=[]; b_gov=''; b_v2=''
try:
    ms,_=read_csv(MERGE_SUM)
    if not ms or ms[0].get('status')!='COMMAND_V3_MERGE_READY': raise RuntimeError('merge summary not ready')
    CP.mkdir(parents=True,exist_ok=True); ts=datetime.now().strftime('%Y%m%d_%H%M%S')
    b_gov=str(CP/f'edgeiq_live_runner_board_governed_v1_BEFORE_COMMAND_V3_APPLY_{ts}.csv')
    b_v2=str(CP/f'edgeiq_command_enrichment_feed_v2_BEFORE_COMMAND_V3_APPLY_{ts}.csv')
    shutil.copy2(TGT_GOV,b_gov); shutil.copy2(TGT_V2,b_v2)
    shutil.copy2(SRC_GOV,TGT_GOV); shutil.copy2(SRC_V3,TGT_V2)
    checks,gov,v2=validate()
    audits=[{'check':n,'result':'PASS' if ok else 'FAIL','detail':str(d)} for n,ok,d in checks]
    if all(ok for n,ok,d in checks): status='COMMAND_V3_APPLY_SUCCESS'
    else:
        shutil.copy2(b_gov,TGT_GOV); shutil.copy2(b_v2,TGT_V2)
except Exception as e:
    err=str(e)
    try:
        if b_gov: shutil.copy2(b_gov,TGT_GOV)
        if b_v2: shutil.copy2(b_v2,TGT_V2)
    except Exception as re: err += ' rollback_error='+str(re)
    audits.append({'check':'apply_exception','result':'FAIL','detail':err})
checks,gov,v2=validate()
summary={'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'backup_governed':b_gov,'backup_v2_feed':b_v2,'governed_rows':len(gov),'feed_rows':len(v2),'governed_races':len(set(rkey(r) for r in gov)),'feed_races':len(set(rkey(r) for r in v2)),'caulfield_r7_governed_rows':sum(1 for r in gov if rkey(r)==('2026-06-27','CAULFIELD','7')),'caulfield_r7_feed_rows':sum(1 for r in v2 if rkey(r)==('2026-06-27','CAULFIELD','7')),'error':err}
write_csv(OUT,audits,['check','result','detail']); write_csv(SUMMARY,[summary],list(summary.keys()))
REPORT.write_text('\n'.join(['EDGEiQ Command V3 Apply V1','='*30,f'Status: {status}',f'Governed/feed rows: {summary["governed_rows"]}/{summary["feed_rows"]}',f'Governed/feed races: {summary["governed_races"]}/{summary["feed_races"]}',f'CAULFIELD R7 governed/feed: {summary["caulfield_r7_governed_rows"]}/{summary["caulfield_r7_feed_rows"]}',f'Backup governed: {b_gov}',f'Backup v2 feed: {b_v2}',f'Error: {err or "None"}'])+'\n',encoding='utf-8')
print(status)
