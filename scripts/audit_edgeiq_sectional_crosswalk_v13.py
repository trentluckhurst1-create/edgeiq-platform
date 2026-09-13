from __future__ import annotations
import csv,re,hashlib
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
TARGETS=[DATA/'edgeiq_sectional_payload_reconstruction_v1.csv',DATA/'sectionals.csv']
OUT_SUMMARY=DATA/'edgeiq_sectional_crosswalk_v13_summary.csv'
OUT_REF=DATA/'edgeiq_sectional_crosswalk_v13_reference_source_quality.csv'
OUT_RACE=DATA/'edgeiq_sectional_crosswalk_v13_reference_race_encoding.csv'
OUT_TARGET=DATA/'edgeiq_sectional_crosswalk_v13_target_overlap.csv'
OUT_TRACK=DATA/'edgeiq_sectional_crosswalk_v13_unmatched_tracks.csv'
OUT_YEAR=DATA/'edgeiq_sectional_crosswalk_v13_unmatched_years.csv'

MISSING={'','-','nan','none','null','undefined','n/a'}
ALIASES={
 'date':('race_date','run_date','date','meeting_date'),
 'track':('track','venue','meeting','track_name'),
 'horse':('horse_name','horse','runner_name','runner','name'),
 'horse_id':('canonical_horse_id','horse_id','horse_key','runner_id','runner_key'),
 'race_no':('race_no','race_number','race'),
 'race_id':('canonical_race_id','race_id','racingcom_race_id','raceid'),
 'source':('source','source_file','source_lineage'),
}

def clean(v):
 s=str(v or '').strip(); return '' if s.lower() in MISSING else s
def nk(s):return re.sub(r'[^a-z0-9]+','',clean(s).lower())
def nt(s):return ' '.join(clean(s).upper().replace('_',' ').split())
def nh(s):return re.sub(r'[^A-Z0-9]','',clean(s).upper())
def nr(s):
 x=re.sub(r'[^0-9]','',clean(s)); return str(int(x)) if x else ''
def ridnorm(s):
 s=clean(s); return s[:-2] if re.fullmatch(r'\d+\.0',s) else s
def dn(s):
 s=clean(s)[:10]
 for f in ('%Y-%m-%d','%d/%m/%Y','%Y/%m/%d','%d-%m-%Y'):
  try:return datetime.strptime(s,f).strftime('%Y-%m-%d')
  except:pass
 return s
def find_all(fields,aliases):
 d={nk(x):x for x in fields}; return [d[nk(a)] for a in aliases if nk(a) in d]
def cmap(fields):return {k:find_all(fields,v) for k,v in ALIASES.items()}
def first(r,c,k):
 for col in c.get(k,[]):
  v=clean(r.get(col,''))
  if v:return v
 return ''
def refs():
 z=[]
 for p in DATA.glob('*.csv'):
  n=p.name.lower()
  if 'checkpoint' in n:continue
  if n.startswith('edgeiq_graphql_') and ('result' in n or 'master' in n):z.append(p)
  elif n in {'edgeiq_historical_results_warehouse_v2_graphql.csv','edgeiq_graphql_master_v2.csv'}:z.append(p)
 return sorted(set(z),key=lambda p:p.name.lower())

def main():
 total=Counter(); source_stats=defaultdict(Counter); race_ctx=defaultdict(set); horse_index=defaultdict(set); source_rowkeys=defaultdict(set)
 # Pass 1: reference estate. Race-number encoding is assessed at race context, NOT horse-row level.
 for p in refs():
  rel=str(p.relative_to(ROOT)); rows=valid=0
  try:
   with p.open('r',newline='',encoding='utf-8-sig') as h:
    rd=csv.DictReader(h);c=cmap(rd.fieldnames or [])
    if not(c['date'] and c['track'] and c['race_no'] and (c['horse'] or c['horse_id'])):
     source_stats[rel]['skip_schema']=1;continue
    for r in rd:
     rows+=1;d=dn(first(r,c,'date'));t=nt(first(r,c,'track'));ho=nh(first(r,c,'horse') or first(r,c,'horse_id'));rn=nr(first(r,c,'race_no'));rid=ridnorm(first(r,c,'race_id'))
     if not(d and t and ho and rn):continue
     valid+=1;source_stats[rel]['valid_rows']+=1
     n=int(rn)
     if 1<=n<=20:source_stats[rel]['race_no_1_20_rows']+=1
     if n in {10,20,30,40,50,60,70,80,90}:source_stats[rel]['multiple_10_rows']+=1
     ctx=(d,t,rid) if rid else (d,t,'NOID:'+rn)
     race_ctx[ctx].add(rn)
     source_rowkeys[rel].add((d,t,ho,rn,rid))
     horse_index[(d,t,ho)].add((rn,rid,rel))
   total['reference_files_used']+=1;total['reference_valid_rows']+=valid
  except Exception as e:source_stats[rel]['error']=1

 # Classify unique race contexts and source exposure to paired x10 defects.
 race_rows=[]; paired_contexts=set(); conflict_contexts=set()
 for ctx,rns in race_ctx.items():
  ints=sorted({int(x) for x in rns if x.isdigit()}); pairs=[]
  for n in range(1,10):
   if n in ints and n*10 in ints:pairs.append((n,n*10))
  if pairs: paired_contexts.add(ctx)
  canon_candidates=set(ints)
  for a,b in pairs: canon_candidates.discard(b)
  if len(canon_candidates)>1: conflict_contexts.add(ctx)
  race_rows.append({'race_date':ctx[0],'track':ctx[1],'race_id':ctx[2],'raw_race_nos':'|'.join(map(str,ints)),'x10_pairs':'|'.join(f'{a}:{b}' for a,b in pairs),'post_pair_collapse_race_nos':'|'.join(map(str,sorted(canon_candidates))),'classification':'PAIRED_X10_ONLY' if pairs and len(canon_candidates)==1 else ('MULTI_RACE_NO_CONFLICT' if len(canon_candidates)>1 else 'SINGLE_RACE_NO')})
 total['reference_unique_race_contexts']=len(race_ctx);total['reference_paired_x10_race_contexts']=len(paired_contexts);total['reference_postcollapse_conflict_contexts']=len(conflict_contexts)

 # second source pass cheaply classifies each unique rowkey by whether its race context is paired x10
 ref_out=[]
 for src,st in source_stats.items():
  keys=source_rowkeys.get(src,set()); paired=0; unique_races=set(); paired_races=set()
  for d,t,h,rn,rid in keys:
   ctx=(d,t,rid) if rid else (d,t,'NOID:'+rn);unique_races.add(ctx)
   if ctx in paired_contexts:paired+=1;paired_races.add(ctx)
  ref_out.append({'source_file':src,'valid_rows':st['valid_rows'],'unique_row_keys':len(keys),'unique_race_contexts':len(unique_races),'rows_in_paired_x10_contexts':paired,'paired_x10_race_contexts':len(paired_races),'multiple_10_rows':st['multiple_10_rows'],'race_no_1_20_rows':st['race_no_1_20_rows'],'paired_context_row_pct':round(100*paired/len(keys),4) if keys else 0,'status':'SKIP_SCHEMA' if st['skip_schema'] else ('ERROR' if st['error'] else 'USED')})

 # Build canonical reference overlap index only for measuring presence; no promotion.
 idx=defaultdict(set)
 for (d,t,h),vals in horse_index.items():
  for rn,rid,src in vals:
   n=int(rn);ctx=(d,t,rid) if rid else (d,t,'NOID:'+rn);canon=n
   rns={int(x) for x in race_ctx.get(ctx,set()) if x.isdigit()}
   if n%10==0 and 1<=n//10<=9 and n//10 in rns:canon=n//10
   idx[(d,t,h)].add(str(canon))

 target_out=[];track_counts=Counter();year_counts=Counter()
 for p in TARGETS:
  if not p.exists():continue
  rel=str(p.relative_to(ROOT));stats=Counter();srcval=Counter()
  with p.open('r',newline='',encoding='utf-8-sig') as h:
   rd=csv.DictReader(h);c=cmap(rd.fieldnames or [])
   for r in rd:
    stats['rows']+=1
    if nr(first(r,c,'race_no')):stats['already_has_race_no']+=1;continue
    stats['missing_race_no']+=1;d=dn(first(r,c,'date'));t=nt(first(r,c,'track'));ho=nh(first(r,c,'horse') or first(r,c,'horse_id'));sv=clean(first(r,c,'source')) or '<MISSING>'
    if not d:stats['missing_date']+=1
    if not t:stats['missing_track']+=1
    if not ho:stats['missing_horse']+=1
    vals=idx.get((d,t,ho),set()) if d and t and ho else set()
    if len(vals)==1:stats['unique_overlap']+=1
    elif len(vals)>1:stats['ambiguous_overlap']+=1
    else:
     stats['unmatched']+=1;track_counts[(rel,t or '<MISSING>')]+=1;year_counts[(rel,d[:4] if len(d)>=4 else '<MISSING>')]+=1
    srcval[sv]+=1
  target_out.append({'source_file':rel,**stats,'top_source_values':'|'.join(f'{k}:{v}' for k,v in srcval.most_common(10))})

 with OUT_SUMMARY.open('w',newline='',encoding='utf-8') as h:
  w=csv.writer(h);w.writerow(['metric','value']);[w.writerow([k,v]) for k,v in total.items()]
 with OUT_REF.open('w',newline='',encoding='utf-8') as h:
  f=['source_file','status','valid_rows','unique_row_keys','unique_race_contexts','rows_in_paired_x10_contexts','paired_x10_race_contexts','multiple_10_rows','race_no_1_20_rows','paired_context_row_pct'];w=csv.DictWriter(h,fieldnames=f);w.writeheader();w.writerows(sorted(ref_out,key=lambda x:(-x['paired_context_row_pct'],-x['valid_rows'],x['source_file'])))
 with OUT_RACE.open('w',newline='',encoding='utf-8') as h:
  f=['race_date','track','race_id','raw_race_nos','x10_pairs','post_pair_collapse_race_nos','classification'];w=csv.DictWriter(h,fieldnames=f);w.writeheader();w.writerows(race_rows)
 with OUT_TARGET.open('w',newline='',encoding='utf-8') as h:
  fields=sorted(set().union(*(x.keys() for x in target_out)));w=csv.DictWriter(h,fieldnames=fields);w.writeheader();w.writerows(target_out)
 with OUT_TRACK.open('w',newline='',encoding='utf-8') as h:
  w=csv.writer(h);w.writerow(['source_file','track','unmatched_rows']);[w.writerow([a,b,v]) for (a,b),v in track_counts.most_common()]
 with OUT_YEAR.open('w',newline='',encoding='utf-8') as h:
  w=csv.writer(h);w.writerow(['source_file','year','unmatched_rows']);[w.writerow([a,b,v]) for (a,b),v in year_counts.most_common()]
 print('='*100);print('EDGEIQ SECTIONAL CROSSWALK V13 — REFERENCE ENCODING + TARGET OVERLAP FORENSIC');print('='*100)
 for k,v in total.items():print(f'{k}: {v}')
 print('\nTARGET OVERLAP');
 for x in target_out:print(x)
 print('\nTOP REFERENCE SOURCES BY PAIRED-X10 EXPOSURE')
 for x in sorted(ref_out,key=lambda x:(-x['paired_context_row_pct'],-x['valid_rows']))[:25]:print(x)
 print('\nOUTPUTS:',OUT_SUMMARY,OUT_REF,OUT_RACE,OUT_TARGET,OUT_TRACK,OUT_YEAR,sep='\n')
if __name__=='__main__':main()
