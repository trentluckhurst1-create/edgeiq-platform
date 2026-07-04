from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'public'/'data'
INP=DATA/'edgeiq_v7_2_guarded_display_candidates_v1.csv'
OUT=DATA/'edgeiq_v7_2_guarded_display_candidates_audit_v1.csv'
SUM=DATA/'edgeiq_v7_2_guarded_display_candidates_audit_v1_summary.csv'
REP=DATA/'edgeiq_v7_2_guarded_display_candidates_audit_v1_report.txt'

def audit_strategy(g):
    for c in ['production_display_price_used','guarded_display_fair_price','guarded_price_delta','guarded_pct_delta','production_rank','guarded_rank']:
        g[c]=pd.to_numeric(g[c], errors='coerce')
    g['_race_key']=g['race_date'].astype(str)+'|'+g['track'].astype(str)+'|'+g['race_no'].astype(str)
    top_changed=0; high=0; rank_breaks=0; top_longer=0
    for rk, rg in g.groupby('_race_key'):
        prod_top=rg.sort_values('production_display_price_used', ascending=True, kind='mergesort').iloc[0]['horse']
        guarded_top=rg.sort_values('guarded_display_fair_price', ascending=True, kind='mergesort').iloc[0]['horse']
        large=int(rg['guarded_movement_band'].isin(['LARGE','EXTREME']).sum())
        if prod_top!=guarded_top: top_changed+=1
        if prod_top!=guarded_top or large>3: high+=1
        vals=rg.sort_values('guarded_rank')['guarded_display_fair_price'].tolist()
        if any(vals[i]>vals[i+1]+1e-9 for i in range(len(vals)-1)): rank_breaks+=1
        if len(vals)>=2 and vals[0]>vals[1]+1e-9: top_longer+=1
    rows=len(g); races=g['_race_key'].nunique()
    large_rows=int(g['guarded_movement_band'].isin(['LARGE','EXTREME']).sum())
    decision=int(g['guarded_decision_change_flag'].eq('YES').sum())
    at_cap=int((g['guarded_display_fair_price']>=99.999).sum())
    eligible=(top_changed/races*100<=20 and high/races*100<=20 and decision/rows*100<=35 and large_rows/rows*100<=25 and rank_breaks==0 and top_longer==0 and at_cap==0)
    return {'strategy':g['strategy'].iloc[0],'rows':rows,'races':races,'avg_abs_delta':round(float(g['guarded_price_delta'].mean()),4),'median_abs_delta':round(float(g['guarded_price_delta'].median()),4),'max_abs_delta':round(float(g['guarded_price_delta'].max()),4),'avg_pct_delta':round(float(g['guarded_pct_delta'].mean()),4),'decision_change_rows':decision,'decision_change_pct':round(decision/rows*100,4),'large_extreme_movement_rows':large_rows,'large_extreme_pct':round(large_rows/rows*100,4),'top_pick_changed_races':top_changed,'top_pick_changed_pct':round(top_changed/races*100,4),'high_risk_races':high,'high_risk_pct':round(high/races*100,4),'rows_above_20':int((g['guarded_display_fair_price']>20).sum()),'rows_above_35':int((g['guarded_display_fair_price']>35).sum()),'rows_at_cap':at_cap,'rank_order_breaks':rank_breaks,'top_pick_longer_than_second':top_longer,'production_changed_values':','.join(sorted(g['production_changed_value'].astype(str).unique())),'live_wired_values':','.join(sorted(g['live_wired_value'].astype(str).unique())),'eligible':'YES' if eligible else 'NO'}

df=pd.read_csv(INP,dtype=str,keep_default_na=False,low_memory=False) if INP.exists() else pd.DataFrame()
if df.empty:
    audit=pd.DataFrame(); metrics={'built_at':datetime.now(timezone.utc).isoformat(),'status':'GUARDED_AUDIT_BLOCKED_NO_INPUT'}
else:
    rows=[audit_strategy(g.copy()) for _,g in df.groupby('strategy')]
    audit=pd.DataFrame(rows).sort_values(['eligible','high_risk_pct','decision_change_pct','large_extreme_pct'], ascending=[False,True,True,True])
    eligible=audit[audit['eligible'].eq('YES')]
    best_low=audit.sort_values(['high_risk_pct','top_pick_changed_pct','decision_change_pct']).iloc[0]['strategy']
    best_dec=audit.sort_values(['decision_change_pct','high_risk_pct']).iloc[0]['strategy']
    recommended=eligible.sort_values(['high_risk_pct','decision_change_pct']).iloc[0]['strategy'] if not eligible.empty else best_low
    status='GUARDED_DISPLAY_AUDIT_ELIGIBLE_STRATEGY_FOUND' if not eligible.empty else 'GUARDED_DISPLAY_AUDIT_NO_ELIGIBLE_STRATEGY'
    metrics={'built_at':datetime.now(timezone.utc).isoformat(),'strategies_audited':len(audit),'best_strategy_by_lowest_risk':best_low,'best_strategy_by_lowest_decision_change':best_dec,'eligible_strategies':','.join(eligible['strategy'].tolist()) if not eligible.empty else 'NONE','recommended_strategy':recommended,'status':status}
audit.to_csv(OUT,index=False)
pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_csv(SUM,index=False)
lines='\n'.join([f"- {r.strategy}: eligible {r.eligible}, high-risk {r.high_risk_races}/{r.races} ({r.high_risk_pct}%), top changes {r.top_pick_changed_races}, decision {r.decision_change_pct}%, large/extreme {r.large_extreme_pct}%, cap {r.rows_at_cap}" for r in audit.itertuples(index=False)]) if not audit.empty else '- None.'
report=f'''EDGEiQ V7.2 GUARDED DISPLAY CANDIDATES AUDIT V1

- Status: {metrics.get('status')}
- Recommended strategy: {metrics.get('recommended_strategy','')}
- Eligible strategies: {metrics.get('eligible_strategies','')}
- Best by lowest risk: {metrics.get('best_strategy_by_lowest_risk','')}
- Best by lowest decision change: {metrics.get('best_strategy_by_lowest_decision_change','')}

Strategy audit:
{lines}
'''
REP.write_text(report,encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_string(index=False))
print(report)
