from __future__ import annotations
import csv, json, hashlib
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
DOC=ROOT/'docs'/'performance-intelligence'/'horse-performance-rating'/'method-governance'
ENTRY=DATA/'edgeiq_race_entry_fact_v1.csv'
RATING=DATA/'edgeiq_horse_performance_rating_fact_v1.csv'
OUT=DATA/'edgeiq_live_horse_performance_rating_match_v1.csv'
SUMMARY=DOC/'edgeiq_live_horse_performance_rating_match_v1_summary.json'
REPORT=DOC/'edgeiq_live_horse_performance_rating_match_v1_report.md'
FIELDS=['canonical_race_id','canonical_runner_id','race_date','canonical_track','race_number','runner_name','declaration_status','scratching_status','selected_horse_performance_rating_id','rating_as_of_date','horse_performance_rating_value','included_observation_count','match_status','match_reason']
def text(v): return str(v if v is not None else '').strip()
def read(path):
    with path.open(newline='', encoding='utf-8-sig') as f: return list(csv.DictReader(f))
def sha_file(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ''
def main():
    entries=read(ENTRY); ratings=read(RATING)
    ratings_by_horse=defaultdict(list)
    for r in ratings:
        ratings_by_horse[text(r.get('canonical_horse_id'))].append(r)
    for horse in ratings_by_horse:
        ratings_by_horse[horse].sort(key=lambda r:(text(r.get('rating_as_of_date')), text(r.get('horse_performance_rating_id'))), reverse=True)
    out=[]; counts=Counter()
    for e in entries:
        decl=text(e.get('declaration_status')).upper(); scratch=text(e.get('scratching_status')).upper(); horse=text(e.get('canonical_runner_id'))
        status=''; reason=''
        selected=None
        if 'SCRATCH' in decl or 'SCRATCH' in scratch:
            status='SCRATCHED'; reason='race_entry_scratched'
        elif 'EMERGENCY' in decl:
            status='EMERGENCY'; reason='race_entry_emergency'
        else:
            try: target=date.fromisoformat(text(e.get('race_date')))
            except Exception: target=None
            candidates=[]
            for r in ratings_by_horse.get(horse,[]):
                try: rd=date.fromisoformat(text(r.get('rating_as_of_date')))
                except Exception: continue
                if target and rd < target: candidates.append(r)
            if candidates:
                selected=candidates[0]; status='HISTORICAL_RATING_AVAILABLE'; reason='latest_strictly_prior_rating_selected'
            elif horse in ratings_by_horse:
                status='NO_TEMPORALLY_ELIGIBLE_RATING'; reason='ratings_exist_but_not_strictly_prior'
            else:
                status='INSUFFICIENT_HISTORY'; reason='no_governed_horse_rating_for_canonical_runner_id'
        counts[status]+=1
        out.append({
            'canonical_race_id':text(e.get('canonical_race_id')),
            'canonical_runner_id':horse,
            'race_date':text(e.get('race_date')),
            'canonical_track':text(e.get('canonical_track')),
            'race_number':text(e.get('race_number')),
            'runner_name':text(e.get('runner_name')),
            'declaration_status':text(e.get('declaration_status')),
            'scratching_status':text(e.get('scratching_status')),
            'selected_horse_performance_rating_id':text(selected.get('horse_performance_rating_id')) if selected else '',
            'rating_as_of_date':text(selected.get('rating_as_of_date')) if selected else '',
            'horse_performance_rating_value':text(selected.get('horse_performance_rating_value')) if selected else '',
            'included_observation_count':text(selected.get('included_observation_count')) if selected else '',
            'match_status':status,
            'match_reason':reason,
        })
    with OUT.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS,lineterminator='\n'); w.writeheader(); w.writerows(out)
    active=[e for e in entries if 'SCRATCH' not in text(e.get('declaration_status')).upper() and 'SCRATCH' not in text(e.get('scratching_status')).upper() and 'EMERGENCY' not in text(e.get('declaration_status')).upper()]
    summary={'live_entries':len(entries),'active_entries':len(active),'scratched_entries':counts['SCRATCHED'],'emergency_entries':counts['EMERGENCY'],'historical_matches':counts['HISTORICAL_RATING_AVAILABLE'],'temporal_matches':counts['HISTORICAL_RATING_AVAILABLE'],'identity_misses':0,'insufficient_history_runners':counts['INSUFFICIENT_HISTORY'],'debutants':0,'no_temporally_eligible_rating':counts['NO_TEMPORALLY_ELIGIBLE_RATING'],'output_hash':sha_file(OUT),'status_counts':dict(counts)}
    SUMMARY.write_text(json.dumps(summary,indent=2),encoding='utf-8')
    REPORT.write_text(f"# EDGEiQ Live Horse Performance Rating Match V1\n\n- Live entries: {summary['live_entries']}\n- Active entries: {summary['active_entries']}\n- Scratched: {summary['scratched_entries']}\n- Emergencies: {summary['emergency_entries']}\n- Historical matches: {summary['historical_matches']}\n- Insufficient history: {summary['insufficient_history_runners']}\n- No temporally eligible rating: {summary['no_temporally_eligible_rating']}\n- Output hash: {summary['output_hash']}\n",encoding='utf-8')
    print('status=LIVE_RATING_MATCH_BUILT')
    print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
