import csv, re, shutil
from collections import defaultdict, Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
V2=DATA/'edgeiq_map_enrichment_feed_v2.csv'
GOV=DATA/'edgeiq_live_runner_board_governed_v1.csv'
OUT=DATA/'edgeiq_map_enrichment_feed_v3.csv'
SUM=DATA/'edgeiq_map_enrichment_feed_v3_summary.csv'
AUD=DATA/'edgeiq_map_enrichment_feed_v3_audit.csv'
REP=DATA/'edgeiq_map_enrichment_feed_v3_report.txt'
DASH=chr(8212)
def clean(v): return str(v or '').strip()
def n(v):
    m=re.search(r'-?\d+(?:\.\d+)?',clean(v)); return float(m.group(0)) if m else None
def fmt(x,d=1): return f'{float(x):.{d}f}'.rstrip('0').rstrip('.')
def cap(fs): return 2 if fs<=8 else 3 if fs<=12 else 4
def clamp(x,lo,hi): return max(lo,min(hi,x))
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:
        r=csv.DictReader(f); return list(r),list(r.fieldnames or [])
def speed(r): return n(r.get('early_speed_rating_display')) or n(r.get('projected_speed_display')) or n(r.get('early_speed_rating')) or 0.0
def pressure_band(leaders,onpace,fs,top_cluster):
    score=min(100, leaders*22+onpace*8+top_cluster*6+max(0,fs-10)*1.5)
    band='HIGH PRESSURE' if (leaders>=3 and top_cluster>=3) or score>=70 else 'MODERATE PRESSURE' if score>=45 else 'TACTICAL'
    return score,band
def advantage(band,leaders): return 'LATE RUNNERS' if band=='HIGH PRESSURE' else 'LEADER ADVANTAGE' if band=='TACTICAL' and leaders<=2 else 'BALANCED'
rows,cols=read(V2); gov,_=read(GOV)
g=defaultdict(list)
for r in rows: g[(r['race_date'],r['track'],r['race_no'])].append(r)
out=[]; audit=[]; corrected=0; before_after=[]
for race,grp in g.items():
    vals=sorted([(speed(r),i,r) for i,r in enumerate(grp)], key=lambda x:(-x[0],x[1]))
    fs=len(vals); top=vals[0][0] if vals else 0; leader_cap=cap(fs)
    # Candidate leaders: top 2 or within 3 points, then cap.
    leader_indices=[]
    for rank,(sp,orig_i,r) in enumerate(vals,1):
        if rank<=2 or top-sp<=3: leader_indices.append(orig_i)
    leader_indices=leader_indices[:leader_cap]
    # Ensure top-ranked always leader.
    if vals and vals[0][1] not in leader_indices: leader_indices=[vals[0][1]]+leader_indices[:leader_cap-1]
    styles={}
    for rank,(sp,orig_i,r) in enumerate(vals,1):
        gap=top-sp
        if orig_i in leader_indices and gap<=7: style='LEADER'
        elif gap<=8 or rank<=leader_cap+3: style='ON PACE'
        elif rank <= max(leader_cap+3, int(round(fs*0.72))) and gap<=25: style='MIDFIELD'
        else: style='BACKMARKER'
        if gap>12 and style=='ON PACE': style='MIDFIELD'
        styles[orig_i]=(style,rank,gap,(fs-rank)/(fs-1) if fs>1 else 1)
    counts=Counter(v[0] for v in styles.values())
    top_cluster=sum(1 for sp,_,_ in vals if top-sp<=3)
    pscore,pband=pressure_band(counts['LEADER'],counts['ON PACE'],fs,top_cluster)
    adv=advantage(pband,counts['LEADER'])
    summary=f"{counts['LEADER']} true leader(s), {counts['ON PACE']} on pace, {counts['MIDFIELD']} midfield, {counts['BACKMARKER']} backmarker(s)."
    verdict=(f"High-pressure relative map: {counts['LEADER']} close leader(s) with {counts['ON PACE']} pressing behind." if pband=='HIGH PRESSURE' else f"Tactical relative map: {counts['LEADER']} true leader(s), so control may sit with the front group." if pband=='TACTICAL' else f"Moderate relative map: the first speed group is defined but pressure remains balanced.")
    before=sum(1 for r in grp if clean(r.get('run_style_display')).upper()=='LEADER'); after=counts['LEADER']
    if before!=after: corrected+=1
    before_after.append((race,fs,before,after,top_cluster))
    for sp,orig_i,r in vals:
        style,rank,gap,pct=styles[orig_i]
        rr=dict(r)
        # x: lower means further forward. Similar speeds cluster but gap matters.
        x=clamp(8 + min(78, gap*3.2 + (rank-1)*1.15),4,96)
        y=n(r.get('map_y_px_display'))
        y=clamp(y if y is not None else 50,8,94)
        old_style=clean(r.get('run_style_display')).upper()
        rr.update({
            'speed_rank_v3':str(rank),'speed_gap_to_leader_v3':fmt(gap,1),'speed_percentile_v3':fmt(pct,3),
            'relative_speed_band_v3':'TOP_SPEED' if gap<=3 else 'FORWARD_SPEED' if gap<=8 else 'MID_SPEED' if gap<=20 else 'LOW_SPEED',
            'run_style_display_v3':style,'speed_map_bucket_display_v3':style,'settling_band_display_v3':style,
            'map_x_pct_display_v3':fmt(x,1),'map_y_px_display_v3':fmt(y,1),
            'race_leader_count_v3':str(counts['LEADER']),'race_on_pace_count_v3':str(counts['ON PACE']),'race_midfield_count_v3':str(counts['MIDFIELD']),'race_backmarker_count_v3':str(counts['BACKMARKER']),
            'race_pressure_score_v3':fmt(pscore,0),'race_pressure_band_v3':pband,'race_shape_summary_v3':summary,'race_shape_verdict_v3':verdict,
            'pace_advantage_display_v3':adv,'map_confidence_display_v3':clean(r.get('map_confidence_display')) or 'HIGH',
            'relative_speed_adjustment_v3':'UNCHANGED' if old_style==style else f'{old_style}_TO_{style}',
            'relative_speed_source_v3':'RACE_RELATIVE_SPEED_RANK_GAP',
            'pricing_maths_changed':'NO','v6_1_changed':'NO','v7_2g2_changed':'NO'
        })
        out.append(rr)
        if style=='LEADER' and gap>7: audit.append({'runner_key':r.get('runner_key'),'issue':'LEADER_GAP_GT_7','value':fmt(gap,1)})
        if style=='ON PACE' and gap>12: audit.append({'runner_key':r.get('runner_key'),'issue':'ON_PACE_GAP_GT_12','value':fmt(gap,1)})
        if rank==1 and style!='LEADER': audit.append({'runner_key':r.get('runner_key'),'issue':'RANK1_NOT_LEADER','value':style})
# Preserve columns and append V3.
newcols=list(cols)
for r in out:
    for c in r:
        if c not in newcols: newcols.append(c)
with OUT.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=newcols,extrasaction='ignore'); w.writeheader(); w.writerows(out)
with AUD.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['runner_key','issue','value']); w.writeheader(); w.writerows(audit)
max_after=max(int(r['race_leader_count_v3']) for r in out)
summary=[('rows',len(out)),('races',len(g)),('duplicate_runner_keys',len(out)-len({r['runner_key'] for r in out})),('audit_issues',len(audit)),('races_corrected',corrected),('max_leader_count_v3',max_after),('v7_2g2_on',sum(1 for r in gov if clean(r.get('edgeiq_v7_2g2_feature_flag')).upper()=='ON')),('v7_2g2_live_wired',sum(1 for r in gov if clean(r.get('edgeiq_v7_2g2_live_wired_flag')).upper()=='YES_CONTROLLED_ON'))]
for fld in ['speed_rank_v3','speed_gap_to_leader_v3','run_style_display_v3','map_x_pct_display_v3','race_pressure_band_v3']:
    summary.append((fld+'_populated',sum(1 for r in out if clean(r.get(fld)))))
summary += [('pricing_maths_changed','NO'),('v6_1_changed','NO'),('v7_2g2_changed','NO'),('status','MAP_ENRICHMENT_FEED_V3_BUILT' if not audit else 'MAP_ENRICHMENT_FEED_V3_REVIEW_REQUIRED')]
with SUM.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows({'metric':k,'value':v} for k,v in summary)
lines=['EDGEiQ MAP ENRICHMENT FEED V3']+[f'{k}={v}' for k,v in summary]
for race,fs,b,a,cl in sorted(before_after,key=lambda x:-(x[2]-x[3]))[:8]: lines.append(f'leader_example={race} field={fs} before={b} after={a} close_cluster={cl}')
REP.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines))

