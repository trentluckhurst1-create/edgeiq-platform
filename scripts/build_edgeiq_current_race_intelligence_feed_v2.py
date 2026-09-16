from __future__ import annotations
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
ENTRY = DATA / 'edgeiq_race_entry_fact_v1.csv'
OUT = DATA / 'edgeiq_race_intelligence_feed_v2.csv'
FIELDS = ['race_id','race_date','venue','race_number','runner_id','horse_id','horse_name','projected_performance_score','epi','err','edgeiq_price','form_strength_score','market_signal','benchmark_context','performance_context']

def main() -> None:
    if not ENTRY.exists():
        raise SystemExit(f'MISSING_CURRENT_RACE_ENTRY_FACT: {ENTRY}')
    with ENTRY.open('r', encoding='utf-8-sig', newline='') as handle:
        entries = list(csv.DictReader(handle))
    if not entries:
        raise SystemExit('EMPTY_CURRENT_RACE_ENTRY_FACT')
    rows=[]
    for r in entries:
        horse_id=r.get('canonical_runner_id','')
        rows.append({
            'race_id':r.get('canonical_race_id',''), 'race_date':r.get('race_date',''), 'venue':r.get('canonical_track',''),
            'race_number':r.get('race_number',''), 'runner_id':horse_id, 'horse_id':horse_id, 'horse_name':r.get('runner_name',''),
            'projected_performance_score':'', 'epi':'', 'err':'', 'edgeiq_price':'', 'form_strength_score':'', 'market_signal':'',
            'benchmark_context':'CURRENT_ENTRY', 'performance_context':'GOVERNED_PERFORMANCE_UNAVAILABLE_IN_PAGES_CI'
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open('w', encoding='utf-8', newline='') as handle:
        writer=csv.DictWriter(handle, fieldnames=FIELDS, lineterminator='\n'); writer.writeheader(); writer.writerows(rows)
    dates=sorted({r['race_date'] for r in rows if r['race_date']})
    races=len({r['race_id'] for r in rows if r['race_id']})
    print(f'CURRENT_RACE_INTELLIGENCE_FEED_V2 rows={len(rows)} races={races} dates={dates}')

if __name__ == '__main__':
    main()
