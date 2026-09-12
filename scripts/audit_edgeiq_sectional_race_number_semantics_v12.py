from __future__ import annotations
import csv
from collections import Counter, defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
MATCHES=DATA/'edgeiq_sectional_crosswalk_raceid_v9_matches.csv'
OUT=DATA/'edgeiq_sectional_race_number_semantics_v12.csv'
SUMMARY=DATA/'edgeiq_sectional_race_number_semantics_v12_summary.csv'

def clean(v): return str(v or '').strip()
def num(v):
 s=clean(v)
 try:return int(float(s))
 except:return None

def main():
 if not MATCHES.exists(): raise SystemExit(f'Missing required file: {MATCHES}')
 counts=Counter(); rows=[]; offsets=Counter(); by_source=defaultdict(Counter)
 with MATCHES.open('r',newline='',encoding='utf-8-sig') as h:
  rd=csv.DictReader(h)
  fields=rd.fieldnames or []
  # discover likely original/target race number columns retained by V9
  target_candidates=[f for f in fields if f.lower() in {'target_race_no','source_race_no','existing_race_no','sectional_race_no','race_no'}]
  print('FIELDS',fields)
  print('TARGET_RACE_NO_CANDIDATES',target_candidates)
  for r in rd:
   counts['rows']+=1
   recovered=num(r.get('recovered_race_no'))
   original=None; original_field=''
   for f in target_candidates:
    x=num(r.get(f))
    if x is not None:
     original=x; original_field=f; break
   if recovered is None:
    counts['missing_recovered_race_no']+=1
    continue
   if original is None:
    counts['missing_original_race_no']+=1
    rows.append({'source_file':r.get('source_file',''),'row_no':r.get('row_no',''),'race_date':r.get('race_date',''),'track':r.get('track',''),'horse_key':r.get('horse_key',''),'original_race_no':'','original_field':'','recovered_race_no':recovered,'offset':'','relation':'NO_ORIGINAL_RACE_NO','recovered_race_id':r.get('recovered_race_id','')})
    continue
   off=original-recovered; offsets[off]+=1; by_source[r.get('source_file','')][off]+=1
   relation='EQUAL' if off==0 else ('ORIGINAL_MINUS_RECOVERED_CONSTANT_CANDIDATE')
   counts['equal' if off==0 else 'conflict']+=1
   rows.append({'source_file':r.get('source_file',''),'row_no':r.get('row_no',''),'race_date':r.get('race_date',''),'track':r.get('track',''),'horse_key':r.get('horse_key',''),'original_race_no':original,'original_field':original_field,'recovered_race_no':recovered,'offset':off,'relation':relation,'recovered_race_id':r.get('recovered_race_id','')})
 with OUT.open('w',newline='',encoding='utf-8') as h:
  f=['source_file','row_no','race_date','track','horse_key','original_race_no','original_field','recovered_race_no','offset','relation','recovered_race_id'];w=csv.DictWriter(h,fieldnames=f);w.writeheader();w.writerows(rows)
 with SUMMARY.open('w',newline='',encoding='utf-8') as h:
  w=csv.writer(h);w.writerow(['metric','value'])
  for k,v in counts.items():w.writerow([k,v])
  for off,n in offsets.most_common():w.writerow([f'offset_{off}',n])
 print('='*90);print('EDGEIQ SECTIONAL RACE-NUMBER SEMANTICS AUDIT V12');print('='*90)
 for k,v in counts.items():print(f'{k}: {v}')
 print('OFFSET DISTRIBUTION:')
 for off,n in offsets.most_common(20):print(f'  {off:+d}: {n}')
 print('BY SOURCE:')
 for s,c in by_source.items(): print(s, dict(c.most_common(10)))
 print('OUT:',OUT);print('SUMMARY:',SUMMARY)
if __name__=='__main__':main()
