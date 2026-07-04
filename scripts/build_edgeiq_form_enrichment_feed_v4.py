import csv, os, re, shutil, collections
from datetime import datetime
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
DATA=os.path.join(ROOT,'public','data')
GOV=os.path.join(DATA,'edgeiq_live_runner_board_governed_v1.csv')
V3=os.path.join(DATA,'edgeiq_form_enrichment_feed_v3.csv')
OUT=os.path.join(DATA,'edgeiq_form_enrichment_feed_v4.csv')
SUM=os.path.join(DATA,'edgeiq_form_enrichment_feed_v4_summary.csv')
AUD=os.path.join(DATA,'edgeiq_form_enrichment_feed_v4_audit.csv')
REP=os.path.join(DATA,'edgeiq_form_enrichment_feed_v4_report.txt')
SOURCES=[
 ('RESULTS_WAREHOUSE','edgeiq_historical_results_warehouse_v2_graphql.csv',1,{'horse':['horse','horse_code'],'date':['race_date'],'track':['track','venue_name'],'distance':['distance'],'class':['race_class'],'condition':['track_condition','track_rating'],'finish':['finish_num','finish'],'margin':['margin_l','margin'],'rating':[],'sp':['starting_price_decimal','starting_price'],'comment':['comment_short','comment','comment_stewards']}),
 ('HISTORY_DETAIL','edgeiq_runner_history_detail_v1.csv',2,{'horse':['horse','horse_key','recovery_horse','recovery_horse_key'],'date':['race_date','run_date_iso','recovery_race_date'],'track':['track','recovery_track'],'distance':['distance','recovery_distance'],'class':['class_name','recovery_class_name'],'condition':['condition','recovery_condition'],'finish':['finish_pos','recovery_finish_pos'],'margin':['margin','recovery_margin'],'rating':['run_rating_final','recovered_rating','recovery_recovered_rating','performance_rating'],'sp':['sp','recovery_sp'],'comment':['rating_source','source_confidence','recovery_source_confidence']}),
 ('HISTORY_MASTER','edgeiq_historical_run_ratings_master_v1.csv',3,{'horse':['horse','horse_key'],'date':['race_date'],'track':['track'],'distance':['distance'],'class':['class_name'],'condition':['condition'],'finish':['finish_pos'],'margin':['margin'],'rating':['performance_rating'],'sp':['sp'],'comment':['rating_method','rating_band']}),
 ('RUNNER_FORM_HISTORY','runner_form_history.csv',4,{'horse':['horse','horse_key'],'date':['run_date_iso','run_date'],'track':['track'],'distance':['distance'],'class':['class_name'],'condition':[],'finish':['finish_pos'],'margin':['margin'],'rating':['run_rating'],'sp':['sp'],'comment':['history_status']}),
 ('V6_1_RESEARCH_HISTORY','edgeiq_historical_performance_rating_v6_1_research.csv',5,{'horse':['horse'],'date':['race_date'],'track':['track'],'distance':['distance'],'class':['race_class_clean','race_class_clean_v3_3','race_class_recovered','race_class_raw'],'condition':['condition_recovered','condition_token_recovered'],'finish':['finish_position','finish_pos_raw'],'margin':['margin','margin_raw'],'rating':['performance_rating_v6_1_research','performance_rating_v5_1','performance_rating_v3'],'sp':[],'comment':['performance_rating_v6_1_research_reason','performance_reason_v3']}),
 ('FORM_CARD_STEWARDS','form_card_runs_with_stewards.csv',6,{'horse':['horse','horse_key','horse_soft'],'date':['run_date'],'track':['track'],'distance':['distance'],'class':['race_class'],'condition':['track_condition'],'finish':['finish_pos'],'margin':['margin'],'rating':['run_rating'],'sp':['starting_price','sp_text'],'comment':['stewards_short','comment']}),
 ('FULL_CAREER_FORM','full_career_form.csv',7,{'horse':['horse','horse_key'],'date':['run_date'],'track':['track'],'distance':['distance'],'class':['race_class'],'condition':['track_condition'],'finish':['finish_pos'],'margin':['margin'],'rating':['run_rating','rating_display'],'sp':['starting_price','sp_text'],'comment':['run_type']}),
 ('HISTORICAL_FORM_TABLE','historical_form_table.csv',8,{'horse':['horse'],'date':['race_date'],'track':['track'],'distance':['distance'],'class':[],'condition':['track_condition'],'finish':['finish_pos'],'margin':['margin'],'rating':['run_rating','race_rating'],'sp':['sp'],'comment':[]}),
]

def read_csv(path):
    with open(path,newline='',encoding='utf-8-sig',errors='replace') as f:
        r=csv.DictReader(f); return list(r), r.fieldnames or []
def norm_horse(v):
    s=str(v or '').upper().replace('�','')
    s=re.sub(r'\([^)]*\)',' ',s)
    s=re.sub(r'\b\d+E\b',' ',s)
    return re.sub(r'[^A-Z0-9]+','',s)
def clean_track(v): return re.sub(r'\s+',' ',str(v or '').upper().strip())
def norm_race(v): return str(v or '').upper().replace('R','').replace('.0','').strip()
def runner_key(row):
    rk=str(row.get('runner_key','')).strip()
    if rk: return rk
    return '|'.join([str(row.get('race_date','')).strip(),clean_track(row.get('track','')),norm_race(row.get('race_no')),norm_horse(row.get('horse_key') or row.get('horse'))])
def blank(v): return v is None or str(v).strip()=='' or str(v).strip().upper() in {'--','N/A','NA','NULL','NONE','UNKNOWN','NAN'}
def first(row, cols):
    for c in cols:
        v=row.get(c,'')
        if not blank(v): return str(v).strip()
    return ''
def date_val(v):
    s=str(v or '').strip()[:10]
    try: return datetime.fromisoformat(s)
    except Exception: return datetime.min
def clean_date(v):
    d=date_val(v)
    return d.date().isoformat() if d != datetime.min else ''
def clean_distance(v):
    s=str(v or '').strip()
    if blank(s): return ''
    m=re.search(r'\d+(?:\.\d+)?',s)
    if not m: return s
    x=float(m.group(0))
    return str(int(x)) if abs(x-round(x))<0.001 else f'{x:.0f}'
def clean_finish(v):
    s=str(v or '').strip()
    if blank(s): return ''
    m=re.search(r'\d+',s)
    return m.group(0) if m else s
def clean_margin(v):
    s=str(v or '').strip()
    if blank(s): return ''
    m=re.search(r'-?\d+(?:\.\d+)?',s)
    return m.group(0) if m else s
def clean_price(v):
    s=str(v or '').strip()
    if blank(s): return ''
    m=re.search(r'\d+(?:\.\d+)?',s.replace('$',''))
    return m.group(0) if m else s
def clean_rating(v):
    s=str(v or '').strip()
    if blank(s): return ''
    try: return f'{float(s):.1f}'
    except Exception: return ''
def condition_from(row, cols):
    vals=[str(row.get(c,'')).strip() for c in cols if not blank(row.get(c,''))]
    if not vals: return ''
    if len(vals)>=2 and re.fullmatch(r'\d+(?:\.0)?', vals[1]): return f'{vals[0]} {int(float(vals[1]))}'
    return vals[0]
def run_key(run):
    return '|'.join([run.get('date',''),clean_track(run.get('track','')),clean_distance(run.get('distance','')),clean_finish(run.get('finish',''))])
def merge_run(a,b):
    # lower priority number wins for source ordering, but fields fill from any nonblank source
    for field in ['date','track','distance','class','condition','finish','margin','rating','sp','comment']:
        if blank(a.get(field,'')) and not blank(b.get(field,'')): a[field]=b.get(field,'')
    if blank(a.get('rating','')) and not blank(b.get('rating','')): a['rating']=b['rating']
    sources=set((a.get('source','')+';'+b.get('source','')).split(';'))
    a['source']=';'.join(sorted(x for x in sources if x))
    a['priority']=min(int(a.get('priority',99)), int(b.get('priority',99)))
    return a

gov, gov_cols=read_csv(GOV)
v3, v3_cols=read_csv(V3)
v3_by_key={runner_key(r):r for r in v3}
active_keys={norm_horse(r.get('horse_key') or r.get('horse')) for r in gov}; active_keys.discard('')
all_runs=collections.defaultdict(dict)
source_counts=collections.Counter()
for src,file,priority,mapcols in SOURCES:
    path=os.path.join(DATA,file)
    if not os.path.exists(path): continue
    with open(path,newline='',encoding='utf-8-sig',errors='replace') as f:
        reader=csv.DictReader(f)
        for row in reader:
            h=norm_horse(first(row,mapcols['horse']))
            if not h or h not in active_keys: continue
            dt=clean_date(first(row,mapcols['date']))
            if not dt: continue
            run={
                'date':dt,
                'track':first(row,mapcols['track']),
                'distance':clean_distance(first(row,mapcols['distance'])),
                'class':first(row,mapcols['class']),
                'condition':condition_from(row,mapcols['condition']),
                'finish':clean_finish(first(row,mapcols['finish'])),
                'margin':clean_margin(first(row,mapcols['margin'])),
                'rating':clean_rating(first(row,mapcols['rating'])),
                'sp':clean_price(first(row,mapcols['sp'])),
                'comment':first(row,mapcols['comment']),
                'source':src,
                'priority':priority,
            }
            if not (run['track'] or run['finish'] or run['distance'] or run['rating']): continue
            k=run_key(run)
            if not k: continue
            if k in all_runs[h]: all_runs[h][k]=merge_run(all_runs[h][k],run)
            else: all_runs[h][k]=run
            source_counts[src]+=1

base_cols=[]
for c in gov_cols + v3_cols:
    if c not in base_cols: base_cols.append(c)
extra=[]
for n in range(1,6):
    extra += [f'last_start_{n}_date',f'last_start_{n}_track',f'last_start_{n}_distance',f'last_start_{n}_class',f'last_start_{n}_condition',f'last_start_{n}_finish',f'last_start_{n}_margin',f'last_start_{n}_rating',f'last_start_{n}_sp',f'last_start_{n}_SP',f'last_start_{n}_reason',f'last_start_{n}_source',f'last_start_{n}_finishing_position',f'last_start_{n}_beaten_margin',f'last_start_{n}_performance_label']
extra += ['form_truth_status','form_source','form_data_quality','form_missing_fields_count','form_history_starts','form_history_wins','form_history_places','form_last_start_rating','form_previous_start_rating','form_rating_delta_last_start','form_avg_rating_last5','form_peak_rating_last5','form_trend','rating_trend','rating_trend_delta','form_signal','form_cycle','performance_intelligence_label','performance_intelligence_narrative','form_v4_run_line_count','form_v4_rating_line_count','form_v4_improved_vs_v3']
cols=[]
for c in base_cols+extra:
    if c not in cols: cols.append(c)

out=[]; audit=[]; truth=collections.Counter(); improved=0; run_line_counts=[]
for g in gov:
    k=runner_key(g); h=norm_horse(g.get('horse_key') or g.get('horse'))
    row={c:g.get(c,'') for c in gov_cols}
    old=v3_by_key.get(k,{})
    for c in v3_cols:
        row.setdefault(c, old.get(c,''))
    row['runner_key']=k
    current_date=date_val(g.get('race_date'))
    runs=[r for r in all_runs.get(h,{}).values() if date_val(r['date']) < current_date]
    runs.sort(key=lambda r: date_val(r['date']), reverse=True)
    rating_by_date={}
    for rr in runs:
        if not blank(rr.get('rating','')) and rr.get('date') not in rating_by_date:
            rating_by_date[rr.get('date')] = rr
    recent=runs[:5]
    for rr in recent:
        if blank(rr.get('rating','')) and rr.get('date') in rating_by_date:
            rated=rating_by_date[rr.get('date')]
            rr['rating']=rated.get('rating','')
            if blank(rr.get('comment','')): rr['comment']=rated.get('comment','')
            rr['source']=';'.join(sorted(set((rr.get('source','')+';'+rated.get('source','')+';RATING_DATE_MATCH').split(';'))-set([''])))
    rating_runs=[r for r in recent if not blank(r.get('rating',''))]
    all_rating_runs=[r for r in runs if not blank(r.get('rating',''))]
    for idx in range(1,6):
        p=f'last_start_{idx}_'
        if idx <= len(recent):
            r=recent[idx-1]
            row[p+'date']=r.get('date',''); row[p+'track']=r.get('track',''); row[p+'distance']=r.get('distance',''); row[p+'class']=r.get('class',''); row[p+'condition']=r.get('condition','')
            row[p+'finish']=r.get('finish',''); row[p+'finishing_position']=r.get('finish',''); row[p+'margin']=r.get('margin',''); row[p+'beaten_margin']=r.get('margin','')
            row[p+'rating']=r.get('rating',''); row[p+'sp']=r.get('sp',''); row[p+'SP']=r.get('sp',''); row[p+'reason']=r.get('comment',''); row[p+'source']=r.get('source','')
            row[p+'performance_label']='RATED_HISTORY' if r.get('rating') else 'RESULT_HISTORY'
        else:
            for suffix in ['date','track','distance','class','condition','finish','finishing_position','margin','beaten_margin','rating','sp','SP','reason','source','performance_label']:
                row[p+suffix]=''
    if runs:
        source_set=set()
        for r in recent: source_set.update(x for x in r.get('source','').split(';') if x)
        if len(source_set)>1: source='MIXED_HISTORY'
        elif source_set: source=next(iter(source_set))
        else: source='RESULTS_WAREHOUSE'
        if len(recent)>=3 and len(rating_runs)>=3: status='OK_HISTORY'; quality='FULL HISTORY'
        else: status='PARTIAL_HISTORY'; quality='PARTIAL HISTORY'
    else:
        status='CONTEXT_ONLY' if old.get('form_truth_status') or row.get('form_trend') else 'SOURCE_GAP'
        quality='CONTEXT ONLY' if status=='CONTEXT_ONLY' else 'SOURCE GAP'
        source='TRAJECTORY_CONTEXT_ONLY' if status=='CONTEXT_ONLY' else 'SOURCE_GAP'
    row['form_truth_status']=status; row['form_source']=source; row['form_data_quality']=quality
    row['form_history_starts']=str(len(runs)) if runs else '0'
    wins=sum(1 for r in runs if clean_finish(r.get('finish'))=='1')
    places=sum(1 for r in runs if (clean_finish(r.get('finish')).isdigit() and int(clean_finish(r.get('finish')))<=3))
    row['form_history_wins']=str(wins); row['form_history_places']=str(places)
    if rating_runs:
        ratings=[float(r['rating']) for r in rating_runs]
        row['form_last_start_rating']=f'{ratings[0]:.1f}'
        if len(ratings)>1: row['form_previous_start_rating']=f'{ratings[1]:.1f}'; row['form_rating_delta_last_start']=f'{ratings[0]-ratings[1]:.1f}'
        else: row['form_previous_start_rating']=''; row['form_rating_delta_last_start']=''
        row['form_avg_rating_last5']=f'{sum(ratings)/len(ratings):.1f}'
        row['form_peak_rating_last5']=f'{max(ratings):.1f}'
        delta=ratings[0]-ratings[1] if len(ratings)>1 else None
        trend='IMPROVING' if delta is not None and delta>=3 else 'REGRESSING' if delta is not None and delta<=-3 else 'HOLDING' if delta is not None else 'LIMITED FORM'
    else:
        row['form_last_start_rating']=''; row['form_previous_start_rating']=''; row['form_rating_delta_last_start']=''; row['form_avg_rating_last5']=''; row['form_peak_rating_last5']=''; trend='LIMITED FORM' if runs else 'CONTEXT ONLY'
    row['form_trend']=trend; row['rating_trend']=trend; row['rating_trend_delta']=row.get('form_rating_delta_last_start',''); row['form_cycle']=trend
    row['form_signal']='RECENT FORM LOADED' if status=='OK_HISTORY' else 'PARTIAL FORM LOADED' if status=='PARTIAL_HISTORY' else 'CONTEXT ONLY' if status=='CONTEXT_ONLY' else 'SOURCE GAP'
    row['performance_intelligence_label']='IMPROVING' if trend=='IMPROVING' else 'BELOW EXPECTATIONS' if trend=='REGRESSING' else 'NEUTRAL'
    row['performance_intelligence_narrative']=f'{len(recent)} recent run line(s) loaded from {source}.' if runs else 'Context only - no detailed rated-history lines available.'
    missing=0
    for idx in range(1,min(5,len(recent))+1):
        for fld in ['date','track','distance','class','condition','finish','margin','rating','sp']:
            if blank(row.get(f'last_start_{idx}_{fld}','')): missing+=1
    row['form_missing_fields_count']=str(missing)
    row['form_v4_run_line_count']=str(len(recent)); row['form_v4_rating_line_count']=str(len(rating_runs))
    v3_count=sum(1 for i in range(1,6) if not blank(old.get(f'last_start_{i}_date','')) or not blank(old.get(f'last_start_{i}_rating','')))
    is_improved=len(recent)>v3_count
    if is_improved: improved+=1
    row['form_v4_improved_vs_v3']='YES' if is_improved else 'NO'
    out.append({c:row.get(c,'') for c in cols})
    truth[status]+=1; run_line_counts.append(len(recent) if status in {'OK_HISTORY','PARTIAL_HISTORY'} else 0)
    audit.append({'race_date':g.get('race_date',''),'track':g.get('track',''),'race_no':g.get('race_no',''),'horse':g.get('horse',''),'runner_key':k,'form_truth_status':status,'form_source':source,'form_data_quality':quality,'v4_run_lines':len(recent),'v4_rating_lines':len(rating_runs),'v4_improved_vs_v3':'YES' if is_improved else 'NO','last_start_1_date':row.get('last_start_1_date',''),'last_start_1_class':row.get('last_start_1_class',''),'last_start_1_distance':row.get('last_start_1_distance',''),'last_start_1_condition':row.get('last_start_1_condition',''),'last_start_1_rating':row.get('last_start_1_rating','')})
with open(OUT,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(out)
with open(AUD,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(audit[0].keys())); w.writeheader(); w.writerows(audit)
races=len(set((r.get('race_date',''),r.get('track',''),r.get('race_no','')) for r in out))
avg=sum(run_line_counts)/max(1,sum(1 for x in run_line_counts if x>0))
summary=[{'metric':'rows','value':len(out)},{'metric':'races','value':races},{'metric':'runner_key_populated','value':sum(1 for r in out if r.get('runner_key'))},{'metric':'duplicate_runner_keys','value':len(out)-len(set(r.get('runner_key') for r in out))}]
for k2,v in truth.items(): summary.append({'metric':f'truth_{k2}','value':v})
for fld in ['last_start_1_date','last_start_1_rating','last_start_1_class','last_start_1_distance','last_start_1_condition']:
    summary.append({'metric':f'{fld}_populated','value':sum(1 for r in out if not blank(r.get(fld,'')))})
summary += [{'metric':'average_run_lines_per_ok_partial_horse','value':f'{avg:.2f}'},{'metric':'horses_improved_vs_v3','value':improved},{'metric':'pricing_maths_changed','value':'NO'},{'metric':'v6_1_changed','value':'NO'},{'metric':'v7_2g2_changed','value':'NO'}]
with open(SUM,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows(summary)
rep=['EDGEiQ FORM ENRICHMENT FEED V4 REPORT',f'rows={len(out)}',f'races={races}',f'truth_counts={dict(truth)}',f'horses_improved_vs_v3={improved}',f'average_run_lines_per_ok_partial_horse={avg:.2f}']
for fld in ['last_start_1_date','last_start_1_rating','last_start_1_class','last_start_1_distance','last_start_1_condition']:
    rep.append(f'{fld}_populated={sum(1 for r in out if not blank(r.get(fld,"")))}')
rep += ['source_records_scanned_active_matches:']+[f'- {k}: {v}' for k,v in source_counts.items()]+['pricing_maths_changed=NO','v6_1_changed=NO','v7_2g2_changed=NO','status=FORM_ENRICHMENT_FEED_V4_BUILT']
with open(REP,'w',encoding='utf-8') as f: f.write('\n'.join(rep)+'\n')
print('\n'.join(rep))

