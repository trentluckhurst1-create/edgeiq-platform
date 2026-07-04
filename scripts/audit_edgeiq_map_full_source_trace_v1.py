import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
OUT=DATA/'edgeiq_map_full_source_trace_v1.csv'
SUM=DATA/'edgeiq_map_full_source_trace_v1_summary.csv'
REP=DATA/'edgeiq_map_full_source_trace_v1_report.txt'
FILES={
 'board':DATA/'edgeiq_live_runner_board_governed_v1.csv',
 'map':DATA/'edgeiq_map_enrichment_feed_v1.csv',
 'runner':DATA/'edgeiq_runners_enrichment_feed_v1_1.csv',
 'trajectory':DATA/'edgeiq_runner_trajectory_feed_v1.csv',
 'command':DATA/'edgeiq_command_enrichment_feed_v3.csv',
}
FIELDS=['run_style','speed_map_bucket','early_speed_rating','early_speed_band','projected_speed','pace_fit','late_speed','settling_band','map_x_pct','map_y_px','barrier','lane_wide_risk','race_shape','pressure_score','race_pressure_band','leader_count','on_pace_count','midfield_count','backmarker_count']
ALIASES={
 'run_style':['run_style','run_style_display','dominant_run_style','speed_map_bucket','settling_band'],
 'speed_map_bucket':['speed_map_bucket','speed_map_bucket_display','run_style','lane','settling_band'],
 'early_speed_rating':['early_speed_rating','early_speed','early_speed_display','early_speed_rating_display','projected_speed'],
 'early_speed_band':['early_speed_band','early_speed_band_display','early_speed_truth_status'],
 'projected_speed':['projected_speed','projected_speed_display','early_speed_rating','early_speed'],
 'pace_fit':['pace_fit','pace_fit_display','pace_fit_band','score_pace','edgeiq_score_pace_v3'],
 'late_speed':['late_speed','late_speed_display','latest_rating_v1'],
 'settling_band':['settling_band','settling_band_display','settling_position','settling_position_display'],
 'map_x_pct':['map_x_pct','map_x_pct_display'],
 'map_y_px':['map_y_px','map_y_px_display'],
 'barrier':['barrier','barrier_no','draw'],
 'lane_wide_risk':['wide_risk_display','wide_risk','lane','barrier'],
 'race_shape':['race_shape','race_shape_display','race_shape_summary_v2','race_shape_narrative'],
 'pressure_score':['race_pressure_score','race_pressure_score_display','pressure_score','race_pressure'],
 'race_pressure_band':['race_pressure_band','race_pressure_band_display','race_pressure'],
 'leader_count':['leaders_count','leader_count','race_leader_count_v2'],
 'on_pace_count':['on_pace_count','race_on_pace_count_v2'],
 'midfield_count':['midfield_count','race_midfield_count_v2'],
 'backmarker_count':['backmarker_count','race_backmarker_count_v2'],
}
BAD={'','--','-','—','UNKNOWN','NOT LOADED','SOURCE_MISSING','SOURCE GAP','NULL','NAN','UNDEFINED','0.0'}
def read(path):
    if not path.exists(): return [],[]
    with path.open(encoding='utf-8-sig',newline='') as f:
        r=csv.DictReader(f); return list(r), r.fieldnames or []
def clean(v): return str(v or '').strip()
def norm(v): return re.sub(r'[^A-Z0-9]+','',clean(v).upper())
def ctrack(v): return re.sub(r'\s+',' ',clean(v).upper())
def n(v):
    m=re.search(r'-?\d+(?:\.\d+)?',clean(v))
    return float(m.group(0)) if m else None
def good(v, field):
    s=clean(v)
    if not s or s.upper() in BAD: return False
    if field in {'map_x_pct'}:
        x=n(s); return x is not None and 0<=x<=100
    if field in {'map_y_px'}:
        x=n(s); return x is not None and 0<=x<=500
    if field=='barrier':
        x=n(s); return x is not None and 1<=x<=30
    if field in {'leader_count','on_pace_count','midfield_count','backmarker_count'}:
        x=n(s); return x is not None and x>=0
    if field in {'projected_speed','early_speed_rating','late_speed','pace_fit','pressure_score'}:
        x=n(s); return x is not None and x>=0
    return True
def first(row, field):
    for k in ALIASES[field]:
        if k in row and good(row.get(k),field): return clean(row.get(k)), k
    return '', ''
def key(row):
    rk=clean(row.get('runner_key'))
    if rk: return ('rk',rk)
    return ('rh',clean(row.get('race_date') or row.get('current_race_date')),ctrack(row.get('track')),clean(row.get('race_no')),norm(row.get('horse_key') or row.get('horse')))
def key_rh(row): return (clean(row.get('race_date') or row.get('current_race_date')),ctrack(row.get('track')),clean(row.get('race_no')),norm(row.get('horse_key') or row.get('horse')))
rows_by={}; idx={}
for name,path in FILES.items():
    rows,cols=read(path); rows_by[name]=rows
    m={}
    for r in rows:
        if clean(r.get('runner_key')): m[('rk',clean(r.get('runner_key')))] = r
        m[('rh',)+key_rh(r)] = r
    idx[name]=m
board=rows_by['board']
out=[]; counts=Counter(); field_counts=Counter()
for br in board:
    k1=('rk',clean(br.get('runner_key'))); k2=('rh',)+key_rh(br)
    side={name: (idx[name].get(k1) or idx[name].get(k2) or {}) for name in idx}
    for field in FIELDS:
        status='SOURCE_MISSING'; source=''; value=''
        for source_name,row in [('board',br),('map',side['map']),('runner',side['runner']),('trajectory',side['trajectory']),('command',side['command'])]:
            val,col=first(row,field)
            if val:
                value=val; source=source_name+':'+col
                if source_name=='board': status='OK'
                elif source_name=='map': status='RECOVERABLE_FROM_MAP_FEED'
                elif source_name=='runner': status='RECOVERABLE_FROM_RUNNER_PROFILE'
                elif source_name=='trajectory': status='RECOVERABLE_FROM_HISTORY'
                elif source_name=='command': status='RECOVERABLE_FROM_BOARD' if field=='pace_fit' else 'RECOVERABLE_FROM_RUNNER_PROFILE'
                break
        if not side['map'] and field not in {'barrier'}: status='JOIN_FAILED' if status=='SOURCE_MISSING' else status
        if status!='OK' and status.startswith('RECOVERABLE'): fix='FIX_REQUIRED'
        elif status in {'SOURCE_MISSING','JOIN_FAILED','BAD_VALUE'}: fix='FIX_REQUIRED'
        else: fix='OK'
        out.append({'runner_key':clean(br.get('runner_key')),'race_date':clean(br.get('race_date')),'track':clean(br.get('track')),'race_no':clean(br.get('race_no')),'horse':clean(br.get('horse')),'field':field,'value':value,'source':source,'status':status,'fix_status':fix})
        counts[status]+=1; field_counts[(field,status)]+=1
with OUT.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['runner_key','race_date','track','race_no','horse','field','value','source','status','fix_status']); w.writeheader(); w.writerows(out)
summary=[]
summary += [('governed_rows',len(board)),('governed_races',len({(r.get('race_date'),r.get('track'),r.get('race_no')) for r in board})),('trace_rows',len(out)),('fix_required',sum(1 for r in out if r['fix_status']=='FIX_REQUIRED'))]
for k,v in counts.most_common(): summary.append((k,v))
for field in FIELDS:
    summary.append((field+'_ok_or_recoverable',sum(v for (f,s),v in field_counts.items() if f==field and (s=='OK' or s.startswith('RECOVERABLE')))))
summary += [('pricing_maths_changed','NO'),('v6_1_changed','NO'),('v7_2g2_changed','NO'),('status','MAP_FULL_SOURCE_TRACE_COMPLETE')]
with SUM.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows({'metric':k,'value':v} for k,v in summary)
lines=['EDGEiQ MAP FULL SOURCE TRACE V1']+[f'{k}={v}' for k,v in summary]
REP.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines))
