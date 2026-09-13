from __future__ import annotations
import csv,re,glob
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
P=DATA/'edgeiq_sectional_payload_reconstruction_v1.csv'
S=DATA/'sectionals.csv'
C22=DATA/'edgeiq_sectional_lineage_v22_residual_classification.csv'
OUT_SUM=DATA/'edgeiq_sectional_race_identity_v23_summary.csv'
OUT_MATCH=DATA/'edgeiq_sectional_race_identity_v23_matches.csv'
OUT_UN=DATA/'edgeiq_sectional_race_identity_v23_unmatched.csv'
OUT_REF=DATA/'edgeiq_sectional_race_identity_v23_reference_audit.csv'
MISS={'','-','nan','none','null','undefined','n/a'}

def cl(v):
 s=str(v or '').strip(); return '' if s.lower() in MISS else s

def nd(v):
 s=cl(v)[:10]
 for f in ('%Y-%m-%d','%d/%m/%Y','%Y/%m/%d','%d-%m-%Y'):
  try:return datetime.strptime(s,f).strftime('%Y-%m-%d')
  except:pass
 return s

def first(r,cols):
 for c in cols:
  v=cl(r.get(c,''))
  if v:return v
 return ''
def nt(v):return ' '.join(cl(v).upper().replace('_',' ').split())
def nh(v):return re.sub('[^A-Z0-9]','',cl(v).upper())
def safe_int(v):
 s=cl(v)
 if not s:return ''
 try:
  f=float(s)
  if f.is_integer():return str(int(f))
 except:pass
 m=re.fullmatch(r'R?\s*(\d{1,2})',s.upper())
 return str(int(m.group(1))) if m else ''
def norm_id(v):
 s=cl(v)
 if not s:return ''
 if re.fullmatch(r'\d+\.0',s):return s[:-2]
 return s

def rowkey(r):
 return (nd(first(r,['race_date','run_date','date','meeting_date'])),nt(first(r,['track','venue','meeting','track_name'])),nh(first(r,['horse','horse_name','runner','runner_name','horse_key'])))

def governed_rows():
 with P.open('r',newline='',encoding='utf-8-sig') as h:pr=list(csv.DictReader(h))
 with S.open('r',newline='',encoding='utf-8-sig') as h:sr=list(csv.DictReader(h))
 with C22.open('r',newline='',encoding='utf-8-sig') as h:cr=list(csv.DictReader(h))
 keep_idx={int(r['sectionals_row']) for r in cr if r.get('classification') in {'UNREPRESENTED_PARENT_SOURCE_ROW','UNRESOLVED_PARENT_IDENTITY'}}
 out=[]
 for i,r in enumerate(pr,1):out.append(('payload',i,r))
 for i in sorted(keep_idx):out.append(('sectionals_residual',i,sr[i-1]))
 return out

def ref_files():
 pats=['*historical_results*graphql*.csv','*graphql_master*.csv','*graphql*.csv']
 seen=[]
 for pat in pats:
  for p in DATA.glob(pat):
   if p.name.startswith('edgeiq_sectional_'):continue
   if p not in seen:seen.append(p)
 return seen

def main():
 rows=governed_rows(); refs=ref_files(); idx=defaultdict(set); ra=[]; total_ref=0
 for p in refs:
  used=0
  try:
   with p.open('r',newline='',encoding='utf-8-sig') as h:
    rd=csv.DictReader(h)
    for r in rd:
     d=nd(first(r,['race_date','date','meeting_date','run_date']));t=nt(first(r,['track','venue','meeting','track_name']));hkey=nh(first(r,['horse','horse_name','runner','runner_name']))
     rn=safe_int(first(r,['race_no','race_number','race','raceNum']));rid=norm_id(first(r,['race_id','raceId','id']))
     if d and t and hkey and rn:
      idx[(d,t,hkey)].add((rn,rid));used+=1
   total_ref+=used;ra.append({'file':str(p.relative_to(ROOT)),'usable_rows':used})
  except Exception as e:ra.append({'file':str(p.relative_to(ROOT)),'usable_rows':0,'error':type(e).__name__})
 matches=[];un=[];c=Counter(governed_target_rows=len(rows),reference_files=len(refs),reference_usable_rows=total_ref)
 for src,rownum,r in rows:
  d,t,h=rowkey(r);existing=safe_int(first(r,['race_no','race_number','race']))
  if existing:
   c['already_has_race_no']+=1;matches.append({'source':src,'source_row':rownum,'race_date':d,'track':t,'horse_key':h,'race_no':existing,'race_id':norm_id(first(r,['race_id','raceId'])),'match_method':'EXISTING_RACE_NO'}) ; continue
  if not (d and t and h):
   c['missing_identity_components']+=1;un.append({'source':src,'source_row':rownum,'race_date':d,'track':t,'horse_key':h,'reason':'MISSING_DTH'});continue
  cand=idx.get((d,t,h),set())
  race_nos=sorted({x[0] for x in cand},key=lambda x:int(x))
  if len(race_nos)==1:
   rn=race_nos[0];rids=sorted({x[1] for x in cand if x[1]})
   c['exact_unique_race_no_recovered']+=1;matches.append({'source':src,'source_row':rownum,'race_date':d,'track':t,'horse_key':h,'race_no':rn,'race_id':'|'.join(rids),'match_method':'EXACT_DATE_TRACK_HORSE_UNIQUE_RACE_NO'})
  elif len(race_nos)>1:
   c['ambiguous_multiple_race_no']+=1;un.append({'source':src,'source_row':rownum,'race_date':d,'track':t,'horse_key':h,'reason':'AMBIGUOUS_MULTIPLE_RACE_NO','candidate_race_nos':'|'.join(race_nos)})
  else:
   c['unmatched_exact_dth']+=1;un.append({'source':src,'source_row':rownum,'race_date':d,'track':t,'horse_key':h,'reason':'NO_EXACT_DTH_REFERENCE_MATCH'})
 c['race_identity_resolved_rows']=c['already_has_race_no']+c['exact_unique_race_no_recovered'];c['race_identity_resolved_pct']=round(c['race_identity_resolved_rows']/len(rows)*100,6) if rows else 0
 with OUT_SUM.open('w',newline='',encoding='utf-8') as h:w=csv.writer(h);w.writerow(['metric','value']);[w.writerow([k,v]) for k,v in c.items()]
 for fn,data,fs in [(OUT_MATCH,matches,['source','source_row','race_date','track','horse_key','race_no','race_id','match_method']),(OUT_UN,un,['source','source_row','race_date','track','horse_key','reason','candidate_race_nos']),(OUT_REF,ra,['file','usable_rows','error'])]:
  with fn.open('w',newline='',encoding='utf-8') as h:w=csv.DictWriter(h,fieldnames=fs,extrasaction='ignore');w.writeheader();w.writerows(data)
 print('='*100);print('EDGEIQ SECTIONAL RACE IDENTITY V23 — GOVERNED TARGET CROSSWALK');print('='*100)
 for k,v in c.items():print(f'{k}: {v}')
 print('SUMMARY:',OUT_SUM);print('MATCHES:',OUT_MATCH);print('UNMATCHED:',OUT_UN);print('REFERENCE_AUDIT:',OUT_REF)
if __name__=='__main__':main()
