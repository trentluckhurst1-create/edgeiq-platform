import csv, os, re
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
DATA=os.path.join(ROOT,'public','data')
FORM=os.path.join(DATA,'edgeiq_form_enrichment_feed_v4.csv')
OUT=os.path.join(DATA,'edgeiq_historical_rating_recovery_inventory_v1.csv')
REP=os.path.join(DATA,'edgeiq_historical_rating_recovery_inventory_v1_report.txt')

def read_head(path, n=3):
    try:
        with open(path,newline='',encoding='utf-8-sig',errors='replace') as f:
            r=csv.DictReader(f)
            rows=[]
            for i,row in enumerate(r):
                if i>=n: break
                rows.append(row)
            return r.fieldnames or [], rows
    except Exception:
        return [], []
def count_rows(path):
    try:
        with open(path,newline='',encoding='utf-8-sig',errors='replace') as f:
            return max(0,sum(1 for _ in f)-1)
    except Exception:
        return 0
def cols_matching(cols,pats):
    out=[]
    for c in cols:
        lc=c.lower()
        if any(re.search(p,lc) for p in pats): out.append(c)
    return out

def norm_horse(v):
    s=str(v or '').upper().replace('�','')
    s=re.sub(r'\([^)]*\)',' ',s)
    s=re.sub(r'\b\d+E\b',' ',s)
    return re.sub(r'[^A-Z0-9]+','',s)

def blank(v): return v is None or str(v).strip()=='' or str(v).strip().upper() in {'--','N/A','NA','NULL','NONE','UNKNOWN','NAN'}

def first(row,cols):
    for c in cols:
        v=row.get(c,'')
        if not blank(v): return str(v).strip()
    return ''

active=set()
with open(FORM,newline='',encoding='utf-8-sig',errors='replace') as f:
    for r in csv.DictReader(f):
        h=norm_horse(r.get('horse_key') or r.get('horse'))
        if h: active.add(h)

keyword=re.compile(r'(rating|projection|replay|archive|snapshot|runner|board|intelligence|history|form|result)',re.I)
rows=[]
for name in sorted(os.listdir(DATA)):
    if not name.lower().endswith('.csv'): continue
    if not keyword.search(name): continue
    path=os.path.join(DATA,name)
    cols,sample=read_head(path)
    if not cols: continue
    horse=cols_matching(cols,[r'(^|_)horse($|_)',r'horse_name',r'runner.*name',r'runner_name'])
    date=cols_matching(cols,[r'race_date',r'run_date',r'meeting_date',r'date_k',r'(^|_)date($|_)'])
    track=cols_matching(cols,[r'track',r'venue'])
    distance=cols_matching(cols,[r'distance',r'dist'])
    finish=cols_matching(cols,[r'finish',r'position',r'finish_pos',r'pos($|_)'])
    rating=cols_matching(cols,[r'rating',r'run_rating',r'performance_rating',r'projection',r'projected',r'total_rating_points',r'runner_score',r'figure'])
    if not (horse and date and rating):
        continue
    active_sample=0
    for s in sample:
        if norm_horse(first(s,horse)) in active: active_sample+=1
    lower=name.lower()
    if 'historical_run_ratings_master' in lower: priority=1
    elif 'historical_performance_rating' in lower: priority=2
    elif 'v5_1' in lower: priority=3
    elif 'v6_1' in lower: priority=4
    elif 'projection' in lower or 'projected' in lower: priority=5
    elif 'replay' in lower: priority=6
    elif 'runner_board' in lower or 'snapshot' in lower: priority=7
    elif 'intelligence' in lower: priority=8
    else: priority=9
    usable='YES' if horse and date and rating else 'NO'
    rows.append({'file':name,'rows':count_rows(path),'bytes':os.path.getsize(path),'priority':priority,'horse_columns':'|'.join(horse),'date_columns':'|'.join(date),'track_columns':'|'.join(track),'distance_columns':'|'.join(distance),'finish_columns':'|'.join(finish),'rating_columns':'|'.join(rating),'active_sample_matches':active_sample,'usable_for_recovery':usable})
rows.sort(key=lambda r:(int(r['priority']),-int(r['rows'])))
with open(OUT,'w',newline='',encoding='utf-8') as f:
    fields=['file','rows','bytes','priority','horse_columns','date_columns','track_columns','distance_columns','finish_columns','rating_columns','active_sample_matches','usable_for_recovery']
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
rep=['EDGEiQ HISTORICAL RATING RECOVERY INVENTORY V1',f'active_horses={len(active)}',f'candidate_rating_sources={len(rows)}','top_candidates:']
for r in rows[:30]:
    rep.append(f"- p{r['priority']} {r['file']}: rows={r['rows']} rating_cols={r['rating_columns']}")
rep += ['pricing_maths_changed=NO','v6_1_changed=NO','v7_2g2_changed=NO','status=HISTORICAL_RATING_RECOVERY_INVENTORY_COMPLETE']
with open(REP,'w',encoding='utf-8') as f: f.write('\n'.join(rep)+'\n')
print('\n'.join(rep))
