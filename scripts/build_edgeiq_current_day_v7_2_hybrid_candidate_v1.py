from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import re

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'public' / 'data'
INPUT = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
OUT = DATA / 'edgeiq_current_day_v7_2_hybrid_candidate_v1.csv'
SUM = DATA / 'edgeiq_current_day_v7_2_hybrid_candidate_v1_summary.csv'
AUD = DATA / 'edgeiq_current_day_v7_2_hybrid_candidate_v1_audit.csv'
REP = DATA / 'edgeiq_current_day_v7_2_hybrid_candidate_v1_report.txt'
TEMP = 6.0
HIERARCHY = [
    ('total_rating_points','TOTAL_RATING_POINTS','RATING'),
    ('runner_score_v3','RUNNER_SCORE_V3','RATING'),
    ('runner_score_v2','RUNNER_SCORE_V2','RATING'),
    ('governed_projection_rating_v6','PROJECTION_RATING_V6','RATING'),
    ('confidence_adjusted_rating_v6','CONFIDENCE_ADJUSTED_RATING_V6','RATING'),
    ('strength_adjusted_rating_v6','STRENGTH_ADJUSTED_RATING_V6','RATING'),
    ('projected_rating_v5_2','PROJECTED_RATING_V5_2','RATING'),
    ('runner_dna_v6_2_score','DNA_SCORE','RATING'),
    ('win_pct','WIN_PCT','PROBABILITY'),
    ('V6_1_RESEARCH_price_rank','RANK_WEIGHTED','RANK'),
]

def read(p): return pd.read_csv(p, dtype=str, keep_default_na=False, low_memory=False) if p.exists() else pd.DataFrame()
def norm_date(v):
    raw='' if pd.isna(v) else str(v).strip(); dt=pd.to_datetime(raw, errors='coerce')
    return raw.upper() if pd.isna(dt) else dt.strftime('%Y-%m-%d')
def norm_track(v): return re.sub(r'\s+',' ',('' if pd.isna(v) else str(v)).upper().strip())
def norm_race(v):
    raw='' if pd.isna(v) else str(v).upper().strip(); m=re.search(r'\d+', raw)
    return str(int(m.group(0))) if m else raw
def norm_horse(v):
    raw=('' if pd.isna(v) else str(v)).upper().strip(); raw=re.sub(r'[^A-Z0-9\s]','',raw)
    return re.sub(r'\s+',' ',raw).strip()
def date_col(df):
    for c in ['race_date','meeting_date','date']:
        if c in df.columns: return c
    return None
def race_key(df):
    dc=date_col(df); d=df[dc].map(norm_date) if dc else pd.Series(['']*len(df), index=df.index)
    return d + '|' + df['track'].map(norm_track) + '|' + df['race_no'].map(norm_race)
def join_key(df): return race_key(df) + '|' + df['horse'].map(norm_horse)
def display_mult(rank):
    if rank == 1: return 1.00
    if rank == 2: return 1.05
    if rank == 3: return 1.15
    if rank <= 5: return 1.30
    if rank <= 8: return 1.55
    return 1.85

def usable_numeric(df, col, idx):
    if col not in df.columns: return pd.Series([], dtype=float)
    return pd.to_numeric(df.loc[idx, col].replace('', pd.NA), errors='coerce')

df = read(INPUT)
built_at = datetime.now(timezone.utc).isoformat()
if df.empty:
    pd.DataFrame().to_csv(OUT, index=False)
    summary = pd.DataFrame([{'metric':'status','value':'BLOCKED_INPUT_MISSING'}, {'metric':'production_changed','value':'NO'}])
    summary.to_csv(SUM,index=False)
    pd.DataFrame([{'status':'BLOCKED_INPUT_MISSING'}]).to_csv(AUD,index=False)
    REP.write_text('EDGEiQ CURRENT-DAY V7.2 HYBRID CANDIDATE V1\n\nBlocked: input missing.\nProduction changed: NO\n', encoding='utf-8')
    print(summary.to_string(index=False)); print(REP.read_text(encoding='utf-8'))
    raise SystemExit

out = df.copy()
out['_race_key_v7_2'] = race_key(out)
out['edgeiq_v7_2_join_key'] = join_key(out)
prob = pd.Series(np.nan, index=out.index, dtype=float)
source = pd.Series('', index=out.index, dtype=str)

for rk, idx_obj in out.groupby('_race_key_v7_2', dropna=False).groups.items():
    idx = list(idx_obj); n = len(idx)
    remaining = pd.Index(idx)
    weights = pd.Series(np.nan, index=idx, dtype=float)
    row_source = pd.Series('', index=idx, dtype=str)
    for col, label, kind in HIERARCHY:
        if len(remaining) == 0: break
        vals = usable_numeric(out, col, remaining)
        usable = vals.notna()
        use_idx = vals[usable].index
        if len(use_idx) == 0: continue
        if kind == 'PROBABILITY':
            v = vals.loc[use_idx].astype(float)
            if v.max() > 1.0: v = v / 100.0
            v = v.clip(lower=0.000001)
            weights.loc[use_idx] = v
        elif kind == 'RANK':
            v = vals.loc[use_idx].astype(float).where(lambda s: s > 0)
            weights.loc[use_idx] = 1.0 / v.fillna(v.max() + 1)
        else:
            v = vals.loc[use_idx].astype(float)
            # Convert mixed-source ratings to within-race softmax-like positive weights.
            if len(v) >= 2 and float(v.std(ddof=0)) > 0:
                z = (v - v.mean()) / v.std(ddof=0)
                weights.loc[use_idx] = np.exp(np.clip(z / TEMP, -50, 50))
            else:
                centered = v - v.mean()
                weights.loc[use_idx] = np.exp(np.clip(centered / TEMP, -50, 50))
        row_source.loc[use_idx] = label
        remaining = remaining.difference(use_idx)
    if len(remaining) > 0:
        weights.loc[remaining] = 1.0
        row_source.loc[remaining] = 'EQUAL_PROBABILITY'
    if weights.fillna(0).sum() <= 0:
        weights.loc[idx] = 1.0
        row_source.loc[idx] = 'EQUAL_PROBABILITY'
    prob.loc[idx] = weights.loc[idx] / weights.loc[idx].sum()
    source.loc[idx] = row_source.loc[idx]

out['probability_source_v7_2'] = source
out['edgeiq_probability_v7_2'] = prob.astype(float)
out['edgeiq_fair_price_v7_2'] = (1.0 / out['edgeiq_probability_v7_2']).replace([np.inf,-np.inf], np.nan)
out['edgeiq_price_engine_version_v7_2'] = 'V7_2_HYBRID_CURRENT_DAY_T6'
out['edgeiq_display_price_engine_version_v7_2'] = 'V7_2_DISPLAY_FAIR_PRICE_LAYER_CURRENT_DAY'
out['edgeiq_v7_2_feature_flag'] = 'OFF'
out['edgeiq_v7_2_live_wired_flag'] = 'NO'
out['edgeiq_v7_2_production_changed'] = 'NO'
out['edgeiq_v7_2_built_at'] = built_at
out['__rank_v7_2'] = out.groupby('_race_key_v7_2')['edgeiq_probability_v7_2'].rank(method='first', ascending=False).astype(int)
out['__display_v7_2'] = (out['edgeiq_fair_price_v7_2'] * out['__rank_v7_2'].map(display_mult)).clip(lower=1.01, upper=100.0)
for rk, g in out.groupby('_race_key_v7_2'):
    order = g.sort_values('__rank_v7_2').index.tolist()
    last = 1.01
    for i in order:
        val = float(out.at[i, '__display_v7_2']) if pd.notna(out.at[i, '__display_v7_2']) else last
        if val < last: val = last
        out.at[i, '__display_v7_2'] = min(max(val, 1.01), 100.0)
        last = out.at[i, '__display_v7_2']
out['edgeiq_display_fair_price_v7_2'] = out['__display_v7_2']

race_sums = out.groupby('_race_key_v7_2')['edgeiq_probability_v7_2'].sum()
prob_ok = int(((race_sums - 1.0).abs() <= 0.0001).sum())
prob_bad = int(((race_sums - 1.0).abs() > 0.0001).sum())
rank_breaks = 0; top_second = 0
for rk, g in out.groupby('_race_key_v7_2'):
    vals = g.sort_values('__rank_v7_2')['edgeiq_display_fair_price_v7_2'].astype(float).tolist()
    if any(vals[i] > vals[i+1] + 1e-9 for i in range(len(vals)-1)): rank_breaks += 1
    if len(vals) >= 2 and vals[0] > vals[1] + 1e-9: top_second += 1
source_counts = out['probability_source_v7_2'].value_counts().to_dict()
equal_rows = int((out['probability_source_v7_2'] == 'EQUAL_PROBABILITY').sum())
real_rows = len(out) - equal_rows
status = 'CURRENT_DAY_V7_2_HYBRID_CANDIDATE_BUILT_REVIEW_REQUIRED'
if prob_bad > 0: status = 'CURRENT_DAY_V7_2_HYBRID_BLOCKED_PROBABILITY_SUM_BAD'
elif rank_breaks > 0: status = 'CURRENT_DAY_V7_2_HYBRID_BLOCKED_RANK_ORDER_BREAKS'

out.drop(columns=['_race_key_v7_2','__rank_v7_2','__display_v7_2'], errors='ignore').to_csv(OUT, index=False)
audit = pd.DataFrame([{
    'rows': len(out), 'races': int(out['_race_key_v7_2'].nunique()), 'probability_rows': int(out['edgeiq_probability_v7_2'].notna().sum()), 'display_fair_rows': int(out['edgeiq_display_fair_price_v7_2'].notna().sum()), 'probability_sum_ok_races': prob_ok, 'probability_sum_bad_races': prob_bad, 'min_probability': float(out['edgeiq_probability_v7_2'].min()), 'max_probability': float(out['edgeiq_probability_v7_2'].max()), 'min_fair_price': float(out['edgeiq_fair_price_v7_2'].min()), 'max_fair_price': float(out['edgeiq_fair_price_v7_2'].max()), 'min_display_fair': float(out['edgeiq_display_fair_price_v7_2'].min()), 'max_display_fair': float(out['edgeiq_display_fair_price_v7_2'].max()), 'equal_probability_rows': equal_rows, 'real_model_rows': real_rows, 'source_counts': str(source_counts), 'rank_order_breaks': rank_breaks, 'top_pick_longer_than_second': top_second, 'feature_flag_values': 'OFF', 'live_wired_values': 'NO', 'production_changed_values': 'NO', 'status': status
}])
audit.to_csv(AUD, index=False)
metrics = {'built_at': built_at, 'input_file': str(INPUT.relative_to(BASE)), 'rows': len(out), 'races': int(out['_race_key_v7_2'].nunique()), 'real_model_rows': real_rows, 'equal_probability_rows': equal_rows, 'equal_probability_pct': round(equal_rows/len(out)*100, 4) if len(out) else 0, 'probability_sum_ok_races': prob_ok, 'probability_sum_bad_races': prob_bad, 'rank_order_breaks': rank_breaks, 'top_pick_longer_than_second': top_second, 'min_display_fair': float(out['edgeiq_display_fair_price_v7_2'].min()), 'max_display_fair': float(out['edgeiq_display_fair_price_v7_2'].max()), 'source_counts': str(source_counts), 'feature_flag_values': 'OFF', 'live_wired_values': 'NO', 'production_changed_values': 'NO', 'status': status}
summary = pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()])
summary.to_csv(SUM, index=False)
report = f'''EDGEiQ CURRENT-DAY V7.2 HYBRID CANDIDATE V1

- Candidate only.
- Input: {INPUT.relative_to(BASE)}
- Rows: {len(out)}
- Races: {metrics['races']}
- Real model rows: {real_rows}
- Equal probability rows: {equal_rows}
- Equal probability pct: {metrics['equal_probability_pct']}
- Probability sum ok races: {prob_ok}
- Probability sum bad races: {prob_bad}
- Display fair range: {metrics['min_display_fair']} to {metrics['max_display_fair']}
- Rank order breaks: {rank_breaks}
- Top pick longer than second: {top_second}
- Source counts: {source_counts}
- Feature flag: OFF
- Live wired: NO
- Production changed: NO
- Status: {status}

V7.2 uses the requested hierarchy to reduce equal-probability fallback before any controlled wiring is considered.
'''
REP.write_text(report, encoding='utf-8')
print(summary.to_string(index=False))
print(report)
