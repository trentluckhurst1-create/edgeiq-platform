from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'public'/'data'
SIDE=DATA/'edgeiq_v7_2_activation_side_by_side_v1_summary.csv'
RACE=DATA/'edgeiq_v7_2_activation_race_level_changes_v1_summary.csv'
TOP=DATA/'edgeiq_v7_2_activation_top_changes_review_v1_summary.csv'
CP=DATA/'edgeiq_v7_2_feature_flag_on_candidate_checkpoint_v1.csv'
OUT=DATA/'edgeiq_v7_2_activation_readiness_verdict_v1.csv'
REP=DATA/'edgeiq_v7_2_activation_readiness_verdict_v1_report.txt'

def m(path):
    if not path.exists(): return {}
    df=pd.read_csv(path,dtype=str,keep_default_na=False)
    if {'metric','value'}.issubset(df.columns): return dict(zip(df['metric'],df['value']))
    return df.iloc[0].to_dict() if len(df) else {}
def f(v):
    try: return float(v)
    except Exception: return 0.0

a=m(SIDE); r=m(RACE); t=m(TOP); c=m(CP)
side_ok=a.get('status')=='SIDE_BY_SIDE_COMPARISON_BUILT_REVIEW_REQUIRED'
v72_rows=f(a.get('v7_2_price_rows',0))
prod_ok=a.get('production_changed_values')=='NO'
live_ok=a.get('live_wired_values')=='NO'
top_pct=f(r.get('top_pick_changed_pct',0))
high_pct=f(r.get('high_risk_pct',0))
if not side_ok or v72_rows<=0 or not prod_ok or not live_ok:
    verdict='ACTIVATION_BLOCKED'
elif top_pct>20 or high_pct>20:
    verdict='ACTIVATION_REVIEW_REQUIRED_SIGNIFICANT_CHANGES'
else:
    verdict='ACTIVATION_READY_FOR_HUMAN_REVIEW'
row={'built_at':datetime.now(timezone.utc).isoformat(),'side_by_side_status':a.get('status',''),'v7_2_price_rows':a.get('v7_2_price_rows',''),'production_changed_values':a.get('production_changed_values',''),'live_wired_values':a.get('live_wired_values',''),'decision_change_rows':a.get('decision_change_rows',''),'decision_change_pct':a.get('decision_change_pct',''),'large_or_extreme_rows':a.get('large_or_extreme_rows',''),'top_pick_changed_races':r.get('top_pick_changed_races',''),'top_pick_changed_pct':r.get('top_pick_changed_pct',''),'high_risk_races':r.get('high_risk_races',''),'high_risk_pct':r.get('high_risk_pct',''),'top_changes_suspicious_price_rows':t.get('suspicious_price_rows',''),'candidate_checkpoint_status':c.get('final_status',''),'verdict':verdict,'next_required_action':'DO_NOT_ACTIVATE_REVIEW_SIGNIFICANT_CHANGES' if verdict!='ACTIVATION_READY_FOR_HUMAN_REVIEW' else 'HUMAN_REVIEW_THEN_CONTROLLED_ON_STAGING_IF_APPROVED'}
pd.DataFrame([row]).to_csv(OUT,index=False)
report=f'''EDGEiQ V7.2 ACTIVATION READINESS VERDICT V1

- Verdict: {verdict}
- No activation occurred.
- Candidate only.
- Current live files remain feature flag OFF.

Side-by-side summary:
- Status: {row['side_by_side_status']}
- V7.2 price rows: {row['v7_2_price_rows']}
- Decision change rows: {row['decision_change_rows']} ({row['decision_change_pct']}%)
- Large/extreme rows: {row['large_or_extreme_rows']}
- Production changed values: {row['production_changed_values']}
- Live wired values: {row['live_wired_values']}

Race-level summary:
- Top-pick changed races: {row['top_pick_changed_races']} ({row['top_pick_changed_pct']}%)
- High-risk races: {row['high_risk_races']} ({row['high_risk_pct']}%)
- Suspicious price rows in top-change review: {row['top_changes_suspicious_price_rows']}

Assessment:
The candidate is technically available for review, but activation should not proceed from this audit state. Top-pick changes and high-risk race counts exceed the 20% review threshold. The next step is human review and likely V7.2 display calibration/guardrail work before any controlled ON staging.

Next step, only after approval:
- Controlled overwrite live files with feature flag ON candidate only if the significant changes are accepted or corrected.
'''
REP.write_text(report,encoding='utf-8')
print(pd.DataFrame([row]).to_string(index=False))
print(report)
