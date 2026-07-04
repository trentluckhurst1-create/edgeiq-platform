import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
GOV=DATA/'edgeiq_live_runner_board_governed_v1.csv'
TRACE=DATA/'edgeiq_campaign_source_trace_all_current_v1.csv'
CAMPAIGN=DATA/'edgeiq_campaign_intelligence_engine_v1_1.csv'
OUT=DATA/'edgeiq_campaign_feed_v1.csv'
SUMMARY=DATA/'edgeiq_campaign_feed_v1_summary.csv'
AUDIT=DATA/'edgeiq_campaign_feed_v1_audit.csv'
REPORT=DATA/'edgeiq_campaign_feed_v1_report.txt'

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
def to_float(v):
    try:
        s=str(v or '').strip().replace('%','').replace(',','')
        return float(s) if s not in {'','-','--'} else None
    except Exception: return None

gov,_=read_csv(GOV); campaign,_=read_csv(CAMPAIGN)
strict={key(r):r for r in campaign}
by_horse=defaultdict(list)
for r in campaign: by_horse[clean_horse(r.get('horse') or r.get('horse_key'))].append(r)
rows=[]; audit=[]
for gr in gov:
    k=key(gr); h=k[3]
    src=strict.get(k); method='STRICT_CURRENT_RACE'
    if not src and by_horse.get(h):
        # Choose highest evidence quality, then latest date string.
        order={'STRONG_HISTORY':3,'LIMITED_HISTORY':2,'NO_HISTORY':1,'':0}
        src=sorted(by_horse[h], key=lambda r:(order.get(clean(r.get('evidence_status')),0), clean(r.get('current_race_date'))), reverse=True)[0]
        method='HORSE_KEY_FALLBACK'
    if src:
        evidence=clean(src.get('evidence_status'))
        pos=yes(src.get('campaign_positive_flag')); risk=yes(src.get('campaign_risk_flag'))
        profile_band=clean(src.get('campaign_profile_band'))
        history_runs=to_float(src.get('history_runs_used')) or 0
        sample=to_float(src.get('prep_stage_sample_count')) or 0
        has_material=evidence not in {'','NO_HISTORY','SOURCE_MISSING'} or profile_band not in {'','UNKNOWN','UNPROVEN'} or history_runs>0 or sample>0 or pos or risk
        if has_material:
            available='YES'; truth='CAMPAIGN_EVIDENCE_AVAILABLE'
        else:
            available='NO'; truth='TRUE_ZERO_NO_CAMPAIGN_HISTORY'
        if pos and not risk: score='70'
        elif risk and not pos: score='35'
        elif pos and risk: score='55'
        elif has_material: score='50'
        else: score=''
        narrative=src.get('campaign_narrative','') or ('Limited campaign history available.' if has_material else 'No qualifying campaign pattern available.')
        source='edgeiq_campaign_intelligence_engine_v1_1.csv'
    else:
        available='NO'; truth='CAMPAIGN_SOURCE_MISSING'; score=''; narrative=''; method='NO_MATCH'; source='NO_CAMPAIGN_SOURCE_MATCH'; src={}
    row={'race_date':gr.get('race_date',''),'track':gr.get('track',''),'race_no':gr.get('race_no',''),'horse':gr.get('horse',''),'horse_key':gr.get('horse_key',''),'edgeiq_campaign_available_v1':available,'edgeiq_campaign_truth_status_v1':truth,'edgeiq_campaign_score_v1':score,'edgeiq_campaign_narrative_v1':narrative,'edgeiq_campaign_source_v1':source,'edgeiq_campaign_match_method_v1':method,'campaign_profile_band_v1':src.get('campaign_profile_band',''),'prep_stage_label_v1':src.get('prep_stage_label',''),'evidence_status_v1':src.get('evidence_status',''),'history_runs_used_v1':src.get('history_runs_used',''),'prep_stage_sample_count_v1':src.get('prep_stage_sample_count',''),'campaign_positive_flag_v1':src.get('campaign_positive_flag',''),'campaign_risk_flag_v1':src.get('campaign_risk_flag','')}
    rows.append(row)
    audit.append({'race_date':row['race_date'],'track':row['track'],'race_no':row['race_no'],'horse':row['horse'],'campaign_available':available,'truth_status':truth,'match_method':method})
byrace=defaultdict(list)
for r in rows: byrace[(clean(r['race_date']),clean(r['track']),race_no(r['race_no']))].append(r)
for rk, members in byrace.items():
    counts={'race_campaign_available_count_v1':str(sum(1 for x in members if x['edgeiq_campaign_available_v1']=='YES')),'race_campaign_true_zero_count_v1':str(sum(1 for x in members if x['edgeiq_campaign_truth_status_v1']=='TRUE_ZERO_NO_CAMPAIGN_HISTORY')),'race_campaign_source_missing_count_v1':str(sum(1 for x in members if x['edgeiq_campaign_truth_status_v1']=='CAMPAIGN_SOURCE_MISSING')),'race_campaign_fallback_match_count_v1':str(sum(1 for x in members if x['edgeiq_campaign_match_method_v1']=='HORSE_KEY_FALLBACK'))}
    for x in members: x.update(counts)
fields=list(rows[0].keys())
for f in ['race_campaign_available_count_v1','race_campaign_true_zero_count_v1','race_campaign_source_missing_count_v1','race_campaign_fallback_match_count_v1']:
    if f not in fields: fields.append(f)
status='CAMPAIGN_FEED_V1_BUILT' if len(rows)==383 and len(byrace)==25 else 'CAMPAIGN_FEED_V1_BLOCKED'
summary={'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'rows':len(rows),'races':len(byrace),'campaign_available_rows':sum(1 for r in rows if r['edgeiq_campaign_available_v1']=='YES'),'true_zero_rows':sum(1 for r in rows if r['edgeiq_campaign_truth_status_v1']=='TRUE_ZERO_NO_CAMPAIGN_HISTORY'),'source_missing_rows':sum(1 for r in rows if r['edgeiq_campaign_truth_status_v1']=='CAMPAIGN_SOURCE_MISSING'),'fallback_match_rows':sum(1 for r in rows if r['edgeiq_campaign_match_method_v1']=='HORSE_KEY_FALLBACK'),'pricing_math_changed':'NO','v6_1_changed':'NO','v7_2g2_changed':'NO'}
write_csv(OUT,rows,fields); write_csv(SUMMARY,[summary],list(summary.keys())); write_csv(AUDIT,audit,list(audit[0].keys()))
REPORT.write_text('\n'.join(['EDGEiQ Campaign Feed V1','='*26,f'Status: {status}',f'Rows/races: {len(rows)}/{len(byrace)}',f'Available/true-zero/source-missing/fallback: {summary["campaign_available_rows"]}/{summary["true_zero_rows"]}/{summary["source_missing_rows"]}/{summary["fallback_match_rows"]}','Pricing maths changed: NO','V6.1 changed: NO','V7.2G2 changed: NO'])+'\n',encoding='utf-8')
print(status)
