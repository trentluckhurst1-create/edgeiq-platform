from __future__ import annotations
import csv,re
from collections import Counter,defaultdict
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'public'/'data'
P=D/'edgeiq_sectional_payload_reconstruction_v1.csv';C=D/'edgeiq_sectional_lineage_v22_residual_classification.csv'
OUT=D/'edgeiq_sectional_track_alias_v24_summary.csv';MAP=D/'edgeiq_sectional_track_alias_v24_candidates.csv';UN=D/'edgeiq_sectional_track_alias_v24_unresolved_tracks.csv'
MISS={'','-','nan','none','null','undefined','n/a'}
def cl(v):
 s=str(v or '').strip();return '' if s.lower() in MISS else s
def first(r,cs):
 for c in cs:
  v=cl(r.get(c,''))
  if v:return v
 return ''
def nd(v):
 s=cl(v)[:10]
 for f in ('%Y-%m-%d','%d/%m/%Y','%Y/%m/%d','%d-%m-%Y'):
  try:return datetime.strptime(s,f).strftime('%Y-%m-%d')
  except:pass
 return s
def nt(v):return ' '.join(cl(v).upper().replace('_',' ').split())
def nh(v):return re.sub('[^A-Z0-9]','',cl(v).upper())
def dth(r):return nd(first(r,['race_date','run_date','date','meeting_date'])),nt(first(r,['track','venue','meeting','track_name'])),nh(first(r,['horse','horse_name','runner','runner_name','horse_key']))
def main():
 with P.open(newline='',encoding='utf-8-sig') as h:pr=list(csv.DictReader(h))
 with C.open(newline='',encoding='utf-8-sig') as h:cr=list(csv.DictReader(h))
 targets=[]
 for i,r in enumerate(pr,1):
  if not cl(first(r,['race_no','race_number','race'])):
   d,t,h=dth(r)
   if d and t and h:targets.append(('payload',i,d,t,h))
 # retained sectionals residuals only
 sfile=D/'sectionals.csv'
 with sfile.open(newline='',encoding='utf-8-sig') as h:sr=list(csv.DictReader(h))
 keep={int(x['sectionals_row']) for x in cr if x['classification'] in ('UNREPRESENTED_PARENT_SOURCE_ROW','UNRESOLVED_PARENT_IDENTITY')}
 for i in keep:
  r=sr[i-1]
  if not cl(first(r,['race_no','race_number','race'])):
   d,t,h=dth(r)
   if d and t and h:targets.append(('sectionals_residual',i,d,t,h))
 # Build reference observations: date+horse -> track + race no from result-like csvs. Exclude checkpoints and sectional derived estate.
 by_dh=defaultdict(list);files=0;rows=0
 for f in D.rglob('*.csv'):
  rel=str(f.relative_to(ROOT)).replace('\\','/').lower()
  if 'checkpoint' in rel or 'sectional' in rel:continue
  try:
   with f.open(newline='',encoding='utf-8-sig',errors='replace') as z:
    rd=csv.DictReader(z);fields=set(rd.fieldnames or [])
    if not fields.intersection({'race_no','race_number','race'}):continue
    if not fields.intersection({'horse','horse_name','runner','runner_name','horse_key'}):continue
    if not fields.intersection({'track','venue','meeting','track_name'}):continue
    if not fields.intersection({'race_date','run_date','date','meeting_date'}):continue
    used=False
    for r in rd:
     d,t,h=dth(r);rn=first(r,['race_no','race_number','race'])
     if d and t and h and rn:
      by_dh[(d,h)].append((t,rn,rel));rows+=1;used=True
    if used:files+=1
  except:pass
 # For each raw target track, infer only when every exact date+horse reference observation points to one normalized reference track.
 obs=defaultdict(Counter);support=Counter();unmatched=Counter()
 for src,i,d,t,h in targets:
  refs=by_dh.get((d,h),[])
  tracks={x[0] for x in refs if x[0]}
  if len(tracks)==1:
   rt=next(iter(tracks));obs[t][rt]+=1;support[t]+=1
  elif not refs:unmatched[t]+=1
 rowsout=[];accepted={}
 for raw,c in sorted(obs.items(),key=lambda x:(-sum(x[1].values()),x[0])):
  total=sum(c.values());best,n=c.most_common(1)[0];conf=n/total if total else 0
  # deterministic candidate requires >=3 exact DH observations and 100% agreement; same-name mappings retained as control.
  status='DETERMINISTIC_CANDIDATE' if n>=3 and n==total else 'AMBIGUOUS'
  if status=='DETERMINISTIC_CANDIDATE':accepted[raw]=best
  rowsout.append({'target_track':raw,'reference_track_candidate':best,'support_rows':n,'all_exact_dh_observations':total,'confidence_pct':round(conf*100,6),'status':status,'other_candidates':'|'.join(f'{k}:{v}' for k,v in c.most_common()[1:])})
 with MAP.open('w',newline='',encoding='utf-8') as h:w=csv.DictWriter(h,fieldnames=rowsout[0].keys() if rowsout else ['target_track']);w.writeheader();w.writerows(rowsout)
 unresolved=[{'target_track':t,'target_rows_no_exact_dh_reference':n,'has_deterministic_candidate':'YES' if t in accepted else 'NO'} for t,n in unmatched.most_common()]
 with UN.open('w',newline='',encoding='utf-8') as h:w=csv.DictWriter(h,fieldnames=['target_track','target_rows_no_exact_dh_reference','has_deterministic_candidate']);w.writeheader();w.writerows(unresolved)
 metrics={'target_rows_complete_dth_missing_race_no':len(targets),'reference_files_used':files,'reference_rows_used':rows,'target_track_vocab':len(set(x[3] for x in targets)),'tracks_with_exact_date_horse_reference':len(obs),'deterministic_track_candidates':len(accepted),'non_identity_alias_candidates':sum(1 for a,b in accepted.items() if a!=b),'ambiguous_track_candidates':sum(1 for x in rowsout if x['status']=='AMBIGUOUS')}
 with OUT.open('w',newline='',encoding='utf-8') as h:w=csv.writer(h);w.writerow(['metric','value']);[w.writerow(x) for x in metrics.items()]
 print('='*100);print('EDGEIQ SECTIONAL TRACK ALIAS V24 — EVIDENCE-BACKED VOCABULARY CROSSWALK');print('='*100)
 for k,v in metrics.items():print(f'{k}: {v}')
 print('\nTOP NON-IDENTITY DETERMINISTIC CANDIDATES')
 for x in [r for r in rowsout if r['status']=='DETERMINISTIC_CANDIDATE' and r['target_track']!=r['reference_track_candidate']][:50]:print(x)
 print('SUMMARY:',OUT);print('CANDIDATES:',MAP);print('UNRESOLVED:',UN)
if __name__=='__main__':main()
