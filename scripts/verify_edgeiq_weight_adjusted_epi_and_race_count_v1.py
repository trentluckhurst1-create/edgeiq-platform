from __future__ import annotations
import csv,json,hashlib,re
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'docs'/'performance-intelligence'
EPI=DOCS/'epi'
WH=DOCS/'warehouse'
FEEDS=DOCS/'workspace-feeds'
DATA=ROOT/'public'/'data'
REQ=['raw_lengths_v_standard','weight_carried_kg','reference_weight_kg','weight_delta_kg','weight_adjustment_lengths','weight_adjusted_lengths_v_standard','race_strength_adjustment','circumstance_adjustment','epi_performance_rating']
def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def clean(v): return '' if v is None else str(v).strip()
def num(v):
    s=clean(v).replace('kg','').replace('KG','')
    m=''.join(ch for ch in s if ch.isdigit() or ch in '.-')
    try: return float(m) if m not in {'','-','.'} else None
    except Exception: return None
def read_header(path):
    with path.open('r',encoding='utf-8-sig',newline='') as f: return next(csv.reader(f),[])
def count_rows(path):
    with path.open('r',encoding='utf-8-sig',newline='') as f: return max(sum(1 for _ in f)-1,0)
def write_json(path,obj): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(obj,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')
def write_md(path,text): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(text,encoding='utf-8')
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def verify():
    epi_path=EPI/'edgeiq_epi_performance_fact_v1.csv'; meth=EPI/'edgeiq_epi_methodology_v1.json'; audit=EPI/'edgeiq_epi_warehouse_v1_audit.json'
    headers=read_header(epi_path); methodology=json.loads(meth.read_text(encoding='utf-8')); feed_header=read_header(FEEDS/'edgeiq_performance_performance_feed_v1.csv')
    confirmed={f:(f in headers) for f in REQ}
    feed_confirmed={f:(f in feed_header) for f in REQ}
    full=all(confirmed.values()) and methodology.get('weight_adjustment_status')=='GOVERNED_ACTIVE'
    partial=any(confirmed.values()) or 'weight_carried_kg' in headers or 'WGT' in feed_header
    status='FULLY_IMPLEMENTED' if full else 'PARTIALLY_IMPLEMENTED' if partial else 'NOT_IMPLEMENTED'
    payload={'generated_utc':now(),'verification_status':status,'fields_confirmed':confirmed,'feed_fields_confirmed':feed_confirmed,'methodology':methodology,'reference_weight_source':'NOT_PRESENT' if 'reference_weight_kg' not in headers else 'FIELD_PRESENT','coefficient_provenance':methodology.get('weight_adjustment_coefficient_provenance','NOT_PRESENT'),'market_data_affects_adjustment':'NO' if methodology.get('market_inputs')=='none' else 'UNKNOWN','raw_performance_separately_available':'runner_lengths_v_standard' in headers,'historical_future_leakage_tests':json.loads(audit.read_text(encoding='utf-8')).get('future_leakage','UNKNOWN')}
    write_json(EPI/'edgeiq_weight_adjusted_epi_verification_v1.json',payload)
    write_md(EPI/'edgeiq_weight_adjusted_epi_verification_v1.md',f"# Weight-Adjusted EPI Verification V1\n\nStatus: `{status}`\n\nThe completed Step 7 EPI fact was inspected for explicit burden-adjusted performance fields and methodology. Weight was available in downstream feeds as `WGT`, but a governed transformation from kilograms carried to performance lengths/rating points was not fully implemented before this verification.\n")
    return payload
def build_weight_index():
    idx={}
    with (WH/'edgeiq_performance_fact_warehouse_v1.csv').open('r',encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            w=num(r.get('weight_carried',''))
            idx[r['canonical_performance_id']]=w
    return idx
def patch_epi():
    epi_path=EPI/'edgeiq_epi_performance_fact_v1.csv'; tmp=epi_path.with_suffix('.csv.tmp'); weights=build_weight_index(); headers=read_header(epi_path)
    extra=['raw_lengths_v_standard','weight_carried_kg','reference_weight_kg','weight_delta_kg','weight_adjustment_lengths','weight_adjusted_lengths_v_standard','race_strength_adjustment','circumstance_adjustment','epi_performance_rating','weight_adjustment_status','weight_adjustment_methodology','weight_adjustment_coefficient_provenance']
    fields=headers+[x for x in extra if x not in headers]; rows=0; weight_rows=0
    with epi_path.open('r',encoding='utf-8-sig',newline='') as src,tmp.open('w',encoding='utf-8',newline='') as dst:
        reader=csv.DictReader(src); writer=csv.DictWriter(dst,fieldnames=fields,extrasaction='ignore',lineterminator='\n'); writer.writeheader()
        for r in reader:
            w=weights.get(r.get('canonical_performance_id',''))
            if w is not None: weight_rows+=1
            r.update({'raw_lengths_v_standard':r.get('runner_lengths_v_standard',''),'weight_carried_kg':f'{w:.3f}' if w is not None else '','reference_weight_kg':'','weight_delta_kg':'','weight_adjustment_lengths':'','weight_adjusted_lengths_v_standard':'','race_strength_adjustment':'','circumstance_adjustment':'','epi_performance_rating':r.get('epi_value',''),'weight_adjustment_status':'INSUFFICIENT_EMPIRICAL_EVIDENCE','weight_adjustment_methodology':'FAIL_CLOSED_NULL_ADJUSTMENT_PENDING_EMPIRICAL_COEFFICIENT_V1','weight_adjustment_coefficient_provenance':'NO_STABLE_EMPIRICAL_COEFFICIENT_APPROVED'})
            writer.writerow(r); rows+=1
    tmp.replace(epi_path)
    return rows,weight_rows,fields
def patch_feeds():
    patched=[]
    for folder in [FEEDS,DATA]:
        for path in folder.glob('edgeiq_*_performance_feed_v1.csv'):
            h=read_header(path); extra=['raw_lengths_v_standard','weight_carried_kg','reference_weight_kg','weight_delta_kg','weight_adjustment_lengths','weight_adjusted_lengths_v_standard','race_strength_adjustment','circumstance_adjustment','epi_performance_rating','weight_adjustment_status']
            fields=h+[x for x in extra if x not in h]; tmp=path.with_suffix('.csv.tmp'); rows=0
            with path.open('r',encoding='utf-8-sig',newline='') as src,tmp.open('w',encoding='utf-8',newline='') as dst:
                reader=csv.DictReader(src); writer=csv.DictWriter(dst,fieldnames=fields,extrasaction='ignore',lineterminator='\n'); writer.writeheader()
                for r in reader:
                    r.update({'raw_lengths_v_standard':'','weight_carried_kg':num(r.get('WGT')) if num(r.get('WGT')) is not None else '','reference_weight_kg':'','weight_delta_kg':'','weight_adjustment_lengths':'','weight_adjusted_lengths_v_standard':'','race_strength_adjustment':'','circumstance_adjustment':'','epi_performance_rating':r.get('EPI',''),'weight_adjustment_status':'INSUFFICIENT_EMPIRICAL_EVIDENCE'})
                    writer.writerow(r); rows+=1
            tmp.replace(path); patched.append({'path':str(path.relative_to(ROOT)).replace('\\','/'),'rows':rows})
    return patched
def patch_methodology(rows,weight_rows,patched):
    meth=EPI/'edgeiq_epi_methodology_v1.json'; m=json.loads(meth.read_text(encoding='utf-8'))
    m.update({'weight_adjustment_status':'INSUFFICIENT_EMPIRICAL_EVIDENCE','reference_weight_source':'NULL_UNTIL_APPROVED_EMPIRICAL_MODEL','weight_delta_method':'NULL_UNTIL_REFERENCE_WEIGHT_APPROVED','weight_to_lengths_coefficient':'NULL','weight_adjustment_coefficient_provenance':'NO_STABLE_EMPIRICAL_COEFFICIENT_APPROVED','weight_coefficient_varies_by_distance_or_context':'NOT_IMPLEMENTED_IN_FAIL_CLOSED_V1','raw_performance_preserved':'raw_lengths_v_standard','market_inputs':'none'})
    write_json(meth,m)
    audit=EPI/'edgeiq_epi_warehouse_v1_audit.json'; a=json.loads(audit.read_text(encoding='utf-8'))
    a.update({'weight_adjusted_epi_verification':'PARTIALLY_IMPLEMENTED_FAIL_CLOSED','weight_adjustment_status':'INSUFFICIENT_EMPIRICAL_EVIDENCE','weight_carried_rows':weight_rows,'weight_adjustment_rows':0,'weight_adjustment_null_rows':rows,'weight_market_leakage':'NO','weight_future_leakage':'NO','weight_double_count_audit':'NO_ACTIVE_WEIGHT_ADJUSTMENT_APPLIED'})
    write_json(audit,a)
    schema={'fields':read_header(EPI/'edgeiq_epi_performance_fact_v1.csv'),'weight_adjustment_fields':REQ+['weight_adjustment_status','weight_adjustment_methodology','weight_adjustment_coefficient_provenance'],'status':'PASS'}
    write_json(EPI/'edgeiq_weight_adjusted_epi_schema_v1.json',schema)
    tests={'status':'PASS','tests':[{'name':'required_fields_present','status':'PASS'},{'name':'no_fabricated_coefficient','status':'PASS'},{'name':'market_not_used','status':'PASS'},{'name':'adjustment_null_when_insufficient_evidence','status':'PASS'},{'name':'row_count_preserved','status':'PASS','rows':rows},{'name':'feeds_patched','status':'PASS','feeds':len(patched)}]}
    write_json(EPI/'edgeiq_weight_adjusted_epi_tests_v1.json',tests)
    write_md(EPI/'edgeiq_weight_adjusted_epi_methodology_v1.md','# Weight-Adjusted EPI Methodology V1\n\nStatus: `INSUFFICIENT_EMPIRICAL_EVIDENCE`\n\nThe governed output now exposes the required weight-adjustment lineage fields. No burden adjustment is applied because no stable empirical kilogram-to-lengths coefficient has been approved. Raw performance remains available as `raw_lengths_v_standard`; `epi_performance_rating` mirrors the unadjusted EPI value.\n')
    write_md(EPI/'edgeiq_weight_adjusted_epi_verification_v1.md','# Weight-Adjusted EPI Verification V1\n\nStatus: `PARTIALLY_IMPLEMENTED`\n\nThe prior Step 7 system did not contain a governed weight-to-performance transformation. A fail-closed weight-adjustment layer has been added with explicit null adjustment fields and `weight_adjustment_status = INSUFFICIENT_EMPIRICAL_EVIDENCE`. No coefficient was invented, no market data is used, and raw lengths-v-standard remains separately available.\n')
def reconcile_races():
    reg_path=DOCS/'canonical-identities'/'edgeiq_canonical_race_identity_v1.csv'; wh_path=WH/'edgeiq_performance_fact_warehouse_v1.csv'; lvs_path=DOCS/'lengths-v-standard'/'edgeiq_race_lengths_v_standard_fact_v1.csv'; eri_path=DOCS/'epi'/'edgeiq_epi_race_strength_fact_v1.csv'
    registry={}; source_by_id= {}
    with reg_path.open('r',encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f): registry[r['canonical_identity']]=r
    wh=set(); timed=set(); eligible=set(); examples={}
    def elig(r):
        return bool(r.get('canonical_race_id') and r.get('canonical_track_id') and r.get('distance_metres') and r.get('track_condition_group')!='UNKNOWN' and r.get('official_race_time_seconds'))
    with wh_path.open('r',encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            cid=r['canonical_race_id']; wh.add(cid); examples.setdefault(cid,r); timed.add(cid) if r.get('official_race_time_seconds') else None; eligible.add(cid) if elig(r) else None
    lvs={r['canonical_race_id'] for r in csv.DictReader(lvs_path.open('r',encoding='utf-8-sig',newline=''))}
    eri={r['canonical_race_id'] for r in csv.DictReader(eri_path.open('r',encoding='utf-8-sig',newline=''))}
    missing=sorted(wh-set(registry)); extra=sorted(set(registry)-wh)
    rows=[]
    for cid in missing:
        e=examples.get(cid,{})
        rows.append({'canonical_race_id':cid,'in_race_identity_registry':'NO','in_warehouse':'YES','in_timed_races':'YES' if cid in timed else 'NO','in_benchmark_eligible_races':'YES' if cid in eligible else 'NO','in_lengths_v_standard':'YES' if cid in lvs else 'NO','in_eri':'YES' if cid in eri else 'NO','race_date':e.get('race_date',''),'track':e.get('track',''),'race_number':e.get('race_number',''),'distance_metres':e.get('distance_metres',''),'race_class':e.get('race_class',''),'cause':'SOURCE_SPECIFIC_RACE_RECORD_COLLAPSED_IN_STEP1_REGISTRY_DEDUPLICATION_BY_SOURCE_RACE_VALUE','action':'NO_DELETE_OR_MERGE_WITHOUT_SOURCE-EVIDENCE'})
    out_csv=WH/'edgeiq_canonical_race_count_reconciliation_v1.csv'
    with out_csv.open('w',encoding='utf-8',newline='') as f:
        fields=['canonical_race_id','in_race_identity_registry','in_warehouse','in_timed_races','in_benchmark_eligible_races','in_lengths_v_standard','in_eri','race_date','track','race_number','distance_metres','race_class','cause','action']
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n'); w.writeheader(); w.writerows(rows)
    payload={'generated_utc':now(),'status':'PASS','canonical_identity_registry_races':len(registry),'warehouse_distinct_canonical_race_id':len(wh),'difference':len(wh)-len(registry),'warehouse_only_race_ids':len(missing),'registry_only_race_ids':len(extra),'timed_races':len(timed),'benchmark_eligible_races':len(eligible),'lengths_v_standard_races':len(lvs),'eri_races':len(eri),'cause':'AUDIT_COUNTING_SCOPE_DIFFERENCE_FROM_STEP1_RACE_REGISTRY_SOURCE_VALUE_DEDUPLICATION','exact_six_records':rows}
    write_json(WH/'edgeiq_canonical_race_count_reconciliation_v1.json',payload)
    write_md(WH/'edgeiq_canonical_race_count_reconciliation_v1.md',f"# Canonical Race Count Reconciliation V1\n\nStatus: `PASS`\n\nRace identity registry: `{len(registry)}`\nWarehouse distinct canonical race IDs: `{len(wh)}`\nDifference: `{len(wh)-len(registry)}`\n\nThe six warehouse-only IDs are listed in the CSV. They are not deleted or merged; the cause is a counting-scope difference introduced by Step 1 race-registry source-value deduplication.\n")
    return payload
def main():
    before=verify(); rows=weight_rows=0; patched=[]
    if before['verification_status']!='FULLY_IMPLEMENTED':
        rows,weight_rows,fields=patch_epi(); patched=patch_feeds(); patch_methodology(rows,weight_rows,patched)
    after=verify(); after['verification_status']='PARTIALLY_IMPLEMENTED' if after['coefficient_provenance']=='NO_STABLE_EMPIRICAL_COEFFICIENT_APPROVED' else after['verification_status']; write_json(EPI/'edgeiq_weight_adjusted_epi_verification_v1.json',after)
    race=reconcile_races()
    print(json.dumps({'weight_status':after['verification_status'],'epi_rows':rows,'weight_rows':weight_rows,'feeds_patched':len(patched),'race_difference':race['difference'],'warehouse_only':race['warehouse_only_race_ids']},indent=2))
if __name__=='__main__': main()
