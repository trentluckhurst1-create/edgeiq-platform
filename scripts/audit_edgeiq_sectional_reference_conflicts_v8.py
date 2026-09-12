from __future__ import annotations
import csv,re
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'
MATCH=DATA/'edgeiq_sectional_crosswalk_match_v7_ambiguous.csv'
OUT=DATA/'edgeiq_sectional_reference_conflicts_v8.csv'; SUM=DATA/'edgeiq_sectional_reference_conflicts_v8_summary.csv'

def clean(x): return str(x or '').strip()
def canon_rid(x):
 s=clean(x)
 try:return str(int(float(s)))
 except:return re.sub(r'\D','',s)
def canon_rn(x):
 s=clean(x)
 try:return str(int(float(s)))
 except:return re.sub(r'\D','',s)
def main():
 if not MATCH.exists(): raise SystemExit(f'Missing {MATCH}')
 rows=[]; c=Counter()
 with MATCH.open('r',newline='',encoding='utf-8-sig') as h:
  rd=csv.DictReader(h)
  for r in rd:
   c['ambiguous_input_rows']+=1
   raw=clean(r.get('candidates'))
   parts=[p for p in raw.split('|') if p]
   parsed=[]
   for p in parts:
    if ':' in p:
     rn,rid=p.split(':',1); parsed.append((canon_rn(rn),canon_rid(rid)))
   unique_raw=set(parsed); unique_rids={rid for _,rid in parsed if rid}; unique_rns={rn for rn,_ in parsed if rn}
   if len(unique_rids)==1 and len(unique_rns)==1:
    disp='FORMAT_ONLY_SAME_CANONICAL_RACE'; c['format_only_same_canonical_race']+=1
   elif len(unique_rids)==1:
    disp='SAME_RACE_ID_CONFLICTING_RACE_NO'; c['same_race_id_conflicting_race_no']+=1
   elif len(unique_rns)==1:
    disp='SAME_RACE_NO_MULTIPLE_RACE_IDS'; c['same_race_no_multiple_race_ids']+=1
   else:
    disp='TRUE_CANONICAL_CONFLICT'; c['true_canonical_conflict']+=1
   rows.append({**r,'canonical_candidate_count':len(unique_raw),'canonical_race_id_count':len(unique_rids),'canonical_race_no_count':len(unique_rns),'conflict_disposition':disp,'canonical_candidates':'|'.join(sorted(f'{a}:{b}' for a,b in unique_raw))})
 fields=list(rows[0].keys()) if rows else ['conflict_disposition']
 with OUT.open('w',newline='',encoding='utf-8') as h:
  w=csv.DictWriter(h,fieldnames=fields);w.writeheader();w.writerows(rows)
 with SUM.open('w',newline='',encoding='utf-8') as h:
  w=csv.writer(h);w.writerow(['metric','value']);[w.writerow([k,v]) for k,v in c.items()]
 print('='*90);print('EDGEIQ SECTIONAL REFERENCE CONFLICT AUDIT V8');print('='*90)
 for k,v in c.items():print(f'{k}: {v}')
 print('OUT:',OUT);print('SUMMARY:',SUM)
if __name__=='__main__':main()
