import csv
import shutil
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
MAP=DATA/'edgeiq_map_enrichment_feed_v2.csv'
TARGETS=[(DATA/'edgeiq_live_runner_board_v1.csv',DATA/'edgeiq_live_runner_board_v1_MAP_V2_BACKUP_20260629.csv'),(DATA/'edgeiq_live_runner_board_governed_v1.csv',DATA/'edgeiq_live_runner_board_governed_v1_MAP_V2_BACKUP_20260629.csv')]
OUT=DATA/'edgeiq_map_v2_runner_board_apply_v1.csv'
SUM=DATA/'edgeiq_map_v2_runner_board_apply_v1_summary.csv'
REP=DATA/'edgeiq_map_v2_runner_board_apply_v1_report.txt'
def clean(v): return str(v or '').strip()
def norm(v): return re.sub(r'[^A-Z0-9]+','',clean(v).upper())
def ctrack(v): return re.sub(r'\s+',' ',clean(v).upper())
def key(row): return (clean(row.get('race_date') or row.get('current_race_date')),ctrack(row.get('track')),clean(row.get('race_no')),norm(row.get('horse_key') or row.get('horse')))
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:
        r=csv.DictReader(f); return list(r), list(r.fieldnames or [])
map_rows,map_cols=read(MAP)
by_rk={clean(r.get('runner_key')):r for r in map_rows if clean(r.get('runner_key'))}
by_key={key(r):r for r in map_rows}
apply_cols=[c for c in map_cols if c not in {'race_date','track','race_no','horse'}]
report=[]; summaries=[]
for target,backup in TARGETS:
    rows,cols=read(target)
    if not backup.exists(): shutil.copyfile(target,backup)
    for c in apply_cols:
        if c not in cols: cols.append(c)
    matched=0; missing=0
    for row in rows:
        m=by_rk.get(clean(row.get('runner_key'))) or by_key.get(key(row))
        if not m:
            missing+=1; continue
        matched+=1
        for c in apply_cols: row[c]=m.get(c,'')
    with target.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    races=len({(r.get('race_date'),r.get('track'),r.get('race_no')) for r in rows})
    report.append({'target_file':target.name,'rows':len(rows),'races':races,'matched_rows':matched,'missing_rows':missing,'backup':backup.name})
    summaries += [(target.name+'_rows',len(rows)),(target.name+'_races',races),(target.name+'_matched_rows',matched),(target.name+'_missing_rows',missing)]
with OUT.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['target_file','rows','races','matched_rows','missing_rows','backup']); w.writeheader(); w.writerows(report)
summaries += [('pricing_maths_changed','NO'),('v6_1_changed','NO'),('v7_2g2_changed','NO'),('status','MAP_V2_RUNNER_BOARD_APPLIED' if all(r['missing_rows']==0 for r in report) else 'MAP_V2_RUNNER_BOARD_APPLY_REVIEW_REQUIRED')]
with SUM.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows({'metric':k,'value':v} for k,v in summaries)
lines=['EDGEiQ MAP V2 RUNNER BOARD APPLY']+[f'{k}={v}' for k,v in summaries]
REP.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines))
