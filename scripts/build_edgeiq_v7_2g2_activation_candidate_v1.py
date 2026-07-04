from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'public'/'data'
CANDS=DATA/'edgeiq_v7_2g2_targeted_suppression_candidates_v1.csv'
AUDSUM=DATA/'edgeiq_v7_2g2_targeted_suppression_candidates_audit_v1_summary.csv'
BOARD=DATA/'edgeiq_live_runner_board_v7_2_feature_flag_on_candidate.csv'
OUTBOARD=DATA/'edgeiq_live_runner_board_v7_2g2_activation_candidate.csv'
OUT=DATA/'edgeiq_v7_2g2_activation_candidate_v1.csv'
SUM=DATA/'edgeiq_v7_2g2_activation_candidate_v1_summary.csv'
REP=DATA/'edgeiq_v7_2g2_activation_candidate_v1_report.txt'

def m(path):
    if not path.exists(): return {}
    df=pd.read_csv(path,dtype=str,keep_default_na=False)
    return dict(zip(df['metric'],df['value'])) if {'metric','value'}.issubset(df.columns) else {}
def key(df): return df['race_date'].astype(str)+'|'+df['track'].astype(str).str.upper().str.strip()+'|'+df['race_no'].astype(str)+'|'+df['horse'].astype(str).str.upper().str.replace(r'[^A-Z0-9\s]','',regex=True).str.replace(r'\s+',' ',regex=True).str.strip()

met=m(AUDSUM); rec=met.get('recommended_strategy','HIGH_RISK_BLEND_10'); eligible=met.get('eligible_strategies','NONE')!='NONE'
cands=pd.read_csv(CANDS,dtype=str,keep_default_na=False,low_memory=False) if CANDS.exists() else pd.DataFrame()
board=pd.read_csv(BOARD,dtype=str,keep_default_na=False,low_memory=False) if BOARD.exists() else pd.DataFrame()
if cands.empty or board.empty:
    out=pd.DataFrame(); board_out=board.copy(); status='V7_2G2_BLOCKED_INPUT_MISSING'
else:
    chosen=cands[cands['strategy'].eq(rec)].copy(); chosen['join_key_g2']=key(chosen); board['join_key_g2']=key(board)
    cols=['join_key_g2','strategy','raw_v7_2_display','guarded_v7_2g_display','v7_2g2_display_price','v7_2g2_guardrail_reason','v7_2g2_delta_abs','v7_2g2_delta_pct','production_rank','raw_v7_2_rank','v7_2g_rank','v7_2g2_rank','v7_2g2_decision_change_flag','v7_2g2_movement_band','high_risk_race_flag']
    merged=board.merge(chosen[cols],on='join_key_g2',how='left')
    prob_col='edgeiq_v7_2_preview_probability' if 'edgeiq_v7_2_preview_probability' in merged.columns else 'edgeiq_probability_v7_2'
    merged['edgeiq_v7_2g2_probability']=merged.get(prob_col,'')
    merged['edgeiq_v7_2g2_raw_display_fair_price']=merged['raw_v7_2_display']
    merged['edgeiq_v7_2g2_previous_guarded_display_fair_price']=merged['guarded_v7_2g_display']
    merged['edgeiq_v7_2g2_guarded_display_fair_price']=merged['v7_2g2_display_price']
    merged['edgeiq_v7_2g2_strategy']=rec
    merged['edgeiq_v7_2g2_guardrail_reason']=merged['v7_2g2_guardrail_reason']
    merged['edgeiq_v7_2g2_feature_flag']='ON_CANDIDATE_ONLY'
    merged['edgeiq_v7_2g2_live_wired_flag']='NO'
    merged['edgeiq_v7_2g2_production_changed']='NO'
    status='V7_2G2_ACTIVATION_CANDIDATE_BUILT_REVIEW_REQUIRED' if eligible else 'V7_2G2_RESEARCH_ONLY_NO_ELIGIBLE_STRATEGY'
    merged['edgeiq_v7_2g2_activation_status']=status
    board_out=merged.drop(columns=['join_key_g2'], errors='ignore')
    out=merged[['race_date','track','race_no','horse','raw_v7_2_display','guarded_v7_2g_display','v7_2g2_display_price','edgeiq_v7_2g2_probability','strategy','v7_2g2_guardrail_reason','v7_2g2_delta_abs','v7_2g2_delta_pct','production_rank','raw_v7_2_rank','v7_2g_rank','v7_2g2_rank','v7_2g2_decision_change_flag','v7_2g2_movement_band','high_risk_race_flag','edgeiq_v7_2g2_feature_flag','edgeiq_v7_2g2_live_wired_flag','edgeiq_v7_2g2_production_changed','edgeiq_v7_2g2_activation_status']].copy()
board_out.to_csv(OUTBOARD,index=False); out.to_csv(OUT,index=False)
metrics={'built_at':datetime.now(timezone.utc).isoformat(),'rows':len(out),'recommended_strategy':rec,'eligible_strategy_found':'YES' if eligible else 'NO','activation_status':status,'feature_flag_values':'ON_CANDIDATE_ONLY','live_wired_values':'NO','production_changed_values':'NO','status':status}
pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_csv(SUM,index=False)
report=f'''EDGEiQ V7.2G2 ACTIVATION CANDIDATE V1

- Status: {status}
- Recommended strategy: {rec}
- Eligible strategy found: {'YES' if eligible else 'NO'}
- Rows: {len(out)}
- Feature flag: ON_CANDIDATE_ONLY
- Live wired: NO
- Production changed: NO
- No live files overwritten.
'''
REP.write_text(report,encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_string(index=False)); print(report)
