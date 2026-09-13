from __future__ import annotations
import csv,re,hashlib
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
P=DATA/'edgeiq_sectional_payload_reconstruction_v1.csv'
S=DATA/'sectionals.csv'
OUT_SUM=DATA/'edgeiq_sectional_lineage_v19_summary.csv'
OUT_CERT=DATA/'edgeiq_sectional_lineage_v19_certified_pairs.csv'
OUT_RES=DATA/'edgeiq_sectional_lineage_v19_residual_641.csv'
OUT_COLL=DATA/'edgeiq_sectional_lineage_v19_collision_groups.csv'
OUT_ROLE=DATA/'edgeiq_sectional_lineage_v19_source_role_decision.csv'

MISS={'','-','nan','none','null','undefined','n/a'}
IGNORE_COMPARE={'source','source_file','source_lineage','source_row_id','match_confidence','identity_status','reconstruction_confidence','structure_confidence','validation_status'}

def cl(v):
 s=str(v or '').strip(); return '' if s.lower() in MISS else s

def norm_path(v):
 s=''.join('/' if ch==chr(92) else ch for ch in cl(v)).lower().strip()
 s=re.sub('/+','/',s)
 while s.startswith('./'): s=s[2:]
 return s

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

def dth(r):
 return (
  nd(first(r,['race_date','run_date','date','meeting_date'])),
  ' '.join(first(r,['track','venue','meeting','track_name']).upper().replace('_',' ').split()),
  re.sub('[^A-Z0-9]','',first(r,['horse','horse_name','runner','runner_name','horse_key']).upper())
 )

def norm(v): return re.sub(r'\s+',' ',cl(v)).strip()

def sig(r,fields):
 return hashlib.sha256(('\x1f'.join(norm(r.get(f,'')) for f in fields)).encode('utf-8')).hexdigest()

def main():
 with P.open('r',newline='',encoding='utf-8-sig') as h: pr=list(csv.DictReader(h))
 with S.open('r',newline='',encoding='utf-8-sig') as h: sr=list(csv.DictReader(h))
 target='public/data/sectionals.csv'
 parent=[r for r in pr if norm_path(r.get('source_file',''))==target]
 parent_global_rows=[i+1 for i,r in enumerate(pr) if norm_path(r.get('source_file',''))==target]
 if len(parent)!=36600:
  raise SystemExit(f'Expected 36600 source_file-attributed parent rows, found {len(parent)}')
 common=[f for f in sr[0].keys() if f in pr[0].keys() and f not in IGNORE_COMPARE] if sr and pr else []

 ix=defaultdict(list)
 for j,r in enumerate(parent):
  k=dth(r)
  if all(k): ix[k].append(j)

 total=Counter(payload_rows=len(pr),sectionals_rows=len(sr),attributed_parent_rows=len(parent))
 certified=[]; residual=[]; collisions=[]
 used_semantic_parent=set()

 for i,srow in enumerate(sr,1):
  k=dth(srow)
  cand=ix.get(k,[]) if all(k) else []
  if not cand:
   miss=[]
   if not k[0]: miss.append('DATE')
   if not k[1]: miss.append('TRACK')
   if not k[2]: miss.append('HORSE')
   residual.append({
    'sectionals_row':i,'race_date':k[0],'track':k[1],'horse_key':k[2],
    'missing_components':'|'.join(miss) if miss else 'DTH_PRESENT_NO_PARENT_MATCH',
    'source':cl(srow.get('source')),'run_date':cl(srow.get('run_date')),
    'horse':cl(srow.get('horse')),'raw_track':cl(srow.get('track'))
   })
   total['residual_rows']+=1
   continue

  csigs=[sig(parent[j],common) for j in cand]
  unique_sigs=sorted(set(csigs))
  if len(unique_sigs)==1:
   chosen=min(cand)
   method='EXACT_DTH_UNIQUE' if len(cand)==1 else 'EXACT_DTH_EQUIVALENT_DUPLICATE_COLLAPSE'
   if len(cand)>1:
    total['collision_rows_collapsed']+=1
    total['duplicate_candidate_rows_suppressed']+=len(cand)-1
    collisions.append({
     'sectionals_row':i,'race_date':k[0],'track':k[1],'horse_key':k[2],
     'candidate_count':len(cand),
     'parent_candidate_rows':'|'.join(str(j+1) for j in cand),
     'payload_global_rows':'|'.join(str(parent_global_rows[j]) for j in cand),
     'semantic_signatures': '|'.join(unique_sigs),
     'classification':'EQUIVALENT_DUPLICATE_GROUP'
    })
   else:
    total['unique_exact_rows']+=1
   used_semantic_parent.add((k,unique_sigs[0]))
   diff=[f for f in common if norm(srow.get(f,''))!=norm(parent[chosen].get(f,''))]
   certified.append({
    'sectionals_row':i,'payload_parent_row':chosen+1,'payload_global_row':parent_global_rows[chosen],
    'match_method':method,'race_date':k[0],'track':k[1],'horse_key':k[2],
    'candidate_count':len(cand),'different_common_fields':len(diff),
    'different_field_names':'|'.join(diff[:50])
   })
   total['certified_rows']+=1
  else:
   collisions.append({
    'sectionals_row':i,'race_date':k[0],'track':k[1],'horse_key':k[2],
    'candidate_count':len(cand),
    'parent_candidate_rows':'|'.join(str(j+1) for j in cand),
    'payload_global_rows':'|'.join(str(parent_global_rows[j]) for j in cand),
    'semantic_signatures':'|'.join(unique_sigs),
    'classification':'NON_EQUIVALENT_COLLISION'
   })
   total['non_equivalent_collision_rows']+=1

 total['certified_coverage_pct']=round(total['certified_rows']/len(sr)*100,6) if sr else 0
 total['residual_missing_date']=sum(1 for r in residual if 'DATE' in r['missing_components'])
 total['residual_missing_track']=sum(1 for r in residual if 'TRACK' in r['missing_components'])
 total['residual_missing_horse']=sum(1 for r in residual if 'HORSE' in r['missing_components'])
 total['residual_dth_present_no_parent_match']=sum(1 for r in residual if r['missing_components']=='DTH_PRESENT_NO_PARENT_MATCH')
 # We can certify the source relationship for the resolvable partition, but not yet demote the entire file until the residual 641 are resolved.
 total['partial_lineage_gate_pass']=int(total['non_equivalent_collision_rows']==0 and total['certified_rows']+total['residual_rows']==len(sr))
 total['full_source_role_gate_pass']=int(total['residual_rows']==0 and total['non_equivalent_collision_rows']==0 and total['certified_rows']==len(sr))

 decision=[
  {'dataset':'sectionals.csv','role':'PARTIALLY_CERTIFIED_PARENT_SOURCE' if total['partial_lineage_gate_pass'] else 'PROVISIONAL_PARENT_SOURCE','include_as_independent_target':'YES_UNTIL_641_RESOLVED' if total['residual_rows'] else 'NO','evidence':f"{total['certified_rows']} rows certified after semantic duplicate collapse; {total['residual_rows']} residual rows"},
  {'dataset':'edgeiq_sectional_payload_reconstruction_v1.csv','role':'PARTIALLY_CERTIFIED_RECONSTRUCTION_AGGREGATE' if total['partial_lineage_gate_pass'] else 'PROVISIONAL_RECONSTRUCTION_AGGREGATE','include_as_independent_target':'YES','evidence':'source_file attribution cardinality 36600; duplicate collisions semantically equivalent'}
 ]

 with OUT_SUM.open('w',newline='',encoding='utf-8') as h:
  w=csv.writer(h);w.writerow(['metric','value']);[w.writerow([k,v]) for k,v in total.items()]
 with OUT_CERT.open('w',newline='',encoding='utf-8') as h:
  fs=['sectionals_row','payload_parent_row','payload_global_row','match_method','race_date','track','horse_key','candidate_count','different_common_fields','different_field_names'];w=csv.DictWriter(h,fieldnames=fs);w.writeheader();w.writerows(certified)
 with OUT_RES.open('w',newline='',encoding='utf-8') as h:
  fs=['sectionals_row','race_date','track','horse_key','missing_components','source','run_date','horse','raw_track'];w=csv.DictWriter(h,fieldnames=fs);w.writeheader();w.writerows(residual)
 with OUT_COLL.open('w',newline='',encoding='utf-8') as h:
  fs=['sectionals_row','race_date','track','horse_key','candidate_count','parent_candidate_rows','payload_global_rows','semantic_signatures','classification'];w=csv.DictWriter(h,fieldnames=fs);w.writeheader();w.writerows(collisions)
 with OUT_ROLE.open('w',newline='',encoding='utf-8') as h:
  fs=['dataset','role','include_as_independent_target','evidence'];w=csv.DictWriter(h,fieldnames=fs);w.writeheader();w.writerows(decision)

 print('='*104);print('EDGEIQ SECTIONAL LINEAGE V19 — SEMANTIC DUPLICATE COLLAPSE + 641 RESIDUAL ISOLATION');print('='*104)
 for k,v in total.items(): print(f'{k}: {v}')
 print('\nROLE DECISION')
 for r in decision: print(r)
 print('SUMMARY:',OUT_SUM);print('CERTIFIED:',OUT_CERT);print('RESIDUAL:',OUT_RES);print('COLLISIONS:',OUT_COLL);print('ROLE:',OUT_ROLE)

if __name__=='__main__': main()
