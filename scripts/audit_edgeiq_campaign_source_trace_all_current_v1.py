import csv, re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
GOV=DATA/'edgeiq_live_runner_board_governed_v1.csv'
CMD=DATA/'edgeiq_command_enrichment_feed_v3.csv'
DNA=DATA/'edgeiq_runner_dna_drawer_feed_v2.csv'
EXPLAIN=DATA/'edgeiq_explainability_terminal_feed_v1_2.csv'
FACTOR=DATA/'edgeiq_live_runner_factor_scorecard_v2.csv'
TRAJ=DATA/'edgeiq_runner_trajectory_feed_v1.csv'
CAMPAIGN=DATA/'edgeiq_campaign_intelligence_engine_v1_1.csv'
OUT=DATA/'edgeiq_campaign_source_trace_all_current_v1.csv'
SUMMARY=DATA/'edgeiq_campaign_source_trace_all_current_v1_summary.csv'
REPORT=DATA/'edgeiq_campaign_source_trace_all_current_v1_report.txt'

def read_csv(p):
    if not p.exists(): return [],[]
    with p.open('r',newline='',encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return list(r), list(r.fieldnames or [])
def write_csv(p,rows,fields):
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def clean(v): return ' '.join(str(v or '').strip().upper().replace('\u00a0',' ').split())
def clean_horse(v): return ''.join(ch for ch in clean(v) if ch.isalnum())
def race_no(v):
    s=clean(v).replace('RACE ','').replace('R','')
    return s.lstrip('0') or s
def key(r): return (clean(r.get('race_date') or r.get('current_race_date')),clean(r.get('track')),race_no(r.get('race_no')),clean_horse(r.get('horse') or r.get('horse_key')))
def rkey(r): return key(r)[:3]
def yes(v): return clean(v) in {'YES','TRUE','1','Y','ON'}
def populated(v): return str(v or '').strip() not in {'','-','--','N/A'}
def to_float(v):
    try:
        s=str(v or '').strip().replace('%','').replace('$','').replace(',','')
        if s in {'','-','--'}: return None
        return float(s)
    except Exception: return None
def fmt(v):
    if v is None: return ''
    if abs(v-round(v))<1e-9: return str(int(round(v)))
    return f'{v:.2f}'.rstrip('0').rstrip('.')

gov,_=read_csv(GOV); cmd,_=read_csv(CMD); dna,_=read_csv(DNA); explain,_=read_csv(EXPLAIN); factor,_=read_csv(FACTOR); traj,_=read_csv(TRAJ); camp,_=read_csv(CAMPAIGN)
cmd_by={key(r):r for r in cmd}; dna_by={key(r):r for r in dna}; explain_by={key(r):r for r in explain}; traj_by={key(r):r for r in traj}; camp_by={key(r):r for r in camp}
factors=defaultdict(dict)
for fr in factor: factors[key(fr)][clean(fr.get('factor'))]=fr
camp_horses={clean_horse(r.get('horse') or r.get('horse_key')) for r in camp if clean_horse(r.get('horse') or r.get('horse_key'))}
rows=[]
for gr in gov:
    k=key(gr); c=camp_by.get(k,{}); d=dna_by.get(k,{}); e=explain_by.get(k,{}); tr=traj_by.get(k,{}); fmap=factors.get(k,{})
    matched=bool(c); horse_seen=k[3] in camp_horses
    pos=yes(c.get('campaign_positive_flag')); risk=yes(c.get('campaign_risk_flag'))
    evidence=clean(c.get('evidence_status'))
    history_runs=to_float(c.get('history_runs_used'))
    sample=to_float(c.get('prep_stage_sample_count'))
    # Campaign evidence can be material without being positive/risk if campaign engine has usable history/profile.
    has_profile=clean(c.get('campaign_profile_band')) not in {'','UNKNOWN','UNPROVEN'} or clean(c.get('prep_stage_label')) not in {'','UNKNOWN'}
    has_history=(history_runs or 0)>0 or (sample or 0)>0 or evidence not in {'','NO_HISTORY','SOURCE_MISSING'}
    factor_campaign=fmap.get('CAMPAIGN') or fmap.get('PROFILE') or fmap.get('FORM') or {}
    factor_score=to_float(factor_campaign.get('factor_score')) if factor_campaign else None
    dna_campaign_text=''
    for col in ['runner_dna_v6_2_narrative','impact_explanation','runner_dna_v6_1_customer_summary']:
        if 'CAMPAIGN' in clean(d.get(col,'')):
            dna_campaign_text=d.get(col,'')
            break
    trajectory_context=tr.get('trajectory_band_v1','') if tr else ''
    if matched and (pos or risk or has_profile or has_history):
        classification='HAS_CAMPAIGN_EVIDENCE'
        available='YES'
    elif matched:
        classification='TRUE_ZERO'
        available='NO'
    elif horse_seen:
        classification='JOIN_FAILED'
        available='NO'
    else:
        # Check alternate sources. They do not create campaign evidence unless they explicitly mention campaign.
        if dna_campaign_text:
            classification='FIELD_NAME_MISMATCH'
        else:
            classification='SOURCE_MISSING'
        available='NO'
    score=''
    if available=='YES':
        if pos and not risk: score='70'
        elif risk and not pos: score='35'
        elif pos and risk: score='55'
        elif has_profile or has_history: score='50'
    elif factor_score is not None and clean(factor_campaign.get('factor'))=='CAMPAIGN':
        score=fmt(factor_score)
    summary=c.get('campaign_narrative','') if c else ''
    if not summary and dna_campaign_text: summary=dna_campaign_text
    rows.append({'race_date':gr.get('race_date',''),'track':gr.get('track',''),'race_no':gr.get('race_no',''),'horse':gr.get('horse',''),'campaign_source_matched':'YES' if matched else 'NO','campaign_horse_seen_elsewhere':'YES' if horse_seen else 'NO','campaign_available':available,'campaign_gap_classification':classification,'campaign_score':score,'campaign_summary':summary,'campaign_profile_band':c.get('campaign_profile_band',''),'prep_stage_label':c.get('prep_stage_label',''),'evidence_status':c.get('evidence_status',''),'history_runs_used':c.get('history_runs_used',''),'prep_stage_sample_count':c.get('prep_stage_sample_count',''),'campaign_positive_flag':c.get('campaign_positive_flag',''),'campaign_risk_flag':c.get('campaign_risk_flag',''),'factor_campaign_score':fmt(factor_score),'dna_campaign_text_available':'YES' if dna_campaign_text else 'NO','trajectory_context_available':'YES' if trajectory_context else 'NO','matched_source':'edgeiq_campaign_intelligence_engine_v1_1.csv' if matched else ('DNA_TEXT' if dna_campaign_text else '')})
byrace=defaultdict(list)
for r in rows: byrace[(clean(r['race_date']),clean(r['track']),race_no(r['race_no']))].append(r)
status='CAMPAIGN_TRACE_COMPLETE'
if any(r['campaign_gap_classification'] in {'JOIN_FAILED','FIELD_NAME_MISMATCH'} for r in rows): status='CAMPAIGN_JOIN_OR_FIELD_ISSUE_FOUND'
summary={'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'rows':len(rows),'races':len(byrace),'campaign_source_matched_rows':sum(1 for r in rows if r['campaign_source_matched']=='YES'),'campaign_available_rows':sum(1 for r in rows if r['campaign_available']=='YES'),'true_zero_rows':sum(1 for r in rows if r['campaign_gap_classification']=='TRUE_ZERO'),'source_missing_rows':sum(1 for r in rows if r['campaign_gap_classification']=='SOURCE_MISSING'),'join_failed_rows':sum(1 for r in rows if r['campaign_gap_classification']=='JOIN_FAILED'),'field_name_mismatch_rows':sum(1 for r in rows if r['campaign_gap_classification']=='FIELD_NAME_MISMATCH')}
write_csv(OUT,rows,list(rows[0].keys())); write_csv(SUMMARY,[summary],list(summary.keys()))
REPORT.write_text('\n'.join(['EDGEiQ Campaign Source Trace All Current V1','='*50,f'Status: {status}',f'Rows/races: {len(rows)}/{len(byrace)}',f'Source matched/available: {summary["campaign_source_matched_rows"]}/{summary["campaign_available_rows"]}',f'TRUE_ZERO/SOURCE_MISSING/JOIN_FAILED/FIELD_NAME_MISMATCH: {summary["true_zero_rows"]}/{summary["source_missing_rows"]}/{summary["join_failed_rows"]}/{summary["field_name_mismatch_rows"]}'])+'\n',encoding='utf-8')
print(status)
