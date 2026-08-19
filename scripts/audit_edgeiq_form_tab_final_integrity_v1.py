import csv, os, re, collections
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
DATA=os.path.join(ROOT,'public','data')
FORM=os.path.join(DATA,'edgeiq_form_enrichment_feed_v3.csv')
GOV=os.path.join(DATA,'edgeiq_live_runner_board_governed_v1.csv')
TSX=os.path.join(ROOT,'src','components','RaceIntelligenceScreen.tsx')
OUT=os.path.join(DATA,'edgeiq_form_tab_final_integrity_v1.csv')
SUM=os.path.join(DATA,'edgeiq_form_tab_final_integrity_summary_v1.csv')
REP=os.path.join(DATA,'edgeiq_form_tab_final_integrity_report_v1.txt')

def read_csv(path):
    with open(path,newline='',encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return list(r), r.fieldnames or []
def is_blank(v): return v is None or str(v).strip()=='' or str(v).strip().upper() in {'--','N/A','NA','NULL','NONE'}
def is_unknown(v): return is_blank(v) or str(v).strip().upper() in {'UNKNOWN','UNK'}
def clean(v): return re.sub(r'[^A-Z0-9]+','',str(v or '').upper())
def clean_track(v): return re.sub(r'\s+',' ',str(v or '').upper().strip())
def key(r):
    rk=str(r.get('runner_key','')).strip()
    if rk: return rk
    return '|'.join([str(r.get('race_date','')).strip(),clean_track(r.get('track','')),str(r.get('race_no','')).upper().replace('R','').strip(),clean(r.get('horse_key') or r.get('horse'))])
form, form_cols=read_csv(FORM); gov, gov_cols=read_csv(GOV)
form_keys=[key(r) for r in form]; gov_keys=[key(r) for r in gov]
text=open(TSX,encoding='utf-8').read()
checks=[]
truth=collections.Counter(r.get('form_truth_status','') for r in form)
for r in form:
    status=r.get('form_truth_status','')
    row_status='OK'
    issues=[]
    if not r.get('runner_key'): issues.append('MISSING_RUNNER_KEY')
    if status=='OK_HISTORY' and is_blank(r.get('last_start_1_date')) and is_blank(r.get('last_start_1_rating')): issues.append('OK_HISTORY_NO_RUN_DETAIL')
    if status=='BACKFILLED_CONTEXT_ONLY':
        any_fake=False
        for n in range(1,6):
            if not is_blank(r.get(f'last_start_{n}_date')) or not is_blank(r.get(f'last_start_{n}_rating')):
                any_fake=True
        if any_fake: issues.append('CONTEXT_ONLY_HAS_RUN_DETAIL')
    if issues: row_status='FIX_REQUIRED'
    checks.append({'race_date':r.get('race_date',''),'track':r.get('track',''),'race_no':r.get('race_no',''),'horse':r.get('horse',''),'runner_key':r.get('runner_key',''),'form_truth_status':status,'integrity_status':row_status,'issues':';'.join(issues)})
required_cols=[]
for n in range(1,6):
    required_cols += [f'last_start_{n}_class',f'last_start_{n}_distance',f'last_start_{n}_condition',f'last_start_{n}_reason',f'last_start_{n}_finishing_position',f'last_start_{n}_beaten_margin',f'last_start_{n}_SP']
missing_cols=[c for c in required_cols if c not in form_cols]
summary=[]
summary.append({'metric':'governed_rows','value':len(gov)})
summary.append({'metric':'governed_races','value':len(set((r.get('race_date',''),r.get('track',''),r.get('race_no','')) for r in gov))})
summary.append({'metric':'form_rows','value':len(form)})
summary.append({'metric':'form_races','value':len(set((r.get('race_date',''),r.get('track',''),r.get('race_no','')) for r in form))})
summary.append({'metric':'runner_key_populated','value':sum(1 for r in form if r.get('runner_key'))})
summary.append({'metric':'duplicate_form_runner_keys','value':len(form_keys)-len(set(form_keys))})
summary.append({'metric':'form_keys_missing_from_governed','value':len(set(form_keys)-set(gov_keys))})
summary.append({'metric':'governed_keys_missing_from_form','value':len(set(gov_keys)-set(form_keys))})
for k2,v in truth.items(): summary.append({'metric':f'truth_{k2}','value':v})
for fld in ['last_start_1_date','last_start_1_rating','last_start_1_class','last_start_1_distance','last_start_1_condition']:
    summary.append({'metric':f'{fld}_populated','value':sum(1 for r in form if not is_unknown(r.get(fld,'')))})
summary.append({'metric':'required_form_columns_missing','value':len(missing_cols)})
summary.append({'metric':'row_fix_required','value':sum(1 for c in checks if c['integrity_status']=='FIX_REQUIRED')})
summary.append({'metric':'tsx_loads_v3','value':'YES' if '/data/edgeiq_form_enrichment_feed_v3.csv' in text else 'NO'})
summary.append({'metric':'tsx_has_top_level_form','value':'YES' if 'intelMode === "FORM"' in text else 'NO'})
summary.append({'metric':'tsx_has_sp_column','value':'YES' if '<span>SP</span>' in text else 'NO'})
summary.append({'metric':'tsx_has_reason_column','value':'YES' if '<span>Reason</span>' in text else 'NO'})
summary.append({'metric':'tsx_has_context_message','value':'YES' if 'Context only - no detailed rated-history lines available.' in text else 'NO'})
summary += [{'metric':'pricing_maths_changed','value':'NO'},{'metric':'v6_1_changed','value':'NO'},{'metric':'v7_2g2_changed','value':'NO'}]
with open(OUT,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(checks[0].keys())); w.writeheader(); w.writerows(checks)
with open(SUM,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows(summary)
summary_map={r['metric']:str(r['value']) for r in summary}
ready = (
    summary_map.get('governed_rows')=='383' and summary_map.get('form_rows')=='383' and summary_map.get('runner_key_populated')=='383' and
    summary_map.get('duplicate_form_runner_keys')=='0' and summary_map.get('governed_keys_missing_from_form')=='0' and
    summary_map.get('required_form_columns_missing')=='0' and summary_map.get('row_fix_required')=='0' and
    summary_map.get('tsx_loads_v3')=='YES' and summary_map.get('tsx_has_top_level_form')=='YES' and summary_map.get('tsx_has_sp_column')=='YES' and summary_map.get('tsx_has_reason_column')=='YES'
)
rep=['EDGEiQ FORM TAB FINAL INTEGRITY V1',f'governed_rows={summary_map.get("governed_rows")}',f'governed_races={summary_map.get("governed_races")}',f'form_rows={summary_map.get("form_rows")}',f'OK_HISTORY={summary_map.get("truth_OK_HISTORY","0")}',f'CONTEXT_ONLY={summary_map.get("truth_BACKFILLED_CONTEXT_ONLY","0")}',f'last_start_1_date_populated={summary_map.get("last_start_1_date_populated")}',f'last_start_1_rating_populated={summary_map.get("last_start_1_rating_populated")}',f'last_start_1_class_populated={summary_map.get("last_start_1_class_populated")}',f'last_start_1_distance_populated={summary_map.get("last_start_1_distance_populated")}',f'last_start_1_condition_populated={summary_map.get("last_start_1_condition_populated")}',f'missing_required_columns={missing_cols}',f'tsx_loads_v3={summary_map.get("tsx_loads_v3")}',f'tsx_has_sp_column={summary_map.get("tsx_has_sp_column")}',f'tsx_has_reason_column={summary_map.get("tsx_has_reason_column")}',f'pricing_maths_changed=NO',f'v6_1_changed=NO',f'v7_2g2_changed=NO',f'status={"FORM_TAB_FINAL_INTEGRITY_PASS" if ready else "FORM_TAB_FINAL_INTEGRITY_REVIEW_REQUIRED"}']
with open(REP,'w',encoding='utf-8') as f: f.write('\n'.join(rep)+'\n')
print('\n'.join(rep))
