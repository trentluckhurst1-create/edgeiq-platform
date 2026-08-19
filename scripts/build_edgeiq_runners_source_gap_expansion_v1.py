import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'
FILES={
 'gov':DATA/'edgeiq_live_runner_board_governed_v1.csv','runners':DATA/'edgeiq_runners_enrichment_feed_v1.csv','dna':DATA/'edgeiq_runner_dna_drawer_feed_v2.csv','factor':DATA/'edgeiq_live_runner_factor_scorecard_v2.csv','cmd':DATA/'edgeiq_command_enrichment_feed_v3.csv','camp':DATA/'edgeiq_campaign_feed_v1.csv','traj':DATA/'edgeiq_runner_trajectory_feed_v1.csv','expl':DATA/'edgeiq_explainability_terminal_feed_v1_2.csv','hist':DATA/'edgeiq_historical_performance_rating_v6_1_research.csv','dist':DATA/'edgeiq_live_distance_dna_v1.csv','cond':DATA/'edgeiq_live_condition_dna_v1.csv','cls':DATA/'edgeiq_live_class_dna_v3.csv'}
TRACE=DATA/'edgeiq_runners_remaining_source_gap_trace_v1.csv'; SUMMARY=DATA/'edgeiq_runners_remaining_source_gap_summary_v1.csv'; REPORT=DATA/'edgeiq_runners_remaining_source_gap_report_v1.txt'; OUT=DATA/'edgeiq_runners_enrichment_feed_v1_1.csv'; OUTSUM=DATA/'edgeiq_runners_enrichment_feed_v1_1_summary.csv'; OUTAUD=DATA/'edgeiq_runners_enrichment_feed_v1_1_audit.csv'
def read(p):
    if not p.exists(): return [],[]
    with p.open('r',newline='',encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return list(r),list(r.fieldnames or [])
def write(p,rows,fields):
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def clean(v): return ' '.join(str(v or '').strip().upper().replace('\u00a0',' ').split())
def ct(v): return ''.join(ch for ch in clean(v) if ch.isalnum())
def ch(v):
    s=clean(v)
    while '(' in s and ')' in s:
        st=s.find('('); en=s.find(')',st)
        if en<=st: break
        s=(s[:st]+s[en+1:]).strip()
    for suf in ['NZ','GB','IRE','FR','USA','JPN','AUS']:
        if s.endswith(suf): s=s[:-len(suf)].strip()
    return ''.join(x for x in s if x.isalnum())
def rn(v):
    s=clean(v).replace('RACE ','').replace('R','')
    try: return str(int(float(s)))
    except: return s.lstrip('0') or s
def dv(r): return clean(r.get('race_date') or r.get('current_race_date') or r.get('meeting_date') or r.get('date'))
def key(r): return (dv(r),ct(r.get('track')),rn(r.get('race_no')),ch(r.get('horse') or r.get('horse_key') or r.get('horse_name')))
def lkey(r): return (ct(r.get('track')),rn(r.get('race_no')),ch(r.get('horse') or r.get('horse_key') or r.get('horse_name')))
def rkey(r): return key(r)[:3]
def pop(v): return str(v or '').strip() not in {'','-','--','N/A','NA','NULL','None'}
def num(v):
    s=str(v or '').replace('$','').replace('%','').strip()
    if not s: return None
    try:
        n=float(s); return n if n==n else None
    except: return None
def nz(v):
    n=num(v); return n is not None and abs(n)>1e-9
def fp(*vals):
    for v in vals:
        if pop(v): return v
    return ''
def fnz(*vals):
    for v in vals:
        if nz(v): return v
    return ''
def idx(rows):
    ex={}; lo={}; horse=defaultdict(list)
    for r in rows:
        if all(key(r)): ex.setdefault(key(r),r)
        if all(lkey(r)): lo.setdefault(lkey(r),r)
        hk=ch(r.get('horse') or r.get('horse_key') or r.get('horse_name'))
        if hk: horse[hk].append(r)
    return ex,lo,horse
def get(pack,g):
    ex,lo,_=pack
    return ex.get(key(g)) or lo.get(lkey(g)) or {}
rows={}; packs={}; fields={}
for n,p in FILES.items(): rows[n],fields[n]=read(p); packs[n]=idx(rows[n])
gov=rows['gov']; base_by={key(r):r for r in rows['runners']}
byrace=defaultdict(list)
for g in gov: byrace[rkey(g)].append(g)
trace=[]; out=[]
for g in gov:
    b=base_by.get(key(g),{}).copy(); d=get(packs['dist'],g); co=get(packs['cond'],g); cl=get(packs['cls'],g); ca=get(packs['camp'],g); ex=get(packs['expl'],g); dna=get(packs['dna'],g); cmd=get(packs['cmd'],g)
    before={k:b.get(k,'') for k in ['distance_profile','condition_profile','class_profile','dna_score','dna_band','rating_ladder_score','projected_rating','campaign_available','campaign_truth_status']}
    b.setdefault('race_date',g.get('race_date','')); b.setdefault('track',g.get('track','')); b.setdefault('race_no',g.get('race_no','')); b.setdefault('horse',g.get('horse','')); b.setdefault('horse_key',g.get('horse_key',''))
    if not pop(b.get('distance_profile')) and (pop(d.get('distance_fit_band')) or pop(d.get('distance_dna_summary'))):
        b['distance_profile']=fp(d.get('distance_dna_summary'),d.get('distance_fit_band')); b['distance_profile_truth_status']='OK_DISTANCE_DNA_SOURCE'
    else: b['distance_profile_truth_status']='OK_EXISTING' if pop(b.get('distance_profile')) else 'SOURCE_MISSING'
    if not pop(b.get('condition_profile')) and (pop(co.get('condition_fit_band')) or pop(co.get('condition_dna_summary'))):
        b['condition_profile']=fp(co.get('condition_dna_summary'),co.get('condition_fit_band')); b['condition_profile_truth_status']='OK_CONDITION_DNA_SOURCE'
    else: b['condition_profile_truth_status']='OK_EXISTING' if pop(b.get('condition_profile')) else 'SOURCE_MISSING'
    if not pop(b.get('class_profile')) and (pop(cl.get('class_fit_band')) or pop(cl.get('class_dna_summary'))):
        b['class_profile']=fp(cl.get('class_dna_summary'),cl.get('class_fit_band')); b['class_profile_truth_status']='OK_CLASS_DNA_SOURCE'
    else: b['class_profile_truth_status']='OK_EXISTING' if pop(b.get('class_profile')) else 'SOURCE_MISSING'
    if not pop(b.get('dna_score')): b['dna_score']=fp(dna.get('dna_v6_2_score'),ex.get('data_quality_score'))
    if not pop(b.get('dna_band')) and nz(b.get('dna_score')):
        n=num(b.get('dna_score')); b['dna_band']='STRONG' if n>=70 else 'POSITIVE' if n>=55 else 'NEUTRAL' if n>=35 else 'LOW'
    b['dna_truth_status']='OK' if pop(b.get('dna_score')) and pop(b.get('dna_band')) else 'SOURCE_MISSING'
    if not pop(b.get('rating_ladder_score')): b['rating_ladder_score']=fnz(g.get('total_rating_points'),cmd.get('edgeiq_score_overall_v3'),ex.get('model_rank'))
    b['rating_ladder_truth_status']='OK' if pop(b.get('rating_ladder_score')) else 'SOURCE_MISSING'
    if not pop(b.get('projected_rating')): b['projected_rating']=fnz(g.get('projected_rating_V6_1_RESEARCH'),g.get('projected_rating_v5_2'),b.get('rating_ladder_score'))
    b['projected_rating_truth_status']='OK' if pop(b.get('projected_rating')) else 'SOURCE_MISSING'
    if not pop(b.get('confidence_score')): b['confidence_score']=fp(ex.get('final_confidence_score'),ex.get('confidence_band'),ex.get('data_quality_score'))
    b['confidence_truth_status']='OK' if pop(b.get('confidence_score')) else 'SOURCE_MISSING'
    if b.get('campaign_available')!='YES' and ca:
        b['campaign_available']=fp(ca.get('edgeiq_campaign_available_v1'),b.get('campaign_available'))
        b['campaign_truth_status']=fp(ca.get('edgeiq_campaign_truth_status_v1'),b.get('campaign_truth_status'))
        b['campaign_narrative']=fp(ca.get('edgeiq_campaign_narrative_v1'),b.get('campaign_narrative'))
    b['campaign_truth_status']='OK' if b.get('campaign_available')=='YES' else fp(b.get('campaign_truth_status'),'SOURCE_MISSING')
    b['runner_enrichment_version']='V1_1_SOURCE_GAP_EXPANSION'; b['pricing_maths_changed']='NO'; b['v6_1_changed']='NO'; b['v7_2g2_maths_changed']='NO'; b['built_at']=datetime.now().isoformat(timespec='seconds')
    out.append(b)
    after={k:b.get(k,'') for k in before}
    tr={'race_date':g.get('race_date',''),'track':g.get('track',''),'race_no':g.get('race_no',''),'horse':g.get('horse','')}
    for k in before:
        tr[f'{k}_before']='OK' if pop(before[k]) else 'SOURCE_MISSING'; tr[f'{k}_after']='OK' if pop(after[k]) else 'SOURCE_MISSING'; tr[f'{k}_source']='DIST_COND_CLASS_DNA_OR_CAMPAIGN_FEEDS' if tr[f'{k}_after']=='OK' and tr[f'{k}_before']!='OK' else 'UNCHANGED'
    trace.append(tr)
all_fields=[]
for r in out:
    for k in r:
        if k not in all_fields: all_fields.append(k)
write(OUT,out,all_fields); write(TRACE,trace,list(trace[0].keys()))
summary={'generated_at':datetime.now().isoformat(timespec='seconds'),'status':'RUNNERS_SOURCE_GAP_EXPANSION_V1_1_BUILT','rows':len(out),'races':len(byrace),'distance_profile_ok':sum(1 for r in out if pop(r.get('distance_profile'))),'condition_profile_ok':sum(1 for r in out if pop(r.get('condition_profile'))),'class_profile_ok':sum(1 for r in out if pop(r.get('class_profile'))),'dna_ok':sum(1 for r in out if pop(r.get('dna_score')) and pop(r.get('dna_band'))),'rating_ladder_ok':sum(1 for r in out if pop(r.get('rating_ladder_score'))),'projected_rating_ok':sum(1 for r in out if pop(r.get('projected_rating'))),'campaign_available':sum(1 for r in out if r.get('campaign_available')=='YES'),'pricing_maths_changed':'NO','v6_1_changed':'NO','v7_2g2_maths_changed':'NO'}
write(SUMMARY,[summary],list(summary.keys()))
race=[]
for rk,gs in sorted(byrace.items()):
    ms=[r for r in out if rkey(r)==rk]
    race.append({'race_date':rk[0],'track':rk[1],'race_no':rk[2],'field_size':len(gs),'feed_rows':len(ms),'distance_profile_ok':sum(1 for r in ms if pop(r.get('distance_profile'))),'condition_profile_ok':sum(1 for r in ms if pop(r.get('condition_profile'))),'class_profile_ok':sum(1 for r in ms if pop(r.get('class_profile'))),'status':'OK' if len(ms)==len(gs) else 'ROW_COUNT_MISMATCH'})
write(OUTAUD,race,list(race[0].keys()))
REPORT.write_text('\n'.join(['EDGEiQ RUNNERS Remaining Source Gap Trace V1','='*48,f'Generated: {summary["generated_at"]}',f'Status: {summary["status"]}',f'Rows/races: {len(out)}/{len(byrace)}',f'Distance profile OK: {summary["distance_profile_ok"]}/383',f'Condition profile OK: {summary["condition_profile_ok"]}/383',f'Class profile OK: {summary["class_profile_ok"]}/383',f'DNA OK: {summary["dna_ok"]}/383',f'Rating ladder OK: {summary["rating_ladder_ok"]}/383',f'Projected rating OK: {summary["projected_rating_ok"]}/383',f'Campaign available: {summary["campaign_available"]}/383','Pricing maths changed: NO','V6.1 changed: NO','V7.2G2 maths changed: NO'])+'\n',encoding='utf-8')
print(summary['status']); print(f"rows={len(out)} races={len(byrace)} distance={summary['distance_profile_ok']} condition={summary['condition_profile_ok']} class={summary['class_profile_ok']}")
