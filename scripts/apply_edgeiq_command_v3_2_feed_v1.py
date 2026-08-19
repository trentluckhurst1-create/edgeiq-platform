import csv, shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
CP = DATA / 'checkpoints'
SRC = DATA / 'edgeiq_command_enrichment_feed_v3_2.csv'
BUILD_SUM = DATA / 'edgeiq_command_enrichment_feed_v3_2_summary.csv'
TGT_V3 = DATA / 'edgeiq_command_enrichment_feed_v3.csv'
TGT_V2 = DATA / 'edgeiq_command_enrichment_feed_v2.csv'
OUT = DATA / 'edgeiq_command_v3_2_apply_v1.csv'
SUMMARY = DATA / 'edgeiq_command_v3_2_apply_v1_summary.csv'
REPORT = DATA / 'edgeiq_command_v3_2_apply_v1_report.txt'

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
    s = clean(v).replace('RACE ', '').replace('R', '')
    return s.lstrip('0') or s
def key(r): return (clean(r.get('race_date') or r.get('current_race_date')), clean(r.get('track')), race_no(r.get('race_no')), clean_horse(r.get('horse') or r.get('horse_key')))
def rkey(r): return key(r)[:3]

status = 'BLOCKED_ROLLED_BACK'
error = ''
audits = []
backup_v3 = ''
backup_v2 = ''
try:
    sum_rows, _ = read_csv(BUILD_SUM)
    if not sum_rows or sum_rows[0].get('status') != 'COMMAND_ENRICHMENT_FEED_V3_2_BUILT':
        raise RuntimeError('V3.2 build summary not ready')
    CP.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_v3 = str(CP / f'edgeiq_command_enrichment_feed_v3_BEFORE_V3_2_APPLY_{ts}.csv')
    backup_v2 = str(CP / f'edgeiq_command_enrichment_feed_v2_BEFORE_V3_2_APPLY_{ts}.csv')
    shutil.copy2(TGT_V3, backup_v3)
    shutil.copy2(TGT_V2, backup_v2)
    shutil.copy2(SRC, TGT_V3)
    shutil.copy2(SRC, TGT_V2)
    rows3, fields3 = read_csv(TGT_V3)
    rows2, fields2 = read_csv(TGT_V2)
    checks = [
        ('v3_rows_383', len(rows3) == 383, len(rows3)),
        ('v2_rows_383', len(rows2) == 383, len(rows2)),
        ('v3_races_25', len(set(rkey(r) for r in rows3)) == 25, len(set(rkey(r) for r in rows3))),
        ('v2_races_25', len(set(rkey(r) for r in rows2)) == 25, len(set(rkey(r) for r in rows2))),
        ('v3_2_fields_present', 'edgeiq_trajectory_available_v3_2' in fields3, 'edgeiq_trajectory_available_v3_2' in fields3),
        ('v2_has_v3_2_fields', 'edgeiq_trajectory_available_v3_2' in fields2, 'edgeiq_trajectory_available_v3_2' in fields2),
        ('v3_no_duplicates', len(set(key(r) for r in rows3)) == len(rows3), len(rows3)-len(set(key(r) for r in rows3))),
        ('v2_no_duplicates', len(set(key(r) for r in rows2)) == len(rows2), len(rows2)-len(set(key(r) for r in rows2))),
    ]
    audits = [{'check': n, 'result': 'PASS' if ok else 'FAIL', 'detail': str(d)} for n, ok, d in checks]
    if all(ok for n, ok, d in checks):
        status = 'COMMAND_V3_2_APPLY_SUCCESS'
    else:
        shutil.copy2(backup_v3, TGT_V3)
        shutil.copy2(backup_v2, TGT_V2)
except Exception as exc:
    error = str(exc)
    try:
        if backup_v3: shutil.copy2(backup_v3, TGT_V3)
        if backup_v2: shutil.copy2(backup_v2, TGT_V2)
    except Exception as rollback_exc:
        error += f' rollback_error={rollback_exc}'
    audits.append({'check': 'apply_exception', 'result': 'FAIL', 'detail': error})
rows3, fields3 = read_csv(TGT_V3)
rows2, fields2 = read_csv(TGT_V2)
summary = {
    'status': status,
    'generated_at': datetime.now().isoformat(timespec='seconds'),
    'backup_v3_feed': backup_v3,
    'backup_v2_feed': backup_v2,
    'v3_rows': len(rows3),
    'v2_rows': len(rows2),
    'v3_races': len(set(rkey(r) for r in rows3)),
    'v2_races': len(set(rkey(r) for r in rows2)),
    'trajectory_usable_rows': sum(1 for r in rows3 if r.get('edgeiq_trajectory_available_v3_2') == 'YES'),
    'trajectory_no_history_rows': sum(1 for r in rows3 if r.get('edgeiq_trajectory_truth_status_v3_2') == 'TRUE_ZERO_NO_TRAJECTORY_HISTORY'),
    'trajectory_source_missing_rows': sum(1 for r in rows3 if r.get('edgeiq_trajectory_truth_status_v3_2') == 'TRAJECTORY_SOURCE_MISSING_OR_JOIN_FAILED'),
    'pricing_math_changed': 'NO',
    'v6_1_changed': 'NO',
    'v7_2g2_changed': 'NO',
    'governed_board_changed': 'NO',
    'error': error,
}
write_csv(OUT, audits, ['check','result','detail'])
write_csv(SUMMARY, [summary], list(summary.keys()))
REPORT.write_text('\n'.join([
    'EDGEiQ Command V3.2 Apply V1', '='*35,
    f'Status: {status}',
    f'V3/V2 rows: {summary["v3_rows"]}/{summary["v2_rows"]}',
    f'V3/V2 races: {summary["v3_races"]}/{summary["v2_races"]}',
    f'Trajectory usable/no-history/source-missing: {summary["trajectory_usable_rows"]}/{summary["trajectory_no_history_rows"]}/{summary["trajectory_source_missing_rows"]}',
    f'Backup V3: {backup_v3}', f'Backup V2: {backup_v2}',
    'Governed board changed: NO', 'Pricing maths changed: NO', 'V6.1 changed: NO', 'V7.2G2 changed: NO',
    f'Error: {error or "None"}',
]) + '\n', encoding='utf-8')
print(status)
