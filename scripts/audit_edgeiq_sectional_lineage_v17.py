from __future__ import annotations
import csv,re
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'
P=DATA/'edgeiq_sectional_payload_reconstruction_v1.csv'; S=DATA/'sectionals.csv'
O=DATA/'edgeiq_sectional_lineage_v17_summary.csv'; A=DATA/'edgeiq_sectional_lineage_v17_source_field_forensic.csv'; PA=DATA/'edgeiq_sectional_lineage_v17_parent_pair_audit.csv'; U=DATA/'edgeiq_sectional_lineage_v17_parent_unmatched.csv'; R=DATA/'edgeiq_sectional_lineage_v17_source_role_decision.csv'
MISS={'','-','nan','none','null','undefined','n/a'}
def cl(v):
 s=str(v or '').strip(); return '' if s.lower() in MISS else s
def path(v):
 # Character-level conversion avoids all slash-literal ambiguity.
 s=''.join('/' if ch==chr(92) else ch for ch in cl(v)).lower().strip()
 s=re.sub('/+','/',s)
 while s.startswith('./'):s=s[2:]
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
def dth(r):return (nd(first(r,['race_date','run_date','date','meeting_date'])), ' '.join(first(r,['track','venue','meeting','track_name']).upper().replace('_',' ').split()), re.sub('[^A-Z0-9]','',first(r,['horse','horse_name','runner','runner_name','horse_key']).upper()))
def main():
 with P.open('r',newline='',encoding='utf-8-sig') as h: pr=list(csv.DictReader(h))
 with S.open('r',newline='',encoding='utf-8-sig') as h: sr=list(csv.DictReader(h))
 t=Counter(payload_rows=len(pr),sectionals_rows=len(sr)); fields=list(pr[0].keys()) if pr else []
 # Do not trust a hard-coded column name: inspect every field for sectionals.csv attribution.
 forensic=[]; hits=defaultdict(list)
 for f in fields:
  c=Counter()
  for i,r in enumerate(pr):
   raw=cl(r.get(f,'')); n=path(raw)
   if raw and ('sectionals.csv' in n or n.endswith('/sectionals.csv')):
    c[(raw,n)]+=1; hits[f].append(i)
  for (raw,n),count in c.items():forensic.append({'field':f,'raw_value':raw,'normalized_value':n,'rows':count})
 t['fields_with_sectionals_attribution']=len(hits)
 # Prefer exact normalized attribution in source; otherwise certify which single field V14 was actually seeing.
 candidate_fields=[]
 for f,idxs in hits.items():
  exact=[i for i in idxs if path(pr[i].get(f,''))=='public/data/sectionals.csv']
  if exact:candidate_fields.append((f,exact))
 candidate_fields.sort(key=lambda x:(x[0]!='source',-len(x[1]),x[0]))
 if candidate_fields:
  parent_field,parent_idx=candidate_fields[0]
 else: parent_field,parent_idx='',[]
 parent=[pr[i] for i in parent_idx]; t['payload_rows_source_sectionals']=len(parent); t['parent_attribution_field']=parent_field
 # Exact DTH multiplicity pairing, already supported by V14. This does not infer race identity.
 ix=defaultdict(list)
 for j,r in enumerate(parent):
  k=dth(r)
  if all(k):ix[k].append(j)
 used=set();pairs=[];un=[]
 for i,r in enumerate(sr,1):
  k=dth(r); free=[j for j in ix.get(k,[]) if j not in used] if all(k) else []
  if len(free)==1:
   j=free[0];used.add(j);t['parent_rows_matched']+=1;pairs.append({'sectionals_row':i,'payload_parent_row':j+1,'match_method':'EXACT_DTH_UNIQUE_MULTIPLICITY','dth':'|'.join(k)})
  else:
   t['parent_rows_unmatched_or_ambiguous']+=1;un.append({'sectionals_row':i,'candidate_count':len(free),'race_date':k[0],'track':k[1],'horse_key':k[2]})
 t['payload_parent_rows_unpaired']=len(parent)-len(used);t['parent_pair_coverage_pct']=round(t['parent_rows_matched']/len(sr)*100,6) if sr else 0
 # Full role gate requires attribution cardinality plus one-to-one row pairing. Rows lacking DTH remain unresolved rather than guessed.
 gate=len(parent)==len(sr) and t['parent_rows_matched']==len(sr) and t['payload_parent_rows_unpaired']==0;t['source_role_gate_pass']=int(gate)
 dec=[{'dataset':'sectionals.csv','role':'RAW_PARENT_SOURCE' if gate else 'PROVISIONAL_PARENT_SOURCE','include_as_independent_target':'NO' if gate else 'YES_UNTIL_RESOLVED','evidence':f'attribution_field={parent_field}; exact one-to-one DTH multiplicity gate'}, {'dataset':'edgeiq_sectional_payload_reconstruction_v1.csv','role':'CANONICAL_RECONSTRUCTION_AGGREGATE' if gate else 'PROVISIONAL_RECONSTRUCTION_AGGREGATE','include_as_independent_target':'YES','evidence':'payload attribution + lineage audit'}]
 with O.open('w',newline='',encoding='utf-8') as h:w=csv.writer(h);w.writerow(['metric','value']);[w.writerow([k,v]) for k,v in t.items()]
 for fn,rows,fs in [(A,forensic,['field','raw_value','normalized_value','rows']),(PA,pairs,['sectionals_row','payload_parent_row','match_method','dth']),(U,un,['sectionals_row','candidate_count','race_date','track','horse_key']),(R,dec,['dataset','role','include_as_independent_target','evidence'])]:
  with fn.open('w',newline='',encoding='utf-8') as h:w=csv.DictWriter(h,fieldnames=fs);w.writeheader();w.writerows(rows)
 print('='*100);print('EDGEIQ SECTIONAL LINEAGE V17 — SOURCE-FIELD FORENSIC + EXACT LINEAGE CERTIFICATION');print('='*100)
 print('PAYLOAD_FIELDS:', '|'.join(fields))
 for k,v in t.items():print(f'{k}: {v}')
 print('FORENSIC:');[print(x) for x in forensic[:30]]
 print('SUMMARY:',O);print('SOURCE_FORENSIC:',A);print('PAIR_AUDIT:',PA);print('UNMATCHED:',U);print('ROLE_DECISION:',R)
if __name__=='__main__':main()
