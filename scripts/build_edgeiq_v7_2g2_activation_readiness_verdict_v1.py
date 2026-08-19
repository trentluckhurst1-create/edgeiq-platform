from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'public'/'data'
AUD=DATA/'edgeiq_v7_2g2_targeted_suppression_candidates_audit_v1_summary.csv'
CAND=DATA/'edgeiq_v7_2g2_activation_candidate_v1_summary.csv'
SIDE=DATA/'edgeiq_v7_2g2_side_by_side_review_v1_summary.csv'
OUT=DATA/'edgeiq_v7_2g2_activation_readiness_verdict_v1.csv'
REP=DATA/'edgeiq_v7_2g2_activation_readiness_verdict_v1_report.txt'

def m(path):
    if not path.exists(): return {}
    df=pd.read_csv(path,dtype=str,keep_default_na=False)
    return dict(zip(df['metric'],df['value'])) if {'metric','value'}.issubset(df.columns) else {}
aud=m(AUD); cand=m(CAND); side=m(SIDE)
elig=aud.get('eligible_strategies','NONE')!='NONE'
rec=aud.get('recommended_strategy','')
rec_status=aud.get('recommended_status','')
prod_ok=cand.get('production_changed_values')=='NO'; live_ok=cand.get('live_wired_values')=='NO'; rows_ok=cand.get('rows','0') not in ['','0']
if not rows_ok or not prod_ok or not live_ok:
    verdict='V7_2G2_BLOCKED'
elif elig and rec_status=='ELIGIBLE_BUT_TOO_CONSERVATIVE_REVIEW_REQUIRED':
    verdict='V7_2G2_REVIEW_REQUIRED_TOO_CONSERVATIVE'
elif elig:
    verdict='V7_2G2_READY_FOR_HUMAN_VISUAL_REVIEW'
else:
    verdict='V7_2G2_RESEARCH_ONLY_MORE_GUARDRAILS_REQUIRED'
row={'built_at':datetime.now(timezone.utc).isoformat(),'eligible_strategies':aud.get('eligible_strategies',''),'recommended_strategy':rec,'recommended_status':rec_status,'candidate_status':cand.get('status',''),'side_by_side_status':side.get('status',''),'rows':cand.get('rows',''),'raw_decision_changes':side.get('raw_decision_changes',''),'v7_2g_decision_changes':side.get('v7_2g_decision_changes',''),'v7_2g2_decision_changes':side.get('v7_2g2_decision_changes',''),'raw_large_extreme':side.get('raw_large_extreme',''),'v7_2g_large_extreme':side.get('v7_2g_large_extreme',''),'v7_2g2_large_extreme':side.get('v7_2g2_large_extreme',''),'raw_top_pick_changes':side.get('raw_top_pick_changes',''),'v7_2g_top_pick_changes':side.get('v7_2g_top_pick_changes',''),'v7_2g2_top_pick_changes':side.get('v7_2g2_top_pick_changes',''),'v7_2g_high_risk_races':side.get('v7_2g_high_risk_races',''),'v7_2g2_high_risk_races':side.get('v7_2g2_high_risk_races',''),'production_changed_values':cand.get('production_changed_values',''),'live_wired_values':cand.get('live_wired_values',''),'verdict':verdict,'next_required_action':'HUMAN_VISUAL_REVIEW_ONLY_BEFORE_ANY_STAGING_OR_ACTIVATION' if verdict=='V7_2G2_READY_FOR_HUMAN_VISUAL_REVIEW' else 'REVIEW_BEFORE_ANY_STAGING'}
pd.DataFrame([row]).to_csv(OUT,index=False)
report=f'''EDGEiQ V7.2G2 ACTIVATION READINESS VERDICT V1

- Verdict: {verdict}
- No activation occurred.
- No live files overwritten.
- UI unchanged.
- Feature flag ON candidate only.
- V7.2G2 is a guarded display layer, not probability replacement.
- V7.2 probability remains reference.
- Production changed values: {row['production_changed_values']}
- Live wired values: {row['live_wired_values']}

Strategy:
- Recommended strategy: {row['recommended_strategy']}
- Eligible strategies: {row['eligible_strategies']}
- Recommended status: {row['recommended_status']}

Risk reduction:
- Decision changes raw -> G -> G2: {row['raw_decision_changes']} -> {row['v7_2g_decision_changes']} -> {row['v7_2g2_decision_changes']}
- Large/extreme raw -> G -> G2: {row['raw_large_extreme']} -> {row['v7_2g_large_extreme']} -> {row['v7_2g2_large_extreme']}
- Top-pick changes raw -> G -> G2: {row['raw_top_pick_changes']} -> {row['v7_2g_top_pick_changes']} -> {row['v7_2g2_top_pick_changes']}
- High-risk races G -> G2: {row['v7_2g_high_risk_races']} -> {row['v7_2g2_high_risk_races']}

Human visual review is required before any staging or activation.
'''
REP.write_text(report,encoding='utf-8')
print(pd.DataFrame([row]).to_string(index=False)); print(report)
