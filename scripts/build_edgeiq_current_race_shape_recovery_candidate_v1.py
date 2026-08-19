import csv, re
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public/data'
LEGACY=DATA/'edgeiq_live_runner_board_v1.csv'; GOV=DATA/'edgeiq_live_runner_board_governed_v1.csv'
OUT=DATA/'edgeiq_current_race_shape_recovery_candidate_v1.csv'; SUM=DATA/'edgeiq_current_race_shape_recovery_candidate_v1_summary.csv'; AUD=DATA/'edgeiq_current_race_shape_recovery_candidate_v1_audit.csv'; REPORT=DATA/'edgeiq_current_race_shape_recovery_candidate_v1_report.txt'
SOURCES=[('CURRENT_PACE_MAP','live_speed_map_v3.csv'),('CURRENT_RUN_STYLE','edgeiq_live_runner_style_v2.csv'),('HISTORICAL_RUN_STYLE','edgeiq_live_runner_style_v1.csv'),('RUNNER_INTELLIGENCE','edgeiq_runner_intelligence_v1.csv'),('PROJECTED_ARCHETYPE','edgeiq_horse_archetype_engine_v1.csv')]
def read(path):
    if not path.exists(): return [], []
    with path.open('r',newline='',encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return r.fieldnames or [], list(r)
def write(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
def norm(s): return re.sub(r'[^a-z0-9]+','',str(s or '').lower())
def rno(s):
    m=re.search(r'\d+',str(s or '')); return m.group(0) if m else str(s or '').strip()
def first(r,keys):
    for k in keys:
        if k in r and str(r.get(k,'')).strip(): return str(r.get(k)).strip()
    return ''
def race_key(r): return (first(r,['race_date','meeting_date','current_race_date','date']),first(r,['track']),rno(first(r,['race_no','race_number','race'])))
def runner_key(r): return race_key(r)+(norm(first(r,['horse','horse_name','runner_name','horse_key'])),)
def horse_key(r): return norm(first(r,['horse','horse_name','runner_name','horse_key']))
def style(row):
    s=' '.join([first(row,['speed_map_bucket','dominant_run_style','run_style','settling_band','map_style','speed_map_label','horse_archetype','distance_profile'])]).upper().replace('-','_').replace(' ','_')
    if not s or s in {'NO_PROFILE','UNKNOWN','FIRST_START'}: return ''
    if 'LEADER' in s or 'FRONT' in s or 'SPEED' in s: return 'LEADER'
    if 'ONPACE' in s or 'ON_PACE' in s or 'PROMINENT' in s or 'PRESS' in s: return 'ON_PACE'
    if 'MID' in s or 'MILER' in s: return 'MIDFIELD'
    if 'BACK' in s or 'CLOSER' in s or 'LATE' in s or 'STAYER' in s: return 'BACKMARKER'
    return ''
# identify field 19 legacy race
lcols,lrows=read(LEGACY); gcols,grows=read(GOV)
races={}
for r in lrows: races.setdefault(race_key(r),[]).append(r)
field19=[(rk,rs) for rk,rs in races.items() if len(rs)==19]
if not field19:
    field19=sorted(races.items(), key=lambda x:-len(x[1]))[:1]
focus_rk, runners=field19[0]
# build source indexes
source_indexes=[]
for label,name in SOURCES:
    cols,rows=read(DATA/name)
    idx={}; hidx={}
    for r in rows:
        idx.setdefault(runner_key(r),[]).append(r)
        hk=horse_key(r)
        if hk: hidx.setdefault(hk,[]).append(r)
    source_indexes.append((label,name,idx,hidx))
out=[]; audit=[]
for br in runners:
    recovered='UNKNOWN'; source='FALLBACK_UNKNOWN'; source_file=''; matched='NO'
    for label,name,idx,hidx in source_indexes:
        candidates=idx.get(runner_key(br),[])
        # projected archetype is horse-only by design
        if not candidates and label=='PROJECTED_ARCHETYPE': candidates=hidx.get(horse_key(br),[])
        for c in candidates[:3]:
            st=style(c)
            if st:
                recovered=st; source=label; source_file=name; matched='YES'; break
        if matched=='YES': break
    out.append({**br,'recovered_speed_map_bucket_v1':recovered,'race_shape_recovery_source_v1':source,'race_shape_recovery_source_file_v1':source_file,'race_shape_recovery_status_v1':'RECOVERED' if recovered!='UNKNOWN' else 'UNKNOWN'})
    audit.append({'race_date':focus_rk[0],'track':focus_rk[1],'race_no':focus_rk[2],'horse':first(br,['horse']),'recovered_bucket':recovered,'source':source,'source_file':source_file,'status':'RECOVERED' if recovered!='UNKNOWN' else 'UNKNOWN'})
leaders=sum(1 for r in out if r['recovered_speed_map_bucket_v1']=='LEADER'); onp=sum(1 for r in out if r['recovered_speed_map_bucket_v1']=='ON_PACE'); mid=sum(1 for r in out if r['recovered_speed_map_bucket_v1']=='MIDFIELD'); back=sum(1 for r in out if r['recovered_speed_map_bucket_v1']=='BACKMARKER'); unknown=sum(1 for r in out if r['recovered_speed_map_bucket_v1']=='UNKNOWN')
status='RACE_SHAPE_RECOVERY_READY_FOR_REVIEW' if len(out)-unknown>0 else 'RACE_SHAPE_SOURCE_MISSING'
summary=[{'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'race':'|'.join(focus_rk),'field_size':len(out),'mapped_runners':len(out)-unknown,'unmapped_runners':unknown,'recovered_leaders':leaders,'recovered_on_pace':onp,'recovered_midfield':mid,'recovered_backmarkers':back,'source_breakdown':'|'.join(sorted(set(r['race_shape_recovery_source_v1'] for r in out)))}]
write(OUT,out); write(AUD,audit); write(SUM,summary)
report=['EDGEiQ Current Race Shape Recovery Candidate V1','='*56,f"Status: {status}",f"Race: {summary[0]['race']}",f"Field size: {len(out)}",f"Mapped/unmapped: {len(out)-unknown} / {unknown}",f"Recovered leaders/on pace/midfield/backmarkers: {leaders} / {onp} / {mid} / {back}",f"Source breakdown: {summary[0]['source_breakdown']}",'','Candidate only. Governed live board not overwritten.']
REPORT.write_text('\n'.join(report)+'\n',encoding='utf-8')
print(status); print(summary[0])
