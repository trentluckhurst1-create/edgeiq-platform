import csv
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
GOV = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
CMD = DATA / 'edgeiq_command_enrichment_feed_v2.csv'
OUT = DATA / 'edgeiq_post_fresh_current_visual_data_v1.csv'
SUMMARY = DATA / 'edgeiq_post_fresh_current_visual_data_v1_summary.csv'
REPORT = DATA / 'edgeiq_post_fresh_current_visual_data_v1_report.txt'

def read_csv(path):
    if not path.exists(): return [], []
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        r = csv.DictReader(f); return list(r), list(r.fieldnames or [])

def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)

def clean(v): return ' '.join(str(v or '').strip().upper().replace('\u00a0',' ').split())
def clean_horse(v): return ''.join(ch for ch in clean(v) if ch.isalnum())
def race_no(v):
    s = clean(v).replace('RACE ', '').replace('R','')
    return s.lstrip('0') or s
def rkey(r): return (clean(r.get('race_date') or r.get('current_race_date')), clean(r.get('track')), race_no(r.get('race_no')))
def runner_key(r): return (clean(r.get('race_date') or r.get('current_race_date')), clean(r.get('track')), race_no(r.get('race_no')), clean_horse(r.get('horse') or r.get('horse_key')))
def yes(v): return clean(v) in {'YES','TRUE','1','Y','ON'}
def populated(v): return str(v or '').strip() not in {'', '0', '0.0', '0.00'}

gov, _ = read_csv(GOV)
cmd, _ = read_csv(CMD)
caulfield = ('2026-06-27','CAULFIELD','7')
g_rows = [r for r in gov if rkey(r) == caulfield]
c_rows = [r for r in cmd if rkey(r) == caulfield]
cmd_by_key = {runner_key(r): r for r in c_rows}
rows = []
for r in g_rows:
    cr = cmd_by_key.get(runner_key(r), {})
    pace_fields = [r.get('run_style',''), r.get('speed_map_bucket',''), r.get('settling_band',''), r.get('early_speed_band','')]
    pace_mapped = any(str(v or '').strip() for v in pace_fields)
    score_loaded = any(str(cr.get(f,'')).strip() for f in ['edgeiq_score_overall_v2','edgeiq_score_distance_v2','edgeiq_score_condition_v2','edgeiq_score_class_v2','edgeiq_score_campaign_v2','edgeiq_score_pace_v2','edgeiq_score_connections_v2','edgeiq_score_market_v2','edgeiq_score_confidence_v2'])
    rows.append({
        'race_date': r.get('race_date',''), 'track': r.get('track',''), 'race_no': r.get('race_no',''), 'horse': r.get('horse',''),
        'market_available': 'YES' if yes(cr.get('edgeiq_market_evidence_available_v2') or r.get('edgeiq_market_evidence_available')) else 'NO',
        'connection_available': 'YES' if yes(cr.get('edgeiq_connection_evidence_available_v2') or r.get('edgeiq_connection_evidence_available')) else 'NO',
        'hidden_gem_available': 'YES' if yes(cr.get('edgeiq_hidden_gem_evidence_available_v2') or r.get('edgeiq_hidden_gem_evidence_available')) else 'NO',
        'edgeiq_price_available': 'YES' if populated(r.get('edgeiq_active_display_fair_price_shadow') or r.get('edgeiq_active_display_fair_price') or r.get('display_fair_price') or r.get('ui_fair_price')) else 'NO',
        'pace_mapped': 'YES' if pace_mapped else 'NO',
        'pace_source_fields': '|'.join(str(v or '') for v in pace_fields),
        'score_loaded': 'YES' if score_loaded else 'NO',
        'command_field_size': cr.get('race_field_size_v2',''),
        'command_market_count': cr.get('race_market_count_v2',''),
        'command_connection_count': cr.get('race_connection_count_v2',''),
        'command_hidden_gem_count': cr.get('race_hidden_gem_count_v2',''),
        'command_score_count': cr.get('race_score_breakdown_count_v2',''),
    })
field_size = len(g_rows)
market_count = sum(1 for r in rows if r['market_available'] == 'YES')
connection_count = sum(1 for r in rows if r['connection_available'] == 'YES')
hidden_count = sum(1 for r in rows if r['hidden_gem_available'] == 'YES')
price_count = sum(1 for r in rows if r['edgeiq_price_available'] == 'YES')
pace_count = sum(1 for r in rows if r['pace_mapped'] == 'YES')
score_count = sum(1 for r in rows if r['score_loaded'] == 'YES')
if field_size == 19 and market_count == 19 and price_count == 19 and score_count == 19 and pace_count > 0:
    status = 'CAULFIELD_R7_VISUAL_DATA_READY'
elif field_size == 19 and market_count == 19 and price_count == 19 and score_count == 19:
    status = 'CAULFIELD_R7_PARTIAL_DATA_READY'
else:
    status = 'CAULFIELD_R7_STILL_BROKEN'
summary = {
    'status': status,
    'generated_at': datetime.now().isoformat(timespec='seconds'),
    'race_date': '2026-06-27', 'track': 'CAULFIELD', 'race_no': '7',
    'rows': field_size,
    'market_count': market_count,
    'connection_count': connection_count,
    'hidden_gem_count': hidden_count,
    'edgeiq_price_count': price_count,
    'pace_mapped_count': pace_count,
    'score_rows': score_count,
    'command_rows': len(c_rows),
    'production_changed': 'NO',
}
fields = list(rows[0].keys()) if rows else ['race_date','track','race_no','horse']
write_csv(OUT, rows, fields)
write_csv(SUMMARY, [summary], list(summary.keys()))
REPORT.write_text('\n'.join(['EDGEiQ Post Fresh Current Visual Data Audit V1','='*50,f'Status: {status}',f'CAULFIELD R7 rows: {field_size}',f'Market count: {market_count}/{field_size}',f'Connections count: {connection_count}/{field_size}',f'Hidden Gem count: {hidden_count}/{field_size}',f'EDGEiQ Price count: {price_count}/{field_size}',f'Pace mapped count: {pace_count}/{field_size}',f'Score rows: {score_count}/{field_size}',f'Command rows: {len(c_rows)}','Production changed: NO']) + '\n', encoding='utf-8')
print(status)
