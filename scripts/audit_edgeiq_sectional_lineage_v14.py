from __future__ import annotations
import csv,re
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'
P=DATA/'edgeiq_sectional_payload_reconstruction_v1.csv'; S=DATA/'sectionals.csv'
OUT=DATA/'edgeiq_sectional_lineage_v14_summary.csv'; PAIRS=DATA/'edgeiq_sectional_lineage_v14_pair_overlap.csv'; SRC=DATA/'edgeiq_sectional_lineage_v14_source_values.csv'; SAMPLE=DATA/'edgeiq_sectional_lineage_v14_samples.csv'
M={'','-','nan','none','null','undefined','n/a'}
def clean(v):
 s=str(v or '').strip();return '' if s.lower() in M else s
def normdate(v):
 s=clean(v)[:10]
 for f in ('%Y-%m-%d','%d/%m/%Y','%Y/%m/%d','%d-%m-%Y'):
  try:return datetime.strptime(s,f).strftime('%Y-%m-%d')
  except:pass
 return s
def nt(v):return ' '.join(clean(v).upper().replace('_',' ').split())
def nh(v):return re.sub(r'[^A-Z0-9]','',clean(v).upper())
def first(r,*names):
 for n in names:
  if n in r and clean(r[n]):return clean(r[n])
 return ''
def load(path):
 rows=[]
 with path.open('r',newline='',encoding='utf-8-sig') as h:
  for n,r in enumerate(csv.DictReader(h),2):
   d=normdate(first(r,'race_date','run_date','date','meeting_date'));t=nt(first(r,'track','venue','meeting','track_name'));ho=nh(first(r,'horse','horse_name','runner','runner_name','horse_key'))
   rows.append({'row_no':n,'date':d,'track':t,'horse':ho,'source':first(r,'source','source_file'),'source_lineage':first(r,'source_lineage'),'source_row_id':first(r,'source_row_id'),'sectional_race_key':first(r,'sectional_race_key'),'sectional_runner_key':first(r,'sectional_runner_key')})
 return rows
p=load(P);s=load(S);pc=Counter((r['date'],r['track'],r['horse']) for r in p if r['date'] and r['track'] and r['horse']);sc=Counter((r['date'],r['track'],r['horse']) for r in s if r['date'] and r['track'] and r['horse']);pk=set(pc);sk=set(sc);both=pk&sk
summary=[('payload_rows',len(p)),('sectionals_rows',len(s)),('payload_complete_dth_rows',sum(pc.values())),('sectionals_complete_dth_rows',sum(sc.values())),('payload_unique_dth_keys',len(pk)),('sectionals_unique_dth_keys',len(sk)),('shared_unique_dth_keys',len(both)),('payload_only_unique_dth_keys',len(pk-sk)),('sectionals_only_unique_dth_keys',len(sk-pk)),('shared_payload_rows',sum(pc[k] for k in both)),('shared_sectionals_rows',sum(sc[k] for k in both)),('exact_multiplicity_match_keys',sum(1 for k in both if pc[k]==sc[k])),('multiplicity_mismatch_keys',sum(1 for k in both if pc[k]!=sc[k]))]
with OUT.open('w',newline='',encoding='utf-8') as h:
 w=csv.writer(h);w.writerow(['metric','value']);w.writerows(summary)
with PAIRS.open('w',newline='',encoding='utf-8') as h:
 w=csv.writer(h);w.writerow(['race_date','track','horse_key','payload_rows','sectionals_rows','multiplicity_equal']);
 for k in sorted(both):w.writerow([*k,pc[k],sc[k],'YES' if pc[k]==sc[k] else 'NO'])
vals=[]
for label,rows in [('payload',p),('sectionals',s)]:
 for field in ('source','source_lineage'):
  c=Counter(r[field] or '<MISSING>' for r in rows)
  for v,n in c.most_common():vals.append([label,field,v,n])
with SRC.open('w',newline='',encoding='utf-8') as h:
 w=csv.writer(h);w.writerow(['dataset','field','value','rows']);w.writerows(vals)
with SAMPLE.open('w',newline='',encoding='utf-8') as h:
 f=['dataset','row_no','date','track','horse','source','source_lineage','source_row_id','sectional_race_key','sectional_runner_key'];w=csv.DictWriter(h,fieldnames=f);w.writeheader()
 for label,rows in [('payload',p),('sectionals',s)]:
  for r in rows[:100]:w.writerow({'dataset':label,**r})
print('='*92);print('EDGEIQ SECTIONAL LINEAGE V14 — TARGET SEMANTIC OVERLAP');print('='*92)
for k,v in summary:print(f'{k}: {v}')
print('SUMMARY:',OUT);print('PAIR_OVERLAP:',PAIRS);print('SOURCE_VALUES:',SRC);print('SAMPLES:',SAMPLE)
