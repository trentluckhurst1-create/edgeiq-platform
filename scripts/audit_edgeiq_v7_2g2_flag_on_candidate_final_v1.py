import csv
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'

candidate_path = DATA / 'edgeiq_live_runner_board_v7_2g2_flag_on_candidate.csv'
visual_path = DATA / 'edgeiq_v7_2g2_final_visual_review_summary_v1.csv'
out_audit = DATA / 'edgeiq_v7_2g2_flag_on_candidate_final_audit_v1.csv'
out_summary = DATA / 'edgeiq_v7_2g2_flag_on_candidate_final_audit_v1_summary.csv'
out_report = DATA / 'edgeiq_v7_2g2_flag_on_candidate_final_audit_v1_report.txt'

EXPECTED_ROWS = 378
PASS_STATUS = 'FLAG_ON_CANDIDATE_FINAL_AUDIT_PASS_REVIEW_REQUIRED'
BLOCK_STATUS = 'FLAG_ON_CANDIDATE_FINAL_AUDIT_BLOCKED'


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


def to_float(v):
    try:
        s = str(v).replace('$', '').replace(',', '').strip()
        if s == '':
            return None
        return float(s)
    except Exception:
        return None


def uniq(rows, col):
    return sorted({str(r.get(col, '')).strip() for r in rows if str(r.get(col, '')).strip() != ''})


def metric_from_visual(rows, metric_name, default=''):
    for r in rows:
        for key in ['metric', 'check', 'field']:
            if str(r.get(key, '')).strip().lower() == metric_name.lower():
                return str(r.get('value', r.get('observed', r.get('status', '')))).strip()
    if rows:
        for key in [metric_name, metric_name.lower(), metric_name.upper()]:
            if key in rows[0]:
                return str(rows[0].get(key, '')).strip()
    return default

rows = read_rows(candidate_path)
visual_rows = read_rows(visual_path)
fields = list(rows[0].keys()) if rows else []
checks = []
blockers = []

def add(name, observed, expected, passed):
    checks.append({
        'check': name,
        'observed': observed,
        'expected': expected,
        'passed': 'YES' if passed else 'NO',
        'notes': '' if passed else f'Expected {expected}; observed {observed}'
    })
    if not passed:
        blockers.append(name)

race_keys = {(r.get('race_date') or r.get('current_race_date') or '', r.get('track') or '', r.get('race_no') or '') for r in rows}
active_col = 'edgeiq_v7_2g2_active_display_fair_price_shadow'
preview_col = 'edgeiq_v7_2g2_on_preview_display_fair_price'
active_prices = [to_float(r.get(active_col)) for r in rows]
active_populated = sum(1 for p in active_prices if p is not None)
active_min = min([p for p in active_prices if p is not None], default='')
active_max = max([p for p in active_prices if p is not None], default='')
flag_vals = uniq(rows, 'edgeiq_v7_2g2_feature_flag')
live_vals = uniq(rows, 'edgeiq_v7_2g2_live_wired_flag')
prod_vals = uniq(rows, 'edgeiq_v7_2g2_production_changed')
fallback_fields = ['fair_price', 'ui_fair_price', 'live_price', 'win_pct']
fallback_present = [c for c in fallback_fields if c in fields]
on_preview_present = preview_col in fields
active_equals_preview = sum(1 for r in rows if str(r.get(active_col, '')).strip() != '' and str(r.get(active_col, '')).strip() == str(r.get(preview_col, '')).strip())

# Compute high-risk races from row-level risk flags if present, else visual summary metric/report fallback.
risk_cols = [c for c in fields if 'high_risk' in c.lower() or 'risk_race' in c.lower()]
high_risk_keys = set()
for r in rows:
    if any(str(r.get(c, '')).strip().upper() in {'YES', 'TRUE', '1', 'HIGH_RISK'} for c in risk_cols):
        high_risk_keys.add((r.get('race_date') or r.get('current_race_date') or '', r.get('track') or '', r.get('race_no') or ''))
high_risk_count = len(high_risk_keys)
visual_high_risk = metric_from_visual(visual_rows, 'high_risk_races', '')
if high_risk_count == 0 and visual_high_risk:
    try:
        high_risk_count = int(float(visual_high_risk))
    except Exception:
        pass

add('candidate_file_exists', str(candidate_path.exists()), 'True', candidate_path.exists())
add('rows', str(len(rows)), str(EXPECTED_ROWS), len(rows) == EXPECTED_ROWS)
add('races_present', str(len(race_keys)), '>0', len(race_keys) > 0)
add('active_display_populated', str(active_populated), str(EXPECTED_ROWS), active_populated == EXPECTED_ROWS)
add('active_display_min_positive', str(active_min), '>0', active_min != '' and float(active_min) > 0)
add('active_display_max_reasonable', str(active_max), '<=100', active_max != '' and float(active_max) <= 100)
add('feature_flag_on_only', '|'.join(flag_vals), 'ON', flag_vals == ['ON'])
add('live_wired_candidate_only', '|'.join(live_vals), 'YES_CANDIDATE_ONLY', live_vals == ['YES_CANDIDATE_ONLY'])
add('production_changed_no_only', '|'.join(prod_vals), 'NO', prod_vals == ['NO'])
add('fallback_fields_still_present', '|'.join(fallback_present), '|'.join(fallback_fields), set(fallback_fields).issubset(set(fields)))
add('on_preview_field_present', str(on_preview_present), 'True', on_preview_present)
add('active_display_equals_on_preview_rows', str(active_equals_preview), str(EXPECTED_ROWS), active_equals_preview == EXPECTED_ROWS)
add('visual_review_pack_exists', str(visual_path.exists()), 'True', visual_path.exists())

status = PASS_STATUS if not blockers else BLOCK_STATUS
summary = [{
    'status': status,
    'generated_at': datetime.now().isoformat(timespec='seconds'),
    'rows': len(rows),
    'races': len(race_keys),
    'active_display_rows': active_populated,
    'active_display_min': active_min,
    'active_display_max': active_max,
    'high_risk_races': high_risk_count,
    'feature_flag_values': '|'.join(flag_vals),
    'live_wired_values': '|'.join(live_vals),
    'production_changed_values': '|'.join(prod_vals),
    'fallback_fields_present': '|'.join(fallback_present),
    'on_preview_fields_present': 'YES' if on_preview_present else 'NO',
    'active_display_equals_on_preview_rows': active_equals_preview,
    'candidate_only': 'YES',
    'live_board_overwritten': 'NO',
    'blocked_reasons': '; '.join(blockers)
}]

write_csv(out_audit, checks, ['check', 'observed', 'expected', 'passed', 'notes'])
write_csv(out_summary, summary, list(summary[0].keys()))

report = []
report.append('EDGEiQ V7.2G2 Flag-ON Candidate Final Audit V1')
report.append('=' * 58)
report.append(f'Status: {status}')
report.append(f'Generated: {summary[0]["generated_at"]}')
report.append(f'Rows: {len(rows)}')
report.append(f'Races: {len(race_keys)}')
report.append(f'Active display populated: {active_populated}')
report.append(f'Active display min/max: {active_min} / {active_max}')
report.append(f'High-risk races: {high_risk_count}')
report.append(f'Feature flag values: {"|".join(flag_vals)}')
report.append(f'Live wired values: {"|".join(live_vals)}')
report.append(f'Production changed values: {"|".join(prod_vals)}')
report.append(f'Active display equals ON-preview rows: {active_equals_preview}')
report.append('')
report.append('Candidate only. Live governed board has not been overwritten.')
if blockers:
    report.append('Blocked reasons: ' + '; '.join(blockers))
out_report.write_text('\n'.join(report) + '\n', encoding='utf-8')

print(status)
print('rows', len(rows), 'races', len(race_keys), 'active_display_rows', active_populated, 'high_risk_races', high_risk_count)
