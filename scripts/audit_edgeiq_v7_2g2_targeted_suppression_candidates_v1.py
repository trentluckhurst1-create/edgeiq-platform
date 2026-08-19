from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'public'/'data'
INP=DATA/'edgeiq_v7_2g2_targeted_suppression_candidates_v1.csv'
OUT=DATA/'edgeiq_v7_2g2_targeted_suppression_candidates_audit_v1.csv'
SUM=DATA/'edgeiq_v7_2g2_targeted_suppression_candidates_audit_v1_summary.csv'
REP=DATA/'edgeiq_v7_2g2_targeted_suppression_candidates_audit_v1_report.txt'

def audit(g):
    for c in ['production_display','v7_2g2_display_price','production_rank','v7_2g2_rank','v7_2g2_delta_abs','v7_2g2_delta_pct']:
        g[c]=pd.to_numeric(g[c], errors='coerce')
    g['race_key']=g['race_date'].astype(str)+'|'+g['track'].astype(str)+'|'+g['race_no'].astype(str)
    top=0; high=0; rb=0; tls=0
    for rk,rg in g.groupby('race_key'):
        prod_top=rg.sort_values('production_display', ascending=True, kind='mergesort').iloc[0]['horse']
        g2_top=rg.sort_values('v7_2g2_display_price', ascending=True, kind='mergesort').iloc[0]['horse']
        large=int(rg['v7_2g2_movement_band'].isin(['LARGE','EXTREME']).sum())
        dec=int(rg['v7_2g2_decision_change_flag'].eq('YES').sum())
        if prod_top!=g2_top: top+=1
        if prod_top!=g2_top or large>3 or dec/len(rg)>0.35: high+=1
        vals=rg.sort_values('v7_2g2_rank')['v7_2g2_display_price'].tolist()
        if any(vals[i]>vals[i+1]+1e-9 for i in range(len(vals)-1)): rb+=1
        if len(vals)>=2 and vals[0]>vals[1]+1e-9: tls+=1
    rows=len(g); races=g['race_key'].nunique(); dec_rows=int(g['v7_2g2_decision_change_flag'].eq('YES').sum()); large_rows=int(g['v7_2g2_movement_band'].isin(['LARGE','EXTREME']).sum()); atcap=int(g['v7_2g2_display_price'].ge(49.999).sum())
    eligible=high<=5 and top<=5 and dec_rows/rows*100<=35 and large_rows/rows*100<=25 and rb==0 and tls==0 and atcap==0
    return {'strategy':g['strategy'].iloc[0],'rows':rows,'races':races,'decision_change_rows':dec_rows,'decision_change_pct':round(dec_rows/rows*100,4),'large_extreme_rows':large_rows,'large_extreme_pct':round(large_rows/rows*100,4),'top_pick_changed_races':top,'top_pick_changed_pct':round(top/races*100,4),'high_risk_races':high,'high_risk_pct':round(high/races*100,4),'avg_abs_delta':round(float(g['v7_2g2_delta_abs'].mean()),4),'max_abs_delta':round(float(g['v7_2g2_delta_abs'].max()),4),'rows_above_20':int(g['v7_2g2_display_price'].gt(20).sum()),'rows_above_35':int(g['v7_2g2_display_price'].gt(35).sum()),'rows_at_cap':atcap,'rank_order_breaks':rb,'top_pick_longer_than_second':tls,'eligible':'YES' if eligible else 'NO'}

df=pd.read_csv(INP,dtype=str,keep_default_na=False,low_memory=False) if INP.exists() else pd.DataFrame()
if df.empty:
    out=pd.DataFrame(); metrics={'built_at':datetime.now(timezone.utc).isoformat(),'status':'G2_AUDIT_BLOCKED_NO_INPUT'}
else:
    out=pd.DataFrame([audit(g.copy()) for _,g in df.groupby('strategy')]).sort_values(['eligible','high_risk_races','top_pick_changed_races','decision_change_pct'], ascending=[False,True,True,True])
    eligible=out[out['eligible'].eq('YES')]
    if not eligible.empty:
        non_fallback=eligible[~eligible['strategy'].eq('HIGH_RISK_PRODUCTION_FALLBACK')]
        pool=non_fallback if not non_fallback.empty else eligible
        rec=pool.sort_values(['high_risk_races','top_pick_changed_races','decision_change_pct']).iloc[0]['strategy']
        rec_status='ELIGIBLE_BUT_TOO_CONSERVATIVE_REVIEW_REQUIRED' if rec=='HIGH_RISK_PRODUCTION_FALLBACK' else 'ELIGIBLE_RECOMMENDED_REVIEW_REQUIRED'
        status='G2_AUDIT_ELIGIBLE_STRATEGY_FOUND'
    else:
        rec=out.sort_values(['high_risk_races','top_pick_changed_races','decision_change_pct']).iloc[0]['strategy']; rec_status='NO_ELIGIBLE_STRATEGY'; status='G2_AUDIT_NO_ELIGIBLE_STRATEGY'
    metrics={'built_at':datetime.now(timezone.utc).isoformat(),'eligible_strategies':','.join(eligible['strategy'].tolist()) if not eligible.empty else 'NONE','recommended_strategy':rec,'recommended_status':rec_status,'status':status}
out.to_csv(OUT,index=False)
pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_csv(SUM,index=False)
lines='\n'.join([f"- {r.strategy}: eligible {r.eligible}, high {r.high_risk_races}, top {r.top_pick_changed_races}, decision {r.decision_change_pct}%, large {r.large_extreme_pct}%, cap {r.rows_at_cap}" for r in out.itertuples(index=False)]) if not out.empty else '- None.'
report=f'''EDGEiQ V7.2G2 TARGETED SUPPRESSION CANDIDATES AUDIT V1

- Status: {metrics.get('status')}
- Eligible strategies: {metrics.get('eligible_strategies')}
- Recommended strategy: {metrics.get('recommended_strategy')}
- Recommended status: {metrics.get('recommended_status')}

Strategy audit:
{lines}
'''
REP.write_text(report,encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_string(index=False)); print(report)
