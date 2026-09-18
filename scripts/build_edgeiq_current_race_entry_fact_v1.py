from __future__ import annotations
import csv, hashlib, json, re
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'public/data/edgeiq_three_day_product_catalog_v1.json'
OUT=ROOT/'public/data/edgeiq_race_entry_fact_v1.csv'
FIELDS=['canonical_race_id','canonical_runner_id','race_date','meeting_date','canonical_track','course_identity','state','country','race_number','race_name','race_distance_metres','surface_group','track_condition_number','scheduled_start_time','saddlecloth_number','runner_name','barrier','weight_kg','jockey_name','trainer_name','declaration_status','scratching_status','source_updated_at','source_system','source_record_id','source_hash','audit_status']

def norm(v): return re.sub(r'[^A-Z0-9]+','_',str(v or '').upper()).strip('_')
def deep(obj, keys, depth=0):
    if depth>7:return None
    if isinstance(obj,dict):
        for k in keys:
            v=obj.get(k)
            if v not in (None,''):return v
        for v in obj.values():
            if isinstance(v,(dict,list)):
                x=deep(v,keys,depth+1)
                if x not in (None,''):return x
    elif isinstance(obj,list):
        for v in obj:
            x=deep(v,keys,depth+1)
            if x not in (None,''):return x
    return None

def official_value(r,*keys):
    official=r.get('official') if isinstance(r.get('official'),dict) else {}
    for k in keys:
        v=official.get(k)
        if v not in (None,''): return v
    for k in keys:
        v=r.get(k)
        if v not in (None,''): return v
    return deep(r.get('source') or {},list(keys))

def runner_name(r):
    return str(official_value(r,'runner','horseName','horse_name','runnerName','runner_name','horse','name') or '').strip()

def horse_id(r):
    raw=deep(r,['canonicalRunnerId','canonical_runner_id','horseId','horse_id','runnerId','runner_id','id'])
    s=str(raw or '')
    if s.startswith('RCOM_HORSE_'):return s
    digits=re.sub(r'\D','',s)
    if digits:return 'RCOM_HORSE_'+digits
    name=runner_name(r)
    return 'EDGEIQ_HORSE_'+hashlib.sha256(name.upper().encode()).hexdigest()[:16].upper()

def main():
    d=json.loads(CAT.read_text(encoding='utf-8-sig')); rows=[]; now=datetime.now(timezone.utc).isoformat()
    for m in d.get('meetings') or []:
        date=str(m.get('date') or '')[:10]; track=norm(m.get('meeting') or m.get('track') or m.get('meetingKey')); state=str(deep(m,['state','State']) or '').upper()
        for race in m.get('races') or []:
            rn=race.get('raceNumber'); dist=re.sub(r'\D','',str(race.get('distance') or '')); start=race.get('startTime') or race.get('raceTime') or ''
            rid=str(race.get('canonicalRaceId') or race.get('raceKey') or f'RACE|{date}|{track}|R{rn}|{dist}M|{start}')
            for i,r in enumerate(race.get('runners') or [],1):
                name=runner_name(r)
                scratched=bool(official_value(r,'scratched','isScratched') or str(official_value(r,'status') or '').upper()=='SCRATCHED')
                hid=horse_id(r)
                row={'canonical_race_id':rid,'canonical_runner_id':hid,'race_date':date,'meeting_date':date,'canonical_track':track,'course_identity':track,'state':state,'country':'AUS','race_number':rn,'race_name':race.get('raceName') or '','race_distance_metres':dist,'surface_group':'TURF','track_condition_number':re.sub(r'\D','',str(race.get('trackCondition') or m.get('trackCondition') or '')),'scheduled_start_time':start,'saddlecloth_number':official_value(r,'no','number','runnerNumber','runner_number') or i,'runner_name':name,'barrier':official_value(r,'barrier','barrierNumber','barrier_number') or '','weight_kg':official_value(r,'weight','weightKg','weight_kg') or '','jockey_name':official_value(r,'jockey','jockeyName','jockey_name') or '','trainer_name':official_value(r,'trainer','trainerName','trainer_name') or '','declaration_status':'SCRATCHED_ENTRY' if scratched else 'ACTIVE_ENTRY','scratching_status':'SCRATCHED' if scratched else 'ACTIVE','source_updated_at':now,'source_system':'EDGEIQ_LIVE_THREE_DAY_CATALOGUE','source_record_id':deep(r,['sourceRecordId','source_record_id','runnerId','runner_id','id']) or '','audit_status':'CANDIDATE'}
                row['source_hash']=hashlib.sha256(json.dumps(row,sort_keys=True,default=str).encode()).hexdigest(); rows.append(row)
    missing_names=[r for r in rows if not r['runner_name']]
    duplicate_ids=len(rows)-len({(r['canonical_race_id'],r['canonical_runner_id']) for r in rows})
    if missing_names: raise SystemExit(f'CURRENT_RACE_ENTRY_FACT missing runner names={len(missing_names)}')
    if duplicate_ids: raise SystemExit(f'CURRENT_RACE_ENTRY_FACT duplicate race/runner identities={duplicate_ids}')
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with OUT.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    print(f'CURRENT_RACE_ENTRY_FACT rows={len(rows)} races={len(set(r["canonical_race_id"] for r in rows))} named={len(rows)} identity_gate=PASS')
if __name__=='__main__':main()
