from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import re

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'public' / 'data'
LIVE = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
CAND = DATA / 'edgeiq_live_runner_board_v7_2_feature_flag_on_candidate.csv'
OUT = DATA / 'edgeiq_v7_2_activation_side_by_side_v1.csv'
SUM = DATA / 'edgeiq_v7_2_activation_side_by_side_v1_summary.csv'
REP = DATA / 'edgeiq_v7_2_activation_side_by_side_v1_report.txt'

def read(p): return pd.read_csv(p, dtype=str, keep_default_na=False, low_memory=False) if p.exists() else pd.DataFrame()
def norm_date(v):
    raw='' if pd.isna(v) else str(v).strip(); dt=pd.to_datetime(raw, errors='coerce')
    return raw.upper() if pd.isna(dt) else dt.strftime('%Y-%m-%d')
def norm_track(v): return re.sub(r'\s+',' ',('' if pd.isna(v) else str(v)).upper().strip())
def norm_race(v):
    raw='' if pd.isna(v) else str(v).upper().strip(); m=re.search(r'\d+', raw)
    return str(int(m.group(0))) if m else raw
def norm_horse(v):
    raw=('' if pd.isna(v) else str(v)).upper().strip(); raw=re.sub(r'[^A-Z0-9\s]','', raw)
    return re.sub(r'\s+',' ', raw).strip()
def get_date_col(df):
    for c in ['race_date','meeting_date','date']:
        if c in df.columns: return c
    return 'race_date'
def key(df): return df[get_date_col(df)].map(norm_date)+'|'+df['track'].map(norm_track)+'|'+df['race_no'].map(norm_race)+'|'+df['horse'].map(norm_horse)
def first_numeric(df, cols):
    out=pd.Series([pd.NA]*len(df), index=df.index, dtype='Float64')
    for c in cols:
        if c in df.columns:
            vals=pd.to_numeric(df[c].replace('', pd.NA), errors='coerce')
            out=out.where(out.notna(), vals)
    return out.astype('Float64')
def first_text(df, cols):
    out=pd.Series(['']*len(df), index=df.index, dtype=object)
    for c in cols:
        if c in df.columns:
            vals=df[c].fillna('').astype(str)
            out=out.where(out.astype(str).str.strip().ne(''), vals)
    return out.fillna('').astype(str)
def movement_band(pct):
    if pd.isna(pct): return 'UNKNOWN'
    a=abs(float(pct))
    if a < 5: return 'SAME_OR_TINY'
    if a < 15: return 'SMALL'
    if a < 30: return 'MEDIUM'
    if a <= 60: return 'LARGE'
    return 'EXTREME'

def suff(cols): return [c+'_cand' for c in cols] + cols

built_at=datetime.now(timezone.utc).isoformat()
live=read(LIVE); cand=read(CAND)
status='SIDE_BY_SIDE_COMPARISON_BUILT_REVIEW_REQUIRED'
if live.empty or cand.empty:
    out=pd.DataFrame(); status='BLOCKED_CANDIDATE_MISSING'
else:
    live=live.copy(); cand=cand.copy(); live['_join_key']=key(live); cand['_join_key']=key(cand)
    merged=live.merge(cand, on='_join_key', how='left', suffixes=('', '_cand'))
    prod_display=first_numeric(merged, ['ui_fair_price','display_fair_price','fair_price','rated_price','live_price'])
    v72_display=first_numeric(merged, suff(['edgeiq_active_display_fair_price_shadow','edgeiq_v7_2_preview_display_fair_price','edgeiq_display_fair_price_v7_2','edgeiq_fair_price_v7_2']))
    prod_fair=first_numeric(merged, ['fair_price'])
    prod_ui=first_numeric(merged, ['ui_fair_price'])
    prod_live=first_numeric(merged, ['live_price'])
    prod_win=first_numeric(merged, ['win_pct'])
    v72_prob=first_numeric(merged, suff(['edgeiq_active_probability_shadow','edgeiq_v7_2_preview_probability','edgeiq_probability_v7_2']))
    v72_fair=first_numeric(merged, suff(['edgeiq_active_fair_price_shadow','edgeiq_v7_2_preview_fair_price','edgeiq_fair_price_v7_2']))
    delta=(v72_display-prod_display).abs()
    pct=((v72_display-prod_display).abs()/prod_display.replace(0, pd.NA))*100
    base=pd.DataFrame({
        'race_date': merged[get_date_col(live)].map(norm_date),
        'track': merged['track'] if 'track' in merged.columns else '',
        'race_no': merged['race_no'] if 'race_no' in merged.columns else '',
        'runner_no': first_text(merged, ['runner_no','horse_no','saddlecloth']),
        'saddlecloth': first_text(merged, ['saddlecloth','horse_no','runner_no']),
        'horse': merged['horse'] if 'horse' in merged.columns else '',
        'production_live_price': prod_live,
        'production_fair_price': prod_fair,
        'production_ui_fair_price': prod_ui,
        'production_win_pct': prod_win,
        'v7_2_probability': v72_prob,
        'v7_2_fair_price': v72_fair,
        'v7_2_display_fair_price': v72_display,
        'production_display_price_used': prod_display,
        'v7_2_display_price_used': v72_display,
        'absolute_display_price_delta': delta,
        'pct_display_price_delta': pct,
        'v7_2_probability_source': first_text(merged, suff(['edgeiq_v7_2_probability_source','probability_source_v7_2','edgeiq_v7_2_preview_price_source','edgeiq_active_price_source_shadow'])),
        'feature_flag_candidate_value': first_text(merged, suff(['edgeiq_v7_2_feature_flag'])),
        'live_wired_value': first_text(merged, suff(['edgeiq_v7_2_live_wired_flag'])),
        'production_changed_value': first_text(merged, suff(['edgeiq_v7_2_production_changed'])),
    })
    base['_race_key']=base['race_date'].astype(str)+'|'+base['track'].astype(str)+'|'+base['race_no'].astype(str)
    base['production_rank_in_race']=base.groupby('_race_key')['production_display_price_used'].rank(method='first', ascending=True)
    base['v7_2_rank_in_race']=base.groupby('_race_key')['v7_2_display_price_used'].rank(method='first', ascending=True)
    base['rank_delta']=base['v7_2_rank_in_race']-base['production_rank_in_race']
    decision_mask=((base['rank_delta'].abs()>=2).fillna(False) | (base['pct_display_price_delta']>=30).fillna(False))
    base['decision_change_flag']=decision_mask.map(lambda x:'YES' if bool(x) else 'NO')
    base['price_movement_band']=base['pct_display_price_delta'].map(movement_band)
    out=base.drop(columns=['_race_key'])
    if len(out)!=len(live) or int(v72_display.notna().sum())==0:
        status='BLOCKED'

out.to_csv(OUT, index=False)
if out.empty:
    metrics={'built_at':built_at,'rows':0,'races':0,'comparison_rows':0,'status':status}
else:
    abs_delta=pd.to_numeric(out['absolute_display_price_delta'], errors='coerce')
    pct_delta=pd.to_numeric(out['pct_display_price_delta'], errors='coerce')
    metrics={
        'built_at':built_at,'rows':len(live),'races':int((out['race_date'].astype(str)+'|'+out['track'].astype(str)+'|'+out['race_no'].astype(str)).nunique()),'comparison_rows':len(out),
        'production_price_rows':int(pd.to_numeric(out['production_display_price_used'], errors='coerce').notna().sum()),'v7_2_price_rows':int(pd.to_numeric(out['v7_2_display_price_used'], errors='coerce').notna().sum()),'rows_with_price_delta':int(abs_delta.notna().sum()),
        'avg_abs_price_delta':round(float(abs_delta.mean()),4) if abs_delta.notna().any() else '', 'median_abs_price_delta':round(float(abs_delta.median()),4) if abs_delta.notna().any() else '', 'max_abs_price_delta':round(float(abs_delta.max()),4) if abs_delta.notna().any() else '',
        'avg_pct_price_delta':round(float(pct_delta.mean()),4) if pct_delta.notna().any() else '', 'decision_change_rows':int((out['decision_change_flag']=='YES').sum()), 'decision_change_pct':round(float((out['decision_change_flag']=='YES').mean()*100),4),
        'rank_change_rows':int((pd.to_numeric(out['rank_delta'], errors='coerce').fillna(0).abs()>0).sum()), 'large_or_extreme_rows':int(out['price_movement_band'].isin(['LARGE','EXTREME']).sum()),
        'feature_flag_values_in_candidate': ','.join(sorted(out['feature_flag_candidate_value'].astype(str).unique())), 'live_wired_values': ','.join(sorted(out['live_wired_value'].astype(str).unique())), 'production_changed_values': ','.join(sorted(out['production_changed_value'].astype(str).unique())), 'status':status}
pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_csv(SUM, index=False)
if not out.empty:
    biggest=out.sort_values('absolute_display_price_delta', ascending=False).head(10)
    biggest_lines='\n'.join([f"- {r.track} R{r.race_no} {r.horse}: prod {r.production_display_price_used}, V7.2 {r.v7_2_display_price_used}, delta {r.absolute_display_price_delta}" for r in biggest.itertuples(index=False)])
else:
    biggest_lines='- None.'
report=f'''EDGEiQ V7.2 ACTIVATION SIDE-BY-SIDE V1

- Status: {status}
- No activation occurred.
- Feature flag ON exists only in candidate file.
- Current live files remain feature flag OFF.
- Rows compared: {metrics.get('comparison_rows')}
- Races: {metrics.get('races')}
- V7.2 price rows: {metrics.get('v7_2_price_rows','')}
- Avg absolute price delta: {metrics.get('avg_abs_price_delta','')}
- Median absolute price delta: {metrics.get('median_abs_price_delta','')}
- Max absolute price delta: {metrics.get('max_abs_price_delta','')}
- Decision change rows: {metrics.get('decision_change_rows','')}
- Large/extreme rows: {metrics.get('large_or_extreme_rows','')}
- Candidate feature flag values: {metrics.get('feature_flag_values_in_candidate','')}
- Live wired values: {metrics.get('live_wired_values','')}
- Production changed values: {metrics.get('production_changed_values','')}

Biggest changes:
{biggest_lines}
'''
REP.write_text(report, encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_string(index=False))
print(report)
