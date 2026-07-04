from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'public' / 'data'
BOARD_IN = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
TERM_IN = DATA / 'edgeiq_live_terminal_feed_v1.csv'
BOARD_OUT = DATA / 'edgeiq_live_runner_board_v7_2_feature_flag_on_candidate.csv'
TERM_OUT = DATA / 'edgeiq_live_terminal_feed_v7_2_feature_flag_on_candidate.csv'
OUT = DATA / 'edgeiq_v7_2_feature_flag_on_data_candidate_v1.csv'
SUM = DATA / 'edgeiq_v7_2_feature_flag_on_data_candidate_v1_summary.csv'
REP = DATA / 'edgeiq_v7_2_feature_flag_on_data_candidate_v1_report.txt'

def read(path): return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False) if path.exists() else pd.DataFrame()
def first_series(df, cols):
    out = pd.Series([''] * len(df), index=df.index, dtype=object)
    for col in cols:
        if col in df.columns:
            vals = df[col].fillna('').astype(str)
            out = out.where(out.astype(str).str.strip().ne(''), vals)
    return out.fillna('').astype(str)
def present(df, col): return int(df[col].fillna('').astype(str).str.strip().ne('').sum()) if col in df.columns else 0
def values(df, col): return ','.join(sorted(df[col].fillna('').astype(str).unique())) if col in df.columns and len(df) else ''
def build_candidate(df):
    out = df.copy()
    for col in ['edgeiq_v7_2_preview_probability','edgeiq_v7_2_preview_fair_price','edgeiq_v7_2_preview_display_fair_price']:
        if col not in out.columns: out[col] = ''
    out['edgeiq_v7_2_feature_flag'] = 'ON'
    out['edgeiq_v7_2_live_wired_flag'] = 'NO'
    out['edgeiq_v7_2_production_changed'] = 'NO'
    preview = out['edgeiq_v7_2_preview_display_fair_price'].fillna('').astype(str).str.strip().ne('')
    prod_prob = first_series(out, ['win_pct','V6_1_RESEARCH_probability','probability_normalised_v1','probability'])
    prod_fair = first_series(out, ['fair_price','ui_fair_price','display_fair_price','rated_price','ui_price'])
    prod_display = first_series(out, ['ui_fair_price','display_fair_price','fair_price','rated_price','ui_price'])
    out['edgeiq_active_probability_shadow'] = out['edgeiq_v7_2_preview_probability'].where(preview, prod_prob)
    out['edgeiq_active_fair_price_shadow'] = out['edgeiq_v7_2_preview_fair_price'].where(preview, prod_fair)
    out['edgeiq_active_display_fair_price_shadow'] = out['edgeiq_v7_2_preview_display_fair_price'].where(preview, prod_display)
    out['edgeiq_active_price_source_shadow'] = preview.map(lambda x: 'V7_2_PREVIEW_FEATURE_FLAG_ON_CANDIDATE' if x else 'PRODUCTION_FALLBACK_V7_2_PREVIEW_MISSING')
    return out

built_at = datetime.now(timezone.utc).isoformat()
board = read(BOARD_IN); term = read(TERM_IN)
board_c = build_candidate(board) if not board.empty else board
term_c = build_candidate(term) if not term.empty else term
board_c.to_csv(BOARD_OUT, index=False)
term_c.to_csv(TERM_OUT, index=False)

def row(label, source, df):
    preview = present(df, 'edgeiq_v7_2_preview_display_fair_price')
    active = int((df.get('edgeiq_active_price_source_shadow', pd.Series(dtype=str)) == 'V7_2_PREVIEW_FEATURE_FLAG_ON_CANDIDATE').sum()) if len(df) else 0
    fallback = int((df.get('edgeiq_active_price_source_shadow', pd.Series(dtype=str)) == 'PRODUCTION_FALLBACK_V7_2_PREVIEW_MISSING').sum()) if len(df) else 0
    return {'file_label': label, 'source_file': str(source.relative_to(BASE)), 'rows': len(df), 'preview_rows': preview, 'flag_on_rows': int((df.get('edgeiq_v7_2_feature_flag', pd.Series(dtype=str)) == 'ON').sum()) if len(df) else 0, 'v7_2_active_rows': active, 'fallback_rows': fallback, 'production_changed_values': values(df, 'edgeiq_v7_2_production_changed'), 'live_wired_values': values(df, 'edgeiq_v7_2_live_wired_flag')}
rows = [row('LIVE_BOARD', BOARD_OUT, board_c), row('TERMINAL_FEED', TERM_OUT, term_c)]
pd.DataFrame(rows).to_csv(OUT, index=False)
blocked = len(board_c) != len(board) or len(term_c) != len(term) or values(board_c,'edgeiq_v7_2_feature_flag') != 'ON' or values(term_c,'edgeiq_v7_2_feature_flag') != 'ON' or values(board_c,'edgeiq_v7_2_production_changed') != 'NO' or values(term_c,'edgeiq_v7_2_production_changed') != 'NO'
status = 'BLOCKED' if blocked else 'FEATURE_FLAG_ON_DATA_CANDIDATE_BUILT_REVIEW_REQUIRED'
metrics = {
    'built_at': built_at,
    'board_rows': len(board_c),
    'board_preview_rows': rows[0]['preview_rows'],
    'board_flag_on_rows': rows[0]['flag_on_rows'],
    'board_v7_2_active_rows': rows[0]['v7_2_active_rows'],
    'board_fallback_rows': rows[0]['fallback_rows'],
    'terminal_rows': len(term_c),
    'terminal_preview_rows': rows[1]['preview_rows'],
    'terminal_flag_on_rows': rows[1]['flag_on_rows'],
    'terminal_v7_2_active_rows': rows[1]['v7_2_active_rows'],
    'terminal_fallback_rows': rows[1]['fallback_rows'],
    'production_changed_values': f"{rows[0]['production_changed_values']} | {rows[1]['production_changed_values']}",
    'live_wired_values': f"{rows[0]['live_wired_values']} | {rows[1]['live_wired_values']}",
    'status': status,
}
pd.DataFrame([{'metric': k, 'value': v} for k,v in metrics.items()]).to_csv(SUM, index=False)
report = f'''EDGEiQ V7.2 FEATURE FLAG ON DATA CANDIDATE V1

- Candidate files only. Live files were not overwritten with ON values.
- Board rows: {metrics['board_rows']}
- Board preview rows: {metrics['board_preview_rows']}
- Board flag ON rows: {metrics['board_flag_on_rows']}
- Board V7.2 active rows: {metrics['board_v7_2_active_rows']}
- Board fallback rows: {metrics['board_fallback_rows']}
- Terminal rows: {metrics['terminal_rows']}
- Terminal preview rows: {metrics['terminal_preview_rows']}
- Terminal flag ON rows: {metrics['terminal_flag_on_rows']}
- Terminal V7.2 active rows: {metrics['terminal_v7_2_active_rows']}
- Terminal fallback rows: {metrics['terminal_fallback_rows']}
- Production changed values: {metrics['production_changed_values']}
- Live wired values: {metrics['live_wired_values']}
- Status: {status}
'''
REP.write_text(report, encoding='utf-8')
print(pd.DataFrame([{'metric': k, 'value': v} for k,v in metrics.items()]).to_string(index=False))
print(report)
