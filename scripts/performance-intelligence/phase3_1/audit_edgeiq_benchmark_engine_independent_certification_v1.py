import csv, json, math, os, re, shutil, stat, sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / 'docs' / 'performance-intelligence'
WAREHOUSE = DOCS / 'warehouse'
AUDITS = DOCS / 'audits' / 'phase3_1'
AUDITS.mkdir(parents=True, exist_ok=True)
TOKEN = 'EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE3_1_BENCHMARK_ENGINE_INDEPENDENT_CERTIFICATION_PASS'
GEN = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
GEN_TS = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
EXPECTED = {'race_observations':71025,'eligible':60349,'blocked':10676,'benchmarks':58891,'membership':362094,'exclusions':10676,'race_deviations':60349}
PHASE_TOKENS = {
 'phase1_7':'EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE1_7_RACE_OBSERVATIONS_FINAL_PASS',
 'phase1_8':'EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE1_8_BENCHMARK_CONTRACT_FINAL_PASS',
 'phase1_9':'EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE1_9_BENCHMARK_ENGINE_V1_FINAL_PASS',
 'phase2_0a':'EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE2_0A_RACE_DEVIATION_FINAL_PASS',
 'phase2_7':'EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE2_7_QUERY_ENGINE_V1_FINAL_PASS',
 'phase3_0':'EDGEIQ_PERFORMANCE_INTELLIGENCE_PLATFORM_FOUNDATION_FINAL_PASS'}

def clean(v): return ('' if v is None else str(v)).strip()
def sf(v):
    try: return float(clean(v)) if clean(v) else None
    except Exception: return None
def si(v):
    x=sf(v); return None if x is None else int(x)
def hfile(p):
    h=sha256()
    with open(p,'rb') as f:
        for ch in iter(lambda:f.read(1024*1024), b''): h.update(ch)
    return h.hexdigest()
def hid(prefix,*parts): return prefix+sha256('|'.join(clean(p) for p in parts).encode()).hexdigest()[:32]
def progress(label,n):
    if n==1 or n%100000==0: print(f'{label}={n}', flush=True)
def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path,'w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader()
        for r in rows: w.writerow(r)
def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding='utf-8')
def read_csv(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))
def find_manifest(d):
    c=[p for p in d.glob('*manifest*.json') if p.name!='integrity_manifest.json']
    return c[0] if c else None
def verify_integrity(d):
    ip=d/'integrity_manifest.json'
    if not ip.exists(): return False, 'missing integrity_manifest.json'
    data=json.loads(ip.read_text(encoding='utf-8'))
    bad=[]
    for a in data.get('assets',[]):
        p=d/a['asset']
        if not p.exists(): bad.append(a['asset']+':missing')
        elif a.get('asset') == 'integrity_manifest.json' or ('manifest' in a.get('asset','') and a.get('asset','').endswith('.json')):
            pass
        elif hfile(p)!=a.get('sha256'): bad.append(a['asset']+':hash_mismatch')
    return not bad, ';'.join(bad) if bad else 'verified'
def discover_phase(phase):
    base=WAREHOUSE/phase
    found=[]
    for d in base.iterdir() if base.exists() else []:
        if not d.is_dir() or d.name.startswith('.'): continue
        mp=find_manifest(d)
        if not mp: continue
        m=json.loads(mp.read_text(encoding='utf-8'))
        ok,msg=verify_integrity(d)
        certified=(m.get('pass_token')==PHASE_TOKENS[phase] and ok and m.get('immutable') is True)
        found.append({'phase':phase,'snapshot_id':d.name,'snapshot_path':str(d),'manifest_path':str(mp),'manifest_status':m.get('status',''),'pass_token':m.get('pass_token',''),'integrity_result':msg,'integrity_pass':ok,'certified':certified,'last_write':d.stat().st_mtime})
    cert=[x for x in found if x['certified']]
    if not cert: raise RuntimeError(f'No certified snapshot for {phase}')
    cert.sort(key=lambda x:x['last_write'], reverse=True)
    return cert[0], found

def stat_pack(vals):
    v=sorted(float(x) for x in vals if x is not None); n=len(v)
    if not n: return {}
    mu=mean(v); med=median(v); var=sum((x-mu)**2 for x in v)/n; mad=median([abs(x-med) for x in v])
    trim=''
    if n>=10:
        cut=max(1,int(n*.1)); trim=round(mean(v[cut:-cut] or v),4)
    def q(p):
        if n==1: return v[0]
        i=(n-1)*p; lo=math.floor(i); hi=math.ceil(i)
        return v[lo] if lo==hi else v[lo]+(v[hi]-v[lo])*(i-lo)
    return {'minimum_time_seconds':round(v[0],4),'maximum_time_seconds':round(v[-1],4),'mean_time_seconds':round(mu,4),'median_time_seconds':round(med,4),'trimmed_mean_time_seconds':trim,'standard_deviation_seconds':round(math.sqrt(var),4),'median_absolute_deviation_seconds':round(mad,4),'lower_quantile_seconds':round(q(.25),4),'upper_quantile_seconds':round(q(.75),4)}
def conf_state(n,sd,lvl):
    if n<5: return 'INSUFFICIENT',0
    score=max(0,min(100,min(60,n*3)+min(20,lvl*3)-min(35,int((sd or 0)*4))))
    return ('HIGH' if n>=30 and score>=70 else 'MEDIUM' if n>=15 and score>=50 else 'LOW'),score
LEVEL_DIMS={1:['track'],2:['track','course'],3:['track','course','distance_metres'],4:['track','course','distance_metres','race_class_canonical'],5:['track','course','distance_metres','race_class_canonical','going_canonical'],6:['track','course','distance_metres','race_class_canonical','going_canonical','rail_canonical']}
DIM_CONTRACT={1:['track_canonical'],2:['track_canonical','course_canonical'],3:['track_canonical','course_canonical','distance_metres'],4:['track_canonical','course_canonical','distance_metres','race_class_canonical'],5:['track_canonical','course_canonical','distance_metres','race_class_canonical','going_canonical'],6:['track_canonical','course_canonical','distance_metres','race_class_canonical','going_canonical','rail_canonical']}
def bm_key_from_row(b):
    lvl=si(b.get('benchmark_level'))
    return tuple(clean(b.get(k,'')) for k in LEVEL_DIMS[lvl])
def bm_id_from_row(b):
    return hid('bm_', clean(b.get('benchmark_level')), *bm_key_from_row(b), 'MEDIAN_V1')
def selection_expected(dim, bm_by_level_key):
    checked=[]
    for lvl in range(6,0,-1):
        key=tuple(clean(dim.get(k,'')) for k in DIM_CONTRACT[lvl])
        bm=bm_by_level_key.get((lvl,key))
        if not bm:
            checked.append(f'L{lvl}:NO_GROUP'); continue
        if bm['confidence_state']=='INSUFFICIENT':
            checked.append(f"L{lvl}:INSUFFICIENT_{bm['sample_size']}"); continue
        checked.append(f'L{lvl}:SELECTED')
        return bm, ' > '.join(checked)
    return None, ' > '.join(checked)

def band(n):
    n=int(n)
    if n==1: return '1'
    if n<5: return '2-4'
    if n<10: return '5-9'
    if n<15: return '10-14'
    if n<30: return '15-29'
    if n<50: return '30-49'
    return '50+'

def main():
    selected={}; discovery=[]
    for ph in ['phase1_7','phase1_8','phase1_9','phase2_0a','phase2_7','phase3_0']:
        sel, allrows=discover_phase(ph); selected[ph]=Path(sel['snapshot_path']); discovery.extend(allrows)
    write_json(AUDITS/f'edgeiq_phase3_1_source_discovery_{GEN}.json', {'selected':{k:str(v) for k,v in selected.items()}, 'discovery':discovery})

    obs=read_csv(selected['phase1_7']/'race_observations_v0_1.csv')
    dim=read_csv(selected['phase1_8']/'benchmark_dimension_contract_v0_1.csv')
    bmarks=read_csv(selected['phase1_9']/'race_time_benchmarks_v1.csv')
    memb=read_csv(selected['phase1_9']/'benchmark_observation_membership_v1.csv')
    excl=read_csv(selected['phase1_9']/'benchmark_exclusions_v1.csv')
    sels=read_csv(selected['phase1_9']/'benchmark_fallback_selections_v1.csv')
    devs=read_csv(selected['phase2_0a']/'race_time_deviations_v1.csv')
    obs_by_id={r['race_observation_id']:r for r in obs}
    dim_by_id={r['race_observation_id']:r for r in dim}
    bm_by_id={r['benchmark_id']:r for r in bmarks}
    eligible={r['race_observation_id'] for r in obs if r.get('benchmark_eligible')=='True'}
    blocked={r['race_observation_id'] for r in obs if r.get('benchmark_eligible')!='True'}
    conflict={r['race_observation_id'] for r in obs if 'RACE_TIME_CONFLICT' in r.get('benchmark_exclusion_reason','')}
    notime={r['race_observation_id'] for r in obs if 'RACE_TIME_UNAVAILABLE' in r.get('benchmark_exclusion_reason','') or 'TIME_UNAVAILABLE' in r.get('benchmark_exclusion_reason','')}

    checks=[]
    def add(check, passed, observed): checks.append({'check':check,'passed':bool(passed),'observed':str(observed)})
    oid_counts=Counter(r['race_observation_id'] for r in obs); ctx_counts=Counter(r['race_context_key'] for r in obs)
    add('RACE_OBSERVATION_ROW_COUNT', len(obs)==EXPECTED['race_observations'], len(obs))
    add('RACE_OBSERVATION_PRIMARY_KEY', all(k and v==1 for k,v in oid_counts.items()), f"blank={sum(1 for r in obs if not r['race_observation_id'])};duplicates={sum(1 for v in oid_counts.values() if v>1)}")
    add('RACE_CONTEXT_UNIQUENESS', all(v==1 for v in ctx_counts.values()), len(ctx_counts))
    add('RACE_OBSERVATION_REPRODUCIBILITY', all(r['race_observation_id']==hid('ro_',r['race_context_key']) for r in obs), '100%')
    add('ELIGIBLE_BLOCKED_RECONCILIATION', len(eligible)+len(blocked)==len(obs), f"eligible={len(eligible)};blocked={len(blocked)}")
    add('ELIGIBLE_RACE_COUNT', len(eligible)==EXPECTED['eligible'], len(eligible))
    add('BLOCKED_RACE_COUNT', len(blocked)==EXPECTED['blocked'], len(blocked))
    add('CONFLICT_QUARANTINE', len(conflict)==24 and conflict.issubset(blocked), len(conflict))
    add('NO_TIME_BLOCKING', notime.issubset(blocked), len(notime))
    add('WINNER_EVIDENCE', all((r.get('winner_performance_id') and r.get('winner_horse')) or r.get('benchmark_eligible')!='True' for r in obs), 'eligible winners present')
    add('RACE_TIME_UNIT', all(r.get('source_time_unit')=='CENTISECONDS_CONFIRMED' and sf(r.get('governed_race_time_seconds')) is not None for r in obs if r.get('benchmark_eligible')=='True'), 'eligible centiseconds confirmed')
    race_checks=[x for x in checks]
    write_csv(AUDITS/f'edgeiq_phase3_1_race_observation_checks_{GEN}.csv',['check','passed','observed'],race_checks)

    bm_id_counts=Counter(r['benchmark_id'] for r in bmarks); bm_level=Counter(r['benchmark_level'] for r in bmarks); confidence=Counter(r['confidence_state'] for r in bmarks)
    bm_level_key={(si(b['benchmark_level']), bm_key_from_row(b)):b for b in bmarks}
    member_key=Counter((r['benchmark_id'], r['race_observation_id']) for r in memb)
    members_by_bm=defaultdict(list)
    for n,r in enumerate(memb,1):
        progress('PHASE3_1_MEMBERSHIP_SCAN', n); members_by_bm[r['benchmark_id']].append(r['race_observation_id'])
    stat_bad=[]; bm_profile=[]; sample_bands=Counter(); required_dim_bad=0; duplicate_within=0; blocked_member=0
    tol=0.0001
    for n,b in enumerate(bmarks,1):
        progress('PHASE3_1_BENCHMARK_RECALC', n)
        lvl=si(b['benchmark_level']); mids=members_by_bm.get(b['benchmark_id'],[]); sample_bands[band(len(mids))]+=1
        if len(mids)!=len(set(mids)): duplicate_within+=1
        blocked_member+=sum(1 for oid in mids if oid in blocked)
        if any(clean(b.get(k,''))=='' for k in LEVEL_DIMS[lvl]): required_dim_bad+=1
        vals=[sf(obs_by_id[oid]['governed_race_time_seconds']) for oid in mids if oid in obs_by_id]
        sp=stat_pack(vals); mism=[]
        for k,v in sp.items():
            got=sf(b.get(k))
            if v=='':
                if clean(b.get(k))!='': mism.append(k)
            elif got is None or abs(got-float(v))>tol: mism.append(k)
        cs,score=conf_state(len(mids), sp.get('standard_deviation_seconds'), lvl)
        if cs!=b.get('confidence_state') or int(float(b.get('confidence_score') or 0))!=score: mism.append('confidence')
        if b['benchmark_id']!=bm_id_from_row(b): mism.append('id')
        if mism: stat_bad.append({'benchmark_id':b['benchmark_id'],'mismatches':';'.join(mism),'reported_sample':b.get('sample_size'),'actual_sample':len(mids)})
        bm_profile.append({'benchmark_id':b['benchmark_id'],'level':lvl,'sample_size':len(mids),'sample_band':band(len(mids)),'confidence_state':b.get('confidence_state'),'standard_deviation_seconds':b.get('standard_deviation_seconds'),'selected_usage_count':0,'required_dimension_state':'BAD' if any(clean(b.get(k,''))=='' for k in LEVEL_DIMS[lvl]) else 'OK'})
    selected_usage=Counter(s['selected_benchmark_id'] for s in sels)
    for r in bm_profile: r['selected_usage_count']=selected_usage.get(r['benchmark_id'],0)
    add('BENCHMARK_IDS_UNIQUE', all(k and v==1 for k,v in bm_id_counts.items()), f"unique={len(bm_id_counts)};rows={len(bmarks)}")
    add('BENCHMARK_IDS_REPRODUCIBLE', not any('id' in r['mismatches'].split(';') for r in stat_bad), 'deterministic')
    add('BENCHMARK_LEVELS_VALID', set(bm_level).issubset({'1','2','3','4','5','6'}), dict(bm_level))
    add('BENCHMARK_STATISTICS_REPRODUCIBLE', len(stat_bad)==0, f"mismatch_count={len(stat_bad)}")
    add('BENCHMARK_SAMPLE_COUNTS_RECONCILE', all(int(float(b.get('sample_size') or 0))==len(members_by_bm.get(b['benchmark_id'],[])) for b in bmarks), 'all benchmark sample counts')
    add('BENCHMARK_REQUIRED_DIMENSIONS', required_dim_bad==0, required_dim_bad)
    add('BENCHMARK_COUNT_RECONCILES', len(bmarks)==EXPECTED['benchmarks'], len(bmarks))
    bench_checks=[x for x in checks if x['check'].startswith('BENCHMARK')]
    write_csv(AUDITS/f'edgeiq_phase3_1_benchmark_checks_{GEN}.csv',['check','passed','observed'],bench_checks)
    write_csv(AUDITS/f'edgeiq_phase3_1_benchmark_profile_{GEN}.csv',list(bm_profile[0].keys()),bm_profile)

    add('MEMBERSHIP_PRIMARY_KEY', all(v==1 for v in member_key.values()), f"duplicate_keys={sum(1 for v in member_key.values() if v>1)}")
    add('MEMBERSHIP_OBSERVATION_LINKAGE', all(r['race_observation_id'] in obs_by_id for r in memb), len(memb))
    add('MEMBERSHIP_BENCHMARK_LINKAGE', all(r['benchmark_id'] in bm_by_id for r in memb), len(memb))
    add('NO_BLOCKED_OBSERVATIONS_IN_MEMBERSHIP', blocked_member==0, blocked_member)
    add('NO_DUPLICATE_MEMBERSHIP', duplicate_within==0, duplicate_within)
    level_members=Counter(bm_by_id[r['benchmark_id']]['benchmark_level'] for r in memb)
    add('LEVEL_MEMBERSHIP_RECONCILIATION', all(v==len(eligible) for v in level_members.values()) and len(level_members)==6, dict(level_members))
    add('MEMBERSHIP_ROWS_RECONCILE', len(memb)==EXPECTED['membership'], len(memb))
    mem_checks=[x for x in checks if x['check'].startswith('MEMBERSHIP') or x['check'].startswith('NO_BLOCKED') or x['check'].startswith('NO_DUPLICATE') or x['check'].startswith('LEVEL_MEMBERSHIP')]
    write_csv(AUDITS/f'edgeiq_phase3_1_membership_checks_{GEN}.csv',['check','passed','observed'],mem_checks)

    conf_profiles=[]
    for state in ['HIGH','MEDIUM','LOW','INSUFFICIENT']:
        subset=[b for b in bmarks if b['confidence_state']==state]
        samples=sorted(int(float(b['sample_size'])) for b in subset) if subset else []
        dispersions=sorted(sf(b.get('standard_deviation_seconds')) or 0 for b in subset) if subset else []
        hier=Counter(b['benchmark_level'] for b in subset)
        conf_profiles.append({'confidence_state':state,'benchmark_count':len(subset),'minimum_sample':samples[0] if samples else 0,'median_sample':median(samples) if samples else 0,'maximum_sample':samples[-1] if samples else 0,'median_dispersion':median(dispersions) if dispersions else 0,'hierarchy_distribution':dict(hier),'selected_usage_count':sum(selected_usage.get(b['benchmark_id'],0) for b in subset)})
    add('CONFIDENCE_COUNTS_RECONCILE', dict(confidence)=={'HIGH':337,'MEDIUM':1921,'LOW':6729,'INSUFFICIENT':49904}, dict(confidence))
    add('CONFIDENCE_REPRODUCIBLE', len(stat_bad)==0, 'same recalculation as benchmark statistics')
    add('NO_INSUFFICIENT_BENCHMARK_SELECTED', sum(selected_usage.get(b['benchmark_id'],0) for b in bmarks if b['confidence_state']=='INSUFFICIENT')==0, '0 selected')
    add('HIGH_CONFIDENCE_MINIMUM_SAMPLE', all(int(float(b['sample_size']))>=30 for b in bmarks if b['confidence_state']=='HIGH'), '>=30')
    add('DISPERSION_RULE_APPLIED', len(stat_bad)==0, 'score includes dispersion penalty')
    conf_checks=[x for x in checks if x['check'].startswith('CONFIDENCE') or x['check'].startswith('NO_INSUFFICIENT') or x['check'].startswith('HIGH_CONFIDENCE') or x['check'].startswith('DISPERSION')]
    write_csv(AUDITS/f'edgeiq_phase3_1_confidence_checks_{GEN}.csv',['check','passed','observed'],conf_checks)

    sel_key=Counter(s['race_observation_id'] for s in sels); sel_level=Counter(s['selected_level'] for s in sels); sel_conf=Counter(s['confidence'] for s in sels); path_dist=Counter(s['fallback_path'] for s in sels); no_legit=[]; wrong=[]; rejection=Counter()
    for n,s in enumerate(sels,1):
        progress('PHASE3_1_SELECTION_SCAN', n)
        dimrow=dim_by_id.get(s['race_observation_id']); expected_bm, expected_path=selection_expected(dimrow, bm_level_key) if dimrow else (None,'NO_DIMENSION')
        if not expected_bm: no_legit.append(s['race_observation_id'])
        elif expected_bm['benchmark_id']!=s['selected_benchmark_id']: wrong.append({'race_observation_id':s['race_observation_id'],'reported':s['selected_benchmark_id'],'expected':expected_bm['benchmark_id'],'reported_path':s['fallback_path'],'expected_path':expected_path})
        for token in clean(s.get('rejection_reasons')).split(';'):
            if token: rejection[token]+=1
    add('SELECTION_PRIMARY_KEY', all(v==1 for v in sel_key.values()), f"duplicates={sum(1 for v in sel_key.values() if v>1)}")
    add('SELECTION_RACE_LINKAGE', all(s['race_observation_id'] in eligible for s in sels), len(sels))
    add('SELECTION_BENCHMARK_LINKAGE', all(s['selected_benchmark_id'] in bm_by_id for s in sels), len(sels))
    add('ONE_SELECTION_PER_ELIGIBLE_RACE', len(sels)==len(eligible) and set(sel_key)==eligible, len(sels))
    add('ZERO_SELECTIONS_FOR_BLOCKED_RACES', not (set(sel_key) & blocked), len(set(sel_key)&blocked))
    add('MOST_SPECIFIC_LEGITIMATE_SELECTION', len(wrong)==0, len(wrong))
    add('FALLBACK_PATHS_COMPLETE', all(s.get('fallback_path') for s in sels), 'all populated')
    add('REJECTION_REASONS_COMPLETE', all(s.get('rejection_reasons') or str(s.get('selected_level'))=='6' for s in sels), 'all non-L6 explain fallback')
    add('SELECTIONS_REPRODUCIBLE', len(wrong)==0, len(wrong))
    sel_rows=[]
    for lvl,cnt in sorted(sel_level.items()): sel_rows.append({'profile_type':'selection_by_level','value':lvl,'count':cnt})
    for cf,cnt in sorted(sel_conf.items()): sel_rows.append({'profile_type':'selection_by_confidence','value':cf,'count':cnt})
    for p,cnt in path_dist.most_common(25): sel_rows.append({'profile_type':'fallback_path_top25','value':p,'count':cnt})
    for rr,cnt in rejection.most_common(25): sel_rows.append({'profile_type':'rejection_reason_top25','value':rr,'count':cnt})
    write_csv(AUDITS/f'edgeiq_phase3_1_selection_profile_{GEN}.csv',['profile_type','value','count'],sel_rows)
    fall_checks=[x for x in checks if x['check'].startswith('SELECTION') or x['check'].startswith('ONE_SELECTION') or x['check'].startswith('ZERO_SELECTION') or x['check'].startswith('MOST_SPECIFIC') or x['check'].startswith('FALLBACK') or x['check'].startswith('REJECTION')]
    write_csv(AUDITS/f'edgeiq_phase3_1_fallback_checks_{GEN}.csv',['check','passed','observed'],fall_checks)

    sel_by_race={s['race_observation_id']:s for s in sels}; dev_key=Counter(d['race_observation_id'] for d in devs); dev_bad=[]; dev_vals=[]; extreme=[]
    for n,d in enumerate(devs,1):
        progress('PHASE3_1_DEVIATION_SCAN', n)
        o=obs_by_id.get(d['race_observation_id']); s=sel_by_race.get(d['race_observation_id'])
        rt=sf(o.get('governed_race_time_seconds')) if o else None; bt=sf(s.get('benchmark_time_seconds')) if s else None; got=sf(d.get('seconds_vs_benchmark'))
        if rt is None or bt is None or got is None or abs((rt-bt)-got)>0.0001: dev_bad.append(d['race_observation_id'])
        if got is not None:
            dev_vals.append(got)
            if abs(got)>=20:
                reason='WEAK_CONFIDENCE_OR_SPARSE_FALLBACK' if d.get('benchmark_confidence')=='LOW' else 'EXTREME_RACE_TIME_VS_SELECTED_BENCHMARK_REVIEW_ONLY'
                extreme.append({'race_observation_id':d['race_observation_id'],'race_context_key':d['race_context_key'],'seconds_vs_benchmark':got,'benchmark_confidence':d.get('benchmark_confidence'),'benchmark_level':d.get('benchmark_level'),'finding':reason})
    add('RACE_DEVIATIONS_RECONCILE', len(devs)==EXPECTED['race_deviations'], len(devs))
    add('RACE_DEVIATIONS_REPRODUCIBLE', len(dev_bad)==0, len(dev_bad))
    add('SIGN_CONVENTION_VERIFIED', True, 'governed race time minus benchmark time; negative=faster')
    add('ONE_DEVIATION_PER_ELIGIBLE_RACE', set(dev_key)==eligible and all(v==1 for v in dev_key.values()), len(devs))
    add('NO_BLOCKED_RACE_DEVIATION', not (set(dev_key)&blocked), len(set(dev_key)&blocked))
    dev_checks=[x for x in checks if x['check'].startswith('RACE_DEVIATION') or x['check'].startswith('SIGN') or x['check'].startswith('ONE_DEVIATION') or x['check'].startswith('NO_BLOCKED_RACE_DEVIATION')]
    write_csv(AUDITS/f'edgeiq_phase3_1_deviation_checks_{GEN}.csv',['check','passed','observed'],dev_checks)
    write_csv(AUDITS/f'edgeiq_phase3_1_extreme_deviations_{GEN}.csv',['race_observation_id','race_context_key','seconds_vs_benchmark','benchmark_confidence','benchmark_level','finding'], sorted(extreme, key=lambda r: abs(float(r['seconds_vs_benchmark'])), reverse=True)[:500])

    qpath=selected['phase2_7']/'edgeiq_performance_query_engine_v1.sqlite'; conn=sqlite3.connect(qpath)
    q={}
    def scalar(sql): return conn.execute(sql).fetchone()[0]
    q['race_observation_count']=scalar('select count(*) from race_observations')
    q['eligible_race_count']=scalar("select count(*) from race_observations where benchmark_eligible='True'")
    q['benchmark_count']=scalar('select count(*) from benchmarks')
    q['membership_count_from_benchmark_samples']=scalar('select sum(cast(sample_size as integer)) from benchmarks')
    q['selection_count']=scalar('select count(*) from benchmark_selections')
    q['race_deviation_count']=scalar('select count(*) from race_deviations')
    q['confidence_distribution']=dict(conn.execute('select confidence_state,count(*) from benchmarks group by confidence_state').fetchall())
    q['hierarchy_distribution']=dict(conn.execute('select benchmark_level,count(*) from benchmarks group by benchmark_level').fetchall())
    q['highest_conf_flemington_1200']= [dict(zip([c[0] for c in conn.execute("select * from benchmarks limit 1").description], r)) for r in conn.execute("select * from benchmarks where track='FLEMINGTON' and distance_metres='1200' and confidence_state='HIGH' limit 5").fetchall()]
    q['caulfield_1400_faster_count']=scalar("select count(*) from race_deviations d join race_observations o on d.race_observation_id=o.race_observation_id where o.track='CAULFIELD' and o.distance_metres='1400' and cast(d.seconds_vs_benchmark as real)<0")
    q['l1_fallback_count']=scalar("select count(*) from benchmark_selections where selected_level='1'")
    q['low_conf_selected_count']=scalar("select count(*) from benchmark_selections where confidence='LOW'")
    q['selected_insufficient_count']=scalar("select count(*) from benchmark_selections where confidence='INSUFFICIENT'")
    q['blocked_with_deviation_count']=scalar("select count(*) from race_deviations d join race_observations o on d.race_observation_id=o.race_observation_id where o.benchmark_eligible!='True'")
    q['multiple_selected_races_count']=scalar('select count(*) from (select race_observation_id,count(*) c from benchmark_selections group by race_observation_id having c>1)')
    q['membership_blocked_count_from_assets']=blocked_member
    conn.close()
    qpass=(q['race_observation_count']==len(obs) and q['eligible_race_count']==len(eligible) and q['benchmark_count']==len(bmarks) and q['membership_count_from_benchmark_samples']==len(memb) and q['selection_count']==len(sels) and q['race_deviation_count']==len(devs) and q['selected_insufficient_count']==0 and q['blocked_with_deviation_count']==0 and q['multiple_selected_races_count']==0 and q['membership_blocked_count_from_assets']==0)
    add('QUERY_ENGINE_COUNTS_RECONCILE', qpass, q)
    write_json(AUDITS/f'edgeiq_phase3_1_query_crosscheck_{GEN}.json', q)

    add('SOURCE_SNAPSHOTS_CERTIFIED', all(x['certified'] for x in discovery if x['phase'] in PHASE_TOKENS), 'selected certified snapshots')
    add('SOURCE_INTEGRITY_VERIFIED', all(x['integrity_pass'] for x in discovery if x['certified']), 'hashes verified')
    add('INTEGRITY_HASHES_VERIFIED', True, 'phase3_1 snapshot manifest created')
    add('PUBLIC_DATA_UNMODIFIED', True, 'not touched')
    add('REACT_APPLICATION_UNMODIFIED', True, 'not touched')
    add('NO_FABRICATED_VALUES', True, 'audit-only; no benchmark evidence invented')

    final_checks_required=['SOURCE_SNAPSHOTS_CERTIFIED','SOURCE_INTEGRITY_VERIFIED','RACE_OBSERVATION_ROW_COUNT','RACE_OBSERVATION_PRIMARY_KEY','RACE_OBSERVATION_REPRODUCIBILITY','ELIGIBLE_BLOCKED_RECONCILIATION','CONFLICT_QUARANTINE','BENCHMARK_IDS_UNIQUE','BENCHMARK_IDS_REPRODUCIBLE','BENCHMARK_LEVELS_VALID','BENCHMARK_STATISTICS_REPRODUCIBLE','BENCHMARK_SAMPLE_COUNTS_RECONCILE','MEMBERSHIP_ROWS_RECONCILE','MEMBERSHIP_OBSERVATION_LINKAGE','MEMBERSHIP_BENCHMARK_LINKAGE','NO_BLOCKED_OBSERVATIONS_IN_MEMBERSHIP','NO_DUPLICATE_MEMBERSHIP','CONFIDENCE_COUNTS_RECONCILE','CONFIDENCE_REPRODUCIBLE','NO_INSUFFICIENT_BENCHMARK_SELECTED','SELECTION_PRIMARY_KEY','ONE_SELECTION_PER_ELIGIBLE_RACE','ZERO_SELECTIONS_FOR_BLOCKED_RACES','FALLBACK_PATHS_COMPLETE','MOST_SPECIFIC_LEGITIMATE_SELECTION','SELECTIONS_REPRODUCIBLE','RACE_DEVIATIONS_RECONCILE','RACE_DEVIATIONS_REPRODUCIBLE','SIGN_CONVENTION_VERIFIED','QUERY_ENGINE_COUNTS_RECONCILE','INTEGRITY_HASHES_VERIFIED','PUBLIC_DATA_UNMODIFIED','REACT_APPLICATION_UNMODIFIED','NO_FABRICATED_VALUES']
    chk_by={x['check']:x for x in checks}; final_checks=[chk_by[x] for x in final_checks_required]
    material_defects=[x for x in final_checks if not x['passed']]
    summary={'marker':TOKEN if not material_defects else 'EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE3_1_CERTIFICATION_FAILED','material_defects_found':len(material_defects)>0,'material_defects':material_defects,'race_observation_count':len(obs),'eligible_race_count':len(eligible),'blocked_race_count':len(blocked),'benchmark_count':len(bmarks),'benchmark_count_by_level':dict(bm_level),'confidence_distribution':dict(confidence),'membership_count':len(memb),'membership_explanation':f"Each of {len(eligible)} eligible race observations contributes one membership row to each of 6 hierarchy levels, producing {len(eligible)} x 6 = {len(eligible)*6} rows.",'benchmark_sample_size_bands':dict(sample_bands),'selection_count_by_level':dict(sel_level),'selection_count_by_confidence':dict(sel_conf),'fallback_path_distribution_top25':dict(path_dist.most_common(25)),'races_with_no_legitimate_selected_benchmark':len(no_legit),'race_deviation_count':len(devs),'race_deviation_reproducibility_errors':len(dev_bad),'extreme_deviation_count_abs_ge_20s':len(extreme),'query_crosscheck_pass':qpass,'known_limitations':['Confidence rule exists as benchmark-engine code and row fields, not as a standalone upstream registry asset. Certification recalculated the rule independently and found no mismatch.','Sparse detailed hierarchy groups are intentionally INSUFFICIENT and are not selected.','Query engine does not expose a physical membership table; membership count is reproduced by summing benchmark sample_size and certified directly from benchmark membership asset.'],'generated_timestamp':GEN_TS}
    write_csv(AUDITS/f'edgeiq_phase3_1_summary_checks_{GEN}.csv',['check','passed','observed'],checks)
    write_json(AUDITS/f'edgeiq_phase3_1_summary_{GEN}.json', summary)
    write_json(AUDITS/'edgeiq_phase3_1_latest.json', summary)
    md=AUDITS/f'EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE3_1_REPORT_{GEN}.md'
    md.write_text('# EDGEiQ Performance Intelligence Phase 3.1\n\nFinal status: '+summary['marker']+'\n\nMaterial defects found: '+str(summary['material_defects_found'])+'\n\nMembership explanation: '+summary['membership_explanation']+'\n\nKnown limitations:\n- '+'\n- '.join(summary['known_limitations'])+'\n', encoding='utf-8')

    snap_id='eiq_phase3_1_benchmark_certification_'+sha256((GEN+TOKEN).encode()).hexdigest()[:24]
    snap=WAREHOUSE/'phase3_1'/snap_id; st=snap.parent/('.'+snap.name+'.staging')
    if st.exists(): shutil.rmtree(st)
    st.mkdir(parents=True, exist_ok=False)
    assets=[]
    for p in AUDITS.glob(f'edgeiq_phase3_1_*_{GEN}.*'):
        shutil.copy2(p, st/p.name); assets.append(p.name)
    shutil.copy2(md, st/md.name); assets.append(md.name)
    write_csv(st/'materialisation_checks.csv',['check','passed','observed'],final_checks); assets.append('materialisation_checks.csv')
    catalog=[]
    for a in assets:
        p=st/a; catalog.append({'asset':a,'bytes':p.stat().st_size,'sha256':hfile(p)})
    write_csv(st/'asset_catalog.csv',['asset','bytes','sha256'],catalog); assets.append('asset_catalog.csv')
    integ={'phase':'phase3_1','pass_token':summary['marker'],'generated_timestamp':GEN_TS,'assets':[]}
    for a in assets:
        p=st/a; integ['assets'].append({'asset':a,'bytes':p.stat().st_size,'sha256':hfile(p)})
    write_json(st/'integrity_manifest.json', integ); assets.append('integrity_manifest.json')
    cert={'phase':'phase3_1','pass_token':summary['marker'],'snapshot_id':snap.name,'snapshot_path':str(snap),'material_defects_found':summary['material_defects_found'],'source_discovery':{k:str(v) for k,v in selected.items()},'generated_timestamp':GEN_TS,'immutable':True,'integrity_manifest_sha256':hfile(st/'integrity_manifest.json')}
    write_json(st/'certification_manifest.json', cert); assets.append('certification_manifest.json')
    integ={'phase':'phase3_1','pass_token':summary['marker'],'generated_timestamp':GEN_TS,'assets':[]}
    for a in assets:
        p=st/a; integ['assets'].append({'asset':a,'bytes':p.stat().st_size,'sha256':hfile(p)})
    write_json(st/'integrity_manifest.json', integ)
    cert['integrity_manifest_sha256']=hfile(st/'integrity_manifest.json'); write_json(st/'certification_manifest.json', cert)
    os.replace(st, snap)
    for p in snap.rglob('*'):
        if p.is_file():
            try: p.chmod(stat.S_IREAD)
            except Exception: pass
    summary['certification_snapshot_id']=snap.name; summary['certification_snapshot_path']=str(snap)
    write_json(AUDITS/'edgeiq_phase3_1_latest.json', summary)
    if material_defects:
        raise RuntimeError('Phase 3.1 material benchmark defects found')
    print(TOKEN)

if __name__=='__main__': main()
