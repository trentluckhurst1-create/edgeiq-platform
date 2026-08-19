import csv, os, re, shutil, collections
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
DATA=os.path.join(ROOT,'public','data')
FORM=os.path.join(DATA,'edgeiq_form_enrichment_feed_v4.csv')
REC=os.path.join(DATA,'edgeiq_historical_rating_recovery_v1.csv')
BOARDS=[os.path.join(DATA,'edgeiq_live_runner_board_v1.csv'),os.path.join(DATA,'edgeiq_live_runner_board_governed_v1.csv')]
OUT=os.path.join(DATA,'edgeiq_historical_rating_recovery_apply_v1.csv')
SUM=os.path.join(DATA,'edgeiq_historical_rating_recovery_apply_v1_summary.csv')
REP=os.path.join(DATA,'edgeiq_historical_rating_recovery_apply_v1_report.txt')

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
def fnum(v):
    try:
        if blank(v): return None
        return float(v)
    except Exception: return None
def run_count(r): return sum(1 for i in range(1,6) if not blank(r.get(f'last_start_{i}_date','')) or not blank(r.get(f'last_start_{i}_track','')))
def rating_count(r): return sum(1 for i in range(1,6) if not blank(r.get(f'last_start_{i}_rating','')))
def recompute(row):
    ratings=[]
    for i in range(1,6):
        v=fnum(row.get(f'last_start_{i}_rating',''))
        if v is not None: ratings.append(v)
    rc=run_count(row); rct=len(ratings)
    if rc:
        row['form_truth_status']='OK_HISTORY' if rc>=3 and rct>=3 else 'PARTIAL_HISTORY'
        row['form_data_quality']='FULL HISTORY' if row['form_truth_status']=='OK_HISTORY' else 'PARTIAL HISTORY'
    else:
        row['form_truth_status']='CONTEXT_ONLY'
        row['form_data_quality']='CONTEXT ONLY'
    if ratings:
        row['form_last_start_rating']=f'{ratings[0]:.1f}'
        row['form_avg_rating_last5']=f'{sum(ratings)/len(ratings):.1f}'
        row['form_peak_rating_last5']=f'{max(ratings):.1f}'
        if len(ratings)>1:
            delta=ratings[0]-ratings[1]
            row['form_previous_start_rating']=f'{ratings[1]:.1f}'
            row['form_rating_delta_last_start']=f'{delta:.1f}'
            trend='IMPROVING' if delta>=3 else 'REGRESSING' if delta<=-3 else 'HOLDING'
        else:
            row['form_previous_start_rating']=''; row['form_rating_delta_last_start']=''; trend='LIMITED FORM'
    else:
        row['form_last_start_rating']=''; row['form_avg_rating_last5']=''; row['form_peak_rating_last5']=''; row['form_previous_start_rating']=''; row['form_rating_delta_last_start']=''; trend='LIMITED FORM' if rc else 'CONTEXT ONLY'
    row['form_trend']=trend; row['rating_trend']=trend; row['rating_trend_delta']=row.get('form_rating_delta_last_start',''); row['form_cycle']=trend
    row['form_signal']='RECENT FORM LOADED' if row['form_truth_status']=='OK_HISTORY' else 'PARTIAL FORM LOADED' if row['form_truth_status']=='PARTIAL_HISTORY' else 'CONTEXT ONLY'
    row['performance_intelligence_label']='IMPROVING' if trend=='IMPROVING' else 'BELOW EXPECTATIONS' if trend=='REGRESSING' else 'NEUTRAL'
    row['form_v4_rating_line_count']=str(rct)
    return row

form, form_cols=read_csv(FORM); recs,_=read_csv(REC)
rec_by_key={(r['runner_key'],r['run_index']):r for r in recs}
shutil.copyfile(FORM, FORM.replace('.csv','_RATING_RECOVERY_BACKUP_20260628.csv'))
apply_rows=[]; applied=0
new=[]
for row in form:
    rk=row.get('runner_key','')
    before=rating_count(row)
    for i in range(1,6):
        rec=rec_by_key.get((rk,str(i)))
        if rec and blank(row.get(f'last_start_{i}_rating','')):
            row[f'last_start_{i}_rating']=rec['recovered_rating']
            row[f'last_start_{i}_source']=';'.join(sorted(set((row.get(f'last_start_{i}_source','')+';'+rec['recovery_source_bucket']).split(';'))-set([''])))
            reason=row.get(f'last_start_{i}_reason','')
            add=f"rating recovered from {rec['recovery_source_bucket']}:{rec['rating_column']}"
            row[f'last_start_{i}_reason']=(reason+' | '+add).strip(' |')
            applied+=1
            apply_rows.append({'runner_key':rk,'horse':row.get('horse',''),'run_index':i,'recovered_rating':rec['recovered_rating'],'recovery_source_bucket':rec['recovery_source_bucket'],'recovery_source_file':rec['recovery_source_file'],'recovery_confidence':rec['recovery_confidence']})
    row=recompute(row)
    new.append(row)
# write form with same/expanded cols
out_cols=list(form_cols)
for c in ['form_v4_rating_line_count']:
    if c not in out_cols: out_cols.append(c)
with open(FORM,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=out_cols); w.writeheader(); w.writerows([{c:r.get(c,'') for c in out_cols} for r in new])
# apply changed form fields to boards
form_by_key={key(r):r for r in new}
update_cols=[c for c in out_cols if c.startswith('form_') or c.startswith('last_start_') or c in {'rating_trend','rating_trend_delta','performance_intelligence_label','performance_intelligence_narrative'}]
board_results=[]
for board in BOARDS:
    rows, cols=read_csv(board)
    shutil.copyfile(board, board.replace('.csv','_RATING_RECOVERY_BACKUP_20260628.csv'))
    board_cols=list(cols)
    for c in update_cols:
        if c not in board_cols: board_cols.append(c)
    matched=0
    updated=[]
    for r in rows:
        fr=form_by_key.get(key(r))
        if fr:
            matched+=1
            for c in update_cols: r[c]=fr.get(c,'')
        updated.append({c:r.get(c,'') for c in board_cols})
    with open(board,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=board_cols); w.writeheader(); w.writerows(updated)
    board_results.append({'board':os.path.basename(board),'rows':len(updated),'matched_form_rows':matched})
with open(OUT,'w',newline='',encoding='utf-8') as f:
    fields=['runner_key','horse','run_index','recovered_rating','recovery_source_bucket','recovery_source_file','recovery_confidence']
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(apply_rows)
truth=collections.Counter(r.get('form_truth_status','') for r in new)
summary=[{'metric':'recovered_ratings_applied','value':applied},{'metric':'form_rows','value':len(new)}]
for k2,v in truth.items(): summary.append({'metric':f'truth_{k2}','value':v})
for b in board_results:
    summary.append({'metric':f"{b['board']}_rows",'value':b['rows']}); summary.append({'metric':f"{b['board']}_matched_form_rows",'value':b['matched_form_rows']})
summary += [{'metric':'pricing_maths_changed','value':'NO'},{'metric':'v6_1_changed','value':'NO'},{'metric':'v7_2g2_changed','value':'NO'}]
with open(SUM,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows(summary)
rep=['EDGEiQ HISTORICAL RATING RECOVERY APPLY V1',f'recovered_ratings_applied={applied}',f'truth_counts_after={dict(truth)}']
for b in board_results: rep.append(f"{b['board']}: rows={b['rows']} matched_form_rows={b['matched_form_rows']}")
rep += ['pricing_maths_changed=NO','v6_1_changed=NO','v7_2g2_changed=NO','status=HISTORICAL_RATING_RECOVERY_APPLIED']
with open(REP,'w',encoding='utf-8') as f: f.write('\n'.join(rep)+'\n')
print('\n'.join(rep))
