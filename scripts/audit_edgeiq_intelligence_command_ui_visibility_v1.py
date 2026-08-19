import csv, re
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'
ts=ROOT/'src'/'components'/'RaceIntelligenceScreen.tsx'; live=DATA/'edgeiq_live_runner_board_governed_v1.csv'
out=DATA/'edgeiq_intelligence_command_ui_visibility_v1.csv'; sumout=DATA/'edgeiq_intelligence_command_ui_visibility_v1_summary.csv'; report=DATA/'edgeiq_intelligence_command_ui_visibility_v1_report.txt'
terms=['CONNECTION ANGLES','Evidence Footer','CONNECTION','MARKET','Hidden Gem','Horse Profiles of Interest','Race Shape Command','Key Questions','Race Control Room','COMMAND workspace','edgeiq_v7_2g2_active_display_fair_price_shadow','edgeiq_connection_evidence_available','edgeiq_market_evidence_available','edgeiq_hidden_gem_evidence_available','MARKET COMMAND','CONNECTION COMMAND','EDGEIQ SCORE BREAKDOWN']
def read_csv(path):
    if not path.exists(): return [], []
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return r.fieldnames or [], list(r)
def yes(v): return str(v).strip().upper() in {'YES','TRUE','1','Y'}
text=ts.read_text(encoding='utf-8', errors='replace') if ts.exists() else ''
lines=text.splitlines(); rows=[]
for term in terms:
    matches=[]
    for i,line in enumerate(lines, start=1):
        if term.lower() in line.lower(): matches.append((i,line.strip()))
    cond=[]
    for i,line in matches:
        window='\n'.join(lines[max(0,i-5):min(len(lines),i+5)])
        if any(x in window for x in ['display:', '&&', '?', '.filter(', 'runnerSubMode', 'intelMode', 'selectedConnectionLoaded', 'evidenceFlag']): cond.append(str(i))
    rows.append({'term':term,'present':'YES' if matches else 'NO','match_count':len(matches),'sample_lines':' | '.join([f'{i}:{l[:120]}' for i,l in matches[:8]]),'conditional_rendering_lines':'|'.join(cond[:12]),'likely_below_fold':'YES' if matches and min(i for i,_ in matches)>5000 else 'NO'})
cols, live_rows=read_csv(live)
conn=sum(1 for r in live_rows if yes(r.get('edgeiq_connection_evidence_available')))
market=sum(1 for r in live_rows if yes(r.get('edgeiq_market_evidence_available')))
hidden=sum(1 for r in live_rows if yes(r.get('edgeiq_hidden_gem_evidence_available')))
fields_present=[f for f in ['edgeiq_connection_evidence_available','edgeiq_market_evidence_available','edgeiq_hidden_gem_evidence_available','edgeiq_v7_2g2_active_display_fair_price_shadow'] if f in cols]
# below fold heuristic: COMMAND sections appear after source line 5000 and screenshot first viewport misses them.
connection_term=next((r for r in rows if r['term']=='CONNECTION'),{})
recommended='ADD_COMPACT_MARKET_CONNECTION_SCORE_CARDS_IN_COMMAND_VISIBLE_REGION; KEEP_EXISTING_FOOTER; USE_LIVE_GOVERNED_EVIDENCE_FIELDS'
status='UI_VISIBILITY_AUDIT_COMPLETE' if ts.exists() and live.exists() else 'UI_VISIBILITY_BLOCKED'
summary=[{'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'tsx_exists':'YES' if ts.exists() else 'NO','live_board_exists':'YES' if live.exists() else 'NO','live_rows':len(live_rows),'evidence_fields_present':'|'.join(fields_present),'connection_evidence_rows':conn,'market_evidence_rows':market,'hidden_gem_evidence_rows':hidden,'sections_present_count':sum(1 for r in rows if r['present']=='YES'),'conditional_terms_count':sum(1 for r in rows if r['conditional_rendering_lines']),'likely_below_fold':'YES','recommended_fix':recommended}]
with out.open('w', newline='', encoding='utf-8') as f:
    w=csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
with sumout.open('w', newline='', encoding='utf-8') as f:
    w=csv.DictWriter(f, fieldnames=list(summary[0].keys())); w.writeheader(); w.writerows(summary)
report.write_text('\n'.join(['EDGEiQ Intelligence Command UI Visibility Audit V1','='*60,f'Status: {status}',f'TSX exists: {summary[0]["tsx_exists"]}',f'Live rows: {len(live_rows)}',f'Evidence fields present: {summary[0]["evidence_fields_present"]}',f'Connection/Market/Hidden rows: {conn} / {market} / {hidden}',f'Sections present: {summary[0]["sections_present_count"]}',f'Conditional terms: {summary[0]["conditional_terms_count"]}',f'Likely below fold: {summary[0]["likely_below_fold"]}',f'Recommended fix: {recommended}'])+'\n', encoding='utf-8')
print(status); print('live_rows',len(live_rows),'conn',conn,'market',market,'hidden',hidden)
