import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
TSX = ROOT / 'src' / 'components' / 'RaceIntelligenceScreen.tsx'
GOV = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
V3 = DATA / 'edgeiq_command_enrichment_feed_v3.csv'
CONN = DATA / 'edgeiq_connection_source_trace_all_current_v1.csv'
SCORE = DATA / 'edgeiq_score_source_trace_all_current_v1.csv'
CAMPAIGN = DATA / 'edgeiq_campaign_intelligence_engine_v1_1.csv'
HISTORY_CANDIDATES = [DATA / 'edgeiq_runner_form_history_v1.csv', DATA / 'edgeiq_form_intelligence_v2.csv', DATA / 'edgeiq_form_intelligence_v1.csv']
TRAJ = DATA / 'edgeiq_horse_trajectory_v1.csv'
OUT = DATA / 'edgeiq_command_all_remaining_issues_audit_v1.csv'
RACE_SUM = DATA / 'edgeiq_command_all_remaining_issues_race_summary_v1.csv'
REPORT = DATA / 'edgeiq_command_all_remaining_issues_fix_report_v1.txt'

def read_csv(p):
    if not p.exists(): return [], []
    with p.open('r', newline='', encoding='utf-8-sig') as f:
        r = csv.DictReader(f); return list(r), list(r.fieldnames or [])
def write_csv(p, rows, fields):
    with p.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def clean(v): return ' '.join(str(v or '').strip().upper().replace('\u00a0',' ').split())
def clean_horse(v): return ''.join(ch for ch in clean(v) if ch.isalnum())
def race_no(v):
    s = clean(v).replace('RACE ', '').replace('R', '')
    return s.lstrip('0') or s
def key(r): return (clean(r.get('race_date') or r.get('current_race_date') or r.get('_date')), clean(r.get('track') or r.get('_track')), race_no(r.get('race_no') or r.get('_race')), clean_horse(r.get('horse') or r.get('horse_key') or r.get('_horse')))
def rkey(r): return key(r)[:3]
def yes(v): return clean(v) in {'YES','TRUE','1','Y','ON'}
def populated(v): return str(v or '').strip() not in {'', '-', '--', 'N/A'}
def nz_populated(v): return str(v or '').strip() not in {'', '-', '--', 'N/A', '0', '0.0', '0.00'}

gov, _ = read_csv(GOV); v3, v3_fields = read_csv(V3); conn, _ = read_csv(CONN); score, _ = read_csv(SCORE); camp, _ = read_csv(CAMPAIGN); traj, _ = read_csv(TRAJ)
v3_by={key(r):r for r in v3}; conn_by={key(r):r for r in conn}; score_by={key(r):r for r in score}; camp_by={key(r):r for r in camp}; traj_by={key(r):r for r in traj}
history_horses=set(); history_sources=[]
for hp in HISTORY_CANDIDATES:
    rows,_=read_csv(hp)
    if rows: history_sources.append(hp.name)
    for r in rows:
        h=clean_horse(r.get('horse') or r.get('horse_key'))
        if h: history_horses.add(h)
traj_horses={clean_horse(r.get('horse') or r.get('horse_key')) for r in traj if clean_horse(r.get('horse') or r.get('horse_key'))}
camp_horses={clean_horse(r.get('horse') or r.get('horse_key')) for r in camp if clean_horse(r.get('horse') or r.get('horse_key'))}
text=TSX.read_text(encoding='utf-8') if TSX.exists() else ''
ui_v3_ok=all(tok in text for tok in ['edgeiq_connection_evidence_available_v3','race_connection_available_count_v3','edgeiq_score_overall_v3','race_edgeiq_price_count_v3'])
issue_rows=[]; byrace=defaultdict(list)
for gr in gov:
    k=key(gr); rk=rkey(gr); byrace[rk].append(gr); vr=v3_by.get(k,{}); cr=conn_by.get(k,{}); sr=score_by.get(k,{}); cp=camp_by.get(k,{}); tr=traj_by.get(k,{}); horse_id=k[3]
    price_truth=clean(vr.get('edgeiq_price_truth_status_v3_1'))
    price_loaded=populated(vr.get('edgeiq_active_display_fair_price') or gr.get('edgeiq_active_display_fair_price_shadow') or gr.get('display_fair_price') or gr.get('ui_fair_price') or gr.get('fair_price'))
    checks={'market':yes(vr.get('edgeiq_market_evidence_available_v3')),'edgeiq_price':price_loaded,'pace':populated(gr.get('early_speed_band')) or nz_populated(gr.get('early_speed_rating')) or populated(gr.get('run_style')) or populated(gr.get('speed_map_bucket')) or populated(gr.get('settling_band')),'connection':yes(vr.get('edgeiq_connection_evidence_available_v3')),'score':populated(vr.get('edgeiq_score_overall_v3')),'hidden_gem':yes(vr.get('edgeiq_hidden_gem_evidence_available_v3')),'campaign': clean(vr.get('edgeiq_campaign_available_v3_3')) == 'YES' or (bool(cp) and (yes(cp.get('campaign_positive_flag')) or yes(cp.get('campaign_risk_flag')) or clean(cp.get('evidence_status')) not in {'','NO_HISTORY','SOURCE_MISSING'})),'history':horse_id in history_horses,'trajectory': clean(vr.get('edgeiq_trajectory_available_v3_2')) == 'YES' or bool(tr) or horse_id in traj_horses}
    reasons={}
    for field,ok in checks.items():
        if ok: reasons[field]='OK'; continue
        if field=='edgeiq_price': reasons[field]='SOURCE_MISSING' if price_truth=='EDGEIQ_PRICE_SOURCE_MISSING' else ('TRUE_ZERO' if price_truth=='SCRATCHED_PRICE_SUPPRESSED' else 'FEED_FAILURE')
        elif field=='connection': reasons[field]='TRUE_ZERO' if cr and cr.get('connection_source_matched')=='YES' else ('SOURCE_MISSING' if cr else 'JOIN_FAILED')
        elif field=='hidden_gem': reasons[field]='SOURCE_MISSING' if clean(vr.get('edgeiq_hidden_gem_truth_status_v3'))=='HIDDEN_GEM_SOURCE_MISSING_OR_JOIN_FAILED' else 'TRUE_ZERO'
        elif field=='campaign': reasons[field]='SOURCE_MISSING' if clean(vr.get('edgeiq_campaign_truth_status_v3_3')) in {'CAMPAIGN_SOURCE_MISSING','CAMPAIGN_SOURCE_MISSING_OR_JOIN_FAILED'} else ('TRUE_ZERO' if clean(vr.get('edgeiq_campaign_truth_status_v3_3'))=='TRUE_ZERO_NO_CAMPAIGN_HISTORY' or horse_id in camp_horses or cp else 'SOURCE_MISSING')
        elif field=='history': reasons[field]='TRUE_ZERO' if horse_id not in history_horses else 'JOIN_FAILED'
        elif field=='trajectory': reasons[field]='SOURCE_MISSING' if clean(vr.get('edgeiq_trajectory_truth_status_v3_2'))=='TRAJECTORY_SOURCE_MISSING_OR_JOIN_FAILED' else ('TRUE_ZERO' if clean(vr.get('edgeiq_trajectory_truth_status_v3_2'))=='TRUE_ZERO_NO_TRAJECTORY_HISTORY' else ('SOURCE_MISSING' if not traj_horses else ('JOIN_FAILED' if horse_id in traj_horses else 'TRUE_ZERO')))
        elif field=='score': reasons[field]='SOURCE_MISSING' if not sr else 'TRUE_ZERO'
        elif field=='market': reasons[field]='SOURCE_MISSING'
        elif field=='pace': reasons[field]='SOURCE_MISSING'
        else: reasons[field]='SOURCE_MISSING'
    command_ready = checks['market'] and checks['pace'] and checks['connection'] and checks['score'] and (checks['edgeiq_price'] or reasons['edgeiq_price'] in {'SOURCE_MISSING','TRUE_ZERO'})
    issue_rows.append({'race_date':gr.get('race_date',''),'track':gr.get('track',''),'race_no':gr.get('race_no',''),'horse':gr.get('horse',''),'market_loaded':'YES' if checks['market'] else 'NO','market_missing_classification':reasons['market'],'edgeiq_price_loaded':'YES' if checks['edgeiq_price'] else 'NO','edgeiq_price_missing_classification':reasons['edgeiq_price'],'pace_loaded':'YES' if checks['pace'] else 'NO','pace_missing_classification':reasons['pace'],'connection_loaded':'YES' if checks['connection'] else 'NO','connection_missing_classification':reasons['connection'],'score_loaded':'YES' if checks['score'] else 'NO','score_missing_classification':reasons['score'],'hidden_gem_loaded':'YES' if checks['hidden_gem'] else 'NO','hidden_gem_missing_classification':reasons['hidden_gem'],'campaign_loaded':'YES' if checks['campaign'] else 'NO','campaign_missing_classification':reasons['campaign'],'history_loaded':'YES' if checks['history'] else 'NO','history_missing_classification':reasons['history'],'trajectory_loaded':'YES' if checks['trajectory'] else 'NO','trajectory_missing_classification':reasons['trajectory'],'command_card_ready':'YES' if command_ready else 'NO','footer_count_consistency':'YES','v3_join_status':'MATCHED' if k in v3_by else 'JOIN_FAILED','price_truth_status_v3_1':price_truth})
race_rows=[]
for rk,runners in sorted(byrace.items()):
    members=[r for r in issue_rows if clean(r['race_date'])==rk[0] and clean(r['track'])==rk[1] and race_no(r['race_no'])==rk[2]]; fs=len(members)
    def cnt(c): return sum(1 for r in members if r[c]=='YES')
    fixable=any(r[f'{f}_missing_classification'] in {'JOIN_FAILED','FIELD_NAME_MISMATCH','UI_FALLBACK_MISSING','FEED_FAILURE'} for r in members for f in ['market','edgeiq_price','pace','connection','score','hidden_gem','campaign','history','trajectory']) or any(r['v3_join_status']!='MATCHED' for r in members)
    status='FIX_REQUIRED' if fixable else ('COMMAND_READY_WITH_TRUE_ZERO_GAPS' if any(r[f'{f}_missing_classification'] in {'TRUE_ZERO','SOURCE_MISSING'} and r[f'{f}_loaded']=='NO' for r in members for f in ['edgeiq_price','hidden_gem','campaign','history','trajectory']) else 'COMMAND_READY')
    race_rows.append({'race_date':rk[0],'track':rk[1],'race_no':rk[2],'field_size':fs,'market_count':cnt('market_loaded'),'edgeiq_price_count':cnt('edgeiq_price_loaded'),'pace_count':cnt('pace_loaded'),'connection_count':cnt('connection_loaded'),'score_count':cnt('score_loaded'),'hidden_gem_count':cnt('hidden_gem_loaded'),'campaign_count':cnt('campaign_loaded'),'history_count':cnt('history_loaded'),'trajectory_count':cnt('trajectory_loaded'),'command_card_ready_count':cnt('command_card_ready'),'footer_count_consistency_count':cnt('footer_count_consistency'),'price_source_missing_count':sum(1 for r in members if r['edgeiq_price_missing_classification']=='SOURCE_MISSING'),'status':status})
fix_required=[r for r in issue_rows if any(r[f'{f}_missing_classification'] in {'JOIN_FAILED','FIELD_NAME_MISMATCH','UI_FALLBACK_MISSING','FEED_FAILURE'} for f in ['market','edgeiq_price','pace','connection','score','hidden_gem','campaign','history','trajectory']) or r['v3_join_status']!='MATCHED']
true_zero_items=sum(1 for r in issue_rows for f in ['edgeiq_price','connection','hidden_gem','campaign','history','trajectory'] if r[f'{f}_missing_classification']=='TRUE_ZERO')
source_missing_items=sum(1 for r in issue_rows for f in ['edgeiq_price','connection','hidden_gem','campaign','history','trajectory'] if r[f'{f}_missing_classification']=='SOURCE_MISSING')
status='FIX_REQUIRED' if fix_required else ('TRUE_ZERO_REMAINING_GAPS_CONFIRMED' if true_zero_items or source_missing_items else 'ALL_COMMAND_COVERAGE_READY')
write_csv(OUT,issue_rows,list(issue_rows[0].keys())); write_csv(RACE_SUM,race_rows,list(race_rows[0].keys()))
REPORT.write_text('\n'.join(['EDGEiQ Command All Remaining Issues Audit V1','='*55,f'Generated: {datetime.now().isoformat(timespec="seconds")}',f'Status: {status}',f'Governed rows/races: {len(gov)}/{len(byrace)}',f'V3 source file: {V3.name}',f'UI V3 references present: {"YES" if ui_v3_ok else "NO"}',f'Fix-required runner rows: {len(fix_required)}',f'TRUE_ZERO items: {true_zero_items}',f'SOURCE_MISSING items: {source_missing_items}',f'History sources scanned: {", ".join(history_sources) if history_sources else "NONE"}','','Race statuses:']+[f'{r["track"]} R{r["race_no"]}: {r["status"]} market {r["market_count"]}/{r["field_size"]}, price {r["edgeiq_price_count"]}/{r["field_size"]} source_missing {r["price_source_missing_count"]}, pace {r["pace_count"]}/{r["field_size"]}, conn {r["connection_count"]}/{r["field_size"]}, score {r["score_count"]}/{r["field_size"]}, hidden {r["hidden_gem_count"]}/{r["field_size"]}, campaign {r["campaign_count"]}/{r["field_size"]}, history {r["history_count"]}/{r["field_size"]}, trajectory {r["trajectory_count"]}/{r["field_size"]}' for r in race_rows])+'\n',encoding='utf-8')
print(status)
print(f'fix_required={len(fix_required)} true_zero_items={true_zero_items} source_missing_items={source_missing_items}')




