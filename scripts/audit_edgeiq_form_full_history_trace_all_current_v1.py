import csv, os, re, collections
from datetime import datetime
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
DATA=os.path.join(ROOT,'public','data')
GOV=os.path.join(DATA,'edgeiq_live_runner_board_governed_v1.csv')
OUT=os.path.join(DATA,'edgeiq_form_full_history_trace_all_current_v1.csv')
SUM=os.path.join(DATA,'edgeiq_form_full_history_trace_all_current_v1_summary.csv')
REP=os.path.join(DATA,'edgeiq_form_full_history_trace_all_current_v1_report.txt')
SOURCES=[
 ('RESULTS_WAREHOUSE','edgeiq_historical_results_warehouse_v2_graphql.csv',['horse','horse_code'],['race_date'],['track','venue_name'],['distance'],['race_class'],['track_condition','track_rating'],['finish_num','finish'],['margin_l','margin'],[],['starting_price_decimal','starting_price'],['comment_short','comment','comment_stewards']),
 ('HISTORY_MASTER','edgeiq_historical_run_ratings_master_v1.csv',['horse','horse_key'],['race_date'],['track'],['distance'],['class_name'],['condition'],['finish_pos'],['margin'],['performance_rating'],['sp'],['rating_method','rating_band']),
 ('HISTORY_DETAIL','edgeiq_runner_history_detail_v1.csv',['horse','horse_key','recovery_horse','recovery_horse_key'],['race_date','run_date_iso','recovery_race_date'],['track','recovery_track'],['distance','recovery_distance'],['class_name','recovery_class_name'],['condition','recovery_condition'],['finish_pos','recovery_finish_pos'],['margin','recovery_margin'],['run_rating_final','recovered_rating','recovery_recovered_rating','performance_rating'],['sp','recovery_sp'],['rating_source','source_confidence','recovery_source_confidence']),
 ('RUNNER_FORM_HISTORY','runner_form_history.csv',['horse','horse_key'],['run_date_iso','run_date'],['track'],['distance'],['class_name'],[],['finish_pos'],['margin'],['run_rating'],['sp'],['history_status']),
 ('V6_1_RESEARCH_HISTORY','edgeiq_historical_performance_rating_v6_1_research.csv',['horse'],['race_date'],['track'],['distance'],['race_class_clean','race_class_clean_v3_3','race_class_recovered','race_class_raw'],['condition_recovered','condition_token_recovered'],['finish_position','finish_pos_raw'],['margin','margin_raw'],['performance_rating_v6_1_research','performance_rating_v5_1','performance_rating_v3'],[],['performance_rating_v6_1_research_reason','performance_reason_v3']),
 ('FORM_CARD_STEWARDS','form_card_runs_with_stewards.csv',['horse','horse_key','horse_soft'],['run_date'],['track'],['distance'],['race_class'],['track_condition'],['finish_pos'],['margin'],['run_rating'],['starting_price','sp_text'],['stewards_short','comment']),
 ('FULL_CAREER_FORM','full_career_form.csv',['horse','horse_key'],['run_date'],['track'],['distance'],['race_class'],['track_condition'],['finish_pos'],['margin'],['run_rating','rating_display'],['starting_price','sp_text'],['run_type']),
 ('HISTORICAL_FORM_TABLE','historical_form_table.csv',['horse'],['race_date'],['track'],['distance'],[],['track_condition'],['finish_pos'],['margin'],['run_rating','race_rating'],['sp'],[]),
]

def read_csv(path):
    with open(path,newline='',encoding='utf-8-sig',errors='replace') as f:
        r=csv.DictReader(f); return list(r), r.fieldnames or []
def norm_horse(v):
    s=str(v or '').upper()
    s=re.sub(r'\([^)]*\)',' ',s)
    s=re.sub(r'\b\d+E\b',' ',s)
    s=s.replace('�','')
    return re.sub(r'[^A-Z0-9]+','',s)
def first(row, cols):
    for c in cols:
        v=row.get(c,'')
        if str(v).strip() and str(v).strip().upper() not in {'--','N/A','NA','NULL','NONE','UNKNOWN'}:
            return str(v).strip()
    return ''
def date_val(v):
    s=str(v or '').strip()[:10]
    try: return datetime.fromisoformat(s)
    except Exception: return datetime.min

gov, _=read_csv(GOV)
active_keys={norm_horse(r.get('horse_key') or r.get('horse')) for r in gov}
active_keys.discard('')
counts={src:collections.Counter() for src,*_ in SOURCES}
source_exists={}
for src,file,horse_cols,date_cols,track_cols,dist_cols,class_cols,cond_cols,finish_cols,margin_cols,rating_cols,sp_cols,comment_cols in SOURCES:
    path=os.path.join(DATA,file)
    source_exists[src]=os.path.exists(path)
    if not os.path.exists(path): continue
    with open(path,newline='',encoding='utf-8-sig',errors='replace') as f:
        reader=csv.DictReader(f)
        for row in reader:
            h=norm_horse(first(row,horse_cols))
            if not h or h not in active_keys: continue
            if not first(row,date_cols): continue
            has_run=bool(first(row,track_cols) or first(row,finish_cols) or first(row,dist_cols))
            if has_run: counts[src][h]+=1
rows=[]; class_counts=collections.Counter()
for g in gov:
    h=norm_horse(g.get('horse_key') or g.get('horse'))
    c={src:counts[src][h] for src,*_ in SOURCES}
    total=sum(1 for v in c.values() if v>0)
    if c.get('RESULTS_WAREHOUSE',0)>0: cls='RESULTS_WAREHOUSE_AVAILABLE'
    elif c.get('HISTORY_MASTER',0)>0: cls='MASTER_HISTORY_AVAILABLE'
    elif c.get('HISTORY_DETAIL',0)>0: cls='DETAIL_HISTORY_AVAILABLE'
    elif c.get('RUNNER_FORM_HISTORY',0)>0: cls='RUNNER_FORM_HISTORY_AVAILABLE'
    elif c.get('V6_1_RESEARCH_HISTORY',0)>0: cls='V61_ONLY'
    elif c.get('FORM_CARD_STEWARDS',0)>0 or c.get('FULL_CAREER_FORM',0)>0 or c.get('HISTORICAL_FORM_TABLE',0)>0: cls='OTHER_HISTORY_AVAILABLE'
    else: cls='TRUE_CONTEXT_ONLY'
    if cls!='TRUE_CONTEXT_ONLY' and total==0: cls='JOIN_FAILURE'
    class_counts[cls]+=1
    row={'race_date':g.get('race_date',''),'track':g.get('track',''),'race_no':g.get('race_no',''),'horse':g.get('horse',''),'horse_norm':h,'classification':cls}
    for src in counts: row[f'{src.lower()}_runs']=c.get(src,0)
    row['sources_with_history']=total
    rows.append(row)
with open(OUT,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
summary=[{'metric':'governed_rows','value':len(gov)},{'metric':'governed_races','value':len(set((r.get('race_date',''),r.get('track',''),r.get('race_no','')) for r in gov))}]
for k,v in class_counts.items(): summary.append({'metric':f'class_{k}','value':v})
for src in counts: summary.append({'metric':f'{src.lower()}_matched_runners','value':sum(1 for r in rows if int(r[f'{src.lower()}_runs'])>0)})
summary += [{'metric':'pricing_maths_changed','value':'NO'},{'metric':'v6_1_changed','value':'NO'},{'metric':'v7_2g2_changed','value':'NO'}]
with open(SUM,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows(summary)
rep=['EDGEiQ FORM FULL HISTORY TRACE ALL CURRENT V1',f'governed_rows={len(gov)}','classification_counts:']
for k,v in class_counts.most_common(): rep.append(f'- {k}: {v}')
rep.append('source_runner_matches:')
for src in counts: rep.append(f'- {src}: {sum(1 for r in rows if int(r[f"{src.lower()}_runs"])>0)}')
rep += ['pricing_maths_changed=NO','v6_1_changed=NO','v7_2g2_changed=NO','status=FORM_FULL_HISTORY_TRACE_COMPLETE']
with open(REP,'w',encoding='utf-8') as f: f.write('\n'.join(rep)+'\n')
print('\n'.join(rep))
