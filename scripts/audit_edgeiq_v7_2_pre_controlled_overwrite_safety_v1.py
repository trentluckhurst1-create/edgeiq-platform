from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'public' / 'data'
BOARD = DATA / 'edgeiq_live_runner_board_v7_2_feature_flag_candidate.csv'
TERM = DATA / 'edgeiq_live_terminal_feed_v7_2_feature_flag_candidate.csv'
READY = DATA / 'edgeiq_v7_2_controlled_wiring_readiness_checkpoint_v1.csv'
SAFETY = DATA / 'edgeiq_v7_2_feature_flag_safety_v1_summary.csv'
TARGET_BOARD = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
TARGET_TERM = DATA / 'edgeiq_live_terminal_feed_v1.csv'
CHECKPOINT_SUM = DATA / 'edgeiq_v7_2_live_wiring_checkpoints_v1_summary.csv'
OUT = DATA / 'edgeiq_v7_2_pre_controlled_overwrite_safety_v1.csv'
SUM = DATA / 'edgeiq_v7_2_pre_controlled_overwrite_safety_v1_summary.csv'
REP = DATA / 'edgeiq_v7_2_pre_controlled_overwrite_safety_v1_report.txt'

def read_csv(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False) if path.exists() else pd.DataFrame()
def metric_file(path):
    if not path.exists(): return {}
    df = read_csv(path)
    if {'metric','value'}.issubset(df.columns): return dict(zip(df['metric'], df['value']))
    if len(df): return df.iloc[0].to_dict()
    return {}
def values(df, col):
    return ','.join(sorted(df[col].fillna('').astype(str).unique())) if col in df.columns and len(df) else ''
def check_candidate(label, path):
    df = read_csv(path)
    fallback_source_ok = values(df, 'edgeiq_active_price_source_shadow') == 'PRODUCTION_FALLBACK_FEATURE_FLAG_OFF'
    return {
        'candidate': label,
        'file': str(path.relative_to(BASE)),
        'exists': 'YES' if path.exists() else 'NO',
        'rows': len(df),
        'feature_flag_values': values(df, 'edgeiq_v7_2_feature_flag'),
        'live_wired_values': values(df, 'edgeiq_v7_2_live_wired_flag'),
        'production_changed_values': values(df, 'edgeiq_v7_2_production_changed'),
        'active_shadow_source_production_fallback': 'YES' if fallback_source_ok else 'NO',
    }

built_at = datetime.now(timezone.utc).isoformat()
rows = [check_candidate('LIVE_BOARD', BOARD), check_candidate('TERMINAL_FEED', TERM)]
ready_row = metric_file(READY)
safety_row = metric_file(SAFETY)
checkpoint_row = metric_file(CHECKPOINT_SUM)
for target in [TARGET_BOARD, TARGET_TERM]:
    rows.append({'candidate': 'TARGET_LIVE_FILE', 'file': str(target.relative_to(BASE)), 'exists': 'YES' if target.exists() else 'NO', 'rows': len(read_csv(target)), 'feature_flag_values': 'NOT_APPLICABLE', 'live_wired_values': 'NOT_APPLICABLE', 'production_changed_values': 'NOT_APPLICABLE', 'active_shadow_source_production_fallback': 'NOT_APPLICABLE'})

detail = pd.DataFrame(rows)
detail.to_csv(OUT, index=False)
pass_conditions = [
    all(r['exists'] == 'YES' for r in rows),
    all((r['rows'] > 0 if r['candidate'] != 'TARGET_LIVE_FILE' else r['rows'] > 0) for r in rows),
    rows[0]['feature_flag_values'] == 'OFF' and rows[1]['feature_flag_values'] == 'OFF',
    rows[0]['live_wired_values'] == 'NO' and rows[1]['live_wired_values'] == 'NO',
    rows[0]['production_changed_values'] == 'NO' and rows[1]['production_changed_values'] == 'NO',
    rows[0]['active_shadow_source_production_fallback'] == 'YES' and rows[1]['active_shadow_source_production_fallback'] == 'YES',
    ready_row.get('final_status','') == 'READY_FOR_HUMAN_REVIEW_BEFORE_CONTROLLED_OVERWRITE',
    safety_row.get('global_status','') == 'FEATURE_FLAG_SAFETY_PASS',
    CHECKPOINT_SUM.exists(),
]
status = 'PRE_CONTROLLED_OVERWRITE_SAFETY_PASS' if all(pass_conditions) else 'PRE_CONTROLLED_OVERWRITE_BLOCKED'
metrics = {
    'built_at': built_at,
    'board_candidate_exists': rows[0]['exists'],
    'terminal_candidate_exists': rows[1]['exists'],
    'board_candidate_rows': rows[0]['rows'],
    'terminal_candidate_rows': rows[1]['rows'],
    'feature_flag_values': f"{rows[0]['feature_flag_values']} | {rows[1]['feature_flag_values']}",
    'live_wired_values': f"{rows[0]['live_wired_values']} | {rows[1]['live_wired_values']}",
    'production_changed_values': f"{rows[0]['production_changed_values']} | {rows[1]['production_changed_values']}",
    'active_shadow_source_production_fallback': f"{rows[0]['active_shadow_source_production_fallback']} | {rows[1]['active_shadow_source_production_fallback']}",
    'readiness_checkpoint_status': ready_row.get('final_status',''),
    'feature_flag_safety_status': safety_row.get('global_status',''),
    'target_live_files_exist': 'YES' if TARGET_BOARD.exists() and TARGET_TERM.exists() else 'NO',
    'checkpoint_summary_exists': 'YES' if CHECKPOINT_SUM.exists() else 'NO',
    'ui_modified': 'NO',
    'npm_build_run': 'NO',
    'status': status,
}
pd.DataFrame([{'metric': k, 'value': v} for k, v in metrics.items()]).to_csv(SUM, index=False)
report = f'''EDGEiQ V7.2 PRE CONTROLLED OVERWRITE SAFETY V1

- Status: {status}
- Board candidate rows: {rows[0]['rows']}
- Terminal candidate rows: {rows[1]['rows']}
- Feature flag values: {metrics['feature_flag_values']}
- Live wired values: {metrics['live_wired_values']}
- Production changed values: {metrics['production_changed_values']}
- Active/shadow source production fallback: {metrics['active_shadow_source_production_fallback']}
- Readiness checkpoint status: {metrics['readiness_checkpoint_status']}
- Feature flag safety status: {metrics['feature_flag_safety_status']}
- Target live files exist: {metrics['target_live_files_exist']}
- Checkpoint summary exists: {metrics['checkpoint_summary_exists']}
- UI modified: NO
- npm build run: NO
'''
REP.write_text(report, encoding='utf-8')
print(pd.DataFrame([{'metric': k, 'value': v} for k, v in metrics.items()]).to_string(index=False))
print(report)
