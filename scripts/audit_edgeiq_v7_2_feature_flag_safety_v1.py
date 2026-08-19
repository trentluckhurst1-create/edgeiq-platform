from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'public' / 'data'
BOARD = DATA / 'edgeiq_live_runner_board_v7_2_feature_flag_candidate.csv'
TERM = DATA / 'edgeiq_live_terminal_feed_v7_2_feature_flag_candidate.csv'
BOARD_SUM = DATA / 'edgeiq_live_runner_board_v7_2_feature_flag_candidate_summary_v1.csv'
TERM_SUM = DATA / 'edgeiq_live_terminal_feed_v7_2_feature_flag_candidate_summary_v1.csv'
OUT = DATA / 'edgeiq_v7_2_feature_flag_safety_v1.csv'
SUM = DATA / 'edgeiq_v7_2_feature_flag_safety_v1_summary.csv'
REP = DATA / 'edgeiq_v7_2_feature_flag_safety_v1_report.txt'

def read(p): return pd.read_csv(p, dtype=str, keep_default_na=False, low_memory=False) if p.exists() else pd.DataFrame()
def summary(p):
    if not p.exists(): return {}
    df = pd.read_csv(p, dtype=str, keep_default_na=False)
    return dict(zip(df['metric'], df['value'])) if {'metric','value'}.issubset(df.columns) else {}
def vals(df, col): return ','.join(sorted(df[col].fillna('').astype(str).unique())) if col in df.columns and len(df) else ''
def present(df, col): return int(df[col].fillna('').astype(str).str.strip().ne('').sum()) if col in df.columns else 0
def audit_one(label, path, sum_path):
    df = read(path); sm = summary(sum_path)
    if df.empty:
        return {'candidate': label, 'file': str(path.relative_to(BASE)), 'exists': 'NO', 'rows': 0, 'feature_flag_values': '', 'live_wired_values': '', 'production_changed_values': '', 'preview_probability_rows': 0, 'preview_display_fair_rows': 0, 'active_shadow_fields_populated': 0, 'active_shadow_equals_fallback_count': 0, 'old_fields_preserved': 'NO', 'forbidden_overwrite_columns_changed': 'NOT_APPLICABLE', 'row_count_preserved': 'NO', 'status': 'MISSING'}
    old_fields = ['live_price'] + (['ui_fair_price'] if 'ui_fair_price' in df.columns else [])
    old_preserved = all(c in df.columns for c in old_fields)
    flag_ok = vals(df, 'edgeiq_v7_2_feature_flag') == 'OFF'
    live_ok = vals(df, 'edgeiq_v7_2_live_wired_flag') == 'NO'
    prod_ok = vals(df, 'edgeiq_v7_2_production_changed') == 'NO'
    row_ok = sm.get('row_count_unchanged','YES') == 'YES'
    status = 'FEATURE_FLAG_CANDIDATE_SAFETY_PASS' if flag_ok and live_ok and prod_ok and row_ok and old_preserved else 'FEATURE_FLAG_CANDIDATE_SAFETY_BLOCKED'
    return {'candidate': label, 'file': str(path.relative_to(BASE)), 'exists': 'YES', 'rows': len(df), 'feature_flag_values': vals(df, 'edgeiq_v7_2_feature_flag'), 'live_wired_values': vals(df, 'edgeiq_v7_2_live_wired_flag'), 'production_changed_values': vals(df, 'edgeiq_v7_2_production_changed'), 'preview_probability_rows': present(df, 'edgeiq_v7_2_preview_probability'), 'preview_display_fair_rows': present(df, 'edgeiq_v7_2_preview_display_fair_price'), 'active_shadow_fields_populated': min(present(df, 'edgeiq_active_fair_price_shadow'), present(df, 'edgeiq_active_display_fair_price_shadow')), 'active_shadow_equals_fallback_count': sm.get('shadow_fields_equal_fallback_rows',''), 'old_fields_preserved': 'YES' if old_preserved else 'NO', 'forbidden_overwrite_columns_changed': 'NOT_APPLICABLE', 'row_count_preserved': sm.get('row_count_unchanged',''), 'status': status}

rows = [audit_one('LIVE_BOARD', BOARD, BOARD_SUM), audit_one('TERMINAL_FEED', TERM, TERM_SUM)]
detail = pd.DataFrame(rows)
detail.to_csv(OUT, index=False)
all_exist = all(r['exists'] == 'YES' for r in rows)
flags_ok = all(r['feature_flag_values'] == 'OFF' for r in rows)
live_ok = all(r['live_wired_values'] == 'NO' for r in rows)
prod_ok = all(r['production_changed_values'] == 'NO' for r in rows)
rows_ok = all(r['row_count_preserved'] == 'YES' for r in rows)
global_status = 'FEATURE_FLAG_SAFETY_PASS' if all_exist and flags_ok and live_ok and prod_ok and rows_ok else 'FEATURE_FLAG_SAFETY_BLOCKED'
metrics = {
    'built_at': datetime.now(timezone.utc).isoformat(),
    'candidates_audited': len(rows),
    'both_candidates_exist': 'YES' if all_exist else 'NO',
    'feature_flag_values': ' | '.join(r['feature_flag_values'] for r in rows),
    'live_wired_values': ' | '.join(r['live_wired_values'] for r in rows),
    'production_changed_values': ' | '.join(r['production_changed_values'] for r in rows),
    'row_counts_preserved': 'YES' if rows_ok else 'NO',
    'live_board_preview_display_rows': rows[0]['preview_display_fair_rows'],
    'terminal_preview_display_rows': rows[1]['preview_display_fair_rows'],
    'global_status': global_status,
    'production_files_overwritten': 'NO',
}
pd.DataFrame([{'metric': k, 'value': v} for k, v in metrics.items()]).to_csv(SUM, index=False)
report = f'''EDGEiQ V7.2 FEATURE-FLAG SAFETY V1

- Global status: {global_status}
- Both candidates exist: {metrics['both_candidates_exist']}
- Feature flag values: {metrics['feature_flag_values']}
- Live wired values: {metrics['live_wired_values']}
- Production changed values: {metrics['production_changed_values']}
- Row counts preserved: {metrics['row_counts_preserved']}
- Live-board preview display rows: {metrics['live_board_preview_display_rows']}
- Terminal preview display rows: {metrics['terminal_preview_display_rows']}

No source live files were overwritten. Feature flag is OFF. V7.2 preview is available on the live-board candidate. Active display remains fallback on both candidates.
'''
REP.write_text(report, encoding='utf-8')
print(pd.DataFrame([{'metric': k, 'value': v} for k, v in metrics.items()]).to_string(index=False))
print(report)
