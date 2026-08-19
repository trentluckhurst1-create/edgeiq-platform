import csv, os, re, shutil
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
DATA=os.path.join(ROOT,'public','data')
FORM=os.path.join(DATA,'edgeiq_form_enrichment_feed_v4.csv')
BOARDS=[os.path.join(DATA,'edgeiq_live_runner_board_v1.csv'),os.path.join(DATA,'edgeiq_live_runner_board_governed_v1.csv')]
OUT=os.path.join(DATA,'edgeiq_form_display_clean_apply_v1.csv')
SUM=os.path.join(DATA,'edgeiq_form_display_clean_apply_v1_summary.csv')
REP=os.path.join(DATA,'edgeiq_form_display_clean_apply_v1_report.txt')

def read_csv(path):
    with open(path,newline='',encoding='utf-8-sig',errors='replace') as f:
        r=csv.DictReader(f); return list(r), r.fieldnames or []
def norm_horse(v):
    s=str(v or '').upper(); s=re.sub(r'\([^)]*\)',' ',s); s=re.sub(r'\b\d+E\b',' ',s); return re.sub(r'[^A-Z0-9]+','',s)
def clean_track(v): return re.sub(r'\s+',' ',str(v or '').upper().strip())
def norm_race(v): return str(v or '').upper().replace('R','').replace('.0','').strip()
def key(r):
    rk=str(r.get('runner_key','')).strip()
    if rk: return rk
    return '|'.join([str(r.get('race_date','')).strip(),clean_track(r.get('track','')),norm_race(r.get('race_no')),norm_horse(r.get('horse_key') or r.get('horse'))])
form, form_cols=read_csv(FORM)
form_by_key={key(r):r for r in form}
update_cols=[c for c in form_cols if c.startswith('form_') or c.startswith('last_start_') or c.endswith('_profile_display') or c in {'rating_trend','rating_trend_delta','performance_intelligence_label','performance_intelligence_narrative'}]
results=[]; summary=[]
for board in BOARDS:
    rows, cols=read_csv(board)
    backup=board.replace('.csv','_DISPLAY_CLEAN_BACKUP_20260628.csv')
    if not os.path.exists(backup): shutil.copyfile(board,backup)
    out_cols=list(cols)
    for c in update_cols:
        if c not in out_cols: out_cols.append(c)
    matched=0; missing=0; updated=[]
    for r in rows:
        f=form_by_key.get(key(r))
        if f:
            matched+=1
            for c in update_cols: r[c]=f.get(c,'')
        else:
            missing+=1
        updated.append({c:r.get(c,'') for c in out_cols})
    with open(board,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=out_cols); w.writeheader(); w.writerows(updated)
    races=len(set((r.get('race_date',''),r.get('track',''),r.get('race_no','')) for r in updated))
    rec={'board':os.path.basename(board),'rows':len(updated),'races':races,'matched_form_rows':matched,'missing_form_rows':missing,'backup':os.path.basename(backup),'pricing_maths_changed':'NO','v6_1_changed':'NO','v7_2g2_changed':'NO'}
    results.append(rec)
    for k,v in rec.items(): summary.append({'metric':f'{os.path.basename(board)}_{k}','value':v})
with open(OUT,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(results[0].keys())); w.writeheader(); w.writerows(results)
summary += [{'metric':'pricing_maths_changed','value':'NO'},{'metric':'v6_1_changed','value':'NO'},{'metric':'v7_2g2_changed','value':'NO'}]
with open(SUM,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows(summary)
rep=['EDGEiQ FORM DISPLAY CLEAN APPLY V1']
for r in results: rep.append(f"{r['board']}: rows={r['rows']} races={r['races']} matched_form_rows={r['matched_form_rows']} missing_form_rows={r['missing_form_rows']} backup={r['backup']}")
rep += ['pricing_maths_changed=NO','v6_1_changed=NO','v7_2g2_changed=NO','status=FORM_DISPLAY_CLEAN_APPLIED_TO_BOARDS']
with open(REP,'w',encoding='utf-8') as f: f.write('\n'.join(rep)+'\n')
print('\n'.join(rep))
