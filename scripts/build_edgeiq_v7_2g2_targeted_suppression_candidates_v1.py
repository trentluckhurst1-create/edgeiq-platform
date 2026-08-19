from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'public'/'data'
G=DATA/'edgeiq_v7_2g_side_by_side_review_v1.csv'
RISK=DATA/'edgeiq_v7_2g_remaining_high_risk_races_v1.csv'
CAND=DATA/'edgeiq_v7_2g_guarded_activation_candidate_v1.csv'
OUT=DATA/'edgeiq_v7_2g2_targeted_suppression_candidates_v1.csv'
SUM=DATA/'edgeiq_v7_2g2_targeted_suppression_candidates_v1_summary.csv'
REP=DATA/'edgeiq_v7_2g2_targeted_suppression_candidates_v1_report.txt'

def band(pct):
    if pd.isna(pct): return 'UNKNOWN'
    a=abs(float(pct))
    if a<5: return 'SAME_OR_TINY'
    if a<15: return 'SMALL'
    if a<30: return 'MEDIUM'
    if a<=60: return 'LARGE'
    return 'EXTREME'
def clamp(prod,val,cap,maxp):
    if pd.isna(prod) or pd.isna(val): return prod
    lo=max(1.01,prod*(1-cap)); hi=min(maxp,prod*(1+cap))
    return min(max(float(val),lo),hi)
def race_key_cols(df): return df['race_date'].astype(str)+'|'+df['track'].astype(str)+'|'+df['race_no'].astype(str)

g=pd.read_csv(G,dtype=str,keep_default_na=False,low_memory=False) if G.exists() else pd.DataFrame()
risk=pd.read_csv(RISK,dtype=str,keep_default_na=False,low_memory=False) if RISK.exists() else pd.DataFrame()
if g.empty or risk.empty:
    out=pd.DataFrame(); metrics={'built_at':datetime.now(timezone.utc).isoformat(),'rows':0,'status':'G2_SUPPRESSION_CANDIDATES_BLOCKED_NO_INPUT'}
else:
    for c in ['production_display','raw_v7_2_display','guarded_v7_2g_display','production_rank','raw_v7_2_rank','v7_2g_rank']:
        g[c]=pd.to_numeric(g[c], errors='coerce')
    g['race_key_g2']=race_key_cols(g)
    high=set((risk[risk['current_risk_band'].eq('HIGH')]['race_date']+'|'+risk[risk['current_risk_band'].eq('HIGH')]['track']+'|'+risk[risk['current_risk_band'].eq('HIGH')]['race_no']).tolist())
    rows=[]
    for strategy in ['HIGH_RISK_BLEND_15','HIGH_RISK_BLEND_10','HIGH_RISK_PRODUCTION_FALLBACK','TOP_PICK_PROTECTED_G2']:
        df=g.copy(); vals=[]; reasons=[]
        for r in df.itertuples(index=False):
            prod=r.production_display; base=r.guarded_v7_2g_display; is_high=r.race_key_g2 in high
            if not is_high:
                val=base; reason='NON_HIGH_RISK_KEEP_V7_2G'
            elif strategy=='HIGH_RISK_BLEND_15':
                val=clamp(prod, prod*0.85+base*0.15, 0.15, 25); reason='HIGH_RISK_BLEND_15_CAP_15_MAX_25'
            elif strategy=='HIGH_RISK_BLEND_10':
                val=clamp(prod, prod*0.90+base*0.10, 0.10, 22); reason='HIGH_RISK_BLEND_10_CAP_10_MAX_22'
            elif strategy=='HIGH_RISK_PRODUCTION_FALLBACK':
                val=prod; reason='HIGH_RISK_PRODUCTION_FALLBACK'
            else:
                val=clamp(prod, prod*0.90+base*0.10, 0.10, 22); reason='TOP_PICK_PROTECTED_G2_BLEND_10_CAP_10_MAX_22'
            vals.append(max(1.01,min(49.95,val if not pd.isna(val) else prod)))
            reasons.append(reason)
        df['strategy']=strategy
        df['high_risk_race_flag']=df['race_key_g2'].map(lambda x:'YES' if x in high else 'NO')
        df['v7_2g2_display_price']=vals
        df['v7_2g2_guardrail_reason']=reasons
        if strategy=='TOP_PICK_PROTECTED_G2':
            for rk,rg in df[df['high_risk_race_flag'].eq('YES')].groupby('race_key_g2'):
                prod_top_idx=rg.sort_values('production_display', ascending=True, kind='mergesort').index[0]
                prod_top_price=df.loc[prod_top_idx,'production_display']
                df.loc[prod_top_idx,'v7_2g2_display_price']=min(df.loc[prod_top_idx,'v7_2g2_display_price'], prod_top_price)
                eps=0.01
                for idx in rg.index:
                    if idx!=prod_top_idx and df.loc[idx,'v7_2g2_display_price'] < prod_top_price+eps:
                        df.loc[idx,'v7_2g2_display_price']=prod_top_price+eps
                        df.loc[idx,'v7_2g2_guardrail_reason']+='|TOP_PICK_FLOOR_APPLIED'
        df['v7_2g2_delta_abs']=(df['v7_2g2_display_price']-df['production_display']).abs()
        df['v7_2g2_delta_pct']=(df['v7_2g2_delta_abs']/df['production_display'].replace(0,np.nan))*100
        df['v7_2g2_rank']=df.groupby('race_key_g2')['v7_2g2_display_price'].rank(method='first', ascending=True)
        df['v7_2g2_movement_band']=df['v7_2g2_delta_pct'].map(band)
        df['v7_2g2_decision_change_flag']=(((df['v7_2g2_rank']-df['production_rank']).abs()>=2).fillna(False)|(df['v7_2g2_delta_pct']>=30).fillna(False)).map(lambda x:'YES' if bool(x) else 'NO')
        keep=['strategy','race_date','track','race_no','horse','production_display','raw_v7_2_display','guarded_v7_2g_display','v7_2g2_display_price','production_rank','raw_v7_2_rank','v7_2g_rank','v7_2g2_rank','high_risk_race_flag','v7_2g2_delta_abs','v7_2g2_delta_pct','v7_2g2_movement_band','v7_2g2_decision_change_flag','v7_2g2_guardrail_reason']
        rows.append(df[keep])
    out=pd.concat(rows,ignore_index=True)
    metrics={'built_at':datetime.now(timezone.utc).isoformat(),'strategies':4,'rows':len(out),'runners_per_strategy':len(g),'high_risk_races_targeted':len(high),'status':'G2_SUPPRESSION_CANDIDATES_BUILT_REVIEW_REQUIRED'}
out.to_csv(OUT,index=False)
pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_csv(SUM,index=False)
report=f'''EDGEiQ V7.2G2 TARGETED SUPPRESSION CANDIDATES V1

- Status: {metrics.get('status')}
- Strategies: {metrics.get('strategies')}
- Rows: {metrics.get('rows')}
- Runners per strategy: {metrics.get('runners_per_strategy')}
- High-risk races targeted: {metrics.get('high_risk_races_targeted')}
- No activation occurred.
'''
REP.write_text(report,encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_string(index=False)); print(report)



