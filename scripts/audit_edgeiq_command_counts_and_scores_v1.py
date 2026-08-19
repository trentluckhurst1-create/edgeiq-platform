import csv, re, json, math
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'
live=DATA/'edgeiq_live_runner_board_governed_v1.csv'; feed=DATA/'edgeiq_command_enrichment_feed_v1.csv'; cand=DATA/'edgeiq_current_intelligence_evidence_fix_candidate_v1.csv'; ts=ROOT/'src'/'components'/'RaceIntelligenceScreen.tsx'
out=DATA/'edgeiq_command_counts_and_scores_v1.csv'; sumout=DATA/'edgeiq_command_counts_and_scores_v1_summary.csv'; report=DATA/'edgeiq_command_counts_and_scores_v1_report.txt'
def read(path):
    if not path.exists(): return [], []
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return r.fieldnames or [], list(r)
def yes(v): return str(v).strip().upper() in {'YES','TRUE','1','Y'}
def nonblank(v):
    s=str(v or '').strip(); return bool(s) and s.upper() not in {'NO','NONE','N/A','NA','NO_SOURCE_MATCH','NO_CONNECTION','NO_EVIDENCE','FALSE','0','--'}
def numlike(v):
    try:
        s=str(v).replace('$','').replace('%','').replace(',','').strip()
        return float(s) if s!='' else None
    except Exception: return None
def field_stats(rows, flag, summary):
    return {'field_exists':'YES' if rows and flag in rows[0] else 'NO','true_count':sum(1 for r in rows if yes(r.get(flag))),'summary_nonblank_count':sum(1 for r in rows if nonblank(r.get(summary))),'sample_values':' | '.join([str(r.get(summary,''))[:120] for r in rows if nonblank(r.get(summary))][:3])}
def numeric_fields(cols, rows):
    out=[]
    sample=rows[:250]
    for c in cols:
        vals=[numlike(r.get(c)) for r in sample]
        vals=[v for v in vals if v is not None]
        if len(vals)>=max(3, min(20, len(sample)//10)):
            uniq=len(set(vals)); mn=min(vals); mx=max(vals); avg=sum(vals)/len(vals)
            suspicious='YES' if any(x in c.lower() for x in ['runner_no','runnerno','barrier','rank','saddle','horse_no','number']) or (uniq<=5 and mx<=30) else 'NO'
            out.append({'field':c,'numeric_count':len(vals),'min':mn,'max':mx,'avg':avg,'unique_count':uniq,'suspicious_non_score':suspicious})
    return out
live_cols, live_rows=read(live); feed_cols, feed_rows=read(feed); cand_cols, cand_rows=read(cand)
text=ts.read_text(encoding='utf-8', errors='replace') if ts.exists() else ''
rows=[]
for source_name, cols, rows_in in [('governed_board',live_cols,live_rows),('enrichment_v1',feed_cols,feed_rows),('candidate',cand_cols,cand_rows)]:
    for label, flag, summ in [('connection','edgeiq_connection_evidence_available','edgeiq_connection_angle_summary'),('market','edgeiq_market_evidence_available','edgeiq_market_signal_summary'),('hidden_gem','edgeiq_hidden_gem_evidence_available','edgeiq_hidden_gem_summary')]:
        st=field_stats(rows_in,flag,summ)
        rows.append({'source':source_name,'audit_type':'evidence','field_group':label,'field':flag,'field_exists':st['field_exists'],'true_count':st['true_count'],'summary_nonblank_count':st['summary_nonblank_count'],'sample_values':st['sample_values'],'line_numbers':'','uses':''})
for pat,label in [('connectionsCoverageCount','Connections footer count'),('marketCoverageCount','Market footer count'),('hiddenGemCoverageCount','Hidden Gem footer count'),('connectionCommandRows','Connection Command'),('scoreBreakdownRows','Score Breakdown'),('scoreBreakdownRunner','Score Breakdown runner'),('edgeiq_v7_2g2_active_display_fair_price_shadow','V7.2G2 display')]:
    lns=[str(i) for i,l in enumerate(text.splitlines(),1) if pat in l]
    uses=[]
    for i,l in enumerate(text.splitlines(),1):
        if pat in l or (lns and any(abs(i-int(x))<=3 for x in lns[:8])):
            if 'runner_no' in l or 'barrier' in l or 'rank' in l: uses.append('SUSPICIOUS_SCORE_FIELD')
            if 'edgeiq_' in l: uses.append('EDGEIQ_FIELD')
            if 'evidenceFlag' in l: uses.append('EVIDENCE_FLAG')
            if 'commandEnrichment' in l: uses.append('COMMAND_ENRICHMENT')
    rows.append({'source':'tsx','audit_type':'logic','field_group':label,'field':pat,'field_exists':'YES' if lns else 'NO','true_count':'','summary_nonblank_count':'','sample_values':'','line_numbers':'|'.join(lns),'uses':'|'.join(sorted(set(uses)))})
for src, cols, rows_in in [('governed_board',live_cols,live_rows),('enrichment_v1',feed_cols,feed_rows)]:
    for nf in numeric_fields(cols, rows_in)[:120]:
        rows.append({'source':src,'audit_type':'numeric_field','field_group':'score_candidate','field':nf['field'],'field_exists':'YES','true_count':nf['numeric_count'],'summary_nonblank_count':'','sample_values':f"min={nf['min']}; max={nf['max']}; unique={nf['unique_count']}; suspicious={nf['suspicious_non_score']}",'line_numbers':'','uses':'SUSPICIOUS_NON_SCORE' if nf['suspicious_non_score']=='YES' else 'POSSIBLE_SCORE'})
conn=field_stats(live_rows,'edgeiq_connection_evidence_available','edgeiq_connection_angle_summary')
market=field_stats(live_rows,'edgeiq_market_evidence_available','edgeiq_market_signal_summary')
hidden=field_stats(live_rows,'edgeiq_hidden_gem_evidence_available','edgeiq_hidden_gem_summary')
tsx_correct_footer='YES' if all(x in text for x in ['edgeiq_connection_evidence_available','edgeiq_market_evidence_available','edgeiq_hidden_gem_evidence_available']) and 'commandEnrichment' in text else 'NO'
tsx_correct_score='YES' if 'edgeiq_score_overall_v2' in text else 'NO'
overall_suspect='YES' if 'total_rating_points' not in live_cols or conn['true_count']>0 and 'commandEnrichment' not in text else 'YES'
summary=[{'status':'COMMAND_COUNTS_AND_SCORES_AUDIT_COMPLETE','generated_at':datetime.now().isoformat(timespec='seconds'),'live_rows':len(live_rows),'enrichment_rows':len(feed_rows),'connection_available_count':conn['true_count'],'market_available_count':market['true_count'],'hidden_gem_available_count':hidden['true_count'],'tsx_uses_correct_footer_fields':tsx_correct_footer,'tsx_uses_correct_score_fields':tsx_correct_score,'overall_score_suspect':overall_suspect,'recommended_fix':'BUILD_V2_FEED_AND_WIRE_COMMAND_TO_COMMAND_ENRICHMENT_V2; DO_NOT_USE_RUNNER_NO_BARRIER_RANK_FOR_OVERALL'}]
with out.open('w', newline='', encoding='utf-8') as f:
    w=csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
with sumout.open('w', newline='', encoding='utf-8') as f:
    w=csv.DictWriter(f, fieldnames=list(summary[0].keys())); w.writeheader(); w.writerows(summary)
report.write_text('\n'.join(['EDGEiQ Command Counts and Scores Audit V1','='*52,f'Status: {summary[0]["status"]}',f'Live rows: {len(live_rows)}',f'Enrichment v1 rows: {len(feed_rows)}',f'Governed connection/market/hidden counts: {conn["true_count"]} / {market["true_count"]} / {hidden["true_count"]}',f'TSX uses command enrichment for counts: {tsx_correct_footer}',f'TSX uses v2 score fields: {tsx_correct_score}',f'Overall score suspect: {overall_suspect}',f'Recommended fix: {summary[0]["recommended_fix"]}'])+'\n', encoding='utf-8')
print(summary[0]['status']); print('live',len(live_rows),'feed',len(feed_rows),'conn',conn['true_count'],'market',market['true_count'],'hidden',hidden['true_count'],'tsx_footer',tsx_correct_footer)
