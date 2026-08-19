import csv, re
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'
live=DATA/'edgeiq_live_runner_board_governed_v1.csv'; cand=DATA/'edgeiq_current_intelligence_evidence_fix_candidate_v1.csv'
outboard=DATA/'edgeiq_live_runner_board_governed_v1_EVIDENCE_MERGED.csv'
out=DATA/'edgeiq_evidence_merge_v1.csv'; sumout=DATA/'edgeiq_evidence_merge_v1_summary.csv'; report=DATA/'edgeiq_evidence_merge_v1_report.txt'
fields_to_merge=['edgeiq_connection_evidence_available','edgeiq_connection_angle_summary','edgeiq_market_evidence_available','edgeiq_market_signal_summary','edgeiq_hidden_gem_evidence_available','edgeiq_hidden_gem_summary','edgeiq_evidence_fix_source','edgeiq_evidence_fix_status']
pricing_fields=['fair_price','ui_fair_price','live_price','win_pct','edgeiq_v7_2g2_active_display_fair_price_shadow','edgeiq_v7_2g2_on_preview_display_fair_price']
def read(path):
    if not path.exists(): return [], []
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return r.fieldnames or [], list(r)
def write(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore', lineterminator='\n'); w.writeheader(); w.writerows(rows)
def norm(s): return re.sub(r'[^a-z0-9]+','',str(s or '').lower())
def rno(s):
    m=re.search(r'\d+', str(s or '')); return m.group(0) if m else str(s or '').strip()
def first(row, cols):
    for c in cols:
        if c in row and str(row.get(c,'')).strip(): return str(row.get(c,'')).strip()
    return ''
def key(row): return (norm(first(row,['race_date','meeting_date','current_race_date','date'])), norm(first(row,['track'])), rno(first(row,['race_no','race_number','race'])), norm(first(row,['horse','horse_name','runner_name','horse_key'])))
def blank(v): return str(v if v is not None else '').strip()==''
status='EVIDENCE_MERGE_READY_FOR_AUDIT'; err=''; audit=[]; rows_out=[]; matched=0; no_match=0; fields=[]
try:
    live_cols, live_rows=read(live); cand_cols, cand_rows=read(cand)
    if not live_rows: raise RuntimeError('Live board missing or empty')
    if not cand_rows: raise RuntimeError('Evidence candidate missing or empty')
    idx={key(r):r for r in cand_rows}
    fields=list(live_cols)
    for c in fields_to_merge:
        if c not in fields: fields.append(c)
    for lr in live_rows:
        k=key(lr); cr=idx.get(k); changed=[]
        if cr:
            matched+=1
            for c in fields_to_merge:
                if blank(lr.get(c,'')):
                    val=str(cr.get(c,'')).strip()
                    if val:
                        lr[c]=val; changed.append(c)
            if blank(lr.get('edgeiq_evidence_fix_status','')):
                lr['edgeiq_evidence_fix_status']='NO_SOURCE_MATCH'
        else:
            no_match+=1
            for c in fields_to_merge:
                if blank(lr.get(c,'')): lr[c]=''
            lr['edgeiq_connection_evidence_available']='NO'
            lr['edgeiq_market_evidence_available']='NO'
            lr['edgeiq_hidden_gem_evidence_available']='NO'
            lr['edgeiq_evidence_fix_source']='NO_SOURCE_MATCH'
            lr['edgeiq_evidence_fix_status']='NO_SOURCE_MATCH'
        audit.append({'race_date':first(lr,['race_date','meeting_date','current_race_date']),'track':lr.get('track',''),'race_no':lr.get('race_no',''),'horse':first(lr,['horse','horse_name','runner_name']),'candidate_match':'YES' if cr else 'NO','fields_filled':'|'.join(changed),'evidence_status':lr.get('edgeiq_evidence_fix_status','')})
        rows_out.append(lr)
    write(outboard, rows_out, fields)
except Exception as e:
    status='BLOCKED'; err=str(e)
summary=[{'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'live_rows':len(rows_out),'candidate_matches':matched,'candidate_no_matches':no_match,'evidence_fields_added':'|'.join(fields_to_merge),'pricing_fields_present':'|'.join([p for p in pricing_fields if p in fields]),'output_file':str(outboard),'error':err}]
write(out, audit if audit else [{'error':err}], list(audit[0].keys()) if audit else ['error'])
write(sumout, summary, list(summary[0].keys()))
report.write_text('\n'.join(['EDGEiQ Evidence Fields Merge V1','='*42,f'Status: {status}',f'Generated: {summary[0]["generated_at"]}',f'Live rows: {len(rows_out)}',f'Candidate matches: {matched}',f'Candidate no matches: {no_match}',f'Output: {outboard}',f'Pricing fields present: {summary[0]["pricing_fields_present"]}',f'Error: {err or "None"}'])+'\n', encoding='utf-8')
print(status); print('rows',len(rows_out),'matches',matched,'no_match',no_match)
