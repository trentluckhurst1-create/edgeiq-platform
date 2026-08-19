from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'public'/'data'
SIDE=DATA/'edgeiq_v7_2_activation_side_by_side_v1.csv'
CAND=DATA/'edgeiq_live_runner_board_v7_2_feature_flag_on_candidate.csv'
OUT=DATA/'edgeiq_v7_2_guarded_display_candidates_v1.csv'
SUM=DATA/'edgeiq_v7_2_guarded_display_candidates_v1_summary.csv'
REP=DATA/'edgeiq_v7_2_guarded_display_candidates_v1_report.txt'

def band(pct):
    if pd.isna(pct): return 'UNKNOWN'
    a=abs(float(pct))
    if a<5: return 'SAME_OR_TINY'
    if a<15: return 'SMALL'
    if a<30: return 'MEDIUM'
    if a<=60: return 'LARGE'
    return 'EXTREME'
def source_quality(src):
    s=str(src).upper()
    if 'TOTAL_RATING_POINTS' in s or 'PROJECTED_RATING_V5_2' in s: return 'STRONG'
    if 'WIN_PCT' in s: return 'MEDIUM'
    return 'WEAK'
def clamp_move(prod, val, pct_cap, max_price):
    if pd.isna(prod) or prod<=0 or pd.isna(val): return np.nan
    lo=max(1.01, prod*(1-pct_cap)); hi=min(max_price, prod*(1+pct_cap))
    return min(max(float(val), lo), hi)
def apply_blend(prod, raw, weight, cap, maxp):
    if pd.isna(prod): return np.nan
    if pd.isna(raw): raw=prod
    return clamp_move(prod, prod*(1-weight)+raw*weight, cap, maxp)
def rank_protect(df):
    out=df.copy()
    for race,g in out.groupby('_race_key'):
        prod_top_idx=g.sort_values('production_display_price_used', ascending=True, kind='mergesort').index[0]
        # iteratively pull production top down if worse than rank 2
        for _ in range(20):
            ranks=out.loc[g.index,'guarded_display_fair_price'].rank(method='first', ascending=True)
            if ranks.loc[prod_top_idx] <= 2: break
            cur=out.loc[prod_top_idx,'guarded_display_fair_price']; prod=out.loc[prod_top_idx,'production_display_price_used']
            out.loc[prod_top_idx,'guarded_display_fair_price']=max(1.01, prod*1.10 if not pd.isna(prod) else cur*0.9)
            out.loc[prod_top_idx,'guardrail_reason'] += '|TOP_PICK_PROTECTED'
        # final cap +/-25 max30
        for idx in g.index:
            prod=out.loc[idx,'production_display_price_used']; val=out.loc[idx,'guarded_display_fair_price']
            out.loc[idx,'guarded_display_fair_price']=clamp_move(prod,val,0.25,30)
    return out

side=pd.read_csv(SIDE,dtype=str,keep_default_na=False,low_memory=False) if SIDE.exists() else pd.DataFrame()
if side.empty:
    out=pd.DataFrame(); metrics={'built_at':datetime.now(timezone.utc).isoformat(),'rows':0,'status':'GUARDED_CANDIDATES_BLOCKED_NO_INPUT'}
else:
    for c in ['production_display_price_used','v7_2_display_price_used','v7_2_probability','v7_2_fair_price','production_rank_in_race','v7_2_rank_in_race']:
        side[c]=pd.to_numeric(side[c], errors='coerce')
    side['_race_key']=side['race_date'].astype(str)+'|'+side['track'].astype(str)+'|'+side['race_no'].astype(str)
    all_rows=[]
    for strategy in ['SOFT_BLEND_50','SOFT_BLEND_30','SOURCE_GATED_BLEND','RANK_PROTECTED']:
        df=side.copy()
        guarded=[]; reasons=[]; sources=[]
        for r in df.itertuples(index=False):
            prod=getattr(r,'production_display_price_used'); raw=getattr(r,'v7_2_display_price_used'); src=getattr(r,'v7_2_probability_source')
            q=source_quality(src)
            if strategy=='SOFT_BLEND_50':
                val=apply_blend(prod,raw,0.50,0.35,50); reason='BLEND_50_CAP_35_MAX_50'; source='SOFT_BLEND_50'
            elif strategy=='SOFT_BLEND_30':
                val=apply_blend(prod,raw,0.30,0.25,35); reason='BLEND_30_CAP_25_MAX_35'; source='SOFT_BLEND_30'
            elif strategy in ['SOURCE_GATED_BLEND','RANK_PROTECTED']:
                if q=='STRONG': val=apply_blend(prod,raw,0.50,0.35,35); reason='STRONG_SOURCE_BLEND_50_CAP_35_MAX_35'; source='SOURCE_GATED_STRONG'
                elif q=='MEDIUM': val=apply_blend(prod,raw,0.25,0.20,35); reason='MEDIUM_SOURCE_BLEND_25_CAP_20_MAX_35'; source='SOURCE_GATED_MEDIUM'
                else: val=prod; reason='WEAK_SOURCE_PRODUCTION_FALLBACK'; source='SOURCE_GATED_FALLBACK'
            guarded.append(val); reasons.append(reason); sources.append(source)
        df['strategy']=strategy
        df['guarded_display_fair_price']=guarded
        df['guarded_fair_price_source']=sources
        df['guardrail_reason']=reasons
        if strategy=='RANK_PROTECTED':
            df=rank_protect(df)
            df['strategy']='RANK_PROTECTED'
        df['guarded_price_delta']=(df['guarded_display_fair_price']-df['production_display_price_used']).abs()
        df['guarded_pct_delta']=(df['guarded_price_delta']/df['production_display_price_used'].replace(0,np.nan))*100
        df['guarded_rank']=df.groupby('_race_key')['guarded_display_fair_price'].rank(method='first', ascending=True)
        df['production_rank']=df['production_rank_in_race']
        df['v7_2_rank']=df['v7_2_rank_in_race']
        df['guarded_decision_change_flag']=(((df['guarded_rank']-df['production_rank']).abs()>=2).fillna(False) | (df['guarded_pct_delta']>=30).fillna(False)).map(lambda x:'YES' if bool(x) else 'NO')
        df['guarded_movement_band']=df['guarded_pct_delta'].map(band)
        df['production_changed_value']='NO'
        df['live_wired_value']='NO'
        keep=['strategy','race_date','track','race_no','runner_no','saddlecloth','horse','production_display_price_used','v7_2_display_price_used','v7_2_probability','v7_2_fair_price','v7_2_probability_source','production_rank','v7_2_rank','guarded_display_fair_price','guarded_fair_price_source','guarded_price_delta','guarded_pct_delta','guarded_rank','guarded_decision_change_flag','guarded_movement_band','guardrail_reason','production_changed_value','live_wired_value']
        all_rows.append(df[keep])
    out=pd.concat(all_rows, ignore_index=True)
    metrics={'built_at':datetime.now(timezone.utc).isoformat(),'strategies':4,'rows':len(out),'runners_per_strategy':len(side),'status':'GUARDED_DISPLAY_CANDIDATES_BUILT_REVIEW_REQUIRED'}
out.to_csv(OUT,index=False)
pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_csv(SUM,index=False)
report=f'''EDGEiQ V7.2 GUARDED DISPLAY CANDIDATES V1

- Status: {metrics.get('status')}
- No activation occurred.
- Strategies built: {metrics.get('strategies','')}
- Rows: {metrics.get('rows')}
- Runners per strategy: {metrics.get('runners_per_strategy','')}

Strategies: SOFT_BLEND_50, SOFT_BLEND_30, SOURCE_GATED_BLEND, RANK_PROTECTED. All preserve V7.2 probability as reference and create guarded display prices only.
'''
REP.write_text(report,encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_string(index=False))
print(report)
