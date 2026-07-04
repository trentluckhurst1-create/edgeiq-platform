from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import re

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'public' / 'data'
BOARD = DATA / 'edgeiq_live_runner_board_v7_2_feature_flag_on_candidate.csv'
TERM = DATA / 'edgeiq_live_terminal_feed_v7_2_feature_flag_on_candidate.csv'
OUT = DATA / 'edgeiq_v7_2_feature_flag_on_impact_v1.csv'
SUM = DATA / 'edgeiq_v7_2_feature_flag_on_impact_v1_summary.csv'
REP = DATA / 'edgeiq_v7_2_feature_flag_on_impact_v1_report.txt'

def read(path): return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False) if path.exists() else pd.DataFrame()
def values(df,col): return ','.join(sorted(df[col].fillna('').astype(str).unique())) if col in df.columns and len(df) else ''
def present(df,col): return int(df[col].fillna('').astype(str).str.strip().ne('').sum()) if col in df.columns else 0
def num(df,col): return pd.to_numeric(df[col].replace('', pd.NA), errors='coerce') if col in df.columns else pd.Series([pd.NA]*len(df))
def race_key(df):
    if not {'race_date','track','race_no'}.issubset(df.columns): return pd.Series(['']*len(df), index=df.index)
    return df['race_date'].astype(str)+'|'+df['track'].astype(str).str.upper()+'|'+df['race_no'].astype(str)
def rank_breaks(df):
    if df.empty: return (0,0)
    probs = num(df,'edgeiq_active_probability_shadow')
    disp = num(df,'edgeiq_active_display_fair_price_shadow')
    temp = df.copy(); temp['_p']=probs; temp['_d']=disp; temp['_race']=race_key(temp); temp['_row_order']=range(len(temp))
    breaks=0; top_second=0
    for _, g in temp.dropna(subset=['_p','_d']).groupby('_race'):
        if len(g) < 2: continue
        gg = g.sort_values(['_p','_row_order'], ascending=[False, True], kind='mergesort')
        vals = gg['_d'].astype(float).tolist()
        if any(vals[i] > vals[i+1] + 1e-9 for i in range(len(vals)-1)): breaks += 1
        if vals[0] > vals[1] + 1e-9: top_second += 1
    return breaks, top_second
def audit(label, path):
    df = read(path)
    active_rows = int((df.get('edgeiq_active_price_source_shadow', pd.Series(dtype=str)) == 'V7_2_PREVIEW_FEATURE_FLAG_ON_CANDIDATE').sum()) if len(df) else 0
    fallback_rows = int((df.get('edgeiq_active_price_source_shadow', pd.Series(dtype=str)) == 'PRODUCTION_FALLBACK_V7_2_PREVIEW_MISSING').sum()) if len(df) else 0
    active_fair = num(df,'edgeiq_active_fair_price_shadow')
    active_disp = num(df,'edgeiq_active_display_fair_price_shadow')
    preview_disp = num(df,'edgeiq_v7_2_preview_display_fair_price')
    rb, ts = rank_breaks(df)
    return {'file_label': label, 'file': str(path.relative_to(BASE)), 'rows': len(df), 'feature_flag_values': values(df,'edgeiq_v7_2_feature_flag'), 'preview_probability_rows': present(df,'edgeiq_v7_2_preview_probability'), 'preview_fair_rows': present(df,'edgeiq_v7_2_preview_fair_price'), 'preview_display_rows': present(df,'edgeiq_v7_2_preview_display_fair_price'), 'active_v7_2_rows': active_rows, 'fallback_rows': fallback_rows, 'null_active_fair_rows': int(active_fair.isna().sum()), 'display_min': '' if preview_disp.dropna().empty else float(preview_disp.min()), 'display_max': '' if preview_disp.dropna().empty else float(preview_disp.max()), 'active_fair_min': '' if active_fair.dropna().empty else float(active_fair.min()), 'active_fair_max': '' if active_fair.dropna().empty else float(active_fair.max()), 'active_display_fair_min': '' if active_disp.dropna().empty else float(active_disp.min()), 'active_display_fair_max': '' if active_disp.dropna().empty else float(active_disp.max()), 'rows_active_display_above_10': int((active_disp > 10).sum()), 'rows_active_display_above_20': int((active_disp > 20).sum()), 'rank_order_breaks_by_race': rb, 'top_pick_longer_than_second': ts, 'production_changed_values': values(df,'edgeiq_v7_2_production_changed'), 'live_wired_values': values(df,'edgeiq_v7_2_live_wired_flag')}
rows = [audit('LIVE_BOARD', BOARD), audit('TERMINAL_FEED', TERM)]
pd.DataFrame(rows).to_csv(OUT, index=False)
board_ok = rows[0]['active_v7_2_rows'] > 0 and rows[0]['rank_order_breaks_by_race'] == 0 and rows[0]['top_pick_longer_than_second'] == 0
term_ok = rows[1]['active_v7_2_rows'] >= 0
safe = all(r['production_changed_values'] == 'NO' and r['live_wired_values'] == 'NO' for r in rows)
status = 'FEATURE_FLAG_ON_IMPACT_PASS_REVIEW_REQUIRED' if board_ok and term_ok and safe else 'FEATURE_FLAG_ON_IMPACT_BLOCKED'
metrics = {'built_at': datetime.now(timezone.utc).isoformat(), 'board_rows': rows[0]['rows'], 'board_active_v7_2_rows': rows[0]['active_v7_2_rows'], 'board_fallback_rows': rows[0]['fallback_rows'], 'board_rank_order_breaks_by_race': rows[0]['rank_order_breaks_by_race'], 'board_top_pick_longer_than_second': rows[0]['top_pick_longer_than_second'], 'board_active_display_fair_min': rows[0]['active_display_fair_min'], 'board_active_display_fair_max': rows[0]['active_display_fair_max'], 'terminal_rows': rows[1]['rows'], 'terminal_active_v7_2_rows': rows[1]['active_v7_2_rows'], 'terminal_fallback_rows': rows[1]['fallback_rows'], 'production_changed_values': f"{rows[0]['production_changed_values']} | {rows[1]['production_changed_values']}", 'live_wired_values': f"{rows[0]['live_wired_values']} | {rows[1]['live_wired_values']}", 'status': status}
pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_csv(SUM, index=False)
report = f'''EDGEiQ V7.2 FEATURE FLAG ON IMPACT V1

- Status: {status}
- Board active V7.2 rows: {metrics['board_active_v7_2_rows']}
- Board fallback rows: {metrics['board_fallback_rows']}
- Board rank order breaks by race: {metrics['board_rank_order_breaks_by_race']}
- Board top pick longer than second: {metrics['board_top_pick_longer_than_second']}
- Board active display fair range: {metrics['board_active_display_fair_min']} to {metrics['board_active_display_fair_max']}
- Terminal active V7.2 rows: {metrics['terminal_active_v7_2_rows']}
- Terminal fallback rows: {metrics['terminal_fallback_rows']}
- Production changed values: {metrics['production_changed_values']}
- Live wired values: {metrics['live_wired_values']}
'''
REP.write_text(report, encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_string(index=False))
print(report)

