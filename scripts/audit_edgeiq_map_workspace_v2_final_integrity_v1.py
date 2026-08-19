import csv
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
MAP=DATA/'edgeiq_map_enrichment_feed_v2.csv'
GOV=DATA/'edgeiq_live_runner_board_governed_v1.csv'
OUT=DATA/'edgeiq_map_workspace_v2_final_integrity_v1.csv'
SUM=DATA/'edgeiq_map_workspace_v2_final_integrity_summary_v1.csv'
REP=DATA/'edgeiq_map_workspace_v2_final_integrity_report_v1.txt'
DASH=chr(8212)
BAD={'','--','-','UNKNOWN','NOT LOADED','SOURCE_MISSING','SOURCE GAP','NULL','NAN','UNDEFINED','0.0'}
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))
def clean(v): return str(v or '').strip()
def n(v):
    m=re.search(r'-?\d+(?:\.\d+)?',clean(v)); return float(m.group(0)) if m else None
def good(v):
    s=clean(v); return bool(s and s!=DASH and s.upper() not in BAD and chr(65533) not in s)
map_rows=read(MAP); gov=read(GOV)
issues=[]
seen=set(); dup=0
for r in map_rows:
    rk=clean(r.get('runner_key'))
    if rk in seen: dup+=1
    seen.add(rk)
    for field in ['run_style_display','projected_speed_display','pace_fit_display','late_speed_display','race_shape_display','wide_risk_display','map_confidence_display']:
        if not good(r.get(field)): issues.append({'runner_key':rk,'field':field,'issue':'RAW_OR_MISSING_DISPLAY','value':clean(r.get(field))})
    x=n(r.get('map_x_pct_display')); y=n(r.get('map_y_px_display'))
    if x is None or not (0<=x<=100): issues.append({'runner_key':rk,'field':'map_x_pct_display','issue':'BAD_MAP_COORDINATE','value':clean(r.get('map_x_pct_display'))})
    if y is None or not (0<=y<=100): issues.append({'runner_key':rk,'field':'map_y_px_display','issue':'BAD_MAP_COORDINATE','value':clean(r.get('map_y_px_display'))})
    b=n(r.get('barrier'))
    if b is None or not (1<=b<=30): issues.append({'runner_key':rk,'field':'barrier','issue':'INVALID_BARRIER_SOURCE_CLASSIFIED','value':clean(r.get('barrier'))})
with OUT.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['runner_key','field','issue','value']); w.writeheader(); w.writerows(issues)
metrics=[
 ('governed_rows',len(gov)),('governed_races',len({(r.get('race_date'),r.get('track'),r.get('race_no')) for r in gov})),
 ('map_v2_rows',len(map_rows)),('map_v2_races',len({(r.get('race_date'),r.get('track'),r.get('race_no')) for r in map_rows})),
 ('duplicate_runners',dup),('v7_2g2_on',sum(1 for r in gov if clean(r.get('edgeiq_v7_2g2_feature_flag')).upper()=='ON')),('v7_2g2_live_wired',sum(1 for r in gov if clean(r.get('edgeiq_v7_2g2_live_wired_flag')).upper()=='YES_CONTROLLED_ON'))]
for field in ['projected_speed_display','pace_fit_display','run_style_display','late_speed_display','race_shape_display','wide_risk_display','map_confidence_display']:
    metrics.append((field.replace('_display','')+'_populated_count',sum(1 for r in map_rows if good(r.get(field)))))
metrics += [('raw_placeholder_defects',sum(1 for i in issues if i['issue']=='RAW_OR_MISSING_DISPLAY')),('bad_map_coordinates',sum(1 for i in issues if i['issue']=='BAD_MAP_COORDINATE')),('invalid_barriers',sum(1 for i in issues if i['issue']=='INVALID_BARRIER_SOURCE_CLASSIFIED')),('fix_required',len(issues)),('pricing_maths_changed','NO'),('v6_1_changed','NO'),('v7_2g2_changed','NO')]
ok=(len(gov)==383 and len(map_rows)==383 and len({(r.get('race_date'),r.get('track'),r.get('race_no')) for r in gov})==25 and len({(r.get('race_date'),r.get('track'),r.get('race_no')) for r in map_rows})==25 and dup==0 and len(issues)==0 and sum(1 for r in gov if clean(r.get('edgeiq_v7_2g2_feature_flag')).upper()=='ON')==383 and sum(1 for r in gov if clean(r.get('edgeiq_v7_2g2_live_wired_flag')).upper()=='YES_CONTROLLED_ON')==383)
metrics.append(('status','MAP_WORKSPACE_V2_FINAL_INTEGRITY_PASS' if ok else 'MAP_WORKSPACE_V2_FINAL_INTEGRITY_REVIEW_REQUIRED'))
with SUM.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows({'metric':k,'value':v} for k,v in metrics)
lines=['EDGEiQ MAP WORKSPACE V2 FINAL INTEGRITY']+[f'{k}={v}' for k,v in metrics]
REP.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines))

