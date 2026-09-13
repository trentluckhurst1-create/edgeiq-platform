from __future__ import annotations
import csv,re
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
P=DATA/'edgeiq_sectional_payload_reconstruction_v1.csv'
S=DATA/'sectionals.csv'
R19=DATA/'edgeiq_sectional_lineage_v19_residual_641.csv'
OUT_SUM=DATA/'edgeiq_sectional_lineage_v20_summary.csv'
OUT_HORSE=DATA/'edgeiq_sectional_lineage_v20_residual_horse_families.csv'
OUT_ALT=DATA/'edgeiq_sectional_lineage_v20_alternate_key_audit.csv'
OUT_MISS=DATA/'edgeiq_sectional_lineage_v20_missing_identity_residual.csv'
MISS={'','-','nan','none','null','undefined','n/a'}

def cl(v):
 s=str(v or '').strip();return '' if s.lower() in MISS else s

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
def tr(r):return ' '.join(first(r,['track','venue','meeting','track_name']).upper().replace('_',' ').split())
def ho(r):return re.sub('[^A-Z0-9]','',first(r,['horse','horse_name','runner','runner_name','horse_key']).upper())
def dt(r):return nd(first(r,['race_date','run_date','date','meeting_date']))
def dth(r):return (dt(r),tr(r),ho(r))
def norm_path(v):
 s=''.join('/' if ch==chr(92) else ch for ch in cl(v)).lower().strip();s=re.sub('/+','/',s)
 while s.startswith('./'):s=s[2:]
 return s

def main():
 with P.open('r',newline='',encoding='utf-8-sig') as h:pr=list(csv.DictReader(h))
 with S.open('r',newline='',encoding='utf-8-sig') as h:sr=list(csv.DictReader(h))
 with R19.open('r',newline='',encoding='utf-8-sig') as h:rr=list(csv.DictReader(h))
 parent=[r for r in pr if norm_path(r.get('source_file',''))=='public/data/sectionals.csv']
 # indexes over attributed payload parent rows; no fuzzy matching.
 by_dh=defaultdict(list);by_th=defaultdict(list);by_h=defaultdict(list);by_dt=defaultdict(list)
 for j,r in enumerate(parent,1):
  d,t,h=dth(r)
  if d and h:by_dh[(d,h)].append(j)
  if t and h:by_th[(t,h)].append(j)
  if h:by_h[h].append(j)
  if d and t:by_dt[(d,t)].append(j)
 residual=[]
 for x in rr:
  i=int(x['sectionals_row']);r=sr[i-1];d,t,h=dth(r)
  dh=by_dh.get((d,h),[]) if d and h else []
  th=by_th.get((t,h),[]) if t and h else []
  alt='NONE';cand=[]
  if len(dh)==1:alt='EXACT_DATE_HORSE_UNIQUE';cand=dh
  elif len(th)==1:alt='EXACT_TRACK_HORSE_UNIQUE';cand=th
  residual.append({'sectionals_row':i,'race_date':d,'track':t,'horse_key':h,'missing_components':x.get('missing_components',''),'date_horse_candidates':len(dh),'track_horse_candidates':len(th),'horse_parent_rows':len(by_h.get(h,[])),'alternate_key_class':alt,'payload_parent_rows':'|'.join(map(str,cand))})
 # Horse-family clustering of the 585 DTH-present residuals: detects systematic scaffold blocks.
 fam=defaultdict(list)
 for x in residual:
  if x['missing_components']=='DTH_PRESENT_NO_PARENT_MATCH':fam[x['horse_key']].append(x)
 horses=[]
 for h,rows in fam.items():
  horses.append({'horse_key':h,'residual_rows':len(rows),'min_date':min(x['race_date'] for x in rows),'max_date':max(x['race_date'] for x in rows),'unique_tracks':len(set(x['track'] for x in rows)),'parent_rows_same_horse':len(by_h.get(h,[])),'unique_date_horse_matches':sum(x['alternate_key_class']=='EXACT_DATE_HORSE_UNIQUE' for x in rows)})
 horses.sort(key=lambda x:(-x['residual_rows'],x['horse_key']))
 c=Counter()
 c['residual_rows']=len(residual);c['residual_unique_horses']=len(set(x['horse_key'] for x in residual if x['horse_key']))
 c['dth_present_no_parent_match']=sum(x['missing_components']=='DTH_PRESENT_NO_PARENT_MATCH' for x in residual)
 c['missing_track_only']=sum(x['missing_components']=='TRACK' for x in residual);c['missing_date_track']=sum(x['missing_components']=='DATE|TRACK' for x in residual)
 c['exact_date_horse_unique_recoverable']=sum(x['alternate_key_class']=='EXACT_DATE_HORSE_UNIQUE' for x in residual)
 c['exact_track_horse_unique_recoverable']=sum(x['alternate_key_class']=='EXACT_TRACK_HORSE_UNIQUE' for x in residual)
 c['residual_horse_families_dth_present']=len(fam);c['dth_residual_rows_in_multirow_horse_families']=sum(len(v) for v in fam.values() if len(v)>1)
 for fn,rows,fs in [(OUT_HORSE,horses,['horse_key','residual_rows','min_date','max_date','unique_tracks','parent_rows_same_horse','unique_date_horse_matches']),(OUT_ALT,residual,['sectionals_row','race_date','track','horse_key','missing_components','date_horse_candidates','track_horse_candidates','horse_parent_rows','alternate_key_class','payload_parent_rows']),(OUT_MISS,[x for x in residual if x['missing_components']!='DTH_PRESENT_NO_PARENT_MATCH'],['sectionals_row','race_date','track','horse_key','missing_components','date_horse_candidates','track_horse_candidates','horse_parent_rows','alternate_key_class','payload_parent_rows'])]:
  with fn.open('w',newline='',encoding='utf-8') as h:w=csv.DictWriter(h,fieldnames=fs);w.writeheader();w.writerows(rows)
 with OUT_SUM.open('w',newline='',encoding='utf-8') as h:w=csv.writer(h);w.writerow(['metric','value']);[w.writerow([k,v]) for k,v in c.items()]
 print('='*100);print('EDGEIQ SECTIONAL LINEAGE V20 — 641 RESIDUAL FAMILY + ALTERNATE-KEY AUDIT');print('='*100)
 for k,v in c.items():print(f'{k}: {v}')
 print('\nTOP DTH RESIDUAL HORSE FAMILIES');[print(x) for x in horses[:30]]
 print('SUMMARY:',OUT_SUM);print('HORSE_FAMILIES:',OUT_HORSE);print('ALT_KEYS:',OUT_ALT);print('MISSING_IDENTITY:',OUT_MISS)
if __name__=='__main__':main()
