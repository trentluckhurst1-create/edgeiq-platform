import csv, re, math
from pathlib import Path
from datetime import datetime
DATA=Path('public/data')
REC=DATA/'edgeiq_live_runner_board_governed_v1_RECOVERY_CANDIDATE.csv'
ENR=DATA/'edgeiq_command_enrichment_feed_v2_RECOVERY_CANDIDATE.csv'
EVID=DATA/'edgeiq_current_intelligence_evidence_fix_candidate_v1_RECOVERY_CANDIDATE.csv'
SHAPE=DATA/'edgeiq_current_race_shape_recovery_candidate_v1_RECOVERY_CANDIDATE.csv'
REPORT=DATA/'edgeiq_governed_board_recovery_end_to_end_report.txt'
def read(path):
    with path.open('r',newline='',encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return r.fieldnames or [], list(r)
def write(path,rows,fields=None):
    if fields is None: fields=list(rows[0].keys())
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',lineterminator='\n'); w.writeheader(); w.writerows(rows)
def rno(v):
    m=re.search(r'\d+',str(v or '')); return m.group(0) if m else str(v or '').strip()
def norm(s): return re.sub(r'[^a-z0-9]+','',str(s or '').lower())
def first(r,keys):
    for k in keys:
        if k in r and str(r.get(k,'')).strip(): return str(r.get(k)).strip()
    return ''
def key(r): return (first(r,['race_date','meeting_date']),first(r,['track']),rno(first(r,['race_no'])),norm(first(r,['horse','horse_key','horse_name'])))
def racekey(r): return key(r)[:3]
def yes(v): return str(v).strip().upper() in {'YES','TRUE','1','Y'}
def num(v):
    try:
        s=str(v).replace('$','').replace('%','').replace(',','').strip(); return float(s) if s!='' else None
    except Exception: return None
def meaningful(v):
    s=str(v or '').strip().upper(); return bool(s) and s not in {'NO','NONE','N/A','NA','NO_SOURCE_MATCH','NO_CONNECTION','NO_EVIDENCE','FALSE','0','--'}
def style(r):
    s=' '.join([first(r,['recovered_speed_map_bucket_v1','dominant_run_style','run_style','settling_band','speed_map_bucket','map_style'])]).upper().replace(' ','_')
    if 'LEADER' in s: return 'LEADER'
    if 'ON_PACE' in s or 'ONPACE' in s or 'PROMINENT' in s: return 'ON_PACE'
    if 'MID' in s: return 'MIDFIELD'
    if 'BACK' in s or 'CLOSER' in s: return 'BACKMARKER'
    return 'UNKNOWN'
cols,rows=read(REC)
# Evidence candidate: retain already merged rows, mark appended missing rows honestly.
efields=list(cols)
for c in ['edgeiq_connection_evidence_available','edgeiq_connection_angle_summary','edgeiq_market_evidence_available','edgeiq_market_signal_summary','edgeiq_hidden_gem_evidence_available','edgeiq_hidden_gem_summary','edgeiq_evidence_fix_source','edgeiq_evidence_fix_status']:
    if c not in efields: efields.append(c)
evid=[]
for r in rows:
    rr=dict(r)
    if not meaningful(rr.get('edgeiq_evidence_fix_status')):
        rr['edgeiq_connection_evidence_available']='NO'; rr['edgeiq_market_evidence_available']='NO'; rr['edgeiq_hidden_gem_evidence_available']='NO'; rr['edgeiq_evidence_fix_source']='NO_SOURCE_MATCH_RECOVERY_CANDIDATE'; rr['edgeiq_evidence_fix_status']='NO_SOURCE_MATCH'
    evid.append(rr)
write(EVID,evid,efields)
# Enrichment recovery feed.
enr=[]
for r in rows:
    fair=num(r.get('edgeiq_v7_2g2_active_display_fair_price_shadow')) or num(r.get('fair_price')) or num(r.get('ui_fair_price'))
    livep=num(r.get('live_price'))
    edge=((livep/fair)-1)*100 if fair and livep else num(r.get('edge_pct'))
    market_av=yes(r.get('edgeiq_market_evidence_available')) or meaningful(r.get('edgeiq_market_signal_summary')) or fair is not None
    conn_av=yes(r.get('edgeiq_connection_evidence_available')) or meaningful(r.get('edgeiq_connection_angle_summary'))
    hidden_av=yes(r.get('edgeiq_hidden_gem_evidence_available')) or meaningful(r.get('edgeiq_hidden_gem_summary'))
    overall=num(r.get('total_rating_points')) or num(r.get('projected_rating_v5_2')) or num(r.get('governed_projection_rating_v6'))
    market_score=max(0,min(100,50+(edge/2))) if edge is not None else ''
    conn_score=50 if conn_av else ''
    enr.append({'race_date':first(r,['race_date','meeting_date']),'track':first(r,['track']),'race_no':first(r,['race_no']),'horse':first(r,['horse']),'edgeiq_active_display_fair_price':fair or '','edgeiq_v7_2g2_guarded_display_fair_price':r.get('edgeiq_v7_2g2_active_display_fair_price_shadow',''),'edgeiq_connection_evidence_available_v2':'YES' if conn_av else 'NO','edgeiq_connection_angle_summary_v2':r.get('edgeiq_connection_angle_summary',''),'edgeiq_market_evidence_available_v2':'YES' if market_av else 'NO','edgeiq_market_signal_summary_v2':r.get('edgeiq_market_signal_summary','') or ('Market reference available.' if market_av else ''),'edgeiq_hidden_gem_evidence_available_v2':'YES' if hidden_av else 'NO','edgeiq_hidden_gem_summary_v2':r.get('edgeiq_hidden_gem_summary',''),'edgeiq_score_overall_v2':overall or '','edgeiq_score_connections_v2':conn_score,'edgeiq_score_market_v2':market_score,'edgeiq_score_source_v2':'RECOVERY_CANDIDATE_MINIMAL','command_market_role_v2':'MARKET_WATCH' if market_av else 'NO_MARKET_SIGNAL','command_connection_role_v2':'CONNECTION_ANGLE' if conn_av else 'NO_CONNECTION_SIGNAL','command_review_flag_v2':'RECOVERY_CANDIDATE'})
# race aggregate counts
agg={}
for r in enr: agg.setdefault((r['race_date'],r['track'],r['race_no']),[]).append(r)
for r in enr:
    g=agg[(r['race_date'],r['track'],r['race_no'])]
    r['race_field_size_v2']=len(g); r['race_connection_count_v2']=sum(1 for x in g if x['edgeiq_connection_evidence_available_v2']=='YES'); r['race_market_count_v2']=sum(1 for x in g if x['edgeiq_market_evidence_available_v2']=='YES'); r['race_hidden_gem_count_v2']=sum(1 for x in g if x['edgeiq_hidden_gem_evidence_available_v2']=='YES'); r['race_score_breakdown_count_v2']=sum(1 for x in g if str(x.get('edgeiq_score_overall_v2','')).strip())
write(ENR,enr)
# Shape candidate across recovery board, using any recovered bucket if present otherwise UNKNOWN.
shape=[]
for r in rows:
    b=style(r)
    shape.append({'race_date':first(r,['race_date','meeting_date']),'track':first(r,['track']),'race_no':first(r,['race_no']),'horse':first(r,['horse']),'recovered_speed_map_bucket_v1':b,'race_shape_recovery_source_v1':r.get('race_shape_recovery_source_v1','RECOVERY_CANDIDATE_UNKNOWN' if b=='UNKNOWN' else 'RECOVERY_CANDIDATE_EXISTING'),'race_shape_recovery_status_v1':'RECOVERED' if b!='UNKNOWN' else 'UNKNOWN'})
write(SHAPE,shape)
# Summary report
caul=[r for r in enr if r['race_date']=='2026-06-27' and r['track'].upper()=='CAULFIELD' and r['race_no']=='7']
caul_shape=[r for r in shape if r['race_date']=='2026-06-27' and r['track'].upper()=='CAULFIELD' and r['race_no']=='7']
status='END_TO_END_RECOVERY_READY_FOR_REVIEW'
report=['EDGEiQ Governed Board Recovery End-to-End Report','='*58,f'Final status: {status}',f'Generated: {datetime.now().isoformat(timespec="seconds")}',f'Recovery candidate rows: {len(rows)}',f'Recovery candidate races: {len(set(racekey(r) for r in rows))}',f'Command enrichment recovery rows: {len(enr)}',f'Evidence recovery rows: {len(evid)}',f'Race shape recovery rows: {len(shape)}','', 'Caulfield R7 recovery candidate:',f'- Rows: {len(caul)}',f'- Market available: {sum(1 for r in caul if r["edgeiq_market_evidence_available_v2"]=="YES")}',f'- Connections available: {sum(1 for r in caul if r["edgeiq_connection_evidence_available_v2"]=="YES")}',f'- Hidden Gem available: {sum(1 for r in caul if r["edgeiq_hidden_gem_evidence_available_v2"]=="YES")}',f'- Shape mapped: {sum(1 for r in caul_shape if r["recovered_speed_map_bucket_v1"]!="UNKNOWN")}/{len(caul_shape)}','', 'Controls:', '- Candidate only.', '- No production overwrite.', '- No live wiring changes.', '- No UI changes.']
REPORT.write_text('\n'.join(report)+'\n',encoding='utf-8')
print(status); print('caulfield_rows',len(caul),'market',sum(1 for r in caul if r['edgeiq_market_evidence_available_v2']=='YES'),'shape_mapped',sum(1 for r in caul_shape if r['recovered_speed_map_bucket_v1']!='UNKNOWN'))
