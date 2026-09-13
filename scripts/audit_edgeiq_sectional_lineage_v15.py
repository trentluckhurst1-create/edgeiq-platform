from __future__ import annotations
import csv,re
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
PAYLOAD=DATA/'edgeiq_sectional_payload_reconstruction_v1.csv'
SECTIONALS=DATA/'sectionals.csv'
OUT_SUMMARY=DATA/'edgeiq_sectional_lineage_v15_summary.csv'
OUT_PAIR=DATA/'edgeiq_sectional_lineage_v15_parent_pair_audit.csv'
OUT_UNMATCHED=DATA/'edgeiq_sectional_lineage_v15_parent_unmatched.csv'
OUT_ROLE=DATA/'edgeiq_sectional_lineage_v15_source_role_decision.csv'

MISSING={'','-','nan','none','null','undefined','n/a'}

def clean(v):
 s=str(v or '').strip(); return '' if s.lower() in MISSING else s

def nk(s): return re.sub(r'[^a-z0-9]+','',clean(s).lower())
def nt(s): return ' '.join(clean(s).upper().replace('_',' ').split())
def nh(s): return re.sub(r'[^A-Z0-9]','',clean(s).upper())
def nd(s):
 s=clean(s)[:10]
 for f in ('%Y-%m-%d','%d/%m/%Y','%Y/%m/%d','%d-%m-%Y'):
  try:return datetime.strptime(s,f).strftime('%Y-%m-%d')
  except:pass
 return s

def first_nonmissing(row, cols):
 for c in cols:
  if c in row:
   v=clean(row.get(c,''))
   if v:return v
 return ''

def dth(row):
 d=nd(first_nonmissing(row,['race_date','run_date','date','meeting_date']))
 t=nt(first_nonmissing(row,['track','venue','meeting','track_name']))
 h=nh(first_nonmissing(row,['horse','horse_name','runner','runner_name','horse_key']))
 return d,t,h

def norm_text(v): return re.sub(r'\s+',' ',clean(v)).strip()

def row_signature(row, fields):
 return tuple(norm_text(row.get(f,'')) for f in fields)

def main():
 if not PAYLOAD.exists() or not SECTIONALS.exists(): raise SystemExit('Required files missing')
 with PAYLOAD.open('r',newline='',encoding='utf-8-sig') as h:
  pr=list(csv.DictReader(h))
 with SECTIONALS.open('r',newline='',encoding='utf-8-sig') as h:
  sr=list(csv.DictReader(h))
 total=Counter()
 total['payload_rows']=len(pr); total['sectionals_rows']=len(sr)
 parent=[r for r in pr if clean(r.get('source'))==r'public\data\sectionals.csv']
 total['payload_rows_source_sectionals']=len(parent)
 # Build layered indexes. source_row_id/source_lineage are preferred; DTH is fallback evidence only.
 p_by_rowid=defaultdict(list); p_by_lineage=defaultdict(list); p_by_dth=defaultdict(list)
 for i,r in enumerate(parent, start=1):
  rid=clean(r.get('source_row_id'))
  lin=clean(r.get('source_lineage'))
  if rid:p_by_rowid[rid].append(i)
  if lin:p_by_lineage[lin].append(i)
  k=dth(r)
  if all(k):p_by_dth[k].append(i)
 pair=[]; unmatched=[]; used=set()
 for idx,r in enumerate(sr,start=1):
  candidates=[]; method=''
  # Common lineage forms observed elsewhere are file#row and raw numeric row IDs.
  row_tokens={str(idx),str(idx+1),f'public\\data\\sectionals.csv#{idx}',f'public\\data\\sectionals.csv#{idx+1}'}
  for tok in row_tokens:
   if tok in p_by_rowid:candidates.extend(p_by_rowid[tok]); method='SOURCE_ROW_ID'
   if tok in p_by_lineage:candidates.extend(p_by_lineage[tok]); method='SOURCE_LINEAGE'
  candidates=sorted(set(candidates))
  if len(candidates)!=1:
   k=dth(r)
   if all(k):
    free=[x for x in p_by_dth.get(k,[]) if x not in used]
    if len(free)==1:candidates=free;method='EXACT_DTH_UNIQUE_MULTIPLICITY'
  if len(candidates)==1:
   pi=candidates[0];used.add(pi);p=parent[pi-1]
   total['parent_rows_matched']+=1; total[f'matched_{method}']+=1
   # Compare fields that are expected to carry identity/sectional information when shared.
   common=[f for f in r.keys() if f in p.keys() and f not in {'source','source_file','source_lineage','source_row_id','match_confidence','identity_status','reconstruction_confidence','structure_confidence','validation_status'}]
   diff=[]
   for f in common:
    a=norm_text(r.get(f,''));b=norm_text(p.get(f,''))
    if a!=b and not (a=='' and b==''):diff.append(f)
   pair.append({'sectionals_row':idx,'payload_parent_row':pi,'match_method':method,'sectionals_dth':'|'.join(dth(r)),'payload_dth':'|'.join(dth(p)),'common_fields_compared':len(common),'different_common_fields':len(diff),'different_field_names':'|'.join(diff[:50])})
   if not diff:total['parent_rows_exact_common_field_match']+=1
   else:total['parent_rows_with_common_field_differences']+=1
  else:
   total['parent_rows_unmatched_or_ambiguous']+=1
   unmatched.append({'sectionals_row':idx,'candidate_count':len(candidates),'race_date':dth(r)[0],'track':dth(r)[1],'horse_key':dth(r)[2]})
 total['payload_parent_rows_unpaired']=len(parent)-len(used)
 total['parent_pair_coverage_pct']=round((total['parent_rows_matched']/len(sr)*100) if sr else 0,6)
 # Governed decision is only PASS when cardinality and one-to-one pairing are complete.
 role_pass=(len(parent)==len(sr) and total['parent_rows_matched']==len(sr) and total['payload_parent_rows_unpaired']==0)
 decision=[
  {'dataset':'sectionals.csv','role':'RAW_PARENT_SOURCE' if role_pass else 'PROVISIONAL_PARENT_SOURCE','include_as_independent_target':'NO' if role_pass else 'YES_UNTIL_RESOLVED','evidence':'payload source attribution + one-to-one lineage audit'},
  {'dataset':'edgeiq_sectional_payload_reconstruction_v1.csv','role':'CANONICAL_RECONSTRUCTION_AGGREGATE' if role_pass else 'PROVISIONAL_RECONSTRUCTION_AGGREGATE','include_as_independent_target':'YES','evidence':'contains sectionals.csv lineage plus additional source families'},
 ]
 total['source_role_gate_pass']=1 if role_pass else 0
 with OUT_SUMMARY.open('w',newline='',encoding='utf-8') as h:
  w=csv.writer(h);w.writerow(['metric','value']);[w.writerow([k,v]) for k,v in total.items()]
 with OUT_PAIR.open('w',newline='',encoding='utf-8') as h:
  f=['sectionals_row','payload_parent_row','match_method','sectionals_dth','payload_dth','common_fields_compared','different_common_fields','different_field_names'];w=csv.DictWriter(h,fieldnames=f);w.writeheader();w.writerows(pair)
 with OUT_UNMATCHED.open('w',newline='',encoding='utf-8') as h:
  f=['sectionals_row','candidate_count','race_date','track','horse_key'];w=csv.DictWriter(h,fieldnames=f);w.writeheader();w.writerows(unmatched)
 with OUT_ROLE.open('w',newline='',encoding='utf-8') as h:
  f=['dataset','role','include_as_independent_target','evidence'];w=csv.DictWriter(h,fieldnames=f);w.writeheader();w.writerows(decision)
 print('='*96);print('EDGEIQ SECTIONAL LINEAGE V15 — ONE-TO-ONE PARENT SOURCE CERTIFICATION');print('='*96)
 for k,v in total.items():print(f'{k}: {v}')
 print('\nSOURCE ROLE DECISION')
 for r in decision:print(r)
 print('SUMMARY:',OUT_SUMMARY);print('PAIR_AUDIT:',OUT_PAIR);print('UNMATCHED:',OUT_UNMATCHED);print('ROLE_DECISION:',OUT_ROLE)
if __name__=='__main__':main()
