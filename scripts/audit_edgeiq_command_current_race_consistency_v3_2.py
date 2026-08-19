import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
GOV=DATA/'edgeiq_live_runner_board_governed_v1.csv'
CMD=DATA/'edgeiq_command_enrichment_feed_v3.csv'
OUT=DATA/'edgeiq_command_current_race_consistency_v3_2.csv'
SUMMARY=DATA/'edgeiq_command_current_race_consistency_v3_2_summary.csv'
REPORT=DATA/'edgeiq_command_current_race_consistency_v3_2_report.txt'

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
def key(r): return (clean(r.get('race_date') or r.get('current_race_date')), clean(r.get('track')), race_no(r.get('race_no')), clean_horse(r.get('horse') or r.get('horse_key')))
def rkey(r): return key(r)[:3]
def yes(v): return clean(v) in {'YES','TRUE','1','Y','ON'}
def populated(v): return str(v or '').strip() not in {'','-','--','N/A'}

gov,_=read_csv(GOV); cmd,fields=read_csv(CMD); cmd_by={key(r):r for r in cmd}
byrace=defaultdict(list)
for r in gov: byrace[rkey(r)].append(r)
rows=[]
for rk, members in sorted(byrace.items()):
    side=[cmd_by.get(key(r),{}) for r in members]
    fs=len(members)
    pace=sum(1 for r in members if populated(r.get('early_speed_band')) or populated(r.get('early_speed_rating')) or populated(r.get('run_style')))
    market=sum(1 for s in side if yes(s.get('edgeiq_market_evidence_available_v3')))
    conn=sum(1 for s in side if yes(s.get('edgeiq_connection_evidence_available_v3')))
    score=sum(1 for s in side if populated(s.get('edgeiq_score_overall_v3')))
    hidden=sum(1 for s in side if yes(s.get('edgeiq_hidden_gem_evidence_available_v3')))
    price=sum(1 for s in side if populated(s.get('edgeiq_active_display_fair_price')))
    traj=sum(1 for s in side if yes(s.get('edgeiq_trajectory_available_v3_2')))
    traj_no=sum(1 for s in side if clean(s.get('edgeiq_trajectory_truth_status_v3_2'))=='TRUE_ZERO_NO_TRAJECTORY_HISTORY')
    traj_miss=sum(1 for s in side if clean(s.get('edgeiq_trajectory_truth_status_v3_2'))=='TRAJECTORY_SOURCE_MISSING_OR_JOIN_FAILED')
    status='COMMAND_READY'
    if market==0 or pace==0 or conn==0 or score==0 or traj+traj_no != fs or traj_miss:
        status='FEED_FAILURE'
    elif traj_no or price<fs or hidden<fs:
        status='COMMAND_READY_WITH_TRUE_ZERO_GAPS'
    rows.append({'race_date':rk[0],'track':rk[1],'race_no':rk[2],'field_size':fs,'pace_mapped_count':pace,'market_count':market,'connection_count':conn,'score_count':score,'hidden_gem_count':hidden,'edgeiq_price_count':price,'trajectory_count':traj,'trajectory_no_history_count':traj_no,'trajectory_source_missing_count':traj_miss,'status':status})
fail=sum(1 for r in rows if r['status']=='FEED_FAILURE')
summary={'status':'COMMAND_V3_2_CONSISTENCY_PASS' if fail==0 else 'COMMAND_V3_2_CONSISTENCY_FAIL','generated_at':datetime.now().isoformat(timespec='seconds'),'races':len(rows),'feed_failure_races':fail,'trajectory_rows':sum(int(r['trajectory_count']) for r in rows),'trajectory_no_history_rows':sum(int(r['trajectory_no_history_count']) for r in rows),'trajectory_source_missing_rows':sum(int(r['trajectory_source_missing_count']) for r in rows),'pricing_math_changed':'NO','v6_1_changed':'NO','v7_2g2_changed':'NO'}
write_csv(OUT,rows,list(rows[0].keys())); write_csv(SUMMARY,[summary],list(summary.keys()))
REPORT.write_text('\n'.join(['EDGEiQ Command Current Race Consistency V3.2','='*52,f'Status: {summary["status"]}',f'Races: {summary["races"]}',f'Feed failure races: {fail}',f'Trajectory usable/no-history/source-missing: {summary["trajectory_rows"]}/{summary["trajectory_no_history_rows"]}/{summary["trajectory_source_missing_rows"]}','Pricing maths changed: NO','V6.1 changed: NO','V7.2G2 changed: NO','']+[f'{r["track"]} R{r["race_no"]}: {r["status"]} trajectory {r["trajectory_count"]}/{r["field_size"]}, no-history {r["trajectory_no_history_count"]}, source-missing {r["trajectory_source_missing_count"]}' for r in rows])+'\n',encoding='utf-8')
print(summary['status'])
