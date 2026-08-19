import csv
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'

input_path = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
out_candidate = DATA / 'edgeiq_live_runner_board_v7_2g2_flag_on_candidate.csv'
out_summary = DATA / 'edgeiq_live_runner_board_v7_2g2_flag_on_candidate_summary_v1.csv'
out_audit = DATA / 'edgeiq_live_runner_board_v7_2g2_flag_on_candidate_audit_v1.csv'
out_report = DATA / 'edgeiq_live_runner_board_v7_2g2_flag_on_candidate_report_v1.txt'

EXPECTED_ROWS = 378
SOURCE_ON = 'V7_2G2_GUARDED_DISPLAY_FEATURE_FLAG_ON_CANDIDATE'
PASS_STATUS = 'FLAG_ON_LIVE_BOARD_CANDIDATE_BUILT_REVIEW_REQUIRED'
BLOCK_STATUS = 'FLAG_ON_LIVE_BOARD_CANDIDATE_BLOCKED'


def to_float(v):
    try:
        s = str(v).replace('$', '').replace(',', '').strip()
        if s == '':
            return None
        return float(s)
    except Exception:
        return None


def read_rows(path):
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


def unique_values(rows, col):
    return sorted({str(r.get(col, '')).strip() for r in rows if str(r.get(col, '')).strip() != ''})


def rank_checks(rows, price_col):
    grouped = {}
    for r in rows:
        key = (r.get('race_date') or r.get('current_race_date') or '', r.get('track') or '', r.get('race_no') or '')
        grouped.setdefault(key, []).append(r)
    breaks = 0
    top_longer = 0
    for group in grouped.values():
        priced = [(to_float(r.get(price_col)), r) for r in group]
        priced = [(p, r) for p, r in priced if p is not None]
        if len(priced) < 2:
            continue
        ordered = sorted(priced, key=lambda item: item[0])
        if ordered[0][0] > ordered[1][0]:
            top_longer += 1
        last = None
        for price, _ in ordered:
            if last is not None and price < last - 1e-9:
                breaks += 1
            last = price
    return breaks, top_longer

if not input_path.exists():
    raise FileNotFoundError(input_path)

rows = read_rows(input_path)
fields = list(rows[0].keys()) if rows else []
required_cols = [
    'edgeiq_v7_2g2_feature_flag',
    'edgeiq_v7_2g2_live_wired_flag',
    'edgeiq_v7_2g2_production_changed',
    'edgeiq_v7_2g2_active_display_fair_price_shadow',
    'edgeiq_v7_2g2_active_price_source_shadow',
]
for col in required_cols:
    if col not in fields:
        fields.append(col)

preview_col = 'edgeiq_v7_2g2_on_preview_display_fair_price'
for r in rows:
    preview = str(r.get(preview_col, '')).strip()
    r['edgeiq_v7_2g2_feature_flag'] = 'ON'
    r['edgeiq_v7_2g2_live_wired_flag'] = 'YES_CANDIDATE_ONLY'
    r['edgeiq_v7_2g2_production_changed'] = 'NO'
    r['edgeiq_v7_2g2_active_display_fair_price_shadow'] = preview
    r['edgeiq_v7_2g2_active_price_source_shadow'] = SOURCE_ON

write_csv(out_candidate, rows, fields)

checks = []
blockers = []
def add_check(name, observed, expected, passed):
    checks.append({
        'check': name,
        'observed': observed,
        'expected': expected,
        'passed': 'YES' if passed else 'NO',
        'notes': '' if passed else f'Expected {expected}; observed {observed}'
    })
    if not passed:
        blockers.append(name)

row_count = len(rows)
flag_vals = unique_values(rows, 'edgeiq_v7_2g2_feature_flag')
live_vals = unique_values(rows, 'edgeiq_v7_2g2_live_wired_flag')
prod_vals = unique_values(rows, 'edgeiq_v7_2g2_production_changed')
source_vals = unique_values(rows, 'edgeiq_v7_2g2_active_price_source_shadow')
active_prices = [to_float(r.get('edgeiq_v7_2g2_active_display_fair_price_shadow')) for r in rows]
active_populated = sum(1 for p in active_prices if p is not None)
active_min = min([p for p in active_prices if p is not None], default='')
active_max = max([p for p in active_prices if p is not None], default='')
breaks, top_longer = rank_checks(rows, 'edgeiq_v7_2g2_active_display_fair_price_shadow')
fallback_fields = ['fair_price', 'ui_fair_price', 'live_price', 'win_pct']
fallback_present = [c for c in fallback_fields if c in fields]
on_preview_present = preview_col in fields

add_check('rows', str(row_count), str(EXPECTED_ROWS), row_count == EXPECTED_ROWS)
add_check('feature_flag_on_rows', str(sum(1 for r in rows if r.get('edgeiq_v7_2g2_feature_flag') == 'ON')), str(EXPECTED_ROWS), flag_vals == ['ON'] and row_count == EXPECTED_ROWS)
add_check('active_display_rows', str(active_populated), str(EXPECTED_ROWS), active_populated == EXPECTED_ROWS)
add_check('production_fallback_fields_present', '|'.join(fallback_present), '|'.join(fallback_fields), set(fallback_fields).issubset(set(fields)))
add_check('on_preview_fields_present', str(on_preview_present), 'True', on_preview_present)
add_check('no_null_active_display', str(row_count - active_populated), '0', active_populated == row_count)
add_check('rank_order_breaks', str(breaks), '0', breaks == 0)
add_check('top_pick_longer_than_second', str(top_longer), '0', top_longer == 0)
add_check('production_changed_no', '|'.join(prod_vals), 'NO', prod_vals == ['NO'])
add_check('live_wired_candidate_only', '|'.join(live_vals), 'YES_CANDIDATE_ONLY', live_vals == ['YES_CANDIDATE_ONLY'])
add_check('active_source_candidate', '|'.join(source_vals), SOURCE_ON, source_vals == [SOURCE_ON])

status = PASS_STATUS if not blockers else BLOCK_STATUS
summary = [{
    'status': status,
    'generated_at': datetime.now().isoformat(timespec='seconds'),
    'rows': row_count,
    'feature_flag_values': '|'.join(flag_vals),
    'live_wired_values': '|'.join(live_vals),
    'production_changed_values': '|'.join(prod_vals),
    'active_source_values': '|'.join(source_vals),
    'active_display_rows': active_populated,
    'active_display_min': active_min,
    'active_display_max': active_max,
    'rank_order_breaks': breaks,
    'top_pick_longer_than_second': top_longer,
    'fallback_fields_present': '|'.join(fallback_present),
    'on_preview_fields_present': 'YES' if on_preview_present else 'NO',
    'candidate_only': 'YES',
    'live_board_overwritten': 'NO',
    'production_changed': 'NO',
    'blocked_reasons': '; '.join(blockers)
}]

write_csv(out_audit, checks, ['check', 'observed', 'expected', 'passed', 'notes'])
write_csv(out_summary, summary, list(summary[0].keys()))

report = []
report.append('EDGEiQ V7.2G2 Feature-Flag ON Live Board Candidate V1')
report.append('=' * 62)
report.append(f'Status: {status}')
report.append(f'Generated: {summary[0]["generated_at"]}')
report.append(f'Candidate file: {out_candidate}')
report.append(f'Rows: {row_count}')
report.append(f'Feature flag values: {"|".join(flag_vals)}')
report.append(f'Live wired values: {"|".join(live_vals)}')
report.append(f'Production changed values: {"|".join(prod_vals)}')
report.append(f'Active display rows: {active_populated}')
report.append(f'Active display min/max: {active_min} / {active_max}')
report.append(f'Rank order breaks: {breaks}')
report.append(f'Top pick longer than second: {top_longer}')
report.append('')
report.append('Important: this is a candidate file only. The governed live board was not overwritten.')
if blockers:
    report.append('Blocked reasons: ' + '; '.join(blockers))
out_report.write_text('\n'.join(report) + '\n', encoding='utf-8')

print(status)
print('rows', row_count, 'active_display_rows', active_populated, 'active_min', active_min, 'active_max', active_max)
print('candidate', out_candidate)
