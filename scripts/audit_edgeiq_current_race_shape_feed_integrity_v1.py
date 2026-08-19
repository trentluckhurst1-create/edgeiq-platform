import csv, re
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public/data'
BOARD=DATA/'edgeiq_live_runner_board_governed_v1.csv'
OUT=DATA/'edgeiq_current_race_shape_feed_integrity_v1.csv'; SUM=DATA/'edgeiq_current_race_shape_feed_integrity_v1_summary.csv'; REPORT=DATA/'edgeiq_current_race_shape_feed_integrity_v1_report.txt'
SOURCES=['edgeiq_live_runner_style_v2.csv','edgeiq_live_runner_style_v1.csv','live_speed_map_v3.csv','edgeiq_tactical_dna_speed_map_v2.csv','edgeiq_runner_intelligence_v1.csv','edgeiq_race_shape_intelligence_v1.csv','edgeiq_race_shape_engine_v2.csv','edgeiq_race_shape_fallback_engine_v1.csv']
def read(path):
    if not path.exists(): return [], []
    with path.open('r',newline='',encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return r.fieldnames or [], list(r)
def norm(s): return re.sub(r'[^a-z0-9]+','',str(s or '').lower())
def rno(s):
    m=re.search(r'\d+',str(s or '')); return m.group(0) if m else str(s or '').strip()
def first(r,keys):
    for k in keys:
        if k in r and str(r.get(k,'')).strip(): return str(r.get(k)).strip()
    return ''
def race_key(r): return (first(r,['race_date','meeting_date','current_race_date','date']), first(r,['track']), rno(first(r,['race_no','race_number','race'])))
def runner_key(r): return race_key(r)+(norm(first(r,['horse','horse_name','runner_name','horse_key'])),)
def style_bucket(row):
    vals=[first(row,['dominant_run_style','run_style','settling_band','speed_map_bucket','map_style','speed_map_label','historic_speed_bucket','memory_projected_map_style'])]
    u=' '.join(vals).upper().replace('-','_').replace(' ','_')
    if not u or u in {'NO_PROFILE','FIRST_START','UNKNOWN','--'}: return ''
    if 'LEADER' in u or 'FRONT' in u: return 'LEADER'
    if 'ONPACE' in u or 'ON_PACE' in u or 'PROMINENT' in u or 'PRESser'.upper() in u: return 'ON_PACE'
    if 'MID' in u: return 'MIDFIELD'
    if 'BACK' in u or 'CLOSER' in u or 'LATE' in u: return 'BACKMARKER'
    return ''
board_cols, board=read(BOARD)
races={}
for r in board: races.setdefault(race_key(r),[]).append(r)
source_data=[]
for name in SOURCES:
    cols, rows=read(DATA/name)
    if not rows: continue
    idx={}
    race_idx={}
    for row in rows:
        idx.setdefault(runner_key(row),[]).append(row)
        race_idx.setdefault(race_key(row),[]).append(row)
    source_data.append((name,cols,idx,race_idx,rows))
out=[]
for rk, runners in sorted(races.items()):
    field=len(runners)
    best=None
    for name,cols,idx,race_idx,rows in source_data:
        matched=[]; buckets=[]
        for br in runners:
            k=runner_key(br)
            row=(idx.get(k) or [None])[0]
            if row:
                matched.append(row); buckets.append(style_bucket(row))
        mapped=sum(1 for b in buckets if b)
        rec={'source':name,'matched':len(matched),'mapped':mapped,'leaders':buckets.count('LEADER'),'on_pace':buckets.count('ON_PACE'),'midfield':buckets.count('MIDFIELD'),'backmarkers':buckets.count('BACKMARKER')}
        if best is None or (rec['mapped'],rec['matched'])>(best['mapped'],best['matched']): best=rec
    if not best: best={'source':'NONE','matched':0,'mapped':0,'leaders':0,'on_pace':0,'midfield':0,'backmarkers':0}
    unmapped=field-best['mapped']
    if not source_data: status='PACE_SOURCE_MISSING'
    elif best['matched']==0 or (field and best['mapped']==0): status='PACE_JOIN_FAILURE'
    else: status='PACE_FEED_OK'
    out.append({'race_date':rk[0],'track':rk[1],'race_no':rk[2],'field_size':field,'best_source':best['source'],'source_matched_runners':best['matched'],'mapped_runners':best['mapped'],'leaders':best['leaders'],'on_pace':best['on_pace'],'midfield':best['midfield'],'backmarkers':best['backmarkers'],'unmapped_runners':unmapped,'status':status})
field19=[r for r in out if int(r['field_size'])==19]
problem=[r for r in out if int(r['field_size'])==19 and r['status']!='PACE_FEED_OK'] or [r for r in out if int(r['field_size'])==19] or [r for r in out if r['status']!='PACE_FEED_OK']
focus=problem[0] if problem else (out[0] if out else {})
summary=[{'status':focus.get('status','PACE_SOURCE_MISSING'),'generated_at':datetime.now().isoformat(timespec='seconds'),'races_audited':len(out),'field_19_races':len(field19),'focus_race':'|'.join([focus.get('race_date',''),focus.get('track',''),focus.get('race_no','')]),'field_size':focus.get('field_size',''),'mapped_runners':focus.get('mapped_runners',''),'unmapped_runners':focus.get('unmapped_runners',''),'leaders':focus.get('leaders',''),'on_pace':focus.get('on_pace',''),'midfield':focus.get('midfield',''),'backmarkers':focus.get('backmarkers',''),'best_source':focus.get('best_source',''),'source_files_tested':'|'.join([s[0] for s in source_data])}]
for p,data in [(OUT,out),(SUM,summary)]:
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0].keys())); w.writeheader(); w.writerows(data)
report=['EDGEiQ Current Race Shape Feed Integrity V1','='*52,f"Status: {summary[0]['status']}",f"Focus race: {summary[0]['focus_race']}",f"Field size: {summary[0]['field_size']}",f"Mapped/unmapped: {summary[0]['mapped_runners']} / {summary[0]['unmapped_runners']}",f"Leaders/on pace/midfield/backmarkers: {summary[0]['leaders']} / {summary[0]['on_pace']} / {summary[0]['midfield']} / {summary[0]['backmarkers']}",f"Best source: {summary[0]['best_source']}",'','Field-19 races:']
for r in field19: report.append(f"- {r['race_date']} {r['track']} R{r['race_no']}: status={r['status']}; source={r['best_source']}; mapped={r['mapped_runners']}/{r['field_size']}; L/OP/M/B={r['leaders']}/{r['on_pace']}/{r['midfield']}/{r['backmarkers']}")
REPORT.write_text('\n'.join(report)+'\n',encoding='utf-8')
print(summary[0]['status']); print(summary[0])
