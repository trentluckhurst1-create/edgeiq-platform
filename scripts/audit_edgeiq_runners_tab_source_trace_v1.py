import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
TSX = ROOT / 'src' / 'components' / 'RaceIntelligenceScreen.tsx'
GOV = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
SOURCES = {
    'runner_profile': DATA / 'edgeiq_runner_profile_engine_current.csv',
    'dna_drawer': DATA / 'edgeiq_runner_dna_drawer_feed_v2.csv',
    'factor_scorecard': DATA / 'edgeiq_live_runner_factor_scorecard_v2.csv',
    'command': DATA / 'edgeiq_command_enrichment_feed_v3.csv',
    'trajectory': DATA / 'edgeiq_runner_trajectory_feed_v1.csv',
    'connection': DATA / 'edgeiq_connection_intelligence_v2_1.csv',
    'form': DATA / 'edgeiq_form_intelligence_v2.csv',
    'campaign': DATA / 'edgeiq_campaign_intelligence_engine_v1_1.csv',
    'map': DATA / 'edgeiq_map_enrichment_feed_v1.csv',
    'runner_intel': DATA / 'edgeiq_runner_intelligence_v1.csv',
    'runners_enrichment': DATA / 'edgeiq_runners_enrichment_feed_v1_1.csv',
}
OUT = DATA / 'edgeiq_runners_tab_source_trace_v1.csv'
RACE = DATA / 'edgeiq_runners_tab_race_summary_v1.csv'
REPORT = DATA / 'edgeiq_runners_tab_fix_report_v1.txt'
FIX = {'JOIN_FAILED','FIELD_NAME_MISMATCH','UI_FALLBACK_MISSING','FEED_FAILURE'}
FIELDS = [
    'runner_profile','DNA_score','DNA_band','rating_ladder','projected_rating','confidence',
    'positive_factors','risk_factors','distance_profile','condition_profile','class_profile',
    'campaign','trajectory_history','connection_evidence','selected_runner_dossier',
    'decision_engine_fields','score_breakdown','UI_fallback_rendering_fields'
]

def read_csv(path):
    if not path.exists(): return [], []
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return list(r), list(r.fieldnames or [])

def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)

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
def date_value(r): return clean(r.get('race_date') or r.get('current_race_date') or r.get('meeting_date') or r.get('date'))
def key(r): return (date_value(r), clean_track(r.get('track')), race_no(r.get('race_no')), clean_horse(r.get('horse') or r.get('horse_name') or r.get('horse_key')))
def loose_key(r): return (clean_track(r.get('track')), race_no(r.get('race_no')), clean_horse(r.get('horse') or r.get('horse_name') or r.get('horse_key')))
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
def nz(v):
    n=num(v); return n is not None and abs(n)>1e-9
def first_pop(*vals):
    for v in vals:
        if populated(v): return v
    return ''
def yes(v): return clean(v) in {'YES','TRUE','1','Y','ON'}
def status(ok, alt, source, missing_reason, source_reason='No source value available.', true_zero=False):
    if ok: return 'OK','Current RUNNERS path is populated.'
    if alt: return 'UI_FALLBACK_MISSING', missing_reason
    if true_zero: return 'TRUE_ZERO', source_reason
    return ('SOURCE_MISSING' if source else 'SOURCE_MISSING'), source_reason

def build_indexes(rows):
    exact={}; loose={}; byhorse=defaultdict(list); byrace=defaultdict(list)
    for r in rows:
        k=key(r); lk=loose_key(r)
        if all(k): exact.setdefault(k,r)
        if all(lk): loose.setdefault(lk,r)
        hk=clean_horse(r.get('horse') or r.get('horse_key') or r.get('horse_name'))
        if hk: byhorse[hk].append(r)
        rk=rkey(r)
        if all(rk): byrace[rk].append(r)
    return exact,loose,byhorse,byrace

gov,gf=read_csv(GOV)
source_rows={}; indexes={}; loose_indexes={}; byhorse={}; byrace_src={}
for name,path in SOURCES.items():
    rows,fields=read_csv(path); source_rows[name]=rows
    indexes[name],loose_indexes[name],byhorse[name],byrace_src[name]=build_indexes(rows)
factor_by_key=defaultdict(list)
for r in source_rows['factor_scorecard']:
    factor_by_key[key(r)].append(r)
    if not date_value(r): factor_by_key[('',)+loose_key(r)].append(r)

def get_source(name,g):
    return indexes[name].get(key(g)) or loose_indexes[name].get(loose_key(g)) or {}
def factors_for(g):
    return factor_by_key.get(key(g),[]) or factor_by_key.get(('',)+loose_key(g),[])
def factor_row(factors, name):
    for f in factors:
        if clean(f.get('factor'))==clean(name): return f
    return {}

tsx=TSX.read_text(encoding='utf-8') if TSX.exists() else ''
ui_tokens={
    'RUNNERS tab': 'RUNNERS' in tsx,
    'DNA subtab': 'DNA' in tsx and 'runnerSubMode' in tsx,
    'PROFILE subtab': 'PROFILE' in tsx,
    'FORM subtab': 'FORM' in tsx,
    'CONNECTIONS subtab': 'CONNECTIONS' in tsx,
    'EXPLAINABILITY subtab': 'EXPLAINABILITY' in tsx,
    'Runner Profile Scorecard': 'Runner Profile Scorecard' in tsx,
    'selectedRunnerFactors': 'selectedRunnerFactors' in tsx,
}
ui_ok=all(ui_tokens.values())

race_members=defaultdict(list)
for g in gov: race_members[rkey(g)].append(g)
rows_out=[]
for g in gov:
    prof=get_source('runner_profile',g); dna=get_source('dna_drawer',g); cmd=get_source('command',g); traj=get_source('trajectory',g); conn=get_source('connection',g); form=get_source('form',g); camp=get_source('campaign',g); mapr=get_source('map',g); ri=get_source('runner_intel',g); re=get_source('runners_enrichment',g); facts=factors_for(g)
    f_distance=factor_row(facts,'DISTANCE'); f_condition=factor_row(facts,'CONDITION'); f_class=factor_row(facts,'CLASS'); f_conf=factor_row(facts,'CONFIDENCE')
    f_pace=factor_row(facts,'PACE'); f_connection=factor_row(facts,'CONNECTION')
    profile_ok=any(populated(re.get(c)) for c in ['horse_archetype','profile_strength','profile_summary','career_starts','distance_profile']) or any(populated(prof.get(c)) for c in ['horse_archetype','profile_strength','profile_summary','career_starts','distance_profile'])
    profile_alt=any(populated(dna.get(c)) for c in ['dna_v6_2_score','dna_v6_2_band','distance_fit_band']) or populated(g.get('horse'))
    dna_score_ok=nz(re.get('dna_score')) or nz(dna.get('dna_v6_2_score')) or nz(dna.get('runner_dna_v6_1_score')) or nz(dna.get('dna_score'))
    dna_band_ok=meaningful(re.get('dna_band')) or meaningful(dna.get('dna_v6_2_band')) or meaningful(dna.get('runner_dna_v6_1_band')) or meaningful(dna.get('dna_band'))
    rating_ok=nz(re.get('rating_ladder_score')) or nz(g.get('total_rating_points')) or nz(cmd.get('edgeiq_score_overall_v3')) or nz(g.get('win_pct'))
    projected_ok=nz(re.get('projected_rating')) or nz(g.get('projected_rating_V6_1_RESEARCH')) or nz(g.get('projected_rating_v5_2'))
    projected_alt=False
    confidence_ok=nz(re.get('confidence_score')) or nz(ri.get('confidence_score')) or nz(dna.get('confidence_score')) or nz(f_conf.get('factor_score')) or nz(cmd.get('edgeiq_score_confidence_v3'))
    confidence_alt=nz(g.get('total_rating_points')) or nz(dna.get('dna_v6_2_score'))
    positive_ok=any(meaningful(re.get(c)) for c in ['positive_1_factor','positive_2_factor','positive_3_factor']) or any(meaningful(dna.get(c)) for c in ['positive_1_factor','positive_2_factor','positive_3_factor','strongest_factor_v6_2','strongest_factor_v6_1'])
    risk_ok=any(meaningful(re.get(c)) for c in ['negative_1_factor','negative_2_factor','negative_3_factor']) or any(meaningful(dna.get(c)) for c in ['negative_1_factor','negative_2_factor','negative_3_factor','weakest_factor_v6_2','weakest_factor_v6_1'])
    distance_ok=meaningful(re.get('distance_profile')) or meaningful(prof.get('distance_profile')) or meaningful(dna.get('distance_fit_band')) or nz(dna.get('distance_fit_score')) or nz(f_distance.get('factor_score'))
    condition_ok=meaningful(re.get('condition_profile')) or meaningful(prof.get('condition_profile')) or meaningful(dna.get('condition_fit_band')) or nz(dna.get('condition_fit_score')) or nz(f_condition.get('factor_score'))
    class_ok=meaningful(re.get('class_profile')) or meaningful(prof.get('class_profile')) or meaningful(dna.get('class_fit_band')) or nz(dna.get('class_fit_score')) or nz(f_class.get('factor_score'))
    campaign_ok=yes(re.get('campaign_available')) or yes(cmd.get('edgeiq_campaign_available_v3_3')) or meaningful(camp.get('evidence_status')) and clean(camp.get('evidence_status'))!='NO HISTORY'
    campaign_truth=clean(cmd.get('edgeiq_campaign_truth_status_v3_3') or camp.get('evidence_status'))
    campaign_true_zero='TRUE_ZERO' in campaign_truth or campaign_truth in {'NO HISTORY','NO_HISTORY'}
    traj_ok=yes(re.get('trajectory_available')) or yes(cmd.get('edgeiq_trajectory_available_v3_2')) or meaningful(traj.get('trajectory_evidence_status_v1')) and clean(traj.get('trajectory_evidence_status_v1'))!='NO_HISTORY'
    traj_truth=clean(cmd.get('edgeiq_trajectory_truth_status_v3_2') or traj.get('trajectory_evidence_status_v1'))
    traj_true_zero='TRUE_ZERO' in traj_truth or traj_truth in {'NO HISTORY','NO_HISTORY'}
    connection_ok=yes(re.get('connection_available')) or yes(cmd.get('edgeiq_connection_evidence_available_v3')) or meaningful(conn.get('connection_band')) and clean(conn.get('connection_band')) not in {'NO_EVIDENCE','NO EVIDENCE'}
    connection_truth=clean(cmd.get('edgeiq_connection_truth_status_v3') or conn.get('connection_evidence_status'))
    connection_true_zero='NO' in connection_truth and 'SOURCE' not in connection_truth
    decision_ok=populated(g.get('display_decision')) or populated(g.get('execution_action')) or populated(g.get('execution_action_final'))
    score_ok=nz(re.get('score_overall')) or nz(cmd.get('edgeiq_score_overall_v3')) or nz(g.get('total_rating_points'))
    score_alt=rating_ok or dna_score_ok
    selected_dossier_ok=profile_ok and dna_score_ok and decision_ok and score_ok
    selected_dossier_alt=False
    field_status={}
    field_status['runner_profile']=status(profile_ok, profile_alt, bool(re) or bool(prof), 'Profile feed has partial/fallback values but selected profile path can be blank.', 'No runner profile source matched.')
    field_status['DNA_score']=status(dna_score_ok, False, bool(dna), '', 'DNA score source missing.')
    field_status['DNA_band']=status(dna_band_ok, dna_score_ok, bool(dna), 'DNA score exists but band fallback can be blank.', 'DNA band source missing.')
    field_status['rating_ladder']=status(rating_ok, False, True, '', 'No rating ladder value available.')
    field_status['projected_rating']=status(projected_ok, projected_alt, True, 'Projected rating is blank, but score/probability rating proxies exist for display fallback.', 'No projected rating source available.')
    field_status['confidence']=status(confidence_ok, confidence_alt, True, 'Confidence is blank, but DNA/rating confidence proxy exists.', 'No confidence source available.')
    field_status['positive_factors']=status(positive_ok, dna_score_ok, bool(dna), 'DNA score exists but positive factor labels are missing.', 'No positive factor evidence available.')
    field_status['risk_factors']=status(risk_ok, dna_score_ok, bool(dna), 'DNA score exists but risk factor labels are missing.', 'No risk factor evidence available.')
    field_status['distance_profile']=status(distance_ok, False, bool(re) or bool(prof) or bool(dna) or bool(f_distance), '', 'No distance profile evidence available.')
    field_status['condition_profile']=status(condition_ok, False, bool(re) or bool(prof) or bool(dna) or bool(f_condition), '', 'No condition profile evidence available.')
    field_status['class_profile']=status(class_ok, False, bool(re) or bool(prof) or bool(dna) or bool(f_class), '', 'No class profile evidence available.')
    field_status['campaign']=status(campaign_ok, False, bool(camp) or bool(cmd), '', 'No campaign history available.' if campaign_true_zero else 'Campaign source missing.', campaign_true_zero)
    field_status['trajectory_history']=status(traj_ok, False, bool(traj) or bool(cmd), '', 'No trajectory/history available.' if traj_true_zero else 'Trajectory/history source missing.', traj_true_zero)
    field_status['connection_evidence']=status(connection_ok, False, bool(conn) or bool(cmd), '', 'No material connection evidence currently triggered.' if connection_true_zero else 'Connection source missing.', connection_true_zero)
    field_status['selected_runner_dossier']=status(selected_dossier_ok, selected_dossier_alt, True, 'Selected dossier has enough sources but current UI path can show blanks.', 'Selected runner dossier lacks required sources.')
    field_status['decision_engine_fields']=status(decision_ok, False, True, '', 'Decision field missing.')
    field_status['score_breakdown']=status(score_ok, score_alt, True, 'Score breakdown has rating/DNA proxy but current score path can be blank.', 'No score breakdown source available.')
    field_status['UI_fallback_rendering_fields']=('OK','RUNNERS labels and render paths are mounted.') if ui_ok else ('UI_FALLBACK_MISSING','Missing RUNNERS UI tokens: '+', '.join(k for k,v in ui_tokens.items() if not v))
    out={'race_date':g.get('race_date',''),'track':g.get('track',''),'race_no':g.get('race_no',''),'horse':g.get('horse','')}
    for name in FIELDS:
        out[f'{name}_classification']=field_status[name][0]
        out[f'{name}_reason']=field_status[name][1]
    out.update({
        'matched_runner_profile':'YES' if (re or prof) else 'NO','matched_dna':'YES' if dna else 'NO','matched_command':'YES' if cmd else 'NO','matched_trajectory':'YES' if traj else 'NO','matched_connection':'YES' if conn else 'NO','matched_campaign':'YES' if camp else 'NO','matched_form':'YES' if form else 'NO',
        'current_dna_score': first_pop(dna.get('dna_v6_2_score'),dna.get('runner_dna_v6_1_score'),dna.get('dna_score')),
        'current_projected_rating': first_pop(g.get('projected_rating_V6_1_RESEARCH'),g.get('projected_rating_v5_2')),
        'current_rating_proxy': first_pop(g.get('total_rating_points'),cmd.get('edgeiq_score_overall_v3'),g.get('win_pct')),
        'current_confidence': first_pop(ri.get('confidence_score'),f_conf.get('factor_score'),cmd.get('edgeiq_score_confidence_v3')),
    })
    rows_out.append(out)

fields=['race_date','track','race_no','horse']
for f in FIELDS: fields += [f'{f}_classification', f'{f}_reason']
fields += ['matched_runner_profile','matched_dna','matched_command','matched_trajectory','matched_connection','matched_campaign','matched_form','current_dna_score','current_projected_rating','current_rating_proxy','current_confidence']
write_csv(OUT,rows_out,fields)

race_rows=[]
for rk,members_g in sorted(race_members.items()):
    members=[r for r in rows_out if (clean(r['race_date']),clean_track(r['track']),race_no(r['race_no']))==rk]
    rec={'race_date':rk[0],'track':rk[1],'race_no':rk[2],'field_size':len(members)}
    fix=truez=srcmiss=0
    for f in FIELDS:
        counts=defaultdict(int)
        for m in members: counts[m.get(f'{f}_classification','')]+=1
        rec[f'{f}_ok_count']=counts['OK']; rec[f'{f}_fix_required_count']=sum(counts[c] for c in FIX); rec[f'{f}_true_zero_count']=counts['TRUE_ZERO']; rec[f'{f}_source_missing_count']=counts['SOURCE_MISSING']
        fix+=rec[f'{f}_fix_required_count']; truez+=counts['TRUE_ZERO']; srcmiss+=counts['SOURCE_MISSING']
    rec['fix_required_count']=fix; rec['true_zero_count']=truez; rec['source_missing_count']=srcmiss; rec['status']='FIX_REQUIRED' if fix else 'RUNNERS_SOURCE_TRACE_PASS_WITH_PROVEN_GAPS'
    race_rows.append(rec)
write_csv(RACE,race_rows,list(race_rows[0].keys()))
fix_total=sum(1 for r in rows_out for f in FIELDS if r.get(f'{f}_classification') in FIX)
status_text='RUNNERS_SOURCE_TRACE_FIX_REQUIRED' if fix_total else 'RUNNERS_SOURCE_TRACE_PASS'
summary=[]
for f in FIELDS:
    counts=defaultdict(int)
    for r in rows_out: counts[r.get(f'{f}_classification')]+=1
    summary.append(f'{f}: '+', '.join(f'{k}={v}' for k,v in sorted(counts.items())))
REPORT.write_text('\n'.join(['EDGEiQ RUNNERS Tab Source Trace V1','='*42,f'Generated: {datetime.now().isoformat(timespec="seconds")}',f'Status: {status_text}',f'Governed rows/races: {len(gov)}/{len(race_members)}',f'Fix-required classifications: {fix_total}',f'UI token presence: {ui_tokens}','','Classification counts:',*summary,'','Race statuses:',*[f'{r["track"]} R{r["race_no"]}: {r["status"]}, fix_required={r["fix_required_count"]}, source_missing={r["source_missing_count"]}, true_zero={r["true_zero_count"]}' for r in race_rows]])+'\n',encoding='utf-8')
print(status_text)
print(f'governed_rows={len(gov)}')
print(f'governed_races={len(race_members)}')
print(f'fix_required={fix_total}')



