import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
GOV = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
BASE_CANDIDATES = [DATA / 'edgeiq_command_enrichment_feed_v3.csv', DATA / 'edgeiq_command_enrichment_feed_v2.csv']
TRAJ = DATA / 'edgeiq_runner_trajectory_feed_v1.csv'
OUT = DATA / 'edgeiq_command_enrichment_feed_v3_2.csv'
SUMMARY = DATA / 'edgeiq_command_enrichment_feed_v3_2_summary.csv'
AUDIT = DATA / 'edgeiq_command_enrichment_feed_v3_2_audit.csv'
REPORT = DATA / 'edgeiq_command_enrichment_feed_v3_2_report.txt'

def read_csv(path):
    if not path.exists():
        return [], []
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        r = csv.DictReader(f)
        return list(r), list(r.fieldnames or [])

def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader(); w.writerows(rows)

def clean(v):
    return ' '.join(str(v or '').strip().upper().replace('\u00a0',' ').split())

def clean_horse(v):
    return ''.join(ch for ch in clean(v) if ch.isalnum())

def race_no(v):
    s = clean(v).replace('RACE ', '').replace('R', '')
    return s.lstrip('0') or s

def key(r):
    return (clean(r.get('race_date') or r.get('current_race_date')), clean(r.get('track')), race_no(r.get('race_no')), clean_horse(r.get('horse') or r.get('horse_key')))

def rkey(r):
    return key(r)[:3]

def yes(v):
    return clean(v) in {'YES','TRUE','1','Y','ON'}

base_path = next((p for p in BASE_CANDIDATES if p.exists()), None)
if not base_path:
    raise SystemExit('No command enrichment base feed found')
base_rows, base_fields = read_csv(base_path)
gov_rows, gov_fields = read_csv(GOV)
traj_rows, traj_fields = read_csv(TRAJ)
gov_by = {key(r): r for r in gov_rows}
traj_by = {key(r): r for r in traj_rows}
base_keys = [key(r) for r in base_rows]

out_fields = list(base_fields)
new_fields = [
    'edgeiq_trajectory_available_v3_2',
    'edgeiq_trajectory_truth_status_v3_2',
    'edgeiq_trajectory_score_v3_2',
    'edgeiq_trajectory_band_v3_2',
    'edgeiq_trajectory_narrative_v3_2',
    'edgeiq_trajectory_source_v3_2',
    'edgeiq_trajectory_recent_start_count_v3_2',
    'edgeiq_trajectory_rating_movement_v3_2',
    'edgeiq_trajectory_finish_position_movement_v3_2',
    'edgeiq_trajectory_sp_movement_v3_2',
    'race_trajectory_available_count_v3_2',
    'race_trajectory_source_missing_count_v3_2',
    'race_trajectory_no_history_count_v3_2',
]
for f in new_fields:
    if f not in out_fields:
        out_fields.append(f)

out_rows = []
audit_rows = []
matched = 0
usable = 0
source_missing = 0
no_history = 0
for row in base_rows:
    nr = dict(row)
    k = key(row)
    tr = traj_by.get(k)
    if tr:
        matched += 1
        evidence = clean(tr.get('trajectory_evidence_status_v1'))
        if evidence == 'NO_HISTORY':
            truth = 'TRUE_ZERO_NO_TRAJECTORY_HISTORY'
            no_history += 1
            available = 'NO'
        else:
            truth = 'TRAJECTORY_AVAILABLE'
            usable += 1
            available = 'YES'
        nr['edgeiq_trajectory_available_v3_2'] = available
        nr['edgeiq_trajectory_truth_status_v3_2'] = truth
        nr['edgeiq_trajectory_score_v3_2'] = tr.get('trajectory_score_v1','')
        nr['edgeiq_trajectory_band_v3_2'] = tr.get('trajectory_band_v1','')
        nr['edgeiq_trajectory_narrative_v3_2'] = tr.get('trajectory_narrative_v1','')
        nr['edgeiq_trajectory_source_v3_2'] = tr.get('trajectory_source_v1','')
        nr['edgeiq_trajectory_recent_start_count_v3_2'] = tr.get('recent_start_count_v1','')
        nr['edgeiq_trajectory_rating_movement_v3_2'] = tr.get('rating_movement_v1','')
        nr['edgeiq_trajectory_finish_position_movement_v3_2'] = tr.get('finish_position_movement_v1','')
        nr['edgeiq_trajectory_sp_movement_v3_2'] = tr.get('sp_movement_v1','')
    else:
        source_missing += 1
        nr['edgeiq_trajectory_available_v3_2'] = 'NO'
        nr['edgeiq_trajectory_truth_status_v3_2'] = 'TRAJECTORY_SOURCE_MISSING_OR_JOIN_FAILED'
        nr['edgeiq_trajectory_score_v3_2'] = ''
        nr['edgeiq_trajectory_band_v3_2'] = ''
        nr['edgeiq_trajectory_narrative_v3_2'] = ''
        nr['edgeiq_trajectory_source_v3_2'] = 'NO_MATCH_IN_EDGEIQ_RUNNER_TRAJECTORY_FEED_V1'
        nr['edgeiq_trajectory_recent_start_count_v3_2'] = ''
        nr['edgeiq_trajectory_rating_movement_v3_2'] = ''
        nr['edgeiq_trajectory_finish_position_movement_v3_2'] = ''
        nr['edgeiq_trajectory_sp_movement_v3_2'] = ''
    out_rows.append(nr)
    audit_rows.append({
        'race_date': row.get('race_date',''), 'track': row.get('track',''), 'race_no': row.get('race_no',''), 'horse': row.get('horse',''),
        'trajectory_matched': 'YES' if tr else 'NO',
        'trajectory_available': nr['edgeiq_trajectory_available_v3_2'],
        'trajectory_truth_status': nr['edgeiq_trajectory_truth_status_v3_2'],
        'trajectory_score': nr['edgeiq_trajectory_score_v3_2'],
        'trajectory_band': nr['edgeiq_trajectory_band_v3_2'],
    })

byrace = defaultdict(list)
for row in out_rows:
    byrace[rkey(row)].append(row)
for rk, members in byrace.items():
    counts = {
        'race_trajectory_available_count_v3_2': str(sum(1 for x in members if x['edgeiq_trajectory_available_v3_2'] == 'YES')),
        'race_trajectory_source_missing_count_v3_2': str(sum(1 for x in members if x['edgeiq_trajectory_truth_status_v3_2'] == 'TRAJECTORY_SOURCE_MISSING_OR_JOIN_FAILED')),
        'race_trajectory_no_history_count_v3_2': str(sum(1 for x in members if x['edgeiq_trajectory_truth_status_v3_2'] == 'TRUE_ZERO_NO_TRAJECTORY_HISTORY')),
    }
    for x in members:
        x.update(counts)

gov_races = set(rkey(r) for r in gov_rows)
out_races = set(rkey(r) for r in out_rows)
duplicates = len(out_rows) - len(set(key(r) for r in out_rows))
v7_on = sum(1 for r in gov_rows if yes(r.get('edgeiq_v7_2g2_feature_flag')))
status = 'COMMAND_ENRICHMENT_FEED_V3_2_BUILT'
if len(out_rows) != 383 or len(out_races) != 25 or duplicates or v7_on != len(gov_rows) or matched != len(out_rows):
    status = 'COMMAND_ENRICHMENT_FEED_V3_2_BLOCKED'
summary = {
    'status': status,
    'generated_at': datetime.now().isoformat(timespec='seconds'),
    'base_feed': base_path.name,
    'rows': len(out_rows),
    'races': len(out_races),
    'trajectory_rows': len(traj_rows),
    'trajectory_matched_rows': matched,
    'usable_trajectory_rows': usable,
    'trajectory_no_history_rows': no_history,
    'trajectory_source_missing_rows': source_missing,
    'duplicate_runner_keys': duplicates,
    'v7_2g2_on_rows': v7_on,
    'v7_2g2_total_rows': len(gov_rows),
    'pricing_math_changed': 'NO',
    'v6_1_changed': 'NO',
    'v7_2g2_changed': 'NO',
}
write_csv(OUT, out_rows, out_fields)
write_csv(SUMMARY, [summary], list(summary.keys()))
write_csv(AUDIT, audit_rows, list(audit_rows[0].keys()) if audit_rows else ['status'])
REPORT.write_text('\n'.join([
    'EDGEiQ Command Enrichment Feed V3.2', '='*44,
    f'Status: {status}', f'Base feed: {base_path.name}',
    f'Rows/races: {summary["rows"]}/{summary["races"]}',
    f'Trajectory matched/usable/no-history/source-missing: {matched}/{usable}/{no_history}/{source_missing}',
    f'Duplicate runner keys: {duplicates}',
    f'V7.2G2 ON: {v7_on}/{len(gov_rows)}',
    'Pricing maths changed: NO', 'V6.1 changed: NO', 'V7.2G2 changed: NO',
]) + '\n', encoding='utf-8')
print(status)
