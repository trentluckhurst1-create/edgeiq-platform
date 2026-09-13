from __future__ import annotations
import csv,re,hashlib
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
P=DATA/'edgeiq_sectional_payload_reconstruction_v1.csv'
S=DATA/'sectionals.csv'
R19=DATA/'edgeiq_sectional_lineage_v19_residual_641.csv'
OUT_SUM=DATA/'edgeiq_sectional_lineage_v21_summary.csv'
OUT_FAM=DATA/'edgeiq_sectional_lineage_v21_family_sequence_audit.csv'
OUT_ROW=DATA/'edgeiq_sectional_lineage_v21_row_sequence_pairs.csv'
OUT_RES=DATA/'edgeiq_sectional_lineage_v21_unresolved_residual.csv'
MISS={'','-','nan','none','null','undefined','n/a'}
IGNORE={'source','source_file','source_lineage','source_row_id','match_confidence','identity_status','reconstruction_confidence','structure_confidence','validation_status','race_date','run_date','date','meeting_date','track','venue','meeting','track_name'}

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
def ho(r):return re.sub('[^A-Z0-9]','',first(r,['horse','horse_name','runner','runner_name','horse_key']).upper())
def dt(r):return nd(first(r,['race_date','run_date','date','meeting_date']))
def tr(r):return ' '.join(first(r,['track','venue','meeting','track_name']).upper().replace('_',' ').split())
def norm_path(v):
 s=''.join('/' if ch==chr(92) else ch for ch in cl(v)).lower().strip();s=re.sub('/+','/',s)
 while s.startswith('./'):s=s[2:]
 return s

def n(v):return re.sub(r'\s+',' ',cl(v)).strip()
def sig(r,fields):return hashlib.sha256(('\x1f'.join(n(r.get(f,'')) for f in fields)).encode()).hexdigest()

def main():
 with P.open('r',newline='',encoding='utf-8-sig') as h:pr=list(csv.DictReader(h))
 with S.open('r',newline='',encoding='utf-8-sig') as h:sr=list(csv.DictReader(h))
 with R19.open('r',newline='',encoding='utf-8-sig') as h:rr=list(csv.DictReader(h))
 parent=[r for r in pr if norm_path(r.get('source_file',''))=='public/data/sectionals.csv']
 common=[f for f in sr[0].keys() if f in pr[0].keys() and f not in IGNORE] if sr and pr else []
 parent_by_h=defaultdict(list)
 for j,r in enumerate(parent,1):
  h=ho(r)
  if h:parent_by_h[h].append((j,r))
 residual_dth=[]; other=[]
 for x in rr:
  i=int(x['sectionals_row']);r=sr[i-1]
  rec=(i,r,x)
  if x.get('missing_components')=='DTH_PRESENT_NO_PARENT_MATCH':residual_dth.append(rec)
  else:other.append(rec)
 res_by_h=defaultdict(list)
 for i,r,x in residual_dth:res_by_h[ho(r)].append((i,r,x))
 fam_rows=[];row_pairs=[];certified_seq_rows=0
 for h,rs in sorted(res_by_h.items()):
  ps=parent_by_h.get(h,[])
  rs_sorted=sorted(rs,key=lambda z:(dt(z[1]),tr(z[1]),z[0]))
  ps_sorted=sorted(ps,key=lambda z:(dt(z[1]),tr(z[1]),z[0]))
  same_count=len(rs_sorted)==len(ps_sorted) and len(rs_sorted)>0
  residual_sigs=[sig(r,common) for _,r,_ in rs_sorted]
  parent_sigs=[sig(r,common) for _,r in ps_sorted]
  multiset_equal=Counter(residual_sigs)==Counter(parent_sigs) if same_count else False
  ordered_equal=residual_sigs==parent_sigs if same_count else False
  classification=''
  if same_count and ordered_equal:classification='ORDERED_SEQUENCE_EQUIVALENT'
  elif same_count and multiset_equal:classification='UNORDERED_MULTISET_EQUIVALENT'
  elif len(ps_sorted)==0:classification='NO_PARENT_SAME_HORSE_BLOCK'
  elif not same_count:classification='ROWCOUNT_MISMATCH'
  else:classification='NON_EQUIVALENT_BLOCK'
  if classification in {'ORDERED_SEQUENCE_EQUIVALENT','UNORDERED_MULTISET_EQUIVALENT'}:
   certified_seq_rows+=len(rs_sorted)
  fam_rows.append({'horse_key':h,'residual_rows':len(rs_sorted),'parent_same_horse_rows':len(ps_sorted),'same_row_count':'YES' if same_count else 'NO','ordered_signatures_equal':'YES' if ordered_equal else 'NO','multiset_signatures_equal':'YES' if multiset_equal else 'NO','classification':classification,'residual_min_date':min((dt(r) for _,r,_ in rs_sorted),default=''),'residual_max_date':max((dt(r) for _,r,_ in rs_sorted),default=''),'parent_min_date':min((dt(r) for _,r in ps_sorted),default=''),'parent_max_date':max((dt(r) for _,r in ps_sorted),default='')})
  # emit deterministic sequence comparison where cardinality matches
  if same_count:
   for pos,((si,srow,_),(pj,prow)) in enumerate(zip(rs_sorted,ps_sorted),1):
    row_pairs.append({'horse_key':h,'position':pos,'sectionals_row':si,'payload_parent_row':pj,'sectionals_date':dt(srow),'payload_date':dt(prow),'sectionals_track':tr(srow),'payload_track':tr(prow),'semantic_signature_equal':'YES' if sig(srow,common)==sig(prow,common) else 'NO'})
 # 48 date+horse rows are exact recoveries from V20 logic; recompute safely
 by_dh=defaultdict(list)
 for j,r in enumerate(parent,1):
  d,h=dt(r),ho(r)
  if d and h:by_dh[(d,h)].append(j)
 exact_dh=0; unresolved=[]
 for i,r,x in other:
  c=by_dh.get((dt(r),ho(r)),[]) if dt(r) and ho(r) else []
  if len(c)==1:exact_dh+=1
  else:unresolved.append({'sectionals_row':i,'race_date':dt(r),'track':tr(r),'horse_key':ho(r),'missing_components':x.get('missing_components',''),'date_horse_candidates':len(c),'horse_parent_rows':len(parent_by_h.get(ho(r),[]))})
 c=Counter()
 c['residual_rows_input']=len(rr);c['dth_present_residual_rows']=len(residual_dth);c['dth_residual_horse_families']=len(res_by_h)
 for r in fam_rows:c['family_'+r['classification'].lower()]+=1
 c['sequence_equivalent_rows_certifiable']=certified_seq_rows;c['exact_date_horse_rows_certifiable']=exact_dh
 c['total_additional_rows_certifiable']=certified_seq_rows+exact_dh;c['remaining_unresolved_rows']=len(rr)-(certified_seq_rows+exact_dh)
 with OUT_SUM.open('w',newline='',encoding='utf-8') as h:w=csv.writer(h);w.writerow(['metric','value']);[w.writerow([k,v]) for k,v in c.items()]
 with OUT_FAM.open('w',newline='',encoding='utf-8') as h:
  fs=['horse_key','residual_rows','parent_same_horse_rows','same_row_count','ordered_signatures_equal','multiset_signatures_equal','classification','residual_min_date','residual_max_date','parent_min_date','parent_max_date'];w=csv.DictWriter(h,fieldnames=fs);w.writeheader();w.writerows(fam_rows)
 with OUT_ROW.open('w',newline='',encoding='utf-8') as h:
  fs=['horse_key','position','sectionals_row','payload_parent_row','sectionals_date','payload_date','sectionals_track','payload_track','semantic_signature_equal'];w=csv.DictWriter(h,fieldnames=fs);w.writeheader();w.writerows(row_pairs)
 with OUT_RES.open('w',newline='',encoding='utf-8') as h:
  fs=['sectionals_row','race_date','track','horse_key','missing_components','date_horse_candidates','horse_parent_rows'];w=csv.DictWriter(h,fieldnames=fs);w.writeheader();w.writerows(unresolved)
 print('='*104);print('EDGEIQ SECTIONAL LINEAGE V21 — RESIDUAL HORSE-FAMILY SEQUENCE EQUIVALENCE');print('='*104)
 for k,v in c.items():print(f'{k}: {v}')
 print('\nFAMILY CLASSIFICATIONS');[print(x) for x in fam_rows]
 print('SUMMARY:',OUT_SUM);print('FAMILY_AUDIT:',OUT_FAM);print('ROW_PAIRS:',OUT_ROW);print('UNRESOLVED:',OUT_RES)
if __name__=='__main__':main()
