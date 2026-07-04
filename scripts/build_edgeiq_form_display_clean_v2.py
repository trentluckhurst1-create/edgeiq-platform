import csv, os, re, shutil, collections
from datetime import datetime
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
DATA=os.path.join(ROOT,'public','data')
FORM=os.path.join(DATA,'edgeiq_form_enrichment_feed_v4.csv')
OUT=os.path.join(DATA,'edgeiq_form_display_clean_v2.csv')
SUM=os.path.join(DATA,'edgeiq_form_display_clean_v2_summary.csv')
REP=os.path.join(DATA,'edgeiq_form_display_clean_v2_report.txt')
BACKUP=os.path.join(DATA,'edgeiq_form_enrichment_feed_v4_DISPLAY_CLEAN_V2_BACKUP_20260628.csv')
DASH='—'
BAD={'','--','-','—','N/A','NA','NULL','NONE','UNKNOWN','NAN','NOT LOADED','SOURCE GAP','UNDEFINED','NO_CLASS','0.0','0'}
SOURCES=[
 ('RESULTS_WAREHOUSE','edgeiq_historical_results_warehouse_v2_graphql.csv',{'horse':['horse','horse_code'],'date':['race_date'],'track':['track','venue_name'],'distance':['distance'],'class':['race_class'],'condition':['track_condition','track_rating'],'position':['finish_num','finish'],'margin':['margin_l','margin'],'sp':['starting_price_decimal','starting_price'],'rating':[],'comment':['comment_short','comment','comment_stewards']}),
 ('HISTORICAL_FORM_TABLE','historical_form_table.csv',{'horse':['horse'],'date':['race_date'],'track':['track'],'distance':['distance'],'class':[],'condition':['track_condition'],'position':['finish_pos'],'margin':['margin'],'sp':['sp'],'rating':['run_rating','race_rating'],'comment':[]}),
 ('HISTORY_MASTER','edgeiq_historical_run_ratings_master_v1.csv',{'horse':['horse','horse_key'],'date':['race_date'],'track':['track'],'distance':['distance'],'class':['class_name'],'condition':['condition'],'position':['finish_pos'],'margin':['margin'],'sp':['sp'],'rating':['performance_rating'],'comment':['rating_method','rating_band']}),
 ('REPLAY_ARCHIVE','edgeiq_v6_1_settled_gap_replay_v2_expanded.csv',{'horse':['horse','horse_key'],'date':['race_date'],'track':['track'],'distance':['distance'],'class':['class_name','race_class'],'condition':['condition','track_condition'],'position':['finish_pos','finish_position'],'margin':['margin'],'sp':['sp','market_price'],'rating':['projected_rating_V6_1_RESEARCH','performance_rating','run_rating'],'comment':['projection_band_V6_1_RESEARCH']}),
 ('RUNNER_BOARD_SNAPSHOT','edgeiq_archived_probability_rating_candidates_v1.csv',{'horse':['horse','horse_key'],'date':['race_date'],'track':['track'],'distance':['distance'],'class':['race_class','class'],'condition':['condition','track_condition'],'position':['finish_pos','finish_position'],'margin':['margin'],'sp':['sp','market_price'],'rating':['rating','production_rating','total_rating_points'],'comment':['source_file','rating_source']}),
 ('V6_1_RESEARCH_ARCHIVE','edgeiq_historical_performance_rating_v6_1_research.csv',{'horse':['horse'],'date':['race_date'],'track':['track'],'distance':['distance'],'class':['race_class_clean','race_class_clean_v3_3','race_class_recovered','race_class_raw'],'condition':['condition_recovered','condition_token_recovered'],'position':['finish_position','finish_pos_raw'],'margin':['margin','margin_raw'],'sp':[],'rating':['performance_rating_v6_1_research','performance_rating_v5_1','performance_rating_v3'],'comment':['performance_rating_v6_1_research_reason','performance_reason_v3']}),
]

def read_csv(path):
    with open(path,newline='',encoding='utf-8-sig',errors='replace') as f:
        r=csv.DictReader(f); return list(r), r.fieldnames or []
def blank(v): return str(v or '').strip().upper() in BAD
def norm_horse(v):
    s=str(v or '').upper().replace('�','')
    s=re.sub(r'\([^)]*\)',' ',s); s=re.sub(r'\b\d+E\b',' ',s)
    return re.sub(r'[^A-Z0-9]+','',s)
def clean_date(v):
    s=str(v or '').strip()[:10]
    try: return datetime.fromisoformat(s).date().isoformat()
    except Exception: return ''
def clean_track(v): return re.sub(r'\s+',' ',str(v or '').upper().strip())
def num(v):
    try:
        if blank(v): return None
        m=re.search(r'-?\d+(?:\.\d+)?',str(v))
        return float(m.group(0)) if m else None
    except Exception: return None
def clean_distance(v):
    x=num(v)
    if x is None or x<=0: return ''
    return str(int(round(x)))
def first(row,cols):
    for c in cols:
        v=row.get(c,'')
        if not blank(v): return str(v).strip()
    return ''
def source_label(src):
    return {'RESULTS_WAREHOUSE':'Results Warehouse','HISTORICAL_FORM_TABLE':'Historical Form','HISTORY_MASTER':'History Master','REPLAY_ARCHIVE':'Replay Archive','RUNNER_BOARD_SNAPSHOT':'Board Snapshot','V6_1_RESEARCH_ARCHIVE':'V6.1 Rated History','INTELLIGENCE_SNAPSHOT':'Intelligence Snapshot'}.get(src,'Historical Evidence')
def pos_display(v):
    x=num(v)
    if x is None or x<=0 or x>30: return DASH,False
    return str(int(x)),True
def sp_display(v):
    x=num(v)
    if x is None or x<=1.0: return DASH,False
    return f'{x:.2f}'.rstrip('0').rstrip('.'),True
def margin_display(pos, m):
    x=num(m); p=num(pos)
    if x is None: return DASH,False
    if p==1: return ('Won by '+(f'{x:.2f}L' if x<0.1 and x>0 else f'{x:.1f}L')) if x>0 else 'Won', True
    return (('Beaten '+(f'{x:.2f}L' if x<0.1 else f'{x:.1f}L')), True) if x>0 else (DASH,False)
def class_display(v):
    if blank(v): return DASH,False
    s=str(v).strip()
    if s.upper() in {'NO_CLASS','UNKNOWN','NOT LOADED'}: return DASH,False
    return s,True
def condition_display(v):
    if blank(v): return DASH,False
    s=str(v).strip().upper()
    if s in {'0','0.0','UNKNOWN','NOT LOADED'}: return DASH,False
    return re.sub(r'\s+','',s),True
def distance_display(v):
    d=clean_distance(v)
    return (f'{d}m',True) if d else (DASH,False)
def rating_display(v):
    x=num(v)
    if x is None or x < 15 or x > 110: return DASH,False
    return f'{x:.1f}',True
def customer_source(raw, fallback=''):
    text=str(raw or '').upper()
    labels=[]
    def add(x):
        if x not in labels: labels.append(x)
    for part in re.split(r'[;|]',text):
        p=part.strip()
        if not p: continue
        if 'RESULTS_WAREHOUSE' in p: add('Results Warehouse')
        elif 'HISTORICAL_FORM' in p: add('Historical Form')
        elif 'HISTORY_MASTER' in p or 'HISTORICAL_RATING' in p: add('History Master')
        elif 'REPLAY' in p: add('Replay Archive')
        elif 'RUNNER_BOARD' in p or 'BOARD' in p: add('Board Snapshot')
        elif 'V6_1' in p or 'V6.1' in p: add('V6.1 Rated History')
        elif 'RECOVER' in p or 'OTHER_RATING_SOURCE' in p or 'RATING_DATE_MATCH' in p: add('Recovered Rating')
        elif 'INTELLIGENCE' in p: add('Intelligence Snapshot')
        elif 'RESULT' in p: add('Results Warehouse')
    if fallback: add(fallback)
    return ' + '.join(labels[:2]) if labels else DASH

def run_key(h,d): return (h,d)
form, cols=read_csv(FORM)
active=set(); target_dates=set()
for r in form:
    h=norm_horse(r.get('horse_key') or r.get('horse'))
    if h: active.add(h)
    for i in range(1,6):
        d=clean_date(r.get(f'last_start_{i}_date'))
        if d: target_dates.add(d)
lookup=collections.defaultdict(list)
for src,file,mapc in SOURCES:
    path=os.path.join(DATA,file)
    if not os.path.exists(path): continue
    with open(path,newline='',encoding='utf-8-sig',errors='replace') as f:
        reader=csv.DictReader(f)
        for row in reader:
            h=norm_horse(first(row,mapc['horse']))
            if h not in active: continue
            d=clean_date(first(row,mapc['date']))
            if d not in target_dates: continue
            rec={'src':src,'track':clean_track(first(row,mapc.get('track',[]))),'distance':clean_distance(first(row,mapc.get('distance',[]))),'class':first(row,mapc.get('class',[])),'condition':first(row,mapc.get('condition',[])),'position':first(row,mapc.get('position',[])),'margin':first(row,mapc.get('margin',[])),'sp':first(row,mapc.get('sp',[])),'rating':first(row,mapc.get('rating',[])),'comment':first(row,mapc.get('comment',[]))}
            lookup[run_key(h,d)].append(rec)

def best_recover(h,date,track,dist,field):
    candidates=lookup.get(run_key(h,date),[])
    best=None; score=-999
    for c in candidates:
        val=c.get(field,'')
        if blank(val): continue
        sc=0
        if c.get('track') and track and c['track']==track: sc+=5
        if c.get('distance') and dist and c['distance']==dist: sc+=5
        sc += {'RESULTS_WAREHOUSE':60,'HISTORICAL_FORM_TABLE':50,'HISTORY_MASTER':45,'REPLAY_ARCHIVE':35,'RUNNER_BOARD_SNAPSHOT':30,'V6_1_RESEARCH_ARCHIVE':25}.get(c['src'],10)
        if sc>score: best=c; score=sc
    return best

def clean_status(s):
    raw=str(s or '').upper().replace('_',' ')
    if 'OK' in raw: return 'OK HISTORY'
    if 'PARTIAL' in raw: return 'PARTIAL HISTORY'
    if 'CONTEXT' in raw: return 'CONTEXT ONLY'
    return 'SOURCE GAP'
def clean_trend(*vals):
    raw=' '.join(str(v or '').upper().replace('_',' ') for v in vals)
    if 'IMPROV' in raw or 'PEAK' in raw: return 'IMPROVING'
    if 'REGRESS' in raw or 'DECLIN' in raw: return 'REGRESSING'
    if 'LIMITED' in raw: return 'LIMITED'
    if 'CONTEXT' in raw: return 'CONTEXT ONLY'
    if 'PARTIAL' in raw: return 'PARTIAL EVIDENCE'
    return 'HOLDING FORM'
def score_band(v):
    x=num(v)
    if x is None: return DASH,'LIMITED'
    return f'{x:.0f}', 'ELITE' if x>=85 else 'STRONG' if x>=75 else 'AVERAGE' if x>=60 else 'RISK' if x>=45 else 'POOR'

rows=[]; counts=collections.Counter(); coverage=collections.Counter(); totals=collections.Counter()
for r in form:
    h=norm_horse(r.get('horse_key') or r.get('horse'))
    score,band=score_band(r.get('form_peak_rating_last5') or r.get('form_avg_rating_last5') or r.get('form_last_start_rating'))
    r['form_status_display_v2']=clean_status(r.get('form_truth_status'))
    r['form_trend_display_v2']=clean_trend(r.get('form_trend'),r.get('form_signal'),r.get('form_data_quality'))
    r['form_data_quality_display_v2']=clean_status(r.get('form_truth_status')) if 'CONTEXT' in clean_status(r.get('form_truth_status')) else (r.get('form_data_quality_display') or r.get('form_data_quality') or clean_status(r.get('form_truth_status'))).replace('_',' ').upper()
    r['form_score_display_v2']=score; r['form_score_band_display_v2']=band
    r['form_evidence_display_v2']='HIGH' if r['form_status_display_v2']=='OK HISTORY' else 'MEDIUM' if r['form_status_display_v2']=='PARTIAL HISTORY' else 'LOW'
    for profile in ['distance','condition','class']:
        raw=r.get(f'{profile}_profile_display') or ''
        if raw and 'score 0' not in raw.lower() and 'risk' not in raw.lower(): r[f'{profile}_profile_display_v2']=raw.replace('UNKNOWN',DASH).replace('Not Enough Evidence','Not Enough Evidence')
        else: r[f'{profile}_profile_display_v2']='Not Enough Evidence'
    for i in range(1,6):
        p=f'last_start_{i}_'
        date=clean_date(r.get(p+'date'))
        track=clean_track(r.get(p+'track'))
        dist_raw=clean_distance(r.get(p+'distance'))
        # Recover field values if display/raw invalid.
        recovered_src=[]
        base={
          'position':r.get(p+'position_display') or r.get(p+'finish') or r.get(p+'finishing_position'),
          'sp':r.get(p+'sp_display') or r.get(p+'sp') or r.get(p+'SP'),
          'margin':r.get(p+'margin_display') or r.get(p+'margin') or r.get(p+'beaten_margin'),
          'class':r.get(p+'class_display') or r.get(p+'class'),
          'condition':r.get(p+'condition_display') or r.get(p+'condition'),
          'distance':r.get(p+'distance_display') or r.get(p+'distance'),
          'rating':r.get(p+'rating_display') or r.get(p+'rating'),
          'comment':r.get(p+'comment_display') or r.get(p+'source') or r.get(p+'reason'),
        }
        rating_hidden = str(r.get(p+'rating_outlier_status','')).upper() == 'UNRELIABLE_RATING_HIDDEN'
        for fld in ['position','sp','margin','class','condition','distance','rating']:
            display_func={'position':pos_display,'sp':sp_display,'class':class_display,'condition':condition_display,'distance':distance_display,'rating':rating_display}.get(fld)
            ok=False
            if fld=='rating' and rating_hidden:
                val,ok=DASH,False
            elif fld=='margin':
                val,ok=margin_display(base['position'],base['margin'])
            else:
                val,ok=display_func(base[fld])
            if not ok and date and not (fld=='rating' and rating_hidden):
                rec=best_recover(h,date,track,dist_raw,fld)
                if rec:
                    if fld=='margin': val,ok=margin_display(rec.get('position') or base['position'],rec.get('margin'))
                    else: val,ok=display_func(rec.get(fld))
                    if ok: recovered_src.append(source_label(rec['src']))
            r[p+fld+'_display_v2']=val
            totals[fld]+=1
            if val!=DASH: coverage[fld]+=1
            else: counts[f'{fld.upper()}_DASH_DISPLAY']+=1
        if str(r.get(p+'rating_outlier_status','')).upper() == 'UNRELIABLE_RATING_HIDDEN':
            comment='Rating not reliable'
        else:
            comment=customer_source(base['comment'], recovered_src[0] if recovered_src else '')
        r[p+'comment_display_v2']=comment
        totals['comment']+=1
        if comment!=DASH: coverage['comment']+=1
        else: counts['COMMENT_DASH_DISPLAY']+=1
    rows.append(r)
new_cols=list(cols)
for c in rows[0].keys():
    if c not in new_cols: new_cols.append(c)
with open(OUT,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=new_cols); w.writeheader(); w.writerows([{c:r.get(c,'') for c in new_cols} for r in rows])
# Update FORM feed in place with backup.
backup=os.path.join(DATA,'edgeiq_form_enrichment_feed_v4_DISPLAY_CLEAN_V2_BACKUP_20260628.csv')
if not os.path.exists(backup): shutil.copyfile(FORM,backup)
with open(FORM,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=new_cols); w.writeheader(); w.writerows([{c:r.get(c,'') for c in new_cols} for r in rows])
summary=[{'metric':'rows','value':len(rows)}]
for fld in ['position','sp','condition','class','distance','margin','rating','comment']:
    summary.append({'metric':f'{fld}_coverage','value':coverage[fld]})
    summary.append({'metric':f'{fld}_total','value':totals[fld]})
    summary.append({'metric':f'{fld}_coverage_pct','value':f'{coverage[fld]/max(1,totals[fld])*100:.2f}'})
for k,v in counts.most_common(): summary.append({'metric':k,'value':v})
summary += [{'metric':'pricing_maths_changed','value':'NO'},{'metric':'v6_1_changed','value':'NO'},{'metric':'v7_2g2_changed','value':'NO'}]
with open(SUM,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows(summary)
rep=['EDGEiQ FORM DISPLAY CLEAN V2']+[f"{x['metric']}={x['value']}" for x in summary]+['status=FORM_DISPLAY_CLEAN_V2_BUILT']
with open(REP,'w',encoding='utf-8') as f: f.write('\n'.join(rep)+'\n')
print('\n'.join(rep))
