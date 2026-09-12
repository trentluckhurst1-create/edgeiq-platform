from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
TARGETS=[DATA/'edgeiq_sectional_payload_reconstruction_v1.csv',DATA/'sectionals.csv']
OUT_SUMMARY=DATA/'edgeiq_sectional_crosswalk_raceid_v9_summary.csv'
OUT_MATCHES=DATA/'edgeiq_sectional_crosswalk_raceid_v9_matches.csv'
OUT_CONFLICTS=DATA/'edgeiq_sectional_crosswalk_raceid_v9_conflicts.csv'

MISSING={'','-','nan','none','null','undefined','n/a'}
ALIASES={
 'date':('race_date','date','meeting_date','run_date'),
 'track':('track','venue','meeting','track_name'),
 'horse':('horse_name','horse','runner_name','runner','name'),
 'horse_id':('canonical_horse_id','horse_id','horse_key','runner_id','runner_key'),
 'distance':('distance','race_distance','dist','race_distance_metres'),
 'race_no':('race_no','race_number','race'),
 'race_id':('canonical_race_id','race_id','racingcom_race_id','raceid'),
}

def clean(v):
 s=str(v or '').strip(); return '' if s.lower() in MISSING else s

def nk(s): return re.sub(r'[^a-z0-9]+','',clean(s).lower())
def nt(s): return ' '.join(clean(s).upper().replace('_',' ').split())
def nh(s): return re.sub(r'[^A-Z0-9]','',clean(s).upper())
def nd(s):
 x=re.sub(r'[^0-9.]','',clean(s))
 if not x:return ''
 try:return str(int(round(float(x))))
 except:return ''
def nr(s):
 x=re.sub(r'[^0-9]','',clean(s)); return str(int(x)) if x else ''
def ridnorm(s):
 s=clean(s)
 if not s:return ''
 try:return str(int(float(s)))
 except:return s

def date_norm(s):
 s=clean(s)[:10]
 for f in ('%Y-%m-%d','%d/%m/%Y','%Y/%m/%d','%d-%m-%Y'):
  try:return datetime.strptime(s,f).strftime('%Y-%m-%d')
  except:pass
 return s

def find(fields,aliases):
 d={nk(x):x for x in fields}
 for a in aliases:
  if nk(a) in d:return d[nk(a)]
 return ''
def cmap(fields):return {k:find(fields,v) for k,v in ALIASES.items()}
def g(r,c,k):return clean(r.get(c.get(k,''))) if c.get(k) else ''

def reference_files():
 files=[]
 for p in DATA.glob('edgeiq_graphql*_results_v1.csv'):
  if 'checkpoint' not in p.name.lower(): files.append(p)
 for name in ('edgeiq_graphql_master_v2.csv','edgeiq_historical_results_warehouse_v2_graphql.csv'):
  p=DATA/name
  if p.exists():files.append(p)
 # deterministic unique list
 seen=set(); out=[]
 for p in sorted(files,key=lambda x:x.name.lower()):
  rp=str(p.resolve()).lower()
  if rp not in seen:seen.add(rp);out.append(p)
 return out

def main():
 refs=reference_files()
 idx_dthd=defaultdict(set); idx_dth=defaultdict(set)
 race_meta=defaultdict(lambda:{'race_nos':Counter(),'dates':Counter(),'tracks':Counter(),'distances':Counter(),'sources':Counter()})
 counts=Counter()
 for p in refs:
  try:
   with p.open('r',newline='',encoding='utf-8-sig') as h:
    rd=csv.DictReader(h); c=cmap(list(rd.fieldnames or []))
    if not (c['date'] and c['track'] and (c['horse'] or c['horse_id']) and c['race_id']):
     counts['reference_files_skipped_schema']+=1; continue
    counts['reference_files_used']+=1
    for r in rd:
     counts['reference_rows']+=1
     d=date_norm(g(r,c,'date')); t=nt(g(r,c,'track')); horse=nh(g(r,c,'horse') or g(r,c,'horse_id')); dist=nd(g(r,c,'distance')); rid=ridnorm(g(r,c,'race_id')); rn=nr(g(r,c,'race_no'))
     if not (d and t and horse and rid):continue
     counts['reference_valid_rows']+=1
     if dist: idx_dthd[(d,t,horse,dist)].add(rid)
     idx_dth[(d,t,horse)].add(rid)
     m=race_meta[rid]; m['dates'][d]+=1; m['tracks'][t]+=1; m['sources'][p.name]+=1
     if dist:m['distances'][dist]+=1
     if rn:m['race_nos'][rn]+=1
  except Exception:
   counts['reference_files_failed']+=1

 matches=[]; conflicts=[]
 for path in TARGETS:
  if not path.exists():continue
  with path.open('r',newline='',encoding='utf-8-sig') as h:
   rd=csv.DictReader(h); c=cmap(list(rd.fieldnames or []))
   for rowno,r in enumerate(rd,2):
    counts['target_rows']+=1
    if nr(g(r,c,'race_no')): counts['already_has_race_no']+=1; continue
    counts['target_missing_race_no']+=1
    d=date_norm(g(r,c,'date')); t=nt(g(r,c,'track')); horse=nh(g(r,c,'horse') or g(r,c,'horse_id')); dist=nd(g(r,c,'distance'))
    rids=set(); method=''
    if d and t and horse and dist:
     rids=idx_dthd.get((d,t,horse,dist),set()); method='EXACT_DATE_TRACK_HORSE_DISTANCE_TO_RACE_ID'
    if not rids and d and t and horse:
     rids=idx_dth.get((d,t,horse),set()); method='EXACT_DATE_TRACK_HORSE_TO_RACE_ID'
    if len(rids)==1:
     rid=next(iter(rids)); meta=race_meta[rid]; race_nos=meta['race_nos']
     if len(race_nos)==1:
      rn=next(iter(race_nos)); disposition='RACE_ID_UNIQUE_RACE_NO_UNIQUE'; counts['exact_unique_raceid_and_raceno']+=1
     elif len(race_nos)>1:
      rn=''; disposition='RACE_ID_UNIQUE_RACE_NO_CONFLICT'; counts['exact_unique_raceid_raceno_conflict']+=1
     else:
      rn=''; disposition='RACE_ID_UNIQUE_RACE_NO_MISSING'; counts['exact_unique_raceid_raceno_missing']+=1
     counts[method]+=1
     matches.append({'source_file':str(path.relative_to(ROOT)),'row_no':rowno,'race_date':d,'track':t,'horse_key':horse,'distance':dist,'recovered_race_id':rid,'recovered_race_no':rn,'identity_method':method,'race_no_disposition':disposition,'race_no_candidates':'|'.join(sorted(race_nos.keys()))})
    elif len(rids)>1:
     counts['ambiguous_race_ids']+=1
     if len(conflicts)<2000:conflicts.append({'source_file':str(path.relative_to(ROOT)),'row_no':rowno,'race_date':d,'track':t,'horse_key':horse,'distance':dist,'candidate_race_ids':'|'.join(sorted(rids)),'candidate_count':len(rids)})
    else:counts['unmatched']+=1

 with OUT_SUMMARY.open('w',newline='',encoding='utf-8') as h:
  w=csv.writer(h);w.writerow(['metric','value']);w.writerow(['reference_files_discovered',len(refs)])
  for k,v in counts.items():w.writerow([k,v])
 with OUT_MATCHES.open('w',newline='',encoding='utf-8') as h:
  f=['source_file','row_no','race_date','track','horse_key','distance','recovered_race_id','recovered_race_no','identity_method','race_no_disposition','race_no_candidates'];w=csv.DictWriter(h,fieldnames=f);w.writeheader();w.writerows(matches)
 with OUT_CONFLICTS.open('w',newline='',encoding='utf-8') as h:
  f=['source_file','row_no','race_date','track','horse_key','distance','candidate_race_ids','candidate_count'];w=csv.DictWriter(h,fieldnames=f);w.writeheader();w.writerows(conflicts)
 print('='*90);print('EDGEIQ SECTIONAL RACE-ID FIRST CROSSWALK AUDIT V9');print('='*90)
 print('reference_files_discovered:',len(refs))
 for k,v in counts.items():print(f'{k}: {v}')
 print('SUMMARY:',OUT_SUMMARY);print('MATCHES:',OUT_MATCHES);print('CONFLICTS:',OUT_CONFLICTS)

if __name__=='__main__':main()
