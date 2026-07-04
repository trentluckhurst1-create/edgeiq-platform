from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'public' / 'data'
BOARD = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
TERM = DATA / 'edgeiq_live_terminal_feed_v1.csv'
OVER_SUM = DATA / 'edgeiq_v7_2_controlled_overwrite_feature_flag_off_v1_summary.csv'
OUT = DATA / 'edgeiq_v7_2_post_controlled_overwrite_v1.csv'
SUM = DATA / 'edgeiq_v7_2_post_controlled_overwrite_v1_summary.csv'
REP = DATA / 'edgeiq_v7_2_post_controlled_overwrite_v1_report.txt'

def read(path): return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False) if path.exists() else pd.DataFrame()
def values(df, col): return ','.join(sorted(df[col].fillna('').astype(str).unique())) if col in df.columns and len(df) else ''
def present(df, col): return int(df[col].fillna('').astype(str).str.strip().ne('').sum()) if col in df.columns else 0
def audit(label, path, expected_rows, expected_preview=None):
    df = read(path)
    preview_cols = ['edgeiq_v7_2_preview_probability','edgeiq_v7_2_preview_fair_price','edgeiq_v7_2_preview_display_fair_price']
    required_old = ['live_price'] + (['ui_fair_price'] if label == 'TERMINAL_FEED' else ['fair_price','ui_fair_price','win_pct'])
    old_exists = all(c in df.columns for c in required_old)
    preview_rows = present(df, 'edgeiq_v7_2_preview_display_fair_price')
    shadows_pop = present(df, 'edgeiq_active_display_fair_price_shadow')
    status = 'PASS' if len(df) == expected_rows and values(df,'edgeiq_v7_2_feature_flag') == 'OFF' and values(df,'edgeiq_v7_2_live_wired_flag') == 'NO' and values(df,'edgeiq_v7_2_production_changed') == 'NO' and old_exists and all(c in df.columns for c in preview_cols) else 'REVIEW'
    if expected_preview is not None and preview_rows != expected_preview:
        status = 'REVIEW'
    return {'file_label': label, 'file': str(path.relative_to(BASE)), 'rows': len(df), 'expected_rows': expected_rows, 'preview_columns_exist': 'YES' if all(c in df.columns for c in preview_cols) else 'NO', 'preview_display_fair_rows': preview_rows, 'feature_flag_values': values(df,'edgeiq_v7_2_feature_flag'), 'live_wired_values': values(df,'edgeiq_v7_2_live_wired_flag'), 'production_changed_values': values(df,'edgeiq_v7_2_production_changed'), 'active_shadow_fields_populated_rows': shadows_pop, 'current_price_columns_exist': 'YES' if old_exists else 'NO', 'status': status}

rows = [audit('LIVE_BOARD', BOARD, 378, 378), audit('TERMINAL_FEED', TERM, 383, None)]
detail = pd.DataFrame(rows)
detail.to_csv(OUT, index=False)
all_ok = rows[0]['status'] == 'PASS' and rows[1]['status'] == 'PASS'
status = 'POST_CONTROLLED_OVERWRITE_PASS_FEATURE_FLAG_OFF' if all_ok else 'POST_CONTROLLED_OVERWRITE_BLOCKED_REVIEW_REQUIRED'
metrics = {
    'built_at': datetime.now(timezone.utc).isoformat(),
    'live_board_rows': rows[0]['rows'],
    'terminal_rows': rows[1]['rows'],
    'live_board_preview_rows': rows[0]['preview_display_fair_rows'],
    'terminal_preview_rows': rows[1]['preview_display_fair_rows'],
    'feature_flag_values': f"{rows[0]['feature_flag_values']} | {rows[1]['feature_flag_values']}",
    'live_wired_values': f"{rows[0]['live_wired_values']} | {rows[1]['live_wired_values']}",
    'production_changed_values': f"{rows[0]['production_changed_values']} | {rows[1]['production_changed_values']}",
    'active_shadow_fields_populated': f"{rows[0]['active_shadow_fields_populated_rows']} | {rows[1]['active_shadow_fields_populated_rows']}",
    'current_price_columns_exist': f"{rows[0]['current_price_columns_exist']} | {rows[1]['current_price_columns_exist']}",
    'ui_modified': 'NO',
    'npm_build_run': 'NO',
    'status': status,
}
pd.DataFrame([{'metric': k, 'value': v} for k, v in metrics.items()]).to_csv(SUM, index=False)
report = f'''EDGEiQ V7.2 POST CONTROLLED OVERWRITE V1

- Status: {status}
- Live board rows: {metrics['live_board_rows']} expected 378
- Terminal rows: {metrics['terminal_rows']} expected 383
- Live board V7.2 preview rows: {metrics['live_board_preview_rows']} expected 378
- Terminal V7.2 preview rows: {metrics['terminal_preview_rows']} may be 0 due to known mismatch
- Feature flag values: {metrics['feature_flag_values']}
- Live wired values: {metrics['live_wired_values']}
- Production changed values: {metrics['production_changed_values']}
- Active/shadow fields populated: {metrics['active_shadow_fields_populated']}
- Current price columns exist: {metrics['current_price_columns_exist']}
- UI modified: NO
- npm build run: NO
'''
REP.write_text(report, encoding='utf-8')
print(pd.DataFrame([{'metric': k, 'value': v} for k, v in metrics.items()]).to_string(index=False))
print(report)
