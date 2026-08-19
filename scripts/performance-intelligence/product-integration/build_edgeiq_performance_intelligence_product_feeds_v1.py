
import csv, json, re, sqlite3, hashlib
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
DOCS=ROOT/'docs'/'performance-intelligence'
INTEG=DOCS/'integration'; AUD=INTEG/'audits'; PUB=ROOT/'public'/'performance-intelligence'
P31=DOCS/'audits'/'phase3_1'/'edgeiq_phase3_1_latest.json'
FOUND=DOCS/'audits'/'post_phase1_6_1'/'edgeiq_performance_intelligence_platform_foundation_final_report_latest.json'
CAT=ROOT/'public'/'data'/'edgeiq_three_day_product_catalog_v1.json'
TOKEN='EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE4_0_PRODUCT_FEEDS_PASS'
UNSUPPORTED=['runner_adjusted_time_seconds','runner_seconds_vs_benchmark','runner_lengths_vs_benchmark','official_sectional_time','sectional_benchmark_seconds','sectional_deviation_lengths']
CONF={'HIGH':3,'MEDIUM':2,'LOW':1,'INSUFFICIENT':0,'':0}
def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def j(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def txt(v):
    if v is None: return ''
    s=str(v).strip()
    return '' if (not s or s.lower() in {'none','null','nan','na','n/a','-'}) else re.sub(r'\s+',' ',s)
def key(v): return re.sub(r'[^A-Z0-9]+','',txt(v).upper().replace('&','AND').replace("'",''))
def code(v):
    s=txt(v)
    if s.endswith('.0'): s=s[:-2]
    return re.sub(r'[^A-Za-z0-9]+','',s)
def num(v):
    m=re.search(r'\d+(?:\.\d+)?',txt(v).replace(',',''))
    return m.group(0) if m else ''
def inum(v):
    try: return str(int(float(num(v)))) if num(v) else ''
    except Exception: return ''
def cond(v):
    s=txt(v).upper()
    for x in ['HEAVY','SOFT','GOOD','FIRM']:
        if x in s: return x
    return 'SYNTHETIC' if 'SYNTH' in s else key(s)
def cls(v):
    s=txt(v).upper().replace('BENCHMARK','BM')
    if 'MAIDEN' in s or s in {'MDN','MDN-SW'}: return 'MAIDEN'
    m=re.search(r'BM\s*(\d+)',s)
    return 'BM'+m.group(1) if m else re.sub(r'[^A-Z0-9]+','_',s).strip('_')
def first(*vals):
    for v in vals:
        s=txt(v)
        if s: return s
    return ''
def fnum(v):
    try: return float(txt(v).replace(',',''))
    except Exception: return None
def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as fh:
        for b in iter(lambda:fh.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def qin(con, sql, vals):
    vals=list(vals); out=[]
    for i in range(0,len(vals),500):
        part=vals[i:i+500]
        if part: out += con.execute(sql+' ('+','.join('?' for _ in part)+')',part).fetchall()
    return out
def row(row, keys): return {k:txt(row[k]) for k in keys}
def verify():
    p31=j(P31); f=j(FOUND)
    if p31.get('marker')!='EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE3_1_BENCHMARK_ENGINE_INDEPENDENT_CERTIFICATION_PASS': raise SystemExit('Phase 3.1 not PASS')
    if f.get('overall_final_status')!='EDGEIQ_PERFORMANCE_INTELLIGENCE_PLATFORM_FOUNDATION_FINAL_PASS': raise SystemExit('Foundation not PASS')
    return p31,f
def current(cat):
    races=[]; runners=[]
    for m in cat.get('meetings',[]):
        for r in m.get('races',[]):
            rk=txt(r.get('raceKey'))
            if not rk: continue
            rs=r.get('source') or {}; ms=m.get('source') or {}
            races.append({'meeting_key':txt(m.get('meetingKey')),'meeting':txt(m.get('meeting')),'race_context_key':rk,'race_date':txt(m.get('date')),'state':txt(ms.get('state') or rs.get('state')),'track':txt(m.get('meeting')),'race_number':inum(r.get('raceNumber')),'race_name':txt(r.get('raceName')),'distance_metres':inum(r.get('distance')),'race_class':txt(r.get('raceClass')),'track_condition':txt(r.get('trackCondition') or m.get('trackCondition')),'track_rating':inum(r.get('trackCondition') or m.get('trackCondition')),'rail_position':txt(r.get('rail') or m.get('rail')),'runner_count':str(len(r.get('runners',[])))})
            for ru in r.get('runners',[]):
                o=ru.get('official') or {}; s=ru.get('source') or {}; hn=first(o.get('runner'),s.get('horseName'),s.get('runnerName'))
                runners.append({'race_context_key':rk,'meeting_key':txt(m.get('meetingKey')),'race_date':txt(m.get('date')),'track':txt(m.get('meeting')),'race_number':inum(r.get('raceNumber')),'runner_number':inum(o.get('no') or o.get('number') or s.get('raceEntryNumber')),'horse_code':code(first(s.get('horseCode'),s.get('id'),s.get('runnerId'))),'horse_name':hn,'horse_name_key':key(hn),'trainer':first(o.get('trainer'),s.get('trainerName')),'jockey':first(o.get('jockey'),s.get('jockeyName')),'barrier':inum(o.get('barrier') or s.get('barrierNumber')),'weight':first(o.get('weight'),s.get('weight')),'market':txt(o.get('market'))})
    return races,runners
def best_bm(con,race):
    tr=txt(race.get('track')).upper(); dist=inum(race.get('distance_metres')); rc=cls(race.get('race_class')); go=cond(race.get('track_condition'))
    if not tr: return None
    rows=con.execute('select * from benchmarks where upper(track)=? and distance_metres=?',[tr,dist]).fetchall() if dist else []
    if not rows: rows=con.execute('select * from benchmarks where upper(track)=?',[tr]).fetchall()
    if not rows: return None
    def score(r): return (CONF.get(txt(r['confidence_state']).upper(),0),(1 if rc and cls(r['race_class_canonical'])==rc else 0)+(1 if go and cond(r['going_canonical'])==go else 0),int(fnum(r['benchmark_level']) or 0),int(fnum(r['sample_size']) or 0))
    return sorted(rows,key=score,reverse=True)[0]
def bm_summary(r):
    keys=['benchmark_id','benchmark_level','hierarchy_dimensions','track','course','distance_metres','race_class_canonical','going_canonical','rail_canonical','sample_size','eligible_sample_size','excluded_sample_size','mean_time_seconds','median_time_seconds','trimmed_mean_time_seconds','standard_deviation_seconds','median_absolute_deviation_seconds','lower_quantile_seconds','upper_quantile_seconds','confidence_state','confidence_score','minimum_sample_rule','benchmark_version','source_snapshot_id','generated_timestamp']
    return row(r,keys)
def build_races(con,races,srcids,gen):
    out=[]; ids=set()
    for r in races:
        b=best_bm(con,r); bid=txt(b['benchmark_id']) if b else ''
        if bid: ids.add(bid)
        out.append({**r,'race_quality_state':'HISTORICAL_BENCHMARK_CONTEXT' if b else 'BENCHMARK_UNAVAILABLE','governed_race_time_seconds':'','selected_benchmark_id':bid,'selected_benchmark_level':txt(b['benchmark_level']) if b else '','selected_benchmark_confidence':txt(b['confidence_state']) if b else 'BENCHMARK_UNAVAILABLE','selected_benchmark_sample_size':txt(b['sample_size']) if b else '','benchmark_time_seconds':txt(b['median_time_seconds']) if b else '','seconds_vs_benchmark':'','fallback_path':'Historical benchmark context for current product race; post-race deviation unavailable until official result exists.','fingerprint_pattern':'INSUFFICIENT SECTIONAL EVIDENCE','fingerprint_quality_state':'RACE_NOT_COMPLETED_IN_CURRENT_PRODUCT_CONTEXT','source_snapshot_ids':srcids,'generated_timestamp':gen,'provenance':{'scope':'RACE_BENCHMARK_CONTEXT','calculation_owner':'certified_performance_intelligence_backend','display_owner':'React service/UI'}})
    return out,ids
def horses(con,runners,gen):
    codes=sorted({r['horse_code'] for r in runners if r.get('horse_code')}); names=sorted({r['horse_name_key'] for r in runners if r.get('horse_name_key')})
    byc={code(r['historical_horse_code']):r for r in qin(con,"select * from horse_profiles where replace(historical_horse_code,'.0','') in",codes)}
    byn={key(r['horse_name']):r for r in qin(con,"select * from horse_profiles where upper(replace(horse_name,' ','')) in",names)}
    out=[]
    for ru in runners:
        r=byc.get(ru['horse_code']) or byn.get(ru['horse_name_key'])
        if r:
            out.append({'race_context_key':ru['race_context_key'],'runner_number':ru['runner_number'],'horse_identity_evidence_id':txt(r['horse_identity_evidence_id']),'horse_code':code(r['historical_horse_code']),'horse_name':txt(r['horse_name']),'identity_quality_state':txt(r['identity_quality_state']),'profile_quality_state':txt(r['profile_quality_state']),'performance_count':txt(r['performance_count']),'eligible_performance_count':txt(r['eligible_performance_count']),'date_range':txt(r['date_range']),'track_profile':txt(r['track_profile']),'distance_profile':txt(r['distance_profile']),'going_profile':txt(r['going_profile']),'class_profile':txt(r['class_profile']),'pressure_profile':txt(r['pressure_profile']),'acceleration_profile':txt(r['acceleration_profile']),'late_speed_profile':txt(r['late_speed_profile']),'efficiency_profile':txt(r['efficiency_profile']),'consistency_profile':txt(r['consistency_profile']),'track_affinity':txt(r['track_affinity']),'distance_affinity':txt(r['distance_affinity']),'pattern_distribution':txt(r['pattern_distribution']),'quality_distribution':txt(r['quality_state_distribution']),'source_snapshot_ids':[],'generated_timestamp':gen})
        else:
            out.append({'race_context_key':ru['race_context_key'],'runner_number':ru['runner_number'],'horse_identity_evidence_id':'','horse_code':ru['horse_code'],'horse_name':ru['horse_name'],'identity_quality_state':'UNMATCHED_CURRENT_RUNNER','profile_quality_state':'INSUFFICIENT_EVIDENCE','performance_count':'0','eligible_performance_count':'0','date_range':'','track_profile':'','distance_profile':'','going_profile':'','class_profile':'','pressure_profile':'UNAVAILABLE_SECTIONAL_OR_MAP_REQUIRED','acceleration_profile':'UNAVAILABLE_SECTIONAL_REQUIRED','late_speed_profile':'UNAVAILABLE_SECTIONAL_REQUIRED','efficiency_profile':'UNAVAILABLE','consistency_profile':'','track_affinity':'','distance_affinity':'','pattern_distribution':'','quality_distribution':'','source_snapshot_ids':[],'generated_timestamp':gen})
    return out
def scan_facts(facts,runners):
    codes={r['horse_code'] for r in runners if r['horse_code']}; names={r['horse_name_key'] for r in runners if r['horse_name_key']}; found=defaultdict(list)
    with facts.open(encoding='utf-8-sig',newline='') as fh:
        for r in csv.DictReader(fh):
            c=code(r.get('horse_code')); n=key(r.get('horse')); ids=[]
            if c in codes: ids.append('code:'+c)
            if n in names: ids.append('name:'+n)
            if not ids: continue
            item={'performance_fact_id':txt(r.get('performance_fact_id')),'legacy_performance_fact_id':txt(r.get('legacy_performance_fact_id')),'race_context_key':txt(r.get('race_context_key')),'race_date':txt(r.get('race_date')),'track':txt(r.get('track')),'state':txt(r.get('state')),'race_number':inum(r.get('race_number')),'race_name':txt(r.get('race_name')),'race_class':txt(r.get('race_class')),'distance_metres':inum(r.get('distance_metres')),'track_condition':txt(r.get('track_condition')),'track_rating':txt(r.get('track_rating')),'rail_position':txt(r.get('rail_position')),'horse':txt(r.get('horse')),'horse_code':c,'trainer':txt(r.get('trainer')),'jockey':txt(r.get('jockey')),'barrier':inum(r.get('barrier')),'weight':txt(r.get('weight')),'finish_position':inum(r.get('finish_position')),'margin_raw':txt(r.get('margin_raw')),'margin_lengths_raw':txt(r.get('margin_lengths')),'starting_price':txt(r.get('starting_price')),'governed_race_time_seconds':txt(r.get('governed_time_seconds') or r.get('race_time_governed_seconds')),'performance_quality_state':txt(r.get('quality_state')),'benchmark_exclusion_reason':txt(r.get('benchmark_exclusion_reason')),'source_snapshot_ids':[]}
            for ident in set(ids): found[ident].append(item)
    for k,v in found.items(): v.sort(key=lambda x:x.get('race_date',''),reverse=True); found[k]=v[:8]
    return found
def enrich(con,runners,found):
    rks=sorted({x['race_context_key'] for v in found.values() for x in v if x.get('race_context_key')})
    dev={r['race_context_key']:r for r in qin(con,'select * from race_deviations where race_context_key in',rks)}
    sel={r['race_context_key']:r for r in qin(con,'select * from benchmark_selections where race_context_key in',rks)}
    fp={r['race_context_key']:r for r in qin(con,'select * from fingerprints where race_context_key in',rks)}
    out=[]; bids=set(); seen=set()
    for ru in runners:
        vals=[]
        for ident in ['code:'+ru['horse_code'],'name:'+ru['horse_name_key']]: vals += found.get(ident,[])
        vals.sort(key=lambda x:x.get('race_date',''),reverse=True)
        for x in vals[:8]:
            k=(ru['race_context_key'],ru['runner_number'],x['performance_fact_id'])
            if k in seen: continue
            seen.add(k); rk=x['race_context_key']; d=dev.get(rk); s=sel.get(rk); f=fp.get(rk); bid=txt(d['selected_benchmark_id'] if d else s['selected_benchmark_id'] if s else '')
            if bid: bids.add(bid)
            out.append({'current_race_context_key':ru['race_context_key'],'runner_number':ru['runner_number'],**x,'selected_benchmark_id':bid,'benchmark_level':txt(d['benchmark_level'] if d else s['selected_level'] if s else ''),'benchmark_confidence':txt(d['benchmark_confidence'] if d else s['confidence'] if s else 'BENCHMARK_UNAVAILABLE'),'benchmark_sample_size':txt(d['benchmark_sample_size'] if d else s['sample_size'] if s else ''),'benchmark_time_seconds':txt(d['benchmark_time_seconds'] if d else s['benchmark_time_seconds'] if s else ''),'race_seconds_vs_benchmark':txt(d['seconds_vs_benchmark'] if d else ''),'fallback_path':txt(d['fallback_path'] if d else s['fallback_path'] if s else ''),'fingerprint_pattern':txt(f['primary_pattern'] if f else 'INSUFFICIENT_SECTIONAL_EVIDENCE'),'fingerprint_quality_state':txt(f['quality_state'] if f else 'INSUFFICIENT_EVIDENCE')})
    return out,bids
def main():
    gen=now(); p31,foundn=verify(); snaps=foundn['snapshots']; srcids=[p31['certification_snapshot_id'],snaps['phase1_9']['snapshot_id'],snaps['phase2_0a']['snapshot_id'],snaps['phase2_5']['snapshot_id'],snaps['phase2_6']['snapshot_id']]
    db=Path(snaps['phase2_7']['snapshot_path'])/'edgeiq_performance_query_engine_v1.sqlite'; facts=ROOT/'docs'/'performance-intelligence'/'warehouse'/'performance-facts-corrected'/snaps['phase1_7']['manifest']['source_snapshot_id']/'canonical_performance_facts_v0_2.csv'
    cat=j(CAT); races,runners=current(cat); con=sqlite3.connect(db); con.row_factory=sqlite3.Row
    try:
        race_idx,b1=build_races(con,races,srcids,gen); horse_idx=horses(con,runners,gen); recent=scan_facts(facts,runners); hist_idx,b2=enrich(con,runners,recent)
        bidset=b1|b2; bench=[bm_summary(r) for r in qin(con,'select * from benchmarks where benchmark_id in',sorted(bidset))]
        existing={b['benchmark_id'] for b in bench}
        for tr in sorted({txt(r['track']).upper() for r in races if txt(r.get('track'))}):
            for r in con.execute('select * from benchmarks where upper(track)=? order by confidence_score desc, sample_size desc limit 60',[tr]).fetchall():
                if r['benchmark_id'] not in existing: bench.append(bm_summary(r)); existing.add(r['benchmark_id'])
    finally: con.close()
    manifest={'pass_token':TOKEN,'generated_timestamp':gen,'feed_version':'edgeiq_performance_intelligence_product_feeds_v1','source_snapshots':srcids,'source_reports':{'foundation':str(FOUND),'phase3_1':str(P31)},'row_counts':{'race_intelligence_index':len(race_idx),'horse_intelligence_index':len(horse_idx),'historical_performance_intelligence_index':len(hist_idx),'benchmark_explanation_index':len(bench),'current_product_runners':len(runners)},'unsupported_fields':UNSUPPORTED,'known_limitations':['Current races expose historical benchmark context until official governed race time exists.','Runner-adjusted seconds and lengths versus benchmark remain unavailable.','Official sectional benchmarks and deviations remain unavailable.','Historical deviations shown are race-context deviations, not independently timed runner deviations.']}
    payload={'manifest':manifest,'race_intelligence_index':race_idx,'horse_intelligence_index':horse_idx,'historical_performance_intelligence_index':hist_idx,'benchmark_explanation_index':bench}
    PUB.mkdir(parents=True,exist_ok=True); AUD.mkdir(parents=True,exist_ok=True); INTEG.mkdir(parents=True,exist_ok=True)
    feed=PUB/'edgeiq_performance_intelligence_product_feeds_v1.json'; feed.write_text(json.dumps(payload,indent=2),encoding='utf-8')
    manifest['hashes']={feed.name:sha(feed)}; (PUB/'edgeiq_performance_intelligence_product_manifest_v1.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8'); (AUD/'edgeiq_performance_intelligence_phase4_0_product_feeds_latest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    with (AUD/'edgeiq_performance_intelligence_phase4_0_feed_counts.csv').open('w',newline='',encoding='utf-8') as fh:
        w=csv.writer(fh); w.writerow(['feed','rows']); [w.writerow([k,v]) for k,v in manifest['row_counts'].items()]
    (INTEG/'EDGEIQ_PERFORMANCE_INTELLIGENCE_PRODUCT_INTEGRATION_AUDIT_V1.md').write_text('# EDGEiQ Performance Intelligence Product Integration Audit V1\n\nGenerated: '+gen+'\n\n## Current implementations\n- Race workspace: `src/edgeiq-os/race/components/RaceWorkspace.tsx`\n- Performance workspace: `src/edgeiq-os/race/components/EpiWorkspaceWorkspace.tsx`\n- Form workspace: `src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx`\n- Runner profile: `src/edgeiq-os/race/components/RunnerProfileWorkspace.tsx`\n- Results workspace: `src/edgeiq-os/race/components/ResultsWorkspace.tsx`\n- Compare workspace: `src/edgeiq-os/compare/CompareWorkspace.tsx`\n- Insights workspace: `src/edgeiq-os/race/components/InsightsWorkspace.tsx`\n- Current catalogue: `public/data/edgeiq_three_day_product_catalog_v1.json`\n\n## Integration points\nCompact feed: `/performance-intelligence/edgeiq_performance_intelligence_product_feeds_v1.json`\nService boundary: `src/edgeiq-os/services/performance-intelligence/`\n\n## Fields intentionally unavailable\n'+('\n'.join('- '+x for x in UNSUPPORTED))+'\n\n## Identity safety\nHorse-code matches are preferred. Name matching is secondary. Unmatched current runners remain unavailable.\n\nToken: `'+TOKEN+'`\n',encoding='utf-8')
    print(TOKEN); print(json.dumps(manifest['row_counts'],indent=2)); print(feed)
if __name__=='__main__':
    try: main()
    except Exception as e:
        AUD.mkdir(parents=True,exist_ok=True); (AUD/'edgeiq_performance_intelligence_phase4_0_product_feeds_failure.json').write_text(json.dumps({'status':'FAIL','error':str(e),'generated_timestamp':now()},indent=2),encoding='utf-8'); raise
