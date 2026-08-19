from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'public' / 'data'
TSX = BASE / 'src' / 'components' / 'RaceIntelligenceScreen.tsx'
BOARD = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
TERM = DATA / 'edgeiq_live_terminal_feed_v1.csv'
OUT = DATA / 'edgeiq_v7_2_ui_readiness_after_staging_v1.csv'
SUM = DATA / 'edgeiq_v7_2_ui_readiness_after_staging_v1_summary.csv'
REP = DATA / 'edgeiq_v7_2_ui_readiness_after_staging_v1_report.txt'
FIELDS = ['edgeiq_v7_2_preview_probability','edgeiq_v7_2_preview_fair_price','edgeiq_v7_2_preview_display_fair_price','edgeiq_v7_2_feature_flag']

def read(path): return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False) if path.exists() else pd.DataFrame()
def has_cols(df): return all(c in df.columns for c in FIELDS)
def values(df, col): return ','.join(sorted(df[col].fillna('').astype(str).unique())) if col in df.columns and len(df) else ''

text = TSX.read_text(encoding='utf-8', errors='ignore') if TSX.exists() else ''
board = read(BOARD); term = read(TERM)
rows = [
    {'check':'TSX exists','value':'YES' if TSX.exists() else 'NO'},
    {'check':'contains fair_price references','value':'YES' if 'fair_price' in text else 'NO'},
    {'check':'contains ui_fair_price references','value':'YES' if 'ui_fair_price' in text else 'NO'},
    {'check':'contains live_price references','value':'YES' if 'live_price' in text else 'NO'},
    {'check':'contains V7.2 references','value':'YES' if 'v7_2' in text.lower() or 'V7_2' in text else 'NO'},
    {'check':'live board has V7.2 preview schema','value':'YES' if has_cols(board) else 'NO'},
    {'check':'terminal has V7.2 preview schema','value':'YES' if has_cols(term) else 'NO'},
    {'check':'live board feature flag values','value':values(board,'edgeiq_v7_2_feature_flag')},
    {'check':'terminal feature flag values','value':values(term,'edgeiq_v7_2_feature_flag')},
]
pd.DataFrame(rows).to_csv(OUT, index=False)
status = 'UI_READY_FOR_FEATURE_FLAG_WIRING_PLAN_ONLY' if TSX.exists() and has_cols(board) and has_cols(term) and values(board,'edgeiq_v7_2_feature_flag') == 'OFF' and values(term,'edgeiq_v7_2_feature_flag') == 'OFF' else 'UI_NOT_READY_SCHEMA_MISSING'
recommended = 'Create a UI feature-flag wiring plan only; do not activate V7.2 until visual audit and human approval.' if status.startswith('UI_READY') else 'Resolve staged CSV schema before UI planning.'
metrics = {
    'built_at': datetime.now(timezone.utc).isoformat(),
    'tsx_exists': 'YES' if TSX.exists() else 'NO',
    'contains_fair_price_references': 'YES' if 'fair_price' in text else 'NO',
    'contains_ui_fair_price_references': 'YES' if 'ui_fair_price' in text else 'NO',
    'contains_live_price_references': 'YES' if 'live_price' in text else 'NO',
    'contains_v7_2_references': 'YES' if 'v7_2' in text.lower() or 'V7_2' in text else 'NO',
    'live_board_v7_2_preview_schema': 'YES' if has_cols(board) else 'NO',
    'terminal_v7_2_preview_schema': 'YES' if has_cols(term) else 'NO',
    'live_board_feature_flag_values': values(board,'edgeiq_v7_2_feature_flag'),
    'terminal_feature_flag_values': values(term,'edgeiq_v7_2_feature_flag'),
    'recommended_ui_next_step': recommended,
    'ui_modified': 'NO',
    'status': status,
}
pd.DataFrame([{'metric': k, 'value': v} for k, v in metrics.items()]).to_csv(SUM, index=False)
report = f'''EDGEiQ V7.2 UI READINESS AFTER STAGING V1

- Status: {status}
- TSX exists: {metrics['tsx_exists']}
- fair_price references: {metrics['contains_fair_price_references']}
- ui_fair_price references: {metrics['contains_ui_fair_price_references']}
- live_price references: {metrics['contains_live_price_references']}
- V7.2 references: {metrics['contains_v7_2_references']}
- Live board V7.2 preview schema: {metrics['live_board_v7_2_preview_schema']}
- Terminal V7.2 preview schema: {metrics['terminal_v7_2_preview_schema']}
- Live board feature flag values: {metrics['live_board_feature_flag_values']}
- Terminal feature flag values: {metrics['terminal_feature_flag_values']}
- Recommended UI next step: {recommended}
- UI modified: NO
'''
REP.write_text(report, encoding='utf-8')
print(pd.DataFrame([{'metric': k, 'value': v} for k, v in metrics.items()]).to_string(index=False))
print(report)
