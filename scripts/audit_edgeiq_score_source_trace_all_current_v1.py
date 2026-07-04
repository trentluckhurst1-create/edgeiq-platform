import csv, json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
GOV = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
CMD = DATA / 'edgeiq_command_enrichment_feed_v2.csv'
FACTOR = DATA / 'edgeiq_live_runner_factor_scorecard_v2.csv'
DNA = DATA / 'edgeiq_runner_dna_drawer_feed_v2.csv'
EXPLAIN = DATA / 'edgeiq_explainability_terminal_feed_v1_2.csv'
LIVE_TERM = DATA / 'edgeiq_live_terminal_feed_v1.csv'
CONN_TRACE = DATA / 'edgeiq_connection_source_trace_all_current_v1.csv'
OUT = DATA / 'edgeiq_score_source_trace_all_current_v1.csv'
SUMMARY = DATA / 'edgeiq_score_source_trace_all_current_v1_summary.csv'
REPORT = DATA / 'edgeiq_score_source_trace_all_current_v1_report.txt'

def read_csv(path):
    if not path.exists(): return [], []
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return list(r), list(r.fieldnames or [])

def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)

def clean(v): return ' '.join(str(v or '').strip().upper().replace('\u00a0',' ').split())
def clean_horse(v): return ''.join(ch for ch in clean(v) if ch.isalnum())
def race_no(v):
    s=clean(v).replace('RACE ','').replace('R','')
    return s.lstrip('0') or s
def key(r): return (clean(r.get('race_date') or r.get('current_race_date') or r.get('_date')), clean(r.get('track') or r.get('_track')), race_no(r.get('race_no') or r.get('_race')), clean_horse(r.get('horse') or r.get('horse_key') or r.get('_horse')))
def race_key(r): return key(r)[:3]
def to_float(v):
    try:
        s=str(v or '').strip().replace('%','').replace('$','').replace(',','')
        if not s: return None
        return float(s)
    except Exception: return None
def fmt(v):
    n=to_float(v)
    if n is None: return ''
    if abs(n-round(n))<0.000001: return str(int(round(n)))
    return f'{n:.2f}'.rstrip('0').rstrip('.')
def candidate_text(pairs):
    return '|'.join(f'{k}={v}' for k,v in pairs if str(v or '').strip()!='')
def valid_factor(fr):
    if not fr: return False
    if str(fr.get('factor_score','')).strip()=='': return False
    if clean(fr.get('factor_band')) == 'NO_SCORE': return False
    return True
def factor_score(fmap, names):
    for n in names:
        fr=fmap.get(n)
        if valid_factor(fr): return fmt(fr.get('factor_score')), f'FACTOR_SCORECARD_V2:{n}', fr.get('factor_explanation','')
    return '', '', ''
def first_score(row, cols):
    for c in cols:
        if c in row:
            n=to_float(row.get(c))
            if n is not None: return fmt(n), c
    return '', ''
def band_allows(row, band_cols):
    return not any(clean(row.get(c)) in {'NO_PROFILE','NO_SCORE','UNKNOWN'} for c in band_cols if c in row)

gov,_=read_csv(GOV); cmd,_=read_csv(CMD); factor,_=read_csv(FACTOR); dna,_=read_csv(DNA); explain,_=read_csv(EXPLAIN); live_term,_=read_csv(LIVE_TERM); conn,_=read_csv(CONN_TRACE)
cmd_by={key(r):r for r in cmd}; dna_by={key(r):r for r in dna}; explain_by={key(r):r for r in explain}; live_by={key(r):r for r in live_term}; conn_by={key(r):r for r in conn}
factors=defaultdict(dict)
for fr in factor: factors[key(fr)][clean(fr.get('factor'))]=fr
rows=[]
for r in gov:
    k=key(r); fmap=factors.get(k,{}); d=dna_by.get(k,{}); e=explain_by.get(k,{}); lt=live_by.get(k,{}); ct=conn_by.get(k,{}); c2=cmd_by.get(k,{})
    candidates={}
    # Overall: never runner_no/barrier/rank.
    overall, overall_src = first_score(r, ['total_rating_points','runner_score_v3','runner_score_v2','governed_projection_rating_v6','confidence_adjusted_rating_v6','strength_adjusted_rating_v6','projected_rating_v5_2','projected_rating_V6_1_RESEARCH','runner_dna_v6_2_score','win_pct'])
    if not overall:
        overall, overall_src = first_score(d, ['dna_v6_2_score','dna_score','runner_dna_v6_1_score'])
    if not overall:
        overall, overall_src = factor_score(fmap, ['RATING'])[:2]
    candidates['overall'] = candidate_text([(c,r.get(c,'')) for c in ['total_rating_points','runner_score_v3','runner_score_v2','governed_projection_rating_v6','confidence_adjusted_rating_v6','strength_adjusted_rating_v6','projected_rating_v5_2','projected_rating_V6_1_RESEARCH','runner_dna_v6_2_score','win_pct']] + [('dna_v6_2_score',d.get('dna_v6_2_score',''))])
    dist, dist_src, _ = factor_score(fmap, ['DISTANCE'])
    if not dist and band_allows(d, ['distance_fit_band']): dist, dist_src = first_score(d, ['distance_fit_score'])
    cond, cond_src, _ = factor_score(fmap, ['CONDITION','TRACK'])
    if not cond and band_allows(d, ['condition_fit_band']): cond, cond_src = first_score(d, ['condition_fit_score'])
    cls, cls_src, _ = factor_score(fmap, ['CLASS'])
    if not cls and band_allows(d, ['class_fit_band']): cls, cls_src = first_score(d, ['class_fit_score'])
    camp, camp_src, _ = factor_score(fmap, ['CAMPAIGN','PROFILE','FORM'])
    if not camp: camp, camp_src = first_score(lt, ['rating_trend_delta','profile_confidence_score'])
    pace, pace_src, _ = factor_score(fmap, ['PACE','SPEED'])
    if not pace: pace, pace_src = first_score(r, ['early_speed_rating'])
    conn_score = fmt(ct.get('connection_score')) or ''
    conn_src = 'CONNECTION_TRACE_ALL_CURRENT_V1' if conn_score else ''
    if not conn_score:
        vals=[]
        for n in ['TRAINER','JOCKEY','COMBO']:
            sc=factor_score(fmap,[n])[0]
            if sc!='': vals.append(to_float(sc))
        if vals:
            conn_score=fmt(sum(vals)/len(vals)); conn_src='FACTOR_SCORECARD_V2:TRAINER_JOCKEY_COMBO_AVG'
    market, market_src = '', ''
    edge = to_float(r.get('display_edge_pct') or r.get('ui_edge_pct') or r.get('edge_pct'))
    if edge is not None:
        market = fmt(max(0,min(100,50+edge)))
        market_src='GOVERNED_BOARD_EDGE_TO_MARKET_SCORE'
    elif str(r.get('edgeiq_market_evidence_available','')).strip():
        market='50'; market_src='GOVERNED_BOARD_MARKET_CONTEXT_BASELINE'
    conf, conf_src = first_score(e, ['final_confidence_score','projection_confidence_score','profile_confidence_score','market_confidence_score','data_quality_score'])
    if not conf: conf, conf_src = first_score(lt, ['final_confidence_score','projection_confidence_score','profile_confidence_score','market_confidence_score','data_quality_score'])
    chosen=[('overall',overall,overall_src),('distance',dist,dist_src),('condition',cond,cond_src),('class',cls,cls_src),('campaign',camp,camp_src),('pace',pace,pace_src),('connections',conn_score,conn_src),('market',market,market_src),('confidence',conf,conf_src)]
    missing=[name for name,val,src in chosen if val=='']
    rows.append({
        'race_date': r.get('race_date',''), 'track': r.get('track',''), 'race_no': r.get('race_no',''), 'horse': r.get('horse',''),
        'overall_candidate_fields': candidates['overall'],
        'distance_candidate_fields': candidate_text([('factor_DISTANCE', fmap.get('DISTANCE',{}).get('factor_score','')),('dna_distance_fit_score',d.get('distance_fit_score','')),('dna_distance_fit_band',d.get('distance_fit_band',''))]),
        'condition_candidate_fields': candidate_text([('factor_CONDITION', fmap.get('CONDITION',{}).get('factor_score','')),('dna_condition_fit_score',d.get('condition_fit_score','')),('dna_condition_fit_band',d.get('condition_fit_band',''))]),
        'class_candidate_fields': candidate_text([('factor_CLASS', fmap.get('CLASS',{}).get('factor_score','')),('dna_class_fit_score',d.get('class_fit_score','')),('dna_class_fit_band',d.get('class_fit_band',''))]),
        'campaign_candidate_fields': candidate_text([('factor_CAMPAIGN', fmap.get('CAMPAIGN',{}).get('factor_score','')),('factor_PROFILE', fmap.get('PROFILE',{}).get('factor_score','')),('rating_trend_delta',lt.get('rating_trend_delta',''))]),
        'pace_candidate_fields': candidate_text([('factor_PACE', fmap.get('PACE',{}).get('factor_score','')),('early_speed_rating',r.get('early_speed_rating','')),('early_speed_band',r.get('early_speed_band',''))]),
        'connection_candidate_fields': candidate_text([('trace_connection_score',ct.get('connection_score','')),('trainer_score',ct.get('trainer_score','')),('jockey_score',ct.get('jockey_score','')),('combo_score',ct.get('combo_score',''))]),
        'market_candidate_fields': candidate_text([('display_edge_pct',r.get('display_edge_pct','')),('edge_pct',r.get('edge_pct','')),('market_evidence',r.get('edgeiq_market_evidence_available',''))]),
        'confidence_candidate_fields': candidate_text([('explain_final_confidence_score',e.get('final_confidence_score','')),('terminal_final_confidence_score',lt.get('final_confidence_score',''))]),
        'chosen_overall_source': overall_src or 'MISSING', 'chosen_overall_score': overall,
        'chosen_distance_source': dist_src or 'MISSING', 'chosen_distance_score': dist,
        'chosen_condition_source': cond_src or 'MISSING', 'chosen_condition_score': cond,
        'chosen_class_source': cls_src or 'MISSING', 'chosen_class_score': cls,
        'chosen_campaign_source': camp_src or 'MISSING', 'chosen_campaign_score': camp,
        'chosen_pace_source': pace_src or 'MISSING', 'chosen_pace_score': pace,
        'chosen_connection_source': conn_src or 'MISSING', 'chosen_connection_score': conn_score,
        'chosen_market_source': market_src or 'MISSING', 'chosen_market_score': market,
        'chosen_confidence_source': conf_src or 'MISSING', 'chosen_confidence_score': conf,
        'missing_reason': 'ALL_CORE_SCORES_PRESENT' if not missing else 'MISSING_' + '|'.join(missing).upper(),
    })

races=set(race_key(r) for r in gov)
score_fields=['chosen_overall_score','chosen_distance_score','chosen_condition_score','chosen_class_score','chosen_campaign_score','chosen_pace_score','chosen_connection_score','chosen_market_score','chosen_confidence_score']
counts={f:sum(1 for r in rows if r[f]!='') for f in score_fields}
caulfield=[r for r in rows if clean(r['track'])=='CAULFIELD' and r['race_no']=='7']
status='SCORE_TRACE_COMPLETE'
if counts['chosen_overall_score'] < len(rows) or counts['chosen_connection_score'] < len(rows) or counts['chosen_pace_score'] < len(rows): status='SCORE_MAPPING_FAILURE_FOUND'
if sum(counts.values())==0: status='SCORE_SOURCES_MISSING'
summary={'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'rows':len(rows),'races':len(races), **counts,
         'caulfield_r7_rows':len(caulfield),'caulfield_r7_overall_count':sum(1 for r in caulfield if r['chosen_overall_score']!=''),'caulfield_r7_distance_count':sum(1 for r in caulfield if r['chosen_distance_score']!=''),'caulfield_r7_condition_count':sum(1 for r in caulfield if r['chosen_condition_score']!=''),'caulfield_r7_connection_count':sum(1 for r in caulfield if r['chosen_connection_score']!='')}
write_csv(OUT, rows, list(rows[0].keys()) if rows else ['status'])
write_csv(SUMMARY, [summary], list(summary.keys()))
REPORT.write_text('\n'.join(['EDGEiQ Score Source Trace All Current V1','='*44,f'Status: {status}',f'Rows/races: {len(rows)}/{len(races)}'] + [f'{k}: {v}' for k,v in counts.items()] + [f'CAULFIELD R7 rows/overall/distance/condition/connection: {summary["caulfield_r7_rows"]}/{summary["caulfield_r7_overall_count"]}/{summary["caulfield_r7_distance_count"]}/{summary["caulfield_r7_condition_count"]}/{summary["caulfield_r7_connection_count"]}'])+'\n',encoding='utf-8')
print(status)
