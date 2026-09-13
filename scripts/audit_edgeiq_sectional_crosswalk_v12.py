from __future__ import annotations
import csv,re
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
TARGETS=[DATA/'edgeiq_sectional_payload_reconstruction_v1.csv',DATA/'sectionals.csv']
OUT_SUMMARY=DATA/'edgeiq_sectional_crosswalk_v12_summary.csv'
OUT_MATCHES=DATA/'edgeiq_sectional_crosswalk_v12_matches.csv'
OUT_AMBIG=DATA/'edgeiq_sectional_crosswalk_v12_ambiguous.csv'
OUT_SOURCES=DATA/'edgeiq_sectional_crosswalk_v12_sources.csv'
OUT_NORMALIZATION=DATA/'edgeiq_sectional_crosswalk_v12_race_no_normalization_audit.csv'

MISSING={'','-','nan','none','null','undefined','n/a'}
ALIASES={
 'date':('race_date','run_date','date','meeting_date'),
 'track':('track','venue','meeting','track_name'),
 'horse':('horse_name','horse','runner_name','runner','name'),
 'horse_id':('canonical_horse_id','horse_id','horse_key','runner_id','runner_key'),
 'race_no':('race_no','race_number','race'),
 'race_id':('canonical_race_id','race_id','racingcom_race_id','raceid'),
}

def clean(v):
 s=str(v or '').strip(); return '' if s.lower() in MISSING else s

def nk(s): return re.sub(r'[^a-z0-9]+','',clean(s).lower())
def nt(s): return ' '.join(clean(s).upper().replace('_',' ').split())
def nh(s): return re.sub(r'[^A-Z0-9]','',clean(s).upper())
def nr_raw(s):
 x=re.sub(r'[^0-9]','',clean(s)); return str(int(x)) if x else ''
def ridnorm(s):
 s=clean(s)
 return s[:-2] if re.fullmatch(r'\d+\.0',s) else s

def date_norm(s):
 s=clean(s)[:10]
 for f in ('%Y-%m-%d','%d/%m/%Y','%Y/%m/%d','%d-%m-%Y'):
  try:return datetime.strptime(s,f).strftime('%Y-%m-%d')
  except:pass
 return s

def find_all(fields,aliases):
 d={nk(x):x for x in fields}; out=[]
 for a in aliases:
  if nk(a) in d: out.append(d[nk(a)])
 return out

def cmap(fields): return {k:find_all(fields,v) for k,v in ALIASES.items()}

def g_first_nonmissing(r,c,k):
 for col in c.get(k,[]):
  v=clean(r.get(col,''))
  if v:return v
 return ''

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

 # Build raw reference candidates first. We do NOT blindly divide every 10/20/etc by 10.
 # A x10 encoding is only collapsed when the same date+track+horse+race_id is also seen with the base 1..9 race number.
 raw_records=[]; src_rows=[]; total=Counter()
 for p in refs:
  rows=valid=0
  try:
   with p.open('r',newline='',encoding='utf-8-sig') as h:
    rd=csv.DictReader(h); c=cmap(list(rd.fieldnames or []))
    if not (c['date'] and c['track'] and c['race_no'] and (c['horse'] or c['horse_id'])):
     src_rows.append({'source_file':str(p.relative_to(ROOT)),'status':'SKIP_SCHEMA','rows':0,'valid_rows':0}); continue
    for r in rd:
     rows+=1
     d=date_norm(g_first_nonmissing(r,c,'date')); t=nt(g_first_nonmissing(r,c,'track')); horse=nh(g_first_nonmissing(r,c,'horse') or g_first_nonmissing(r,c,'horse_id')); rn=nr_raw(g_first_nonmissing(r,c,'race_no')); rid=ridnorm(g_first_nonmissing(r,c,'race_id'))
     if not(d and t and horse and rn):continue
     valid+=1; raw_records.append((d,t,horse,rn,rid,str(p.relative_to(ROOT))))
   src_rows.append({'source_file':str(p.relative_to(ROOT)),'status':'USED','rows':rows,'valid_rows':valid}); total['reference_files_used']+=1; total['reference_valid_rows']+=valid
  except Exception as exc:
   src_rows.append({'source_file':str(p.relative_to(ROOT)),'status':f'ERROR:{type(exc).__name__}','rows':rows,'valid_rows':valid}); total['reference_files_error']+=1

 # Evidence-driven normalization map scoped to exact date+track+horse+race_id.
 seen=defaultdict(set)
 for d,t,h,rn,rid,src in raw_records:
  if rid: seen[(d,t,h,rid)].add(rn)
 norm_audit=[]; norm_map={}
 for key,rns in seen.items():
  ints={int(x) for x in rns if x.isdigit()}
  for n in sorted(ints):
   if 1<=n<=9 and n*10 in ints:
    norm_map[(key,n*10)]=n
    norm_audit.append({'race_date':key[0],'track':key[1],'horse_key':key[2],'race_id':key[3],'raw_race_no':n*10,'canonical_race_no':n,'evidence':f'paired_with_{n}_same_exact_context'})
 total['reference_x10_normalizations']=len(norm_audit)

 idx=defaultdict(lambda:defaultdict(set))
 for d,t,h,rn,rid,src in raw_records:
  n=int(rn)
  canon=str(norm_map.get(((d,t,h,rid),n),n)) if rid else rn
  idx[(d,t,h)][canon].add(rid)

 matches=[]; amb=[]
 for path in TARGETS:
  if not path.exists():continue
  with path.open('r',newline='',encoding='utf-8-sig') as h:
   rd=csv.DictReader(h); c=cmap(list(rd.fieldnames or []))
   for rowno,r in enumerate(rd,2):
    total['target_rows']+=1
    if nr_raw(g_first_nonmissing(r,c,'race_no')):
     total['already_has_race_no']+=1; continue
    total['target_missing_race_no']+=1
    d=date_norm(g_first_nonmissing(r,c,'date')); t=nt(g_first_nonmissing(r,c,'track')); horse=nh(g_first_nonmissing(r,c,'horse') or g_first_nonmissing(r,c,'horse_id'))
    if not d: total['missing_date_after_fallback']+=1
    if not t: total['missing_track']+=1
    if not horse: total['missing_horse']+=1
    vals=idx.get((d,t,horse),{}) if d and t and horse else {}
    if len(vals)==1:
     rn=next(iter(vals)); ids=sorted(x for x in vals[rn] if x)
     total['exact_unique_matches']+=1
     if len(ids)>1: total['unique_race_no_multiple_reference_ids']+=1
     matches.append({'source_file':str(path.relative_to(ROOT)),'row_no':rowno,'race_date':d,'track':t,'horse_key':horse,'recovered_race_no':rn,'recovered_race_id':ids[0] if len(ids)==1 else '','reference_race_ids':'|'.join(ids),'identity_method':'EXACT_DATE_TRACK_HORSE_UNIQUE_CANONICAL_RACE_NO'})
    elif len(vals)>1:
     total['ambiguous_multiple_race_numbers']+=1
     if len(amb)<5000: amb.append({'source_file':str(path.relative_to(ROOT)),'row_no':rowno,'race_date':d,'track':t,'horse_key':horse,'race_nos':'|'.join(sorted(vals,key=lambda x:int(x)))})
    else:
     total['unmatched']+=1

 with OUT_SUMMARY.open('w',newline='',encoding='utf-8') as h:
  w=csv.writer(h); w.writerow(['metric','value']); [w.writerow([k,v]) for k,v in total.items()]
 with OUT_MATCHES.open('w',newline='',encoding='utf-8') as h:
  f=['source_file','row_no','race_date','track','horse_key','recovered_race_no','recovered_race_id','reference_race_ids','identity_method']; w=csv.DictWriter(h,fieldnames=f); w.writeheader(); w.writerows(matches)
 with OUT_AMBIG.open('w',newline='',encoding='utf-8') as h:
  f=['source_file','row_no','race_date','track','horse_key','race_nos']; w=csv.DictWriter(h,fieldnames=f); w.writeheader(); w.writerows(amb)
 with OUT_SOURCES.open('w',newline='',encoding='utf-8') as h:
  f=['source_file','status','rows','valid_rows']; w=csv.DictWriter(h,fieldnames=f); w.writeheader(); w.writerows(src_rows)
 with OUT_NORMALIZATION.open('w',newline='',encoding='utf-8') as h:
  f=['race_date','track','horse_key','race_id','raw_race_no','canonical_race_no','evidence']; w=csv.DictWriter(h,fieldnames=f); w.writeheader(); w.writerows(norm_audit)

 print('='*96); print('EDGEIQ SECTIONAL CROSSWALK V12 — TRUE DATE FALLBACK + EVIDENCE-BASED X10 NORMALIZATION'); print('='*96)
 for k,v in total.items(): print(f'{k}: {v}')
 print('SUMMARY:',OUT_SUMMARY); print('MATCHES:',OUT_MATCHES); print('AMBIGUOUS:',OUT_AMBIG); print('NORMALIZATION:',OUT_NORMALIZATION)

if __name__=='__main__': main()
