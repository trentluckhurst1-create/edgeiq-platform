import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
GOV = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
CMD = DATA / 'edgeiq_command_enrichment_feed_v3.csv'
RACE_SHAPE = DATA / 'edgeiq_race_shape_fallback_engine_v1.csv'
OUT = DATA / 'edgeiq_map_enrichment_feed_v1.csv'
SUMMARY = DATA / 'edgeiq_map_enrichment_feed_v1_summary.csv'
AUDIT = DATA / 'edgeiq_map_enrichment_feed_v1_audit.csv'
REPORT = DATA / 'edgeiq_map_enrichment_feed_v1_report.txt'


def read_csv(path):
    if not path.exists(): return [], []
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f); return list(reader), list(reader.fieldnames or [])


def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); writer.writeheader(); writer.writerows(rows)


def clean(v): return ' '.join(str(v or '').strip().upper().replace('\u00a0',' ').split())
def clean_track(v): return ''.join(ch for ch in clean(v) if ch.isalnum())
def clean_horse(v):
    s = clean(v)
    while '(' in s and ')' in s:
        start=s.find('('); end=s.find(')',start)
        if end <= start: break
        s=(s[:start]+s[end+1:]).strip()
    for suffix in ['NZ','GB','IRE','FR','USA','JPN','AUS']:
        if s.endswith(suffix): s=s[:-len(suffix)].strip()
    return ''.join(ch for ch in s if ch.isalnum())
def race_no(v):
    s=clean(v).replace('RACE ','').replace('R','')
    try: return str(int(float(s)))
    except Exception: return s.lstrip('0') or s
def key(r): return (clean(r.get('race_date') or r.get('current_race_date')), clean_track(r.get('track')), race_no(r.get('race_no')), clean_horse(r.get('horse') or r.get('horse_key')))
def rkey(r): return key(r)[:3]
def populated(v): return str(v or '').strip() not in {'','-','--','N/A','NA','NULL','None'}
def num(v):
    s=str(v or '').replace('$','').replace('%','').strip()
    if not s: return None
    try:
        n=float(s); return n if n==n else None
    except Exception: return None
def nz(v):
    n=num(v); return n is not None and abs(n)>1e-9

def role_from(raw):
    value=clean(raw).replace('_',' ')
    if 'LEADER' in value or value in {'FRONT','FRONT RUNNER'}: return 'LEADERS'
    if 'ON PACE' in value or value == 'PACE' or 'FORWARD' in value: return 'ON PACE'
    if 'BACKMARK' in value or 'REAR' in value: return 'BACKMARKERS'
    if 'OFF PACE' in value or 'MIDFIELD' in value: return 'MIDFIELD'
    return 'MIDFIELD'

def role_speed(role):
    return {'LEADERS': 8.5, 'ON PACE': 7.0, 'MIDFIELD': 5.2, 'BACKMARKERS': 3.6}.get(role, 5.0)

def role_x(role):
    return {'LEADERS': 12, 'ON PACE': 30, 'MIDFIELD': 55, 'BACKMARKERS': 78}.get(role, 55)

def role_y(role, barrier, field_size):
    base={'LEADERS':14,'ON PACE':36,'MIDFIELD':58,'BACKMARKERS':80}.get(role,58)
    b=num(barrier) or 1
    fs=max(num(field_size) or 1, 1)
    return round(max(8, min(88, base + ((b-1) / fs) * 12)), 1)

def pressure_band(score, label):
    txt=clean(label)
    if 'HIGH' in txt or 'FAST' in txt or 'PRESSURE' in txt: return 'HIGH'
    if 'SLOW' in txt or 'LOW' in txt: return 'LOW'
    n=num(score)
    if n is not None:
        if n >= 70: return 'HIGH'
        if n <= 35: return 'LOW'
    return 'MODERATE'

def pace_fit(role, pressure):
    # Transparent tactical fit from role and race pressure only; not pricing/model maths.
    matrix={
        ('LEADERS','LOW'):72, ('LEADERS','MODERATE'):62, ('LEADERS','HIGH'):43,
        ('ON PACE','LOW'):68, ('ON PACE','MODERATE'):66, ('ON PACE','HIGH'):52,
        ('MIDFIELD','LOW'):52, ('MIDFIELD','MODERATE'):60, ('MIDFIELD','HIGH'):68,
        ('BACKMARKERS','LOW'):42, ('BACKMARKERS','MODERATE'):55, ('BACKMARKERS','HIGH'):72,
    }
    return matrix.get((role, pressure), 55)

def fit_band(score):
    if score >= 70: return 'POSITIVE'
    if score >= 58: return 'SUITED'
    if score >= 48: return 'NEUTRAL'
    return 'RISK'

def first_pop(*vals):
    for v in vals:
        if populated(v): return v
    return ''

gov, _ = read_csv(GOV)
cmd, _ = read_csv(CMD)
shape, _ = read_csv(RACE_SHAPE)
cmd_by={key(r):r for r in cmd}
shape_by={rkey(r):r for r in shape}
byrace=defaultdict(list)
for g in gov: byrace[rkey(g)].append(g)

rows=[]
for g in gov:
    k=key(g); rk=k[:3]
    cr=cmd_by.get(k,{})
    sr=shape_by.get(rk,{})
    field_size=len(byrace[rk])
    role=role_from(first_pop(g.get('settling_band'), g.get('run_style'), g.get('speed_map_bucket'), g.get('early_speed_band')))
    speed_value=num(g.get('projected_spd'))
    speed_source='GOVERNED_PROJECTED_SPD'
    speed_truth='OK_SOURCE_FIELD'
    if speed_value is None or abs(speed_value) < 1e-9:
        if nz(g.get('early_speed_rating')):
            speed_value=num(g.get('early_speed_rating')); speed_source='GOVERNED_EARLY_SPEED_RATING'; speed_truth='OK_SOURCE_FIELD'
        else:
            speed_value=role_speed(role); speed_source='DERIVED_FROM_RUN_STYLE_BAND'; speed_truth='DERIVED_TRANSPARENT_FALLBACK'
    pressure=pressure_band(sr.get('early_pressure_score'), first_pop(sr.get('pressure_risk'), sr.get('tempo_label')))
    fit=pace_fit(role, pressure)
    fit_source='RUN_STYLE_PLUS_RACE_PRESSURE'
    fit_truth='DERIVED_TRANSPARENT_TACTICAL_FIT'
    early=num(g.get('early_speed_rating'))
    early_source='GOVERNED_EARLY_SPEED_RATING'
    early_truth='OK_SOURCE_FIELD'
    if early is None or abs(early)<1e-9:
        early=round(speed_value,1); early_source=speed_source; early_truth=speed_truth
    late=None
    if role == 'BACKMARKERS': late=68
    elif role == 'MIDFIELD': late=60
    elif role == 'ON PACE': late=52
    else: late=45
    late_source='DERIVED_FROM_RUN_STYLE_BALANCE'; late_truth='DERIVED_TRANSPARENT_FALLBACK'
    track=clean_track(g.get('track'))
    direction='LEFT_HANDED' if track in {'CAULFIELD','CAULFIELDHEATH','FLEMINGTON','SANDOWN','SANDOWNLAKESIDE','SANDOWNHILLSIDE','MORNINGTON'} else 'RIGHT_HANDED' if track in {'BENDIGO','BALLARAT','BALLARATSYNTHETIC','GEELONG','SALE','CRANBOURNE','PAKENHAM','WERRIBEE','WARRNAMBOOL'} else 'UNKNOWN'
    orientation='INSIDE_LOW_BARRIERS' if direction != 'UNKNOWN' else 'UNKNOWN'
    row={
        'race_date':g.get('race_date',''), 'track':g.get('track',''), 'race_no':g.get('race_no',''), 'horse':g.get('horse',''), 'horse_key':g.get('horse_key',''),
        'barrier':g.get('barrier',''), 'runner_no':g.get('horse_no') or g.get('saddlecloth',''),
        'projected_speed':round(speed_value,1), 'projected_speed_source':speed_source, 'projected_speed_truth_status':speed_truth,
        'pace_fit':fit, 'pace_fit_band':fit_band(fit), 'pace_fit_source':fit_source, 'pace_fit_truth_status':fit_truth,
        'run_style':role, 'run_style_source':'GOVERNED_EARLY_SPEED_BAND_OR_RUN_STYLE', 'run_style_truth_status':'OK_SOURCE_FIELD',
        'early_speed':round(early,1), 'early_speed_source':early_source, 'early_speed_truth_status':early_truth,
        'late_speed':late, 'late_speed_source':late_source, 'late_speed_truth_status':late_truth,
        'settling_position':role, 'settling_position_source':'RUN_STYLE_NORMALISED', 'settling_position_truth_status':'OK_SOURCE_FIELD',
        'lane':role, 'map_x_pct':role_x(role), 'map_y_px':role_y(role,g.get('barrier'),field_size),
        'leaders_count':sum(1 for x in byrace[rk] if role_from(first_pop(x.get('settling_band'),x.get('run_style'),x.get('speed_map_bucket'),x.get('early_speed_band')))=='LEADERS'),
        'on_pace_count':sum(1 for x in byrace[rk] if role_from(first_pop(x.get('settling_band'),x.get('run_style'),x.get('speed_map_bucket'),x.get('early_speed_band')))=='ON PACE'),
        'midfield_count':sum(1 for x in byrace[rk] if role_from(first_pop(x.get('settling_band'),x.get('run_style'),x.get('speed_map_bucket'),x.get('early_speed_band')))=='MIDFIELD'),
        'backmarker_count':sum(1 for x in byrace[rk] if role_from(first_pop(x.get('settling_band'),x.get('run_style'),x.get('speed_map_bucket'),x.get('early_speed_band')))=='BACKMARKERS'),
        'race_pressure':pressure, 'race_pressure_score':sr.get('early_pressure_score',''), 'race_shape':sr.get('race_shape_label') or sr.get('tempo_label') or pressure,
        'race_shape_narrative':sr.get('race_shape_narrative',''), 'rail':g.get('rail_position',''), 'track_condition':g.get('track_condition',''),
        'track_direction':direction, 'barrier_orientation':orientation, 'left_right_handed_logic':direction,
        'selected_runner_pace_summary':f'{role} | SPD {round(speed_value,1)} | Pace fit {fit_band(fit)} | Pressure {pressure}',
        'map_enrichment_truth_status':'MAP_ENRICHMENT_AVAILABLE',
        'map_enrichment_source':'edgeiq_live_runner_board_governed_v1.csv|edgeiq_race_shape_fallback_engine_v1.csv',
        'pricing_maths_changed':'NO','v6_1_changed':'NO','v7_2g2_maths_changed':'NO',
    }
    rows.append(row)

fields=list(rows[0].keys()) if rows else []
write_csv(OUT,rows,fields)
summary=[{
    'generated_at':datetime.now().isoformat(timespec='seconds'),
    'status':'MAP_ENRICHMENT_FEED_V1_BUILT',
    'rows':len(rows), 'races':len(byrace),
    'projected_speed_available':sum(1 for r in rows if populated(r['projected_speed'])),
    'projected_speed_derived':sum(1 for r in rows if r['projected_speed_truth_status']=='DERIVED_TRANSPARENT_FALLBACK'),
    'pace_fit_available':sum(1 for r in rows if populated(r['pace_fit'])),
    'run_style_available':sum(1 for r in rows if populated(r['run_style'])),
    'race_shape_available':sum(1 for r in rows if populated(r['race_shape'])),
    'pricing_maths_changed':'NO','v6_1_changed':'NO','v7_2g2_maths_changed':'NO',
}]
write_csv(SUMMARY,summary,list(summary[0].keys()))
race_rows=[]
for rk,members in sorted(byrace.items()):
    out_members=[r for r in rows if (clean(r['race_date']),clean_track(r['track']),race_no(r['race_no']))==rk]
    race_rows.append({'race_date':rk[0],'track':rk[1],'race_no':rk[2],'field_size':len(members),'map_rows':len(out_members),'projected_speed_available':sum(1 for r in out_members if populated(r['projected_speed'])),'pace_fit_available':sum(1 for r in out_members if populated(r['pace_fit'])),'run_style_available':sum(1 for r in out_members if populated(r['run_style'])),'status':'OK' if len(out_members)==len(members) else 'ROW_COUNT_MISMATCH'})
write_csv(AUDIT,race_rows,list(race_rows[0].keys()))
REPORT.write_text('\n'.join([
    'EDGEiQ MAP Enrichment Feed V1', '='*34,
    f'Generated: {datetime.now().isoformat(timespec="seconds")}',
    'Status: MAP_ENRICHMENT_FEED_V1_BUILT',
    f'Rows/races: {len(rows)}/{len(byrace)}',
    f'Projected speed available: {summary[0]["projected_speed_available"]}/{len(rows)}',
    f'Projected speed transparent fallback: {summary[0]["projected_speed_derived"]}/{len(rows)}',
    f'Pace fit available: {summary[0]["pace_fit_available"]}/{len(rows)}',
    f'Run style available: {summary[0]["run_style_available"]}/{len(rows)}',
    'Pricing maths changed: NO', 'V6.1 changed: NO', 'V7.2G2 maths changed: NO',
])+'\n',encoding='utf-8')
print('MAP_ENRICHMENT_FEED_V1_BUILT')
print(f'rows={len(rows)}')
print(f'races={len(byrace)}')
print(f'pace_fit_available={summary[0]["pace_fit_available"]}')
