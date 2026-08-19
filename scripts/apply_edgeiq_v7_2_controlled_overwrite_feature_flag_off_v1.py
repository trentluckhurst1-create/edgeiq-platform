from pathlib import Path
from datetime import datetime, timezone
import shutil
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'public' / 'data'
CHECKPOINTS = DATA / 'checkpoints'
CHECKPOINTS.mkdir(parents=True, exist_ok=True)
BOARD_CAND = DATA / 'edgeiq_live_runner_board_v7_2_feature_flag_candidate.csv'
TERM_CAND = DATA / 'edgeiq_live_terminal_feed_v7_2_feature_flag_candidate.csv'
BOARD_TARGET = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
TERM_TARGET = DATA / 'edgeiq_live_terminal_feed_v1.csv'
OUT = DATA / 'edgeiq_v7_2_controlled_overwrite_feature_flag_off_v1.csv'
SUM = DATA / 'edgeiq_v7_2_controlled_overwrite_feature_flag_off_v1_summary.csv'
REP = DATA / 'edgeiq_v7_2_controlled_overwrite_feature_flag_off_v1_report.txt'

def read(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False) if path.exists() else pd.DataFrame()
def values(df, col):
    return ','.join(sorted(df[col].fillna('').astype(str).unique())) if col in df.columns and len(df) else ''
def copy_candidate(candidate, target):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = CHECKPOINTS / f"{target.stem}_IMMEDIATE_BACKUP_BEFORE_V7_2_CONTROLLED_OVERWRITE_{ts}{target.suffix}"
    row = {'target_file': str(target.relative_to(BASE)), 'candidate_file': str(candidate.relative_to(BASE)), 'backup_file': str(backup.relative_to(BASE)), 'target_rows_before': 0, 'candidate_rows': 0, 'target_rows_after': 0, 'overwrite_applied': 'NO', 'feature_flag_values_after': '', 'live_wired_values_after': '', 'production_changed_values_after': '', 'status': ''}
    try:
        before = read(target); cand = read(candidate)
        row['target_rows_before'] = len(before); row['candidate_rows'] = len(cand)
        if before.empty or cand.empty:
            row['status'] = 'CONTROLLED_OVERWRITE_BLOCKED_OR_ROLLED_BACK'
            return row
        shutil.copy2(target, backup)
        shutil.copy2(candidate, target)
        after = read(target)
        row['target_rows_after'] = len(after)
        row['feature_flag_values_after'] = values(after, 'edgeiq_v7_2_feature_flag')
        row['live_wired_values_after'] = values(after, 'edgeiq_v7_2_live_wired_flag')
        row['production_changed_values_after'] = values(after, 'edgeiq_v7_2_production_changed')
        ok = len(after) == len(cand) and row['feature_flag_values_after'] == 'OFF' and row['live_wired_values_after'] == 'NO' and row['production_changed_values_after'] == 'NO'
        if ok:
            row['overwrite_applied'] = 'YES'
            row['status'] = 'CONTROLLED_OVERWRITE_APPLIED_FEATURE_FLAG_OFF'
        else:
            shutil.copy2(backup, target)
            restored = read(target)
            row['target_rows_after'] = len(restored)
            row['overwrite_applied'] = 'NO'
            row['status'] = 'CONTROLLED_OVERWRITE_BLOCKED_OR_ROLLED_BACK'
    except Exception as exc:
        row['status'] = 'CONTROLLED_OVERWRITE_BLOCKED_OR_ROLLED_BACK'
        row['error'] = str(exc)
        try:
            if backup.exists(): shutil.copy2(backup, target)
        except Exception as restore_exc:
            row['restore_error'] = str(restore_exc)
    return row

rows = [copy_candidate(BOARD_CAND, BOARD_TARGET), copy_candidate(TERM_CAND, TERM_TARGET)]
detail = pd.DataFrame(rows)
detail.to_csv(OUT, index=False)
all_applied = all(r['status'] == 'CONTROLLED_OVERWRITE_APPLIED_FEATURE_FLAG_OFF' for r in rows)
status = 'CONTROLLED_OVERWRITE_APPLIED_FEATURE_FLAG_OFF' if all_applied else 'CONTROLLED_OVERWRITE_BLOCKED_OR_ROLLED_BACK'
metrics = {
    'built_at': datetime.now(timezone.utc).isoformat(),
    'targets_processed': len(rows),
    'overwrites_applied': int(sum(r['overwrite_applied'] == 'YES' for r in rows)),
    'board_target_rows_after': rows[0]['target_rows_after'],
    'terminal_target_rows_after': rows[1]['target_rows_after'],
    'feature_flag_values_after': ' | '.join(r['feature_flag_values_after'] for r in rows),
    'live_wired_values_after': ' | '.join(r['live_wired_values_after'] for r in rows),
    'production_changed_values_after': ' | '.join(r['production_changed_values_after'] for r in rows),
    'status': status,
}
pd.DataFrame([{'metric': k, 'value': v} for k, v in metrics.items()]).to_csv(SUM, index=False)
report = f'''EDGEiQ V7.2 CONTROLLED OVERWRITE FEATURE FLAG OFF V1

- Status: {status}
- Targets processed: {metrics['targets_processed']}
- Overwrites applied: {metrics['overwrites_applied']}
- Board target rows after: {metrics['board_target_rows_after']}
- Terminal target rows after: {metrics['terminal_target_rows_after']}
- Feature flag values after: {metrics['feature_flag_values_after']}
- Live wired values after: {metrics['live_wired_values_after']}
- Production changed values after: {metrics['production_changed_values_after']}

This was a staging overwrite only. Feature flag remains OFF, live wired remains NO, and production changed metadata remains NO.
'''
REP.write_text(report, encoding='utf-8')
print(pd.DataFrame([{'metric': k, 'value': v} for k, v in metrics.items()]).to_string(index=False))
print(report)
