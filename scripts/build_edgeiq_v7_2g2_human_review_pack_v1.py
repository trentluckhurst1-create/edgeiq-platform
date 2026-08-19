from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'public'/'data'
SIDE=DATA/'edgeiq_v7_2g2_side_by_side_review_v1.csv'
CAND=DATA/'edgeiq_v7_2g2_activation_candidate_v1.csv'
VERD=DATA/'edgeiq_v7_2g2_activation_readiness_verdict_v1.csv'
OUT=DATA/'edgeiq_v7_2g2_human_review_pack_v1.csv'
SUM=DATA/'edgeiq_v7_2g2_human_review_pack_v1_summary.csv'
REP=DATA/'edgeiq_v7_2g2_human_review_pack_v1_report.txt'

def m(path):
    if not path.exists(): return {}
    df=pd.read_csv(path,dtype=str,keep_default_na=False)
    return df.iloc[0].to_dict() if len(df) else {}

df=pd.read_csv(SIDE,dtype=str,keep_default_na=False,low_memory=False) if SIDE.exists() else pd.DataFrame()
ver=m(VERD)
if df.empty:
    out=pd.DataFrame(); metrics={'built_at':datetime.now(timezone.utc).isoformat(),'review_rows':0,'status':'HUMAN_REVIEW_PACK_BLOCKED_NO_INPUT'}
else:
    for c in ['production_display','raw_v7_2_display','v7_2g_display','v7_2g2_display','production_rank','raw_v7_2_rank','v7_2g_rank','v7_2g2_rank','v7_2g2_delta_abs','v7_2g2_delta_pct']:
        df[c]=pd.to_numeric(df[c],errors='coerce')
    df['race_key']=df['race_date'].astype(str)+'|'+df['track'].astype(str)+'|'+df['race_no'].astype(str)
    # race-level G2 high risk
    high_keys=set(); reasons={}
    for rk,g in df.groupby('race_key'):
        prod_top=g.sort_values('production_display',ascending=True,kind='mergesort').iloc[0]['horse']
        g2_top=g.sort_values('v7_2g2_display',ascending=True,kind='mergesort').iloc[0]['horse']
        large=int(g['v7_2g2_movement_band'].isin(['LARGE','EXTREME']).sum())
        dec=int(g['v7_2g2_decision_change_flag'].eq('YES').sum())
        reason=[]
        if prod_top!=g2_top: reason.append('TOP_PICK_CHANGED')
        if large>3: reason.append('LARGE_EXTREME_GT_3')
        if len(g) and dec/len(g)>0.35: reason.append('DECISION_RATIO_GT_35')
        if reason:
            high_keys.add(rk); reasons[rk]='|'.join(reason)
    df['high_risk_flag']=df['race_key'].map(lambda x:'YES' if x in high_keys else 'NO')
    df['rank_delta']=(df['v7_2g2_rank']-df['production_rank'])
    df['abs_delta']=df['v7_2g2_delta_abs']
    df['pct_delta']=df['v7_2g2_delta_pct']
    # select review rows
    idx=set(df[df['high_risk_flag'].eq('YES')].index)
    idx.update(df.sort_values('abs_delta',ascending=False).head(30).index)
    idx.update(df.sort_values('pct_delta',ascending=False).head(30).index)
    idx.update(df[df['rank_delta'].abs()>=2].index)
    idx.update(df[df['v7_2g2_movement_band'].isin(['LARGE','EXTREME'])].index)
    out=df.loc[sorted(idx)].copy()
    def reason_row(r):
        bits=[]
        if r.high_risk_flag=='YES': bits.append('HIGH_RISK_RACE')
        if abs(r.rank_delta)>=2: bits.append('MAJOR_RANK_MOVE')
        if r.v7_2g2_movement_band in ['LARGE','EXTREME']: bits.append('LARGE_OR_EXTREME_MOVE')
        if r.abs_delta in set(df.sort_values('abs_delta',ascending=False).head(30)['abs_delta']): bits.append('TOP_ABS_DELTA')
        if r.pct_delta in set(df.sort_values('pct_delta',ascending=False).head(30)['pct_delta']): bits.append('TOP_PCT_DELTA')
        return '|'.join(bits) if bits else 'REVIEW'
    out['review_reason']=out.apply(reason_row,axis=1)
    out['guardrail_reason']=out.get('v7_2g2_guardrail_reason','')
    out['probability_source']='V7_2_REFERENCE'
    cols=['race_date','track','race_no','horse','production_display','raw_v7_2_display','v7_2g_display','v7_2g2_display','production_rank','raw_v7_2_rank','v7_2g_rank','v7_2g2_rank','rank_delta','abs_delta','pct_delta','v7_2g2_movement_band','high_risk_flag','guardrail_reason','probability_source','review_reason']
    out=out[cols].rename(columns={'production_display':'production_display_price','raw_v7_2_display':'raw_v7_2_display_price','v7_2g_display':'v7_2g_display_price','v7_2g2_display':'v7_2g2_display_price','v7_2g2_movement_band':'movement_band'})
    out.to_csv(OUT,index=False)
    metrics={'built_at':datetime.now(timezone.utc).isoformat(),'review_rows':len(out),'high_risk_races':len(high_keys),'large_extreme_rows':int(df['v7_2g2_movement_band'].isin(['LARGE','EXTREME']).sum()),'major_rank_move_rows':int(df['rank_delta'].abs().ge(2).sum()),'biggest_abs_delta':round(float(df['abs_delta'].max()),4),'biggest_pct_delta':round(float(df['pct_delta'].max()),4),'final_verdict':ver.get('verdict',''),'status':'HUMAN_REVIEW_PACK_BUILT'}
    pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_csv(SUM,index=False)
    high_lines='\n'.join([f"- {x}" for x in sorted(high_keys)]) or '- None.'
    top=out.sort_values('abs_delta',ascending=False).head(20)
    top_lines='\n'.join([f"- {r.track} R{r.race_no} {r.horse}: prod {r.production_display_price}, G2 {r.v7_2g2_display_price}, delta {r.abs_delta}, {r.review_reason}" for r in top.itertuples(index=False)])
    report=f'''EDGEiQ V7.2G2 HUMAN REVIEW PACK V1

Executive summary:
- Review rows: {len(out)}
- High-risk races: {len(high_keys)}
- Large/extreme rows: {metrics['large_extreme_rows']}
- Major rank move rows: {metrics['major_rank_move_rows']}
- Biggest abs delta: {metrics['biggest_abs_delta']}
- Biggest pct delta: {metrics['biggest_pct_delta']}
- Final verdict: {metrics['final_verdict']}
- No activation occurred.

High-risk races:
{high_lines}

Biggest 20 remaining changes:
{top_lines}
'''
    REP.write_text(report,encoding='utf-8')
    print(pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_string(index=False)); print(report)
    raise SystemExit
out.to_csv(OUT,index=False)
pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_csv(SUM,index=False)
REP.write_text('EDGEiQ V7.2G2 HUMAN REVIEW PACK V1\n\nBlocked: no input.\n',encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_string(index=False)); print(REP.read_text(encoding='utf-8'))
