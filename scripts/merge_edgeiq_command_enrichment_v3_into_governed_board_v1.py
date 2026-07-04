import csv
from pathlib import Path
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
GOV=DATA/'edgeiq_live_runner_board_governed_v1.csv'
V3=DATA/'edgeiq_command_enrichment_feed_v3.csv'
OUT=DATA/'edgeiq_live_runner_board_governed_v1_COMMAND_V3_MERGED.csv'
AUDIT=DATA/'edgeiq_command_v3_merge_v1.csv'
SUMMARY=DATA/'edgeiq_command_v3_merge_v1_summary.csv'
REPORT=DATA/'edgeiq_command_v3_merge_v1_report.txt'

def read_csv(p):
    if not p.exists(): return [],[]
    with p.open('r',newline='',encoding='utf-8-sig') as f:
        r=csv.DictReader(f); return list(r), list(r.fieldnames or [])
def write_csv(p,rows,fields):
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def clean(v): return ' '.join(str(v or '').strip().upper().replace('\u00a0',' ').split())
def clean_horse(v): return ''.join(ch for ch in clean(v) if ch.isalnum())
def race_no(v):
    s=clean(v).replace('RACE ','').replace('R','')
    return s.lstrip('0') or s
def key(r): return (clean(r.get('race_date') or r.get('current_race_date')),clean(r.get('track')),race_no(r.get('race_no')),clean_horse(r.get('horse') or r.get('horse_key')))
def rkey(r): return key(r)[:3]

gov, gf=read_csv(GOV); v3, vf=read_csv(V3); v3_by={key(r):r for r in v3}
v7_before={key(r):{k:v for k,v in r.items() if k.startswith('edgeiq_v7_2g2') or k in ['fair_price','ui_fair_price','display_fair_price','win_pct']} for r in gov}
v3_fields=[f for f in vf if f not in ['race_date','track','race_no','horse']]
out_fields=list(gf)
for f in v3_fields:
    if f not in out_fields: out_fields.append(f)
out=[]; audit=[]; matched=0
for r in gov:
    nr=dict(r); m=v3_by.get(key(r))
    if m:
        matched+=1
        for f in v3_fields: nr[f]=m.get(f,'')
    out.append(nr)
    audit.append({'race_date':r.get('race_date',''),'track':r.get('track',''),'race_no':r.get('race_no',''),'horse':r.get('horse',''),'merge_matched':'YES' if m else 'NO','merge_key':'|'.join(key(r))})
# checks
races=set(rkey(r) for r in out); duplicates=len(out)-len(set(key(r) for r in out)); caul=sum(1 for r in out if clean(r.get('track'))=='CAULFIELD' and race_no(r.get('race_no'))=='7')
v7_unchanged=all(v7_before.get(key(r),{})=={k:v for k,v in r.items() if k.startswith('edgeiq_v7_2g2') or k in ['fair_price','ui_fair_price','display_fair_price','win_pct']} for r in out)
status='COMMAND_V3_MERGE_READY' if len(out)==383 and len(races)==25 and matched==383 and duplicates==0 and caul==19 and v7_unchanged else 'COMMAND_V3_MERGE_BLOCKED'
summary={'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'rows':len(out),'races':len(races),'v3_rows':len(v3),'matched_rows':matched,'duplicate_keys':duplicates,'caulfield_r7_rows':caul,'v7_2g2_fields_unchanged':'YES' if v7_unchanged else 'NO'}
write_csv(OUT,out,out_fields); write_csv(AUDIT,audit,list(audit[0].keys())); write_csv(SUMMARY,[summary],list(summary.keys()))
REPORT.write_text('\n'.join(['EDGEiQ Command V3 Merge V1','='*30,f'Status: {status}',f'Rows/races: {len(out)}/{len(races)}',f'Matched rows: {matched}',f'Duplicates: {duplicates}',f'CAULFIELD R7 rows: {caul}',f'V7.2G2 fields unchanged: {summary["v7_2g2_fields_unchanged"]}'])+'\n',encoding='utf-8')
print(status)
