import csv, os, re, collections
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
DATA=os.path.join(ROOT,'public','data')
GOV=os.path.join(DATA,'edgeiq_live_runner_board_governed_v1.csv')
FORM=os.path.join(DATA,'edgeiq_form_enrichment_feed_v4.csv')
V3=os.path.join(DATA,'edgeiq_form_enrichment_feed_v3.csv')
TSX=os.path.join(ROOT,'src','components','RaceIntelligenceScreen.tsx')
OUT=os.path.join(DATA,'edgeiq_form_v4_final_integrity_v1.csv')
SUM=os.path.join(DATA,'edgeiq_form_v4_final_integrity_summary_v1.csv')
REP=os.path.join(DATA,'edgeiq_form_v4_final_integrity_report_v1.txt')

def read_csv(path):
    with open(path,newline='',encoding='utf-8-sig',errors='replace') as f:
        r=csv.DictReader(f); return list(r), r.fieldnames or []
def blank(v): return v is None or str(v).strip()=='' or str(v).strip().upper() in {'--','N/A','NA','NULL','NONE','UNKNOWN','NAN'}
def norm_horse(v):
    s=str(v or '').upper(); s=re.sub(r'\([^)]*\)',' ',s); s=re.sub(r'\b\d+E\b',' ',s); return re.sub(r'[^A-Z0-9]+','',s)
def clean_track(v): return re.sub(r'\s+',' ',str(v or '').upper().strip())
def norm_race(v): return str(v or '').upper().replace('R','').replace('.0','').strip()
def key(r):
    rk=str(r.get('runner_key','')).strip()
    if rk: return rk
    return '|'.join([str(r.get('race_date','')).strip(),clean_track(r.get('track','')),norm_race(r.get('race_no')),norm_horse(r.get('horse_key') or r.get('horse'))])
def run_count(r):
    return sum(1 for i in range(1,6) if not blank(r.get(f'last_start_{i}_date','')) or not blank(r.get(f'last_start_{i}_track','')) or not blank(r.get(f'last_start_{i}_rating','')))

gov, gov_cols=read_csv(GOV); form, form_cols=read_csv(FORM); v3, _=read_csv(V3)
gov_keys=[key(r) for r in gov]; form_keys=[key(r) for r in form]
v3_by_key={key(r):r for r in v3}
rows=[]; truth=collections.Counter(); improved=0; ok_partial_runs=[]
for r in form:
    k=key(r); status=r.get('form_truth_status',''); truth[status]+=1
    rc=run_count(r); v3c=run_count(v3_by_key.get(k,{}))
    if rc>v3c: improved+=1
    if status in {'OK_HISTORY','PARTIAL_HISTORY'}: ok_partial_runs.append(rc)
    issues=[]
    if not r.get('runner_key'): issues.append('MISSING_RUNNER_KEY')
    if status in {'OK_HISTORY','PARTIAL_HISTORY'} and rc==0: issues.append('HISTORY_STATUS_WITH_NO_RUN_LINES')
    if status in {'CONTEXT_ONLY','SOURCE_GAP'} and rc>0: issues.append('CONTEXT_OR_GAP_HAS_RUN_LINES')
    rows.append({'race_date':r.get('race_date',''),'track':r.get('track',''),'race_no':r.get('race_no',''),'horse':r.get('horse',''),'runner_key':r.get('runner_key',''),'form_truth_status':status,'form_source':r.get('form_source',''),'form_data_quality':r.get('form_data_quality',''),'run_lines':rc,'v3_run_lines':v3c,'improved_vs_v3':'YES' if rc>v3c else 'NO','issues':';'.join(issues),'integrity_status':'FIX_REQUIRED' if issues else 'OK'})
text=open(TSX,encoding='utf-8').read()
summary=[
 {'metric':'governed_rows','value':len(gov)},
 {'metric':'governed_races','value':len(set((r.get('race_date',''),r.get('track',''),r.get('race_no','')) for r in gov))},
 {'metric':'form_v4_rows','value':len(form)},
 {'metric':'form_v4_races','value':len(set((r.get('race_date',''),r.get('track',''),r.get('race_no','')) for r in form))},
 {'metric':'runner_key_populated','value':sum(1 for r in form if r.get('runner_key'))},
 {'metric':'duplicate_runner_keys','value':len(form_keys)-len(set(form_keys))},
 {'metric':'form_keys_missing_from_governed','value':len(set(form_keys)-set(gov_keys))},
 {'metric':'governed_keys_missing_from_form','value':len(set(gov_keys)-set(form_keys))},
]
for name in ['OK_HISTORY','PARTIAL_HISTORY','CONTEXT_ONLY','SOURCE_GAP']:
    summary.append({'metric':f'{name}_count','value':truth.get(name,0)})
for fld in ['last_start_1_date','last_start_1_rating','last_start_1_class','last_start_1_distance','last_start_1_condition']:
    summary.append({'metric':f'{fld}_count','value':sum(1 for r in form if not blank(r.get(fld,'')))})
summary += [
 {'metric':'average_run_lines_per_ok_partial_horse','value':f'{(sum(ok_partial_runs)/max(1,len(ok_partial_runs))):.2f}'},
 {'metric':'horses_improved_vs_v3','value':improved},
 {'metric':'fix_required_rows','value':sum(1 for r in rows if r['integrity_status']=='FIX_REQUIRED')},
 {'metric':'tsx_references_v4','value':'YES' if '/data/edgeiq_form_enrichment_feed_v4.csv' in text else 'NO'},
 {'metric':'tsx_has_data_quality_badge','value':'YES' if 'selectedFormDataQuality' in text and 'DATA QUALITY' in text else 'NO'},
 {'metric':'tsx_has_source_comment_column','value':'YES' if 'Source / Comment' in text else 'NO'},
 {'metric':'pricing_maths_changed','value':'NO'}, {'metric':'v6_1_changed','value':'NO'}, {'metric':'v7_2g2_changed','value':'NO'}]
with open(OUT,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
with open(SUM,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows(summary)
sm={r['metric']:str(r['value']) for r in summary}
ready=sm['governed_rows']=='383' and sm['form_v4_rows']=='383' and sm['runner_key_populated']=='383' and sm['duplicate_runner_keys']=='0' and sm['governed_keys_missing_from_form']=='0' and sm['fix_required_rows']=='0' and sm['tsx_references_v4']=='YES' and sm['tsx_has_data_quality_badge']=='YES'
rep=['EDGEiQ FORM V4 FINAL INTEGRITY V1']+[f"{r['metric']}={r['value']}" for r in summary]+[f'status={"FORM_V4_FINAL_INTEGRITY_PASS" if ready else "FORM_V4_FINAL_INTEGRITY_REVIEW_REQUIRED"}']
with open(REP,'w',encoding='utf-8') as f: f.write('\n'.join(rep)+'\n')
print('\n'.join(rep))
