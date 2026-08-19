import csv, re, math
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'
live=DATA/'edgeiq_live_runner_board_governed_v1.csv'; v1=DATA/'edgeiq_command_enrichment_feed_v1.csv'; factor=DATA/'edgeiq_live_runner_factor_scorecard_v2.csv'; dna=DATA/'edgeiq_runner_dna_drawer_feed_v2.csv'; expl=DATA/'edgeiq_explainability_terminal_feed_v1_2.csv'
out=DATA/'edgeiq_command_enrichment_feed_v2.csv'; sumout=DATA/'edgeiq_command_enrichment_feed_v2_summary.csv'; auditout=DATA/'edgeiq_command_enrichment_feed_v2_audit.csv'; report=DATA/'edgeiq_command_enrichment_feed_v2_report.txt'
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
        if k in row and str(row.get(k,'')).strip(): return str(row.get(k)).strip()
    return default
def num(row, keys, plausible=True):
    bad=['runner_no','runnerno','horse_no','barrier','bar','rank','saddlecloth','number','no']
    for k in keys:
        if plausible and any(b == k.lower() or b in k.lower() for b in bad): continue
        try:
            s=str(row.get(k,'')).replace('$','').replace('%','').replace(',','').strip()
            if s=='': continue
            v=float(s)
            if plausible and not (0 <= v <= 100): continue
            return v
        except Exception: pass
    return None
def anynum(*items):
    for row, keys in items:
        v=num(row, keys)
        if v is not None: return v
    return None
def clamp(v): return '' if v is None or not math.isfinite(v) else round(max(0,min(100,v)),4)
def yes(v): return str(v).strip().upper() in {'YES','TRUE','1','Y'}
def meaningful(v):
    s=str(v or '').strip(); u=s.upper()
    return bool(s) and u not in {'NO','NONE','N/A','NA','NO_SOURCE_MATCH','NO_CONNECTION','NO_EVIDENCE','FALSE','0','--','NO CONNECTION ANGLE TRIGGERED.','NO MARKET SIGNAL LOADED.','NO HIDDEN GEM FLAGGED.'}
def key(row): return (norm(first(row,['race_date','meeting_date','current_race_date','date'])), norm(first(row,['track'])), rno(first(row,['race_no','race_number','race'])), norm(first(row,['horse','horse_name','runner_name','horse_key'])))
def racekey(row): return key(row)[:3]
def idx(rows): return {key(r):r for r in rows}
def edge_pct(fair, livep): return ((livep/fair)-1)*100 if fair and livep and fair>0 else None
live_cols, live_rows=read(live); v1_cols,v1_rows=read(v1); factor_cols,factor_rows=read(factor); dna_cols,dna_rows=read(dna); expl_cols,expl_rows=read(expl)
idx_v1=idx(v1_rows); idx_factor=idx(factor_rows); idx_dna=idx(dna_rows); idx_expl=idx(expl_rows)
rows=[]; audit=[]
for r in live_rows:
    k=key(r); vr=idx_v1.get(k,{}); fr=idx_factor.get(k,{}); dr=idx_dna.get(k,{}); er=idx_expl.get(k,{})
    conn_summary=first(r,['edgeiq_connection_angle_summary']) or first(vr,['edgeiq_connection_angle_summary'])
    market_summary=first(r,['edgeiq_market_signal_summary']) or first(vr,['edgeiq_market_signal_summary'])
    hidden_summary=first(r,['edgeiq_hidden_gem_summary']) or first(vr,['edgeiq_hidden_gem_summary'])
    fair=num(r,['edgeiq_v7_2g2_active_display_fair_price_shadow','edgeiq_v7_2g2_on_preview_display_fair_price','fair_price','ui_fair_price'], plausible=False)
    livep=num(r,['live_price','tab_price','market_price','price'], plausible=False)
    ep=edge_pct(fair, livep)
    market_role=first(vr,['command_market_role'])
    conn_av=yes(r.get('edgeiq_connection_evidence_available')) or meaningful(conn_summary)
    market_av=yes(r.get('edgeiq_market_evidence_available')) or meaningful(market_summary) or ep is not None or meaningful(market_role)
    hidden_av=yes(r.get('edgeiq_hidden_gem_evidence_available')) or meaningful(hidden_summary)
    overall=anynum((r,['total_rating_points','current_rating','rating','projected_rating_v5_2','governed_projection_rating_v6','confidence_adjusted_rating_v6','strength_adjusted_rating_v6']),(vr,['score_overall']))
    distance=anynum((vr,['score_distance']),(fr,['distance_score','distance_fit_score','DISTANCE']),(dr,['distance_fit_score','distance_profile_score']))
    condition=anynum((vr,['score_condition']),(fr,['condition_score','condition_fit_score','CONDITION']),(dr,['condition_fit_score','condition_profile_score']))
    klass=anynum((vr,['score_class']),(fr,['class_score','class_fit_score','CLASS']),(dr,['class_fit_score','class_profile_score']))
    campaign=anynum((vr,['score_campaign']),(fr,['campaign_score','preparation_score','CAMPAIGN']),(r,['campaign_score','preparation_score']),(er,['campaign_score']))
    pace=anynum((vr,['score_pace']),(fr,['pace_score','race_shape_score','PACE']),(er,['pace_score','race_shape_score']))
    connections=anynum((vr,['score_connections']),(fr,['connection_score','connections_score','CONNECTION']),(r,['connection_score']))
    conn_source='NUMERIC'
    if connections is None and conn_av:
        connections=50; conn_source='EVIDENCE_AVAILABLE_BASELINE'
    market=anynum((vr,['score_market']),(fr,['market_score','MARKET']),(r,['market_score']))
    market_source='NUMERIC'
    if market is None and ep is not None:
        market=max(0,min(100,50+(ep/2))); market_source='MARKET_EDGE_DERIVED'
    confidence=anynum((vr,['score_confidence']),(r,['confidence_score','edgeiq_confidence','model_confidence','confidence']),(er,['confidence_score']))
    source_bits=[]
    for name,val,src in [('OVERALL',overall,'NUMERIC'),('DISTANCE',distance,'NUMERIC'),('CONDITION',condition,'NUMERIC'),('CLASS',klass,'NUMERIC'),('CAMPAIGN',campaign,'NUMERIC'),('PACE',pace,'NUMERIC'),('CONNECTIONS',connections,conn_source),('MARKET',market,market_source),('CONFIDENCE',confidence,'NUMERIC')]:
        source_bits.append(f'{name}:{src if val is not None else "MISSING"}')
    outrow={
      'race_date':first(r,['race_date','meeting_date','current_race_date','date']),'track':first(r,['track']),'race_no':first(r,['race_no']),'horse':first(r,['horse','horse_name','runner_name']),
      'edgeiq_active_display_fair_price': fair if fair is not None else '',
      'edgeiq_v7_2g2_guarded_display_fair_price': first(r,['edgeiq_v7_2g2_active_display_fair_price_shadow','edgeiq_v7_2g2_on_preview_display_fair_price']),
      'edgeiq_connection_evidence_available_v2':'YES' if conn_av else 'NO','edgeiq_connection_angle_summary_v2':conn_summary,
      'edgeiq_market_evidence_available_v2':'YES' if market_av else 'NO','edgeiq_market_signal_summary_v2':market_summary,
      'edgeiq_hidden_gem_evidence_available_v2':'YES' if hidden_av else 'NO','edgeiq_hidden_gem_summary_v2':hidden_summary,
      'edgeiq_score_overall_v2':clamp(overall),'edgeiq_score_distance_v2':clamp(distance),'edgeiq_score_condition_v2':clamp(condition),'edgeiq_score_class_v2':clamp(klass),'edgeiq_score_campaign_v2':clamp(campaign),'edgeiq_score_pace_v2':clamp(pace),'edgeiq_score_connections_v2':clamp(connections),'edgeiq_score_market_v2':clamp(market),'edgeiq_score_confidence_v2':clamp(confidence),'edgeiq_score_source_v2':'|'.join(source_bits),
      'command_market_role_v2': market_role if meaningful(market_role) else ('MARKET_WATCH' if market_av else 'NO_MARKET_SIGNAL'),
      'command_connection_role_v2': 'CONNECTION_ANGLE' if conn_av else 'NO_CONNECTION_SIGNAL',
      'command_review_flag_v2': '|'.join([x for x,y in [('CONNECTION',conn_av),('MARKET',market_av),('HIDDEN_GEM',hidden_av)] if y]) or 'STANDARD_REVIEW'
    }
    rows.append(outrow)
# race aggregates
agg={}
for r in rows:
    rk=(r['race_date'],r['track'],r['race_no']); agg.setdefault(rk,[]).append(r)
for r in rows:
    group=agg[(r['race_date'],r['track'],r['race_no'])]
    r['race_field_size_v2']=len(group)
    r['race_connection_count_v2']=sum(1 for x in group if x['edgeiq_connection_evidence_available_v2']=='YES')
    r['race_market_count_v2']=sum(1 for x in group if x['edgeiq_market_evidence_available_v2']=='YES')
    r['race_hidden_gem_count_v2']=sum(1 for x in group if x['edgeiq_hidden_gem_evidence_available_v2']=='YES')
    r['race_score_breakdown_count_v2']=sum(1 for x in group if any(str(x.get(f,'')).strip() for f in ['edgeiq_score_overall_v2','edgeiq_score_distance_v2','edgeiq_score_condition_v2','edgeiq_score_class_v2','edgeiq_score_campaign_v2','edgeiq_score_pace_v2','edgeiq_score_connections_v2','edgeiq_score_market_v2','edgeiq_score_confidence_v2']))
    audit.append({'horse':r['horse'],'race_key':'|'.join([r['race_date'],r['track'],r['race_no']]),'conn':r['edgeiq_connection_evidence_available_v2'],'market':r['edgeiq_market_evidence_available_v2'],'hidden':r['edgeiq_hidden_gem_evidence_available_v2'],'overall':r['edgeiq_score_overall_v2'],'source':r['edgeiq_score_source_v2']})
races=len(agg); missing=sum(1 for r in rows if 'MISSING' in r['edgeiq_score_source_v2'])
status='COMMAND_ENRICHMENT_FEED_V2_BUILT' if missing==0 else 'COMMAND_ENRICHMENT_FEED_V2_BUILT_WITH_MISSING_FACTORS'
summary=[{'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'rows':len(rows),'races':races,'connection_evidence_rows':sum(1 for r in rows if r['edgeiq_connection_evidence_available_v2']=='YES'),'market_evidence_rows':sum(1 for r in rows if r['edgeiq_market_evidence_available_v2']=='YES'),'hidden_gem_rows':sum(1 for r in rows if r['edgeiq_hidden_gem_evidence_available_v2']=='YES'),'score_overall_rows':sum(1 for r in rows if str(r['edgeiq_score_overall_v2']).strip()),'distance_score_rows':sum(1 for r in rows if str(r['edgeiq_score_distance_v2']).strip()),'condition_score_rows':sum(1 for r in rows if str(r['edgeiq_score_condition_v2']).strip()),'class_score_rows':sum(1 for r in rows if str(r['edgeiq_score_class_v2']).strip()),'campaign_score_rows':sum(1 for r in rows if str(r['edgeiq_score_campaign_v2']).strip()),'pace_score_rows':sum(1 for r in rows if str(r['edgeiq_score_pace_v2']).strip()),'connection_score_rows':sum(1 for r in rows if str(r['edgeiq_score_connections_v2']).strip()),'market_score_rows':sum(1 for r in rows if str(r['edgeiq_score_market_v2']).strip()),'confidence_score_rows':sum(1 for r in rows if str(r['edgeiq_score_confidence_v2']).strip()),'rows_with_missing_factor_scores':missing}]
write(out,rows,list(rows[0].keys())); write(auditout,audit,list(audit[0].keys())); write(sumout,summary,list(summary[0].keys()))
report.write_text('\n'.join(['EDGEiQ Command Enrichment Feed V2','='*42,f'Status: {status}',f'Rows/races: {len(rows)} / {races}',f'Connection/market/hidden: {summary[0]["connection_evidence_rows"]} / {summary[0]["market_evidence_rows"]} / {summary[0]["hidden_gem_rows"]}',f'Overall score rows: {summary[0]["score_overall_rows"]}',f'Distance/condition/class/campaign/pace: {summary[0]["distance_score_rows"]} / {summary[0]["condition_score_rows"]} / {summary[0]["class_score_rows"]} / {summary[0]["campaign_score_rows"]} / {summary[0]["pace_score_rows"]}',f'Connections/market/confidence scores: {summary[0]["connection_score_rows"]} / {summary[0]["market_score_rows"]} / {summary[0]["confidence_score_rows"]}',f'Rows with missing factor scores: {missing}'])+'\n', encoding='utf-8')
print(status); print('rows',len(rows),'races',races,'conn',summary[0]['connection_evidence_rows'],'market',summary[0]['market_evidence_rows'],'hidden',summary[0]['hidden_gem_rows'],'overall',summary[0]['score_overall_rows'])
