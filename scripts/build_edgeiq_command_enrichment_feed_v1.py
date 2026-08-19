import csv, re, math
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'
live=DATA/'edgeiq_live_runner_board_governed_v1.csv'; factor=DATA/'edgeiq_live_runner_factor_scorecard_v2.csv'; dna=DATA/'edgeiq_runner_dna_drawer_feed_v2.csv'; expl=DATA/'edgeiq_explainability_terminal_feed_v1_2.csv'
out=DATA/'edgeiq_command_enrichment_feed_v1.csv'; sumout=DATA/'edgeiq_command_enrichment_feed_v1_summary.csv'; auditout=DATA/'edgeiq_command_enrichment_feed_v1_audit.csv'; report=DATA/'edgeiq_command_enrichment_feed_v1_report.txt'
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
def first(row, keys, default=''):
    for k in keys:
        if k in row and str(row.get(k,'')).strip(): return str(row.get(k,'')).strip()
    return default
def num(row, keys):
    for k in keys:
        try:
            s=str(row.get(k,'')).replace('$','').replace('%','').replace(',','').strip()
            if s!='': return float(s)
        except Exception: pass
    return None
def clamp(v):
    if v is None or not math.isfinite(v): return ''
    return max(0,min(100,v))
def yes(v): return str(v).strip().upper() in {'YES','TRUE','1','Y'}
def key(row): return (norm(first(row,['race_date','meeting_date','current_race_date','date'])), norm(first(row,['track'])), rno(first(row,['race_no','race_number','race'])), norm(first(row,['horse','horse_name','runner_name','horse_key'])))
def idx(rows): return {key(r):r for r in rows}
def edge_pct(fair, livep):
    if fair and livep and fair>0: return ((livep/fair)-1)*100
    return None
live_cols, live_rows=read(live); factor_cols, factor_rows=read(factor); dna_cols, dna_rows=read(dna); expl_cols, expl_rows=read(expl)
idx_factor=idx(factor_rows); idx_dna=idx(dna_rows); idx_expl=idx(expl_rows)
rows=[]; audit=[]
for r in live_rows:
    k=key(r); fr=idx_factor.get(k,{}); dr=idx_dna.get(k,{}); er=idx_expl.get(k,{})
    fair=num(r,['edgeiq_v7_2g2_active_display_fair_price_shadow','edgeiq_v7_2g2_on_preview_display_fair_price','fair_price','ui_fair_price'])
    livep=num(r,['live_price','tab_price','market_price','price'])
    ep=edge_pct(fair, livep)
    scores={
      'score_overall': clamp(num(r,['total_rating_points','runner_score_v3','runner_score_v2','governed_projection_rating_v6','confidence_adjusted_rating_v6','strength_adjusted_rating_v6','projected_rating_v5_2','rating','rating_points'])),
      'score_distance': clamp(num(fr,['DISTANCE','distance_score','distance_fit_score']) or num(dr,['distance_fit_score','distance_profile_score'])),
      'score_condition': clamp(num(fr,['CONDITION','condition_score','condition_fit_score']) or num(dr,['condition_fit_score','condition_profile_score'])),
      'score_class': clamp(num(fr,['CLASS','class_score','class_fit_score']) or num(dr,['class_fit_score','class_profile_score'])),
      'score_campaign': clamp(num(fr,['CAMPAIGN','campaign_score','preparation_score']) or num(r,['campaign_score','campaign_risk_score'])),
      'score_pace': clamp(num(fr,['PACE','pace_score','race_shape_score']) or num(er,['pace_score','race_shape_score'])),
      'score_connections': clamp(num(fr,['CONNECTION','connections_score','connection_score']) or num(r,['connection_score'])),
      'score_market': clamp(num(fr,['MARKET','market_score','market_signal_score']) or (50+(ep/2) if ep is not None else None)),
      'score_confidence': clamp(num(r,['confidence','confidence_score','edgeiq_confidence','model_confidence']) or num(er,['confidence_score'])),
    }
    src=[]
    if any(v!='' for v in scores.values()): src.append('LIVE_BOARD_AND_AVAILABLE_FEEDS')
    for name,val in scores.items():
        if val=='': src.append(name+':MISSING')
    conn_av=yes(r.get('edgeiq_connection_evidence_available'))
    market_av=yes(r.get('edgeiq_market_evidence_available'))
    hidden_av=yes(r.get('edgeiq_hidden_gem_evidence_available'))
    if ep is not None:
        if ep>=15: market_role='BEST_VALUE_CANDIDATE'
        elif ep<=-15: market_role='OVERBET_RISK'
        elif abs(ep)>=7.5: market_role='MARKET_WATCH'
        else: market_role='NO_MARKET_SIGNAL' if not market_av else 'MARKET_WATCH'
    else:
        market_role='MARKET_WATCH' if market_av else 'NO_MARKET_SIGNAL'
    conn_role='CONNECTION_ANGLE' if conn_av else 'NO_CONNECTION_SIGNAL'
    review=[]
    if hidden_av: review.append('HIDDEN_GEM')
    if market_role in {'BEST_VALUE_CANDIDATE','OVERBET_RISK'}: review.append(market_role)
    if conn_av: review.append('CONNECTION')
    outrow={
      'race_date':first(r,['race_date','meeting_date','current_race_date','date']),'track':first(r,['track']),'race_no':first(r,['race_no']),'horse':first(r,['horse','horse_name','runner_name']),
      'edgeiq_active_display_fair_price': fair if fair is not None else '',
      'edgeiq_v7_2g2_guarded_display_fair_price': first(r,['edgeiq_v7_2g2_active_display_fair_price_shadow','edgeiq_v7_2g2_on_preview_display_fair_price']),
      'edgeiq_connection_evidence_available': first(r,['edgeiq_connection_evidence_available'],'NO'),
      'edgeiq_connection_angle_summary': first(r,['edgeiq_connection_angle_summary'],''),
      'edgeiq_market_evidence_available': first(r,['edgeiq_market_evidence_available'],'NO'),
      'edgeiq_market_signal_summary': first(r,['edgeiq_market_signal_summary'],''),
      'edgeiq_hidden_gem_evidence_available': first(r,['edgeiq_hidden_gem_evidence_available'],'NO'),
      'edgeiq_hidden_gem_summary': first(r,['edgeiq_hidden_gem_summary'],''),
      'edgeiq_score_breakdown_available': 'YES' if any(v!='' for v in scores.values()) else 'NO',
      **scores,
      'score_breakdown_source': '|'.join(src) if src else 'MISSING',
      'command_market_role': market_role,
      'command_connection_role': conn_role,
      'command_review_flag': '|'.join(review) if review else 'STANDARD_REVIEW'
    }
    rows.append(outrow)
    audit.append({'horse':outrow['horse'],'market_role':market_role,'connection_role':conn_role,'score_fields_loaded':sum(1 for v in scores.values() if v!=''),'missing_scores':'|'.join([k for k,v in scores.items() if v==''])})
races=len({(r['race_date'],r['track'],r['race_no']) for r in rows})
score_rows=sum(1 for r in rows if r['edgeiq_score_breakdown_available']=='YES')
missing_factor_rows=sum(1 for r in rows if 'MISSING' in r['score_breakdown_source'])
status='COMMAND_ENRICHMENT_FEED_BUILT' if missing_factor_rows==0 else 'COMMAND_ENRICHMENT_FEED_BUILT_WITH_MISSING_FACTORS'
summary=[{'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'rows':len(rows),'races':races,'market_evidence_rows':sum(1 for r in rows if yes(r['edgeiq_market_evidence_available'])),'connection_evidence_rows':sum(1 for r in rows if yes(r['edgeiq_connection_evidence_available'])),'hidden_gem_rows':sum(1 for r in rows if yes(r['edgeiq_hidden_gem_evidence_available'])),'score_breakdown_rows':score_rows,'market_command_rows':sum(1 for r in rows if r['command_market_role']!='NO_MARKET_SIGNAL'),'connection_command_rows':sum(1 for r in rows if r['command_connection_role']=='CONNECTION_ANGLE'),'rows_with_missing_factor_scores':missing_factor_rows}]
write(out,rows,list(rows[0].keys())); write(auditout,audit,list(audit[0].keys())); write(sumout,summary,list(summary[0].keys()))
report.write_text('\n'.join(['EDGEiQ Command Enrichment Feed V1','='*42,f'Status: {status}',f'Rows/races: {len(rows)} / {races}',f'Market/connection/hidden rows: {summary[0]["market_evidence_rows"]} / {summary[0]["connection_evidence_rows"]} / {summary[0]["hidden_gem_rows"]}',f'Score breakdown rows: {score_rows}',f'Market command rows: {summary[0]["market_command_rows"]}',f'Connection command rows: {summary[0]["connection_command_rows"]}',f'Rows with missing factor scores: {missing_factor_rows}'])+'\n', encoding='utf-8')
print(status); print('rows',len(rows),'races',races,'score',score_rows,'market',summary[0]['market_command_rows'],'conn',summary[0]['connection_command_rows'])
