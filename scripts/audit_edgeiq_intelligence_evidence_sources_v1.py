import csv
import re
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'

explicit = [
 'edgeiq_connection_intelligence_v1.csv',
 'edgeiq_connection_intelligence_current.csv',
 'edgeiq_explainability_terminal_feed_v1_1.csv',
 'edgeiq_explainability_terminal_feed_v1_2.csv',
 'edgeiq_live_terminal_feed_v1.csv',
 'edgeiq_live_runner_board_governed_v1.csv',
 'edgeiq_runner_explainability_v1.csv',
 'edgeiq_runner_dna_drawer_feed_v2.csv',
 'edgeiq_live_runner_factor_scorecard_v2.csv',
 'edgeiq_pre_result_market_history_warehouse_v1.csv',
 'edgeiq_tab_market_v1.csv',
 'edgeiq_market_tape.csv',
]
keywords = ['market','connection','hidden','gem']
out_detail = DATA / 'edgeiq_intelligence_evidence_sources_v1.csv'
out_summary = DATA / 'edgeiq_intelligence_evidence_sources_v1_summary.csv'
out_report = DATA / 'edgeiq_intelligence_evidence_sources_v1_report.txt'

def read_sample(path, limit=5000):
    if not path.exists(): return [], []
    try:
        with path.open('r', newline='', encoding='utf-8-sig') as f:
            reader=csv.DictReader(f)
            fields=reader.fieldnames or []
            rows=[]
            for i,row in enumerate(reader):
                if i<limit: rows.append(row)
                else: break
            return fields, rows
    except Exception:
        return [], []

def count_rows(path):
    if not path.exists(): return 0
    try:
        with path.open('r', newline='', encoding='utf-8-sig') as f:
            return max(sum(1 for _ in f)-1, 0)
    except Exception: return 0

def cols_matching(cols, pats):
    out=[]
    for c in cols:
        lc=c.lower()
        if any(p in lc for p in pats): out.append(c)
    return out

def norm(s):
    return re.sub(r'[^a-z0-9]+','',str(s).lower())

def detect_key(cols, pats): return cols_matching(cols, pats)

live_path=DATA/'edgeiq_live_runner_board_governed_v1.csv'
live_cols, live_rows=read_sample(live_path, 100000)
live_keys=set()
for r in live_rows:
    key=(norm(r.get('race_date') or r.get('current_race_date')), norm(r.get('track')), str(r.get('race_no','')).strip(), norm(r.get('horse') or r.get('runner_name') or r.get('horse_name')))
    live_keys.add(key)

candidate_files=[]
for name in explicit:
    candidate_files.append(DATA/name)
for path in DATA.glob('*.csv'):
    lname=path.name.lower()
    if any(k in lname for k in keywords) and path not in candidate_files:
        candidate_files.append(path)

rows_out=[]
for path in sorted(candidate_files, key=lambda p:p.name.lower()):
    exists=path.exists(); cols=[]; sample=[]; rows=0
    if exists:
        cols,sample=read_sample(path); rows=count_rows(path)
    key_cols=detect_key(cols, ['race_date','current_race_date','date','track','race_no','race','horse','runner'])
    race_key_cols=detect_key(cols, ['race_date','current_race_date','date','track','race_no'])
    horse_key_cols=detect_key(cols, ['horse','runner'])
    connection_cols=cols_matching(cols, ['connection','trainer','jockey','combo','partnership'])
    market_cols=cols_matching(cols, ['market','price','sp','odds','fair','prob','value'])
    hidden_cols=cols_matching(cols, ['hidden','gem','overlay','opportunity','value'])
    matched=0
    if exists and sample and race_key_cols and horse_key_cols:
        for r in sample:
            key=(norm(r.get('race_date') or r.get('current_race_date') or r.get('date')), norm(r.get('track')), str(r.get('race_no','')).strip(), norm(r.get('horse') or r.get('runner_name') or r.get('horse_name')))
            if key in live_keys: matched += 1
    likely=[]
    if connection_cols: likely.append('CONNECTION_SOURCE')
    if market_cols: likely.append('MARKET_SOURCE')
    if hidden_cols: likely.append('HIDDEN_GEM_SOURCE')
    if not exists: action='SOURCE_MISSING'
    elif rows==0: action='EMPTY_SOURCE'
    elif matched>0: action='USABLE_JOIN_CANDIDATE'
    elif not horse_key_cols or not race_key_cols: action='SCHEMA_REVIEW_REQUIRED'
    else: action='HAS_DATA_JOIN_MISMATCH_OR_HISTORICAL_ONLY'
    rows_out.append({
        'file_name': str(path.relative_to(ROOT)),
        'exists': 'YES' if exists else 'NO',
        'rows': rows,
        'columns': '|'.join(cols),
        'likely_race_key_columns': '|'.join(race_key_cols),
        'likely_horse_key_columns': '|'.join(horse_key_cols),
        'connection_evidence_columns': '|'.join(connection_cols),
        'market_evidence_columns': '|'.join(market_cols),
        'hidden_gem_columns': '|'.join(hidden_cols),
        'current_live_sample_match_rows': matched,
        'source_type_flags': '|'.join(likely),
        'recommended_action': action
    })

connection_sources=[r for r in rows_out if r['exists']=='YES' and r['connection_evidence_columns']]
market_sources=[r for r in rows_out if r['exists']=='YES' and r['market_evidence_columns']]
hidden_sources=[r for r in rows_out if r['exists']=='YES' and r['hidden_gem_columns']]
conn_rows=sum(int(r['rows']) for r in connection_sources)
market_rows=sum(int(r['rows']) for r in market_sources)
hidden_rows=sum(int(r['rows']) for r in hidden_sources)
issue_confirmed='YES' if (connection_sources or market_sources or hidden_sources) else 'NO'
status='INTELLIGENCE_EVIDENCE_SOURCES_AUDIT_COMPLETE' if rows_out else 'INTELLIGENCE_EVIDENCE_SOURCES_NOT_FOUND'
summary=[{
 'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),
 'files_audited':len(rows_out),'connection_sources_found':len(connection_sources),'connection_rows_available':conn_rows,
 'market_sources_found':len(market_sources),'market_rows_available':market_rows,
 'hidden_gem_sources_found':len(hidden_sources),'hidden_gem_rows_available':hidden_rows,
 'live_board_rows':len(live_rows),'current_screen_issue_confirmed':issue_confirmed,
 'usable_join_candidate_files':'|'.join([r['file_name'] for r in rows_out if r['recommended_action']=='USABLE_JOIN_CANDIDATE'])
}]
with out_detail.open('w', newline='', encoding='utf-8') as f:
    fields=list(rows_out[0].keys()) if rows_out else ['file_name']; w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows_out)
with out_summary.open('w', newline='', encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(summary[0].keys())); w.writeheader(); w.writerows(summary)
report=['EDGEiQ Intelligence Evidence Sources Audit V1','='*52,f'Status: {status}',f'Generated: {summary[0]["generated_at"]}',f'Files audited: {len(rows_out)}',f'Connection sources/rows: {len(connection_sources)} / {conn_rows}',f'Market sources/rows: {len(market_sources)} / {market_rows}',f'Hidden gem sources/rows: {len(hidden_sources)} / {hidden_rows}',f'Live board rows: {len(live_rows)}',f'Current screen issue confirmed: {issue_confirmed}','', 'Usable join candidate files:']
for r in rows_out:
    if r['recommended_action']=='USABLE_JOIN_CANDIDATE': report.append(f'- {r["file_name"]}: matches={r["current_live_sample_match_rows"]}; flags={r["source_type_flags"]}')
report.append('')
report.append('Missing/empty explicit sources:')
for r in rows_out:
    if r['recommended_action'] in {'SOURCE_MISSING','EMPTY_SOURCE'}: report.append(f'- {r["file_name"]}: {r["recommended_action"]}')
out_report.write_text('\n'.join(report)+'\n',encoding='utf-8')
print(status)
print('files',len(rows_out),'conn_sources',len(connection_sources),'market_sources',len(market_sources),'hidden_sources',len(hidden_sources),'usable',summary[0]['usable_join_candidate_files'])
