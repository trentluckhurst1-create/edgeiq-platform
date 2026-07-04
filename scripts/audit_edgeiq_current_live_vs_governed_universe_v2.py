import csv,re
from pathlib import Path
from datetime import datetime
D=Path('public/data'); LIVE=D/'edgeiq_live_runner_board_v1.csv'; GOV=D/'edgeiq_live_runner_board_governed_v1.csv'
OUT=D/'edgeiq_current_live_vs_governed_universe_v2.csv'; SUM=D/'edgeiq_current_live_vs_governed_universe_v2_summary.csv'; REP=D/'edgeiq_current_live_vs_governed_universe_v2_report.txt'
def read(p):
 with p.open('r',newline='',encoding='utf-8-sig') as f: r=csv.DictReader(f); return list(r)
def rn(v):
 m=re.search(r'\d+',str(v or '')); return m.group(0) if m else str(v or '').strip()
def rk(r): return (str(r.get('race_date') or r.get('meeting_date') or '').strip(),str(r.get('track','')).strip().upper(),rn(r.get('race_no')))
def rowk(r): return rk(r)+(str(r.get('horse') or r.get('horse_name') or '').strip().upper(),)
live=read(LIVE); gov=read(GOV); lr={}; gr={}
for r in live: lr.setdefault(rk(r),[]).append(r)
for r in gov: gr.setdefault(rk(r),[]).append(r)
rows=[]
for k in sorted(set(lr)|set(gr)):
 st='OVERLAP'
 if k in lr and k not in gr: st='LIVE_ONLY'
 if k in gr and k not in lr: st='GOVERNED_ONLY'
 rows.append({'race_date':k[0],'track':k[1],'race_no':k[2],'live_rows':len(lr.get(k,[])),'governed_rows':len(gr.get(k,[])),'status':st})
live_only=[r for r in rows if r['status']=='LIVE_ONLY']; gov_only=[r for r in rows if r['status']=='GOVERNED_ONLY']; overlap=[r for r in rows if r['status']=='OVERLAP']
caul=('2026-06-27','CAULFIELD','7')
status='UNIVERSE_MATCH' if not live_only and not gov_only and len(live)==len(gov) else 'GOVERNED_UNIVERSE_STALE_REBUILD_REQUIRED'
s=[{'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'live_rows':len(live),'governed_rows':len(gov),'live_races':len(lr),'governed_races':len(gr),'live_only_races':len(live_only),'governed_only_races':len(gov_only),'overlapping_races':len(overlap),'live_only_runner_rows':sum(int(x['live_rows']) for x in live_only),'governed_only_runner_rows':sum(int(x['governed_rows']) for x in gov_only),'caulfield_r7_live_present':'YES' if caul in lr else 'NO','caulfield_r7_governed_present':'YES' if caul in gr else 'NO'}]
for p,data in [(OUT,rows),(SUM,s)]:
 with p.open('w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=list(data[0].keys())); w.writeheader(); w.writerows(data)
REP.write_text('\n'.join(['EDGEiQ Current Live vs Governed Universe V2','='*52,f"Status: {status}",f"Live rows/races: {len(live)} / {len(lr)}",f"Governed rows/races: {len(gov)} / {len(gr)}",f"Live-only races/rows: {len(live_only)} / {s[0]['live_only_runner_rows']}",f"Governed-only races/rows: {len(gov_only)} / {s[0]['governed_only_runner_rows']}",f"CAULFIELD R7 live/governed: {s[0]['caulfield_r7_live_present']} / {s[0]['caulfield_r7_governed_present']}"])+'\n',encoding='utf-8')
print(status, s[0])
