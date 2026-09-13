from __future__ import annotations
import csv,re
from collections import defaultdict,Counter
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'public'/'data'
P=D/'edgeiq_sectional_payload_reconstruction_v1.csv'
S=D/'sectionals.csv'
C22=D/'edgeiq_sectional_lineage_v22_residual_classification.csv'
A24=D/'edgeiq_sectional_track_alias_v24_candidates.csv'
OUT_SUM=D/'edgeiq_sectional_race_identity_v25_summary.csv'
OUT_MATCH=D/'edgeiq_sectional_race_identity_v25_matches.csv'
OUT_UN=D/'edgeiq_sectional_race_identity_v25_unmatched.csv'
OUT_ALIAS=D/'edgeiq_sectional_race_identity_v25_alias_usage.csv'
MISS={'','-','nan','none','null','undefined','n/a'}
def cl(v):
 s=str(v or '').strip(); return '' if s.lower() in MISS else s
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
def nr(v):
 s=cl(v)
 if not s:return ''
 try:
  f=float(s)
  if f.is_integer():return str(int(f))
 except:pass
 m=re.fullmatch(r'\s*(\d+)\s*',s)
 return m.group(1) if m else s.upper()
def dth(r):return nd(first(r,['race_date','run_date','date','meeting_date'])),nt(first(r,['track','venue','meeting','track_name'])),nh(first(r,['horse','horse_name','runner','runner_name','horse_key']))
def main():
 with A24.open(newline='',encoding='utf-8-sig') as h:
  aliases={r['target_track']:r['reference_track_candidate'] for r in csv.DictReader(h) if r['status']=='DETERMINISTIC_CANDIDATE'}
 with P.open(newline='',encoding='utf-8-sig') as h:pr=list(csv.DictReader(h))
 with S.open(newline='',encoding='utf-8-sig') as h:sr=list(csv.DictReader(h))
 with C22.open(newline='',encoding='utf-8-sig') as h:cr=list(csv.DictReader(h))
 keep={int(r['sectionals_row']) for r in cr if r['classification'] in ('UNREPRESENTED_PARENT_SOURCE_ROW','UNRESOLVED_PARENT_IDENTITY')}
 targets=[]
 for i,r in enumerate(pr,1):targets.append(('payload',i,r))
 for i in sorted(keep):targets.append(('sectionals_residual',i,sr[i-1]))
 # reference index, excluding checkpoints + sectional estate
 idx=defaultdict(set);ref_files=0;ref_rows=0
 for f in D.rglob('*.csv'):
  rel=str(f.relative_to(ROOT)).replace('\\','/').lower()
  if 'checkpoint' in rel or 'sectional' in rel:continue
  try:
   with f.open(newline='',encoding='utf-8-sig',errors='replace') as z:
    rd=csv.DictReader(z);fs=set(rd.fieldnames or [])
    if not fs.intersection({'race_no','race_number','race'}):continue
    if not fs.intersection({'horse','horse_name','runner','runner_name','horse_key'}):continue
    if not fs.intersection({'track','venue','meeting','track_name'}):continue
    if not fs.intersection({'race_date','run_date','date','meeting_date'}):continue
    used=False
    for r in rd:
     d,t,h=dth(r);rn=nr(first(r,['race_no','race_number','race']))
     if d and t and h and rn:
      idx[(d,t,h)].add(rn);ref_rows+=1;used=True
    if used:ref_files+=1
  except:pass
 matches=[];un=[];aliasuse=Counter()
 for src,i,r in targets:
  d,t,h=dth(r);existing=nr(first(r,['race_no','race_number','race']))
  if existing:
   matches.append({'source':src,'source_row':i,'race_date':d,'track_raw':t,'track_match':t,'horse_key':h,'race_no':existing,'match_method':'EXISTING_RACE_NO','alias_applied':'NO'});continue
  if not(d and t and h):
   un.append({'source':src,'source_row':i,'race_date':d,'track_raw':t,'track_match':'','horse_key':h,'reason':'MISSING_DTH','candidate_race_nos':''});continue
  mt=aliases.get(t,t);alias_applied='YES' if mt!=t else 'NO'
  if alias_applied=='YES':aliasuse[(t,mt)]+=1
  vals=idx.get((d,mt,h),set())
  if len(vals)==1:
   rn=next(iter(vals));method='EXACT_DTH_AFTER_CERTIFIED_TRACK_ALIAS' if alias_applied=='YES' else 'EXACT_DTH_UNALIASED'
   matches.append({'source':src,'source_row':i,'race_date':d,'track_raw':t,'track_match':mt,'horse_key':h,'race_no':rn,'match_method':method,'alias_applied':alias_applied})
  else:
   reason='NO_EXACT_DTH_REFERENCE_MATCH' if not vals else 'AMBIGUOUS_RACE_NO'
   un.append({'source':src,'source_row':i,'race_date':d,'track_raw':t,'track_match':mt,'horse_key':h,'reason':reason,'candidate_race_nos':'|'.join(sorted(vals,key=lambda x:(len(x),x)))})
 with OUT_MATCH.open('w',newline='',encoding='utf-8') as h:w=csv.DictWriter(h,fieldnames=['source','source_row','race_date','track_raw','track_match','horse_key','race_no','match_method','alias_applied']);w.writeheader();w.writerows(matches)
 with OUT_UN.open('w',newline='',encoding='utf-8') as h:w=csv.DictWriter(h,fieldnames=['source','source_row','race_date','track_raw','track_match','horse_key','reason','candidate_race_nos']);w.writeheader();w.writerows(un)
 au=[{'target_track':a,'reference_track':b,'target_rows_alias_applied':n} for (a,b),n in aliasuse.most_common()]
 with OUT_ALIAS.open('w',newline='',encoding='utf-8') as h:w=csv.DictWriter(h,fieldnames=['target_track','reference_track','target_rows_alias_applied']);w.writeheader();w.writerows(au)
 mc=Counter(x['match_method'] for x in matches);uc=Counter(x['reason'] for x in un)
 metrics={'governed_target_rows':len(targets),'reference_files_excluding_checkpoints_sectionals':ref_files,'reference_rows_used':ref_rows,'certified_aliases_loaded':len(aliases),'already_has_race_no':mc['EXISTING_RACE_NO'],'exact_dth_unaliased_recovered':mc['EXACT_DTH_UNALIASED'],'exact_dth_after_certified_track_alias_recovered':mc['EXACT_DTH_AFTER_CERTIFIED_TRACK_ALIAS'],'total_race_identity_resolved_rows':len(matches),'race_identity_resolved_pct':round(100*len(matches)/len(targets),6),'missing_dth':uc['MISSING_DTH'],'no_exact_dth_reference_match':uc['NO_EXACT_DTH_REFERENCE_MATCH'],'ambiguous_race_no':uc['AMBIGUOUS_RACE_NO']}
 with OUT_SUM.open('w',newline='',encoding='utf-8') as h:w=csv.writer(h);w.writerow(['metric','value']);[w.writerow(x) for x in metrics.items()]
 print('='*100);print('EDGEIQ SECTIONAL RACE IDENTITY V25 — CERTIFIED TRACK ALIAS CROSSWALK');print('='*100)
 for k,v in metrics.items():print(f'{k}: {v}')
 print('\nTOP ALIAS USAGE');[print(x) for x in au[:40]]
 print('SUMMARY:',OUT_SUM);print('MATCHES:',OUT_MATCH);print('UNMATCHED:',OUT_UN);print('ALIAS_USAGE:',OUT_ALIAS)
if __name__=='__main__':main()
