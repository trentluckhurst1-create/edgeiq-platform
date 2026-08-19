from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import re

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'public' / 'data'
TERM_PREF = [DATA / 'edgeiq_live_terminal_feed_v1.csv', DATA / 'edgeiq_vic_live_terminal_feed_v1.csv']
HYBRID = DATA / 'edgeiq_current_day_v7_2_hybrid_candidate_v1.csv'
OUT = DATA / 'edgeiq_live_terminal_feed_v7_2_feature_flag_candidate.csv'
AUD = DATA / 'edgeiq_live_terminal_feed_v7_2_feature_flag_candidate_audit_v1.csv'
SUM = DATA / 'edgeiq_live_terminal_feed_v7_2_feature_flag_candidate_summary_v1.csv'
REP = DATA / 'edgeiq_live_terminal_feed_v7_2_feature_flag_candidate_report_v1.txt'

def read(p): return pd.read_csv(p, dtype=str, keep_default_na=False, low_memory=False) if p and p.exists() else pd.DataFrame()
def pick(paths):
    for p in paths:
        if p.exists(): return p
    return None
def rel(p): return str(p.relative_to(BASE)) if p else 'MISSING'
def norm_date(v):
    raw = '' if pd.isna(v) else str(v).strip(); dt = pd.to_datetime(raw, errors='coerce')
    return raw.upper() if pd.isna(dt) else dt.strftime('%Y-%m-%d')
def norm_track(v): return re.sub(r'\s+',' ',('' if pd.isna(v) else str(v)).upper().strip())
def norm_race(v):
    raw = '' if pd.isna(v) else str(v).upper().strip(); m = re.search(r'\d+', raw)
    return str(int(m.group(0))) if m else raw
def norm_horse(v):
    raw = ('' if pd.isna(v) else str(v)).upper().strip(); raw = re.sub(r'[^A-Z0-9\s]','', raw)
    return re.sub(r'\s+',' ', raw).strip()
def key(df): return df['race_date'].map(norm_date)+'|'+df['track'].map(norm_track)+'|'+df['race_no'].map(norm_race)+'|'+df['horse'].map(norm_horse)
def first_series(df, cols):
    out = pd.Series([''] * len(df), index=df.index, dtype=object)
    for col in cols:
        if col in df.columns:
            vals = df[col].fillna('').astype(str)
            out = out.where(out.astype(str).str.strip().ne(''), vals)
    return out.fillna('').astype(str)
def metric_df(m): return pd.DataFrame([{'metric': k, 'value': v} for k, v in m.items()])

built_at = datetime.now(timezone.utc).isoformat()
term_path = pick(TERM_PREF)
term = read(term_path); cand = read(HYBRID)
blocked = term.empty or cand.empty
if blocked:
    out = term.copy(); status = 'TERMINAL_FEATURE_FLAG_CANDIDATE_BLOCKED_SCHEMA_MISSING'; matched_rows = 0
else:
    out = term.copy(); out['_join_key'] = key(out)
    if 'edgeiq_v7_2_join_key' not in cand.columns:
        cand = cand.copy(); cand['edgeiq_v7_2_join_key'] = key(cand)
    ccols = ['edgeiq_v7_2_join_key'] + [c for c in ['edgeiq_probability_v7_2','edgeiq_fair_price_v7_2','edgeiq_display_fair_price_v7_2','probability_source_v7_2','edgeiq_price_engine_version_v7_2','edgeiq_display_price_engine_version_v7_2'] if c in cand.columns]
    cmap = cand[ccols].drop_duplicates('edgeiq_v7_2_join_key', keep='first')
    out = out.merge(cmap, left_on='_join_key', right_on='edgeiq_v7_2_join_key', how='left')
    for c in ['edgeiq_probability_v7_2','edgeiq_fair_price_v7_2','edgeiq_display_fair_price_v7_2','probability_source_v7_2','edgeiq_price_engine_version_v7_2','edgeiq_display_price_engine_version_v7_2']:
        if c not in out.columns: out[c] = ''
        out[c] = out[c].fillna('').astype(str)
    out['edgeiq_v7_2_probability_source'] = out['probability_source_v7_2']
    out['edgeiq_v7_2_price_engine_version'] = out['edgeiq_price_engine_version_v7_2'].replace('', 'V7_2_HYBRID_CURRENT_DAY_T6')
    out['edgeiq_v7_2_display_price_engine_version'] = out['edgeiq_display_price_engine_version_v7_2'].replace('', 'V7_2_DISPLAY_FAIR_PRICE_LAYER_CURRENT_DAY')
    out['edgeiq_v7_2_feature_flag'] = 'OFF'
    out['edgeiq_v7_2_live_wired_flag'] = 'NO'
    out['edgeiq_v7_2_production_changed'] = 'NO'
    out['edgeiq_active_probability_shadow'] = first_series(out, ['win_pct','probability','ui_probability'])
    out['edgeiq_active_fair_price_shadow'] = first_series(out, ['fair_price','ui_fair_price','rated_price','ui_price'])
    out['edgeiq_active_display_fair_price_shadow'] = first_series(out, ['ui_fair_price','fair_price','rated_price','ui_price'])
    out['edgeiq_active_price_source_shadow'] = 'PRODUCTION_FALLBACK_FEATURE_FLAG_OFF'
    out['edgeiq_v7_2_preview_probability'] = out['edgeiq_probability_v7_2']
    out['edgeiq_v7_2_preview_fair_price'] = out['edgeiq_fair_price_v7_2']
    out['edgeiq_v7_2_preview_display_fair_price'] = out['edgeiq_display_fair_price_v7_2']
    out['edgeiq_v7_2_preview_price_source'] = out['edgeiq_v7_2_probability_source']
    out['edgeiq_v7_2_join_key'] = out['_join_key']
    matched = out['edgeiq_probability_v7_2'].astype(str).str.strip().ne('') | out['edgeiq_display_fair_price_v7_2'].astype(str).str.strip().ne('')
    matched_rows = int(matched.sum())
    out = out.drop(columns=['_join_key'], errors='ignore')
    if len(out) != len(term) or set(out['edgeiq_v7_2_production_changed'].unique()) != {'NO'}:
        status = 'TERMINAL_FEATURE_FLAG_CANDIDATE_BLOCKED'
    elif matched_rows == 0:
        status = 'TERMINAL_FEATURE_FLAG_CANDIDATE_PASS_REVIEW_REQUIRED_ZERO_MATCH'
    else:
        status = 'TERMINAL_FEATURE_FLAG_CANDIDATE_PASS'

out.to_csv(OUT, index=False)
shadow_fair = first_series(term, ['fair_price','ui_fair_price','rated_price','ui_price']) if not term.empty else pd.Series(dtype=str)
shadow_display = first_series(term, ['ui_fair_price','fair_price','rated_price','ui_price']) if not term.empty else pd.Series(dtype=str)
shadow_equal = int(((out.get('edgeiq_active_fair_price_shadow', pd.Series(dtype=str)).astype(str).values == shadow_fair.astype(str).values) & (out.get('edgeiq_active_display_fair_price_shadow', pd.Series(dtype=str)).astype(str).values == shadow_display.astype(str).values)).sum()) if len(out) == len(term) and len(out) else 0
metrics = {
    'built_at': built_at,
    'terminal_source_file_used': rel(term_path),
    'v7_2_source_file_used': rel(HYBRID),
    'terminal_rows': len(term),
    'output_rows': len(out),
    'matched_rows': matched_rows,
    'unmatched_rows': len(out) - matched_rows,
    'match_rate_pct': round(matched_rows / len(out) * 100, 4) if len(out) else 0,
    'v7_2_probability_rows': int(out.get('edgeiq_probability_v7_2', pd.Series(dtype=str)).astype(str).str.strip().ne('').sum()) if len(out) else 0,
    'v7_2_display_fair_rows': int(out.get('edgeiq_display_fair_price_v7_2', pd.Series(dtype=str)).astype(str).str.strip().ne('').sum()) if len(out) else 0,
    'feature_flag_values': ','.join(sorted(out.get('edgeiq_v7_2_feature_flag', pd.Series([''])).astype(str).unique())) if len(out) else '',
    'live_wired_values': ','.join(sorted(out.get('edgeiq_v7_2_live_wired_flag', pd.Series([''])).astype(str).unique())) if len(out) else '',
    'production_changed_values': ','.join(sorted(out.get('edgeiq_v7_2_production_changed', pd.Series([''])).astype(str).unique())) if len(out) else '',
    'old_ui_price_column_preserved': 'YES' if 'ui_price' in out.columns else 'NO',
    'old_ui_fair_price_column_preserved': 'YES' if 'ui_fair_price' in out.columns else 'NO',
    'old_live_price_column_preserved': 'YES' if 'live_price' in out.columns else 'NO',
    'old_market_price_column_preserved': 'YES' if 'market_price' in out.columns else 'NO',
    'old_fair_price_column_preserved': 'YES' if 'fair_price' in out.columns else 'NOT_APPLICABLE',
    'shadow_fields_equal_fallback_rows': shadow_equal,
    'preview_fields_populated_rows': int(out.get('edgeiq_v7_2_preview_display_fair_price', pd.Series(dtype=str)).astype(str).str.strip().ne('').sum()) if len(out) else 0,
    'row_count_unchanged': 'YES' if len(out) == len(term) else 'NO',
    'status': status,
}
metric_df(metrics).to_csv(SUM, index=False)
pd.DataFrame([metrics]).to_csv(AUD, index=False)
report = f'''EDGEiQ LIVE TERMINAL FEED V7.2 FEATURE-FLAG CANDIDATE V1

- Candidate only.
- No terminal feed overwrite.
- Feature flag: {metrics['feature_flag_values']}
- Live wired: {metrics['live_wired_values']}
- Production changed: {metrics['production_changed_values']}
- Terminal rows: {metrics['terminal_rows']}
- Output rows: {metrics['output_rows']}
- Matched rows: {metrics['matched_rows']}
- Match rate pct: {metrics['match_rate_pct']}
- Shadow fields equal fallback rows: {metrics['shadow_fields_equal_fallback_rows']}
- Status: {status}

Zero V7.2 matches are review-required, not fatal, because the terminal feed may be a different date/meeting universe from the live-board candidate source. Active/shadow fields remain production fallback because feature flag is OFF.
'''
REP.write_text(report, encoding='utf-8')
print(metric_df(metrics).to_string(index=False))
print(report)
