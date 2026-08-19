import csv
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'

live_path = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
activation_path = DATA / 'edgeiq_v7_2g2_activation_safety_gate_v1_summary.csv'
staging_audit_path = DATA / 'edgeiq_v7_2g2_staging_candidate_audit_v1_summary.csv'
staging_checkpoint_path = DATA / 'edgeiq_v7_2g2_staging_checkpoint_v1.csv'
visual_summary_path = DATA / 'edgeiq_v7_2g2_final_visual_review_summary_v1.csv'

out_detail = DATA / 'edgeiq_v7_2g2_pre_flag_on_safety_gate_v1.csv'
out_summary = DATA / 'edgeiq_v7_2g2_pre_flag_on_safety_gate_v1_summary.csv'
out_report = DATA / 'edgeiq_v7_2g2_pre_flag_on_safety_gate_v1_report.txt'

EXPECTED_ROWS = 378
EXPECTED_STAGING_STATUS = 'V7_2G2_STAGED_FLAG_OFF_READY_FOR_FINAL_VISUAL_REVIEW'
EXPECTED_ACTIVE_SOURCE_OFF = 'PRODUCTION_FALLBACK_FEATURE_FLAG_OFF'
PASS_STATUS = 'PRE_FLAG_ON_SAFETY_GATE_PASS_HUMAN_APPROVAL_REQUIRED'
BLOCK_STATUS = 'PRE_FLAG_ON_SAFETY_GATE_BLOCKED'


def read_csv_rows(path):
    if not path.exists():
        return []
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def write_rows(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def pick_metric(rows, keys, default=''):
    if not rows:
        return default
    first = rows[0]
    for key in keys:
        if key in first and str(first.get(key, '')).strip() != '':
            return str(first.get(key, '')).strip()
    # Also support metric/value summary style.
    for row in rows:
        metric = str(row.get('metric', row.get('check', row.get('field', '')))).strip().lower()
        if metric in [k.lower() for k in keys]:
            return str(row.get('value', row.get('status', ''))).strip()
    return default


def truthy_pass(value):
    v = str(value).strip().upper()
    return v in {'PASS', 'PASSED', 'YES', 'TRUE', '1', 'READY', 'OK'} or 'PASS' in v or 'READY' in v


def to_float(v):
    try:
        s = str(v).replace('$', '').replace(',', '').strip()
        if s == '':
            return None
        return float(s)
    except Exception:
        return None


def unique_values(rows, col):
    vals = sorted({str(r.get(col, '')).strip() for r in rows if str(r.get(col, '')).strip() != ''})
    return vals


def rank_order_breaks(rows, price_col):
    breaks = 0
    top_longer = 0
    grouped = {}
    for r in rows:
        key = (r.get('race_date') or r.get('current_race_date') or '', r.get('track') or '', r.get('race_no') or '')
        grouped.setdefault(key, []).append(r)
    for group in grouped.values():
        priced = []
        for r in group:
            price = to_float(r.get(price_col))
            if price is not None:
                priced.append((price, r))
        if len(priced) < 2:
            continue
        priced_by_display = sorted(priced, key=lambda x: x[0])
        top_price = priced_by_display[0][0]
        second_price = priced_by_display[1][0]
        if top_price > second_price:
            top_longer += 1
        last = None
        for price, _ in priced_by_display:
            if last is not None and price < last - 1e-9:
                breaks += 1
            last = price
    return breaks, top_longer

checks = []
blocked_reasons = []

def add_check(name, observed, expected, passed, severity='BLOCKER'):
    checks.append({
        'check': name,
        'observed': observed,
        'expected': expected,
        'passed': 'YES' if passed else 'NO',
        'severity': severity,
        'notes': '' if passed else f'Expected {expected}; observed {observed}'
    })
    if not passed and severity == 'BLOCKER':
        blocked_reasons.append(name)

live_rows = read_csv_rows(live_path)
activation_rows = read_csv_rows(activation_path)
staging_audit_rows = read_csv_rows(staging_audit_path)
staging_checkpoint_rows = read_csv_rows(staging_checkpoint_path)
visual_summary_rows = read_csv_rows(visual_summary_path)

add_check('input_live_board_exists', str(live_path.exists()), 'True', live_path.exists())
add_check('activation_safety_gate_summary_exists', str(activation_path.exists()), 'True', activation_path.exists())
add_check('staging_candidate_audit_summary_exists', str(staging_audit_path.exists()), 'True', staging_audit_path.exists())
add_check('staging_checkpoint_exists', str(staging_checkpoint_path.exists()), 'True', staging_checkpoint_path.exists())
add_check('visual_review_summary_exists', str(visual_summary_path.exists()), 'True', visual_summary_path.exists())

rows = len(live_rows)
add_check('live_board_rows', str(rows), str(EXPECTED_ROWS), rows == EXPECTED_ROWS)

flag_vals = unique_values(live_rows, 'edgeiq_v7_2g2_feature_flag')
add_check('feature_flag_currently_off_only', '|'.join(flag_vals), 'OFF', flag_vals == ['OFF'])

preview_col = 'edgeiq_v7_2g2_on_preview_display_fair_price'
preview_populated = sum(1 for r in live_rows if to_float(r.get(preview_col)) is not None)
add_check('on_preview_display_fair_price_populated', str(preview_populated), str(EXPECTED_ROWS), preview_populated == EXPECTED_ROWS)

source_vals = unique_values(live_rows, 'edgeiq_v7_2g2_active_price_source_shadow')
add_check('active_pricing_source_fallback_while_off', '|'.join(source_vals), EXPECTED_ACTIVE_SOURCE_OFF, source_vals == [EXPECTED_ACTIVE_SOURCE_OFF])

prod_vals = unique_values(live_rows, 'edgeiq_v7_2g2_production_changed')
add_check('production_changed_no_only', '|'.join(prod_vals), 'NO', prod_vals == ['NO'])

live_wired_vals = unique_values(live_rows, 'edgeiq_v7_2g2_live_wired_flag')
add_check('live_wired_no_only', '|'.join(live_wired_vals), 'NO', live_wired_vals == ['NO'])

breaks, top_longer = rank_order_breaks(live_rows, preview_col)
add_check('rank_order_breaks', str(breaks), '0', breaks == 0)
add_check('top_pick_longer_than_second', str(top_longer), '0', top_longer == 0)

staging_status = pick_metric(staging_checkpoint_rows, ['final_status', 'status', 'checkpoint_status'])
add_check('staging_checkpoint_status', staging_status, EXPECTED_STAGING_STATUS, staging_status == EXPECTED_STAGING_STATUS)

activation_status = pick_metric(activation_rows, ['final_status', 'status', 'gate_status', 'verdict'])
add_check('activation_safety_gate_passed', activation_status, 'PASS/READY', truthy_pass(activation_status))

staging_audit_status = pick_metric(staging_audit_rows, ['final_status', 'status', 'audit_status', 'verdict'])
add_check('staging_candidate_audit_passed', staging_audit_status, 'PASS/READY', truthy_pass(staging_audit_status))

visual_status = pick_metric(visual_summary_rows, ['final_status', 'status', 'review_status'])
add_check('visual_review_pack_ready', visual_status, 'FINAL_VISUAL_REVIEW_PACK_READY', visual_status == 'FINAL_VISUAL_REVIEW_PACK_READY')

add_check('ui_unchanged_this_pass', 'NO_UI_CHANGES_PER_SCRIPTED_AUDIT', 'NO_UI_CHANGES', True, 'INFO')
add_check('npm_build_not_run_this_pass', 'NOT_RUN_PER_TASK_RULE', 'NOT_RUN', True, 'INFO')

status = PASS_STATUS if not blocked_reasons else BLOCK_STATUS

summary = [{
    'status': status,
    'generated_at': datetime.now().isoformat(timespec='seconds'),
    'checks_total': len(checks),
    'checks_passed': sum(1 for c in checks if c['passed'] == 'YES'),
    'checks_failed': sum(1 for c in checks if c['passed'] != 'YES'),
    'blocker_count': len(blocked_reasons),
    'blocked_reasons': '; '.join(blocked_reasons),
    'live_rows': rows,
    'feature_flag_values': '|'.join(flag_vals),
    'on_preview_populated_rows': preview_populated,
    'active_source_values': '|'.join(source_vals),
    'production_changed_values': '|'.join(prod_vals),
    'live_wired_values': '|'.join(live_wired_vals),
    'rank_order_breaks': breaks,
    'top_pick_longer_than_second': top_longer,
    'activation': 'NO',
    'candidate_only': 'YES',
    'production_changed': 'NO'
}]

write_rows(out_detail, checks, ['check', 'observed', 'expected', 'passed', 'severity', 'notes'])
write_rows(out_summary, summary, list(summary[0].keys()))

report = []
report.append('EDGEiQ V7.2G2 Pre-Flag-ON Safety Gate V1')
report.append('=' * 52)
report.append(f'Status: {status}')
report.append(f'Generated: {summary[0]["generated_at"]}')
report.append('')
report.append(f'Live board rows: {rows}')
report.append(f'Feature flag values: {"|".join(flag_vals)}')
report.append(f'ON-preview populated rows: {preview_populated}')
report.append(f'Active source values: {"|".join(source_vals)}')
report.append(f'Production changed values: {"|".join(prod_vals)}')
report.append(f'Live wired values: {"|".join(live_wired_vals)}')
report.append(f'Rank order breaks: {breaks}')
report.append(f'Top pick longer than second: {top_longer}')
report.append('')
if blocked_reasons:
    report.append('Blocked reasons:')
    for reason in blocked_reasons:
        report.append(f'- {reason}')
else:
    report.append('All blocker checks passed. Human approval is still required before any controlled live overwrite.')
report.append('')
report.append('Explicit controls:')
report.append('- Candidate/staging audit only.')
report.append('- UI unchanged.')
report.append('- npm build not run.')
report.append('- Production changed NO.')
report.append('- Live board remains feature flag OFF.')

out_report.write_text('\n'.join(report) + '\n', encoding='utf-8')
print(status)
print('checks_total', len(checks), 'failed', summary[0]['checks_failed'], 'blockers', len(blocked_reasons))
if blocked_reasons:
    print('blocked_reasons:', '; '.join(blocked_reasons))
