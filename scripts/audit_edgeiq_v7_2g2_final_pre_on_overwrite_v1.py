import csv
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'

live_path = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
candidate_path = DATA / 'edgeiq_live_runner_board_v7_2g2_flag_on_candidate.csv'
checkpoint_path = DATA / 'edgeiq_v7_2g2_flag_on_candidate_checkpoint_v1.csv'

out_detail = DATA / 'edgeiq_v7_2g2_final_pre_on_overwrite_v1.csv'
out_summary = DATA / 'edgeiq_v7_2g2_final_pre_on_overwrite_v1_summary.csv'
out_report = DATA / 'edgeiq_v7_2g2_final_pre_on_overwrite_v1_report.txt'

EXPECTED_ROWS = 378
PASS_STATUS = 'PRE_ON_OVERWRITE_PASS'
BLOCK_STATUS = 'PRE_ON_OVERWRITE_BLOCKED'

def read_rows(path):
    if not path.exists():
        return []
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)

def to_float(value):
    try:
        s = str(value).replace('$', '').replace(',', '').strip()
        return float(s) if s else None
    except Exception:
        return None

def unique(rows, col):
    return sorted({str(r.get(col, '')).strip() for r in rows if str(r.get(col, '')).strip()})

live_rows = read_rows(live_path)
candidate_rows = read_rows(candidate_path)
checkpoint_rows = read_rows(checkpoint_path)
checks = []
blockers = []

def add(name, observed, expected, passed):
    checks.append({'check': name, 'observed': observed, 'expected': expected, 'passed': 'YES' if passed else 'NO', 'notes': '' if passed else f'Expected {expected}; observed {observed}'})
    if not passed:
        blockers.append(name)

active_col = 'edgeiq_v7_2g2_active_display_fair_price_shadow'
active_prices = [to_float(r.get(active_col)) for r in candidate_rows]
active_populated = sum(1 for p in active_prices if p is not None)
active_min = min([p for p in active_prices if p is not None], default=None)
active_max = max([p for p in active_prices if p is not None], default=None)
checkpoint_status = checkpoint_rows[0].get('status', '') if checkpoint_rows else ''

add('current_live_board_exists', str(live_path.exists()), 'True', live_path.exists())
add('on_candidate_exists', str(candidate_path.exists()), 'True', candidate_path.exists())
add('current_live_board_rows', str(len(live_rows)), str(EXPECTED_ROWS), len(live_rows) == EXPECTED_ROWS)
add('candidate_rows', str(len(candidate_rows)), str(EXPECTED_ROWS), len(candidate_rows) == EXPECTED_ROWS)
add('current_flag_off', '|'.join(unique(live_rows, 'edgeiq_v7_2g2_feature_flag')), 'OFF', unique(live_rows, 'edgeiq_v7_2g2_feature_flag') == ['OFF'])
add('candidate_flag_on', '|'.join(unique(candidate_rows, 'edgeiq_v7_2g2_feature_flag')), 'ON', unique(candidate_rows, 'edgeiq_v7_2g2_feature_flag') == ['ON'])
add('candidate_active_display_rows', str(active_populated), str(EXPECTED_ROWS), active_populated == EXPECTED_ROWS)
add('candidate_active_display_min_ge_1_01', str(active_min), '>=1.01', active_min is not None and active_min >= 1.01)
add('candidate_active_display_max_le_50', str(active_max), '<=50', active_max is not None and active_max <= 50)
add('candidate_production_changed_no', '|'.join(unique(candidate_rows, 'edgeiq_v7_2g2_production_changed')), 'NO', unique(candidate_rows, 'edgeiq_v7_2g2_production_changed') == ['NO'])
add('candidate_live_wired_candidate_only', '|'.join(unique(candidate_rows, 'edgeiq_v7_2g2_live_wired_flag')), 'YES_CANDIDATE_ONLY', unique(candidate_rows, 'edgeiq_v7_2g2_live_wired_flag') == ['YES_CANDIDATE_ONLY'])
add('candidate_no_null_active_display', str(len(candidate_rows) - active_populated), '0', active_populated == len(candidate_rows) and len(candidate_rows) > 0)
add('checkpoint_exists', str(checkpoint_path.exists()), 'True', checkpoint_path.exists())
add('checkpoint_ready_for_final_approval', checkpoint_status, 'V7_2G2_FLAG_ON_CANDIDATE_READY_FOR_FINAL_APPROVAL', checkpoint_status == 'V7_2G2_FLAG_ON_CANDIDATE_READY_FOR_FINAL_APPROVAL')

status = PASS_STATUS if not blockers else BLOCK_STATUS
summary = [{
    'status': status,
    'generated_at': datetime.now().isoformat(timespec='seconds'),
    'checks_total': len(checks),
    'checks_failed': len(blockers),
    'live_rows': len(live_rows),
    'candidate_rows': len(candidate_rows),
    'current_flag_values': '|'.join(unique(live_rows, 'edgeiq_v7_2g2_feature_flag')),
    'candidate_flag_values': '|'.join(unique(candidate_rows, 'edgeiq_v7_2g2_feature_flag')),
    'candidate_active_display_rows': active_populated,
    'candidate_active_display_min': active_min if active_min is not None else '',
    'candidate_active_display_max': active_max if active_max is not None else '',
    'candidate_production_changed_values': '|'.join(unique(candidate_rows, 'edgeiq_v7_2g2_production_changed')),
    'candidate_live_wired_values': '|'.join(unique(candidate_rows, 'edgeiq_v7_2g2_live_wired_flag')),
    'checkpoint_status': checkpoint_status,
    'blocked_reasons': '; '.join(blockers)
}]
write_csv(out_detail, checks, ['check', 'observed', 'expected', 'passed', 'notes'])
write_csv(out_summary, summary, list(summary[0].keys()))
report = [
    'EDGEiQ V7.2G2 Final Pre-ON Overwrite Check V1',
    '=' * 56,
    f'Status: {status}',
    f'Generated: {summary[0]["generated_at"]}',
    f'Live rows: {len(live_rows)}',
    f'Candidate rows: {len(candidate_rows)}',
    f'Current flag values: {summary[0]["current_flag_values"]}',
    f'Candidate flag values: {summary[0]["candidate_flag_values"]}',
    f'Candidate active display rows: {active_populated}',
    f'Candidate active display min/max: {summary[0]["candidate_active_display_min"]} / {summary[0]["candidate_active_display_max"]}',
    f'Checkpoint status: {checkpoint_status}',
    '',
    'Blocked reasons: ' + ('; '.join(blockers) if blockers else 'None')
]
out_report.write_text('\n'.join(report) + '\n', encoding='utf-8')
print(status)
print('failed', len(blockers))
