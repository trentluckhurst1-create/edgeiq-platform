import csv
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
LIVE = DATA / 'edgeiq_live_runner_board_v1.csv'
GOV = DATA / 'edgeiq_live_runner_board_governed_v7_2g2_FRESH_CURRENT_EVIDENCE_MERGED.csv'
CMD = DATA / 'edgeiq_command_enrichment_feed_v2_FRESH_CURRENT.csv'
OUT = DATA / 'edgeiq_fresh_current_governed_end_to_end_v1.csv'
SUMMARY = DATA / 'edgeiq_fresh_current_governed_end_to_end_v1_summary.csv'
REPORT = DATA / 'edgeiq_fresh_current_governed_end_to_end_v1_report.txt'
EXPECTED_ROWS = 383
EXPECTED_RACES = 25

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
def runner_key(r): return (clean(r.get('race_date') or r.get('current_race_date')), clean(r.get('track')), race_no(r.get('race_no')), clean_horse(r.get('horse') or r.get('horse_key')))
def race_key(r): return (clean(r.get('race_date') or r.get('current_race_date')), clean(r.get('track')), race_no(r.get('race_no')))
def yn(ok): return 'PASS' if ok else 'FAIL'
def yes(v): return clean(v) in {'YES','TRUE','1','Y','ON'}
def populated(v): return str(v or '').strip() != ''

live, live_fields = read_csv(LIVE)
gov, gov_fields = read_csv(GOV)
cmd, cmd_fields = read_csv(CMD)
sets = {'live': set(runner_key(r) for r in live), 'gov': set(runner_key(r) for r in gov), 'cmd': set(runner_key(r) for r in cmd)}
races = {'live': set(race_key(r) for r in live), 'gov': set(race_key(r) for r in gov), 'cmd': set(race_key(r) for r in cmd)}
caulfield_key = ('2026-06-27','CAULFIELD','7')
checks = []
def add(name, ok, detail): checks.append({'check': name, 'result': yn(ok), 'detail': str(detail)})
add('live_rows_expected', len(live) == EXPECTED_ROWS, len(live))
add('governed_rows_expected', len(gov) == EXPECTED_ROWS, len(gov))
add('command_rows_expected', len(cmd) == EXPECTED_ROWS, len(cmd))
add('live_races_expected', len(races['live']) == EXPECTED_RACES, len(races['live']))
add('governed_races_expected', len(races['gov']) == EXPECTED_RACES, len(races['gov']))
add('command_races_expected', len(races['cmd']) == EXPECTED_RACES, len(races['cmd']))
add('no_live_only_missing_in_governed', not (sets['live'] - sets['gov']), len(sets['live'] - sets['gov']))
add('no_governed_only_stale_rows', not (sets['gov'] - sets['live']), len(sets['gov'] - sets['live']))
add('no_live_only_missing_in_command', not (sets['live'] - sets['cmd']), len(sets['live'] - sets['cmd']))
add('no_command_only_stale_rows', not (sets['cmd'] - sets['live']), len(sets['cmd'] - sets['live']))
add('caulfield_r7_live_present', sum(1 for r in live if race_key(r) == caulfield_key) == 19, sum(1 for r in live if race_key(r) == caulfield_key))
add('caulfield_r7_governed_present', sum(1 for r in gov if race_key(r) == caulfield_key) == 19, sum(1 for r in gov if race_key(r) == caulfield_key))
add('caulfield_r7_command_present', sum(1 for r in cmd if race_key(r) == caulfield_key) == 19, sum(1 for r in cmd if race_key(r) == caulfield_key))
add('governed_no_duplicate_runner_keys', len(sets['gov']) == len(gov), len(gov) - len(sets['gov']))
add('command_no_duplicate_runner_keys', len(sets['cmd']) == len(cmd), len(cmd) - len(sets['cmd']))
add('v7_2g2_feature_flag_on', all(yes(r.get('edgeiq_v7_2g2_feature_flag')) for r in gov), sum(1 for r in gov if yes(r.get('edgeiq_v7_2g2_feature_flag'))))
add('v7_2g2_live_wired_yes_controlled_on', all(clean(r.get('edgeiq_v7_2g2_live_wired_flag')) == 'YES_CONTROLLED_ON' for r in gov), sum(1 for r in gov if clean(r.get('edgeiq_v7_2g2_live_wired_flag')) == 'YES_CONTROLLED_ON'))
add('active_display_populated', sum(1 for r in gov if populated(r.get('edgeiq_active_display_fair_price_shadow') or r.get('edgeiq_active_display_fair_price'))) >= EXPECTED_ROWS - 5, sum(1 for r in gov if populated(r.get('edgeiq_active_display_fair_price_shadow') or r.get('edgeiq_active_display_fair_price'))))
required_evidence = ['edgeiq_market_evidence_available','edgeiq_connection_evidence_available','edgeiq_hidden_gem_evidence_available']
add('evidence_fields_present', all(f in gov_fields for f in required_evidence), ','.join(f for f in required_evidence if f not in gov_fields) or 'all present')
required_cmd = ['race_field_size_v2','race_market_count_v2','race_connection_count_v2','race_hidden_gem_count_v2','race_score_breakdown_count_v2']
add('command_enrichment_counts_present', all(f in cmd_fields for f in required_cmd), ','.join(f for f in required_cmd if f not in cmd_fields) or 'all present')
caulfield_cmd = [r for r in cmd if race_key(r) == caulfield_key]
add('caulfield_r7_market_count_19', bool(caulfield_cmd) and all(r.get('race_market_count_v2') == '19' and r.get('race_field_size_v2') == '19' for r in caulfield_cmd), caulfield_cmd[0].get('race_market_count_v2') if caulfield_cmd else 'missing')
failed = [c for c in checks if c['result'] != 'PASS']
status = 'FRESH_CURRENT_END_TO_END_PASS' if not failed else 'FRESH_CURRENT_END_TO_END_BLOCKED'
summary = {
    'status': status,
    'generated_at': datetime.now().isoformat(timespec='seconds'),
    'live_rows': len(live), 'governed_rows': len(gov), 'command_rows': len(cmd),
    'live_races': len(races['live']), 'governed_races': len(races['gov']), 'command_races': len(races['cmd']),
    'caulfield_r7_live_rows': sum(1 for r in live if race_key(r) == caulfield_key),
    'caulfield_r7_governed_rows': sum(1 for r in gov if race_key(r) == caulfield_key),
    'caulfield_r7_command_rows': sum(1 for r in cmd if race_key(r) == caulfield_key),
    'failed_checks': len(failed),
    'production_changed': 'NO',
}
write_csv(OUT, checks, ['check','result','detail'])
write_csv(SUMMARY, [summary], list(summary.keys()))
REPORT.write_text('\n'.join(['EDGEiQ Fresh Current Governed End-to-End Audit V1','='*56,f'Status: {status}',f'Rows live/governed/command: {len(live)}/{len(gov)}/{len(cmd)}',f'Races live/governed/command: {len(races["live"])}/{len(races["gov"])}/{len(races["cmd"])}',f'CAULFIELD R7 live/governed/command: {summary["caulfield_r7_live_rows"]}/{summary["caulfield_r7_governed_rows"]}/{summary["caulfield_r7_command_rows"]}',f'Failed checks: {len(failed)}','Production changed: NO',''] + [f'{c["check"]}: {c["result"]} ({c["detail"]})' for c in checks]) + '\n', encoding='utf-8')
print(status)
