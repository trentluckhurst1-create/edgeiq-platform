import csv, re, os, collections
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA = os.path.join(ROOT, 'public', 'data')
GOV = os.path.join(DATA, 'edgeiq_live_runner_board_governed_v1.csv')
FORM2 = os.path.join(DATA, 'edgeiq_form_enrichment_feed_v2.csv')
HIST = os.path.join(DATA, 'edgeiq_historical_performance_rating_v6_1_research.csv')
TRAJ = os.path.join(DATA, 'edgeiq_runner_trajectory_feed_v1.csv')
OUT = os.path.join(DATA, 'edgeiq_form_enrichment_feed_v3.csv')
SUM = os.path.join(DATA, 'edgeiq_form_enrichment_feed_v3_summary.csv')
AUD = os.path.join(DATA, 'edgeiq_form_enrichment_feed_v3_audit.csv')
REP = os.path.join(DATA, 'edgeiq_form_enrichment_feed_v3_report.txt')

def read_csv(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return list(r), r.fieldnames or []

def clean(v): return re.sub(r'[^A-Z0-9]+','',str(v or '').upper())
def clean_track(v): return re.sub(r'\s+',' ',str(v or '').upper().strip())
def norm_race_no(v): return str(v or '').upper().replace('R','').strip()
def is_blank(v): return v is None or str(v).strip()=='' or str(v).strip().upper() in {'--','N/A','NA','NULL','NONE'}
def is_unknown(v): return is_blank(v) or str(v).strip().upper() in {'UNKNOWN','UNK'}
def first(row, cols):
    for c in cols:
        v=row.get(c,'')
        if not is_unknown(v): return str(v).strip()
    return ''
def as_float(v):
    try:
        if is_blank(v): return None
        return float(str(v).replace('$','').replace(',','').strip())
    except Exception: return None
def fmt(v, digits=1):
    if v is None: return ''
    if abs(v-round(v))<0.000001 and digits==0: return str(int(round(v)))
    return f'{v:.{digits}f}'
def date_val(s):
    try: return datetime.fromisoformat(str(s or '')[:10])
    except Exception: return datetime.min
def runner_key(row):
    rk=str(row.get('runner_key','')).strip()
    if rk: return rk
    return '|'.join([str(row.get('race_date','')).strip(), clean_track(row.get('track','')), norm_race_no(row.get('race_no')), clean(row.get('horse_key') or row.get('horse'))])

gov, gov_cols = read_csv(GOV)
form2, form_cols = read_csv(FORM2)
hist, hist_cols = read_csv(HIST)
traj, traj_cols = read_csv(TRAJ)
form_by_key={runner_key(r):r for r in form2}
traj_by_key={runner_key(r):r for r in traj}
hist_by_horse=collections.defaultdict(list)
for r in hist:
    h=clean(r.get('horse'))
    if h: hist_by_horse[h].append(r)
for arr in hist_by_horse.values(): arr.sort(key=lambda r: date_val(r.get('race_date')), reverse=True)

base_cols=[]
for c in gov_cols + form_cols:
    if c not in base_cols: base_cols.append(c)
extra=[]
for n in range(1,6):
    extra += [f'last_start_{n}_reason', f'last_start_{n}_finishing_position', f'last_start_{n}_beaten_margin', f'last_start_{n}_SP', f'last_start_{n}_performance_label']
extra += ['form_cycle','rating_trend','rating_trend_delta','performance_intelligence_label','performance_intelligence_narrative','form_v3_truth_status','form_v3_recovery_notes']
cols=[]
for c in base_cols+extra:
    if c not in cols: cols.append(c)

out=[]; audit=[]; recovery_counts=collections.Counter()
for g in gov:
    k=runner_key(g)
    f=dict(form_by_key.get(k, {}))
    row={c:g.get(c,'') for c in gov_cols}
    for c in form_cols:
        row[c]=f.get(c,row.get(c,''))
    if not row.get('runner_key'): row['runner_key']=k
    if not row.get('horse_key'): row['horse_key']=clean(row.get('horse'))
    horse_key=clean(row.get('horse_key') or row.get('horse'))
    current_date=date_val(row.get('race_date'))
    hrows=[hr for hr in hist_by_horse.get(horse_key, []) if date_val(hr.get('race_date')) < current_date]
    status=row.get('form_truth_status') or ('OK_HISTORY' if hrows else 'BACKFILLED_CONTEXT_ONLY')
    notes=[]
    has_existing_run = (not is_blank(row.get('last_start_1_date')) or not is_blank(row.get('last_start_1_rating')))
    if status == 'OK_HISTORY' and not hrows and not has_existing_run:
        status='BACKFILLED_CONTEXT_ONLY'
        notes.append('downgraded_no_historical_rows')
    row['form_truth_status']=status
    if not row.get('form_source'):
        row['form_source']='HISTORICAL_V6_1' if status=='OK_HISTORY' else 'TRAJECTORY_CONTEXT_ONLY'
    if status == 'OK_HISTORY':
        ratings=[]; wins=0; places=0
        for idx, hr in enumerate(hrows[:5], start=1):
            p=f'last_start_{idx}_'
            mappings={
                'date': first(hr,['race_date']),
                'track': first(hr,['track']),
                'distance': first(hr,['distance']),
                'class': first(hr,['race_class_clean','race_class_clean_v3_3','race_class_recovered','race_class_raw']),
                'condition': first(hr,['condition_recovered','condition_token_recovered']),
                'finish': first(hr,['finish_position','finish_pos_raw']),
                'margin': first(hr,['margin','margin_raw']),
                'rating': first(hr,['performance_rating_v6_1_research','performance_rating_v5_1','performance_rating_v3']),
                'sp': first(hr,['sp_price','SP','sp','market_price']),
            }
            reason=first(hr,['performance_rating_v6_1_research_reason','performance_reason_v3','class_recovery_reason','rating_v5_1_status'])
            for fld,val in mappings.items():
                target=p+fld
                if fld in {'class','condition'}:
                    if is_unknown(row.get(target)) and not is_unknown(val):
                        row[target]=val; recovery_counts[target]+=1; notes.append(f'recovered_{target}')
                elif is_blank(row.get(target)) and not is_blank(val):
                    row[target]=val; recovery_counts[target]+=1; notes.append(f'recovered_{target}')
            row[p+'reason']=reason
            row[p+'finishing_position']=row.get(p+'finish','')
            row[p+'beaten_margin']=row.get(p+'margin','')
            row[p+'SP']=row.get(p+'sp','')
            row[p+'performance_label']=first(hr,['performance_band_v3','rating_v5_1_status']) or ''
            rv=as_float(row.get(p+'rating'))
            if rv is not None: ratings.append(rv)
            fin=as_float(row.get(p+'finish'))
            if fin == 1: wins += 1
            if fin is not None and fin <= 3: places += 1
        if ratings:
            row['form_history_starts']=row.get('form_history_starts') or str(len(hrows))
            row['form_history_wins']=row.get('form_history_wins') or str(wins)
            row['form_history_places']=row.get('form_history_places') or str(places)
            row['form_last_start_rating']=row.get('form_last_start_rating') or fmt(ratings[0],1)
            row['form_avg_rating_last5']=row.get('form_avg_rating_last5') or fmt(sum(ratings)/len(ratings),1)
            row['form_peak_rating_last5']=row.get('form_peak_rating_last5') or fmt(max(ratings),1)
            if len(ratings)>=2:
                delta=ratings[0]-ratings[1]
                row['form_rating_delta_last_start']=row.get('form_rating_delta_last_start') or fmt(delta,1)
                row['rating_trend_delta']=fmt(delta,1)
                if delta >= 3: trend='IMPROVING'
                elif delta <= -3: trend='DECLINING'
                else: trend='STABLE'
            else:
                trend='LIMITED FORM'
                row['rating_trend_delta']=row.get('form_rating_delta_last_start','')
            row['form_trend']=row.get('form_trend') or trend
            row['rating_trend']=trend
            row['form_cycle']=trend
            row['form_signal']=row.get('form_signal') or ('STRONG RECENT FIGURE' if max(ratings)>=70 else 'LIMITED FORM' if len(ratings)<3 else 'RECENT FORM LOADED')
            row['performance_intelligence_label']=row.get('performance_intelligence_label') or ('IMPROVING' if trend=='IMPROVING' else 'BELOW EXPECTATIONS' if trend=='DECLINING' else 'NEUTRAL')
            row['performance_intelligence_narrative']=row.get('performance_intelligence_narrative') or f"Recent rated form available from {len(ratings)} historical run{'s' if len(ratings)!=1 else ''}."
    else:
        for idx in range(1,6):
            p=f'last_start_{idx}_'
            row[p+'reason']=row.get(p+'reason','')
            row[p+'finishing_position']=row.get(p+'finish','')
            row[p+'beaten_margin']=row.get(p+'margin','')
            row[p+'SP']=row.get(p+'sp','')
            row[p+'performance_label']=row.get(p+'performance_label','')
        t=traj_by_key.get(k,{})
        row['form_cycle']=row.get('form_cycle') or first(t,['trajectory_direction','trajectory_truth_status']) or 'CONTEXT ONLY'
        row['rating_trend']=row.get('rating_trend') or row.get('form_trend') or 'CONTEXT ONLY'
        row['rating_trend_delta']=row.get('rating_trend_delta') or row.get('form_rating_delta_last_start','')
        row['performance_intelligence_label']=row.get('performance_intelligence_label') or 'NEUTRAL'
        row['performance_intelligence_narrative']=row.get('performance_intelligence_narrative') or 'Context only - no detailed rated-history lines available.'
    row['form_v3_truth_status']=status
    row['form_v3_recovery_notes']=';'.join(sorted(set(notes))) if notes else 'NO_RECOVERY_REQUIRED'
    out.append({c:row.get(c,'') for c in cols})
    audit.append({
        'race_date':row.get('race_date',''),'track':row.get('track',''),'race_no':row.get('race_no',''),'horse':row.get('horse',''),'runner_key':row.get('runner_key',''),
        'form_truth_status':status,'last_start_1_date':row.get('last_start_1_date',''),'last_start_1_distance':row.get('last_start_1_distance',''),
        'last_start_1_class':row.get('last_start_1_class',''),'last_start_1_condition':row.get('last_start_1_condition',''),
        'last_start_1_rating':row.get('last_start_1_rating',''),'recovery_notes':row.get('form_v3_recovery_notes','')
    })

with open(OUT,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(out)
with open(AUD,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f, fieldnames=list(audit[0].keys())); w.writeheader(); w.writerows(audit)
truth=collections.Counter(r['form_truth_status'] for r in out)
races=len(set((r.get('race_date',''),r.get('track',''),r.get('race_no','')) for r in out))
summary=[
 {'metric':'rows','value':len(out)}, {'metric':'races','value':races},
 {'metric':'runner_key_populated','value':sum(1 for r in out if r.get('runner_key'))},
 {'metric':'duplicate_runner_keys','value':len(out)-len(set(r.get('runner_key') for r in out))},
]
for k2,v in truth.items(): summary.append({'metric':f'truth_{k2}','value':v})
for fld in ['last_start_1_date','last_start_1_rating','last_start_1_class','last_start_1_distance','last_start_1_condition']:
    summary.append({'metric':f'{fld}_populated','value':sum(1 for r in out if not is_unknown(r.get(fld,'')))})
for k2,v in recovery_counts.items(): summary.append({'metric':f'recovered_{k2}','value':v})
summary += [{'metric':'pricing_maths_changed','value':'NO'},{'metric':'v6_1_changed','value':'NO'},{'metric':'v7_2g2_changed','value':'NO'}]
with open(SUM,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f, fieldnames=['metric','value']); w.writeheader(); w.writerows(summary)
rep=['EDGEiQ FORM ENRICHMENT FEED V3 REPORT',f'rows={len(out)}',f'races={races}',f'truth_counts={dict(truth)}']
for fld in ['last_start_1_date','last_start_1_rating','last_start_1_class','last_start_1_distance','last_start_1_condition']:
    rep.append(f'{fld}_populated={sum(1 for r in out if not is_unknown(r.get(fld,"")))}')
rep += ['pricing_maths_changed=NO','v6_1_changed=NO','v7_2g2_changed=NO','status=FORM_ENRICHMENT_FEED_V3_BUILT']
with open(REP,'w',encoding='utf-8') as f: f.write('\n'.join(rep)+'\n')
print('\n'.join(rep))


