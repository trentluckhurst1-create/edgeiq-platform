import csv, shutil
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'; CP=DATA/'checkpoints'
source=DATA/'edgeiq_live_runner_board_governed_v1_EVIDENCE_MERGED.csv'; target=DATA/'edgeiq_live_runner_board_governed_v1.csv'
out=DATA/'edgeiq_evidence_apply_v1.csv'; sumout=DATA/'edgeiq_evidence_apply_v1_summary.csv'; report=DATA/'edgeiq_evidence_apply_v1_report.txt'
fields_req=['edgeiq_connection_evidence_available','edgeiq_connection_angle_summary','edgeiq_market_evidence_available','edgeiq_market_signal_summary','edgeiq_hidden_gem_evidence_available','edgeiq_hidden_gem_summary','edgeiq_evidence_fix_source','edgeiq_evidence_fix_status']
pricing_fields=['fair_price','ui_fair_price','live_price','win_pct','edgeiq_v7_2g2_active_display_fair_price_shadow','edgeiq_v7_2g2_on_preview_display_fair_price']
def read(path):
    if not path.exists(): return [], []
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return r.fieldnames or [], list(r)
def write(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def uniq(rows,col): return sorted({str(r.get(col,'')).strip() for r in rows if str(r.get(col,'')).strip()})
status='EVIDENCE_APPLY_SUCCESS'; err=''; backup=''; rolled='NO'; checks=[]; blockers=[]
def add(name,obs,exp,passed):
    checks.append({'check':name,'observed':obs,'expected':exp,'passed':'YES' if passed else 'NO','notes':'' if passed else f'Expected {exp}; observed {obs}'})
    if not passed: blockers.append(name)
try:
    if not source.exists(): raise FileNotFoundError(source)
    if not target.exists(): raise FileNotFoundError(target)
    CP.mkdir(parents=True, exist_ok=True); ts=datetime.now().strftime('%Y%m%d_%H%M%S')
    b=CP/f'edgeiq_live_runner_board_governed_v1_BEFORE_EVIDENCE_APPLY_{ts}.csv'; shutil.copy2(target,b); backup=str(b)
    shutil.copy2(source,target)
    cols, rows=read(target)
    add('rows',str(len(rows)),'378',len(rows)==378)
    add('evidence_fields_present','|'.join([c for c in fields_req if c in cols]),'all_required',set(fields_req).issubset(set(cols)))
    add('feature_flag_on','|'.join(uniq(rows,'edgeiq_v7_2g2_feature_flag')),'ON',uniq(rows,'edgeiq_v7_2g2_feature_flag')==['ON'])
    add('live_wired_yes_controlled_on','|'.join(uniq(rows,'edgeiq_v7_2g2_live_wired_flag')),'YES_CONTROLLED_ON',uniq(rows,'edgeiq_v7_2g2_live_wired_flag')==['YES_CONTROLLED_ON'])
    add('pricing_fields_present','|'.join([c for c in pricing_fields if c in cols]),'all_required',set(pricing_fields).issubset(set(cols)))
    if blockers:
        shutil.copy2(b,target); rolled='YES'; status='BLOCKED_ROLLED_BACK'; err='; '.join(blockers)
except Exception as e:
    status='BLOCKED_ROLLED_BACK'; err=str(e)
    if backup and Path(backup).exists(): shutil.copy2(backup,target); rolled='YES'
cols, rows=read(target)
summary=[{'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'backup_file':backup,'rows':len(rows),'feature_flag_values':'|'.join(uniq(rows,'edgeiq_v7_2g2_feature_flag')),'live_wired_values':'|'.join(uniq(rows,'edgeiq_v7_2g2_live_wired_flag')),'evidence_fields_present':'|'.join([c for c in fields_req if c in cols]),'pricing_fields_present':'|'.join([c for c in pricing_fields if c in cols]),'rolled_back':rolled,'error':err}]
write(out,checks if checks else [{'check':'apply','observed':status,'expected':'EVIDENCE_APPLY_SUCCESS','passed':'YES' if status=='EVIDENCE_APPLY_SUCCESS' else 'NO','notes':err}],['check','observed','expected','passed','notes'])
write(sumout,summary,list(summary[0].keys()))
report.write_text('\n'.join(['EDGEiQ Evidence Apply V1','='*30,f'Status: {status}',f'Backup: {backup}',f'Rows: {len(rows)}',f'Feature flag: {summary[0]["feature_flag_values"]}',f'Live wired: {summary[0]["live_wired_values"]}',f'Rolled back: {rolled}',f'Error: {err or "None"}'])+'\n',encoding='utf-8')
print(status); print('rows',len(rows),'rolled',rolled)
