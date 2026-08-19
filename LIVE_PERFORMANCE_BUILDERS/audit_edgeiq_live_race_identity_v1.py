import csv
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "performance-intelligence" / "race-entry"
OUT_DIR.mkdir(parents=True, exist_ok=True)
CATALOG = ROOT / "public/data/edgeiq_three_day_product_catalog_v1.json"
OUT = OUT_DIR / "edgeiq_live_race_identity_v1.csv"
SUMMARY = OUT_DIR / "edgeiq_live_race_identity_v1_summary.csv"
REPORT = OUT_DIR / "edgeiq_live_race_identity_v1_report.md"

def clean(v): return "" if v is None else str(v).strip()
def track_key(v):
    s=clean(v).upper()
    for x in ["SPORTSBET-", "SPORTSBET ", "LADBROKES ", "BET365 ", "BET365-", "SOUTHSIDE "]:
        s=s.replace(x,"")
    s=re.sub(r"[^A-Z0-9]+","_",s).strip("_")
    return s
def metres(v):
    m=re.search(r"\d+",clean(v)); return m.group(0) if m else ""
def dt(v):
    s=clean(v)
    if s.endswith('Z'): s=s[:-1]+'+00:00'
    try: return datetime.fromisoformat(s).isoformat()
    except Exception: return s

def load_races():
    obj=json.loads(CATALOG.read_text(encoding='utf-8-sig'))
    rows=[]
    for m in obj.get('meetings',[]) or []:
        mdate=clean(m.get('date'))
        track=clean(m.get('meeting') or m.get('track'))
        course=track_key(track)
        for r in m.get('races',[]) or []:
            rn=clean(r.get('raceNumber'))
            dist=metres(r.get('distance'))
            start=dt(r.get('raceTime') or r.get('time'))
            race_id=clean(r.get('raceId') or r.get('id'))
            canonical=f"RACE|{mdate}|{course}|R{rn}|{dist}M|{start}"
            rows.append({
                'source_file':'public/data/edgeiq_three_day_product_catalog_v1.json',
                'source_race_id':race_id,
                'canonical_race_id':canonical,
                'race_date':mdate,
                'canonical_track':course,
                'course_identity':course,
                'race_number':rn,
                'race_distance_metres':dist,
                'race_start_time':start,
                'race_name':clean(r.get('raceName')),
                'race_status':clean(r.get('raceStatus') or r.get('status')),
                'declared_runner_count':len(r.get('runners') or []),
                'identity_status':'OK' if mdate and course and rn and dist else 'IDENTITY_MISS',
            })
    return rows

def main():
    rows=load_races()
    collisions={}
    for row in rows:
        collisions.setdefault(row['canonical_race_id'],[]).append(row)
    for row in rows:
        if len(collisions[row['canonical_race_id']])>1:
            row['identity_status']='IDENTITY_COLLISION'
    fields=['source_file','source_race_id','canonical_race_id','race_date','canonical_track','course_identity','race_number','race_distance_metres','race_start_time','race_name','race_status','declared_runner_count','identity_status']
    with OUT.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    source_races=len(rows); canonical=len(set(r['canonical_race_id'] for r in rows)); misses=sum(1 for r in rows if r['identity_status']=='IDENTITY_MISS'); collision_rows=sum(1 for r in rows if r['identity_status']=='IDENTITY_COLLISION')
    summary=[
        {'metric':'source_races','value':source_races},
        {'metric':'canonical_races','value':canonical},
        {'metric':'exact_identity_matches','value':source_races-misses-collision_rows},
        {'metric':'identity_misses','value':misses},
        {'metric':'identity_collision_rows','value':collision_rows},
        {'metric':'duplicate_race_keys','value':source_races-canonical},
        {'metric':'audit_status','value':'PASS' if misses==0 and collision_rows==0 else 'FAIL'},
    ]
    with SUMMARY.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows(summary)
    REPORT.write_text('\n'.join(['# EDGEiQ Live Race Identity Audit V1','',f'- Source races: {source_races}',f'- Canonical races: {canonical}',f'- Identity misses: {misses}',f'- Collision rows: {collision_rows}',f'- Audit status: {summary[-1]["value"]}','', 'Race identity uses date, canonical track/course, race number, distance and start time. Race name alone is not used.'])+'\n',encoding='utf-8')
    print(f'source_races={source_races} canonical_races={canonical} misses={misses} collisions={collision_rows}')
if __name__=='__main__': main()
