from __future__ import annotations
import csv, hashlib, json, re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'public'/'data'
PRIVATE=ROOT/'data'/'market'/'ladbrokes'
DOCS=ROOT/'docs'/'market-intelligence'/'ladbrokes'
RACE_FIELDS=PUBLIC/'race_fields.csv'
CATALOG=PUBLIC/'edgeiq_three_day_product_catalog_v1.json'
RAW_RUNTIME=PUBLIC/'edgeiq_ladbrokes_affiliate_market_runtime_v1.csv'
RAW_HISTORY=PRIVATE/'edgeiq_ladbrokes_market_observation_history_v1.csv'
CANONICAL_HISTORY=PRIVATE/'edgeiq_ladbrokes_canonical_market_observation_history_v1.csv'
OUT_CSV=PUBLIC/'edgeiq_current_market_v1.csv'
OUT_JSON=PUBLIC/'edgeiq_current_market_v1.json'
OUT_SUMMARY=PUBLIC/'edgeiq_current_market_v1_summary.csv'
OUT_PROVIDER_UNMATCHED=PUBLIC/'edgeiq_current_market_v1_provider_unmatched.csv'
OUT_OBS_SUMMARY=PUBLIC/'edgeiq_current_market_v1_observation_history_summary.csv'
SCHEMA_CSV=DOCS/'edgeiq_ladbrokes_market_schema_inventory_v1.csv'
SCHEMA_JSON=DOCS/'edgeiq_ladbrokes_market_schema_inventory_v1.json'
SCHEMA_MD=DOCS/'edgeiq_ladbrokes_market_schema_inventory_v1.md'
ALIAS_CSV=DOCS/'edgeiq_track_alias_registry_v1.csv'
CANONICAL_FIELDS='''generated_at edgeiq_observed_at race_date canonical_meeting_id canonical_meeting_key canonical_meeting_name canonical_track canonical_race_id canonical_race_key race_number advertised_start actual_start race_status canonical_runner_id canonical_runner_key runner_number horse_name normalised_horse_name provider provider_meeting_id provider_meeting_name provider_race_id provider_runner_id provider_runner_number provider_horse_name fixed_win fixed_place opening_price high_price low_price recent_price price_timestamp flucs_untimestamped flucs_with_timestamp fluctuation_status previous_fixed_win price_movement price_movement_percent price_movement_status is_scratched scratch_time market_status market_availability_status market_freshness_status source_priority_rank source_confidence join_status join_reason meeting_match_method race_match_method runner_match_method match_conflicts raw_publication_status track meeting_name race_no horse market price market_source market_observed_at'''.split()
PROVIDER_UNMATCHED_FIELDS='''generated_at edgeiq_observed_at race_date provider_meeting_id provider_meeting_name provider_race_id provider_runner_id provider_runner_number provider_horse_name fixed_win fixed_place race_status provider_track_key provider_race_no join_reason meeting_match_method race_match_method runner_match_method raw_publication_status'''.split()
HISTORY_FIELDS='''observation_id edgeiq_observed_at race_date canonical_meeting_id canonical_meeting_key canonical_race_id canonical_race_key canonical_runner_id canonical_runner_key runner_number horse_name provider_runner_id fixed_win fixed_place race_status is_scratched payload_hash'''.split()

def now_utc(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def text(v):
    if v is None: return ''
    s=str(v).strip()
    return '' if s.lower() in {'','none','null','nan','n/a','na','unknown'} else s
def normalise(v):
    s=text(v).upper(); s=re.sub(r'\b(BET365|SPORTSBET|LADBROKES|TAB|THE)\b',' ',s); s=re.sub(r'\b(RACECOURSE|RACING|TRACK|SYNTHETIC)\b',' ',s)
    return re.sub(r'[^A-Z0-9]+','',s)
def number_text(v):
    s=text(v).replace('R','').replace('$','').replace(',','')
    if not s: return ''
    try:
        f=float(s); return str(int(f)) if f.is_integer() else str(f)
    except ValueError:
        m=re.search(r'\d+',s); return m.group(0) if m else s
def money(v):
    s=text(v).replace('$','').replace(',','')
    if not s: return ''
    try: f=float(s)
    except ValueError: return ''
    return f'{f:.2f}' if f>0 else ''
def read_csv(path):
    if not path.exists(): return []
    with path.open('r',encoding='utf-8-sig',errors='replace',newline='') as h: return list(csv.DictReader(h))
def write_csv(path,rows,fields):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='') as h:
        w=csv.DictWriter(h,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def read_json(path):
    if not path.exists(): return {}
    return json.loads(path.read_text(encoding='utf-8'))
def write_json(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def race_base(row): return (text(row.get('race_date')), normalise(row.get('display_track') or row.get('track')), number_text(row.get('race_no') or row.get('race_number')))
def provider_base(row,alias):
    raw=normalise(row.get('track') or row.get('provider_meeting_name'))
    return (text(row.get('race_date')), alias.get(raw,raw), number_text(row.get('race_no') or row.get('provider_race_no')))

def build_alias(canon,runtime):
    tracks=sorted({normalise(r.get('display_track') or r.get('track')) for r in canon if normalise(r.get('display_track') or r.get('track'))})
    alias={t:t for t in tracks}
    for r in runtime:
        raw=normalise(r.get('track'))
        if not raw or raw in alias: continue
        cand=[t for t in tracks if raw.startswith(t) or t.startswith(raw) or t in raw]
        alias[raw]=cand[0] if len(cand)==1 else raw
    write_csv(ALIAS_CSV,[{'provider_track_key':k,'canonical_track_key':v,'alias_status':'CANONICAL' if k==v else 'ALIASED'} for k,v in sorted(alias.items())],['provider_track_key','canonical_track_key','alias_status'])
    return alias

def catalog_maps():
    payload=read_json(CATALOG); meetings={}; races={}
    for m in payload.get('meetings',[]) if isinstance(payload,dict) else []:
        if not isinstance(m,dict): continue
        mk=text(m.get('meetingKey')) or f"{text(m.get('date'))}|{normalise(m.get('meeting'))}"; meetings[mk]=m
        for r in m.get('races',[]) or []:
            if not isinstance(r,dict): continue
            rk=text(r.get('raceKey')) or f"{mk}|R{number_text(r.get('raceNumber'))}"; races[rk]=r
    return meetings,races

def build_indices(canon):
    by_number_name={}; by_horse_by_race=defaultdict(lambda:defaultdict(list)); by_key={}
    for r in canon:
        base=race_base(r); num=number_text(r.get('runner_number') or r.get('saddlecloth') or r.get('horse_no')); hk=normalise(r.get('horse') or r.get('runner') or r.get('horse_key'))
        if all(base) and num and hk: by_number_name[(*base,num,hk)]=r
        if all(base) and hk: by_horse_by_race[base][hk].append(r)
        if text(r.get('runner_key')): by_key[text(r.get('runner_key'))]=r
    return {'by_number_name':by_number_name,'by_horse_by_race':by_horse_by_race,'by_key':by_key}

def match_provider(row,idx,alias,provider_to_canonical):
    base=provider_base(row,alias); num=number_text(row.get('provider_runner_number') or row.get('runner_number')); hk=normalise(row.get('provider_horse') or row.get('provider_horse_name') or row.get('horse'))
    if all(base) and num and hk:
        m=idx['by_number_name'].get((*base,num,hk))
        if m: return m,'MATCHED','EXACT_DATE_TRACK_RACE_RUNNER_NUMBER_AND_NAME','ALL_KEYS_MATCHED'
    pid=text(row.get('provider_runner_id')); prior=provider_to_canonical.get(pid)
    if pid and prior and prior in idx['by_key']:
        return idx['by_key'][prior],'MATCHED','PROVIDER_ID_CONTINUITY','PROVIDER_RUNNER_ID_PREVIOUSLY_LINKED_TO_CANONICAL_RUNNER'
    if all(base) and hk:
        cand=idx['by_horse_by_race'].get(base,{}).get(hk,[])
        if len(cand)==1: return cand[0],'MATCHED','CONTROLLED_RACE_SCOPED_NAME_FALLBACK','RUNNER_NUMBER_UNAVAILABLE_OR_MISMATCH_UNIQUE_RACE_SCOPED_NAME'
        if len(cand)>1: return None,'UNMATCHED','CONTROLLED_RACE_SCOPED_NAME_FALLBACK','AMBIGUOUS_RACE_SCOPED_NAME'
    race_bases={race_base(r) for r in idx['by_key'].values()}; tracks={b[1] for b in race_bases}
    if base[1] not in tracks: return None,'UNMATCHED','NO_MATCH','OUTSIDE_EDGEIQ_PRODUCT_CATALOG'
    if base not in race_bases: return None,'UNMATCHED','NO_MATCH','MISSING_CANONICAL_RACE'
    if num: return None,'UNMATCHED','NO_MATCH','RUNNER_NUMBER_OR_NAME_MISMATCH'
    return None,'UNMATCHED','NO_MATCH','RUNNER_NUMBER_UNAVAILABLE_NO_SAFE_NAME_MATCH'

def latest_runtime_rows(rows):
    grouped={}
    for r in rows:
        key=(text(r.get('provider_race_id')),text(r.get('provider_runner_id')))
        if not all(key): continue
        if key not in grouped or text(r.get('edgeiq_observed_at'))>=text(grouped[key].get('edgeiq_observed_at')): grouped[key]=r
    return list(grouped.values())

def canonical_base(row,meeting_map,race_map):
    mk=text(row.get('meeting_key')) or f"{text(row.get('race_date'))}|{normalise(row.get('display_track') or row.get('track'))}"
    rk=text(row.get('race_key')) or f"{mk}|R{number_text(row.get('race_no'))}"
    m=meeting_map.get(mk,{}); r=race_map.get(rk,{})
    return {'race_date':text(row.get('race_date')),'canonical_meeting_id':mk,'canonical_meeting_key':mk,'canonical_meeting_name':text(m.get('meeting') or row.get('display_track') or row.get('track')),'canonical_track':normalise(row.get('display_track') or row.get('track')),'canonical_race_id':rk,'canonical_race_key':rk,'race_number':number_text(row.get('race_no') or row.get('race_number')),'advertised_start':text(r.get('raceTime') or row.get('race_time')),'actual_start':'','race_status':'','canonical_runner_id':text(row.get('runner_id')) or text(row.get('runner_key')),'canonical_runner_key':text(row.get('runner_key')),'runner_number':number_text(row.get('runner_number') or row.get('saddlecloth') or row.get('horse_no')),'horse_name':text(row.get('horse') or row.get('runner')),'normalised_horse_name':normalise(row.get('horse') or row.get('runner') or row.get('horse_key')),'is_scratched':'true' if text(row.get('is_scratched')).lower()=='true' or text(row.get('runner_status')).upper() in {'SCRATCHED','SCR'} else 'false','scratch_time':''}

def availability(row,base):
    if text(row.get('is_scratched')).lower()=='true' or base.get('is_scratched')=='true': return 'SCRATCHED','SCRATCHED','CURRENT_PROVIDER_OBSERVATION' if row else 'CATALOG_STATUS'
    if money(row.get('fixed_win')): return 'LIVE_MARKET','LIVE_MARKET','CURRENT_PROVIDER_OBSERVATION'
    if money(row.get('recent_price') or row.get('opening_price')): return 'MARKET_SNAPSHOT','MARKET_SNAPSHOT','CURRENT_PROVIDER_OBSERVATION'
    return 'MARKET_UNAVAILABLE','MARKET_UNAVAILABLE','NO_PROVIDER_MATCH'

def append_canonical_history(rows):
    existing=read_csv(CANONICAL_HISTORY); keys={(text(r.get('canonical_runner_id')),text(r.get('edgeiq_observed_at'))) for r in existing}; new=[]
    for r in rows:
        if not text(r.get('canonical_runner_id')) or not text(r.get('edgeiq_observed_at')): continue
        key=(text(r.get('canonical_runner_id')),text(r.get('edgeiq_observed_at')))
        if key in keys: continue
        payload='|'.join(text(r.get(f)) for f in ['canonical_runner_id','edgeiq_observed_at','fixed_win','fixed_place','race_status','is_scratched'])
        new.append({'observation_id':hashlib.sha256(payload.encode()).hexdigest()[:24],'edgeiq_observed_at':text(r.get('edgeiq_observed_at')),'race_date':text(r.get('race_date')),'canonical_meeting_id':text(r.get('canonical_meeting_id')),'canonical_meeting_key':text(r.get('canonical_meeting_key')),'canonical_race_id':text(r.get('canonical_race_id')),'canonical_race_key':text(r.get('canonical_race_key')),'canonical_runner_id':text(r.get('canonical_runner_id')),'canonical_runner_key':text(r.get('canonical_runner_key')),'runner_number':text(r.get('runner_number')),'horse_name':text(r.get('horse_name')),'provider_runner_id':text(r.get('provider_runner_id')),'fixed_win':money(r.get('fixed_win')),'fixed_place':money(r.get('fixed_place')),'race_status':text(r.get('race_status')),'is_scratched':text(r.get('is_scratched')),'payload_hash':hashlib.sha256(payload.encode()).hexdigest()})
        keys.add(key)
    all_rows=existing+new; all_rows.sort(key=lambda r:(text(r.get('canonical_runner_id')),text(r.get('edgeiq_observed_at'))))
    write_csv(CANONICAL_HISTORY,all_rows,HISTORY_FIELDS); return all_rows

def history_movement(rows):
    by=defaultdict(list); out={}
    for r in rows:
        if text(r.get('canonical_runner_id')): by[text(r.get('canonical_runner_id'))].append(r)
    for rid,items in by.items():
        items.sort(key=lambda r:text(r.get('edgeiq_observed_at')))
        for i,r in enumerate(items):
            prev=None
            for j in range(i-1,-1,-1):
                if money(items[j].get('fixed_win')): prev=items[j]; break
            cur=money(r.get('fixed_win')); prior=money(prev.get('fixed_win')) if prev else ''
            if cur and prior:
                d=float(cur)-float(prior); pct=(d/float(prior))*100 if float(prior) else 0
                out[(rid,text(r.get('edgeiq_observed_at')))]={'previous_fixed_win':prior,'price_movement':f'{d:+.2f}','price_movement_percent':f'{pct:+.2f}','price_movement_status':'DERIVED_FROM_EDGEIQ_CANONICAL_OBSERVATION_HISTORY'}
    return out

def write_schema_inventory(runtime,current):
    dest={'provider_horse':'provider_horse_name','provider_runner_number':'provider_runner_number','fixed_win':'fixed_win','fixed_place':'fixed_place','opening_price':'opening_price','high_price':'high_price','low_price':'low_price','recent_price':'recent_price','price_timestamp':'price_timestamp','edgeiq_observed_at':'edgeiq_observed_at','flucs_untimestamped':'flucs_untimestamped','flucs_with_timestamp':'flucs_with_timestamp','provider_meeting_id':'provider_meeting_id','provider_race_id':'provider_race_id','provider_runner_id':'provider_runner_id','track':'canonical_track/provider_meeting_name','race_no':'race_number','horse':'horse_name','runner_number':'runner_number','runner_id':'canonical_runner_id','runner_key':'canonical_runner_key','meeting_key':'canonical_meeting_id','race_key':'canonical_race_id'}
    rows=[]
    for path,data in [(RAW_RUNTIME,runtime),(RACE_FIELDS,current)]:
        fields=list(data[0].keys()) if data else []
        for f in fields:
            samples=[text(r.get(f)) for r in data if text(r.get(f))][:3]; non=sum(1 for r in data if text(r.get(f)))
            rows.append({'source_file':str(path.relative_to(ROOT)),'field_name':f,'semantic_meaning':dest.get(f,'source context or compatibility field'),'current_data_type':'string','nullable_state':'NONBLANK' if data and non==len(data) else 'NULLABLE','nonblank_rows':non,'rows':len(data),'canonical_destination_field':dest.get(f,''),'consumer_files':'edgeiq_current_market_v1.csv; edgeiq_market_terminal_feed_v1.csv; edgeiq_form_guide_enriched_v2.json; race_fields.csv; edgeiq_overview_terminal_feed_v1.csv','known_mismatch':'canonical runner_number blank in raw runtime' if f=='runner_number' and path==RAW_RUNTIME else '','example_values':' | '.join(samples)})
    write_csv(SCHEMA_CSV,rows,['source_file','field_name','semantic_meaning','current_data_type','nullable_state','nonblank_rows','rows','canonical_destination_field','consumer_files','known_mismatch','example_values'])
    write_json(SCHEMA_JSON,{'schema_version':'edgeiq_ladbrokes_market_schema_inventory_v1','generated_at':now_utc(),'rows':rows})
    SCHEMA_MD.parent.mkdir(parents=True,exist_ok=True); SCHEMA_MD.write_text('# EDGEiQ Ladbrokes Market Schema Inventory V1\n\nCanonical contract source: public/data/edgeiq_current_market_v1.csv\n\nFields inventoried: '+str(len(rows))+'\n',encoding='utf-8')

def main():
    generated_at=now_utc(); current=read_csv(RACE_FIELDS); runtime=read_csv(RAW_RUNTIME); rawhist=read_csv(RAW_HISTORY)
    if not current: raise RuntimeError(f'Missing current EDGEiQ product runners: {RACE_FIELDS}')
    meetings,races=catalog_maps(); alias=build_alias(current,runtime); idx=build_indices(current)
    provider_to_canonical={}; current_keys=set(idx['by_key'].keys())
    for r in runtime:
        pid=text(r.get('provider_runner_id')); key=text(r.get('canonical_runner_key'))
        if pid and key in current_keys: provider_to_canonical[pid]=key
    latest=latest_runtime_rows(runtime); matched_by_key={}; provider_unmatched=[]; canonical_obs=[]
    for r in latest:
        m,js,method,reason=match_provider(r,idx,alias,provider_to_canonical)
        if m:
            base=canonical_base(m,meetings,races); market_status,avail,fresh=availability(r,base); out={f:'' for f in CANONICAL_FIELDS}; out.update(base)
            out.update({'generated_at':generated_at,'edgeiq_observed_at':text(r.get('edgeiq_observed_at')) or generated_at,'actual_start':text(r.get('actual_start')),'race_status':text(r.get('race_status')),'runner_number':base.get('runner_number') or number_text(r.get('provider_runner_number')),'provider':'LADBROKES','provider_meeting_id':text(r.get('provider_meeting_id')),'provider_meeting_name':text(r.get('track')),'provider_race_id':text(r.get('provider_race_id')),'provider_runner_id':text(r.get('provider_runner_id')),'provider_runner_number':number_text(r.get('provider_runner_number')),'provider_horse_name':text(r.get('provider_horse')),'fixed_win':money(r.get('fixed_win')),'fixed_place':money(r.get('fixed_place')),'opening_price':money(r.get('opening_price')),'high_price':money(r.get('high_price')),'low_price':money(r.get('low_price')),'recent_price':money(r.get('recent_price')),'price_timestamp':text(r.get('price_timestamp')),'flucs_untimestamped':text(r.get('flucs_untimestamped')),'flucs_with_timestamp':text(r.get('flucs_with_timestamp')),'fluctuation_status':text(r.get('fluctuation_status')) or 'FLUCTUATION_UNAVAILABLE','is_scratched':'true' if text(r.get('is_scratched')).lower()=='true' or base.get('is_scratched')=='true' else 'false','scratch_time':text(r.get('scratch_time')),'market_status':market_status,'market_availability_status':avail,'market_freshness_status':fresh,'source_priority_rank':'1','source_confidence':'HIGH' if money(r.get('fixed_win')) else 'MEDIUM','join_status':js,'join_reason':reason,'meeting_match_method':'DATE_TRACK_ALIAS_REGISTRY','race_match_method':'DATE_TRACK_RACE_NUMBER','runner_match_method':method,'match_conflicts':'0','raw_publication_status':'CANONICAL_PRODUCT_ROW_ONLY_RAW_PROVIDER_NOT_PUBLIC','track':base['canonical_meeting_name'],'meeting_name':base['canonical_meeting_name'],'race_no':base['race_number'],'horse':base['horse_name'],'market':money(r.get('fixed_win')),'price':money(r.get('fixed_win')),'market_source':'LADBROKES_CANONICAL_MARKET_V1','market_observed_at':text(r.get('edgeiq_observed_at')) or generated_at})
            if base['canonical_runner_key'] not in matched_by_key or text(out.get('edgeiq_observed_at'))>=text(matched_by_key[base['canonical_runner_key']].get('edgeiq_observed_at')): matched_by_key[base['canonical_runner_key']]=out
            canonical_obs.append(out); provider_to_canonical[text(r.get('provider_runner_id'))]=base['canonical_runner_key']
        else:
            provider_unmatched.append({'generated_at':generated_at,'edgeiq_observed_at':text(r.get('edgeiq_observed_at')),'race_date':text(r.get('race_date')),'provider_meeting_id':text(r.get('provider_meeting_id')),'provider_meeting_name':text(r.get('track')),'provider_race_id':text(r.get('provider_race_id')),'provider_runner_id':text(r.get('provider_runner_id')),'provider_runner_number':number_text(r.get('provider_runner_number')),'provider_horse_name':text(r.get('provider_horse')),'fixed_win':money(r.get('fixed_win')),'fixed_place':money(r.get('fixed_place')),'race_status':text(r.get('race_status')),'provider_track_key':provider_base(r,alias)[1],'provider_race_no':number_text(r.get('race_no')),'join_reason':reason,'meeting_match_method':'DATE_TRACK_ALIAS_REGISTRY','race_match_method':'DATE_TRACK_RACE_NUMBER' if reason!='OUTSIDE_EDGEIQ_PRODUCT_CATALOG' else 'NO_CANONICAL_MEETING','runner_match_method':method,'raw_publication_status':'PROVIDER_ONLY_QUARANTINED_NOT_PUBLIC'})
    for h in rawhist:
        key=provider_to_canonical.get(text(h.get('provider_runner_id'))); src=idx['by_key'].get(key or '')
        if not src: continue
        base=canonical_base(src,meetings,races)
        canonical_obs.append({**base,'edgeiq_observed_at':text(h.get('observed_at')),'provider_runner_id':text(h.get('provider_runner_id')),'fixed_win':money(h.get('fixed_win')),'fixed_place':money(h.get('fixed_place')),'race_status':text(h.get('race_status')),'is_scratched':text(h.get('is_scratched'))})
    history=append_canonical_history(canonical_obs); moves=history_movement(history); output=[]
    for src in current:
        base=canonical_base(src,meetings,races); out=matched_by_key.get(base['canonical_runner_key'])
        if out:
            out.update(moves.get((base['canonical_runner_id'],text(out.get('edgeiq_observed_at'))),{'price_movement_status':'INSUFFICIENT_EDGEIQ_CANONICAL_OBSERVATIONS'})); output.append({f:out.get(f,'') for f in CANONICAL_FIELDS}); continue
        market_status,avail,fresh=availability({},base); fallback={f:'' for f in CANONICAL_FIELDS}; fallback.update(base); fallback.update({'generated_at':generated_at,'provider':'LADBROKES','market_status':market_status,'market_availability_status':avail,'market_freshness_status':fresh,'source_priority_rank':'1','source_confidence':'NONE','join_status':'CANONICAL_RUNNER_NO_PROVIDER_MATCH','join_reason':'MARKET_UNAVAILABLE_FOR_CANONICAL_RUNNER','meeting_match_method':'DATE_TRACK_ALIAS_REGISTRY','race_match_method':'DATE_TRACK_RACE_NUMBER','runner_match_method':'NO_PROVIDER_MATCH','match_conflicts':'0','raw_publication_status':'CANONICAL_PRODUCT_ROW_ONLY_NO_PROVIDER_ROW','track':base['canonical_meeting_name'],'meeting_name':base['canonical_meeting_name'],'race_no':base['race_number'],'horse':base['horse_name'],'market_source':'LADBROKES_CANONICAL_MARKET_V1'}); output.append(fallback)
    output.sort(key=lambda r:(text(r.get('race_date')),text(r.get('canonical_track')),int(number_text(r.get('race_number')) or 0),int(number_text(r.get('runner_number')) or 9999),text(r.get('horse_name'))))
    write_csv(OUT_CSV,output,CANONICAL_FIELDS); write_json(OUT_JSON,{'schemaVersion':'edgeiq_current_market_v1','generatedAt':generated_at,'productionPricingChanged':'NO','records':output}); write_csv(OUT_PROVIDER_UNMATCHED,provider_unmatched,PROVIDER_UNMATCHED_FIELDS)
    hist_counter=Counter(r.get('canonical_runner_id') for r in history if text(r.get('canonical_runner_id'))); repeated=sum(1 for _,c in hist_counter.items() if c>=2); distinct=len({text(r.get('edgeiq_observed_at')) for r in history if text(r.get('edgeiq_observed_at'))}); movement=sum(1 for r in output if r.get('price_movement_status')=='DERIVED_FROM_EDGEIQ_CANONICAL_OBSERVATION_HISTORY'); matched=sum(1 for r in output if r.get('join_status')=='MATCHED'); fw=sum(1 for r in output if money(r.get('fixed_win'))); fp=sum(1 for r in output if money(r.get('fixed_place')))
    summary=[{'metric':'status','value':'EDGEIQ_CURRENT_MARKET_V1_BUILT'},{'metric':'generated_at','value':generated_at},{'metric':'canonical_runner_rows','value':len(output)},{'metric':'current_edgeiq_runner_rows','value':len(current)},{'metric':'runtime_provider_rows','value':len(runtime)},{'metric':'latest_provider_rows','value':len(latest)},{'metric':'matched_current_edgeiq_runners','value':matched},{'metric':'unmatched_current_edgeiq_runners','value':len(output)-matched},{'metric':'provider_only_unmatched_rows','value':len(provider_unmatched)},{'metric':'fixed_win_rows','value':fw},{'metric':'fixed_place_rows','value':fp},{'metric':'canonical_history_rows','value':len(history)},{'metric':'distinct_observation_timestamps','value':distinct},{'metric':'repeat_observation_runner_count','value':repeated},{'metric':'movement_rows','value':movement},{'metric':'production_pricing_changed','value':'NO'}]
    write_csv(OUT_SUMMARY,summary,['metric','value']); write_csv(OUT_OBS_SUMMARY,summary,['metric','value']); write_schema_inventory(runtime,current)
    print(json.dumps({r['metric']:r['value'] for r in summary},indent=2))
if __name__=='__main__': main()
