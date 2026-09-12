from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
TARGETS=[DATA/'edgeiq_sectional_payload_reconstruction_v1.csv',DATA/'sectionals.csv']
OUT_SUMMARY=DATA/'edgeiq_sectional_crosswalk_match_v7_summary.csv'
OUT_SOURCES=DATA/'edgeiq_sectional_crosswalk_match_v7_sources.csv'
OUT_MATCHES=DATA/'edgeiq_sectional_crosswalk_match_v7_matches.csv'
OUT_AMBIG=DATA/'edgeiq_sectional_crosswalk_match_v7_ambiguous.csv'

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
def cmap(fields): return {k:find(fields,v) for k,v in ALIASES.items()}
def g(r,c,k): return clean(r.get(c.get(k,''))) if c.get(k) else ''

def candidate_reference_files():
 files=[]
 for p in DATA.glob('*.csv'):
  n=p.name.lower()
  if 'checkpoint' in n: continue
  if n.startswith('edgeiq_graphql_') and ('result' in n or 'master' in n): files.append(p)
  elif n in {'edgeiq_historical_results_warehouse_v2_graphql.csv','edgeiq_graphql_master_v2.csv'}: files.append(p)
 return sorted(set(files),key=lambda p:p.name.lower())

def main():
 refs=candidate_reference_files()
 if not refs: raise SystemExit('No historical GraphQL reference files found')
 indexes={'DTHD':defaultdict(set),'DTH':defaultdict(set),'DHD':defaultdict(set)}
 src_rows=[]; total=Counter(); canonical_races=set()
 for p in refs:
  rows=valid=0
  try:
   with p.open('r',newline='',encoding='utf-8-sig') as h:
    rd=csv.DictReader(h); c=cmap(list(rd.fieldnames or []))
    if not (c['date'] and c['track'] and c['race_no'] and (c['horse'] or c['horse_id'])):
     src_rows.append({'source_file':str(p.relative_to(ROOT)),'status':'SKIP_SCHEMA','rows':0,'valid_rows':0}); continue
    for r in rd:
     rows+=1
     d=date_norm(g(r,c,'date')); t=nt(g(r,c,'track')); horse=nh(g(r,c,'horse') or g(r,c,'horse_id')); dist=nd(g(r,c,'distance')); rn=nr(g(r,c,'race_no')); rid=g(r,c,'race_id')
     if not (d and t and horse and rn): continue
     valid+=1; val=(rn,rid); canonical_races.add((d,t,rn,rid))
     if dist:indexes['DTHD'][(d,t,horse,dist)].add(val)
     indexes['DTH'][(d,t,horse)].add(val)
     if dist:indexes['DHD'][(d,horse,dist)].add((t,rn,rid))
   src_rows.append({'source_file':str(p.relative_to(ROOT)),'status':'USED','rows':rows,'valid_rows':valid}); total['reference_rows']+=rows; total['reference_valid_rows']+=valid; total['reference_files_used']+=1
  except Exception as exc:
   src_rows.append({'source_file':str(p.relative_to(ROOT)),'status':f'ERROR:{type(exc).__name__}','rows':rows,'valid_rows':valid}); total['reference_files_error']+=1

 matches=[]; amb=[]
 for path in TARGETS:
  if not path.exists():continue
  with path.open('r',newline='',encoding='utf-8-sig') as h:
   rd=csv.DictReader(h); c=cmap(list(rd.fieldnames or []))
   for rowno,r in enumerate(rd,2):
    total['target_rows']+=1
    if nr(g(r,c,'race_no')):
     total['already_has_race_no']+=1; continue
    total['target_missing_race_no']+=1
    d=date_norm(g(r,c,'date')); t=nt(g(r,c,'track')); horse=nh(g(r,c,'horse') or g(r,c,'horse_id')); dist=nd(g(r,c,'distance'))
    vals=set(); method=''
    if d and t and horse and dist:
     vals=indexes['DTHD'].get((d,t,horse,dist),set()); method='EXACT_DATE_TRACK_HORSE_DISTANCE'
    if not vals and d and t and horse:
     vals=indexes['DTH'].get((d,t,horse),set()); method='EXACT_DATE_TRACK_HORSE'
    if not vals and d and horse and dist and not t:
     x=indexes['DHD'].get((d,horse,dist),set())
     if len(x)==1:
      tr,rn,rid=next(iter(x)); vals={(rn,rid)}; t=tr; method='EXACT_DATE_HORSE_DISTANCE_UNIQUE_TRACK'
     elif len(x)>1: total['ambiguous_unique_track']+=1
    if len(vals)==1:
     rn,rid=next(iter(vals)); total['exact_unique_matches']+=1; total[method]+=1
     if len(matches)<10000: matches.append({'source_file':str(path.relative_to(ROOT)),'row_no':rowno,'race_date':d,'track':t,'horse_key':horse,'distance':dist,'recovered_race_no':rn,'recovered_race_id':rid,'identity_method':method})
    elif len(vals)>1:
     total['ambiguous_matches']+=1
     if len(amb)<2000: amb.append({'source_file':str(path.relative_to(ROOT)),'row_no':rowno,'race_date':d,'track':t,'horse_key':horse,'distance':dist,'candidate_count':len(vals),'candidates':'|'.join(sorted(f'{a}:{b}' for a,b in vals))})
    else: total['unmatched']+=1

 total['reference_unique_canonical_races']=len(canonical_races)
 total['reference_index_dthd_keys']=len(indexes['DTHD']); total['reference_index_dth_keys']=len(indexes['DTH']); total['reference_index_dhd_keys']=len(indexes['DHD'])
 with OUT_SUMMARY.open('w',newline='',encoding='utf-8') as h:
  w=csv.writer(h); w.writerow(['metric','value']);
  for k,v in total.items():w.writerow([k,v])
 with OUT_SOURCES.open('w',newline='',encoding='utf-8') as h:
  w=csv.DictWriter(h,fieldnames=['source_file','status','rows','valid_rows']);w.writeheader();w.writerows(src_rows)
 with OUT_MATCHES.open('w',newline='',encoding='utf-8') as h:
  f=['source_file','row_no','race_date','track','horse_key','distance','recovered_race_no','recovered_race_id','identity_method'];w=csv.DictWriter(h,fieldnames=f);w.writeheader();w.writerows(matches)
 with OUT_AMBIG.open('w',newline='',encoding='utf-8') as h:
  f=['source_file','row_no','race_date','track','horse_key','distance','candidate_count','candidates'];w=csv.DictWriter(h,fieldnames=f);w.writeheader();w.writerows(amb)
 print('='*90);print('EDGEIQ SECTIONAL MULTI-SOURCE HISTORICAL CROSSWALK AUDIT V7');print('='*90)
 for k,v in total.items():print(f'{k}: {v}')
 print('SOURCES:',OUT_SOURCES);print('SUMMARY:',OUT_SUMMARY);print('MATCHES:',OUT_MATCHES);print('AMBIGUOUS:',OUT_AMBIG)

if __name__=='__main__':main()
