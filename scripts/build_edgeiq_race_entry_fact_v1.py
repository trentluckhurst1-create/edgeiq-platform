import csv
csv.field_size_limit(1024 * 1024 * 64)
import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
TODAY = date.today()
DATA = ROOT / "public/data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
RACE_LIST = DATA / "edgeiq_vic_three_day_race_list_v1.csv"
OUT = DATA / "edgeiq_race_entry_fact_v1_CANDIDATE.csv"
REJECTED = DATA / "edgeiq_race_entry_fact_v1_rejected_v1.csv"
SUMMARY = DATA / "edgeiq_race_entry_fact_v1_candidate_summary.csv"

FIELDS = ["canonical_race_id","canonical_runner_id","race_date","meeting_date","canonical_track","course_identity","state","country","race_number","race_name","race_distance_metres","surface_group","track_condition_number","scheduled_start_time","saddlecloth_number","runner_name","barrier","weight_kg","jockey_name","trainer_name","declaration_status","scratching_status","source_updated_at","source_system","source_record_id","source_hash","audit_status"]
REJECT_FIELDS = ["race_date","track","race_number","runner_name","source_record_id","race_status","rejection_reason"]

def clean(v: Any) -> str:
    return "" if v is None else str(v).strip()
def track_key(v: Any) -> str:
    s=clean(v).upper()
    for x in ["SPORTSBET-", "SPORTSBET ", "LADBROKES ", "BET365 ", "BET365-", "SOUTHSIDE "]:
        s=s.replace(x,"")
    return re.sub(r"[^A-Z0-9]+","_",s).strip("_")
def metres(v: Any) -> str:
    m=re.search(r"\d+",clean(v)); return m.group(0) if m else ""
def kg(v: Any) -> str:
    m=re.search(r"\d+(?:\.\d+)?",clean(v)); return m.group(0) if m else ""
def parse_date(v: Any):
    s=clean(v)
    try: return datetime.fromisoformat(s[:10]).date()
    except Exception: return None
def iso_dt(v: Any) -> str:
    s=clean(v)
    if s.endswith('Z'): s=s[:-1]+'+00:00'
    try: return datetime.fromisoformat(s).isoformat()
    except Exception: return s
def condition_number(*values: Any) -> str:
    for v in values:
        m=re.search(r"\b(\d{1,2})\b",clean(v))
        if m: return m.group(1)
    return ""
def surface_group(track: str, condition: str) -> str:
    t=(track+' '+condition).upper()
    if 'SYNTH' in t or 'ALL WEATHER' in t:
        return 'AUSTRALIAN_SYNTHETIC'
    return 'TURF'
def row_hash(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode('utf-8')).hexdigest()
def canonical_race_id(race_date, course, race_no, dist, start):
    return f"RACE|{race_date}|{course}|R{race_no}|{dist}M|{start}"

def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as handle:
        return [dict(r) for r in csv.DictReader(handle)]

def race_list_lookup() -> Dict[tuple, Dict[str, str]]:
    lookup = {}
    for row in read_csv(RACE_LIST):
        key = (clean(row.get("race_date")), track_key(row.get("track") or row.get("normalised_track")), clean(row.get("race_no")))
        lookup[key] = row
    return lookup

def main():
    obj=json.loads(CATALOG.read_text(encoding='utf-8-sig'))
    generated_at=clean(obj.get('generatedAt')) if isinstance(obj,dict) else ''
    rows=[]; rejected=[]
    race_meta_lookup = race_list_lookup()
    for meeting in obj.get('meetings',[]) or []:
        mdate=clean(meeting.get('date'))
        d=parse_date(mdate)
        track=clean(meeting.get('meeting') or meeting.get('track'))
        course=track_key(track)
        for race in meeting.get('races',[]) or []:
            rn=clean(race.get('raceNumber'))
            meta = race_meta_lookup.get((mdate, course, rn), {})
            race_status=clean(race.get('raceStatus') or race.get('status') or meta.get('race_status'))
            dist=metres(race.get('distance') or meta.get('distance'))
            start=iso_dt(race.get('raceTime') or race.get('time') or meta.get('race_time_utc'))
            race_name=clean(race.get('raceName') or race.get('name') or meta.get('race_name'))
            condition=clean(race.get('trackCondition') or meta.get('track_condition'))
            if d is None or d < TODAY:
                race_reject='STALE_RACE_DATE'
            elif race_status.upper() != 'FINALFIELDS':
                race_reject=f'RACE_STATUS_NOT_FINALFIELDS:{race_status}'
            else:
                race_reject=''
            for node in race.get('runners') or []:
                official=node.get('official') if isinstance(node.get('official'),dict) else {}
                source=node.get('source') if isinstance(node.get('source'),dict) else {}
                horse=clean(source.get('horseName') or official.get('runner'))
                source_record_id=clean(source.get('id'))
                horse_code=clean(source.get('horseCode') or (source.get('horse') or {}).get('id') if isinstance(source.get('horse'),dict) else '')
                if race_reject:
                    rejected.append({'race_date':mdate,'track':track,'race_number':rn,'runner_name':horse,'source_record_id':source_record_id,'race_status':race_status,'rejection_reason':race_reject})
                    continue
                if not source_record_id or not horse_code or not horse:
                    rejected.append({'race_date':mdate,'track':track,'race_number':rn,'runner_name':horse,'source_record_id':source_record_id,'race_status':race_status,'rejection_reason':'IDENTITY_REQUIRED_FIELD_MISSING'})
                    continue
                scratched=bool(source.get('scratched') or official.get('scratched'))
                emergency=bool(source.get('emergency'))
                if scratched:
                    decl='SCRATCHED_ENTRY'; scratch='SCRATCHED'
                elif emergency:
                    decl='EMERGENCY_ENTRY'; scratch='ACTIVE'
                else:
                    decl='ACTIVE_ENTRY'; scratch='ACTIVE'
                row={
                    'canonical_race_id':canonical_race_id(mdate,course,rn,dist,start),
                    'canonical_runner_id':f'RCOM_HORSE_{horse_code}',
                    'race_date':mdate,
                    'meeting_date':mdate,
                    'canonical_track':course,
                    'course_identity':course,
                    'state':'VIC',
                    'country':'AUS',
                    'race_number':rn,
                    'race_name':race_name,
                    'race_distance_metres':dist,
                    'surface_group':surface_group(track, condition),
                    'track_condition_number':condition_number(race.get('trackRating'), meta.get('track_rating'), condition),
                    'scheduled_start_time':start,
                    'saddlecloth_number':clean(source.get('raceEntryNumber') or official.get('number') or official.get('no')),
                    'runner_name':horse,
                    'barrier':clean(source.get('barrierNumber') or official.get('barrier')),
                    'weight_kg':kg(source.get('weight') or official.get('weight')),
                    'jockey_name':clean(source.get('jockeyName') or official.get('jockey')),
                    'trainer_name':clean(source.get('trainerName') or official.get('trainer')),
                    'declaration_status':decl,
                    'scratching_status':scratch,
                    'source_updated_at':generated_at,
                    'source_system':'RACING_COM_GETRACEFORM',
                    'source_record_id':source_record_id,
                    'source_hash':row_hash(source),
                    'audit_status':'CANDIDATE',
                }
                rows.append(row)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with OUT.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    with REJECTED.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=REJECT_FIELDS); w.writeheader(); w.writerows(rejected)
    summary=[
        {'metric':'candidate_rows','value':len(rows)},
        {'metric':'rejected_rows','value':len(rejected)},
        {'metric':'candidate_races','value':len(set(r['canonical_race_id'] for r in rows))},
        {'metric':'active_entries','value':sum(1 for r in rows if r['declaration_status']=='ACTIVE_ENTRY')},
        {'metric':'scratched_entries','value':sum(1 for r in rows if r['declaration_status']=='SCRATCHED_ENTRY')},
        {'metric':'emergency_entries','value':sum(1 for r in rows if r['declaration_status']=='EMERGENCY_ENTRY')},
        {'metric':'source','value':'public/data/edgeiq_three_day_product_catalog_v1.json'},
    ]
    with SUMMARY.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows(summary)
    print(f"candidate_rows={len(rows)} rejected_rows={len(rejected)} races={summary[2]['value']}")
if __name__=='__main__': main()
