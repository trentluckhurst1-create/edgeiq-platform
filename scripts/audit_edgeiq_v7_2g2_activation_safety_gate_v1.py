from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'public'/'data'
CAND=DATA/'edgeiq_v7_2g2_activation_candidate_v1.csv'
BOARD=DATA/'edgeiq_live_runner_board_v7_2g2_activation_candidate.csv'
VERD=DATA/'edgeiq_v7_2g2_activation_readiness_verdict_v1.csv'
PACK=DATA/'edgeiq_v7_2g2_human_review_pack_v1_summary.csv'
OUT=DATA/'edgeiq_v7_2g2_activation_safety_gate_v1.csv'
SUM=DATA/'edgeiq_v7_2g2_activation_safety_gate_v1_summary.csv'
REP=DATA/'edgeiq_v7_2g2_activation_safety_gate_v1_report.txt'

def m(path):
    if not path.exists(): return {}
    df=pd.read_csv(path,dtype=str,keep_default_na=False)
    return dict(zip(df['metric'],df['value'])) if {'metric','value'}.issubset(df.columns) else (df.iloc[0].to_dict() if len(df) else {})
def f(v):
    try: return float(v)
    except: return 0.0

cand=pd.read_csv(CAND,dtype=str,keep_default_na=False,low_memory=False) if CAND.exists() else pd.DataFrame()
board=pd.read_csv(BOARD,dtype=str,keep_default_na=False,low_memory=False) if BOARD.exists() else pd.DataFrame()
ver=m(VERD); pack=m(PACK)
# compute candidate metrics
if cand.empty:
    high=top=dec_pct=large_pct=rows_at_cap=nulls=0; minp=maxp=0
else:
    for c in ['v7_2g2_display_price','v7_2g2_delta_pct']:
        cand[c]=pd.to_numeric(cand[c],errors='coerce')
    cand['race_key']=cand['race_date'].astype(str)+'|'+cand['track'].astype(str)+'|'+cand['race_no'].astype(str)
    high=top=0
    cand['production_rank_num']=pd.to_numeric(cand['production_rank'],errors='coerce'); cand['v7_2g2_rank_num']=pd.to_numeric(cand['v7_2g2_rank'],errors='coerce')
    for rk,g in cand.groupby('race_key'):
        # production rank 1 vs g2 rank 1
        prod_top=g.sort_values('production_rank_num',kind='mergesort').iloc[0]['horse']
        g2_top=g.sort_values('v7_2g2_rank_num',kind='mergesort').iloc[0]['horse']
        large=int(g['v7_2g2_movement_band'].isin(['LARGE','EXTREME']).sum())
        dec=int(g['v7_2g2_decision_change_flag'].eq('YES').sum())
        if prod_top!=g2_top: top+=1
        if prod_top!=g2_top or large>3 or dec/len(g)>0.35: high+=1
    dec_pct=float(cand['v7_2g2_decision_change_flag'].eq('YES').mean()*100)
    large_pct=float(cand['v7_2g2_movement_band'].isin(['LARGE','EXTREME']).mean()*100)
    rows_at_cap=int(cand['v7_2g2_display_price'].ge(50).sum())
    nulls=int(cand['v7_2g2_display_price'].isna().sum())
    minp=float(cand['v7_2g2_display_price'].min())
    maxp=float(cand['v7_2g2_display_price'].max())
checks={
 'readiness_verdict_ready': ver.get('verdict')=='V7_2G2_READY_FOR_HUMAN_VISUAL_REVIEW',
 'candidate_rows_gt_0': len(cand)>0,
 'board_candidate_rows_378': len(board)==378,
 'high_risk_races_lte_5': high<=5,
 'top_pick_changed_zero': top==0,
 'decision_change_pct_lte_25': dec_pct<=25,
 'large_extreme_pct_lte_15': large_pct<=15,
 'rows_at_cap_zero': rows_at_cap==0,
 'production_changed_no': (cand.get('edgeiq_v7_2g2_production_changed',pd.Series(['NO'])).astype(str).unique().tolist()==['NO']) if not cand.empty and 'edgeiq_v7_2g2_production_changed' in cand.columns else True,
 'live_wired_no': (cand.get('edgeiq_v7_2g2_live_wired_flag',pd.Series(['NO'])).astype(str).unique().tolist()==['NO']) if not cand.empty and 'edgeiq_v7_2g2_live_wired_flag' in cand.columns else True,
 'no_null_guarded_display': nulls==0,
 'guarded_min_gte_1_01': minp>=1.01,
 'guarded_max_lte_50': maxp<=50,
 'human_review_pack_created': pack.get('status')=='HUMAN_REVIEW_PACK_BUILT'
}
rows=[{'check':k,'pass':'YES' if v else 'NO'} for k,v in checks.items()]
pd.DataFrame(rows).to_csv(OUT,index=False)
status='V7_2G2_ACTIVATION_SAFETY_GATE_PASS_HUMAN_APPROVAL_REQUIRED' if all(checks.values()) else 'V7_2G2_ACTIVATION_SAFETY_GATE_BLOCKED'
metrics={'built_at':datetime.now(timezone.utc).isoformat(),'readiness_verdict':ver.get('verdict',''),'candidate_rows':len(cand),'board_candidate_rows':len(board),'high_risk_races':high,'top_pick_changed_races':top,'decision_change_pct':round(dec_pct,4),'large_extreme_pct':round(large_pct,4),'rows_at_cap':rows_at_cap,'null_guarded_display_prices':nulls,'guarded_display_min':minp,'guarded_display_max':maxp,'human_review_pack_status':pack.get('status',''),'status':status}
pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_csv(SUM,index=False)
report=f'''EDGEiQ V7.2G2 ACTIVATION SAFETY GATE V1

- Status: {status}
- Candidate is safe enough for human approval: {'YES' if status.endswith('REQUIRED') else 'NO'}
- No activation occurred.
- Candidate rows: {len(cand)}
- Board candidate rows: {len(board)}
- High-risk races: {high}
- Top-pick changed races: {top}
- Decision change pct: {round(dec_pct,4)}
- Large/extreme pct: {round(large_pct,4)}
- Rows at cap: {rows_at_cap}
- Guarded display range: {minp} to {maxp}
- Human review pack: {pack.get('status','')}
'''
REP.write_text(report,encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_string(index=False)); print(report)

