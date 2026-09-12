from __future__ import annotations
import csv
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
MATCHES=DATA/'edgeiq_sectional_crosswalk_raceid_v9_matches.csv'
OUT=DATA/'edgeiq_sectional_identity_promotion_v11.csv'
SUMMARY=DATA/'edgeiq_sectional_identity_promotion_v11_summary.csv'

def clean(v): return str(v or '').strip()

def main():
 if not MATCHES.exists(): raise SystemExit(f'Missing required V9 matches: {MATCHES}')
 counts=Counter(); rows=[]
 with MATCHES.open('r',newline='',encoding='utf-8-sig') as h:
  rd=csv.DictReader(h)
  for r in rd:
   counts['v9_match_rows']+=1
   rid=clean(r.get('recovered_race_id'))
   rn=clean(r.get('recovered_race_no'))
   disp=clean(r.get('race_no_disposition'))
   method=clean(r.get('identity_method'))
   if not rid:
    status='HOLD_NO_RACE_ID'; counts['hold_no_race_id']+=1
   elif disp=='RACE_ID_UNIQUE_RACE_NO_UNIQUE' and rn:
    status='PROMOTABLE_CERTIFIED_IDENTITY'; counts['promotable_certified_identity']+=1
   elif disp=='RACE_ID_UNIQUE_RACE_NO_CONFLICT':
    status='HOLD_RACE_NO_CONFLICT'; counts['hold_race_no_conflict']+=1
   elif disp=='RACE_ID_UNIQUE_RACE_NO_MISSING':
    status='HOLD_RACE_NO_MISSING'; counts['hold_race_no_missing']+=1
   else:
    status='HOLD_OTHER'; counts['hold_other']+=1
   rows.append({
    'source_file':r.get('source_file',''),'row_no':r.get('row_no',''),'race_date':r.get('race_date',''),'track':r.get('track',''),
    'horse_key':r.get('horse_key',''),'distance':r.get('distance',''),'recovered_race_id':rid,'recovered_race_no':rn,
    'identity_method':method,'race_no_disposition':disp,'promotion_status':status,
    'identity_confidence':'HIGH' if status=='PROMOTABLE_CERTIFIED_IDENTITY' else '',
    'identity_evidence':'V9_EXACT_UNIQUE_RACE_ID_AND_UNIQUE_RACE_NO' if status=='PROMOTABLE_CERTIFIED_IDENTITY' else ''
   })
 with OUT.open('w',newline='',encoding='utf-8') as h:
  f=list(rows[0]) if rows else ['source_file']; w=csv.DictWriter(h,fieldnames=f); w.writeheader(); w.writerows(rows)
 with SUMMARY.open('w',newline='',encoding='utf-8') as h:
  w=csv.writer(h); w.writerow(['metric','value'])
  for k,v in counts.items(): w.writerow([k,v])
  denom=counts['v9_match_rows'] or 1
  w.writerow(['promotion_rate_pct',round(100*counts['promotable_certified_identity']/denom,4)])
 print('='*90); print('EDGEIQ SECTIONAL IDENTITY PROMOTION AUDIT V11'); print('='*90)
 for k,v in counts.items(): print(f'{k}: {v}')
 print('promotion_rate_pct:',round(100*counts['promotable_certified_identity']/(counts['v9_match_rows'] or 1),4))
 print('OUT:',OUT); print('SUMMARY:',SUMMARY)
if __name__=='__main__': main()
