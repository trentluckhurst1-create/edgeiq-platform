import csv, re
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'
live=DATA/'edgeiq_live_runner_board_governed_v1.csv'; feed=DATA/'edgeiq_command_enrichment_feed_v2.csv'; ts=ROOT/'src/components/RaceIntelligenceScreen.tsx'
out=DATA/'edgeiq_footer_count_truth_v1.csv'; sumout=DATA/'edgeiq_footer_count_truth_v1_summary.csv'; report=DATA/'edgeiq_footer_count_truth_v1_report.txt'
def read(path):
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return r.fieldnames or [], list(r)
def yes(v): return str(v).strip().upper() in {'YES','TRUE','1','Y'}
def meaningful(v):
    s=str(v or '').strip().upper(); return bool(s) and s not in {'NO','NONE','N/A','NA','NO_SOURCE_MATCH','NO_CONNECTION','NO_EVIDENCE','FALSE','0','--'}
def key(r): return (str(r.get('race_date','')).strip(), str(r.get('track','')).strip(), str(r.get('race_no','')).strip())
cols, rows=read(feed); lcols,lrows=read(live); text=ts.read_text(encoding='utf-8',errors='replace')
groups={}
for r in rows: groups.setdefault(key(r),[]).append(r)
outrows=[]
for rk, grp in sorted(groups.items()):
    field=len(grp)
    mc=sum(1 for r in grp if yes(r.get('edgeiq_market_evidence_available_v2')) or meaningful(r.get('edgeiq_market_signal_summary_v2')))
    cc=sum(1 for r in grp if yes(r.get('edgeiq_connection_evidence_available_v2')) or meaningful(r.get('edgeiq_connection_angle_summary_v2')))
    hc=sum(1 for r in grp if yes(r.get('edgeiq_hidden_gem_evidence_available_v2')) or meaningful(r.get('edgeiq_hidden_gem_summary_v2')))
    # Current visual footer count is inferred from the old runner board when commandEnrichment sidecar is not joined/rendered.
    footer_market=0 if 'runnerBoard: "/data/edgeiq_live_runner_board_v1.csv"' in text else mc
    footer_conn=0 if 'runnerBoard: "/data/edgeiq_live_runner_board_v1.csv"' in text else cc
    footer_hidden=0 if 'runnerBoard: "/data/edgeiq_live_runner_board_v1.csv"' in text else hc
    status='DIFFERENCE' if (mc,cc,hc)!=(footer_market,footer_conn,footer_hidden) else 'MATCH'
    outrows.append({'race_date':rk[0],'track':rk[1],'race_no':rk[2],'field_size':field,'true_market_count':mc,'true_connection_count':cc,'true_hidden_gem_count':hc,'footer_market_count_inferred':footer_market,'footer_connection_count_inferred':footer_conn,'footer_hidden_gem_count_inferred':footer_hidden,'difference':status})
# current screenshot likely field size 16; pick first mismatch with field_size 16 for summary, else first mismatch.
focus=next((r for r in outrows if int(r['field_size'])==16 and r['difference']=='DIFFERENCE'), None) or next((r for r in outrows if r['difference']=='DIFFERENCE'), outrows[0] if outrows else {})
status='FOOTER_COUNTS_INCORRECT' if any(r['difference']=='DIFFERENCE' for r in outrows) else 'FOOTER_COUNTS_CORRECT'
summary=[{'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'races_audited':len(outrows),'focus_race': '|'.join([str(focus.get('race_date','')),str(focus.get('track','')),str(focus.get('race_no',''))]),'focus_field_size':focus.get('field_size',''),'true_counts':f"market={focus.get('true_market_count','')}; connection={focus.get('true_connection_count','')}; hidden={focus.get('true_hidden_gem_count','')}",'footer_counts':f"market={focus.get('footer_market_count_inferred','')}; connection={focus.get('footer_connection_count_inferred','')}; hidden={focus.get('footer_hidden_gem_count_inferred','')}",'difference':'YES' if status=='FOOTER_COUNTS_INCORRECT' else 'NO','tsx_runner_board_source':'edgeiq_live_runner_board_v1.csv' if 'edgeiq_live_runner_board_v1.csv' in text else 'other'}]
for p, data in [(out,outrows),(sumout,summary)]:
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0].keys())); w.writeheader(); w.writerows(data)
report.write_text('\n'.join(['EDGEiQ Footer Count Truth Audit V1','='*42,f'Status: {status}',f'Races audited: {len(outrows)}',f'Focus race: {summary[0]["focus_race"]}',f'Focus field size: {summary[0]["focus_field_size"]}',f'TRUE_COUNTS: {summary[0]["true_counts"]}',f'FOOTER_COUNTS: {summary[0]["footer_counts"]}',f'DIFFERENCE: {summary[0]["difference"]}',f'TSX runner board source: {summary[0]["tsx_runner_board_source"]}'])+'\n',encoding='utf-8')
print(status); print(summary[0])
