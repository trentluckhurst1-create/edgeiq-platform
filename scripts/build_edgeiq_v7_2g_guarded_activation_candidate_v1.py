from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import re

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'public'/'data'
CANDS=DATA/'edgeiq_v7_2_guarded_display_candidates_v1.csv'
AUDSUM=DATA/'edgeiq_v7_2_guarded_display_candidates_audit_v1_summary.csv'
ONCAND=DATA/'edgeiq_live_runner_board_v7_2_feature_flag_on_candidate.csv'
OUTBOARD=DATA/'edgeiq_live_runner_board_v7_2g_guarded_activation_candidate.csv'
OUT=DATA/'edgeiq_v7_2g_guarded_activation_candidate_v1.csv'
SUM=DATA/'edgeiq_v7_2g_guarded_activation_candidate_v1_summary.csv'
REP=DATA/'edgeiq_v7_2g_guarded_activation_candidate_v1_report.txt'

def metrics(path):
    if not path.exists(): return {}
    df=pd.read_csv(path,dtype=str,keep_default_na=False)
    return dict(zip(df['metric'],df['value'])) if {'metric','value'}.issubset(df.columns) else {}
def key(df):
    return df['race_date'].astype(str)+'|'+df['track'].astype(str).str.upper().str.strip()+'|'+df['race_no'].astype(str)+'|'+df['horse'].astype(str).str.upper().str.replace(r'[^A-Z0-9\s]','',regex=True).str.replace(r'\s+',' ',regex=True).str.strip()

m=metrics(AUDSUM); rec=m.get('recommended_strategy','RANK_PROTECTED'); eligible=m.get('eligible_strategies','NONE')!='NONE'
cands=pd.read_csv(CANDS,dtype=str,keep_default_na=False,low_memory=False) if CANDS.exists() else pd.DataFrame()
board=pd.read_csv(ONCAND,dtype=str,keep_default_na=False,low_memory=False) if ONCAND.exists() else pd.DataFrame()
if cands.empty or board.empty:
    out=pd.DataFrame(); board_out=board.copy(); status='V7_2G_BLOCKED_INPUT_MISSING'
else:
    chosen=cands[cands['strategy'].eq(rec)].copy()
    chosen['_join_key']=key(chosen); board['_join_key']=key(board)
    cols=['_join_key','strategy','v7_2_probability','v7_2_display_price_used','guarded_display_fair_price','guardrail_reason','production_display_price_used','guarded_price_delta','guarded_pct_delta','guarded_rank','production_rank','v7_2_rank','guarded_decision_change_flag','guarded_movement_band','guarded_fair_price_source']
    merged=board.merge(chosen[cols], on='_join_key', how='left', suffixes=('','_g'))
    merged['edgeiq_v7_2g_probability']=merged['v7_2_probability']
    merged['edgeiq_v7_2g_raw_display_fair_price']=merged['v7_2_display_price_used']
    merged['edgeiq_v7_2g_guarded_display_fair_price']=merged['guarded_display_fair_price']
    merged['edgeiq_v7_2g_strategy']=rec
    merged['edgeiq_v7_2g_guardrail_reason']=merged['guardrail_reason']
    merged['edgeiq_v7_2g_feature_flag']='ON_CANDIDATE_ONLY'
    merged['edgeiq_v7_2g_live_wired_flag']='NO'
    merged['edgeiq_v7_2g_production_changed']='NO'
    status='V7_2G_ACTIVATION_REVIEW_CANDIDATE_BUILT' if eligible else 'V7_2G_RESEARCH_ONLY_NO_ELIGIBLE_STRATEGY'
    merged['edgeiq_v7_2g_activation_status']=status
    board_out=merged.drop(columns=['_join_key'], errors='ignore')
    out=merged[['race_date','track','race_no','horse','production_display_price_used','v7_2_display_price_used','guarded_display_fair_price','v7_2_probability','strategy','guardrail_reason','guarded_price_delta','guarded_pct_delta','production_rank','v7_2_rank','guarded_rank','guarded_decision_change_flag','guarded_movement_band','edgeiq_v7_2g_feature_flag','edgeiq_v7_2g_live_wired_flag','edgeiq_v7_2g_production_changed','edgeiq_v7_2g_activation_status']].copy()
board_out.to_csv(OUTBOARD,index=False); out.to_csv(OUT,index=False)
metrics_out={'built_at':datetime.now(timezone.utc).isoformat(),'rows':len(out),'recommended_strategy':rec,'eligible_strategy_used':'YES' if eligible else 'NO','activation_status':status,'feature_flag_values':'ON_CANDIDATE_ONLY','live_wired_values':'NO','production_changed_values':'NO','status':status}
pd.DataFrame([{'metric':k,'value':v} for k,v in metrics_out.items()]).to_csv(SUM,index=False)
report=f'''EDGEiQ V7.2G GUARDED ACTIVATION CANDIDATE V1

- Status: {status}
- Recommended strategy used: {rec}
- Eligible strategy used: {'YES' if eligible else 'NO'}
- Rows: {len(out)}
- Feature flag: ON_CANDIDATE_ONLY
- Live wired: NO
- Production changed: NO
- No live files overwritten.

V7.2G is a guarded display layer candidate. It preserves V7.2 probability as reference and applies guarded display fair prices only.
'''
REP.write_text(report,encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in metrics_out.items()]).to_string(index=False))
print(report)
