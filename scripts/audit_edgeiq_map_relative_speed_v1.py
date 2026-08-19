import csv, re, statistics
from collections import defaultdict, Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
IN=DATA/'edgeiq_map_enrichment_feed_v2.csv'
OUT=DATA/'edgeiq_map_relative_speed_audit_v1.csv'
SUM=DATA/'edgeiq_map_relative_speed_audit_v1_summary.csv'
REP=DATA/'edgeiq_map_relative_speed_audit_v1_report.txt'
def clean(v): return str(v or '').strip()
def n(v):
    m=re.search(r'-?\d+(?:\.\d+)?',clean(v)); return float(m.group(0)) if m else None
def leader_cap(fs): return 2 if fs<=8 else 3 if fs<=12 else 4
rows=list(csv.DictReader(open(IN,encoding='utf-8-sig',newline='')))
g=defaultdict(list)
for r in rows: g[(r['race_date'],r['track'],r['race_no'])].append(r)
out=[]; counts=Counter(); race_bad=0
examples=[]
for race,grp in g.items():
    vals=[]
    for r in grp:
        sp=n(r.get('early_speed_rating_display')) or n(r.get('projected_speed_display')) or n(r.get('early_speed_rating')) or 0
        vals.append((sp,r))
    vals.sort(key=lambda x:-x[0])
    top=vals[0][0] if vals else 0
    fs=len(vals); cap=leader_cap(fs); current_leaders=sum(1 for _,r in vals if clean(r.get('run_style_display')).upper()=='LEADER')
    speed_cluster=sum(1 for sp,_ in vals if top-sp<=3)
    race_flags=[]
    if current_leaders>cap and current_leaders>speed_cluster: race_flags.append('TOO_MANY_LEADERS')
    if current_leaders>=max(6,fs//2): race_flags.append('BAD_RELATIVE_MAP')
    if race_flags: race_bad+=1; examples.append((race,fs,current_leaders,cap,speed_cluster))
    for rank,(sp,r) in enumerate(vals,1):
        gap=top-sp; pct=(fs-rank)/(fs-1) if fs>1 else 1
        style=clean(r.get('run_style_display')).upper(); flags=list(race_flags)
        if style=='LEADER' and gap>7: flags.append('SLOW_LEADER')
        if style=='LEADER' and gap>3 and rank>cap: flags.append('LEADER_GAP_TOO_BIG')
        if style=='ON PACE' and gap>12: flags.append('ON_PACE_GAP_TOO_BIG')
        if style=='LEADER' and rank>cap and gap>3: flags.append('SPEED_RANK_STYLE_MISMATCH')
        if style in {'MIDFIELD','BACKMARKER'} and rank<=2 and gap<=3: flags.append('SPEED_RANK_STYLE_MISMATCH')
        issue=';'.join(dict.fromkeys(flags)) if flags else 'OK'
        for f in dict.fromkeys(flags): counts[f]+=1
        out.append({'race_date':race[0],'track':race[1],'race_no':race[2],'horse':r.get('horse',''),'field_size':fs,'speed':sp,'speed_rank':rank,'speed_gap_to_top':round(gap,3),'speed_percentile':round(pct,3),'current_run_style_display':style,'current_speed_map_bucket_display':r.get('speed_map_bucket_display',''),'leader_cap':cap,'current_leader_count':current_leaders,'top_speed_cluster_within_3':speed_cluster,'issue':issue})
with OUT.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
summary=[('rows',len(rows)),('races',len(g)),('races_with_relative_speed_issue',race_bad),('audit_issue_rows',sum(1 for r in out if r['issue']!='OK'))]
for k,v in counts.most_common(): summary.append((k,v))
summary += [('pricing_maths_changed','NO'),('v6_1_changed','NO'),('v7_2g2_changed','NO'),('status','MAP_RELATIVE_SPEED_AUDIT_COMPLETE')]
with SUM.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows({'metric':k,'value':v} for k,v in summary)
lines=['EDGEiQ MAP RELATIVE SPEED AUDIT V1']+[f'{k}={v}' for k,v in summary]
for race,fs,cl,cap,cluster in examples[:8]: lines.append(f'example={race} field={fs} current_leaders={cl} cap={cap} clustered={cluster}')
REP.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines))
