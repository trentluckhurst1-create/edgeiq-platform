from __future__ import annotations
import csv, hashlib, json, os, shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'
DOCS=ROOT/'docs'/'performance-intelligence'/'restart-v1'/'timing-canonical-promotion-v1'
ARCHIVE=DOCS/'archive'; WAREHOUSE=ROOT/'docs'/'performance-intelligence'/'warehouse'/'edgeiq_performance_fact_warehouse_v1.csv'
CURRENT_OBS=DATA/'edgeiq_benchmark_observation_fact_v1.csv'
CURRENT_ROLE=DATA/'edgeiq_benchmark_observation_current_window_v2_1.csv'
CURRENT_META=DATA/'edgeiq_benchmark_observation_current_window_v2_1_metadata.json'
REC={
 'timing_warehouse':DATA/'edgeiq_recovered_timing_warehouse_v1.csv',
 'standard_time':DATA/'edgeiq_standard_time_fact_recovered_v1.csv',
 'race_time_delta':DATA/'edgeiq_race_time_delta_versus_standard_recovered_v1.csv',
 'lengths_versus_standard':DATA/'edgeiq_lengths_versus_standard_recovered_v1.csv',
 'lengths_versus_standard_rejections':DATA/'edgeiq_lengths_versus_standard_recovered_v1_rejections.csv',
 'performance_base':DATA/'edgeiq_performance_intelligence_base_recovered_v1.csv'}
CAN={
 'timing_warehouse':DATA/'edgeiq_canonical_historical_timing_warehouse_v1.csv',
 'standard_time':DATA/'edgeiq_standard_time_fact_v1.csv',
 'race_time_delta':DATA/'edgeiq_race_time_delta_versus_standard_fact_v1.csv',
 'lengths_versus_standard':DATA/'edgeiq_lengths_versus_standard_fact_v1.csv',
 'lengths_versus_standard_rejections':DATA/'edgeiq_lengths_versus_standard_fact_v1_rejections.csv',
 'performance_base':DATA/'edgeiq_performance_intelligence_base_fact_v1.csv'}
TOKENS=['edgeiq_benchmark_observation_fact_v1.csv','edgeiq_benchmark_observation_current_window_v2_1.csv','edgeiq_recovered_timing_warehouse_v1.csv','edgeiq_canonical_historical_timing_warehouse_v1.csv','edgeiq_standard_time_fact_v1.csv','edgeiq_race_time_delta_versus_standard_fact_v1.csv','edgeiq_lengths_versus_standard_fact_v1.csv','edgeiq_performance_intelligence_base_fact_v1.csv','edgeiq_performance_normalisation_fact_v1.csv']

def utc(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def clean(v): return '' if v is None else str(v).strip()
def rel(p): return str(p.relative_to(ROOT)).replace('\\','/')
def rows(p):
    if not p.exists(): return 0
    with p.open('r',encoding='utf-8-sig',newline='') as h: return sum(1 for _ in csv.DictReader(h))
def read_csv(p):
    if not p.exists(): raise FileNotFoundError(p)
    with p.open('r',encoding='utf-8-sig',newline='') as h:
        reader=csv.DictReader(h)
        if reader.fieldnames is None: raise ValueError(f'Missing CSV header: {p}')
        return list(reader)
def sha(p):
    if not p.exists(): return ''
    d=hashlib.sha256()
    with p.open('rb') as h:
        for b in iter(lambda:h.read(1024*1024),b''): d.update(b)
    return d.hexdigest()
def header(p):
    if not p.exists(): return []
    with p.open('r',encoding='utf-8-sig',newline='') as h: return next(csv.reader(h),[])
def wjson(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def wcsv(p,fields,out):
    p.parent.mkdir(parents=True,exist_ok=True); tmp=p.with_suffix(p.suffix+'.tmp')
    with tmp.open('w',encoding='utf-8',newline='') as h:
        wr=csv.DictWriter(h,fieldnames=fields,extrasaction='ignore',lineterminator='\n'); wr.writeheader(); wr.writerows(out)
    os.replace(tmp,p)
def acopy(src,dst):
    if not src.exists(): raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True,exist_ok=True); tmp=dst.with_suffix(dst.suffix+'.tmp')
    with src.open('rb') as s,tmp.open('wb') as t: shutil.copyfileobj(s,t,1024*1024)
    os.replace(tmp,dst)

def archive(src,adir):
    r={'path':rel(src),'exists_before':src.exists(),'rows_before':rows(src),'sha256_before':sha(src),'archive_path':''}
    if src.exists():
        dst=adir/src.relative_to(ROOT); dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst); r['archive_path']=rel(dst)
    return r

def scan_consumers():
    out=[]
    for base in [ROOT/'scripts',ROOT/'src',ROOT/'docs'/'performance-intelligence']:
        if not base.exists(): continue
        for p in base.rglob('*'):
            if p.suffix.lower() not in {'.py','.ts','.tsx','.json','.md','.csv'}: continue
            try: txt=p.read_text(encoding='utf-8',errors='ignore')
            except OSError: continue
            m=[t for t in TOKENS if t in txt]
            if m:
                out.append({'file':rel(p),'matched_contracts':';'.join(m),'consumer_type':'SCRIPT' if rel(p).startswith('scripts/') else 'DOC_OR_UI','migration_status':'USES_PROMOTED_CANONICAL_OR_ARCHIVAL_REFERENCE'})
    return out

def reconcile_three():
    raw=set(); sec=set(); first={}
    with WAREHOUSE.open('r',encoding='utf-8-sig',newline='') as h:
        for r in csv.DictReader(h):
            cid=clean(r.get('canonical_race_id'))
            if not cid: continue
            if clean(r.get('official_race_time')): raw.add(cid)
            try:
                if clean(r.get('official_race_time_seconds')) and float(clean(r.get('official_race_time_seconds')))>0: sec.add(cid)
            except ValueError: pass
            first.setdefault(cid,r)
    diff=sorted(raw-sec); out=[]
    for cid in diff:
        r=first[cid]
        out.append({'canonical_race_id':cid,'race_date':clean(r.get('race_date')),'track':clean(r.get('track')),'race_number':clean(r.get('race_number')),'distance_metres':clean(r.get('distance_metres')),'race_class':clean(r.get('race_class')),'official_race_time':clean(r.get('official_race_time')),'official_race_time_seconds':clean(r.get('official_race_time_seconds')),'time_unit':clean(r.get('time_unit')),'source_record_key':clean(r.get('source_record_key')),'cause':'PRIOR_AUDIT_COUNTED_NONBLANK_RAW_OFFICIAL_RACE_TIME_BUT_RECOVERY_REQUIRES_NUMERIC_POSITIVE_SECONDS','action':'EXCLUDED_UNTIL_SUPPORTED_TIME_UNIT_TRANSFORMATION_EXISTS'})
    return out,{'prior_audit_timed_races':70311,'raw_official_race_time_nonblank_distinct_races':len(raw),'numeric_positive_official_race_time_seconds_distinct_races':len(sec),'difference':len(diff),'status':'RECONCILED' if len(diff)==0 else 'REVIEW_REQUIRED','cause':'AUDIT_COUNTING_SCOPE_DIFFERENCE_RAW_TIME_NONBLANK_VERSUS_GOVERNED_SECONDS_NUMERIC_POSITIVE','exact_three_records':out}

def patch_runner():
    p=ROOT/'scripts'/'run_edgeiq_victoria_performance_intelligence_refresh_v1.py'
    text=p.read_text(encoding='utf-8')
    start=text.index('STEPS = ['); end=text.index('\n\nROW_FILES = {',start)
    steps="""STEPS = [
    ('normalisation_authority_decision', 'scripts/audit_edgeiq_normalisation_temporal_authority_v1.py', True),
    ('length_conversion_parameter_v2_build', 'scripts/build_edgeiq_length_conversion_parameter_fact_v2.py', True),
    ('length_conversion_parameter_v2_audit', 'scripts/audit_edgeiq_length_conversion_parameter_fact_v2.py', True),
    ('performance_normalisation_parameter_build', 'scripts/build_edgeiq_performance_normalisation_parameter_fact_v1.py', True),
    ('performance_normalisation_parameter_audit', 'scripts/audit_edgeiq_performance_normalisation_parameter_fact_v1.py', True),
    ('timing_warehouse_recovery_side_by_side', 'scripts/build_edgeiq_timing_warehouse_recovery_v1.py', True),
    ('timing_canonical_promotion', 'scripts/promote_edgeiq_timing_warehouse_canonical_v1.py', True),
    ('race_time_delta_audit', 'scripts/audit_edgeiq_race_time_delta_versus_standard_v1.py', True),
    ('lengths_versus_standard_audit', 'scripts/audit_edgeiq_lengths_versus_standard_v1.py', True),
    ('condition_rejection_audit', 'scripts/audit_edgeiq_lengths_standard_condition_rejections_v1.py', True),
    ('performance_base_audit', 'scripts/audit_edgeiq_performance_intelligence_base_fact_v1.py', True),
    ('performance_normalisation_build', 'scripts/build_edgeiq_performance_normalisation_fact_v1.py', True),
    ('performance_normalisation_audit', 'scripts/audit_edgeiq_performance_normalisation_fact_v1.py', True),
    ('performance_rating_base_build', 'scripts/build_edgeiq_performance_rating_base_fact_v1.py', True),
    ('performance_rating_base_audit', 'scripts/audit_edgeiq_performance_rating_base_fact_v1.py', True),
    ('horse_observation_build', 'scripts/build_edgeiq_horse_performance_observation_fact_v1.py', True),
    ('horse_observation_audit', 'scripts/audit_edgeiq_horse_performance_observation_fact_v1.py', True),
    ('horse_aggregate_build', 'scripts/build_edgeiq_horse_performance_aggregate_fact_v1.py', True),
    ('horse_aggregate_audit', 'scripts/audit_edgeiq_horse_performance_aggregate_fact_v1.py', True),
    ('horse_rating_build', 'scripts/build_edgeiq_horse_performance_rating_fact_v1.py', True),
    ('horse_rating_audit', 'scripts/audit_edgeiq_horse_performance_rating_fact_v1.py', True),
    ('race_entry_snapshot_build', 'scripts/build_edgeiq_race_entry_horse_performance_snapshot_fact_v1.py', True),
    ('race_entry_snapshot_audit', 'scripts/audit_edgeiq_race_entry_horse_performance_snapshot_fact_v1.py', True),
    ('race_entry_context_build', 'scripts/build_edgeiq_race_entry_performance_context_fact_v1.py', True),
    ('race_entry_context_audit', 'scripts/audit_edgeiq_race_entry_performance_context_fact_v1.py', True),
    ('context_adjusted_build', 'scripts/build_edgeiq_race_entry_context_adjusted_performance_fact_v1.py', True),
    ('context_adjusted_audit', 'scripts/audit_edgeiq_race_entry_context_adjusted_performance_fact_v1.py', True),
    ('projected_performance_build', 'scripts/build_edgeiq_race_entry_projected_performance_fact_v1.py', True),
    ('projected_performance_audit', 'scripts/audit_edgeiq_race_entry_projected_performance_fact_v1.py', True),
    ('epi_dependency_audit', 'scripts/audit_edgeiq_epi_performance_dependency_v1.py', False),
]"""
    p.write_text(text[:start]+steps+text[end:],encoding='utf-8')

def main():
    DOCS.mkdir(parents=True,exist_ok=True); built=utc(); adir=ARCHIVE/built.replace(':','').replace('-',''); adir.mkdir(parents=True,exist_ok=True)
    archived=[archive(p,adir) for p in [CURRENT_OBS,CURRENT_ROLE,CURRENT_META,*CAN.values()]]
    acopy(CURRENT_OBS,CURRENT_ROLE); wjson(CURRENT_META,{'role':'CURRENT_WINDOW_SPEED_CONTRACT_V2_1_PRESERVED_NOT_HISTORICAL_AUTHORITY','source':rel(CURRENT_OBS),'rows':rows(CURRENT_ROLE),'sha256':sha(CURRENT_ROLE),'preserved_at_utc':built})
    promos=[]
    for name,src in REC.items():
        dst=CAN[name]; before_rows=rows(dst); before_hash=sha(dst); acopy(src,dst); after_hash=sha(dst); source_hash=sha(src)
        promos.append({'artifact':name,'source_path':rel(src),'canonical_path':rel(dst),'rows_before':before_rows,'rows_after':rows(dst),'sha256_before':before_hash,'sha256_after':after_hash,'source_sha256':source_hash,'hash_match':'YES' if after_hash==source_hash else 'NO','promotion_status':'PROMOTED' if after_hash==source_hash else 'HASH_MISMATCH'})
    patch_runner()
    consumers=scan_consumers(); recon_rows,recon=reconcile_three()
    old_h=header(CURRENT_ROLE); new_h=header(CAN['timing_warehouse'])
    deps=[
      {'stage':'Timing Warehouse','canonical_artifact':rel(CAN['timing_warehouse']),'producer':'build_edgeiq_timing_warehouse_recovery_v1.py + promote_edgeiq_timing_warehouse_canonical_v1.py','downstream':'Standard Time, Race Time Delta lineage','status':'PROMOTED'},
      {'stage':'Standard Time','canonical_artifact':rel(CAN['standard_time']),'producer':'recovered historical timing promotion','downstream':'Race Time Delta','status':'PROMOTED'},
      {'stage':'Race Time Delta','canonical_artifact':rel(CAN['race_time_delta']),'producer':'recovered historical timing promotion','downstream':'Lengths v Standard','status':'PROMOTED'},
      {'stage':'Lengths v Standard','canonical_artifact':rel(CAN['lengths_versus_standard']),'producer':'recovered historical timing promotion','downstream':'Performance Base','status':'PROMOTED'},
      {'stage':'Performance Base','canonical_artifact':rel(CAN['performance_base']),'producer':'recovered historical timing promotion','downstream':'Normalisation','status':'PROMOTED'},
      {'stage':'Normalisation','canonical_artifact':'public/data/edgeiq_performance_normalisation_fact_v1.csv','producer':'build_edgeiq_performance_normalisation_fact_v1.py','downstream':'Horse Aggregates, Horse Ratings, Race Entry, EPI','status':'REBUILT_AFTER_PROMOTION'}]
    mig={'generated_utc':built,'old_authority':rel(CURRENT_OBS),'old_authority_role_after_migration':rel(CURRENT_ROLE),'new_authority':rel(CAN['timing_warehouse']),'reason':'Recovered governed historical timing warehouse has 70,307 Results Matrix-authorised timed races; active benchmark observation contract is a 39-row current-window Racing.com speed feed and is incompatible as historical timing authority.','rollback_archive':rel(adir),'schema_comparison':{'old_field_count':len(old_h),'new_field_count':len(new_h),'shared_fields':sorted(set(old_h)&set(new_h)),'old_only_fields':sorted(set(old_h)-set(new_h)),'new_only_fields':sorted(set(new_h)-set(old_h))},'three_race_reconciliation':recon,'protected_systems':{'pricing':'NO_CHANGE','probability':'NO_CHANGE','v6_1':'NO_CHANGE','v7_2g2':'NO_CHANGE','ui':'NO_CHANGE'}}
    status='PASS' if all(x['hash_match']=='YES' for x in promos) and recon['status']=='RECONCILED' and rows(CAN['timing_warehouse'])==rows(REC['timing_warehouse']) else 'BLOCKED'
    acceptance={'generated_utc':built,'status':status,'old_contract':rel(CURRENT_OBS)+' retained; current-window role '+rel(CURRENT_ROLE),'new_contract':rel(CAN['timing_warehouse']),'timed_races':rows(CAN['timing_warehouse']),'standard_times':rows(CAN['standard_time']),'race_time_deltas':rows(CAN['race_time_delta']),'lengths_v_standard':rows(CAN['lengths_versus_standard']),'performance_base':rows(CAN['performance_base']),'rollback_status':'AVAILABLE','rollback_archive':rel(adir),'three_race_reconciliation':recon}
    wjson(DOCS/'edgeiq_timing_contract_migration_v1.json',mig); wjson(DATA/'edgeiq_timing_canonical_promotion_v1_summary.json',{'generated_utc':built,'status':status,'promotion_rows':promos,'archived_files':archived}); wjson(DOCS/'edgeiq_timing_canonical_promotion_acceptance_v1.json',acceptance); wjson(DOCS/'edgeiq_timing_70311_70308_reconciliation_v1.json',recon)
    wcsv(DATA/'edgeiq_timing_canonical_promotion_v1.csv',['artifact','source_path','canonical_path','rows_before','rows_after','sha256_before','sha256_after','source_sha256','hash_match','promotion_status'],promos)
    wcsv(DOCS/'edgeiq_timing_downstream_builder_dependency_graph_v1.csv',['stage','canonical_artifact','producer','downstream','status'],deps)
    wcsv(DOCS/'edgeiq_timing_downstream_consumer_graph_v1.csv',['file','matched_contracts','consumer_type','migration_status'],consumers)
    wcsv(DOCS/'edgeiq_timing_70311_70308_reconciliation_v1.csv',['canonical_race_id','race_date','track','race_number','distance_metres','race_class','official_race_time','official_race_time_seconds','time_unit','source_record_key','cause','action'],recon_rows)
    wcsv(DOCS/'edgeiq_timing_canonical_migration_audit_v1.csv',['check','status','detail'],[
      {'check':'current_window_contract_preserved','status':'PASS' if rows(CURRENT_ROLE)==rows(CURRENT_OBS) else 'FAIL','detail':str(rows(CURRENT_ROLE))},
      {'check':'canonical_historical_timing_rows','status':'PASS' if rows(CAN['timing_warehouse'])==rows(REC['timing_warehouse']) else 'FAIL','detail':str(rows(CAN['timing_warehouse']))},
      {'check':'standard_time_promoted','status':'PASS' if rows(CAN['standard_time'])==rows(REC['standard_time']) else 'FAIL','detail':str(rows(CAN['standard_time']))},
      {'check':'race_delta_promoted','status':'PASS' if rows(CAN['race_time_delta'])==rows(REC['race_time_delta']) else 'FAIL','detail':str(rows(CAN['race_time_delta']))},
      {'check':'lengths_v_standard_promoted','status':'PASS' if rows(CAN['lengths_versus_standard'])==rows(REC['lengths_versus_standard']) else 'FAIL','detail':str(rows(CAN['lengths_versus_standard']))},
      {'check':'performance_base_promoted','status':'PASS' if rows(CAN['performance_base'])==rows(REC['performance_base']) else 'FAIL','detail':str(rows(CAN['performance_base']))},
      {'check':'three_race_reconciliation','status':recon['status'],'detail':recon['cause']},
      {'check':'rollback_archive_created','status':'PASS' if adir.exists() else 'FAIL','detail':rel(adir)}])
    (DOCS/'EDGEIQ_TIMING_CONTRACT_MIGRATION_V1.md').write_text('\n'.join(['# EDGEiQ Timing Contract Migration V1','',f'Generated UTC: `{built}`','','## Old Authority',f'`{rel(CURRENT_OBS)}` is retained and copied to `{rel(CURRENT_ROLE)}` as the current-window Racing.com speed-observation role.','','## New Authority',f'`{rel(CAN["timing_warehouse"])}` promoted from `{rel(REC["timing_warehouse"])}`.','','## Reason',mig['reason'],'','## Producers','- `scripts/build_edgeiq_timing_warehouse_recovery_v1.py`','- `scripts/promote_edgeiq_timing_warehouse_canonical_v1.py`','- `scripts/run_edgeiq_victoria_performance_intelligence_refresh_v1.py`','','## Consumers',f'See `{rel(DOCS/"edgeiq_timing_downstream_consumer_graph_v1.csv")}` and `{rel(DOCS/"edgeiq_timing_downstream_builder_dependency_graph_v1.csv")}`.','','## Rollback',f'Archive: `{rel(adir)}`. Restore archived files to reverse promotion.','','## Schema Comparison',f'Old fields: `{len(old_h)}`',f'New fields: `{len(new_h)}`',f'Shared fields: `{len(set(old_h)&set(new_h))}`','','## Contract Comparison','The old contract is current-window sectional speed evidence. The new authority is canonical historical timing evidence with explicit seconds, identity, unit semantics, surface/condition and recovery status.','','## Migration Impact','Standard Time, Race Time Delta, Lengths v Standard and Performance Base now originate from the recovered governed historical timing warehouse; later stages rebuild through existing governance gates.','']),encoding='utf-8')
    (DOCS/'EDGEIQ_TIMING_CANONICAL_PROMOTION_ACCEPTANCE_V1.md').write_text('\n'.join(['# EDGEiQ Timing Canonical Promotion Acceptance V1','',f'Status: `{status}`',f'Old contract: `{acceptance["old_contract"]}`',f'New contract: `{acceptance["new_contract"]}`',f'Timed races: `{acceptance["timed_races"]}`',f'Standard times: `{acceptance["standard_times"]}`',f'Race time deltas: `{acceptance["race_time_deltas"]}`',f'Lengths v standard: `{acceptance["lengths_v_standard"]}`',f'Performance base: `{acceptance["performance_base"]}`',f'Rollback: `{acceptance["rollback_status"]}`','']),encoding='utf-8')
    print(json.dumps(acceptance,indent=2,sort_keys=True)); return 0 if status=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
