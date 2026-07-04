import csv, os, re, json
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
DATA=os.path.join(ROOT,'public','data')
OUT=os.path.join(DATA,'edgeiq_form_all_history_source_inventory_v1.csv')
REP=os.path.join(DATA,'edgeiq_form_all_history_source_inventory_v1_report.txt')
KEYWORDS=re.compile(r'(history|result|form|rating|warehouse|career)', re.I)

def safe_head(path, max_rows=5):
    try:
        with open(path,newline='',encoding='utf-8-sig',errors='replace') as f:
            r=csv.DictReader(f)
            rows=[]
            for i,row in enumerate(r):
                if i>=max_rows: break
                rows.append(row)
            return r.fieldnames or [], rows
    except Exception:
        return [], []

def count_rows(path):
    try:
        with open(path,newline='',encoding='utf-8-sig',errors='replace') as f:
            return max(0, sum(1 for _ in f)-1)
    except Exception:
        return 0

def cols_matching(cols, pats):
    out=[]
    for c in cols:
        lc=c.lower()
        if any(re.search(p,lc) for p in pats): out.append(c)
    return out

rows=[]
for name in sorted(os.listdir(DATA)):
    if not name.lower().endswith('.csv'): continue
    if not KEYWORDS.search(name): continue
    path=os.path.join(DATA,name)
    cols,sample=safe_head(path)
    if not cols: continue
    horse=cols_matching(cols,[r'(^|_)horse($|_)',r'runner.*name',r'runner_name'])
    date=cols_matching(cols,[r'date',r'race_date',r'meeting_date'])
    track=cols_matching(cols,[r'track',r'venue'])
    distance=cols_matching(cols,[r'distance',r'dist'])
    klass=cols_matching(cols,[r'class',r'grade'])
    condition=cols_matching(cols,[r'condition',r'going',r'track_rating'])
    finish=cols_matching(cols,[r'finish',r'position',r'pos($|_)',r'placing'])
    margin=cols_matching(cols,[r'margin',r'beaten'])
    rating=cols_matching(cols,[r'rating',r'figure',r'score'])
    sp=cols_matching(cols,[r'(^|_)sp($|_)',r'price',r'odds',r'starting'])
    usable=bool(horse and date and track and (finish or rating) and (distance or klass or condition or margin or sp or rating))
    rows.append({
        'file':name,'exists':'YES','rows':count_rows(path),'columns':'|'.join(cols),
        'horse_column_candidates':'|'.join(horse),'date_column_candidates':'|'.join(date),'track_column_candidates':'|'.join(track),
        'distance_columns':'|'.join(distance),'class_columns':'|'.join(klass),'condition_columns':'|'.join(condition),
        'finish_columns':'|'.join(finish),'margin_columns':'|'.join(margin),'rating_columns':'|'.join(rating),'sp_price_columns':'|'.join(sp),
        'usable_for_form':'YES' if usable else 'NO'
    })
with open(OUT,'w',newline='',encoding='utf-8') as f:
    fieldnames=['file','exists','rows','columns','horse_column_candidates','date_column_candidates','track_column_candidates','distance_columns','class_columns','condition_columns','finish_columns','margin_columns','rating_columns','sp_price_columns','usable_for_form']
    w=csv.DictWriter(f,fieldnames=fieldnames); w.writeheader(); w.writerows(rows)
usable=[r for r in rows if r['usable_for_form']=='YES']
preferred=['edgeiq_results_warehouse_full_v1.csv','edgeiq_historical_results_warehouse_full_v1.csv','edgeiq_historical_run_ratings_master_v1.csv','edgeiq_runner_history_detail_v1.csv','runner_form_history.csv','edgeiq_historical_performance_rating_v6_1_research.csv','form_card_runs.csv','form_card_runs_with_stewards.csv','full_career_form.csv','historical_form_table.csv','results_history.csv','results_history_clean.csv','master_result_events.csv']
report=['EDGEiQ FORM ALL HISTORY SOURCE INVENTORY V1',f'scanned_files={len(rows)}',f'usable_for_form={len(usable)}','preferred_candidates:']
for p in preferred:
    hit=next((r for r in rows if r['file']==p),None)
    if hit:
        report.append(f"- {p}: rows={hit['rows']} usable={hit['usable_for_form']} horse={hit['horse_column_candidates']} date={hit['date_column_candidates']} rating={hit['rating_columns']}")
report.append('largest_usable_sources:')
for r in sorted(usable,key=lambda x:int(x['rows'] or 0),reverse=True)[:20]:
    report.append(f"- {r['file']}: rows={r['rows']} horse={r['horse_column_candidates']} date={r['date_column_candidates']} track={r['track_column_candidates']}")
report += ['pricing_maths_changed=NO','v6_1_changed=NO','v7_2g2_changed=NO','status=FORM_HISTORY_SOURCE_INVENTORY_COMPLETE']
with open(REP,'w',encoding='utf-8') as f: f.write('\n'.join(report)+'\n')
print('\n'.join(report))
