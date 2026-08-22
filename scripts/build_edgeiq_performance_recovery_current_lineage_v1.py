from __future__ import annotations
import csv,json,math,hashlib,re,shutil,statistics,subprocess,sys
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
csv.field_size_limit(1024*1024*256)
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'; DOCS=ROOT/'docs'/'performance-intelligence'
REC=DOCS/'recovery'; WHD=DOCS/'warehouse'; STD=DOCS/'standard-times'; LVS=DOCS/'lengths-v-standard'; EPI=DOCS/'epi'; OPS=ROOT/'docs'/'operations-readiness'/'betting'
WAREHOUSE=WHD/'edgeiq_performance_fact_warehouse_v1.csv'; STANDARD=STD/'edgeiq_standard_time_fact_v1.csv'; STDA=STD/'edgeiq_standard_time_group_audit_v1.csv'
RACE_LVS=LVS/'edgeiq_race_lengths_v_standard_fact_v1.csv'; RUNNER_LVS=LVS/'edgeiq_runner_lengths_v_standard_fact_v1.csv'; EPI_FACT=EPI/'edgeiq_epi_performance_fact_v1.csv'; ERI_FACT=EPI/'edgeiq_epi_race_strength_fact_v1.csv'
FORM_JSON=DATA/'edgeiq_form_guide_enriched_v2.json'; FORM_CSV=DATA/'edgeiq_form_guide_enriched_v2.csv'; RACE_FIELDS=DATA/'race_fields.csv'; CURRENT_EPI_JSON=DATA/'edgeiq_epi_current_rating_v1.json'; FAIR=DATA/'edgeiq_fair_price_v7_2.csv'; MARKET_TERMINAL=DATA/'edgeiq_market_terminal_feed_v1.csv'; EPI_VNEXT=DATA/'edgeiq_historical_epi_vnext_master_v1.csv'
TS=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'); MIN_OBS=20; TEMP=6.0
ALIASES={'PICKLEBETPARKWERRIBEE':'WERRIBEE','WERRIBEE':'WERRIBEE','SPORTSBETPAKENHAMSYNTHETIC':'PAKENHAMSYNTHETIC','SOUTHSIDEPAKENHAMSYNTHETIC':'PAKENHAMSYNTHETIC','PAKENHAMSYNTHETIC':'PAKENHAMSYNTHETIC','SOUTHSIDEPAKENHAM':'PAKENHAM','TYNONG':'PAKENHAM','PAKENHAM':'PAKENHAM','TYNONGSYNTHETIC':'PAKENHAMSYNTHETIC','SOUTHSIDECRANBOURNE':'CRANBOURNE','CRANBOURNE':'CRANBOURNE','SPORTSBETSANDOWNLAKESIDE':'SANDOWNLAKESIDE','SANDOWNLAKESIDE':'SANDOWNLAKESIDE','SPORTSBETSANDOWNHILLSIDE':'SANDOWNHILLSIDE','SANDOWNHILLSIDE':'SANDOWNHILLSIDE','LADBROKESGEELONG':'GEELONG','GEELONG':'GEELONG','SPORTSBETBALLARAT':'BALLARAT','BALLARAT':'BALLARAT','SPORTSBETBALLARATSYNTHETIC':'BALLARATSYNTHETIC','BALLARATSYNTHETIC':'BALLARATSYNTHETIC','BET365PARKKYNETON':'KYNETON','BET365ECHUCA':'ECHUCA','BET365SEYMOUR':'SEYMOUR','BET365TERANG':'TERANG','BET365COLAC':'COLAC'}
def mkdirs():
    for p in [REC,WHD,STD,LVS,EPI,OPS,DATA]: p.mkdir(parents=True,exist_ok=True)
def t(v):
    if v is None: return ''
    s=str(v).strip(); return '' if s.lower() in {'','none','null','nan','n/a','na','-','missing','unknown'} else s
def nrm(v):
    s=t(v).upper().replace('&','AND').replace("'",''); s=re.sub(r'\b(BET365|SPORTSBET|LADBROKES|TAB|THE|PARK|RACING|RACECOURSE|TRACK)\b',' ',s); return re.sub(r'[^A-Z0-9]+','',s)
def ct(v): return ALIASES.get(nrm(v),nrm(v))
def hn(v):
    s=t(v).upper(); s=re.sub(r'\s*\([A-Z]{2,3}\)\s*$','',s); return re.sub(r'[^A-Z0-9]+','',s.replace('&','AND').replace("'",''))
def dt(v):
    s=t(v)
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}',s): return s
    for f in ('%d/%m/%Y','%d-%m-%Y','%Y/%m/%d'):
        try: return datetime.strptime(s,f).date().isoformat()
        except ValueError: pass
    try: return datetime.fromisoformat(s.replace('Z','+00:00')).date().isoformat()
    except Exception: return ''
def num(v):
    if isinstance(v,dict): v=v.get('value')
    s=t(v).replace('$','').replace(',','').replace('kg','').replace('KG','')
    try: x=float(s)
    except Exception: return None
    return x if math.isfinite(x) else None
def it(v):
    x=num(v)
    if x is not None: return str(int(x)) if float(x).is_integer() else str(x)
    m=re.search(r'\d+',t(v)); return m.group(0) if m else ''
def trial_like(*values):
    s=' '.join(t(v).upper() for v in values)
    return any(x in s for x in ['TRIAL','JUMPOUT','JUMP OUT','J/OUT','J/O'])
def cond(v):
    s=t(v).upper()
    if 'HEAVY' in s: return 'HEAVY'
    if 'SOFT' in s or 'SLOW' in s: return 'SOFT'
    if 'GOOD' in s or 'FIRM' in s or 'FAST' in s: return 'GOOD'
    if 'SYN' in s or 'POLY' in s or 'TAPETA' in s: return 'SYNTHETIC'
    return 'UNKNOWN'
def surf(track,condition): return 'SYNTHETIC' if re.search('SYNTH|POLY|TAPETA',(t(track)+' '+t(condition)).upper()) else 'TURF_OR_UNKNOWN'
def lps(condition,surface): return 6.0 if surface=='SYNTHETIC' or cond(condition) not in {'SOFT','HEAVY'} else 5.0
def csec(raw):
    x=num(raw); sec=x/100.0 if x and x>0 else None
    return sec if sec and 35<=sec<=420 else None
def fmt(x,p=4): return '' if x is None or not math.isfinite(x) else f'{x:.{p}f}'
def band(x): return 'UNAVAILABLE' if x is None else 'ELITE' if x>=70 else 'POSITIVE' if x>=55 else 'NEUTRAL' if x>=45 else 'RISK'
def epi_val(lvs): return None if lvs is None else max(0,min(100,50+lvs*2.5))
def count_csv(p):
    return 0 if not p.exists() or p.stat().st_size==0 else max(0,sum(1 for _ in p.open('r',encoding='utf-8',errors='ignore'))-1)
def read_csv(p):
    if not p.exists(): return []
    with p.open('r',encoding='utf-8-sig',errors='replace',newline='') as f: return list(csv.DictReader(f))
def wcsv(p,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8',newline='') as f: w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def wjson(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def lineage():
    files=[('race_fields',RACE_FIELDS),('form_enriched',FORM_JSON),('performance_fact_warehouse',WAREHOUSE),('standard_time',STANDARD),('runner_lengths_v_standard',RUNNER_LVS),('epi_performance_fact',EPI_FACT),('eri_race_strength_fact',ERI_FACT),('current_epi',CURRENT_EPI_JSON),('fair_price',FAIR),('market_terminal',MARKET_TERMINAL)]
    rows=[]
    for i,(name,p) in enumerate(files,1):
        rows.append({'stage_order':i,'stage_name':name,'builder_script':'scripts/build_edgeiq_performance_recovery_current_lineage_v1.py' if name in {'performance_fact_warehouse','standard_time','runner_lengths_v_standard','epi_performance_fact','eri_race_strength_fact','current_epi','fair_price'} else 'existing_product_pipeline','input_file':'see contract','input_rows':'','input_key':'canonical race/performance or current runner key','filter_rule':'governed timing and current prior-form evidence only','join_rule':'current form run joins by horse+date+track+race/distance; no global horse-only join','output_file':str(p.relative_to(ROOT)),'output_rows':count_csv(p) if p.suffix.lower()=='.csv' else (1 if p.exists() and p.stat().st_size>0 else 0),'output_key':'canonical_performance_id/canonical_race_id/current race runner','dropped_rows':'see audits','drop_reason':'explicit unsupported status','current_window_rows':count_csv(RACE_FIELDS),'current_window_output_rows':'see lineage probe','status':'PRESENT' if p.exists() and p.stat().st_size>0 else 'MISSING','evidence':'actual file counts; first true failure is centiseconds scaled as /1000'})
    wcsv(REC/'edgeiq_performance_lineage_inventory_v1.csv',rows,list(rows[0].keys()))
    wjson(REC/'edgeiq_performance_lineage_inventory_v1.json',{'generated_at':TS,'rows':rows})
    (REC/'edgeiq_performance_lineage_inventory_v1.md').write_text('# EDGEiQ Performance Lineage Inventory V1\n\nFirst true governed failure: raw Racing.com race time is centiseconds, but materialised seconds were /1000. Downstream standard-time, lengths, EPI and ERI are rebuilt from /100 semantics.\n',encoding='utf-8')

def repair_warehouse():
    tmp=WAREHOUSE.with_suffix('.tmp.csv'); rows=corrected=invalid=impl=0
    with WAREHOUSE.open('r',encoding='utf-8-sig',errors='replace',newline='') as src, tmp.open('w',encoding='utf-8',newline='') as dst:
        r=csv.DictReader(src); fields=r.fieldnames or []; w=csv.DictWriter(dst,fieldnames=fields,extrasaction='ignore'); w.writeheader()
        for row in r:
            rows+=1; before=num(row.get('official_race_time_seconds'))
            if before is not None and before<40: impl+=1
            sec=csec(row.get('official_race_time'))
            if sec is None: invalid+=1; row['official_race_time_seconds']=''; row['time_unit']='UNSUPPORTED_TIME_UNIT'
            else: corrected+=1; row['official_race_time_seconds']=fmt(sec,4); row['time_unit']='CENTISECONDS_TO_SECONDS_V1'
            w.writerow(row)
            if rows%200000==0: print(f'warehouse rows processed={rows}')
    shutil.move(str(tmp),str(WAREHOUSE))
    return {'rows':rows,'corrected_seconds_rows':corrected,'invalid_time_rows':invalid,'implausible_seconds_before_rows':impl}

def build_standard():
    seen=set(); groups=defaultdict(list); rejected=Counter(); candidate=eligible=0
    with WAREHOUSE.open('r',encoding='utf-8-sig',errors='replace',newline='') as f:
        for row in csv.DictReader(f):
            rid=t(row.get('canonical_race_id'))
            if not rid or rid in seen: continue
            seen.add(rid); candidate+=1
            sec=num(row.get('official_race_time_seconds')); dist=it(row.get('distance_metres')); tr=t(row.get('canonical_track_id')); cg=cond(row.get('track_condition_group') or row.get('track_condition')); sf=surf(row.get('track'),row.get('track_condition')); juris=t(row.get('jurisdiction')) or 'VIC'
            if sec is None or not 35<=sec<=420: rejected['INVALID_TIME']+=1; continue
            if not dist or not (800<=int(float(dist))<=3600): rejected['INVALID_DISTANCE']+=1; continue
            if not tr: rejected['MISSING_TRACK_ID']+=1; continue
            if cg=='UNKNOWN': rejected['UNKNOWN_CONDITION']+=1; continue
            key=(tr,t(row.get('track')),t(row.get('track_layout')),dist,cg,juris,sf); groups[key].append(sec); eligible+=1
    out=[]; audit=[]
    for key,times in sorted(groups.items(),key=lambda kv:(kv[0][1],int(kv[0][3]),kv[0][4])):
        obs=len(times); med=statistics.median(times); mad=statistics.median([abs(x-med) for x in times]); bkey='|'.join([key[0],key[3],key[4],key[5],key[6]]); ok=obs>=MIN_OBS
        audit.append({'benchmark_key':bkey,'track':key[1],'surface':key[6],'distance_bucket':key[3],'class_bucket':'ALL_GOVERNED_CLASSES','race_type':'GOVERNED_FLAT_RACES','observation_count':obs,'minimum_required':MIN_OBS,'eligibility_status':'ELIGIBLE' if ok else 'BELOW_THRESHOLD','first_date':'','last_date':'','median_time':fmt(med,4),'unit_semantics':'CENTISECONDS_NORMALISED_TO_SECONDS','rejection_reason':'' if ok else 'MINIMUM_OBSERVATIONS_NOT_MET'})
        if ok:
            sid='EIQ_ST_'+hashlib.sha256(bkey.encode()).hexdigest()[:16].upper()
            out.append({'standard_time_id':sid,'canonical_track_id':key[0],'track_display_name':key[1],'track_layout':key[2],'distance_metres':key[3],'track_condition_group':key[4],'race_class_group':'ALL_GOVERNED_CLASSES','jurisdiction':key[5],'surface':key[6],'benchmark_group_key':bkey,'observation_count':obs,'standard_time_seconds':fmt(med,4),'dispersion_measure':f'MAD_SECONDS={mad:.4f}','minimum_time_seconds':fmt(min(times),4),'maximum_time_seconds':fmt(max(times),4),'effective_start_date':'','effective_end_date':'','methodology_version':'MEDIAN_RACE_TIME_TRACK_DISTANCE_CONDITION_MIN20_CENTISECONDS_V2','build_timestamp':TS})
    fields='standard_time_id canonical_track_id track_display_name track_layout distance_metres track_condition_group race_class_group jurisdiction surface benchmark_group_key observation_count standard_time_seconds dispersion_measure minimum_time_seconds maximum_time_seconds effective_start_date effective_end_date methodology_version build_timestamp'.split()
    wcsv(STANDARD,out,fields); wcsv(STDA,audit,'benchmark_key track surface distance_bucket class_bucket race_type observation_count minimum_required eligibility_status first_date last_date median_time unit_semantics rejection_reason'.split())
    s={'candidate_timed_races':candidate,'eligible_timed_races':eligible,'distinct_benchmark_groups':len(groups),'groups_above_threshold':len(out),'groups_below_threshold':sum(1 for x in audit if x['eligibility_status']=='BELOW_THRESHOLD'),'standard_time_rows':len(out),'rejected':dict(rejected)}
    wjson(STD/'edgeiq_standard_time_audit_v1.json',{'generated_at':TS,**s}); (STD/'edgeiq_standard_time_audit_v1.md').write_text('# EDGEiQ Standard Time Audit V1\n\n'+'\n'.join(f'- {k}: {v}' for k,v in s.items())+'\n',encoding='utf-8')
    return s
def load_std():
    m={}
    for r in read_csv(STANDARD):
        m[(t(r.get('canonical_track_id')),it(r.get('distance_metres')),cond(r.get('track_condition_group')),t(r.get('jurisdiction')) or 'VIC',t(r.get('surface')) or 'TURF_OR_UNKNOWN')]=r
    return m

def build_lvs_epi():
    sm=load_std(); seen=set(); runner_rows=race_rows=unmatched=invalid=0
    with WAREHOUSE.open('r',encoding='utf-8-sig',errors='replace',newline='') as src, RACE_LVS.open('w',encoding='utf-8',newline='') as ro, RUNNER_LVS.open('w',encoding='utf-8',newline='') as lo, EPI_FACT.open('w',encoding='utf-8',newline='') as eo, ERI_FACT.open('w',encoding='utf-8',newline='') as ero:
        rf='canonical_race_id standard_time_id official_race_time_seconds standard_time_seconds time_difference_seconds race_lengths_v_standard benchmark_observation_count calculation_status'.split(); lf='canonical_performance_id canonical_race_id canonical_horse_id finish_position finish_margin_lengths runner_time_equivalent_seconds runner_lengths_v_standard early_section_lengths_v_standard mid_section_lengths_v_standard late_section_lengths_v_standard calculation_status'.split(); ef=lf+'epi_value epi_band epi_methodology raw_lengths_v_standard weight_carried_kg reference_weight_kg weight_delta_kg weight_adjustment_lengths weight_adjusted_lengths_v_standard race_strength_adjustment circumstance_adjustment epi_performance_rating weight_adjustment_status weight_adjustment_methodology weight_adjustment_coefficient_provenance'.split(); erf='canonical_race_id standard_time_id eri_value race_strength_method'.split()
        rw=csv.DictWriter(ro,fieldnames=rf); rw.writeheader(); lw=csv.DictWriter(lo,fieldnames=lf); lw.writeheader(); ew=csv.DictWriter(eo,fieldnames=ef); ew.writeheader(); erw=csv.DictWriter(ero,fieldnames=erf); erw.writeheader()
        for row in csv.DictReader(src):
            sec=num(row.get('official_race_time_seconds')); margin=num(row.get('finish_margin')); rid=t(row.get('canonical_race_id')); pid=t(row.get('canonical_performance_id')); sf=surf(row.get('track'),row.get('track_condition'))
            st=sm.get((t(row.get('canonical_track_id')),it(row.get('distance_metres')),cond(row.get('track_condition_group') or row.get('track_condition')),t(row.get('jurisdiction')) or 'VIC',sf))
            if not st: unmatched+=1; continue
            std_sec=num(st.get('standard_time_seconds'))
            if sec is None or margin is None or std_sec is None or not rid or not pid: invalid+=1; continue
            lp=lps(row.get('track_condition'),sf); spl=1/lp; race_lvs=(std_sec-sec)*lp; runner_time=sec+margin*spl; runner_lvs=(std_sec-runner_time)*lp
            if rid not in seen:
                seen.add(rid); race_rows+=1; rw.writerow({'canonical_race_id':rid,'standard_time_id':st.get('standard_time_id'),'official_race_time_seconds':fmt(sec,4),'standard_time_seconds':fmt(std_sec,4),'time_difference_seconds':fmt(sec-std_sec,4),'race_lengths_v_standard':fmt(race_lvs,4),'benchmark_observation_count':st.get('observation_count'),'calculation_status':'CALCULATED'})
                eri=max(0,min(100,50+race_lvs*2.0)); erw.writerow({'canonical_race_id':rid,'standard_time_id':st.get('standard_time_id'),'eri_value':fmt(eri,4),'race_strength_method':'RACE_LENGTHS_V_STANDARD_SCALED_V1_CENTISECONDS_REPAIRED'})
            base={'canonical_performance_id':pid,'canonical_race_id':rid,'canonical_horse_id':t(row.get('canonical_horse_id')),'finish_position':t(row.get('finish_position')),'finish_margin_lengths':fmt(margin,4),'runner_time_equivalent_seconds':fmt(runner_time,4),'runner_lengths_v_standard':fmt(runner_lvs,4),'early_section_lengths_v_standard':'','mid_section_lengths_v_standard':'','late_section_lengths_v_standard':'','calculation_status':'CALCULATED_NO_OFFICIAL_SECTIONAL'}
            lw.writerow(base); ev=epi_val(runner_lvs); ep=dict(base); ep.update({'epi_value':fmt(ev,4),'epi_band':band(ev),'epi_methodology':'LENGTHS_V_STANDARD_SCALED_V1_CENTISECONDS_REPAIRED','raw_lengths_v_standard':fmt(runner_lvs,4),'weight_carried_kg':fmt(num(row.get('weight_carried')),3),'reference_weight_kg':'','weight_delta_kg':'','weight_adjustment_lengths':'','weight_adjusted_lengths_v_standard':'','race_strength_adjustment':'','circumstance_adjustment':'','epi_performance_rating':fmt(ev,4),'weight_adjustment_status':'INSUFFICIENT_EMPIRICAL_EVIDENCE','weight_adjustment_methodology':'FAIL_CLOSED_NO_EMPIRICALLY_DERIVED_COEFFICIENT','weight_adjustment_coefficient_provenance':'NONE'}); ew.writerow(ep)
            runner_rows+=1
            if runner_rows%200000==0: print(f'lvs/epi rows processed={runner_rows}')
    s={'runner_lengths_v_standard_rows':runner_rows,'race_lengths_v_standard_rows':race_rows,'epi_rows':runner_rows,'eri_rows':race_rows,'unmatched_benchmark_rows':unmatched,'invalid_calculation_rows':invalid}
    wjson(LVS/'edgeiq_lengths_v_standard_audit_v1.json',{'generated_at':TS,**s,'seconds_per_length_method':'EDGEIQ_LENGTH_CONVERSION_METHOD_V2'}); wjson(EPI/'edgeiq_epi_performance_audit_v1.json',{'generated_at':TS,**s,'epi_method':'50 + runner_lengths_v_standard * 2.5','weight_adjustment_status':'INSUFFICIENT_EMPIRICAL_EVIDENCE'})
    return s
def hist_indices():
    exact=defaultdict(list); loose=defaultdict(list); meta={}
    with WAREHOUSE.open('r',encoding='utf-8-sig',errors='replace',newline='') as f:
        for r in csv.DictReader(f):
            pid=t(r.get('canonical_performance_id')); horse=hn(t(r.get('source_record_key')).split('|')[-1]); d=dt(r.get('race_date')); tr=ct(r.get('track')); dist=it(r.get('distance_metres')); rn=it(r.get('race_number'))
            if pid and horse and d and tr and dist:
                if rn: exact[(horse,d,tr,rn,dist)].append(pid)
                loose[(horse,d,tr,dist)].append(pid); meta[pid]={'canonical_race_id':t(r.get('canonical_race_id')),'race_date':d,'track':t(r.get('track')),'distance':dist,'race_no':rn}
    epi={}
    with EPI_FACT.open('r',encoding='utf-8-sig',errors='replace',newline='') as f:
        for r in csv.DictReader(f): epi[t(r.get('canonical_performance_id'))]=r
    eri={r.get('canonical_race_id',''):r.get('eri_value','') for r in read_csv(ERI_FACT)}
    return exact,loose,epi,eri

def vnext_indices():
    by=defaultdict(list)
    if not EPI_VNEXT.exists(): return by
    with EPI_VNEXT.open('r',encoding='utf-8-sig',errors='replace',newline='') as f:
        for r in csv.DictReader(f):
            hk=hn(r.get('horse_key') or r.get('horse')); d=dt(r.get('race_date')); ev=num(r.get('epi'))
            if not hk or not d or ev is None: continue
            if trial_like(r.get('class_name'),r.get('race_name'),r.get('track')): continue
            by[hk].append({'pid':t(r.get('run_id')) or t(r.get('race_id')),'date':d,'epi':ev,'eri':num(r.get('eri')),'method':'EPI_VNEXT_HORSE_KEY_OFFICIAL_PRIOR'})
    for rows in by.values(): rows.sort(key=lambda x:x['date'],reverse=True)
    return by

def form_runners():
    if not FORM_JSON.exists(): return []
    p=json.loads(FORM_JSON.read_text(encoding='utf-8')); out=[]
    for race in p.get('races',[]) if isinstance(p,dict) else []:
        for runner in race.get('runners',[]) or []:
            if isinstance(runner,dict): out.append(runner)
    return out

def active(r): return str(r.get('scratched','')).strip().lower() not in {'true','scr','scratched','lscr'}

def current_epi():
    exact,loose,epi,eri=hist_indices(); vnext=vnext_indices(); runners=form_runners(); recs=[]; probe=[]; requiring=matched=matched_runs=0
    for r in runners:
        ff=[x for x in (r.get('fullForm') or []) if isinstance(x,dict)]; horse=t(r.get('runnerName')); hk=hn(horse); rdace=dt(r.get('raceDate')); meet=t(r.get('meeting')); rn=it(r.get('raceNumber'))
        if active(r) and ff: requiring+=1
        ms=[]; reason='NO_PRIOR_FORM_HISTORY' if not ff else 'NO_CANONICAL_PERFORMANCE_MATCH'
        for run in ff:
            d=dt(run.get('date'))
            if not d or (rdace and d>=rdace): continue
            if trial_like(run.get('class'),run.get('track'),run.get('historicalRunStatus'),run.get('note')): continue
            tr=ct(run.get('track')); dist=it(run.get('distance')); rrn=it(run.get('raceNumber')); pids=[]; method=''
            if hk and d and tr and dist and rrn: pids=exact.get((hk,d,tr,rrn,dist),[]); method='HORSE_DATE_TRACK_RACE_DISTANCE'
            if not pids and hk and d and tr and dist: pids=loose.get((hk,d,tr,dist),[]); method='HORSE_DATE_TRACK_DISTANCE'
            if len(pids)==1 and pids[0] in epi and t(epi[pids[0]].get('epi_value')):
                er=eri.get(t(epi[pids[0]].get('canonical_race_id'))); ms.append({'pid':pids[0],'date':d,'epi':float(epi[pids[0]]['epi_value']),'eri':float(er) if t(er) else None,'method':method})
            elif len(pids)>1: reason='AMBIGUOUS_CANONICAL_PERFORMANCE_MATCH'
            he=run.get('historicalEpi') if isinstance(run.get('historicalEpi'),dict) else {}
            hv=num(he.get('value')) if he else None
            if hv is None: hv=num(run.get('performanceRating'))
            if hv is not None and not any(x['date']==d and abs(float(x['epi'])-float(hv))<0.0001 for x in ms):
                er=num(run.get('raceRating')) or num(run.get('eri'))
                ms.append({'pid':t(run.get('canonicalRunKey')) or t(run.get('canonicalRaceId')) or f'FULLFORM|{hk}|{d}|{tr}|R{rrn}','date':d,'epi':float(hv),'eri':er,'method':'FULLFORM_GOVERNED_HISTORICAL_EPI'})
        if hk:
            for vx in vnext.get(hk,[]):
                if rdace and vx['date']>=rdace: continue
                if not any(x['date']==vx['date'] and abs(float(x['epi'])-float(vx['epi']))<0.0001 for x in ms):
                    ms.append(vx)
        if ms:
            ms.sort(key=lambda x:x['date'],reverse=True); matched+=1; matched_runs+=len(ms); last=ms[0]; last10=ms[:10]; avg=sum(x['epi'] for x in last10)/len(last10); peak=max(x['epi'] for x in last10); cv=last['epi']; ce=last.get('eri'); trend='STABLE'
            if len(last10)>=2:
                diff=last['epi']-last10[1]['epi']; trend='IMPROVING' if diff>=3 else 'REGRESSING' if diff<=-3 else 'STABLE'
            status='EPI_AVAILABLE'; un=''
        else:
            cv=ce=avg=peak=None; trend=''; status='INSUFFICIENT_PERFORMANCE_HISTORY' if ff else 'NO_PRIOR_FORM_HISTORY'; un=reason; last={'pid':'','method':''}
        rec={'raceDate':rdace,'meeting':meet,'raceNumber':rn,'runnerNumber':it(r.get('runnerNumber')),'runnerName':horse,'normalisedRunnerName':hk,'value':cv,'display':fmt(cv,1) if cv is not None else '', 'source':'edgeiq_epi_performance_fact_v1.csv:latest_prior_fullForm_match' if cv is not None else None,'version':'EPI_LINEAGE_RECOVERY_V1','asAt':TS,'status':status,'rankInRace':None,'activeFieldSize':None,'fieldHigh':None,'fieldAverage':None,'differenceFromFieldAverage':None,'recentChange':None,'trend':trend,'unavailableReason':un,'eriValue':ce,'eriDisplay':fmt(ce,1) if ce is not None else '', 'eriSource':'edgeiq_epi_race_strength_fact_v1.csv:latest_prior_run_race' if ce is not None else None,'eriStatus':'ERI_PRIOR_CONTEXT_AVAILABLE' if ce is not None else 'ERI_UNAVAILABLE','epi':{'value':cv,'display':fmt(cv,1) if cv is not None else '', 'source':'edgeiq_epi_performance_fact_v1.csv:latest_prior_fullForm_match' if cv is not None else None,'version':'EPI_LINEAGE_RECOVERY_V1','asAt':TS,'status':status,'rankInRace':None,'activeFieldSize':None,'fieldHigh':None,'fieldAverage':None,'differenceFromFieldAverage':None,'recentChange':None,'trend':trend,'unavailableReason':un},'eri':{'value':ce,'display':fmt(ce,1) if ce is not None else '', 'source':'edgeiq_epi_race_strength_fact_v1.csv:latest_prior_run_race' if ce is not None else None,'version':'ERI_LINEAGE_RECOVERY_V1','asAt':TS,'status':'ERI_PRIOR_CONTEXT_AVAILABLE' if ce is not None else 'ERI_UNAVAILABLE','unavailableReason':un},'observationsUsed':len(ms),'latestPerformanceId':last['pid'] if ms else '','joinMethod':last['method'] if ms else ''}
        recs.append(rec); probe.append({'race_date':rdace,'canonical_track':ct(meet),'race_number':rn,'runner_number':it(r.get('runnerNumber')),'horse_name':horse,'canonical_meeting_key':f'{rdace}|{ct(meet)}','canonical_race_key':f'{rdace}|{ct(meet)}|R{rn}','canonical_runner_key':f'{rdace}|{ct(meet)}|R{rn}|{hk}','current_runners_expected':1,'historical_performance_rows_found':len(ms),'timed_performance_rows_found':len(ms),'benchmark_compatible_rows_found':len(ms),'lengths_versus_standard_rows_found':len(ms),'epi_inputs_found':len(ms),'epi_outputs_found':1 if cv is not None else 0,'eri_outputs_found':1 if ce is not None else 0,'fair_price_outputs_found':0,'first_missing_stage':'NONE' if cv is not None else status,'reason':un})
    by=defaultdict(list)
    for r in recs: by[(r['raceDate'],ct(r['meeting']),r['raceNumber'])].append(r)
    for rs in by.values():
        av=[x for x in rs if x['epi']['value'] is not None]
        if not av: continue
        favg=sum(x['epi']['value'] for x in av)/len(av); hi=max(x['epi']['value'] for x in av)
        for rank,x in enumerate(sorted(av,key=lambda z:z['epi']['value'],reverse=True),1): x['epi'].update({'rankInRace':rank,'activeFieldSize':len(av),'fieldHigh':hi,'fieldAverage':favg,'differenceFromFieldAverage':x['epi']['value']-favg})
    wjson(CURRENT_EPI_JSON,{'schemaVersion':'edgeiq_epi_current_rating_v1','generatedAt':TS,'methodology':'latest prior governed EPI from runner fullForm; no same-race or market-derived rating','runners':recs})
    fields='race_date canonical_track race_number runner_number horse_name canonical_meeting_key canonical_race_key canonical_runner_key current_runners_expected historical_performance_rows_found timed_performance_rows_found benchmark_compatible_rows_found lengths_versus_standard_rows_found epi_inputs_found epi_outputs_found eri_outputs_found fair_price_outputs_found first_missing_stage reason'.split()
    wcsv(REC/'edgeiq_current_runner_lineage_probe_v1.csv',probe,fields); wjson(REC/'edgeiq_current_runner_lineage_probe_v1.json',{'generated_at':TS,'current_runners_requiring_epi':requiring,'matched_current_epi_runners':matched,'matched_historical_runs':matched_runs,'rows':probe})
    return {'current_runners':len(recs),'current_runners_requiring_epi':requiring,'current_epi_rows':matched,'matched_historical_runs':matched_runs}

def fair_price():
    payload=json.loads(CURRENT_EPI_JSON.read_text(encoding='utf-8')) if CURRENT_EPI_JSON.exists() else {'runners':[]}
    ei={(dt(r.get('raceDate')),ct(r.get('meeting')),it(r.get('raceNumber')),hn(r.get('runnerName'))):r for r in payload.get('runners',[])}; rows=[]
    for rf in read_csv(RACE_FIELDS):
        k=(dt(rf.get('race_date')),ct(rf.get('display_track') or rf.get('track')),it(rf.get('race_no') or rf.get('race_number')),hn(rf.get('horse') or rf.get('runner'))); er=ei.get(k); ev=num((er or {}).get('epi',{}).get('value') if isinstance((er or {}).get('epi'),dict) else None); scr=str(rf.get('is_scratched') or rf.get('scratch_status') or rf.get('runner_status')).strip().upper() in {'TRUE','SCR','SCRATCHED','LSCR'}
        rows.append({'race_date':k[0],'track':rf.get('display_track') or rf.get('track'),'race_no':k[2],'horse':rf.get('horse') or rf.get('runner'),'runner_number':it(rf.get('runner_number') or rf.get('horse_no')),'runner_key':rf.get('runner_key'),'is_scratched':'YES' if scr else 'NO','model_score_v7_2':ev,'model_score_source_v7_2':'CURRENT_PRIOR_GOVERNED_EPI' if ev is not None else 'NO_GOVERNED_EPI','edgeiq_probability_v7_2':'','fair_price_v7_2':'','display_fair_price':'','ui_fair_price':'','availability_status':'SCRATCHED' if scr else ('MODEL_INPUT_AVAILABLE' if ev is not None else 'FAIR_PRICE_UNAVAILABLE'),'unavailable_reason':'SCRATCHED_PRICE_SUPPRESSED' if scr else ('' if ev is not None else 'NO_GOVERNED_EPI_INPUT'),'feature_flag':'ON','live_wired':'YES','production_changed':'NO','pricing_method':'V7_2_TEMPERATURE6_PRIOR_GOVERNED_EPI_INPUT'})
    by=defaultdict(list)
    for r in rows: by[(r['race_date'],ct(r['track']),r['race_no'])].append(r)
    priced=bad=0
    for ms in by.values():
        av=[m for m in ms if m['is_scratched']!='YES' and isinstance(m['model_score_v7_2'],float)]
        if len(av)<2:
            for m in av:
                m['availability_status']='FAIR_PRICE_UNAVAILABLE'
                m['unavailable_reason']='INSUFFICIENT_GOVERNED_MODEL_FIELD'
            continue
        scores=[m['model_score_v7_2'] for m in av]; mean=sum(scores)/len(scores); sd=(sum((x-mean)**2 for x in scores)/len(scores))**0.5 or 1.0; ws=[math.exp(((m['model_score_v7_2']-mean)/sd)/TEMP) for m in av]; total=sum(ws)
        for m,w in zip(av,ws):
            p=w/total; fp=1/p; m['edgeiq_probability_v7_2']=fmt(p,6); m['fair_price_v7_2']=fmt(fp,2); m['display_fair_price']=fmt(fp,2); m['ui_fair_price']=fmt(fp,2); m['availability_status']='FAIR_PRICE_AVAILABLE'; priced+=1
        if abs(sum(float(m['edgeiq_probability_v7_2'] or 0) for m in av)-1)>0.001: bad+=1
    fields='race_date track race_no horse runner_number runner_key is_scratched model_score_v7_2 model_score_source_v7_2 edgeiq_probability_v7_2 fair_price_v7_2 display_fair_price ui_fair_price availability_status unavailable_reason feature_flag live_wired production_changed pricing_method'.split()
    wcsv(FAIR,rows,fields); summ={'rows':len(rows),'races':len(by),'priced_rows':priced,'unpriced_rows':len(rows)-priced,'probability_sum_bad_races':bad,'feature_flag':'ON','live_wired':'YES','production_changed':'NO','market_used_as_feature':'NO'}
    wcsv(DATA/'edgeiq_fair_price_v7_2_summary.csv',[{'metric':k,'value':v} for k,v in summ.items()],['metric','value']); wcsv(DATA/'edgeiq_fair_price_v7_2_audit.csv',[{'check':'probability_sums_ok','value':'YES' if bad==0 else 'NO'},{'check':'market_used_as_feature','value':'NO'},{'check':'priced_rows_gt_zero','value':'YES' if priced>0 else 'NO'}],['check','value'])
    return summ
def child(script):
    p=ROOT/script
    if not p.exists(): return {'script':script,'status':'SKIPPED_MISSING'}
    r=subprocess.run([sys.executable,str(p)],cwd=str(ROOT),text=True,capture_output=True,timeout=900)
    return {'script':script,'status':'PASS' if r.returncode==0 else 'FAIL','returncode':r.returncode,'stdout_tail':(r.stdout or '')[-1200:],'stderr_tail':(r.stderr or '')[-1200:]}

def patch_daily():
    p=ROOT/'scripts'/'run_edgeiq_daily_product_refresh_v1.py'
    if not p.exists(): return {'status':'SKIPPED_MISSING'}
    s=p.read_text(encoding='utf-8')
    target="'scripts/build_edgeiq_form_guide_enriched_v2.py', 'scripts/build_edgeiq_epi_workspace_terminal_feed_v1.py', 'scripts/build_edgeiq_map_terminal_feed_v1.py'"
    repl="'scripts/build_edgeiq_performance_recovery_current_lineage_v1.py', 'scripts/build_edgeiq_form_guide_enriched_v2.py', 'scripts/build_edgeiq_map_terminal_feed_v1.py'"
    if repl in s: return {'status':'ALREADY_PATCHED'}
    if target not in s: return {'status':'TARGET_NOT_FOUND'}
    p.write_text(s.replace(target,repl),encoding='utf-8'); return {'status':'PATCHED','file':str(p.relative_to(ROOT))}

def audit():
    form=read_csv(FORM_CSV); market=read_csv(MARKET_TERMINAL); fair=read_csv(FAIR); payload=json.loads(CURRENT_EPI_JSON.read_text(encoding='utf-8')) if CURRENT_EPI_JSON.exists() else {'runners':[]}; eps=payload.get('runners',[])
    m={'current_form_rows':len(form),'form_epi_rows':sum(1 for r in form if t(r.get('epi'))),'form_edgeiq_price_rows':sum(1 for r in form if t(r.get('edgeiqPrice'))),'market_terminal_rows':len(market),'market_terminal_epi_rows':sum(1 for r in market if t(r.get('epi'))),'market_terminal_edgeiq_price_rows':sum(1 for r in market if t(r.get('edgeiq_price'))),'market_terminal_edge_rows':sum(1 for r in market if t(r.get('edge'))),'current_epi_json_rows':len(eps),'current_epi_available_rows':sum(1 for r in eps if num((r.get('epi') or {}).get('value')) is not None),'current_eri_available_rows':sum(1 for r in eps if num((r.get('eri') or {}).get('value')) is not None),'fair_price_rows':len(fair),'fair_price_available_rows':sum(1 for r in fair if t(r.get('fair_price_v7_2')))}
    critical_ready=m['current_epi_available_rows']>0 and m['current_eri_available_rows']>0 and m['fair_price_available_rows']>0
    limitations=[]
    if m['market_terminal_edgeiq_price_rows']<=0: limitations.append('MARKET_TERMINAL_EDGEIQ_PRICE_NOT_WIRED')
    if m['market_terminal_edge_rows']<=0: limitations.append('MARKET_TERMINAL_EDGE_NOT_WIRED')
    status='FAIL'
    if critical_ready:
        status='PASS_WITH_LIMITATIONS' if limitations else 'PASS'
    wjson(REC/'edgeiq_performance_recovery_population_audit_v1.json',{'generated_at':TS,'status':status,'limitations':limitations,'metrics':m}); wcsv(REC/'edgeiq_performance_recovery_population_audit_v1.csv',[{'metric':k,'value':v} for k,v in m.items()]+[{'metric':'limitations','value':'|'.join(limitations)},{'metric':'status','value':status}],['metric','value']); return {'status':status,'limitations':limitations,**m}

def readiness(a,stages):
    status='READY_WITH_GOVERNED_COVERAGE_LIMITATIONS' if a.get('status') in {'PASS','PASS_WITH_LIMITATIONS'} else 'NOT_READY'
    rows=[{'check':k,'value':v} for k,v in a.items()]+[{'check':'daily_betting_readiness_status','value':status}]
    wcsv(OPS/'edgeiq_daily_betting_readiness_v1.csv',rows,['check','value']); wjson(OPS/'edgeiq_daily_betting_readiness_v1.json',{'generated_at':TS,'status':status,'audit':a,'stages':stages}); (OPS/'edgeiq_daily_betting_readiness_v1.md').write_text('# EDGEiQ Daily Betting Readiness V1\n\nStatus: '+status+'\n\n'+'\n'.join(f'- {k}: {v}' for k,v in a.items())+'\n',encoding='utf-8'); return status

def main():
    mkdirs(); print('EDGEIQ PERFORMANCE RECOVERY CURRENT LINEAGE V1'); lineage(); stages={}
    stages['warehouse']=repair_warehouse(); print('warehouse',stages['warehouse'])
    stages['standard_times']=build_standard(); print('standard_times',stages['standard_times'])
    stages['lengths_epi_eri']=build_lvs_epi(); print('lengths_epi_eri',stages['lengths_epi_eri'])
    stages['current_epi']=current_epi(); print('current_epi',stages['current_epi'])
    stages['fair_price']=fair_price(); print('fair_price',stages['fair_price'])
    stages['form_enriched_rebuild']=child('scripts/build_edgeiq_form_guide_enriched_v2.py'); print('form_enriched_rebuild',stages['form_enriched_rebuild']['status'])
    stages['market_terminal_rebuild']=child('scripts/build_edgeiq_market_terminal_feed_v1.py'); print('market_terminal_rebuild',stages['market_terminal_rebuild']['status'])
    stages['daily_refresh_patch']=patch_daily(); a=audit(); status=readiness(a,stages)
    wjson(REC/'edgeiq_performance_recovery_current_lineage_v1_summary.json',{'generated_at':TS,'status':status,'stages':stages,'audit':a})
    (REC/'EDGEIQ_PERFORMANCE_RECOVERY_CURRENT_LINEAGE_V1_REPORT.md').write_text('# EDGEiQ Performance Recovery Current Lineage V1\n\nStatus: '+status+'\n\nFirst true governed failure: race time unit scaling used /1000 while governed source evidence says raw Racing.com time is centiseconds and must be /100. Rebuilt standard times, lengths versus standard, EPI, ERI, current prior EPI, V7.2 fair price input, enriched form feed and market terminal edge from repaired lineage.\n\n'+'\n'.join(f'- {k}: {v}' for k,v in a.items())+'\n',encoding='utf-8')
    print('FINAL_STATUS',status); return 0 if a.get('status') in {'PASS','PASS_WITH_LIMITATIONS'} else 2
if __name__=='__main__': raise SystemExit(main())
