from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'public'/'data'
INP=DATA/'edgeiq_v7_2g_guarded_activation_candidate_v1.csv'
OUT=DATA/'edgeiq_v7_2g_side_by_side_review_v1.csv'
SUM=DATA/'edgeiq_v7_2g_side_by_side_review_v1_summary.csv'
REP=DATA/'edgeiq_v7_2g_side_by_side_review_v1_report.txt'

def band(pct):
    if pd.isna(pct): return 'UNKNOWN'
    a=abs(float(pct))
    if a<5: return 'SAME_OR_TINY'
    if a<15: return 'SMALL'
    if a<30: return 'MEDIUM'
    if a<=60: return 'LARGE'
    return 'EXTREME'

df=pd.read_csv(INP,dtype=str,keep_default_na=False,low_memory=False) if INP.exists() else pd.DataFrame()
if df.empty:
    out=pd.DataFrame(); metrics={'built_at':datetime.now(timezone.utc).isoformat(),'rows':0,'status':'V7_2G_SIDE_BY_SIDE_BLOCKED_NO_INPUT'}
else:
    for c in ['production_display_price_used','v7_2_display_price_used','guarded_display_fair_price','production_rank','v7_2_rank','guarded_rank','guarded_price_delta','guarded_pct_delta']:
        df[c]=pd.to_numeric(df[c], errors='coerce')
    df['_race_key']=df['race_date'].astype(str)+'|'+df['track'].astype(str)+'|'+df['race_no'].astype(str)
    df['raw_decision_change_flag']=(((df['v7_2_rank']-df['production_rank']).abs()>=2).fillna(False) | (((df['v7_2_display_price_used']-df['production_display_price_used']).abs()/df['production_display_price_used'].replace(0,pd.NA)*100)>=30).fillna(False)).map(lambda x:'YES' if bool(x) else 'NO')
    df['raw_movement_band']=(((df['v7_2_display_price_used']-df['production_display_price_used']).abs()/df['production_display_price_used'].replace(0,pd.NA))*100).map(band)
    df['guarded_decision_change_flag']=df['guarded_decision_change_flag']
    df['guarded_movement_band']=df['guarded_movement_band']
    out=df.rename(columns={'production_display_price_used':'production_display','v7_2_display_price_used':'raw_v7_2_display','guarded_display_fair_price':'guarded_v7_2g_display','production_rank':'production_rank','v7_2_rank':'raw_v7_2_rank','guarded_rank':'v7_2g_rank'})[['race_date','track','race_no','horse','production_display','raw_v7_2_display','guarded_v7_2g_display','production_rank','raw_v7_2_rank','v7_2g_rank','raw_decision_change_flag','guarded_decision_change_flag','raw_movement_band','guarded_movement_band','guardrail_reason']]
    # race level guarded risk
    top_changed=0; high=0
    for rk,g in df.groupby('_race_key'):
        prod_top=g.sort_values('production_display_price_used', ascending=True, kind='mergesort').iloc[0]['horse']
        guarded_top=g.sort_values('guarded_display_fair_price', ascending=True, kind='mergesort').iloc[0]['horse']
        large=int(g['guarded_movement_band'].isin(['LARGE','EXTREME']).sum())
        if prod_top!=guarded_top: top_changed+=1
        if prod_top!=guarded_top or large>3: high+=1
    raw_dec=int(out['raw_decision_change_flag'].eq('YES').sum()); guard_dec=int(out['guarded_decision_change_flag'].eq('YES').sum())
    raw_large=int(out['raw_movement_band'].isin(['LARGE','EXTREME']).sum()); guard_large=int(out['guarded_movement_band'].isin(['LARGE','EXTREME']).sum())
    metrics={'built_at':datetime.now(timezone.utc).isoformat(),'rows':len(out),'races':df['_race_key'].nunique(),'raw_decision_change_rows':raw_dec,'guarded_decision_change_rows':guard_dec,'decision_change_reduction_rows':raw_dec-guard_dec,'raw_large_extreme_rows':raw_large,'guarded_large_extreme_rows':guard_large,'large_extreme_reduction_rows':raw_large-guard_large,'guarded_top_pick_changed_races':top_changed,'guarded_high_risk_races':high,'biggest_remaining_delta':round(float(df['guarded_price_delta'].max()),4),'status':'V7_2G_SIDE_BY_SIDE_BUILT_REVIEW_REQUIRED'}
out.to_csv(OUT,index=False)
pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_csv(SUM,index=False)
big=df.sort_values('guarded_price_delta', ascending=False).head(20) if not df.empty else pd.DataFrame()
lines='\n'.join([f"- {r.track} R{r.race_no} {r.horse}: prod {r.production_display_price_used}, raw {r.v7_2_display_price_used}, guarded {r.guarded_display_fair_price}, reason {r.guardrail_reason}" for r in big.itertuples(index=False)]) or '- None.'
report=f'''EDGEiQ V7.2G SIDE-BY-SIDE REVIEW V1

- Status: {metrics.get('status')}
- Rows: {metrics.get('rows')}
- Races: {metrics.get('races')}
- Raw decision changes: {metrics.get('raw_decision_change_rows')}
- Guarded decision changes: {metrics.get('guarded_decision_change_rows')}
- Decision change reduction: {metrics.get('decision_change_reduction_rows')}
- Raw large/extreme rows: {metrics.get('raw_large_extreme_rows')}
- Guarded large/extreme rows: {metrics.get('guarded_large_extreme_rows')}
- Large/extreme reduction: {metrics.get('large_extreme_reduction_rows')}
- Remaining guarded top-pick changed races: {metrics.get('guarded_top_pick_changed_races')}
- Remaining guarded high-risk races: {metrics.get('guarded_high_risk_races')}

Biggest remaining guarded changes:
{lines}
'''
REP.write_text(report,encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_string(index=False))
print(report)
