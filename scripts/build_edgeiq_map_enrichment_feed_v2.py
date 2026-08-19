import csv
import re
import shutil
from collections import defaultdict, Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
BOARD=DATA/'edgeiq_live_runner_board_governed_v1.csv'
MAP1=DATA/'edgeiq_map_enrichment_feed_v1.csv'
RUNNER=DATA/'edgeiq_runners_enrichment_feed_v1_1.csv'
TRAJ=DATA/'edgeiq_runner_trajectory_feed_v1.csv'
CMD=DATA/'edgeiq_command_enrichment_feed_v3.csv'
OUT=DATA/'edgeiq_map_enrichment_feed_v2.csv'
SUM=DATA/'edgeiq_map_enrichment_feed_v2_summary.csv'
AUD=DATA/'edgeiq_map_enrichment_feed_v2_audit.csv'
REP=DATA/'edgeiq_map_enrichment_feed_v2_report.txt'
DASH=chr(8212)
BAD={'','--','-','—','UNKNOWN','NOT LOADED','SOURCE_MISSING','SOURCE GAP','NULL','NAN','UNDEFINED','0.0'}
def read(p):
    if not p.exists(): return [],[]
    with p.open(encoding='utf-8-sig',newline='') as f:
        r=csv.DictReader(f); return list(r), r.fieldnames or []
def clean(v): return str(v or '').strip()
def norm(v): return re.sub(r'[^A-Z0-9]+','',clean(v).upper())
def ctrack(v): return re.sub(r'\s+',' ',clean(v).upper())
def key(row): return (clean(row.get('race_date') or row.get('current_race_date')),ctrack(row.get('track')),clean(row.get('race_no')),norm(row.get('horse_key') or row.get('horse')))
def runner_key(row): return clean(row.get('runner_key')) or '_'.join(key(row))
def n(v):
    m=re.search(r'-?\d+(?:\.\d+)?',clean(v))
    return float(m.group(0)) if m else None
def first(row, keys):
    for k in keys:
        v=clean(row.get(k))
        if v and v.upper() not in BAD: return v
    return ''
def num_first(*pairs):
    for row,keys in pairs:
        for k in keys:
            x=n(row.get(k))
            if x is not None: return x
    return None
def clamp(x,lo,hi): return max(lo,min(hi,x))
def fmt_num(x,dec=1):
    if x is None: return DASH
    return f'{x:.{dec}f}'.rstrip('0').rstrip('.')
def style_clean(v):
    raw=clean(v).upper().replace('_',' ').replace('-',' ')
    if raw in BAD or not raw: return 'UNKNOWN'
    if 'LEAD' in raw or raw in {'FRONT','FRONT RUNNER'}: return 'LEADER'
    if 'ON PACE' in raw or 'PROMINENT' in raw or 'PACE' in raw or 'FORWARD' in raw: return 'ON PACE'
    if 'BACK' in raw or 'CLOSER' in raw or 'LATE' in raw: return 'BACKMARKER'
    if 'MID' in raw or 'SETTL' in raw: return 'MIDFIELD'
    return raw if raw in {'LEADER','ON PACE','MIDFIELD','BACKMARKER'} else 'UNKNOWN'
def bucket_from_x(x):
    if x is None: return 'UNKNOWN'
    if x <= 25: return 'LEADER'
    if x <= 47: return 'ON PACE'
    if x <= 72: return 'MIDFIELD'
    return 'BACKMARKER'
def bucket_x(bucket, idx=0):
    base={'LEADER':14,'ON PACE':36,'MIDFIELD':61,'BACKMARKER':84}.get(bucket,75)
    return clamp(base+(idx%5-2)*2.2,4,96)
def pace_fit_label(v, band=''):
    raw=(clean(band) or clean(v)).upper().replace('_',' ')
    x=n(v)
    if any(t in raw for t in ['SUITED','POSITIVE','STRONG','GOOD']): return 'SUITED'
    if any(t in raw for t in ['RISK','NEGATIVE','POOR']): return 'RISK'
    if x is not None:
        if x>=65: return 'SUITED'
        if x<=45: return 'RISK'
        return 'NEUTRAL'
    if 'NEUTRAL' in raw or 'AVERAGE' in raw: return 'NEUTRAL'
    return DASH
def band_speed(x):
    if x is None: return DASH
    return 'HIGH' if x>=7 else 'MEDIUM' if x>=4 else 'LOW'
def wide_risk(barrier, field_size, bucket):
    b=n(barrier)
    if b is None or field_size<=0: return DASH
    if b >= max(1, field_size-2) and bucket in {'LEADER','ON PACE'}: return 'HIGH'
    if b >= max(1, field_size-4): return 'MEDIUM'
    return 'LOW'
def cover_risk(bucket, wide):
    if wide=='HIGH': return 'HIGH'
    if bucket in {'MIDFIELD','BACKMARKER'}: return 'LOW'
    if bucket=='ON PACE': return 'MEDIUM'
    return 'LOW'
def pressure_role(bucket, early):
    if bucket=='LEADER': return 'EARLY SPEED'
    if bucket=='ON PACE': return 'PRESSURE / STALK'
    if bucket=='MIDFIELD': return 'COVER SEEKER'
    if bucket=='BACKMARKER': return 'LATE RUNNER'
    return DASH
def pressure_band(score, leaders, onpace):
    x=n(score)
    if x is None: x=min(100, leaders*22+onpace*9)
    if x>=70: return 'HIGH PRESSURE'
    if x>=45: return 'MODERATE PRESSURE'
    return 'TACTICAL'
def advantage(band):
    if band=='HIGH PRESSURE': return 'LATE RUNNERS'
    if band=='TACTICAL': return 'LEADERS / ON PACE'
    return 'BALANCED'
def verdict(band, leaders, onpace, backs):
    if band=='HIGH PRESSURE': return f'High-pressure map with {leaders} leader(s) and {onpace} on-pace runner(s); late runners can come into play if the speed holds up early.'
    if band=='TACTICAL': return f'Tactical map with limited early pressure; leaders and handy runners may control the race shape.'
    return f'Moderate-pressure map; position and cover should matter more than pure tempo.'

def index(rows):
    m={}
    for r in rows:
        rk=clean(r.get('runner_key'))
        if rk: m[('rk',rk)]=r
        m[('rh',)+key(r)]=r
    return m
board,_=read(BOARD); map1,_=read(MAP1); runner,_=read(RUNNER); traj,_=read(TRAJ); cmd,_=read(CMD)
indexes={'map':index(map1),'runner':index(runner),'trajectory':index(traj),'command':index(cmd)}
pre=[]
for br in board:
    rk=('rk',clean(br.get('runner_key'))); rh=('rh',)+key(br)
    side={name:(idx.get(rk) or idx.get(rh) or {}) for name,idx in indexes.items()}
    m=side['map']; rr=side['runner']; tr=side['trajectory']; cm=side['command']
    style=style_clean(first(m,['run_style','speed_map_bucket','settling_position']) or first(br,['run_style','speed_map_bucket','settling_band']) or first(rr,['dominant_run_style','run_style']))
    speed=num_first((m,['projected_speed','early_speed']),(br,['early_speed_rating','projected_speed']))
    late=num_first((m,['late_speed']),(tr,['latest_rating_v1']),(br,['late_speed']))
    pace_raw=first(m,['pace_fit_band','pace_fit']) or first(cm,['edgeiq_score_pace_v3'])
    pace=pace_fit_label(first(m,['pace_fit']), pace_raw)
    x=num_first((m,['map_x_pct']),(br,['map_x_pct']))
    y=num_first((m,['map_y_px']),(br,['map_y_px']))
    barrier=first(br,['barrier','barrier_no','draw']) or first(m,['barrier'])
    pre.append((br,m,rr,tr,cm,style,speed,late,pace,x,y,barrier))
# Race counts from styles.
race_groups=defaultdict(list)
for item in pre: race_groups[(clean(item[0].get('race_date')),clean(item[0].get('track')),clean(item[0].get('race_no')))].append(item)
rows=[]; audit=[]
for race,items in race_groups.items():
    field_size=len(items)
    styles=[]
    for idx_item,item in enumerate(items):
        style=item[5]
        x=item[9]
        if style=='UNKNOWN': style=bucket_from_x(x)
        if x is None: x=bucket_x(style,idx_item)
        styles.append(style)
    counts=Counter(styles)
    leaders=counts['LEADER']; onpace=counts['ON PACE']; midfield=counts['MIDFIELD']; backs=counts['BACKMARKER']
    source_pressure=num_first((items[0][1],['race_pressure_score','race_pressure']),(items[0][0],['race_pressure_score']))
    pressure_score=source_pressure if source_pressure is not None else min(100, leaders*22+onpace*9+max(0,field_size-10)*2)
    pband=pressure_band(pressure_score,leaders,onpace)
    shape=first(items[0][1],['race_shape','race_shape_narrative']) or pband
    adv=advantage(pband)
    summary=f'{leaders} leader(s), {onpace} on pace, {midfield} midfield, {backs} backmarker(s).'
    race_verdict=verdict(pband,leaders,onpace,backs)
    # y lane: barrier 1 bottom for VIC states; present tracks here Victorian. higher barrier moves up.
    for idx_item,item in enumerate(items):
        br,m,rr,tr,cm,style,speed,late,pace,x,y,barrier=item
        if style=='UNKNOWN': style=bucket_from_x(x)
        if x is None: x=bucket_x(style,idx_item)
        x=clamp(float(x),4,96)
        b=n(barrier)
        if b is not None and 1<=b<=30:
            y=clamp(92 - ((b-1)/max(1,field_size-1))*76,8,94)
            barrier_disp=str(int(b))
        else:
            y=clamp(float(y),8,94) if y is not None else 50
            barrier_disp=DASH
        wr=wide_risk(barrier_disp,field_size,style)
        cr=cover_risk(style,wr)
        ev_sources=[]
        for label,row in [('MAP',m),('BOARD',br),('RUNNER',rr),('HISTORY',tr)]:
            if row: ev_sources.append(label)
        confidence='HIGH' if m and speed is not None and pace!=DASH and style!='UNKNOWN' else 'MEDIUM' if m else 'LOW'
        lane='OUTSIDE' if wr=='HIGH' else 'MIDDLE' if wr=='MEDIUM' else 'INSIDE/COVER'
        zone=f'{style} / {lane}' if style!='UNKNOWN' else lane
        out={
            'runner_key':runner_key(br),'race_date':clean(br.get('race_date')),'track':clean(br.get('track')),'race_no':clean(br.get('race_no')),'horse':clean(br.get('horse')),
            'saddlecloth':clean(br.get('horse_no') or br.get('runner_no') or m.get('runner_no')),'barrier':barrier_disp,
            'run_style_display':style,'run_style_source':'MAP_FEED' if first(m,['run_style','speed_map_bucket']) else 'BOARD_OR_DERIVED',
            'speed_map_bucket_display':style,'early_speed_rating_display':fmt_num(speed,1),'early_speed_band_display':band_speed(speed),
            'projected_speed_display':fmt_num(speed,1),'pace_fit_display':pace,'late_speed_display':fmt_num(late,1),'settling_band_display':style,
            'map_x_pct_display':fmt_num(x,1),'map_y_px_display':fmt_num(y,1),'map_lane_display':lane,'map_zone_display':zone,
            'wide_risk_display':wr,'cover_risk_display':cr,'pressure_role_display':pressure_role(style,speed),
            'race_shape_display':shape.replace('_',' ').upper(),'race_pressure_score_display':fmt_num(pressure_score,0),'race_pressure_band_display':pband,
            'pace_advantage_display':adv,'map_confidence_display':confidence,'map_evidence_display':' + '.join(ev_sources),
            'race_field_size_map_v2':field_size,'race_leader_count_v2':leaders,'race_on_pace_count_v2':onpace,'race_midfield_count_v2':midfield,'race_backmarker_count_v2':backs,
            'race_pressure_score_v2':fmt_num(pressure_score,0),'race_pressure_band_v2':pband,'race_shape_summary_v2':summary,'race_shape_verdict_v2':race_verdict,
            'pricing_maths_changed':'NO','v6_1_changed':'NO','v7_2g2_changed':'NO'
        }
        rows.append(out)
        for k,v in out.items():
            if k.endswith('_display') and (not clean(v) or clean(v).upper() in BAD): audit.append({'runner_key':out['runner_key'],'field':k,'issue':'RAW_OR_BLANK_DISPLAY','value':v})
        if not (0<=float(out['map_x_pct_display'])<=100): audit.append({'runner_key':out['runner_key'],'field':'map_x_pct_display','issue':'BAD_COORD','value':out['map_x_pct_display']})
        if not (0<=float(out['map_y_px_display'])<=100): audit.append({'runner_key':out['runner_key'],'field':'map_y_px_display','issue':'BAD_COORD','value':out['map_y_px_display']})
fields=list(rows[0].keys())
with OUT.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
with AUD.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['runner_key','field','issue','value']); w.writeheader(); w.writerows(audit)
summary=[('rows',len(rows)),('races',len(race_groups)),('duplicate_runner_keys',len(rows)-len({r['runner_key'] for r in rows})),('audit_issues',len(audit)),('v7_2g2_on',sum(1 for r in board if clean(r.get('edgeiq_v7_2g2_feature_flag')).upper()=='ON')),('v7_2g2_live_wired',sum(1 for r in board if clean(r.get('edgeiq_v7_2g2_live_wired_flag')).upper()=='YES_CONTROLLED_ON'))]
for field in ['run_style_display','projected_speed_display','pace_fit_display','late_speed_display','race_shape_display','wide_risk_display','map_confidence_display']:
    summary.append((field+'_populated',sum(1 for r in rows if clean(r[field]) and clean(r[field])!=DASH)))
summary += [('pricing_maths_changed','NO'),('v6_1_changed','NO'),('v7_2g2_changed','NO'),('status','MAP_ENRICHMENT_FEED_V2_BUILT' if not audit else 'MAP_ENRICHMENT_FEED_V2_REVIEW_REQUIRED')]
with SUM.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows({'metric':k,'value':v} for k,v in summary)
lines=['EDGEiQ MAP ENRICHMENT FEED V2']+[f'{k}={v}' for k,v in summary]
REP.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines))

