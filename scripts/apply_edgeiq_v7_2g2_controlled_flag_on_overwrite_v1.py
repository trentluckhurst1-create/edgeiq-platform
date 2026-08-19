import csv
import shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
CHECKPOINTS = DATA / 'checkpoints'

live_path = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
candidate_path = DATA / 'edgeiq_live_runner_board_v7_2g2_flag_on_candidate.csv'
out_detail = DATA / 'edgeiq_v7_2g2_controlled_flag_on_overwrite_v1.csv'
out_summary = DATA / 'edgeiq_v7_2g2_controlled_flag_on_overwrite_v1_summary.csv'
out_report = DATA / 'edgeiq_v7_2g2_controlled_flag_on_overwrite_v1_report.txt'

EXPECTED_ROWS = 378
PASS_STATUS = 'V7_2G2_CONTROLLED_FLAG_ON_OVERWRITE_APPLIED'
BLOCK_STATUS = 'V7_2G2_CONTROLLED_FLAG_ON_OVERWRITE_BLOCKED_ROLLED_BACK'
SOURCE_ON = 'V7_2G2_GUARDED_DISPLAY_FEATURE_FLAG_ON_CANDIDATE'

def read_rows(path):
    if not path.exists():
        return []
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def write_rows(path, rows, fieldnames):
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)

def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)

def to_float(v):
    try:
        s = str(v).replace('$', '').replace(',', '').strip()
        return float(s) if s else None
    except Exception:
        return None

def uniq(rows, col):
    return sorted({str(r.get(col, '')).strip() for r in rows if str(r.get(col, '')).strip()})

def post_checks(rows, fields):
    checks = []
    blockers = []
    def add(name, observed, expected, passed):
        checks.append({'check': name, 'observed': observed, 'expected': expected, 'passed': 'YES' if passed else 'NO', 'notes': '' if passed else f'Expected {expected}; observed {observed}'})
        if not passed:
            blockers.append(name)
    active_col = 'edgeiq_v7_2g2_active_display_fair_price_shadow'
    preview_col = 'edgeiq_v7_2g2_on_preview_display_fair_price'
    active_prices = [to_float(r.get(active_col)) for r in rows]
    active_populated = sum(1 for p in active_prices if p is not None)
    active_equals_preview = sum(1 for r in rows if str(r.get(active_col, '')).strip() and str(r.get(active_col, '')).strip() == str(r.get(preview_col, '')).strip())
    fallback_fields = ['fair_price', 'ui_fair_price', 'live_price', 'win_pct']
    fallback_present = [c for c in fallback_fields if c in fields]
    add('output_rows', str(len(rows)), str(EXPECTED_ROWS), len(rows) == EXPECTED_ROWS)
    add('feature_flag_on', '|'.join(uniq(rows, 'edgeiq_v7_2g2_feature_flag')), 'ON', uniq(rows, 'edgeiq_v7_2g2_feature_flag') == ['ON'])
    add('active_display_rows', str(active_populated), str(EXPECTED_ROWS), active_populated == EXPECTED_ROWS)
    add('active_display_equals_on_preview', str(active_equals_preview), str(EXPECTED_ROWS), active_equals_preview == EXPECTED_ROWS)
    add('production_changed_no', '|'.join(uniq(rows, 'edgeiq_v7_2g2_production_changed')), 'NO', uniq(rows, 'edgeiq_v7_2g2_production_changed') == ['NO'])
    add('live_wired_yes_controlled_on', '|'.join(uniq(rows, 'edgeiq_v7_2g2_live_wired_flag')), 'YES_CONTROLLED_ON', uniq(rows, 'edgeiq_v7_2g2_live_wired_flag') == ['YES_CONTROLLED_ON'])
    add('fallback_fields_still_present', '|'.join(fallback_present), '|'.join(fallback_fields), set(fallback_fields).issubset(set(fields)))
    return checks, blockers

status = PASS_STATUS
errors = []
backup_path = ''
rolled_back = 'NO'
rows_after = []
fields = []
checks = []
try:
    if not live_path.exists():
        raise FileNotFoundError(f'Missing live board: {live_path}')
    if not candidate_path.exists():
        raise FileNotFoundError(f'Missing candidate: {candidate_path}')
    CHECKPOINTS.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = CHECKPOINTS / f'edgeiq_live_runner_board_governed_v1_IMMEDIATE_BACKUP_BEFORE_V7_2G2_FLAG_ON_OVERWRITE_{timestamp}.csv'
    shutil.copy2(live_path, backup)
    backup_path = str(backup)

    candidate_rows = read_rows(candidate_path)
    fields = list(candidate_rows[0].keys()) if candidate_rows else []
    for col in ['edgeiq_v7_2g2_feature_flag', 'edgeiq_v7_2g2_live_wired_flag', 'edgeiq_v7_2g2_production_changed', 'edgeiq_v7_2g2_active_display_fair_price_shadow', 'edgeiq_v7_2g2_active_price_source_shadow']:
        if col not in fields:
            fields.append(col)
    for r in candidate_rows:
        r['edgeiq_v7_2g2_feature_flag'] = 'ON'
        r['edgeiq_v7_2g2_live_wired_flag'] = 'YES_CONTROLLED_ON'
        r['edgeiq_v7_2g2_production_changed'] = 'NO'
        if str(r.get('edgeiq_v7_2g2_on_preview_display_fair_price', '')).strip():
            r['edgeiq_v7_2g2_active_display_fair_price_shadow'] = str(r.get('edgeiq_v7_2g2_on_preview_display_fair_price', '')).strip()
        r['edgeiq_v7_2g2_active_price_source_shadow'] = SOURCE_ON
    write_rows(live_path, candidate_rows, fields)

    rows_after = read_rows(live_path)
    fields_after = list(rows_after[0].keys()) if rows_after else fields
    checks, blockers = post_checks(rows_after, fields_after)
    if blockers:
        shutil.copy2(backup, live_path)
        status = BLOCK_STATUS
        rolled_back = 'YES'
        errors.append('Post-copy check failed: ' + '; '.join(blockers))
except Exception as exc:
    status = BLOCK_STATUS
    errors.append(str(exc))
    if backup_path and Path(backup_path).exists():
        shutil.copy2(backup_path, live_path)
        rolled_back = 'YES'

rows_after = read_rows(live_path)
active_prices = [to_float(r.get('edgeiq_v7_2g2_active_display_fair_price_shadow')) for r in rows_after]
active_populated = sum(1 for p in active_prices if p is not None)
summary = [{
    'status': status,
    'generated_at': datetime.now().isoformat(timespec='seconds'),
    'backup_file': backup_path,
    'rows': len(rows_after),
    'feature_flag_values': '|'.join(uniq(rows_after, 'edgeiq_v7_2g2_feature_flag')),
    'live_wired_values': '|'.join(uniq(rows_after, 'edgeiq_v7_2g2_live_wired_flag')),
    'production_changed_values': '|'.join(uniq(rows_after, 'edgeiq_v7_2g2_production_changed')),
    'active_display_rows': active_populated,
    'active_display_min': min([p for p in active_prices if p is not None], default=''),
    'active_display_max': max([p for p in active_prices if p is not None], default=''),
    'rolled_back': rolled_back,
    'production_changed': 'NO',
    'errors': '; '.join(errors)
}]
if not checks:
    checks = [{'check': 'overwrite_execution', 'observed': status, 'expected': PASS_STATUS, 'passed': 'YES' if status == PASS_STATUS else 'NO', 'notes': '; '.join(errors)}]
write_csv(out_detail, checks, ['check', 'observed', 'expected', 'passed', 'notes'])
write_csv(out_summary, summary, list(summary[0].keys()))
report = [
    'EDGEiQ V7.2G2 Controlled Flag-ON Overwrite V1',
    '=' * 56,
    f'Status: {status}',
    f'Generated: {summary[0]["generated_at"]}',
    f'Backup: {backup_path}',
    f'Rows after operation: {summary[0]["rows"]}',
    f'Feature flag values: {summary[0]["feature_flag_values"]}',
    f'Live wired values: {summary[0]["live_wired_values"]}',
    f'Production changed values: {summary[0]["production_changed_values"]}',
    f'Active display rows: {summary[0]["active_display_rows"]}',
    f'Active display min/max: {summary[0]["active_display_min"]} / {summary[0]["active_display_max"]}',
    f'Rolled back: {rolled_back}',
    f'Errors: {summary[0]["errors"] or "None"}'
]
out_report.write_text('\n'.join(report) + '\n', encoding='utf-8')
print(status)
print('rows', summary[0]['rows'], 'flag', summary[0]['feature_flag_values'], 'wired', summary[0]['live_wired_values'], 'rolled_back', rolled_back)
