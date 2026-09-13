from __future__ import annotations
import csv,re,hashlib
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
P=DATA/'edgeiq_sectional_payload_reconstruction_v1.csv'
S=DATA/'sectionals.csv'
OUT_SUM=DATA/'edgeiq_sectional_lineage_v18_summary.csv'
OUT_FIELDS=DATA/'edgeiq_sectional_lineage_v18_attribution_fields.csv'
OUT_COLL=DATA/'edgeiq_sectional_lineage_v18_collision_audit.csv'
OUT_ROLE=DATA/'edgeiq_sectional_lineage_v18_source_role_decision.csv'

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

def row_sig(r, fields):
 return hashlib.sha256(('\x1f'.join(norm(r.get(f,'')) for f in fields)).encode('utf-8')).hexdigest()

def audit_field(field, idxs, pr, sr):
 parent=[pr[i] for i in idxs]
 ix=defaultdict(list)
 for j,r in enumerate(parent):
  k=dth(r)
  if all(k): ix[k].append(j)
 used=set(); matched=0; amb2=0; ambgt2=0; no=0
 collision_keys=[]
 for i,r in enumerate(sr,1):
  k=dth(r)
  cand=[j for j in ix.get(k,[]) if j not in used] if all(k) else []
  if len(cand)==1:
   used.add(cand[0]); matched+=1
  elif len(cand)==2:
   amb2+=1; collision_keys.append((i,k,cand,parent))
  elif len(cand)>2:
   ambgt2+=1; collision_keys.append((i,k,cand,parent))
  else:no+=1
 return {
  'field':field,
  'attributed_rows':len(parent),
  'complete_dth_parent_rows':sum(1 for r in parent if all(dth(r))),
  'unique_parent_dth_keys':len(ix),
  'one_to_one_matches':matched,
  'two_candidate_collisions':amb2,
  'gt2_candidate_collisions':ambgt2,
  'no_candidate_rows':no,
  'unpaired_parent_rows':len(parent)-len(used),
  'coverage_pct':round(matched/len(sr)*100,6) if sr else 0,
  'collision_keys':collision_keys,
 }

def main():
 with P.open('r',newline='',encoding='utf-8-sig') as h: pr=list(csv.DictReader(h))
 with S.open('r',newline='',encoding='utf-8-sig') as h: sr=list(csv.DictReader(h))
 fields=list(pr[0].keys()) if pr else []
 target='public/data/sectionals.csv'
 hits={}
 raw_counts=defaultdict(Counter)
 for f in fields:
  idx=[]
  for i,r in enumerate(pr):
   raw=cl(r.get(f,'')); np=norm_path(raw)
   if np==target:
    idx.append(i);raw_counts[f][raw]+=1
  if idx:hits[f]=idx

 audits=[]; details={}
 for f,idxs in hits.items():
  a=audit_field(f,idxs,pr,sr); details[f]=a
  audits.append({k:v for k,v in a.items() if k!='collision_keys'})

 # Rank by parent cardinality closeness first, then coverage, then fewer collisions/no-candidates.
 audits_sorted=sorted(audits,key=lambda a:(abs(a['attributed_rows']-len(sr)),-a['one_to_one_matches'],a['two_candidate_collisions']+a['gt2_candidate_collisions']+a['no_candidate_rows'],a['field']))
 best=audits_sorted[0] if audits_sorted else None
 collision_rows=[]
 if best:
  f=best['field']; a=details[f]; parent=[pr[i] for i in hits[f]]
  common=[x for x in sr[0].keys() if x in pr[0].keys() and x not in IGNORE_COMPARE] if sr and pr else []
  for srow,k,cand,_ in a['collision_keys']:
   s=sr[srow-1]
   sigs=[]; diffs=[]
   for j in cand:
    p=parent[j]
    sigs.append(row_sig(p,common))
    diff=[x for x in common if norm(s.get(x,''))!=norm(p.get(x,''))]
    diffs.append('|'.join(diff[:40]))
   same_candidates='YES' if len(set(sigs))==1 else 'NO'
   collision_rows.append({
    'sectionals_row':srow,'race_date':k[0],'track':k[1],'horse_key':k[2],
    'candidate_count':len(cand),'payload_candidate_rows':'|'.join(str(j+1) for j in cand),
    'candidate_common_field_signatures_equal':same_candidates,
    'candidate1_diff_fields':diffs[0] if diffs else '',
    'candidate2_diff_fields':diffs[1] if len(diffs)>1 else '',
   })

 total=Counter()
 total['payload_rows']=len(pr);total['sectionals_rows']=len(sr);total['attribution_fields_found']=len(audits)
 if best:
  total['selected_attribution_field']=best['field'];total['selected_attributed_rows']=best['attributed_rows'];total['selected_one_to_one_matches']=best['one_to_one_matches'];total['selected_two_candidate_collisions']=best['two_candidate_collisions'];total['selected_gt2_candidate_collisions']=best['gt2_candidate_collisions'];total['selected_no_candidate_rows']=best['no_candidate_rows'];total['selected_unpaired_parent_rows']=best['unpaired_parent_rows'];total['selected_coverage_pct']=best['coverage_pct']
  total['collision_rows_candidate_equivalent']=sum(1 for r in collision_rows if r['candidate_common_field_signatures_equal']=='YES')
  total['collision_rows_candidate_non_equivalent']=sum(1 for r in collision_rows if r['candidate_common_field_signatures_equal']=='NO')
 gate=bool(best and best['attributed_rows']==len(sr) and best['one_to_one_matches']==len(sr) and best['unpaired_parent_rows']==0)
 total['source_role_gate_pass']=int(gate)
 decision=[
  {'dataset':'sectionals.csv','role':'RAW_PARENT_SOURCE' if gate else 'PROVISIONAL_PARENT_SOURCE','include_as_independent_target':'NO' if gate else 'YES_UNTIL_RESOLVED','evidence':f"V18 best attribution field={best['field'] if best else 'NONE'}; cardinality-aware field audit"},
  {'dataset':'edgeiq_sectional_payload_reconstruction_v1.csv','role':'CANONICAL_RECONSTRUCTION_AGGREGATE' if gate else 'PROVISIONAL_RECONSTRUCTION_AGGREGATE','include_as_independent_target':'YES','evidence':'contains sectionals lineage plus additional source families'}
 ]

 with OUT_SUM.open('w',newline='',encoding='utf-8') as h:
  w=csv.writer(h);w.writerow(['metric','value']);[w.writerow([k,v]) for k,v in total.items()]
 with OUT_FIELDS.open('w',newline='',encoding='utf-8') as h:
  fs=['field','attributed_rows','complete_dth_parent_rows','unique_parent_dth_keys','one_to_one_matches','two_candidate_collisions','gt2_candidate_collisions','no_candidate_rows','unpaired_parent_rows','coverage_pct'];w=csv.DictWriter(h,fieldnames=fs);w.writeheader();w.writerows(audits_sorted)
 with OUT_COLL.open('w',newline='',encoding='utf-8') as h:
  fs=['sectionals_row','race_date','track','horse_key','candidate_count','payload_candidate_rows','candidate_common_field_signatures_equal','candidate1_diff_fields','candidate2_diff_fields'];w=csv.DictWriter(h,fieldnames=fs);w.writeheader();w.writerows(collision_rows)
 with OUT_ROLE.open('w',newline='',encoding='utf-8') as h:
  fs=['dataset','role','include_as_independent_target','evidence'];w=csv.DictWriter(h,fieldnames=fs);w.writeheader();w.writerows(decision)

 print('='*100);print('EDGEIQ SECTIONAL LINEAGE V18 — ATTRIBUTION FIELD + DUPLICATE COLLISION AUDIT');print('='*100)
 for k,v in total.items():print(f'{k}: {v}')
 print('\nATTRIBUTION FIELD AUDIT')
 for r in audits_sorted:print(r)
 print('SUMMARY:',OUT_SUM);print('FIELDS:',OUT_FIELDS);print('COLLISIONS:',OUT_COLL);print('ROLE:',OUT_ROLE)

if __name__=='__main__':main()
