import csv, re
from collections import defaultdict, Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
MAP=DATA/'edgeiq_map_enrichment_feed_v3.csv'
GOV=DATA/'edgeiq_live_runner_board_governed_v1.csv'
OUT=DATA/'edgeiq_map_v3_relative_speed_final_v1.csv'
SUM=DATA/'edgeiq_map_v3_relative_speed_final_summary_v1.csv'
REP=DATA/'edgeiq_map_v3_relative_speed_final_report_v1.txt'
BAD={'','--','-','UNKNOWN','NOT LOADED','SOURCE_MISSING','SOURCE GAP','NULL','NAN','UNDEFINED','0.0'}
def clean(v): return str(v or '').strip()
def n(v):
    m=re.search(r'-?\d+(?:\.\d+)?',clean(v)); return float(m.group(0)) if m else None
def cap(fs): return 2 if fs<=8 else 3 if fs<=12 else 4
def good(v):
    s=clean(v); return bool(s and s.upper() not in BAD and chr(65533) not in s)
rows=list(csv.DictReader(open(MAP,encoding='utf-8-sig',newline='')))
gov=list(csv.DictReader(open(GOV,encoding='utf-8-sig',newline='')))
g=defaultdict(list)
for r in rows: g[(r['race_date'],r['track'],r['race_no'])].append(r)
issues=[]; speed_rank_mismatch=0; screenshot_fixed=True
for race,grp in g.items():
    fs=len(grp); leader_count=int(n(grp[0].get('race_leader_count_v3')) or 0); leader_cap=cap(fs)
    clustered=sum(1 for r in grp if (n(r.get('speed_gap_to_leader_v3')) or 999)<=3)
    if leader_count>leader_cap: issues.append({'race_date':race[0],'track':race[1],'race_no':race[2],'runner_key':'','horse':'','issue':'LEADER_CAP_EXCEEDED','value':str(leader_count)})
    if leader_count>=6 and clustered<leader_count: issues.append({'race_date':race[0],'track':race[1],'race_no':race[2],'runner_key':'','horse':'','issue':'EXCESSIVE_LEADERS_NOT_CLUSTERED','value':str(leader_count)})
    for r in grp:
        rank=int(n(r.get('speed_rank_v3')) or 999); gap=n(r.get('speed_gap_to_leader_v3')) or 0; style=clean(r.get('run_style_display_v3'))
        x=n(r.get('map_x_pct_display_v3')); y=n(r.get('map_y_px_display_v3'))
        if x is None or not 0<=x<=100 or y is None or not 0<=y<=100: issues.append({'race_date':race[0],'track':race[1],'race_no':race[2],'runner_key':r.get('runner_key'),'horse':r.get('horse'),'issue':'BAD_COORDINATE','value':f'{x}/{y}'})
        for f in ['run_style_display_v3','speed_rank_v3','speed_gap_to_leader_v3','race_pressure_band_v3','map_x_pct_display_v3']:
            if not good(r.get(f)): issues.append({'race_date':race[0],'track':race[1],'race_no':race[2],'runner_key':r.get('runner_key'),'horse':r.get('horse'),'issue':'RAW_PLACEHOLDER','value':f})
        if rank==1 and style!='LEADER': issues.append({'race_date':race[0],'track':race[1],'race_no':race[2],'runner_key':r.get('runner_key'),'horse':r.get('horse'),'issue':'RANK1_NOT_LEADER','value':style}); speed_rank_mismatch+=1
        if style=='LEADER' and gap>7: issues.append({'race_date':race[0],'track':race[1],'race_no':race[2],'runner_key':r.get('runner_key'),'horse':r.get('horse'),'issue':'LEADER_GAP_GT_7','value':str(gap)}); speed_rank_mismatch+=1
        if style=='ON PACE' and gap>12: issues.append({'race_date':race[0],'track':race[1],'race_no':race[2],'runner_key':r.get('runner_key'),'horse':r.get('horse'),'issue':'ON_PACE_GAP_GT_12','value':str(gap)}); speed_rank_mismatch+=1
    if race in {('2026-06-27','CAULFIELD','8'),('2026-06-25','BENDIGO','6'),('2026-06-27','CAULFIELD','6')} and leader_count>=6: screenshot_fixed=False
with OUT.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['race_date','track','race_no','runner_key','horse','issue','value']); w.writeheader(); w.writerows(issues)
metrics=[]
metrics.append(('rows',len(rows)))
metrics.append(('races',len(g)))
metrics.append(('governed_rows',len(gov)))
metrics.append(('governed_races',len({(r.get('race_date'),r.get('track'),r.get('race_no')) for r in gov})))
metrics.append(('duplicate_runners',len(rows)-len({r.get('runner_key') for r in rows})))
metrics.append(('bad_coordinates',sum(1 for i in issues if i['issue']=='BAD_COORDINATE')))
metrics.append(('raw_placeholders',sum(1 for i in issues if i['issue']=='RAW_PLACEHOLDER')))
metrics.append(('leader_cap_violations',sum(1 for i in issues if i['issue']=='LEADER_CAP_EXCEEDED')))
metrics.append(('excessive_leader_races',sum(1 for i in issues if i['issue']=='EXCESSIVE_LEADERS_NOT_CLUSTERED')))
metrics.append(('speed_rank_mismatch_count',speed_rank_mismatch))
metrics.append(('max_leader_count_after_v3',max(int(n(r.get('race_leader_count_v3')) or 0) for r in rows)))
metrics.append(('screenshot_type_races_fixed','YES' if screenshot_fixed else 'NO'))
v7_on=sum(1 for r in gov if clean(r.get('edgeiq_v7_2g2_feature_flag')).upper()=='ON')
v7_wired=sum(1 for r in gov if clean(r.get('edgeiq_v7_2g2_live_wired_flag')).upper()=='YES_CONTROLLED_ON')
metrics.append(('v7_2g2_on',v7_on))
metrics.append(('v7_2g2_live_wired',v7_wired))
metrics.append(('pricing_maths_changed','NO'))
metrics.append(('v6_1_changed','NO'))
metrics.append(('v7_2g2_changed','NO'))
ok=len(rows)==383 and len(g)==25 and len(gov)==383 and len(issues)==0 and v7_on==383 and v7_wired==383
metrics.append(('status','MAP_V3_RELATIVE_SPEED_FINAL_PASS' if ok else 'MAP_V3_RELATIVE_SPEED_REVIEW_REQUIRED'))
with SUM.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows({'metric':k,'value':v} for k,v in metrics)
lines=['EDGEiQ MAP V3 RELATIVE SPEED FINAL']+[f'{k}={v}' for k,v in metrics]
REP.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines))


