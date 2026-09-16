from __future__ import annotations
import csv,json,os,re
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=Path(os.environ.get('EDGEIQ_DATA_DIR',str(ROOT/'public'/'data')))
CATALOG=DATA/'edgeiq_three_day_product_catalog_v1.json'
RATINGS=DATA/'edgeiq_horse_performance_rating_fact_v1.csv'
OLD_EPI=DATA/'edgeiq_race_entry_epi_v2.csv'
OUT=DATA/'edgeiq_race_intelligence_feed_v2.csv'

def clean(v): return '' if v is None else str(v).strip()
def norm(v): return re.sub(r'[^A-Z0-9]+','',clean(v).upper())
def prior(date_value,target):
    try:return datetime.fromisoformat(clean(date_value)[:10]).date()<datetime.fromisoformat(target[:10]).date()
    except:return False
def rows(path):
    if not path.exists(): return []
    with path.open('r',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def deep(obj,keys,depth=0):
    if depth>5:return None
    if isinstance(obj,dict):
        for k in keys:
            if k in obj and obj[k] not in (None,''):return obj[k]
        for v in obj.values():
            x=deep(v,keys,depth+1)
            if x not in (None,''):return x
    elif isinstance(obj,list):
        for v in obj:
            x=deep(v,keys,depth+1)
            if x not in (None,''):return x
    return None

def main():
    if not CATALOG.exists(): raise SystemExit(f'missing current three-day catalog: {CATALOG}')
    catalog=json.loads(CATALOG.read_text(encoding='utf-8-sig'))
    rating_rows=rows(RATINGS); epi_rows=rows(OLD_EPI)
    ratings={}
    for r in rating_rows:
        hid=clean(r.get('canonical_horse_id'))
        if hid:ratings.setdefault(hid,[]).append(r)
    for v in ratings.values():v.sort(key=lambda r:clean(r.get('rating_as_of_date')))
    epi={(clean(r.get('canonical_race_id')),clean(r.get('canonical_runner_id'))):r for r in epi_rows}
    out=[]
    for m in catalog.get('meetings',[]) or []:
        date=clean(m.get('date')); track=clean(m.get('meeting') or m.get('track'))
        for race in m.get('races',[]) or []:
            rn=clean(race.get('raceNumber')); race_id=clean(race.get('canonicalRaceId') or race.get('canonical_race_id'))
            for node in race.get('runners',[]) or []:
                source=node.get('source') if isinstance(node,dict) and isinstance(node.get('source'),dict) else {}
                official=node.get('official') if isinstance(node,dict) and isinstance(node.get('official'),dict) else {}
                name=clean(source.get('horseName') or official.get('runner') or deep(node,['horseName','runnerName','name']))
                horse_code=clean(source.get('horseCode') or deep(source,['horseCode','horseId','horse_id']))
                runner_id=clean(deep(node,['canonical_runner_id','canonicalRunnerId'])) or (f'RCOM_HORSE_{horse_code}' if horse_code else '')
                candidates=[r for r in ratings.get(runner_id,[]) if prior(r.get('rating_as_of_date'),date)]
                rr=candidates[-1] if candidates else None
                er=epi.get((race_id,runner_id)) if race_id and runner_id else None
                hist=clean(rr.get('horse_performance_rating_value')) if rr else ''
                hist_status=clean(rr.get('horse_performance_rating_status')) if rr else 'SNAPSHOT_UNAVAILABLE'
                epi_value=clean(er.get('epi_value')) if er else ''; epi_rank=clean(er.get('epi_rank')) if er else ''
                epi_status=clean(er.get('epi_status')) if er else 'EPI_UNAVAILABLE'
                out.append({'race_intelligence_feed_id':f'LIVE|{date}|{norm(track)}|R{rn}|{runner_id or norm(name)}','canonical_race_id':race_id,'canonical_runner_id':runner_id,'canonical_horse_name':name,'race_date':date,'canonical_track':track,'race_number':rn,'barrier':clean(source.get('barrierNumber') or official.get('barrier')),'weight_kg':clean(source.get('weight') or official.get('weight')),'jockey_name':clean(source.get('jockeyName') or official.get('jockey')),'trainer_name':clean(source.get('trainerName') or official.get('trainer')),'entry_participation_status':'SCRATCHED' if source.get('scratched') else 'ACTIVE_ENTRY','historical_rating_value':hist,'suitability_composite_delta':'','projected_performance_value':'','epi_value':epi_value,'epi_rank':epi_rank,'historical_rating_status':hist_status,'suitability_status':'SUITABILITY_UNAVAILABLE','projected_performance_status':'PROJECTED_PERFORMANCE_UNAVAILABLE','epi_status':epi_status,'race_intelligence_status':'AVAILABLE_PARTIAL' if hist or epi_value else 'RACE_INTELLIGENCE_UNAVAILABLE','race_intelligence_reason_code':'CURRENT_DAY_PRIOR_ONLY','source_race_context_evidence_sha256':'','source_projected_performance_evidence_sha256':'','source_epi_evidence_sha256':'','race_intelligence_builder_version':'EDGEIQ_CURRENT_RACE_INTELLIGENCE_V3','race_intelligence_method_version':'STRICT_PRIOR_CURRENT_RUNNER_JOIN_V1','race_intelligence_evidence_sha256':''})
    fields=['race_intelligence_feed_id','canonical_race_id','canonical_runner_id','canonical_horse_name','race_date','canonical_track','race_number','barrier','weight_kg','jockey_name','trainer_name','entry_participation_status','historical_rating_value','suitability_composite_delta','projected_performance_value','epi_value','epi_rank','historical_rating_status','suitability_status','projected_performance_status','epi_status','race_intelligence_status','race_intelligence_reason_code','source_race_context_evidence_sha256','source_projected_performance_evidence_sha256','source_epi_evidence_sha256','race_intelligence_builder_version','race_intelligence_method_version','race_intelligence_evidence_sha256']
    with OUT.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(out)
    print(f'CURRENT_RACE_INTELLIGENCE_ROWS={len(out)} ERR_AVAILABLE={sum(bool(r["historical_rating_value"]) for r in out)} EPI_AVAILABLE={sum(bool(r["epi_value"]) for r in out)} DATA_DIR={DATA}')
if __name__=='__main__':main()
