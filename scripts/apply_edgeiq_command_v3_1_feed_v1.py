import csv, shutil
from pathlib import Path
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'; CP=DATA/'checkpoints'
SRC=DATA/'edgeiq_command_enrichment_feed_v3_1.csv'
TGT_V3=DATA/'edgeiq_command_enrichment_feed_v3.csv'
TGT_V2=DATA/'edgeiq_command_enrichment_feed_v2.csv'
AUDIT_SUM=DATA/'edgeiq_command_all_remaining_issues_race_summary_v1.csv'
OUT=DATA/'edgeiq_command_v3_1_apply_v1.csv'; SUMMARY=DATA/'edgeiq_command_v3_1_apply_v1_summary.csv'; REPORT=DATA/'edgeiq_command_v3_1_apply_v1_report.txt'

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

status='BLOCKED_ROLLED_BACK'; err=''; audits=[]; b3=''; b2=''
try:
    if not SRC.exists(): raise RuntimeError('V3.1 source missing')
    race_summary,_=read_csv(AUDIT_SUM)
    if any(r.get('status')=='FIX_REQUIRED' for r in race_summary): raise RuntimeError('Remaining issue audit still has FIX_REQUIRED races')
    CP.mkdir(parents=True,exist_ok=True); ts=datetime.now().strftime('%Y%m%d_%H%M%S')
    b3=str(CP/f'edgeiq_command_enrichment_feed_v3_BEFORE_V3_1_APPLY_{ts}.csv')
    b2=str(CP/f'edgeiq_command_enrichment_feed_v2_BEFORE_V3_1_APPLY_{ts}.csv')
    shutil.copy2(TGT_V3,b3); shutil.copy2(TGT_V2,b2)
    shutil.copy2(SRC,TGT_V3); shutil.copy2(SRC,TGT_V2)
    rows,fields=read_csv(TGT_V3); rows2,fields2=read_csv(TGT_V2)
    checks=[('v3_rows_383',len(rows)==383,len(rows)),('v2_rows_383',len(rows2)==383,len(rows2)),('v3_races_25',len(set(rkey(r) for r in rows))==25,len(set(rkey(r) for r in rows))),('v2_races_25',len(set(rkey(r) for r in rows2))==25,len(set(rkey(r) for r in rows2))),('v3_1_fields_present','edgeiq_price_truth_status_v3_1' in fields,'edgeiq_price_truth_status_v3_1' in fields),('v2_has_v3_1_fields','edgeiq_price_truth_status_v3_1' in fields2,'edgeiq_price_truth_status_v3_1' in fields2)]
    audits=[{'check':n,'result':'PASS' if ok else 'FAIL','detail':str(d)} for n,ok,d in checks]
    if all(ok for n,ok,d in checks): status='COMMAND_V3_1_APPLY_SUCCESS'
    else:
        shutil.copy2(b3,TGT_V3); shutil.copy2(b2,TGT_V2)
except Exception as e:
    err=str(e)
    try:
        if b3: shutil.copy2(b3,TGT_V3)
        if b2: shutil.copy2(b2,TGT_V2)
    except Exception as re: err += ' rollback_error='+str(re)
    audits.append({'check':'apply_exception','result':'FAIL','detail':err})
rows,_=read_csv(TGT_V3); rows2,_=read_csv(TGT_V2)
summary={'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'backup_v3_feed':b3,'backup_v2_feed':b2,'v3_rows':len(rows),'v2_rows':len(rows2),'v3_races':len(set(rkey(r) for r in rows)),'v2_races':len(set(rkey(r) for r in rows2)),'pricing_math_changed':'NO','v7_2g2_math_changed':'NO','governed_board_changed':'NO','error':err}
write_csv(OUT,audits,['check','result','detail']); write_csv(SUMMARY,[summary],list(summary.keys()))
REPORT.write_text('\n'.join(['EDGEiQ Command V3.1 Apply V1','='*35,f'Status: {status}',f'V3/V2 rows: {summary["v3_rows"]}/{summary["v2_rows"]}',f'V3/V2 races: {summary["v3_races"]}/{summary["v2_races"]}',f'Backup V3: {b3}',f'Backup V2: {b2}','Governed board changed: NO','Pricing maths changed: NO','V7.2G2 maths changed: NO',f'Error: {err or "None"}'])+'\n',encoding='utf-8')
print(status)
