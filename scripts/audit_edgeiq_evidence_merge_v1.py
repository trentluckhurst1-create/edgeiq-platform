import csv
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'
input_path=DATA/'edgeiq_live_runner_board_governed_v1_EVIDENCE_MERGED.csv'
out=DATA/'edgeiq_evidence_merge_audit_v1.csv'; sumout=DATA/'edgeiq_evidence_merge_audit_v1_summary.csv'; report=DATA/'edgeiq_evidence_merge_audit_v1_report.txt'
fields_req=['edgeiq_connection_evidence_available','edgeiq_connection_angle_summary','edgeiq_market_evidence_available','edgeiq_market_signal_summary','edgeiq_hidden_gem_evidence_available','edgeiq_hidden_gem_summary','edgeiq_evidence_fix_source','edgeiq_evidence_fix_status']
pricing_fields=['fair_price','ui_fair_price','live_price','win_pct','edgeiq_v7_2g2_active_display_fair_price_shadow','edgeiq_v7_2g2_on_preview_display_fair_price']
def read(path):
    if not path.exists(): return [], []
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return r.fieldnames or [], list(r)
def write(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def yes(v): return str(v).strip().upper() in {'YES','TRUE','1','Y'}
def nonblank(v): return str(v if v is not None else '').strip()!=''
def uniq(rows,col): return sorted({str(r.get(col,'')).strip() for r in rows if str(r.get(col,'')).strip()})
cols, rows=read(input_path); checks=[]; blockers=[]
def add(name, obs, exp, passed):
    checks.append({'check':name,'observed':obs,'expected':exp,'passed':'YES' if passed else 'NO','notes':'' if passed else f'Expected {exp}; observed {obs}'})
    if not passed: blockers.append(name)
conn=sum(1 for r in rows if yes(r.get('edgeiq_connection_evidence_available')))
market=sum(1 for r in rows if yes(r.get('edgeiq_market_evidence_available')))
hidden=sum(1 for r in rows if yes(r.get('edgeiq_hidden_gem_evidence_available')))
conn_summary=sum(1 for r in rows if yes(r.get('edgeiq_connection_evidence_available')) and nonblank(r.get('edgeiq_connection_angle_summary')))
market_summary=sum(1 for r in rows if yes(r.get('edgeiq_market_evidence_available')) and nonblank(r.get('edgeiq_market_signal_summary')))
hidden_summary=sum(1 for r in rows if yes(r.get('edgeiq_hidden_gem_evidence_available')) and nonblank(r.get('edgeiq_hidden_gem_summary')))
null_issue=sum(1 for r in rows if any(str(r.get(c,'')).strip()=='' for c in ['edgeiq_connection_evidence_available','edgeiq_market_evidence_available','edgeiq_hidden_gem_evidence_available','edgeiq_evidence_fix_status']))
add('rows',str(len(rows)),'378',len(rows)==378)
add('evidence_fields_exist','|'.join([c for c in fields_req if c in cols]),'all_required','YES' if set(fields_req).issubset(set(cols)) else 'NO' == 'YES')
add('connection_available_count',str(conn),'>0',conn>0)
add('market_available_count',str(market),'>0',market>0)
add('hidden_gem_available_count',str(hidden),'>0',hidden>0)
add('connection_summaries_populated',str(conn_summary),str(conn),conn_summary==conn)
add('market_summaries_populated',str(market_summary),str(market),market_summary==market)
add('hidden_gem_summaries_populated',str(hidden_summary),str(hidden),hidden_summary==hidden)
add('no_null_issue_outside_no_source_match',str(null_issue),'0',null_issue==0)
add('pricing_fields_present','|'.join([c for c in pricing_fields if c in cols]),'all_required',set(pricing_fields).issubset(set(cols)))
add('feature_flag_still_on','|'.join(uniq(rows,'edgeiq_v7_2g2_feature_flag')),'ON',uniq(rows,'edgeiq_v7_2g2_feature_flag')==['ON'])
add('live_wired_still_yes_controlled_on','|'.join(uniq(rows,'edgeiq_v7_2g2_live_wired_flag')),'YES_CONTROLLED_ON',uniq(rows,'edgeiq_v7_2g2_live_wired_flag')==['YES_CONTROLLED_ON'])
status='EVIDENCE_MERGE_AUDIT_PASS' if not blockers else 'BLOCKED'
summary=[{'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'rows':len(rows),'connection_available_count':conn,'market_available_count':market,'hidden_gem_available_count':hidden,'connection_summaries_populated':conn_summary,'market_summaries_populated':market_summary,'hidden_gem_summaries_populated':hidden_summary,'null_issue_count':null_issue,'feature_flag_values':'|'.join(uniq(rows,'edgeiq_v7_2g2_feature_flag')),'live_wired_values':'|'.join(uniq(rows,'edgeiq_v7_2g2_live_wired_flag')),'pricing_fields_present':'|'.join([c for c in pricing_fields if c in cols]),'blocked_reasons':'; '.join(blockers)}]
write(out,checks,['check','observed','expected','passed','notes']); write(sumout,summary,list(summary[0].keys()))
report.write_text('\n'.join(['EDGEiQ Evidence Merge Audit V1','='*40,f'Status: {status}',f'Rows: {len(rows)}',f'Connection available: {conn}',f'Market available: {market}',f'Hidden gem available: {hidden}',f'Feature flag: {summary[0]["feature_flag_values"]}',f'Live wired: {summary[0]["live_wired_values"]}',f'Blocked reasons: {summary[0]["blocked_reasons"] or "None"}'])+'\n', encoding='utf-8')
print(status); print('conn',conn,'market',market,'hidden',hidden,'blocked',len(blockers))
