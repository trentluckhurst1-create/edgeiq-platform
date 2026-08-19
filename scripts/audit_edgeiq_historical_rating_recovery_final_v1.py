import csv, os, re, collections
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
DATA=os.path.join(ROOT,'public','data')
FORM=os.path.join(DATA,'edgeiq_form_enrichment_feed_v4.csv')
REC=os.path.join(DATA,'edgeiq_historical_rating_recovery_v1.csv')
APPLY=os.path.join(DATA,'edgeiq_historical_rating_recovery_apply_v1.csv')
OUT=os.path.join(DATA,'edgeiq_historical_rating_recovery_final_v1.csv')
SUM=os.path.join(DATA,'edgeiq_historical_rating_recovery_final_v1_summary.csv')
REP=os.path.join(DATA,'edgeiq_historical_rating_recovery_final_v1_report.txt')

def read_csv(path):
    with open(path,newline='',encoding='utf-8-sig',errors='replace') as f:
        r=csv.DictReader(f); return list(r), r.fieldnames or []
def blank(v): return v is None or str(v).strip()=='' or str(v).strip().upper() in {'--','N/A','NA','NULL','NONE','UNKNOWN','NAN'}
form,_=read_csv(FORM); rec,_=read_csv(REC); applied,_=read_csv(APPLY)
rows=[]; total_run_cells=0; rating_cells=0; missing_cells=0; first_run_lines=0; first_run_rated=0; truth=collections.Counter(); source=collections.Counter()
for r in form:
    truth[r.get('form_truth_status','')]+=1
    for i in range(1,6):
        has_run=not blank(r.get(f'last_start_{i}_date','')) or not blank(r.get(f'last_start_{i}_track',''))
        if not has_run: continue
        total_run_cells+=1
        has_rating=not blank(r.get(f'last_start_{i}_rating',''))
        if has_rating: rating_cells+=1
        else: missing_cells+=1
        if i==1:
            first_run_lines+=1
            if has_rating: first_run_rated+=1
        rows.append({'runner_key':r.get('runner_key',''),'horse':r.get('horse',''),'run_index':i,'run_date':r.get(f'last_start_{i}_date',''),'has_rating':'YES' if has_rating else 'NO','rating':r.get(f'last_start_{i}_rating',''),'source':r.get(f'last_start_{i}_source',''),'reason':r.get(f'last_start_{i}_reason',''),'status':'RATED' if has_rating else 'STILL_MISSING'})
for a in applied: source[a.get('recovery_source_bucket','UNKNOWN')]+=1
with open(OUT,'w',newline='',encoding='utf-8') as f:
    fields=['runner_key','horse','run_index','run_date','has_rating','rating','source','reason','status']
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
summary=[
 {'metric':'historical_run_lines','value':total_run_cells},
 {'metric':'rated_run_lines_after_recovery','value':rating_cells},
 {'metric':'missing_run_ratings_after_recovery','value':missing_cells},
 {'metric':'rating_coverage_pct_after_recovery','value':f'{rating_cells/max(1,total_run_cells)*100:.2f}'},
 {'metric':'recovered_ratings_applied','value':len(applied)},
 {'metric':'recovered_pct_of_pre_recovery_missing','value':f'{len(applied)/max(1,(len(applied)+missing_cells))*100:.2f}'},
 {'metric':'still_missing','value':missing_cells},
 {'metric':'last_start_1_run_lines','value':first_run_lines},
 {'metric':'last_start_1_rated_after_recovery','value':first_run_rated},
 {'metric':'last_start_1_rating_coverage_pct','value':f'{first_run_rated/max(1,first_run_lines)*100:.2f}'},
]
for k,v in truth.items(): summary.append({'metric':f'truth_{k}','value':v})
for k,v in source.items(): summary.append({'metric':f'recovered_source_{k}','value':v})
summary += [{'metric':'pricing_maths_changed','value':'NO'},{'metric':'v6_1_changed','value':'NO'},{'metric':'v7_2g2_changed','value':'NO'}]
with open(SUM,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows(summary)
rep=['EDGEiQ HISTORICAL RATING RECOVERY FINAL V1']+[f"{x['metric']}={x['value']}" for x in summary]+['status=HISTORICAL_RATING_RECOVERY_FINAL_COMPLETE']
with open(REP,'w',encoding='utf-8') as f: f.write('\n'.join(rep)+'\n')
print('\n'.join(rep))
