import csv, re
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public/data'
LIVE=DATA/'edgeiq_live_runner_board_v1.csv'; GOV=DATA/'edgeiq_live_runner_board_governed_v1.csv'
OUT=DATA/'edgeiq_governed_board_missing_races_v1.csv'; SUM=DATA/'edgeiq_governed_board_missing_races_v1_summary.csv'; REPORT=DATA/'edgeiq_governed_board_missing_races_v1_report.txt'
def read(path):
    with path.open('r',newline='',encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return list(r)
def rno(v):
    m=re.search(r'\d+',str(v or '')); return m.group(0) if m else str(v or '').strip()
def key(r): return (str(r.get('race_date') or r.get('meeting_date') or '').strip(), str(r.get('track','')).strip().upper(), rno(r.get('race_no')))
def group(rows):
    g={}
    for r in rows: g.setdefault(key(r),[]).append(r)
    return g
live=read(LIVE); gov=read(GOV); lg=group(live); gg=group(gov)
allkeys=sorted(set(lg)|set(gg))
out=[]
for k in allkeys:
    status='PRESENT_BOTH'
    if k in lg and k not in gg: status='MISSING_FROM_GOVERNED'
    elif k in gg and k not in lg: status='EXTRA_IN_GOVERNED'
    out.append({'race_date':k[0],'track':k[1],'race_no':k[2],'live_rows':len(lg.get(k,[])),'governed_rows':len(gg.get(k,[])),'status':status})
missing=[r for r in out if r['status']=='MISSING_FROM_GOVERNED']; extra=[r for r in out if r['status']=='EXTRA_IN_GOVERNED']
status='MISSING_RACES_FOUND' if missing else 'NO_MISSING_RACES'
summary=[{'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'live_rows':len(live),'governed_rows':len(gov),'live_races':len(lg),'governed_races':len(gg),'missing_races':len(missing),'missing_runner_rows':sum(int(r['live_rows']) for r in missing),'extra_races':len(extra),'extra_runner_rows':sum(int(r['governed_rows']) for r in extra),'missing_race_keys':'|'.join([f"{r['race_date']} {r['track']} R{r['race_no']} ({r['live_rows']})" for r in missing])}]
for p,data in [(OUT,out),(SUM,summary)]:
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0].keys())); w.writeheader(); w.writerows(data)
report=['EDGEiQ Governed Board Missing Races Audit V1','='*54,f"Status: {status}",f"Live rows/races: {len(live)} / {len(lg)}",f"Governed rows/races: {len(gov)} / {len(gg)}",f"Missing races: {len(missing)}",f"Extra races: {len(extra)}",'','Missing races:']
for r in missing: report.append(f"- {r['race_date']} {r['track']} R{r['race_no']}: live_rows={r['live_rows']} governed_rows=0")
report.append(''); report.append('Extra governed races:')
for r in extra: report.append(f"- {r['race_date']} {r['track']} R{r['race_no']}: governed_rows={r['governed_rows']} live_rows=0")
REPORT.write_text('\n'.join(report)+'\n',encoding='utf-8')
print(status); print('missing',len(missing),'extra',len(extra),'missing_rows',summary[0]['missing_runner_rows'])
