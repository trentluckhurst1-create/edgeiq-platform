from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'public' / 'data'
TSX = BASE / 'src' / 'components' / 'RaceIntelligenceScreen.tsx'
BOARD = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
TERM = DATA / 'edgeiq_live_terminal_feed_v1.csv'
OUT = DATA / 'edgeiq_v7_2_ui_price_field_usage_v1.csv'
SUM = DATA / 'edgeiq_v7_2_ui_price_field_usage_v1_summary.csv'
REP = DATA / 'edgeiq_v7_2_ui_price_field_usage_v1_report.txt'
TOKENS = ['fair_price','ui_fair_price','display_fair_price','live_price','market_price','win_pct','rated_price','V6_1_RESEARCH','edgeiq_v7_2','edgeiq_active_','EDGE','DECISION','MARKET','INTELLIGENCE']
PREVIEW = ['edgeiq_v7_2_preview_probability','edgeiq_v7_2_preview_fair_price','edgeiq_v7_2_preview_display_fair_price','edgeiq_v7_2_feature_flag']
SHADOW = ['edgeiq_active_probability_shadow','edgeiq_active_fair_price_shadow','edgeiq_active_display_fair_price_shadow','edgeiq_active_price_source_shadow']

def read_csv(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False) if path.exists() else pd.DataFrame()
def values(df, col):
    return ','.join(sorted(df[col].fillna('').astype(str).unique())) if col in df.columns and len(df) else ''
def has_cols(df, cols): return all(c in df.columns for c in cols)

text = TSX.read_text(encoding='utf-8', errors='ignore') if TSX.exists() else ''
lines = text.splitlines()
rows = []
for token in TOKENS:
    hits = []
    for i, line in enumerate(lines, start=1):
        if token in line:
            hits.append((i, line.strip()))
    rows.append({'token': token, 'count': len(hits), 'line_numbers': ';'.join(str(i) for i,_ in hits[:30]), 'sample_lines': ' || '.join(f'{i}:{s[:180]}' for i,s in hits[:8])})
board = read_csv(BOARD); term = read_csv(TERM)
rows.extend([
    {'token':'LIVE_BOARD_COLUMNS','count':len(board.columns),'line_numbers':'','sample_lines':','.join(board.columns)},
    {'token':'TERMINAL_COLUMNS','count':len(term.columns),'line_numbers':'','sample_lines':','.join(term.columns)},
    {'token':'LIVE_BOARD_V7_2_PREVIEW_PRESENT','count':1 if has_cols(board, PREVIEW) else 0,'line_numbers':'','sample_lines':'YES' if has_cols(board, PREVIEW) else 'NO'},
    {'token':'LIVE_BOARD_ACTIVE_SHADOW_PRESENT','count':1 if has_cols(board, SHADOW) else 0,'line_numbers':'','sample_lines':'YES' if has_cols(board, SHADOW) else 'NO'},
    {'token':'TERMINAL_V7_2_PREVIEW_PRESENT','count':1 if has_cols(term, PREVIEW) else 0,'line_numbers':'','sample_lines':'YES' if has_cols(term, PREVIEW) else 'NO'},
    {'token':'LIVE_BOARD_FEATURE_FLAG_VALUES','count':0,'line_numbers':'','sample_lines':values(board,'edgeiq_v7_2_feature_flag')},
    {'token':'LIVE_BOARD_LIVE_WIRED_VALUES','count':0,'line_numbers':'','sample_lines':values(board,'edgeiq_v7_2_live_wired_flag')},
    {'token':'LIVE_BOARD_PRODUCTION_CHANGED_VALUES','count':0,'line_numbers':'','sample_lines':values(board,'edgeiq_v7_2_production_changed')},
])
pd.DataFrame(rows).to_csv(OUT, index=False)
ui_price_tokens = sum(1 for r in rows[:len(TOKENS)] if r['count'] > 0)
mode = 'FEATURE_FLAG_AWARE_FALLBACK_ONLY' if has_cols(board, PREVIEW) and has_cols(board, SHADOW) else 'BLOCKED_SCHEMA_MISSING'
metrics = {
    'built_at': datetime.now(timezone.utc).isoformat(),
    'tsx_exists': 'YES' if TSX.exists() else 'NO',
    'live_board_exists': 'YES' if BOARD.exists() else 'NO',
    'terminal_exists': 'YES' if TERM.exists() else 'NO',
    'tsx_has_v7_2_refs': 'YES' if 'edgeiq_v7_2' in text else 'NO',
    'live_board_has_v7_2_preview': 'YES' if has_cols(board, PREVIEW) else 'NO',
    'live_board_has_active_shadow': 'YES' if has_cols(board, SHADOW) else 'NO',
    'terminal_has_v7_2_preview': 'YES' if has_cols(term, PREVIEW) else 'NO',
    'live_board_feature_flag_values': values(board,'edgeiq_v7_2_feature_flag'),
    'live_board_live_wired_values': values(board,'edgeiq_v7_2_live_wired_flag'),
    'live_board_production_changed_values': values(board,'edgeiq_v7_2_production_changed'),
    'ui_price_tokens_found': ui_price_tokens,
    'recommended_ui_wiring_mode': mode,
    'status': 'UI_PRICE_FIELD_USAGE_AUDITED' if mode != 'BLOCKED_SCHEMA_MISSING' else 'UI_PRICE_FIELD_USAGE_BLOCKED_SCHEMA_MISSING',
}
pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_csv(SUM, index=False)
report = f'''EDGEiQ V7.2 UI PRICE FIELD USAGE V1

- TSX exists: {metrics['tsx_exists']}
- Live board exists: {metrics['live_board_exists']}
- Terminal exists: {metrics['terminal_exists']}
- TSX has V7.2 refs: {metrics['tsx_has_v7_2_refs']}
- Live board has V7.2 preview: {metrics['live_board_has_v7_2_preview']}
- Live board has active shadow: {metrics['live_board_has_active_shadow']}
- Terminal has V7.2 preview: {metrics['terminal_has_v7_2_preview']}
- Feature flag values: {metrics['live_board_feature_flag_values']}
- Live wired values: {metrics['live_board_live_wired_values']}
- Production changed values: {metrics['live_board_production_changed_values']}
- UI price tokens found: {ui_price_tokens}
- Recommended UI wiring mode: {mode}
- Status: {metrics['status']}
'''
REP.write_text(report, encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_string(index=False))
print(report)
