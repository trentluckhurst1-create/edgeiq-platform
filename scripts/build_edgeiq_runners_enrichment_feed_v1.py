import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
GOV=DATA/'edgeiq_live_runner_board_governed_v1.csv'
DNA=DATA/'edgeiq_runner_dna_drawer_feed_v2.csv'
FACT=DATA/'edgeiq_live_runner_factor_scorecard_v2.csv'
CMD=DATA/'edgeiq_command_enrichment_feed_v3.csv'
TRAJ=DATA/'edgeiq_runner_trajectory_feed_v1.csv'
CONN=DATA/'edgeiq_connection_intelligence_v2_1.csv'
CAMP=DATA/'edgeiq_campaign_intelligence_engine_v1_1.csv'
FORM=DATA/'edgeiq_form_intelligence_v2.csv'
MAP=DATA/'edgeiq_map_enrichment_feed_v1.csv'
OUT=DATA/'edgeiq_runners_enrichment_feed_v1.csv'
SUMMARY=DATA/'edgeiq_runners_enrichment_feed_v1_summary.csv'
AUDIT=DATA/'edgeiq_runners_enrichment_feed_v1_audit.csv'
REPORT=DATA/'edgeiq_runners_enrichment_feed_v1_report.txt'

def read(path):
    if not path.exists(): return [], []
    with path.open('r',newline='',encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return list(r), list(r.fieldnames or [])
def write(path, rows, fields):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def clean(v): return ' '.join(str(v or '').strip().upper().replace('\u00a0',' ').split())
def clean_track(v): return ''.join(ch for ch in clean(v) if ch.isalnum())
def clean_horse(v):
    s=clean(v)
    while '(' in s and ')' in s:
        st=s.find('('); en=s.find(')',st)
        if en<=st: break
        s=(s[:st]+s[en+1:]).strip()
    for suffix in ['NZ','GB','IRE','FR','USA','JPN','AUS']:
        if s.endswith(suffix): s=s[:-len(suffix)].strip()
    return ''.join(ch for ch in s if ch.isalnum())
def race_no(v):
    s=clean(v).replace('RACE ','').replace('R','')
    try: return str(int(float(s)))
    except Exception: return s.lstrip('0') or s
def date_val(r): return clean(r.get('race_date') or r.get('current_race_date') or r.get('meeting_date') or r.get('date'))
def key(r): return (date_val(r),clean_track(r.get('track')),race_no(r.get('race_no')),clean_horse(r.get('horse') or r.get('horse_key')))
def loose_key(r): return (clean_track(r.get('track')),race_no(r.get('race_no')),clean_horse(r.get('horse') or r.get('horse_key') or r.get('horse_name')))
def rkey(r): return key(r)[:3]
def populated(v): return str(v or '').strip() not in {'','-','--','N/A','NA','NULL','None'}
def meaningful(v):
    s=str(v or '').strip().upper()
    return populated(v) and s not in {'NO','FALSE','0','0.0','NO HISTORY','NO_PROFILE','NO PROFILE','UNKNOWN','UNPROVEN','NO_EVIDENCE','NO EVIDENCE'}
def num(v):
    s=str(v or '').replace('$','').replace('%','').strip()
    if not s: return None
    try:
        n=float(s); return n if n==n else None
    except Exception: return None
def first_pop(*vals):
    for v in vals:
        if populated(v): return v
    return ''
def first_nonzero(*vals):
    for v in vals:
        n=num(v)
        if n is not None and abs(n)>1e-9: return v
    return ''
def yes(v): return clean(v) in {'YES','TRUE','1','Y','ON'}
def index(rows):
    exact={}; loose={}
    for r in rows:
        k=key(r); lk=loose_key(r)
        if all(k): exact.setdefault(k,r)
        if all(lk): loose.setdefault(lk,r)
    return exact,loose
def get(ex,lo,g): return ex.get(key(g)) or lo.get(loose_key(g)) or {}
def factor_for(factors, factor):
    for f in factors:
        if clean(f.get('factor'))==clean(factor): return f
    return {}
def band_from_score(score):
    n=num(score)
    if n is None: return ''
    if n>=70: return 'STRONG'
    if n>=55: return 'POSITIVE'
    if n>=40: return 'NEUTRAL'
    return 'LOW'
def profile_strength_from_sources(dna_score, starts):
    st=num(starts) or 0; ds=num(dna_score)
    if st==0 and ds is None: return 'SOURCE_MISSING'
    if st>=8 or (ds is not None and ds>=70): return 'HIGH'
    if st>=3 or ds is not None: return 'MEDIUM'
    return 'LOW'
def score_truth(v, source): return 'OK_SOURCE_FIELD' if populated(v) else f'{source}_SOURCE_MISSING'

gov,_=read(GOV); dna_rows,_=read(DNA); fact_rows,_=read(FACT); cmd_rows,_=read(CMD); traj_rows,_=read(TRAJ); conn_rows,_=read(CONN); camp_rows,_=read(CAMP); form_rows,_=read(FORM); map_rows,_=read(MAP)
dna_ex,dna_lo=index(dna_rows); cmd_ex,cmd_lo=index(cmd_rows); traj_ex,traj_lo=index(traj_rows); conn_ex,conn_lo=index(conn_rows); camp_ex,camp_lo=index(camp_rows); form_ex,form_lo=index(form_rows); map_ex,map_lo=index(map_rows)
fact_by=defaultdict(list)
for f in fact_rows:
    fact_by[key(f)].append(f); fact_by[('',)+loose_key(f)].append(f)
byrace=defaultdict(list)
for g in gov: byrace[rkey(g)].append(g)
rows=[]
for g in gov:
    d=get(dna_ex,dna_lo,g); c=get(cmd_ex,cmd_lo,g); t=get(traj_ex,traj_lo,g); cn=get(conn_ex,conn_lo,g); ca=get(camp_ex,camp_lo,g); fo=get(form_ex,form_lo,g); mp=get(map_ex,map_lo,g)
    facts=fact_by.get(key(g),[]) or fact_by.get(('',)+loose_key(g),[])
    fd=factor_for(facts,'DISTANCE'); fc=factor_for(facts,'CONDITION'); fcl=factor_for(facts,'CLASS'); fconf=factor_for(facts,'CONFIDENCE')
    dna_score=first_pop(d.get('dna_v6_2_score'),d.get('runner_dna_v6_1_score'),d.get('dna_score'))
    dna_band=first_pop(d.get('dna_v6_2_band'),d.get('runner_dna_v6_1_band'),d.get('dna_band'),band_from_score(dna_score))
    rating=first_nonzero(g.get('projected_rating_V6_1_RESEARCH'),g.get('projected_rating_v5_2'),g.get('total_rating_points'),c.get('edgeiq_score_overall_v3'))
    projected_rating_source='PROJECTION_FIELD' if populated(g.get('projected_rating_V6_1_RESEARCH') or g.get('projected_rating_v5_2')) else 'RATING_PROXY_NOT_V6_1'
    confidence=first_pop(fconf.get('factor_score'),c.get('edgeiq_score_confidence_v3'),d.get('dna_v6_2_score'),d.get('runner_dna_v6_1_score'),g.get('total_rating_points'))
    pos1=first_pop(d.get('positive_1_factor'),d.get('strongest_factor_v6_2'),d.get('strongest_factor_v6_1'))
    pos2=first_pop(d.get('positive_2_factor'),mp.get('pace_fit_band'))
    pos3=first_pop(d.get('positive_3_factor'),c.get('command_market_role_v3'))
    neg1=first_pop(d.get('negative_1_factor'),d.get('weakest_factor_v6_2'),d.get('weakest_factor_v6_1'))
    neg2=first_pop(d.get('negative_2_factor'),ca.get('campaign_risk_band'))
    neg3=first_pop(d.get('negative_3_factor'),cn.get('connection_risk_1'))
    distance_profile=first_pop(d.get('distance_fit_band'),fd.get('factor_band'),fo.get('EPF_band'))
    condition_profile=first_pop(d.get('condition_fit_band'),fc.get('factor_band'))
    class_profile=first_pop(d.get('class_fit_band'),fcl.get('factor_band'))
    campaign_available=yes(c.get('edgeiq_campaign_available_v3_3')) or clean(ca.get('evidence_status')) not in {'','NO HISTORY','NO_HISTORY'}
    trajectory_available=yes(c.get('edgeiq_trajectory_available_v3_2')) or clean(t.get('trajectory_evidence_status_v1')) not in {'','NO HISTORY','NO_HISTORY'}
    connection_available=yes(c.get('edgeiq_connection_evidence_available_v3')) or clean(cn.get('connection_band')) not in {'','NO_EVIDENCE','NO EVIDENCE'}
    starts=first_pop(ca.get('history_runs_used'),t.get('recent_start_count_v1'),fo.get('recent_runs_found'))
    profile_strength=profile_strength_from_sources(dna_score, starts)
    horse_archetype=first_pop(d.get('strongest_factor_v6_2'),d.get('strongest_factor_v6_1'),mp.get('run_style'),'CURRENT RUNNER')
    profile_summary=f"{g.get('horse','Runner')} current profile: DNA {dna_band or 'not loaded'}, rating {rating or 'not loaded'}, pace {mp.get('run_style') or 'not loaded'}, campaign {'loaded' if campaign_available else 'not loaded'}, trajectory {'loaded' if trajectory_available else 'not loaded'}."
    dossier_ok=populated(dna_score) and populated(rating) and populated(first_pop(g.get('display_decision'),g.get('execution_action'),g.get('execution_action_final')))
    row={
        'race_date':g.get('race_date',''),'track':g.get('track',''),'race_no':g.get('race_no',''),'horse':g.get('horse',''),'horse_key':g.get('horse_key',''),'runner_key':g.get('runner_key',''),
        'horse_archetype':horse_archetype,'profile_strength':profile_strength,'career_starts':starts,'career_wins':'','career_places':'','career_win_pct':'','career_place_pct':'',
        'distance_profile':distance_profile,'track_profile':g.get('track',''),'condition_profile':condition_profile,'class_profile':class_profile,'profile_context_rows':starts,
        'dna_score':dna_score,'dna_band':dna_band,'dna_v6_2_score':d.get('dna_v6_2_score',''),'dna_v6_2_band':d.get('dna_v6_2_band',''),'runner_dna_v6_2_rank_in_race':d.get('runner_dna_v6_2_rank_in_race',''),
        'positive_1_factor':pos1,'positive_1_impact':d.get('positive_1_impact',''),'positive_2_factor':pos2,'positive_2_impact':d.get('positive_2_impact',''),'positive_3_factor':pos3,'positive_3_impact':d.get('positive_3_impact',''),
        'negative_1_factor':neg1,'negative_1_impact':d.get('negative_1_impact',''),'negative_2_factor':neg2,'negative_2_impact':d.get('negative_2_impact',''),'negative_3_factor':neg3,'negative_3_impact':d.get('negative_3_impact',''),
        'impact_explanation':first_pop(d.get('impact_explanation'),d.get('runner_dna_v6_2_narrative'),profile_summary),'runner_dna_v6_2_narrative':first_pop(d.get('runner_dna_v6_2_narrative'),profile_summary),
        'projected_rating':rating,'projected_rating_source':projected_rating_source,'projected_rating_truth_status':score_truth(rating,'PROJECTED_RATING'),
        'confidence_score':confidence,'confidence_source':'CONFIDENCE_OR_DNA_PROXY','confidence_truth_status':score_truth(confidence,'CONFIDENCE'),
        'rating_ladder_score':first_nonzero(g.get('total_rating_points'),c.get('edgeiq_score_overall_v3')),'score_overall':first_pop(c.get('edgeiq_score_overall_v3'),g.get('total_rating_points')),
        'score_distance':c.get('edgeiq_score_distance_v3',''),'score_condition':c.get('edgeiq_score_condition_v3',''),'score_class':c.get('edgeiq_score_class_v3',''),'score_campaign':c.get('edgeiq_score_campaign_v3',''),'score_pace':first_pop(c.get('edgeiq_score_pace_v3'),mp.get('pace_fit')),'score_connections':c.get('edgeiq_score_connections_v3',''),'score_market':c.get('edgeiq_score_market_v3',''),'score_confidence':first_pop(c.get('edgeiq_score_confidence_v3'),confidence),
        'campaign_available':'YES' if campaign_available else 'NO','campaign_truth_status':first_pop(c.get('edgeiq_campaign_truth_status_v3_3'),ca.get('evidence_status'),'SOURCE_MISSING'),'campaign_narrative':first_pop(c.get('edgeiq_campaign_narrative_v3_3'),ca.get('campaign_narrative')),
        'trajectory_available':'YES' if trajectory_available else 'NO','trajectory_truth_status':first_pop(c.get('edgeiq_trajectory_truth_status_v3_2'),t.get('trajectory_evidence_status_v1'),'SOURCE_MISSING'),'trajectory_score':first_pop(c.get('edgeiq_trajectory_score_v3_2'),t.get('trajectory_score_v1')),'trajectory_band':first_pop(c.get('edgeiq_trajectory_band_v3_2'),t.get('trajectory_band_v1')),'trajectory_narrative':first_pop(c.get('edgeiq_trajectory_narrative_v3_2'),t.get('trajectory_narrative_v1')),
        'connection_available':'YES' if connection_available else 'NO','connection_truth_status':first_pop(c.get('edgeiq_connection_truth_status_v3'),cn.get('connection_evidence_status'),'SOURCE_MISSING'),'connection_band':cn.get('connection_band',''),'connection_score':first_pop(c.get('edgeiq_score_connections_v3'),cn.get('connection_score')),'connection_narrative':first_pop(c.get('edgeiq_connection_angle_summary_v3'),cn.get('connection_narrative')),
        'decision':first_pop(g.get('display_decision'),g.get('execution_action'),g.get('execution_action_final')),'selected_runner_dossier_status':'OK' if dossier_ok else 'SOURCE_MISSING',
        'profile_summary':profile_summary,'runner_enrichment_truth_status':'RUNNERS_ENRICHMENT_AVAILABLE','pricing_maths_changed':'NO','v6_1_changed':'NO','v7_2g2_maths_changed':'NO','built_at':datetime.now().isoformat(timespec='seconds')
    }
    rows.append(row)
fields=list(rows[0].keys()) if rows else []
write(OUT,rows,fields)
summary={'generated_at':datetime.now().isoformat(timespec='seconds'),'status':'RUNNERS_ENRICHMENT_FEED_V1_BUILT','rows':len(rows),'races':len(byrace),'dna_score_available':sum(1 for r in rows if populated(r['dna_score'])),'dna_band_available':sum(1 for r in rows if populated(r['dna_band'])),'projected_rating_available':sum(1 for r in rows if populated(r['projected_rating'])),'confidence_available':sum(1 for r in rows if populated(r['confidence_score'])),'profile_summary_available':sum(1 for r in rows if populated(r['profile_summary'])),'dossier_ok':sum(1 for r in rows if r['selected_runner_dossier_status']=='OK'),'pricing_maths_changed':'NO','v6_1_changed':'NO','v7_2g2_maths_changed':'NO'}
write(SUMMARY,[summary],list(summary.keys()))
race_rows=[]
for rk,members_g in sorted(byrace.items()):
    members=[r for r in rows if (clean(r['race_date']),clean_track(r['track']),race_no(r['race_no']))==rk]
    race_rows.append({'race_date':rk[0],'track':rk[1],'race_no':rk[2],'field_size':len(members_g),'feed_rows':len(members),'dna_score_available':sum(1 for r in members if populated(r['dna_score'])),'projected_rating_available':sum(1 for r in members if populated(r['projected_rating'])),'confidence_available':sum(1 for r in members if populated(r['confidence_score'])),'status':'OK' if len(members)==len(members_g) else 'ROW_COUNT_MISMATCH'})
write(AUDIT,race_rows,list(race_rows[0].keys()))
REPORT.write_text('\n'.join(['EDGEiQ RUNNERS Enrichment Feed V1','='*38,f'Generated: {summary["generated_at"]}','Status: RUNNERS_ENRICHMENT_FEED_V1_BUILT',f'Rows/races: {len(rows)}/{len(byrace)}',f'DNA score available: {summary["dna_score_available"]}/{len(rows)}',f'Projected rating/display rating available: {summary["projected_rating_available"]}/{len(rows)}',f'Confidence available: {summary["confidence_available"]}/{len(rows)}',f'Profile summary available: {summary["profile_summary_available"]}/{len(rows)}',f'Dossier OK: {summary["dossier_ok"]}/{len(rows)}','Pricing maths changed: NO','V6.1 changed: NO','V7.2G2 maths changed: NO'])+'\n',encoding='utf-8')
print('RUNNERS_ENRICHMENT_FEED_V1_BUILT')
print(f'rows={len(rows)}')
print(f'races={len(byrace)}')
print(f'confidence_available={summary["confidence_available"]}')

