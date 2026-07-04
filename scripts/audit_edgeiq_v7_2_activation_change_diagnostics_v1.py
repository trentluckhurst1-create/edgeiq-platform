from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'public'/'data'
SIDE=DATA/'edgeiq_v7_2_activation_side_by_side_v1.csv'
RACE=DATA/'edgeiq_v7_2_activation_race_level_changes_v1.csv'
HYB=DATA/'edgeiq_current_day_v7_2_hybrid_candidate_v1.csv'
OUT=DATA/'edgeiq_v7_2_activation_change_diagnostics_v1.csv'
SUM=DATA/'edgeiq_v7_2_activation_change_diagnostics_v1_summary.csv'
REP=DATA/'edgeiq_v7_2_activation_change_diagnostics_v1_report.txt'

def bucket_field_size(n):
    try: n=int(n)
    except: return 'UNKNOWN'
    if n<=8: return 'FIELD_1_8'
    if n<=12: return 'FIELD_9_12'
    if n<=16: return 'FIELD_13_16'
    return 'FIELD_17_PLUS'
def rank_bucket(v):
    try: v=float(v)
    except: return 'UNKNOWN'
    if v<=1: return 'RANK_1'
    if v<=3: return 'RANK_2_3'
    if v<=6: return 'RANK_4_6'
    if v<=10: return 'RANK_7_10'
    return 'RANK_11_PLUS'
def source_band(src):
    s=str(src).upper()
    if 'TOTAL_RATING_POINTS' in s or 'PROJECTED_RATING_V5_2' in s: return 'STRONG_SOURCE'
    if 'WIN_PCT' in s: return 'MEDIUM_SOURCE'
    if 'EQUAL' in s or 'FALLBACK' in s: return 'WEAK_SOURCE'
    return 'WEAK_SOURCE'

df=pd.read_csv(SIDE,dtype=str,keep_default_na=False,low_memory=False) if SIDE.exists() else pd.DataFrame()
races=pd.read_csv(RACE,dtype=str,keep_default_na=False,low_memory=False) if RACE.exists() else pd.DataFrame()
if df.empty:
    out=pd.DataFrame(); metrics={'built_at':datetime.now(timezone.utc).isoformat(),'rows':0,'status':'CHANGE_DIAGNOSTICS_BLOCKED_NO_INPUT'}
else:
    for c in ['production_display_price_used','v7_2_display_price_used','absolute_display_price_delta','pct_display_price_delta','production_rank_in_race','v7_2_rank_in_race','rank_delta']:
        df[c]=pd.to_numeric(df[c], errors='coerce')
    df['race_key']=df['race_date'].astype(str)+'|'+df['track'].astype(str)+'|'+df['race_no'].astype(str)
    field_sizes=df.groupby('race_key')['horse'].transform('count')
    df['race_field_size_bucket']=field_sizes.map(bucket_field_size)
    df['production_rank_bucket']=df['production_rank_in_race'].map(rank_bucket)
    df['v7_2_rank_bucket']=df['v7_2_rank_in_race'].map(rank_bucket)
    df['source_quality_band']=df['v7_2_probability_source'].map(source_band)
    top_changed=set()
    if not races.empty:
        top_changed=set((races[races['top_pick_changed'].eq('YES')]['race_date']+'|'+races[races['top_pick_changed'].eq('YES')]['track']+'|'+races[races['top_pick_changed'].eq('YES')]['race_no']).tolist())
    df['top_pick_changed_race']=df['race_key'].map(lambda x:'YES' if x in top_changed else 'NO')
    groups=[]
    group_cols=['v7_2_probability_source','race_field_size_bucket','production_rank_bucket','v7_2_rank_bucket','price_movement_band','source_quality_band','top_pick_changed_race']
    for keys,g in df.groupby(group_cols, dropna=False):
        row=dict(zip(group_cols,keys))
        row.update({'rows':len(g),'races':g['race_key'].nunique(),'avg_production_display_price':round(float(g['production_display_price_used'].mean()),4),'avg_v7_2_display_price':round(float(g['v7_2_display_price_used'].mean()),4),'avg_abs_delta':round(float(g['absolute_display_price_delta'].mean()),4),'avg_pct_delta':round(float(g['pct_display_price_delta'].mean()),4),'large_extreme_rows':int(g['price_movement_band'].isin(['LARGE','EXTREME']).sum()),'decision_change_rows':int(g['decision_change_flag'].eq('YES').sum()),'rank_change_rows':int(g['rank_delta'].fillna(0).abs().gt(0).sum()),'top_pick_changed_races':g[g['top_pick_changed_race'].eq('YES')]['race_key'].nunique(),'max_v7_2_display_price':round(float(g['v7_2_display_price_used'].max()),4),'rows_hitting_cap_100':int(g['v7_2_display_price_used'].ge(100).sum())})
        groups.append(row)
    out=pd.DataFrame(groups).sort_values(['large_extreme_rows','decision_change_rows','rows_hitting_cap_100'], ascending=False)
    source_summary=df.groupby('v7_2_probability_source').agg(rows=('horse','count'),large_extreme_rows=('price_movement_band',lambda s:s.isin(['LARGE','EXTREME']).sum()),decision_change_rows=('decision_change_flag',lambda s:s.eq('YES').sum()),rows_hitting_cap_100=('v7_2_display_price_used',lambda s:s.ge(100).sum()),avg_abs_delta=('absolute_display_price_delta','mean')).reset_index().sort_values(['large_extreme_rows','decision_change_rows'], ascending=False)
    top_sources='; '.join([f"{r.v7_2_probability_source}: rows={r.rows}, large_extreme={r.large_extreme_rows}, cap100={r.rows_hitting_cap_100}" for r in source_summary.head(5).itertuples(index=False)])
    movement=df['price_movement_band'].value_counts().to_dict()
    metrics={'built_at':datetime.now(timezone.utc).isoformat(),'rows':len(df),'races':df['race_key'].nunique(),'top_sources_causing_changes':top_sources,'top_source_causing_extreme_changes':source_summary.iloc[0]['v7_2_probability_source'] if len(source_summary) else 'NONE','top_movement_bands':str(movement),'status':'CHANGE_DIAGNOSTICS_BUILT_REVIEW_REQUIRED'}
out.to_csv(OUT,index=False)
pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_csv(SUM,index=False)
report=f'''EDGEiQ V7.2 ACTIVATION CHANGE DIAGNOSTICS V1

- Status: {metrics.get('status')}
- No activation occurred.
- Rows: {metrics.get('rows')}
- Races: {metrics.get('races')}
- Top sources causing changes: {metrics.get('top_sources_causing_changes','')}
- Top source causing extreme changes: {metrics.get('top_source_causing_extreme_changes','')}
- Movement bands: {metrics.get('top_movement_bands','')}

Disruption is concentrated in broad display movement from raw V7.2 display prices, especially where display prices hit the 100 cap or shift long-priced runners sharply away from production display levels. Guardrails should cap movement from production display, gate weaker source rows, and protect race top ranks.
'''
REP.write_text(report,encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_string(index=False))
print(report)
