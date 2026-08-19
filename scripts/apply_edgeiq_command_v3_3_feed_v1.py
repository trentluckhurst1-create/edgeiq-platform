import csv, shutil
from pathlib import Path
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'; CP=DATA/'checkpoints'
SRC=DATA/'edgeiq_command_enrichment_feed_v3_3.csv'; SUM=DATA/'edgeiq_command_enrichment_feed_v3_3_summary.csv'
TGT3=DATA/'edgeiq_command_enrichment_feed_v3.csv'; TGT2=DATA/'edgeiq_command_enrichment_feed_v2.csv'
OUT=DATA/'edgeiq_command_v3_3_apply_v1.csv'; SUMMARY=DATA/'edgeiq_command_v3_3_apply_v1_summary.csv'; REPORT=DATA/'edgeiq_command_v3_3_apply_v1_report.txt'

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
    s,_=read_csv(SUM)
    if not s or s[0].get('status')!='COMMAND_ENRICHMENT_FEED_V3_3_BUILT': raise RuntimeError('V3.3 build summary not ready')
    CP.mkdir(parents=True,exist_ok=True); ts=datetime.now().strftime('%Y%m%d_%H%M%S')
    b3=str(CP/f'edgeiq_command_enrichment_feed_v3_BEFORE_V3_3_APPLY_{ts}.csv')
    b2=str(CP/f'edgeiq_command_enrichment_feed_v2_BEFORE_V3_3_APPLY_{ts}.csv')
    shutil.copy2(TGT3,b3); shutil.copy2(TGT2,b2); shutil.copy2(SRC,TGT3); shutil.copy2(SRC,TGT2)
    r3,f3=read_csv(TGT3); r2,f2=read_csv(TGT2)
    checks=[('v3_rows_383',len(r3)==383,len(r3)),('v2_rows_383',len(r2)==383,len(r2)),('v3_races_25',len(set(rkey(r) for r in r3))==25,len(set(rkey(r) for r in r3))),('v2_races_25',len(set(rkey(r) for r in r2))==25,len(set(rkey(r) for r in r2))),('v3_3_fields_present','edgeiq_campaign_available_v3_3' in f3,'edgeiq_campaign_available_v3_3' in f3),('v2_has_v3_3_fields','edgeiq_campaign_available_v3_3' in f2,'edgeiq_campaign_available_v3_3' in f2),('v3_no_dupes',len(set(key(r) for r in r3))==len(r3),len(r3)-len(set(key(r) for r in r3)))]
    audits=[{'check':n,'result':'PASS' if ok else 'FAIL','detail':str(d)} for n,ok,d in checks]
    if all(ok for n,ok,d in checks): status='COMMAND_V3_3_APPLY_SUCCESS'
    else:
        shutil.copy2(b3,TGT3); shutil.copy2(b2,TGT2)
except Exception as e:
    err=str(e)
    try:
        if b3: shutil.copy2(b3,TGT3)
        if b2: shutil.copy2(b2,TGT2)
    except Exception as re: err+=' rollback_error='+str(re)
    audits.append({'check':'apply_exception','result':'FAIL','detail':err})
r3,_=read_csv(TGT3); r2,_=read_csv(TGT2)
summary={'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'backup_v3_feed':b3,'backup_v2_feed':b2,'v3_rows':len(r3),'v2_rows':len(r2),'v3_races':len(set(rkey(r) for r in r3)),'v2_races':len(set(rkey(r) for r in r2)),'campaign_available_rows':sum(1 for r in r3 if r.get('edgeiq_campaign_available_v3_3')=='YES'),'campaign_true_zero_rows':sum(1 for r in r3 if r.get('edgeiq_campaign_truth_status_v3_3')=='TRUE_ZERO_NO_CAMPAIGN_HISTORY'),'campaign_source_missing_rows':sum(1 for r in r3 if r.get('edgeiq_campaign_truth_status_v3_3') in {'CAMPAIGN_SOURCE_MISSING','CAMPAIGN_SOURCE_MISSING_OR_JOIN_FAILED'}),'governed_board_changed':'NO','pricing_math_changed':'NO','v6_1_changed':'NO','v7_2g2_changed':'NO','error':err}
write_csv(OUT,audits,['check','result','detail']); write_csv(SUMMARY,[summary],list(summary.keys()))
REPORT.write_text('\n'.join(['EDGEiQ Command V3.3 Apply V1','='*35,f'Status: {status}',f'V3/V2 rows: {summary["v3_rows"]}/{summary["v2_rows"]}',f'Campaign available/true-zero/source-missing: {summary["campaign_available_rows"]}/{summary["campaign_true_zero_rows"]}/{summary["campaign_source_missing_rows"]}',f'Backup V3: {b3}',f'Backup V2: {b2}','Governed board changed: NO','Pricing maths changed: NO','V6.1 changed: NO','V7.2G2 changed: NO',f'Error: {err or "None"}'])+'\n',encoding='utf-8')
print(status)
