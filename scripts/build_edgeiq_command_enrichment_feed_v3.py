import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
GOV=DATA/'edgeiq_live_runner_board_governed_v1.csv'
CONN=DATA/'edgeiq_connection_source_trace_all_current_v1.csv'
SCORE=DATA/'edgeiq_score_source_trace_all_current_v1.csv'
V2=DATA/'edgeiq_command_enrichment_feed_v2.csv'
OUT=DATA/'edgeiq_command_enrichment_feed_v3.csv'
SUMMARY=DATA/'edgeiq_command_enrichment_feed_v3_summary.csv'
AUDIT=DATA/'edgeiq_command_enrichment_feed_v3_audit.csv'
REPORT=DATA/'edgeiq_command_enrichment_feed_v3_report.txt'
EXPECTED_ROWS=383; EXPECTED_RACES=25

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
def key(r): return (clean(r.get('race_date') or r.get('current_race_date')), clean(r.get('track')), race_no(r.get('race_no')), clean_horse(r.get('horse') or r.get('horse_key')))
def rkey(r): return key(r)[:3]
def to_float(v):
    try:
        s=str(v or '').strip().replace('$','').replace('%','').replace(',','')
        if not s or s=='-': return None
        return float(s)
    except Exception: return None
def fmt(v):
    n=to_float(v)
    if n is None: return ''
    if abs(n-round(n))<0.000001: return str(int(round(n)))
    return f'{n:.2f}'.rstrip('0').rstrip('.')
def yes(v): return clean(v) in {'YES','TRUE','1','Y','ON'}
def first(row, cols):
    for c in cols:
        if str(row.get(c,'')).strip(): return row.get(c,'')
    return ''
def price_pair(row):
    live=to_float(first(row,['display_live_price','live_price','tab_fixed_win']))
    fair=to_float(first(row,['edgeiq_active_display_fair_price_shadow','edgeiq_v7_2g2_guarded_display_fair_price','display_fair_price','ui_fair_price','fair_price']))
    return live, fair
def edge_value(row):
    e=to_float(first(row,['display_edge_pct','ui_edge_pct','edge_pct']))
    if e is not None: return e
    live,fair=price_pair(row)
    if live and fair and fair>0: return (live/fair-1)*100
    return None

gov,_=read_csv(GOV); conn,_=read_csv(CONN); score,_=read_csv(SCORE); v2,_=read_csv(V2)
conn_by={key(r):r for r in conn}; score_by={key(r):r for r in score}; v2_by={key(r):r for r in v2}
byrace=defaultdict(list)
for r in gov: byrace[rkey(r)].append(r)
market_role_by_key={}
race_market_commands={}
for rk, rows in byrace.items():
    entries=[]
    for r in rows:
        e=edge_value(r); live,fair=price_pair(r)
        entries.append({'key':key(r),'horse':r.get('horse',''),'edge':e,'live':live,'fair':fair,'market_context':r.get('edgeiq_market_signal_summary','') or 'Market price context loaded.'})
    value=[x for x in entries if x['edge'] is not None and x['edge']>0]
    risk=[x for x in entries if x['edge'] is not None and x['edge']<0]
    best=max(value,key=lambda x:x['edge']) if value else None
    over=min(risk,key=lambda x:x['edge']) if risk else None
    watch=best or over or next((x for x in entries if x['fair'] is not None or x['live'] is not None), entries[0] if entries else None)
    for x in entries:
        role='MARKET_WATCH'
        if best and x['key']==best['key']: role='BEST_VALUE'
        if over and x['key']==over['key']: role='OVERBET_RISK'
        market_role_by_key[x['key']]=role
    race_market_commands[rk]={
        'best_value_horse': best['horse'] if best else '',
        'best_value_summary': (f'{best["horse"]}: live {best["live"]:g} vs EDGEiQ {best["fair"]:g}; positive edge {best["edge"]:.1f}%.' if best and best['live'] and best['fair'] else ''),
        'overbet_horse': over['horse'] if over else '',
        'overbet_summary': (f'{over["horse"]}: live {over["live"]:g} vs EDGEiQ {over["fair"]:g}; negative edge {over["edge"]:.1f}%.' if over and over['live'] and over['fair'] else ''),
        'watch_horse': watch['horse'] if watch else '',
        'watch_summary': (f'{watch["horse"]}: market context loaded; EDGEiQ price {watch["fair"]:g}.' if watch and watch['fair'] is not None else 'Market context loaded; live price not available.'),
    }

out=[]
for r in gov:
    k=key(r); rk=rkey(r); c=conn_by.get(k,{}); s=score_by.get(k,{}); old=v2_by.get(k,{})
    conn_qualified=yes(c.get('connection_qualified_angle'))
    conn_matched=yes(c.get('connection_source_matched'))
    if conn_qualified: conn_truth='QUALIFYING_CONNECTION_ANGLE'
    elif conn_matched: conn_truth='TRUE_ZERO_NO_QUALIFYING_ANGLE'
    else: conn_truth='SOURCE_MISSING_OR_JOIN_FAILED'
    hidden_avail=yes(old.get('edgeiq_hidden_gem_evidence_available_v2') or r.get('edgeiq_hidden_gem_evidence_available'))
    market_avail=yes(r.get('edgeiq_market_evidence_available')) or bool(first(r,['edgeiq_active_display_fair_price_shadow','display_fair_price','ui_fair_price','fair_price']))
    mcmd=race_market_commands.get(rk,{})
    score_src_parts=[]
    score_map={
        'overall':('edgeiq_score_overall_v3','chosen_overall_score','chosen_overall_source'),
        'distance':('edgeiq_score_distance_v3','chosen_distance_score','chosen_distance_source'),
        'condition':('edgeiq_score_condition_v3','chosen_condition_score','chosen_condition_source'),
        'class':('edgeiq_score_class_v3','chosen_class_score','chosen_class_source'),
        'campaign':('edgeiq_score_campaign_v3','chosen_campaign_score','chosen_campaign_source'),
        'pace':('edgeiq_score_pace_v3','chosen_pace_score','chosen_pace_source'),
        'connections':('edgeiq_score_connections_v3','chosen_connection_score','chosen_connection_source'),
        'market':('edgeiq_score_market_v3','chosen_market_score','chosen_market_source'),
        'confidence':('edgeiq_score_confidence_v3','chosen_confidence_score','chosen_confidence_source'),
    }
    nr={
        'race_date':r.get('race_date',''),'track':r.get('track',''),'race_no':r.get('race_no',''),'horse':r.get('horse',''),
        'edgeiq_active_display_fair_price':first(r,['edgeiq_active_display_fair_price_shadow','edgeiq_v7_2g2_guarded_display_fair_price','display_fair_price','ui_fair_price','fair_price']),
        'edgeiq_v7_2g2_guarded_display_fair_price':first(r,['edgeiq_v7_2g2_guarded_display_fair_price','edgeiq_v7_2g2_active_display_fair_price_shadow']),
        'edgeiq_connection_evidence_available_v3':'YES' if conn_qualified else 'NO',
        'edgeiq_connection_angle_summary_v3':c.get('connection_summary',''),
        'edgeiq_connection_truth_status_v3':conn_truth,
        'edgeiq_connection_source_v3':c.get('matched_sources','') or ('NO_SOURCE' if not conn_matched else 'MATCHED_NO_ANGLE'),
        'edgeiq_market_evidence_available_v3':'YES' if market_avail else 'NO',
        'edgeiq_market_signal_summary_v3':r.get('edgeiq_market_signal_summary','') or (f'EDGEiQ price {first(r,["edgeiq_active_display_fair_price_shadow","display_fair_price","ui_fair_price","fair_price"])} available.' if first(r,['edgeiq_active_display_fair_price_shadow','display_fair_price','ui_fair_price','fair_price']) else ''),
        'command_best_value_horse_v3':mcmd.get('best_value_horse',''),
        'command_best_value_summary_v3':mcmd.get('best_value_summary',''),
        'command_overbet_horse_v3':mcmd.get('overbet_horse',''),
        'command_overbet_summary_v3':mcmd.get('overbet_summary',''),
        'command_market_watch_horse_v3':mcmd.get('watch_horse',''),
        'command_market_watch_summary_v3':mcmd.get('watch_summary',''),
        'edgeiq_hidden_gem_evidence_available_v3':'YES' if hidden_avail else 'NO',
        'edgeiq_hidden_gem_summary_v3':old.get('edgeiq_hidden_gem_summary_v2') or r.get('edgeiq_hidden_gem_summary',''),
        'edgeiq_hidden_gem_truth_status_v3':'QUALIFYING_HIDDEN_GEM' if hidden_avail else 'TRUE_ZERO_NO_HIDDEN_GEM_SIGNAL',
        'command_market_role_v3':market_role_by_key.get(k,'MARKET_WATCH'),
        'command_connection_role_v3':'CONNECTION_ANGLE' if conn_qualified else ('CONNECTION_CHECKED_TRUE_ZERO' if conn_matched else 'CONNECTION_SOURCE_MISSING'),
    }
    for label,(outfield,scorefield,srcfield) in score_map.items():
        nr[outfield]=s.get(scorefield,'')
        score_src_parts.append(f'{label.upper()}:{s.get(srcfield,"MISSING") if s.get(scorefield,"") else "MISSING"}')
    nr['edgeiq_score_source_v3']='|'.join(score_src_parts)
    out.append(nr)
# race counts
for rk, rows in byrace.items():
    keys={key(x) for x in rows}; members=[x for x in out if key(x) in keys]
    counts={
        'race_field_size_v3':str(len(rows)),
        'race_connection_available_count_v3':str(sum(1 for x in members if x['edgeiq_connection_evidence_available_v3']=='YES')),
        'race_connection_source_matched_count_v3':str(sum(1 for x in members if x['edgeiq_connection_truth_status_v3']!='SOURCE_MISSING_OR_JOIN_FAILED')),
        'race_market_available_count_v3':str(sum(1 for x in members if x['edgeiq_market_evidence_available_v3']=='YES')),
        'race_hidden_gem_available_count_v3':str(sum(1 for x in members if x['edgeiq_hidden_gem_evidence_available_v3']=='YES')),
        'race_edgeiq_price_count_v3':str(sum(1 for x in members if x['edgeiq_active_display_fair_price']!='')),
        'race_score_overall_count_v3':str(sum(1 for x in members if x['edgeiq_score_overall_v3']!='')),
    }
    for x in members: x.update(counts)
fields=['race_date','track','race_no','horse','edgeiq_active_display_fair_price','edgeiq_v7_2g2_guarded_display_fair_price','edgeiq_connection_evidence_available_v3','edgeiq_connection_angle_summary_v3','edgeiq_connection_truth_status_v3','edgeiq_connection_source_v3','edgeiq_market_evidence_available_v3','edgeiq_market_signal_summary_v3','command_best_value_horse_v3','command_best_value_summary_v3','command_overbet_horse_v3','command_overbet_summary_v3','command_market_watch_horse_v3','command_market_watch_summary_v3','edgeiq_hidden_gem_evidence_available_v3','edgeiq_hidden_gem_summary_v3','edgeiq_hidden_gem_truth_status_v3','edgeiq_score_overall_v3','edgeiq_score_distance_v3','edgeiq_score_condition_v3','edgeiq_score_class_v3','edgeiq_score_campaign_v3','edgeiq_score_pace_v3','edgeiq_score_connections_v3','edgeiq_score_market_v3','edgeiq_score_confidence_v3','edgeiq_score_source_v3','command_market_role_v3','command_connection_role_v3','race_connection_available_count_v3','race_connection_source_matched_count_v3','race_market_available_count_v3','race_hidden_gem_available_count_v3','race_edgeiq_price_count_v3','race_score_overall_count_v3','race_field_size_v3']
races=set(rkey(r) for r in gov); caul=sum(1 for r in out if clean(r['track'])=='CAULFIELD' and r['race_no']=='7')
status='COMMAND_ENRICHMENT_FEED_V3_BUILT'
if sum(1 for r in out if r['edgeiq_connection_evidence_available_v3']=='YES')==0 and sum(1 for r in out if r['race_connection_source_matched_count_v3']!='0')>0:
    status='COMMAND_ENRICHMENT_FEED_V3_BUILT_WITH_TRUE_ZERO_CONNECTIONS'
if len(out)!=EXPECTED_ROWS or len(races)!=EXPECTED_RACES or caul!=19:
    status='COMMAND_ENRICHMENT_FEED_V3_BLOCKED'
audit=[]
for rk, rows in sorted(byrace.items()):
    members=[x for x in out if (clean(x['race_date']),clean(x['track']),race_no(x['race_no']))==rk]
    audit.append({'race_date':rk[0],'track':rk[1],'race_no':rk[2],'field_size':len(rows),'connection_available_count':sum(1 for x in members if x['edgeiq_connection_evidence_available_v3']=='YES'),'connection_source_matched_count':sum(1 for x in members if x['edgeiq_connection_truth_status_v3']!='SOURCE_MISSING_OR_JOIN_FAILED'),'market_available_count':sum(1 for x in members if x['edgeiq_market_evidence_available_v3']=='YES'),'hidden_gem_count':sum(1 for x in members if x['edgeiq_hidden_gem_evidence_available_v3']=='YES'),'edgeiq_price_count':sum(1 for x in members if x['edgeiq_active_display_fair_price']!=''),'score_overall_count':sum(1 for x in members if x['edgeiq_score_overall_v3']!=''),'best_value_horse':members[0].get('command_best_value_horse_v3','') if members else '','overbet_horse':members[0].get('command_overbet_horse_v3','') if members else ''})
summary={'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'rows':len(out),'races':len(races),'caulfield_r7_rows':caul,'connection_available_rows':sum(1 for r in out if r['edgeiq_connection_evidence_available_v3']=='YES'),'connection_source_matched_rows':sum(1 for r in out if r['edgeiq_connection_truth_status_v3']!='SOURCE_MISSING_OR_JOIN_FAILED'),'market_available_rows':sum(1 for r in out if r['edgeiq_market_evidence_available_v3']=='YES'),'hidden_gem_available_rows':sum(1 for r in out if r['edgeiq_hidden_gem_evidence_available_v3']=='YES'),'edgeiq_price_rows':sum(1 for r in out if r['edgeiq_active_display_fair_price']!=''),'score_overall_rows':sum(1 for r in out if r['edgeiq_score_overall_v3']!='')}
write_csv(OUT,out,fields); write_csv(SUMMARY,[summary],list(summary.keys())); write_csv(AUDIT,audit,list(audit[0].keys()))
REPORT.write_text('\n'.join(['EDGEiQ Command Enrichment Feed V3','='*38,f'Status: {status}',f'Rows/races: {len(out)}/{len(races)}',f'CAULFIELD R7 rows: {caul}',f'Connection available/source matched: {summary["connection_available_rows"]}/{summary["connection_source_matched_rows"]}',f'Market/price rows: {summary["market_available_rows"]}/{summary["edgeiq_price_rows"]}',f'Score overall rows: {summary["score_overall_rows"]}'])+'\n',encoding='utf-8')
print(status)
