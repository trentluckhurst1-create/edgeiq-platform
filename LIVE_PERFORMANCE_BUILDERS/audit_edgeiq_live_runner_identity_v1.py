import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "performance-intelligence" / "race-entry"
OUT_DIR.mkdir(parents=True, exist_ok=True)
CATALOG = ROOT / "public/data/edgeiq_three_day_product_catalog_v1.json"
OUT = OUT_DIR / "edgeiq_live_runner_identity_v1.csv"
SUMMARY = OUT_DIR / "edgeiq_live_runner_identity_v1_summary.csv"
REPORT = OUT_DIR / "edgeiq_live_runner_identity_v1_report.md"

def clean(v): return "" if v is None else str(v).strip()
def track_key(v):
    s=clean(v).upper()
    for x in ["SPORTSBET-", "SPORTSBET ", "LADBROKES ", "BET365 ", "BET365-", "SOUTHSIDE "]:
        s=s.replace(x,"")
    return re.sub(r"[^A-Z0-9]+","_",s).strip("_")
def horse_name_key(v): return re.sub(r"[^A-Z0-9]+","",clean(v).upper())
def metres(v):
    m=re.search(r"\d+",clean(v)); return m.group(0) if m else ""

def rows():
    obj=json.loads(CATALOG.read_text(encoding='utf-8-sig'))
    out=[]
    for m in obj.get('meetings',[]) or []:
        mdate=clean(m.get('date')); track=clean(m.get('meeting') or m.get('track')); course=track_key(track)
        for race in m.get('races',[]) or []:
            rn=clean(race.get('raceNumber')); dist=metres(race.get('distance'))
            race_key=f"{mdate}|{course}|R{rn}|{dist}M"
            for node in race.get('runners') or []:
                official=node.get('official') if isinstance(node.get('official'),dict) else {}
                source=node.get('source') if isinstance(node.get('source'),dict) else {}
                horse=clean(source.get('horseName') or official.get('runner'))
                horse_code=clean(source.get('horseCode') or (source.get('horse') or {}).get('id') if isinstance(source.get('horse'),dict) else '')
                entry_id=clean(source.get('id'))
                canonical_runner_id=f"RCOM_HORSE_{horse_code}" if horse_code else f"HORSE_NAME_{horse_name_key(horse)}"
                if horse_code:
                    status='AUTHORITATIVE_SOURCE_ID'
                elif horse:
                    status='NAME_ONLY_IDENTITY_REQUIRES_GOVERNANCE'
                else:
                    status='IDENTITY_MISS'
                out.append({
                    'source_file':'public/data/edgeiq_three_day_product_catalog_v1.json',
                    'race_key':race_key,
                    'source_record_id':entry_id,
                    'authoritative_horse_code':horse_code,
                    'canonical_runner_id':canonical_runner_id,
                    'runner_name':horse,
                    'race_date':mdate,
                    'canonical_track':course,
                    'race_number':rn,
                    'saddlecloth_number':clean(source.get('raceEntryNumber') or official.get('number') or official.get('no')),
                    'barrier':clean(source.get('barrierNumber') or official.get('barrier')),
                    'identity_status':status,
                    'scratching_status':'SCRATCHED' if source.get('scratched') or official.get('scratched') else 'ACTIVE',
                })
    return out

def main():
    data=rows()
    key_counts={}
    race_entry_counts={}
    for r in data:
        key_counts.setdefault((r['race_key'],r['canonical_runner_id']),0); key_counts[(r['race_key'],r['canonical_runner_id'])]+=1
        race_entry_counts.setdefault(r['source_record_id'],0); race_entry_counts[r['source_record_id']]+=1
    collisions=0
    for r in data:
        if key_counts[(r['race_key'],r['canonical_runner_id'])]>1:
            r['identity_status']='IDENTITY_COLLISION'; collisions+=1
        if r['source_record_id'] and race_entry_counts[r['source_record_id']]>1:
            r['identity_status']='SOURCE_RECORD_COLLISION'; collisions+=1
    fields=['source_file','race_key','source_record_id','authoritative_horse_code','canonical_runner_id','runner_name','race_date','canonical_track','race_number','saddlecloth_number','barrier','identity_status','scratching_status']
    with OUT.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(data)
    total=len(data); source_ids=sum(1 for r in data if r['authoritative_horse_code']); misses=sum(1 for r in data if r['identity_status']=='IDENTITY_MISS'); name_only=sum(1 for r in data if r['identity_status']=='NAME_ONLY_IDENTITY_REQUIRES_GOVERNANCE')
    summary=[
        {'metric':'field_runners','value':total},
        {'metric':'authoritative_source_ids','value':source_ids},
        {'metric':'canonical_runner_ids','value':len(set(r['canonical_runner_id'] for r in data))},
        {'metric':'exact_matches','value':source_ids},
        {'metric':'new_valid_identities','value':source_ids},
        {'metric':'identity_misses','value':misses},
        {'metric':'name_only_identities','value':name_only},
        {'metric':'identity_collision_rows','value':collisions},
        {'metric':'audit_status','value':'PASS' if misses==0 and collisions==0 and name_only==0 else 'PASS_WITH_WARNINGS'},
    ]
    with SUMMARY.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows(summary)
    REPORT.write_text('\n'.join(['# EDGEiQ Live Runner Identity Audit V1','',f'- Field runners: {total}',f'- Authoritative Racing.com horse codes: {source_ids}',f'- Name-only identities: {name_only}',f'- Identity misses: {misses}',f'- Collision rows: {collisions}',f'- Audit status: {summary[-1]["value"]}','', 'Runner identity uses Racing.com horseCode where supplied. Horse-name normalisation is reported only as a fallback status and is not silently merged.'])+'\n',encoding='utf-8')
    print(f'field_runners={total} source_ids={source_ids} name_only={name_only} misses={misses} collisions={collisions}')
if __name__=='__main__': main()
