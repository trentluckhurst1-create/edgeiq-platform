from __future__ import annotations
import csv,re
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
S19=DATA/'edgeiq_sectional_lineage_v19_summary.csv'
R19=DATA/'edgeiq_sectional_lineage_v19_residual_641.csv'
A20=DATA/'edgeiq_sectional_lineage_v20_alternate_key_audit.csv'
U21=DATA/'edgeiq_sectional_lineage_v21_unresolved_residual.csv'
OUT_SUM=DATA/'edgeiq_sectional_lineage_v22_summary.csv'
OUT_CLASS=DATA/'edgeiq_sectional_lineage_v22_residual_classification.csv'
OUT_ROLE=DATA/'edgeiq_sectional_lineage_v22_source_role_decision.csv'
OUT_SCOPE=DATA/'edgeiq_sectional_lineage_v22_governed_target_scope.csv'

def read_csv(p):
 with p.open('r',newline='',encoding='utf-8-sig') as h:return list(csv.DictReader(h))

def main():
 s19={r['metric']:r['value'] for r in read_csv(S19)}
 r19=read_csv(R19);a20=read_csv(A20);u21=read_csv(U21)
 byrow={int(r['sectionals_row']):r for r in a20}
 unresolved8={int(r['sectionals_row']) for r in u21}
 rows=[];c=Counter()
 for r in r19:
  i=int(r['sectionals_row']);m=r.get('missing_components','');a=byrow.get(i,{})
  if a.get('alternate_key_class')=='EXACT_DATE_HORSE_UNIQUE':
   cls='CERTIFIED_EXACT_DATE_HORSE_PARENT_LINK';status='CERTIFIED';c['additional_exact_date_horse_certified']+=1
  elif i in unresolved8:
   cls='UNRESOLVED_PARENT_IDENTITY';status='UNRESOLVED';c['unresolved_identity_rows']+=1
  elif m=='DTH_PRESENT_NO_PARENT_MATCH':
   cls='UNREPRESENTED_PARENT_SOURCE_ROW';status='VALID_PARENT_ROW_NOT_IN_PAYLOAD_PARENT_COMPONENT';c['unrepresented_parent_source_rows']+=1
  else:
   cls='UNRESOLVED_OTHER';status='UNRESOLVED';c['unresolved_other_rows']+=1
  rows.append({'sectionals_row':i,'race_date':r.get('race_date',''),'track':r.get('track',''),'horse_key':r.get('horse_key',''),'prior_missing_components':m,'classification':cls,'governed_status':status,'payload_parent_rows':a.get('payload_parent_rows','')})
 base=int(float(s19.get('certified_rows','0')))
 c['v19_certified_rows']=base;c['final_certified_parent_links']=base+c['additional_exact_date_horse_certified']
 c['sectionals_rows_total']=int(float(s19.get('sectionals_rows','36600')))
 c['certified_parent_link_coverage_pct']=round(c['final_certified_parent_links']/c['sectionals_rows_total']*100,6)
 c['governed_sectionals_rows_retained']=c['unrepresented_parent_source_rows']+c['unresolved_identity_rows']+c['unresolved_other_rows']
 # Since payload omits genuine sectionals rows, sectionals.csv cannot be demoted wholesale.
 decision=[
  {'dataset':'sectionals.csv','role':'GOVERNED_RAW_PARENT_SOURCE','include_as_independent_target':'YES_FOR_UNREPRESENTED_ROWS','evidence':f"{c['unrepresented_parent_source_rows']} valid source rows absent from payload parent component; {c['unresolved_identity_rows']} identity-unresolved"},
  {'dataset':'edgeiq_sectional_payload_reconstruction_v1.csv','role':'PARTIAL_RECONSTRUCTION_AGGREGATE','include_as_independent_target':'YES','evidence':f"{c['final_certified_parent_links']} sectionals parent links certified; payload is not a complete substitute for sectionals.csv"}
 ]
 scope=[
  {'component':'payload_reconstruction','rows_rule':'retain all payload rows subject to later race/runner certification','double_count_guard':'exclude any sectionals.csv row with certified parent link into payload'},
  {'component':'sectionals_parent_residual','rows_rule':'retain only sectionals.csv rows classified UNREPRESENTED_PARENT_SOURCE_ROW or UNRESOLVED_PARENT_IDENTITY','double_count_guard':'do not re-add certified parent-linked rows'},
 ]
 with OUT_SUM.open('w',newline='',encoding='utf-8') as h:w=csv.writer(h);w.writerow(['metric','value']);[w.writerow([k,v]) for k,v in c.items()]
 with OUT_CLASS.open('w',newline='',encoding='utf-8') as h:
  fs=['sectionals_row','race_date','track','horse_key','prior_missing_components','classification','governed_status','payload_parent_rows'];w=csv.DictWriter(h,fieldnames=fs);w.writeheader();w.writerows(rows)
 with OUT_ROLE.open('w',newline='',encoding='utf-8') as h:
  fs=['dataset','role','include_as_independent_target','evidence'];w=csv.DictWriter(h,fieldnames=fs);w.writeheader();w.writerows(decision)
 with OUT_SCOPE.open('w',newline='',encoding='utf-8') as h:
  fs=['component','rows_rule','double_count_guard'];w=csv.DictWriter(h,fieldnames=fs);w.writeheader();w.writerows(scope)
 print('='*100);print('EDGEIQ SECTIONAL LINEAGE V22 — GOVERNED SOURCE ROLE + TARGET SCOPE');print('='*100)
 for k,v in c.items():print(f'{k}: {v}')
 print('\nROLE DECISION');[print(x) for x in decision]
 print('SUMMARY:',OUT_SUM);print('CLASSIFICATION:',OUT_CLASS);print('ROLE:',OUT_ROLE);print('SCOPE:',OUT_SCOPE)
if __name__=='__main__':main()
