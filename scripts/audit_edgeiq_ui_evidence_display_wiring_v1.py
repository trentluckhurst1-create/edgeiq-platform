import csv
import re
from pathlib import Path
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
ts_path=ROOT/'src'/'components'/'RaceIntelligenceScreen.tsx'
fix_path=DATA/'edgeiq_current_intelligence_evidence_fix_candidate_v1.csv'
live_path=DATA/'edgeiq_live_runner_board_governed_v1.csv'
out_detail=DATA/'edgeiq_ui_evidence_display_wiring_v1.csv'
out_summary=DATA/'edgeiq_ui_evidence_display_wiring_v1_summary.csv'
out_report=DATA/'edgeiq_ui_evidence_display_wiring_v1_report.txt'

def read_csv(path):
    if not path.exists(): return [], []
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return r.fieldnames or [], list(r)
def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)

text=ts_path.read_text(encoding='utf-8', errors='replace') if ts_path.exists() else ''
lines=text.splitlines()
terms=['CONNECTION ANGLES','Connection','connection','MARKET','Market','market','HIDDEN GEM','Hidden Gem','hiddenGem','hidden','evidence','0/20','No connection angles triggered','unavailable']
findings=[]
for i,line in enumerate(lines, start=1):
    hit=[t for t in terms if t in line]
    if hit:
        window=' '.join(line.strip().split())[:500]
        issue=[]
        if '0/20' in line: issue.append('POSSIBLE_HARDCODED_ZERO_COUNT')
        if 'No connection angles triggered' in line: issue.append('CONNECTION_EMPTY_STATE_TEXT')
        if 'unavailable' in line.lower(): issue.append('UNAVAILABLE_RENDER_STATE')
        if any(x in line for x in ['connectionAngles','connectionInsights','connectionsLoaded','marketLoaded','hiddenGem']): issue.append('CONDITION_OR_FIELD_REFERENCE')
        findings.append({'file':str(ts_path.relative_to(ROOT)),'line':i,'matched_terms':'|'.join(hit),'code_excerpt':window,'issue_flag':'|'.join(issue) if issue else 'REFERENCE','recommended_action':'Review field source and condition; prefer edgeiq_current_intelligence_evidence_fix_candidate_v1 fields if merged/wired.'})

fix_cols, fix_rows=read_csv(fix_path); live_cols, live_rows=read_csv(live_path)
conn_fix=sum(1 for r in fix_rows if r.get('edgeiq_connection_evidence_available')=='YES')
market_fix=sum(1 for r in fix_rows if r.get('edgeiq_market_evidence_available')=='YES')
hidden_fix=sum(1 for r in fix_rows if r.get('edgeiq_hidden_gem_evidence_available')=='YES')
missing_ui_fields=[]
for c in ['edgeiq_connection_evidence_available','edgeiq_market_evidence_available','edgeiq_hidden_gem_evidence_available']:
    if c not in live_cols: missing_ui_fields.append(c)

hardcoded_zero=sum(1 for f in findings if 'POSSIBLE_HARDCODED_ZERO_COUNT' in f['issue_flag'])
empty_state=sum(1 for f in findings if 'CONNECTION_EMPTY_STATE_TEXT' in f['issue_flag'] or 'UNAVAILABLE_RENDER_STATE' in f['issue_flag'])
condition_refs=sum(1 for f in findings if 'CONDITION_OR_FIELD_REFERENCE' in f['issue_flag'])
if not ts_path.exists(): status='UI_EVIDENCE_WIRING_AUDIT_BLOCKED_TSX_MISSING'
else: status='UI_EVIDENCE_WIRING_AUDIT_COMPLETE'
summary=[{'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'tsx_exists':'YES' if ts_path.exists() else 'NO','ui_reference_lines_found':len(findings),'hardcoded_zero_count_lines':hardcoded_zero,'empty_or_unavailable_state_lines':empty_state,'condition_or_field_reference_lines':condition_refs,'fix_candidate_exists':'YES' if fix_path.exists() else 'NO','fix_candidate_rows':len(fix_rows),'fix_candidate_connection_rows':conn_fix,'fix_candidate_market_rows':market_fix,'fix_candidate_hidden_gem_rows':hidden_fix,'live_board_rows':len(live_rows),'live_board_missing_fix_fields':'|'.join(missing_ui_fields),'fields_missing_or_hardcoded':'YES' if missing_ui_fields or hardcoded_zero or empty_state else 'NO','recommended_safe_fix':'ADD_OR_MERGE_EVIDENCE_FIX_FEED_FIELDS_THEN_UPDATE_RENDER_CONDITIONS; DO_NOT_SHOW_ZERO_WHEN_SOURCE_AVAILABLE'}]
write_csv(out_detail, findings, list(findings[0].keys()) if findings else ['file','line','matched_terms','code_excerpt','issue_flag','recommended_action'])
write_csv(out_summary, summary, list(summary[0].keys()))
report=['EDGEiQ UI Evidence Display Wiring Audit V1','='*52,f'Status: {status}',f'Generated: {summary[0]["generated_at"]}',f'UI reference lines found: {len(findings)}',f'Hardcoded 0/20 lines: {hardcoded_zero}',f'Empty/unavailable state lines: {empty_state}',f'Condition/field reference lines: {condition_refs}',f'Fix candidate rows: {len(fix_rows)}',f'Fix candidate connection/market/hidden: {conn_fix} / {market_fix} / {hidden_fix}',f'Live board missing fix fields: {summary[0]["live_board_missing_fix_fields"] or "None"}','', 'Likely suppressors:']
for f in findings:
    if f['issue_flag']!='REFERENCE': report.append(f'- line {f["line"]}: {f["issue_flag"]}: {f["code_excerpt"]}')
report.append('')
report.append('Recommended safe fix: '+summary[0]['recommended_safe_fix'])
report.append('No UI modified by this audit.')
out_report.write_text('\n'.join(report)+'\n',encoding='utf-8')
print(status)
print('findings',len(findings),'hardcoded_zero',hardcoded_zero,'empty_state',empty_state,'missing_live_fields',summary[0]['live_board_missing_fix_fields'])
