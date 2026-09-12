from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
CERT=DATA/'edgeiq_sectional_raceid_to_raceno_v13.csv'
FILES=[
 DATA/'edgeiq_sectional_payload_reconstruction_v1.csv',
 DATA/'edgeiq_sectional_physics_validation_v1.csv',
 DATA/'sectionals.csv',
]
OUT_SUM=DATA/'edgeiq_sectional_certified_lineage_v15_summary.csv'
OUT_ROWS=DATA/'edgeiq_sectional_certified_lineage_v15_rows.csv'
OUT_FIELDS=DATA/'edgeiq_sectional_certified_lineage_v15_fields.csv'
MISSING={'','-','nan','none','null','undefined','n/a'}

def clean(v):
 s=str(v or '').strip(); return '' if s.lower() in MISSING else s

def nk(s):return re.sub(r'[^a-z0-9]+','',clean(s).lower())
def nh(s):return re.sub(r'[^A-Z0-9]','',clean(s).upper())
def norm_track(s):return ' '.join(clean(s).upper().replace('_',' ').split())
def norm_date(s):
 s=clean(s)[:10]
 if re.match(r'^\d{4}-\d{2}-\d{2}$',s):return s
 m=re.match(r'^(\d{2})/(\d{2})/(\d{4})$',s)
 return f'{m.group(3)}-{m.group(2)}-{m.group(1)}' if m else s

def find(fields,*aliases):
 d={nk(f):f for f in fields}
 for a in aliases:
  if nk(a) in d:return d[nk(a)]
 return ''
def get(r,c):return clean(r.get(c)) if c else ''

def splitish_fields(fields):
 out=[]
 for f in fields:
  n=nk(f)
  if any(x in n for x in ('split','section','segment','last200','last400','last600','l200','l400','l600','time','metres','meter','distancefromfinish')):
   out.append(f)
 return out

def main():
 if not CERT.exists():raise SystemExit(f'Missing {CERT}')
 cert=[]
 with CERT.open('r',newline='',encoding='utf-8-sig') as h:
  rd=csv.DictReader(h)
  for r in rd:
   if clean(r.get('status'))!='CERTIFIED_RACE_ID_TO_RACE_NO':continue
   cert.append({
    'source_file':clean(r.get('source_file')),
    'row_no':clean(r.get('row_no')),
    'race_date':norm_date(r.get('race_date')),
    'track':norm_track(r.get('track')),
    'horse_key':nh(r.get('horse_key')),
    'resolved_race_no':clean(r.get('resolved_race_no')),
    'race_id':clean(r.get('recovered_race_id')),
   })
 targets={(x['source_file'],x['row_no']):x for x in cert}
 key_targets=defaultdict(list)
 for x in cert:
  if x['race_date'] and x['track'] and x['horse_key']:
   key_targets[(x['race_date'],x['track'],x['horse_key'])].append(x)
 counts=Counter(); out_rows=[]; field_rows=[]
 for path in FILES:
  if not path.exists():
   counts['files_missing']+=1;continue
  rel=str(path.relative_to(ROOT))
  with path.open('r',newline='',encoding='utf-8-sig') as h:
   rd=csv.DictReader(h); fields=list(rd.fieldnames or [])
   c_date=find(fields,'race_date','date','meeting_date','run_date')
   c_track=find(fields,'track','venue','meeting','track_name')
   c_horse=find(fields,'horse','horse_name','runner_name','runner','name')
   c_horseid=find(fields,'horse_key','horse_id','runner_id','runner_key','canonical_horse_id')
   c_race=find(fields,'race_no','race_number','race')
   sf=splitish_fields(fields)
   field_rows.append({'source_file':rel,'rows':'','date_col':c_date,'track_col':c_track,'horse_col':c_horse,'horse_id_col':c_horseid,'race_no_col':c_race,'splitish_field_count':len(sf),'splitish_fields':'|'.join(sf[:100]),'all_fields':'|'.join(fields[:200])})
   file_count=0
   for rowno,r in enumerate(rd,2):
    file_count+=1; counts['rows_scanned']+=1
    exact=targets.get((rel,str(rowno)))
    d=norm_date(get(r,c_date)); t=norm_track(get(r,c_track)); horse=nh(get(r,c_horse) or get(r,c_horseid))
    candidates=[]
    method=''
    if exact:
     candidates=[exact];method='EXACT_SOURCE_ROW'
    elif d and t and horse:
     candidates=key_targets.get((d,t,horse),[])
     if len(candidates)==1:method='EXACT_DATE_TRACK_HORSE'
    if len(candidates)!=1:continue
    certrow=candidates[0]
    nonblank=[]
    for f in sf:
     v=clean(r.get(f))
     if v:nonblank.append((f,v))
    counts['certified_lineage_hits']+=1
    if nonblank: counts['hits_with_splitish_values']+=1
    else: counts['hits_without_splitish_values']+=1
    out_rows.append({
     'source_file':rel,'row_no':rowno,'lineage_method':method,'race_date':d or certrow['race_date'],'track':t or certrow['track'],'horse_key':horse or certrow['horse_key'],
     'resolved_race_no':certrow['resolved_race_no'],'race_id':certrow['race_id'],'existing_race_no':get(r,c_race),
     'splitish_nonblank_count':len(nonblank),'splitish_values':json.dumps(dict(nonblank[:50]),ensure_ascii=False),
    })
   field_rows[-1]['rows']=file_count
   counts[f'rows_{path.name}']=file_count

 with OUT_SUM.open('w',newline='',encoding='utf-8') as h:
  w=csv.writer(h);w.writerow(['metric','value']);w.writerow(['certified_rows',len(cert)]);[w.writerow([k,v]) for k,v in counts.items()]
 with OUT_ROWS.open('w',newline='',encoding='utf-8') as h:
  fs=['source_file','row_no','lineage_method','race_date','track','horse_key','resolved_race_no','race_id','existing_race_no','splitish_nonblank_count','splitish_values']
  w=csv.DictWriter(h,fieldnames=fs);w.writeheader();w.writerows(out_rows)
 with OUT_FIELDS.open('w',newline='',encoding='utf-8') as h:
  fs=['source_file','rows','date_col','track_col','horse_col','horse_id_col','race_no_col','splitish_field_count','splitish_fields','all_fields']
  w=csv.DictWriter(h,fieldnames=fs);w.writeheader();w.writerows(field_rows)
 print('='*90);print('EDGEIQ SECTIONAL CERTIFIED LINEAGE AUDIT V15');print('='*90)
 print('certified_rows:',len(cert))
 for k,v in counts.items():print(f'{k}: {v}')
 print('SUMMARY:',OUT_SUM);print('ROWS:',OUT_ROWS);print('FIELDS:',OUT_FIELDS)

if __name__=='__main__':main()
