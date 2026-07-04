from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import re

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'public' / 'data'
LIVE_PREF = [DATA / 'edgeiq_live_runner_board_governed_v1.csv', DATA / 'edgeiq_live_runner_board_v1.csv']
JOIN_PREF = [DATA / 'edgeiq_live_runner_board_v7_2_candidate_join_v1.csv', DATA / 'edgeiq_live_runner_board_v7_2_candidate.csv']
HYBRID = DATA / 'edgeiq_current_day_v7_2_hybrid_candidate_v1.csv'
OUT = DATA / 'edgeiq_live_runner_board_v7_2_feature_flag_candidate.csv'
AUD = DATA / 'edgeiq_live_runner_board_v7_2_feature_flag_candidate_audit_v1.csv'
SUM = DATA / 'edgeiq_live_runner_board_v7_2_feature_flag_candidate_summary_v1.csv'
REP = DATA / 'edgeiq_live_runner_board_v7_2_feature_flag_candidate_report_v1.txt'

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
live_path = pick(LIVE_PREF); join_path = pick(JOIN_PREF)
live = read(live_path); joined = read(join_path); hybrid = read(HYBRID)
source_candidate = joined if not joined.empty else hybrid
source_path = join_path if not joined.empty else HYBRID
blocked = live.empty or source_candidate.empty
if blocked:
    out = live.copy()
    status = 'LIVE_BOARD_FEATURE_FLAG_CANDIDATE_BLOCKED_SCHEMA_MISSING'
else:
    out = live.copy(); out['_join_key'] = key(out)
    if 'edgeiq_v7_2_join_key' in source_candidate.columns:
        cand_key_col = 'edgeiq_v7_2_join_key'
    else:
        source_candidate = source_candidate.copy(); source_candidate['edgeiq_v7_2_join_key'] = key(source_candidate); cand_key_col = 'edgeiq_v7_2_join_key'
    ccols = [cand_key_col]
    for c in ['edgeiq_probability_v7_2','edgeiq_fair_price_v7_2','edgeiq_display_fair_price_v7_2','probability_source_v7_2','edgeiq_price_engine_version_v7_2','edgeiq_display_price_engine_version_v7_2']:
        if c in source_candidate.columns: ccols.append(c)
    cmap = source_candidate[ccols].drop_duplicates(cand_key_col, keep='first')
    out = out.merge(cmap, left_on='_join_key', right_on=cand_key_col, how='left', suffixes=('', '_v72src'))
    for c in ['edgeiq_probability_v7_2','edgeiq_fair_price_v7_2','edgeiq_display_fair_price_v7_2','probability_source_v7_2','edgeiq_price_engine_version_v7_2','edgeiq_display_price_engine_version_v7_2']:
        if c not in out.columns: out[c] = ''
        out[c] = out[c].fillna('').astype(str)
    out['edgeiq_v7_2_probability_source'] = out['probability_source_v7_2']
    out['edgeiq_v7_2_price_engine_version'] = out['edgeiq_price_engine_version_v7_2'].replace('', 'V7_2_HYBRID_CURRENT_DAY_T6')
    out['edgeiq_v7_2_display_price_engine_version'] = out['edgeiq_display_price_engine_version_v7_2'].replace('', 'V7_2_DISPLAY_FAIR_PRICE_LAYER_CURRENT_DAY')
    out['edgeiq_v7_2_feature_flag'] = 'OFF'
    out['edgeiq_v7_2_live_wired_flag'] = 'NO'
    out['edgeiq_v7_2_production_changed'] = 'NO'
    out['edgeiq_active_probability_shadow'] = first_series(out, ['win_pct','V6_1_RESEARCH_probability','probability_normalised_v1'])
    out['edgeiq_active_fair_price_shadow'] = first_series(out, ['fair_price','ui_fair_price','display_fair_price','rated_price'])
    out['edgeiq_active_display_fair_price_shadow'] = first_series(out, ['ui_fair_price','display_fair_price','fair_price','rated_price'])
    out['edgeiq_active_price_source_shadow'] = 'PRODUCTION_FALLBACK_FEATURE_FLAG_OFF'
    out['edgeiq_v7_2_preview_probability'] = out['edgeiq_probability_v7_2']
    out['edgeiq_v7_2_preview_fair_price'] = out['edgeiq_fair_price_v7_2']
    out['edgeiq_v7_2_preview_display_fair_price'] = out['edgeiq_display_fair_price_v7_2']
    out['edgeiq_v7_2_preview_price_source'] = out['edgeiq_v7_2_probability_source']
    out['edgeiq_v7_2_join_key'] = out['_join_key']
    out = out.drop(columns=['_join_key'], errors='ignore')
    v72_rows = int(out['edgeiq_probability_v7_2'].astype(str).str.strip().ne('').sum())
    preview_populated = int(out['edgeiq_v7_2_preview_display_fair_price'].astype(str).str.strip().ne('').sum())
    shadow_fair = first_series(live, ['fair_price','ui_fair_price','display_fair_price','rated_price'])
    shadow_display = first_series(live, ['ui_fair_price','display_fair_price','fair_price','rated_price'])
    shadow_equal = int(((out['edgeiq_active_fair_price_shadow'].astype(str).values == shadow_fair.astype(str).values) & (out['edgeiq_active_display_fair_price_shadow'].astype(str).values == shadow_display.astype(str).values)).sum())
    old_cols_preserved = all(c in out.columns for c in ['fair_price','ui_fair_price','live_price','win_pct'])
    if len(out) != len(live) or set(out['edgeiq_v7_2_production_changed'].unique()) != {'NO'}:
        status = 'LIVE_BOARD_FEATURE_FLAG_CANDIDATE_BLOCKED'
    elif set(out['edgeiq_v7_2_feature_flag'].unique()) == {'OFF'} and set(out['edgeiq_v7_2_live_wired_flag'].unique()) == {'NO'} and preview_populated == len(out) and old_cols_preserved:
        status = 'LIVE_BOARD_FEATURE_FLAG_CANDIDATE_PASS'
    else:
        status = 'LIVE_BOARD_FEATURE_FLAG_CANDIDATE_REVIEW_REQUIRED'

out.to_csv(OUT, index=False)
metrics = {
    'built_at': built_at,
    'live_source_file_used': rel(live_path),
    'v7_2_source_file_used': rel(source_path),
    'live_rows': len(live),
    'output_rows': len(out),
    'v7_2_rows_joined': int(out.get('edgeiq_probability_v7_2', pd.Series(dtype=str)).astype(str).str.strip().ne('').sum()) if len(out) else 0,
    'v7_2_probability_rows': int(out.get('edgeiq_probability_v7_2', pd.Series(dtype=str)).astype(str).str.strip().ne('').sum()) if len(out) else 0,
    'v7_2_display_fair_rows': int(out.get('edgeiq_display_fair_price_v7_2', pd.Series(dtype=str)).astype(str).str.strip().ne('').sum()) if len(out) else 0,
    'feature_flag_values': ','.join(sorted(out.get('edgeiq_v7_2_feature_flag', pd.Series([''])).astype(str).unique())) if len(out) else '',
    'live_wired_values': ','.join(sorted(out.get('edgeiq_v7_2_live_wired_flag', pd.Series([''])).astype(str).unique())) if len(out) else '',
    'production_changed_values': ','.join(sorted(out.get('edgeiq_v7_2_production_changed', pd.Series([''])).astype(str).unique())) if len(out) else '',
    'old_fair_price_column_preserved': 'YES' if 'fair_price' in out.columns else 'NO',
    'old_ui_fair_price_column_preserved': 'YES' if 'ui_fair_price' in out.columns else 'NO',
    'old_live_price_column_preserved': 'YES' if 'live_price' in out.columns else 'NO',
    'old_win_pct_column_preserved': 'YES' if 'win_pct' in out.columns else 'NO',
    'shadow_fields_equal_fallback_rows': shadow_equal if not blocked else 0,
    'preview_fields_populated_rows': int(out.get('edgeiq_v7_2_preview_display_fair_price', pd.Series(dtype=str)).astype(str).str.strip().ne('').sum()) if len(out) else 0,
    'row_count_unchanged': 'YES' if len(out) == len(live) else 'NO',
    'status': status,
}
metric_df(metrics).to_csv(SUM, index=False)
pd.DataFrame([metrics]).to_csv(AUD, index=False)
report = f'''EDGEiQ LIVE RUNNER BOARD V7.2 FEATURE-FLAG CANDIDATE V1

- Candidate only.
- No live board overwrite.
- Feature flag: {metrics['feature_flag_values']}
- Live wired: {metrics['live_wired_values']}
- Production changed: {metrics['production_changed_values']}
- Live rows: {metrics['live_rows']}
- Output rows: {metrics['output_rows']}
- V7.2 probability rows: {metrics['v7_2_probability_rows']}
- V7.2 display fair rows: {metrics['v7_2_display_fair_rows']}
- Shadow fields equal fallback rows: {metrics['shadow_fields_equal_fallback_rows']}
- Preview fields populated rows: {metrics['preview_fields_populated_rows']}
- Status: {status}

Active/shadow fields remain production fallback because feature flag is OFF. V7.2 values are present only as preview/candidate fields.
'''
REP.write_text(report, encoding='utf-8')
print(metric_df(metrics).to_string(index=False))
print(report)
