from __future__ import annotations
import csv,re
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'
CONFLICT=DATA/'edgeiq_sectional_crosswalk_raceid_v9_conflicts.csv'
OUT=DATA/'edgeiq_sectional_reference_raceno_semantics_v10.csv'; SUMMARY=DATA/'edgeiq_sectional_reference_raceno_semantics_v10_summary.csv'
ALIASES={'race_id':('race_id','canonical_race_id','racingcom_race_id','raceid'),'race_no':('race_no','race_number','race'),'date':('race_date','date'),'track':('track','venue','track_name'),'horse':('horse','horse_name','runner','runner_name')}
def nk(s):return re.sub(r'[^a-z0-9]+','',str(s or '').lower())
def find(fs,als):
 d={nk(x):x for x in fs}
 for a in als:
  if nk(a) in d:return d[nk(a)]
 return ''
def norm_id(v):
 s=str(v or '').strip()
 try:
  f=float(s); return str(int(f)) if f.is_integer() else s
 except:return s
def norm_no(v):
 s=str(v or '').strip(); m=re.search(r'\d+',s)
 return str(int(m.group())) if m else ''
def main():
 if not CONFLICT.exists():raise SystemExit(f'Missing {CONFLICT}')
 target_ids=set()
 with CONFLICT.open('r',newline='',encoding='utf-8-sig') as h:
  rd=csv.DictReader(h)
  for r in rd:
   for k,v in r.items():
    if 'race_id' in nk(k):
     x=norm_id(v)
     if x:target_ids.add(x)
 print('target_conflict_race_ids:',len(target_ids))
 files=[]; evidence=defaultdict(lambda:defaultdict(lambda:{'rows':0,'files':set(),'dates':set(),'tracks':set(),'horses':set()}))
 for p in sorted(DATA.glob('*.csv')):
  low=p.name.lower()
  if 'graphql' not in low or 'result' not in low or low.endswith(('_audit.csv','_summary.csv')):continue
  try:
   with p.open('r',newline='',encoding='utf-8-sig') as h:
    rd=csv.DictReader(h); fs=list(rd.fieldnames or []); ridc=find(fs,ALIASES['race_id']); rnc=find(fs,ALIASES['race_no'])
    if not ridc or not rnc:continue
    dc=find(fs,ALIASES['date']); tc=find(fs,ALIASES['track']); hc=find(fs,ALIASES['horse']); hit=0
    for r in rd:
     rid=norm_id(r.get(ridc,''))
     if rid not in target_ids:continue
     rn=norm_no(r.get(rnc,''));
     if not rn:continue
     hit+=1; e=evidence[rid][rn];e['rows']+=1;e['files'].add(p.name)
     if dc and r.get(dc):e['dates'].add(str(r.get(dc)).strip())
     if tc and r.get(tc):e['tracks'].add(str(r.get(tc)).strip())
     if hc and r.get(hc):e['horses'].add(str(r.get(hc)).strip())
    if hit:files.append((p.name,hit))
  except Exception:pass
 rows=[]; disp=Counter()
 for rid in sorted(target_ids,key=lambda x:int(x) if x.isdigit() else x):
  vals=evidence.get(rid,{})
  ranked=sorted(vals.items(),key=lambda kv:(-kv[1]['rows'],int(kv[0]) if kv[0].isdigit() else 9999))
  total=sum(v['rows'] for _,v in ranked); top=ranked[0] if ranked else ('',{'rows':0,'files':set(),'dates':set(),'tracks':set(),'horses':set()})
  second=ranked[1][1]['rows'] if len(ranked)>1 else 0
  if not ranked: d='NO_REFERENCE_EVIDENCE'
  elif len(ranked)==1:d='UNANIMOUS_RACE_NO'
  elif top[1]['rows']>second and top[1]['rows']/total>=0.95:d='DOMINANT_95_PLUS'
  else:d='TRUE_CONFLICT'
  disp[d]+=1
  rows.append({'race_id':rid,'candidate_race_nos':'|'.join(f'{rn}:{v["rows"]}' for rn,v in ranked),'candidate_count':len(ranked),'total_reference_rows':total,'top_race_no':top[0],'top_rows':top[1]['rows'],'top_share':round(top[1]['rows']/total,6) if total else 0,'source_file_count':len(set().union(*(v['files'] for _,v in ranked))) if ranked else 0,'dates':'|'.join(sorted(set().union(*(v['dates'] for _,v in ranked)))) if ranked else '','tracks':'|'.join(sorted(set().union(*(v['tracks'] for _,v in ranked)))) if ranked else '','disposition':d})
 with OUT.open('w',newline='',encoding='utf-8') as h:
  fs=list(rows[0]) if rows else ['race_id'];w=csv.DictWriter(h,fieldnames=fs);w.writeheader();w.writerows(rows)
 with SUMMARY.open('w',newline='',encoding='utf-8') as h:
  w=csv.writer(h);w.writerow(['metric','value']);w.writerow(['target_conflict_race_ids',len(target_ids)]);w.writerow(['reference_files_with_conflict_ids',len(files)]);[w.writerow([k.lower(),v]) for k,v in disp.items()]
 print('='*90);print('EDGEIQ SECTIONAL REFERENCE RACE-NO SEMANTICS AUDIT V10');print('='*90);print('target_conflict_race_ids:',len(target_ids));print('reference_files_with_conflict_ids:',len(files));
 for k,v in disp.items():print(f'{k}: {v}')
 print('OUT:',OUT);print('SUMMARY:',SUMMARY)
if __name__=='__main__':main()
