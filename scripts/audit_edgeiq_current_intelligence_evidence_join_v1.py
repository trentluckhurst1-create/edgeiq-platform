import csv
import re
from pathlib import Path
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
source_inventory=DATA/'edgeiq_intelligence_evidence_sources_v1.csv'
live_path=DATA/'edgeiq_live_runner_board_governed_v1.csv'
out_detail=DATA/'edgeiq_current_intelligence_evidence_join_v1.csv'
out_summary=DATA/'edgeiq_current_intelligence_evidence_join_v1_summary.csv'
out_report=DATA/'edgeiq_current_intelligence_evidence_join_v1_report.txt'

def read_rows(path, limit=None):
    if not path.exists(): return [], []
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        reader=csv.DictReader(f); rows=[]
        for i,r in enumerate(reader):
            if limit is None or i<limit: rows.append(r)
            else: break
        return reader.fieldnames or [], rows

def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)

def norm(s): return re.sub(r'[^a-z0-9]+','',str(s or '').lower())
def race_no_norm(s):
    m=re.search(r'\d+', str(s or ''))
    return m.group(0) if m else str(s or '').strip()
def first_val(row, cols):
    for c in cols:
        if c in row and str(row.get(c,'')).strip(): return str(row.get(c,'')).strip()
    return ''
def key_for(row):
    return (norm(first_val(row,['race_date','current_race_date','date'])), norm(first_val(row,['track','race_track'])), race_no_norm(first_val(row,['race_no','race_number','race'])), norm(first_val(row,['horse','runner_name','horse_name','horse_key','selection_name'])))
def live_key_for(row): return key_for(row)
def material_value(row, cols):
    vals=[]
    for c in cols:
        v=str(row.get(c,'')).strip()
        if v and v.upper() not in {'NO','NONE','N/A','NA','NO_EVIDENCE','NO_CONNECTION','FALSE','0','NULL'}:
            vals.append(f'{c}={v}')
    return '; '.join(vals[:4])
def cols_matching(cols, pats):
    return [c for c in cols if any(p in c.lower() for p in pats)]

live_cols, live_rows=read_rows(live_path)
live_keys={live_key_for(r):r for r in live_rows}
inv_cols, inv_rows=read_rows(source_inventory)
source_files=[]
for inv in inv_rows:
    if inv.get('exists')!='YES': continue
    if inv.get('recommended_action') not in {'USABLE_JOIN_CANDIDATE','HAS_DATA_JOIN_MISMATCH_OR_HISTORICAL_ONLY'}: continue
    flags=inv.get('source_type_flags','')
    if not any(x in flags for x in ['CONNECTION_SOURCE','MARKET_SOURCE','HIDDEN_GEM_SOURCE']): continue
    p=ROOT/inv.get('file_name','')
    if p.exists(): source_files.append((p, flags))
# Keep audit tractable and useful: prefer files with exact current match potential, plus named current feeds.
priority=[]
for p,flags in source_files:
    name=p.name.lower()
    score=0
    if 'current' in name or 'live' in name or 'explainability' in name or 'connection_intelligence' in name or 'factor_scorecard' in name: score+=10
    if 'v2_1' in name or 'terminal_feed' in name or 'runner_explainability' in name: score+=5
    priority.append((score,p,flags))
source_files=[(p,flags) for score,p,flags in sorted(priority, key=lambda x:(-x[0], x[1].name.lower()))[:60]]

source_indexes=[]
source_audits=[]
for p,flags in source_files:
    cols, rows=read_rows(p, limit=None)
    if not rows: continue
    conn_cols=cols_matching(cols,['connection','trainer','jockey','combo','partnership'])
    market_cols=cols_matching(cols,['market','price','sp','odds','fair','prob','value'])
    hidden_cols=cols_matching(cols,['hidden','gem','overlay','opportunity','value'])
    idx={}
    loose_horse={}
    for r in rows:
        k=key_for(r)
        idx.setdefault(k,[]).append(r)
        h=k[3]
        if h: loose_horse.setdefault(h,[]).append(r)
    exact=sum(1 for k in live_keys if k in idx)
    source_indexes.append({'path':p,'flags':flags,'cols':cols,'rows':rows,'idx':idx,'loose':loose_horse,'conn_cols':conn_cols,'market_cols':market_cols,'hidden_cols':hidden_cols,'exact':exact})
    source_audits.append((p, exact, len(rows), flags))

out=[]
conn_match=market_match=hidden_match=0
selected_race_rows=len(live_rows)
for lr in live_rows:
    lk=live_key_for(lr)
    rec={'race_date':lk[0],'track':lr.get('track',''),'race_no':lr.get('race_no',''),'horse':first_val(lr,['horse','runner_name','horse_name']),'connection_matched':'NO','connection_source':'','connection_summary':'','market_matched':'NO','market_source':'','market_summary':'','hidden_gem_matched':'NO','hidden_gem_source':'','hidden_gem_summary':'','join_failure_reason':''}
    reasons=[]
    for s in source_indexes:
        matches=s['idx'].get(lk,[])
        if not matches:
            continue
        row=matches[0]
        if rec['connection_matched']=='NO' and s['conn_cols']:
            mv=material_value(row, s['conn_cols'])
            if mv:
                rec['connection_matched']='YES'; rec['connection_source']=str(s['path'].relative_to(ROOT)); rec['connection_summary']=mv
        if rec['market_matched']=='NO' and s['market_cols']:
            mv=material_value(row, s['market_cols'])
            if mv:
                rec['market_matched']='YES'; rec['market_source']=str(s['path'].relative_to(ROOT)); rec['market_summary']=mv
        if rec['hidden_gem_matched']=='NO' and s['hidden_cols']:
            mv=material_value(row, s['hidden_cols'])
            if mv:
                rec['hidden_gem_matched']='YES'; rec['hidden_gem_source']=str(s['path'].relative_to(ROOT)); rec['hidden_gem_summary']=mv
    if rec['connection_matched']=='NO': reasons.append('CONNECTION_NO_EXACT_MATERIAL_SOURCE_MATCH')
    if rec['market_matched']=='NO': reasons.append('MARKET_NO_EXACT_MATERIAL_SOURCE_MATCH')
    if rec['hidden_gem_matched']=='NO': reasons.append('HIDDEN_GEM_NO_EXACT_MATERIAL_SOURCE_MATCH')
    rec['join_failure_reason']='; '.join(reasons)
    conn_match += 1 if rec['connection_matched']=='YES' else 0
    market_match += 1 if rec['market_matched']=='YES' else 0
    hidden_match += 1 if rec['hidden_gem_matched']=='YES' else 0
    out.append(rec)

if not source_indexes:
    status='EVIDENCE_JOIN_BLOCKED_NO_SOURCES'
elif not live_rows:
    status='EVIDENCE_JOIN_BLOCKED_SCHEMA_MISSING'
else:
    status='EVIDENCE_JOIN_AUDIT_COMPLETE'
summary=[{'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'live_rows':len(live_rows),'selected_race_rows_if_detectable':selected_race_rows,'source_files_tested':len(source_indexes),'connection_matched_rows':conn_match,'market_matched_rows':market_match,'hidden_gem_matched_rows':hidden_match,'connection_unmatched_rows':len(live_rows)-conn_match,'market_unmatched_rows':len(live_rows)-market_match,'hidden_gem_unmatched_rows':len(live_rows)-hidden_match,'recommended_fix':'BUILD_EVIDENCE_FIX_CANDIDATE_FROM_EXACT_MATCHED_SOURCES' if (conn_match or market_match or hidden_match) else 'REPORT_SOURCE_UNAVAILABLE_OR_JOIN_SCHEMA_MISMATCH'}]
write_csv(out_detail,out,list(out[0].keys()) if out else ['race_date'])
write_csv(out_summary,summary,list(summary[0].keys()))
report=['EDGEiQ Current Intelligence Evidence Join Audit V1','='*56,f'Status: {status}',f'Generated: {summary[0]["generated_at"]}',f'Live rows: {len(live_rows)}',f'Source files tested: {len(source_indexes)}',f'Connection matched rows: {conn_match}',f'Market matched rows: {market_match}',f'Hidden gem matched rows: {hidden_match}','', 'Top source exact match counts:']
for p, exact, rows_count, flags in sorted(source_audits, key=lambda x:-x[1])[:20]: report.append(f'- {p.relative_to(ROOT)}: exact_live_matches={exact}; rows={rows_count}; flags={flags}')
report.append('')
report.append('Recommended fix: '+summary[0]['recommended_fix'])
out_report.write_text('\n'.join(report)+'\n',encoding='utf-8')
print(status)
print('live',len(live_rows),'sources',len(source_indexes),'conn',conn_match,'market',market_match,'hidden',hidden_match)
