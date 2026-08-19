from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'public'/'data'
G2=DATA/'edgeiq_v7_2g2_activation_candidate_v1.csv'
G=DATA/'edgeiq_v7_2g_side_by_side_review_v1.csv'
OUT=DATA/'edgeiq_v7_2g2_side_by_side_review_v1.csv'
SUM=DATA/'edgeiq_v7_2g2_side_by_side_review_v1_summary.csv'
REP=DATA/'edgeiq_v7_2g2_side_by_side_review_v1_report.txt'

def band(pct):
    if pd.isna(pct): return 'UNKNOWN'
    a=abs(float(pct))
    if a<5: return 'SAME_OR_TINY'
    if a<15: return 'SMALL'
    if a<30: return 'MEDIUM'
    if a<=60: return 'LARGE'
    return 'EXTREME'

g=pd.read_csv(G,dtype=str,keep_default_na=False,low_memory=False) if G.exists() else pd.DataFrame()
g2=pd.read_csv(G2,dtype=str,keep_default_na=False,low_memory=False) if G2.exists() else pd.DataFrame()
if g.empty or g2.empty:
    out=pd.DataFrame(); metrics={'built_at':datetime.now(timezone.utc).isoformat(),'rows':0,'status':'G2_SIDE_BY_SIDE_BLOCKED_NO_INPUT'}
else:
    key_cols=['race_date','track','race_no','horse']
    merged=g.merge(g2[key_cols+['v7_2g2_display_price','v7_2g2_rank','v7_2g2_decision_change_flag','v7_2g2_movement_band','v7_2g2_guardrail_reason','high_risk_race_flag']], on=key_cols, how='left')
    for c in ['production_display','raw_v7_2_display','guarded_v7_2g_display','guarded_v7_2g_display','v7_2g2_display_price','production_rank','raw_v7_2_rank','v7_2g_rank','v7_2g2_rank']:
        if c in merged.columns: merged[c]=pd.to_numeric(merged[c], errors='coerce')
    out=merged.rename(columns={'guarded_v7_2g_display':'v7_2g_display','v7_2g2_display_price':'v7_2g2_display'})
    out['v7_2g2_delta_abs']=(out['v7_2g2_display']-out['production_display']).abs()
    out['v7_2g2_delta_pct']=(out['v7_2g2_delta_abs']/out['production_display'].replace(0,pd.NA))*100
    out['race_key']=out['race_date'].astype(str)+'|'+out['track'].astype(str)+'|'+out['race_no'].astype(str)
    # counts
    raw_dec=int(out['raw_decision_change_flag'].eq('YES').sum())
    g_dec=int(out['guarded_decision_change_flag'].eq('YES').sum())
    g2_dec=int(out['v7_2g2_decision_change_flag'].eq('YES').sum())
    raw_large=int(out['raw_movement_band'].isin(['LARGE','EXTREME']).sum())
    g_large=int(out['guarded_movement_band'].isin(['LARGE','EXTREME']).sum())
    g2_large=int(out['v7_2g2_movement_band'].isin(['LARGE','EXTREME']).sum())
    raw_top=g_top=g2_top=0; g_high=g2_high=0
    for rk,rg in out.groupby('race_key'):
        prod=rg.sort_values('production_display', ascending=True, kind='mergesort').iloc[0]['horse']
        raw=rg.sort_values('raw_v7_2_display', ascending=True, kind='mergesort').iloc[0]['horse']
        gv=rg.sort_values('v7_2g_display', ascending=True, kind='mergesort').iloc[0]['horse']
        g2v=rg.sort_values('v7_2g2_display', ascending=True, kind='mergesort').iloc[0]['horse']
        if prod!=raw: raw_top+=1
        if prod!=gv: g_top+=1
        if prod!=g2v: g2_top+=1
        gl=int(rg['guarded_movement_band'].isin(['LARGE','EXTREME']).sum()); g2l=int(rg['v7_2g2_movement_band'].isin(['LARGE','EXTREME']).sum())
        gd=int(rg['guarded_decision_change_flag'].eq('YES').sum()); g2d=int(rg['v7_2g2_decision_change_flag'].eq('YES').sum())
        if prod!=gv or gl>3 or gd/len(rg)>0.35: g_high+=1
        if prod!=g2v or g2l>3 or g2d/len(rg)>0.35: g2_high+=1
    keep=['race_date','track','race_no','horse','production_display','raw_v7_2_display','v7_2g_display','v7_2g2_display','production_rank','raw_v7_2_rank','v7_2g_rank','v7_2g2_rank','raw_decision_change_flag','guarded_decision_change_flag','v7_2g2_decision_change_flag','raw_movement_band','guarded_movement_band','v7_2g2_movement_band','v7_2g2_delta_abs','v7_2g2_delta_pct','v7_2g2_guardrail_reason','high_risk_race_flag']
    out[keep].to_csv(OUT,index=False)
    metrics={'built_at':datetime.now(timezone.utc).isoformat(),'rows':len(out),'races':out['race_key'].nunique(),'raw_decision_changes':raw_dec,'v7_2g_decision_changes':g_dec,'v7_2g2_decision_changes':g2_dec,'raw_large_extreme':raw_large,'v7_2g_large_extreme':g_large,'v7_2g2_large_extreme':g2_large,'raw_top_pick_changes':raw_top,'v7_2g_top_pick_changes':g_top,'v7_2g2_top_pick_changes':g2_top,'v7_2g_high_risk_races':g_high,'v7_2g2_high_risk_races':g2_high,'status':'G2_SIDE_BY_SIDE_BUILT_REVIEW_REQUIRED'}
pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_csv(SUM,index=False)
if 'out' in locals() and not out.empty:
    top=out.sort_values('v7_2g2_delta_abs', ascending=False).head(20)
    lines='\n'.join([f"- {r.track} R{r.race_no} {r.horse}: prod {r.production_display}, raw {r.raw_v7_2_display}, G {r.v7_2g_display}, G2 {r.v7_2g2_display}, {r.v7_2g2_guardrail_reason}" for r in top.itertuples(index=False)])
else: lines='- None.'
report=f'''EDGEiQ V7.2G2 SIDE-BY-SIDE REVIEW V1

- Status: {metrics.get('status')}
- Rows: {metrics.get('rows')}
- Races: {metrics.get('races')}
- Decision changes raw -> G -> G2: {metrics.get('raw_decision_changes')} -> {metrics.get('v7_2g_decision_changes')} -> {metrics.get('v7_2g2_decision_changes')}
- Large/extreme raw -> G -> G2: {metrics.get('raw_large_extreme')} -> {metrics.get('v7_2g_large_extreme')} -> {metrics.get('v7_2g2_large_extreme')}
- Top-pick changes raw -> G -> G2: {metrics.get('raw_top_pick_changes')} -> {metrics.get('v7_2g_top_pick_changes')} -> {metrics.get('v7_2g2_top_pick_changes')}
- High-risk races G -> G2: {metrics.get('v7_2g_high_risk_races')} -> {metrics.get('v7_2g2_high_risk_races')}

Top remaining G2 changes:
{lines}
'''
REP.write_text(report,encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_string(index=False)); print(report)
