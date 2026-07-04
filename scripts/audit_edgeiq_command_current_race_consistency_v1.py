import csv, re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'; TSX=ROOT/'src'/'components'/'RaceIntelligenceScreen.tsx'
GOV=DATA/'edgeiq_live_runner_board_governed_v1.csv'; V3=DATA/'edgeiq_command_enrichment_feed_v3.csv'
OUT=DATA/'edgeiq_command_current_race_consistency_v1.csv'; SUMMARY=DATA/'edgeiq_command_current_race_consistency_v1_summary.csv'; REPORT=DATA/'edgeiq_command_current_race_consistency_v1_report.txt'

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
def yes(v): return clean(v) in {'YES','TRUE','1','Y','ON'}
def populated(v): return str(v or '').strip() not in {'','0','0.0','0.00','-'}

gov,gf=read_csv(GOV); v3,vf=read_csv(V3); v3_by={key(r):r for r in v3}; byrace=defaultdict(list)
for r in gov: byrace[rkey(r)].append(r)
text=TSX.read_text(encoding='utf-8')
ui_v3_refs=sum(1 for token in ['edgeiq_connection_evidence_available_v3','race_connection_available_count_v3','edgeiq_score_overall_v3','command_best_value_summary_v3','race_edgeiq_price_count_v3'] if token in text)
rows=[]
for rk, rs in sorted(byrace.items()):
    members=[v3_by.get(key(r),{}) for r in rs]
    field_size=len(rs)
    pace=sum(1 for r in rs if populated(r.get('early_speed_band')) or populated(r.get('run_style')) or populated(r.get('speed_map_bucket')) or populated(r.get('settling_band')))
    market=sum(1 for m in members if yes(m.get('edgeiq_market_evidence_available_v3')))
    conn=sum(1 for m in members if yes(m.get('edgeiq_connection_evidence_available_v3')))
    conn_src=sum(1 for m in members if clean(m.get('edgeiq_connection_truth_status_v3'))!='SOURCE_MISSING_OR_JOIN_FAILED' and m)
    hidden=sum(1 for m in members if yes(m.get('edgeiq_hidden_gem_evidence_available_v3')))
    price=sum(1 for m in members if populated(m.get('edgeiq_active_display_fair_price')))
    score=sum(1 for m in members if populated(m.get('edgeiq_score_overall_v3')))
    status='COMMAND_READY'
    if len(members)!=field_size or market==0 or price==0 or pace==0 or score==0 or conn_src==0:
        status='FEED_FAILURE'
    elif conn==0 and conn_src>0:
        status='TRUE_ZERO_CONNECTIONS'
    rows.append({'race_date':rk[0],'track':rk[1],'race_no':rk[2],'field_size':field_size,'pace_mapped_count':pace,'market_count':market,'connection_qualifying_count':conn,'connection_source_matched_count':conn_src,'hidden_gem_count':hidden,'edgeiq_price_count':price,'score_overall_count':score,'status':status})
fail=sum(1 for r in rows if r['status']=='FEED_FAILURE'); true_zero=sum(1 for r in rows if r['status']=='TRUE_ZERO_CONNECTIONS')
caul=next((r for r in rows if r['track']=='CAULFIELD' and r['race_no']=='7'),{})
summary={'status':'COMMAND_CURRENT_RACE_CONSISTENCY_PASS' if fail==0 else 'COMMAND_CURRENT_RACE_CONSISTENCY_FAIL','generated_at':datetime.now().isoformat(timespec='seconds'),'races':len(rows),'feed_failure_races':fail,'true_zero_connection_races':true_zero,'ui_v3_reference_count':ui_v3_refs,'caulfield_r7_status':caul.get('status','MISSING'),'caulfield_r7_line':f"market {caul.get('market_count','?')}/{caul.get('field_size','?')} | edgeiq price {caul.get('edgeiq_price_count','?')}/{caul.get('field_size','?')} | pace {caul.get('pace_mapped_count','?')}/{caul.get('field_size','?')} | connections {caul.get('connection_qualifying_count','?')}/{caul.get('field_size','?')} source {caul.get('connection_source_matched_count','?')}/{caul.get('field_size','?')} | score {caul.get('score_overall_count','?')}/{caul.get('field_size','?')}"}
write_csv(OUT,rows,list(rows[0].keys())); write_csv(SUMMARY,[summary],list(summary.keys()))
REPORT.write_text('\n'.join(['EDGEiQ Command Current Race Consistency V1','='*48,f'Status: {summary["status"]}',f'Races: {len(rows)}',f'Feed failure races: {fail}',f'True-zero connection races: {true_zero}',f'UI V3 reference count: {ui_v3_refs}',f'CAULFIELD R7: {summary["caulfield_r7_line"]}', '']+[f'{r["track"]} R{r["race_no"]}: {r["status"]} market {r["market_count"]}/{r["field_size"]}, conn {r["connection_qualifying_count"]}/{r["field_size"]} source {r["connection_source_matched_count"]}/{r["field_size"]}, price {r["edgeiq_price_count"]}/{r["field_size"]}, pace {r["pace_mapped_count"]}/{r["field_size"]}, score {r["score_overall_count"]}/{r["field_size"]}' for r in rows])+'\n',encoding='utf-8')
print(summary['status'])
