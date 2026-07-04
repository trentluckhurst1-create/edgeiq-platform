import csv
import re
from pathlib import Path
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
live_path=DATA/'edgeiq_live_runner_board_governed_v1.csv'
join_path=DATA/'edgeiq_current_intelligence_evidence_join_v1.csv'
out_candidate=DATA/'edgeiq_current_intelligence_evidence_fix_candidate_v1.csv'
out_summary=DATA/'edgeiq_current_intelligence_evidence_fix_candidate_v1_summary.csv'
out_audit=DATA/'edgeiq_current_intelligence_evidence_fix_candidate_v1_audit.csv'
out_report=DATA/'edgeiq_current_intelligence_evidence_fix_candidate_v1_report.txt'

def read_rows(path):
    if not path.exists(): return [], []
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        reader=csv.DictReader(f); return reader.fieldnames or [], list(reader)
def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore', lineterminator='\n'); w.writeheader(); w.writerows(rows)
def norm(s): return re.sub(r'[^a-z0-9]+','',str(s or '').lower())
def race_no_norm(s):
    m=re.search(r'\d+', str(s or '')); return m.group(0) if m else str(s or '').strip()
def first(row, cols):
    for c in cols:
        if c in row and str(row.get(c,'')).strip(): return str(row.get(c,'')).strip()
    return ''
def key(row): return (norm(first(row,['race_date','current_race_date','date'])), norm(first(row,['track'])), race_no_norm(first(row,['race_no'])), norm(first(row,['horse','runner_name','horse_name','horse_key'])))
def clean_summary(text, max_len=260):
    text=str(text or '').strip()
    text=re.sub(r'\s+', ' ', text)
    if len(text)>max_len: text=text[:max_len-3].rstrip()+'...'
    return text

live_cols, live_rows=read_rows(live_path)
join_cols, join_rows=read_rows(join_path)
join_index={key(r):r for r in join_rows}
new_cols=['edgeiq_connection_evidence_available','edgeiq_connection_angle_summary','edgeiq_market_evidence_available','edgeiq_market_signal_summary','edgeiq_hidden_gem_evidence_available','edgeiq_hidden_gem_summary','edgeiq_evidence_fix_source','edgeiq_evidence_fix_status']
fields=list(live_cols)
for c in new_cols:
    if c not in fields: fields.append(c)
rows_out=[]; audit=[]
conn=market=hidden=0; no_join=0
for r in live_rows:
    jr=join_index.get(key(r))
    if not jr:
        no_join+=1
        r.update({'edgeiq_connection_evidence_available':'NO','edgeiq_connection_angle_summary':'','edgeiq_market_evidence_available':'NO','edgeiq_market_signal_summary':'','edgeiq_hidden_gem_evidence_available':'NO','edgeiq_hidden_gem_summary':'','edgeiq_evidence_fix_source':'NO_JOIN_AUDIT_MATCH','edgeiq_evidence_fix_status':'NO_SOURCE_MATCH'})
    else:
        c_yes=jr.get('connection_matched')=='YES'; m_yes=jr.get('market_matched')=='YES'; h_yes=jr.get('hidden_gem_matched')=='YES'
        r['edgeiq_connection_evidence_available']='YES' if c_yes else 'NO'
        r['edgeiq_connection_angle_summary']=clean_summary(jr.get('connection_summary')) if c_yes else ''
        r['edgeiq_market_evidence_available']='YES' if m_yes else 'NO'
        r['edgeiq_market_signal_summary']=clean_summary(jr.get('market_summary')) if m_yes else ''
        r['edgeiq_hidden_gem_evidence_available']='YES' if h_yes else 'NO'
        r['edgeiq_hidden_gem_summary']=clean_summary(jr.get('hidden_gem_summary')) if h_yes else ''
        src=[]
        if c_yes: src.append('CONNECTION:'+jr.get('connection_source',''))
        if m_yes: src.append('MARKET:'+jr.get('market_source',''))
        if h_yes: src.append('HIDDEN_GEM:'+jr.get('hidden_gem_source',''))
        r['edgeiq_evidence_fix_source']='|'.join(src) if src else 'NO_SOURCE_MATCH'
        r['edgeiq_evidence_fix_status']='EVIDENCE_AVAILABLE' if src else 'NO_SOURCE_MATCH'
        conn+=1 if c_yes else 0; market+=1 if m_yes else 0; hidden+=1 if h_yes else 0
    audit.append({'race_date':first(r,['race_date','current_race_date']),'track':r.get('track',''),'race_no':r.get('race_no',''),'horse':first(r,['horse','runner_name','horse_name']),'connection_available':r['edgeiq_connection_evidence_available'],'market_available':r['edgeiq_market_evidence_available'],'hidden_gem_available':r['edgeiq_hidden_gem_evidence_available'],'status':r['edgeiq_evidence_fix_status'],'source':r['edgeiq_evidence_fix_source']})
    rows_out.append(r)
status='EVIDENCE_FIX_CANDIDATE_BUILT' if (conn or market or hidden) else 'EVIDENCE_FIX_CANDIDATE_RESEARCH_ONLY_NO_USABLE_SOURCE'
summary=[{'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'rows':len(rows_out),'connection_evidence_rows':conn,'market_evidence_rows':market,'hidden_gem_evidence_rows':hidden,'no_join_audit_match_rows':no_join,'production_changed':'NO','live_board_overwritten':'NO','recommended_next_step':'WIRE_OR_MERGE_FIELDS_ONLY_AFTER_UI_WIRING_AUDIT'}]
write_csv(out_candidate, rows_out, fields)
write_csv(out_audit, audit, list(audit[0].keys()) if audit else ['race_date'])
write_csv(out_summary, summary, list(summary[0].keys()))
report=['EDGEiQ Current Intelligence Evidence Fix Candidate V1','='*58,f'Status: {status}',f'Generated: {summary[0]["generated_at"]}',f'Rows: {len(rows_out)}',f'Connection evidence rows: {conn}',f'Market evidence rows: {market}',f'Hidden gem evidence rows: {hidden}',f'No join audit match rows: {no_join}','Production changed: NO','Live board overwritten: NO','','Rules applied:','- No fake evidence created.','- Exact normalized current-runner evidence only.','- Missing hidden gem evidence remains NO_SOURCE_MATCH.']
out_report.write_text('\n'.join(report)+'\n',encoding='utf-8')
print(status)
print('rows',len(rows_out),'conn',conn,'market',market,'hidden',hidden)
