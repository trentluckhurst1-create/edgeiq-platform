import csv, re, os, math, collections
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA = os.path.join(ROOT, 'public', 'data')
GOV = os.path.join(DATA, 'edgeiq_live_runner_board_governed_v1.csv')
FORM = os.path.join(DATA, 'edgeiq_form_enrichment_feed_v2.csv')
HIST = os.path.join(DATA, 'edgeiq_historical_performance_rating_v6_1_research.csv')
TRAJ = os.path.join(DATA, 'edgeiq_runner_trajectory_feed_v1.csv')
OUT = os.path.join(DATA, 'edgeiq_form_tab_full_population_audit_v1.csv')
SUM = os.path.join(DATA, 'edgeiq_form_tab_full_population_summary_v1.csv')
REP = os.path.join(DATA, 'edgeiq_form_tab_full_population_report_v1.txt')

def read_csv(path):
    if not os.path.exists(path):
        return [], []
    with open(path, newline='', encoding='utf-8-sig') as f:
        r = csv.DictReader(f)
        return list(r), r.fieldnames or []

def clean(v):
    return re.sub(r'[^A-Z0-9]+', '', str(v or '').upper())

def clean_track(v):
    return re.sub(r'\s+', ' ', str(v or '').upper().strip())

def is_blank(v):
    return v is None or str(v).strip() == '' or str(v).strip().upper() in {'--','N/A','NA','NULL','NONE'}

def is_unknown(v):
    return is_blank(v) or str(v).strip().upper() in {'UNKNOWN','UNK'}

def key(row):
    rk = row.get('runner_key','')
    if rk and str(rk).strip(): return str(rk).strip()
    return '|'.join([str(row.get('race_date','')).strip(), clean_track(row.get('track','')), str(row.get('race_no','')).replace('R','').replace('r','').strip(), clean(row.get('horse_key') or row.get('horse'))])

gov, gov_cols = read_csv(GOV)
form, form_cols = read_csv(FORM)
hist, hist_cols = read_csv(HIST)
traj, traj_cols = read_csv(TRAJ)
form_by_key = {key(r): r for r in form}
traj_by_key = {key(r): r for r in traj}
hist_by_horse = collections.defaultdict(list)
for r in hist:
    h = clean(r.get('horse'))
    if h: hist_by_horse[h].append(r)

def date_val(r):
    s = str(r.get('race_date','')).strip()
    try: return datetime.fromisoformat(s[:10])
    except Exception: return datetime.min
for arr in hist_by_horse.values():
    arr.sort(key=date_val, reverse=True)

fields = [
    'form_truth_status','form_source','form_history_starts','form_signal','form_trend',
    'form_last_start_rating','form_avg_rating_last5','form_peak_rating_last5',
    'last_start_1_date','last_start_1_track','last_start_1_distance','last_start_1_class','last_start_1_condition',
    'last_start_1_finish','last_start_1_margin','last_start_1_rating','left_runner_list_form_score','left_runner_list_trend_signal'
]
rows=[]
counts=collections.Counter()
recoverable=collections.Counter()
for g in gov:
    k = key(g)
    f = form_by_key.get(k, {})
    t = traj_by_key.get(k, {})
    hrows = hist_by_horse.get(clean(g.get('horse_key') or g.get('horse')), [])
    status = f.get('form_truth_status','')
    for field in fields:
        source_val = ''
        classification = 'OK'
        source = 'FORM_V2'
        if field == 'left_runner_list_form_score':
            source_val = f.get('form_peak_rating_last5') or f.get('form_avg_rating_last5') or f.get('form_last_start_rating') or g.get('projected_rating_v5_2') or g.get('total_rating_points')
        elif field == 'left_runner_list_trend_signal':
            source_val = f.get('form_signal') or f.get('form_trend') or f.get('form_truth_status')
        else:
            source_val = f.get(field,'')
        if is_blank(source_val) or (field.endswith('_class') and is_unknown(source_val)):
            if status == 'BACKFILLED_CONTEXT_ONLY' and field.startswith('last_start_'):
                classification = 'TRUE_CONTEXT_ONLY'
                source = 'CONTEXT_ONLY_NO_FAKE_RUNS'
            elif field.startswith('last_start_1_') and hrows:
                base = field.replace('last_start_1_','')
                hist_col_options = {
                    'date':['race_date'], 'track':['track'], 'distance':['distance'],
                    'class':['race_class_clean','race_class_clean_v3_3','race_class_recovered','race_class_raw'],
                    'condition':['condition_recovered','condition_token_recovered'],
                    'finish':['finish_position','finish_pos_raw'], 'margin':['margin','margin_raw'],
                    'rating':['performance_rating_v6_1_research','performance_rating_v5_1','performance_rating_v3'],
                }.get(base, [])
                got = ''
                for c in hist_col_options:
                    got = hrows[0].get(c,'')
                    if not is_unknown(got): break
                if not is_unknown(got):
                    classification = 'RECOVERABLE_FROM_HISTORY'
                    source = 'HISTORICAL_V6_1'
                    recoverable[field]+=1
                else:
                    classification = 'SOURCE_MISSING'
                    source = 'HISTORICAL_FIELD_BLANK'
            elif field in {'form_trend','form_signal'} and (t.get('trajectory_direction') or t.get('trajectory_truth_status')):
                classification = 'RECOVERABLE_FROM_TRAJECTORY'
                source = 'TRAJECTORY'
                recoverable[field]+=1
            elif field in g and not is_blank(g.get(field)):
                classification = 'RECOVERABLE_FROM_RUNNER_BOARD'
                source = 'RUNNER_BOARD'
                recoverable[field]+=1
            elif status == 'OK_HISTORY':
                classification = 'FIX_REQUIRED'
                source = 'OK_HISTORY_FIELD_GAP'
            else:
                classification = 'SOURCE_MISSING'
                source = 'NO_SOURCE_VALUE'
        rows.append({
            'race_date': g.get('race_date',''), 'track': g.get('track',''), 'race_no': g.get('race_no',''),
            'horse': g.get('horse',''), 'runner_key': k, 'field': field, 'value': source_val,
            'form_truth_status': status, 'classification': classification, 'source_trace': source,
        })
        counts[classification]+=1

with open(OUT,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
summary = [
    {'metric':'governed_rows','value':len(gov)},
    {'metric':'governed_races','value':len(set((r.get('race_date',''),r.get('track',''),r.get('race_no','')) for r in gov))},
    {'metric':'form_rows','value':len(form)},
]
for k2,v in counts.items(): summary.append({'metric':f'class_{k2}','value':v})
for k2,v in recoverable.items(): summary.append({'metric':f'recoverable_{k2}','value':v})
with open(SUM,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f, fieldnames=['metric','value']); w.writeheader(); w.writerows(summary)
report = []
report.append('EDGEiQ FORM TAB FULL POPULATION AUDIT V1')
report.append(f'governed_rows={len(gov)}')
report.append(f'form_rows={len(form)}')
report.append('classification_counts:')
for k2,v in counts.most_common(): report.append(f'- {k2}: {v}')
report.append('recoverable_from_history:')
for k2,v in recoverable.most_common(): report.append(f'- {k2}: {v}')
report.append('pricing_maths_changed=NO')
report.append('v6_1_changed=NO')
report.append('v7_2g2_changed=NO')
with open(REP,'w',encoding='utf-8') as f: f.write('\n'.join(report)+'\n')
print('\n'.join(report))
