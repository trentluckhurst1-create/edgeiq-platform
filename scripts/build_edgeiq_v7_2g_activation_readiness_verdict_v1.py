from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'public'/'data'
SIDE=DATA/'edgeiq_v7_2g_side_by_side_review_v1_summary.csv'
CAND=DATA/'edgeiq_v7_2g_guarded_activation_candidate_v1_summary.csv'
AUD=DATA/'edgeiq_v7_2_guarded_display_candidates_audit_v1_summary.csv'
OUT=DATA/'edgeiq_v7_2g_activation_readiness_verdict_v1.csv'
REP=DATA/'edgeiq_v7_2g_activation_readiness_verdict_v1_report.txt'

def m(path):
    if not path.exists(): return {}
    df=pd.read_csv(path,dtype=str,keep_default_na=False)
    return dict(zip(df['metric'],df['value'])) if {'metric','value'}.issubset(df.columns) else {}
side=m(SIDE); cand=m(CAND); aud=m(AUD)
prod_ok=cand.get('production_changed_values')=='NO'; live_ok=cand.get('live_wired_values')=='NO'; rows_ok=cand.get('rows','0') not in ['0','']
eligible=aud.get('eligible_strategies','NONE')!='NONE'
if not rows_ok or not prod_ok:
    verdict='V7_2G_BLOCKED'
elif eligible:
    verdict='V7_2G_READY_FOR_HUMAN_VISUAL_REVIEW'
else:
    verdict='V7_2G_RESEARCH_ONLY_MORE_GUARDRAILS_REQUIRED'
row={'built_at':datetime.now(timezone.utc).isoformat(),'recommended_strategy':cand.get('recommended_strategy',''),'eligible_strategy_used':cand.get('eligible_strategy_used',''),'eligible_strategies':aud.get('eligible_strategies',''),'candidate_status':cand.get('status',''),'side_by_side_status':side.get('status',''),'rows':cand.get('rows',''),'raw_decision_change_rows':side.get('raw_decision_change_rows',''),'guarded_decision_change_rows':side.get('guarded_decision_change_rows',''),'raw_large_extreme_rows':side.get('raw_large_extreme_rows',''),'guarded_large_extreme_rows':side.get('guarded_large_extreme_rows',''),'guarded_top_pick_changed_races':side.get('guarded_top_pick_changed_races',''),'guarded_high_risk_races':side.get('guarded_high_risk_races',''),'production_changed_values':cand.get('production_changed_values',''),'live_wired_values':cand.get('live_wired_values',''),'verdict':verdict,'next_required_action':'MORE_GUARDRAILS_BEFORE_VISUAL_REVIEW' if verdict!='V7_2G_READY_FOR_HUMAN_VISUAL_REVIEW' else 'HUMAN_VISUAL_REVIEW_ONLY'}
pd.DataFrame([row]).to_csv(OUT,index=False)
report=f'''EDGEiQ V7.2G ACTIVATION READINESS VERDICT V1

- Verdict: {verdict}
- No activation occurred.
- No live files overwritten.
- Feature flag ON candidate only.
- V7.2G is a guarded display layer, not a probability replacement.
- Production changed values: {row['production_changed_values']}
- Live wired values: {row['live_wired_values']}

Candidate summary:
- Recommended strategy: {row['recommended_strategy']}
- Eligible strategy used: {row['eligible_strategy_used']}
- Eligible strategies: {row['eligible_strategies']}
- Rows: {row['rows']}

Disruption reduction:
- Raw decision change rows: {row['raw_decision_change_rows']}
- Guarded decision change rows: {row['guarded_decision_change_rows']}
- Raw large/extreme rows: {row['raw_large_extreme_rows']}
- Guarded large/extreme rows: {row['guarded_large_extreme_rows']}
- Guarded top-pick changed races: {row['guarded_top_pick_changed_races']}
- Guarded high-risk races: {row['guarded_high_risk_races']}

Assessment:
V7.2G materially reduced disruption, but no tested strategy met the activation eligibility gate. Continue guardrail research before any human visual review for activation.
'''
REP.write_text(report,encoding='utf-8')
print(pd.DataFrame([row]).to_string(index=False)); print(report)
