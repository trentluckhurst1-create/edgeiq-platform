from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import re

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'public' / 'data'
TSX = BASE / 'src' / 'components' / 'RaceIntelligenceScreen.tsx'
OUT = DATA / 'edgeiq_v7_2_ui_render_switch_audit_v1.csv'
SUM = DATA / 'edgeiq_v7_2_ui_render_switch_audit_v1_summary.csv'
REP = DATA / 'edgeiq_v7_2_ui_render_switch_audit_v1_report.txt'
HELPERS = ['isV72FeatureOn','getV72AwareFairPrice','getV72AwareDisplayFairPrice','getV72AwareProbability','getV72PriceSource']
text = TSX.read_text(encoding='utf-8', errors='ignore') if TSX.exists() else ''
helper_exists = all(h in text for h in HELPERS)
render_refs = 'getV72AwareDisplayFairPrice(row)' in text and 'getV72AwareProbability(row)' in text
flag_condition = 'edgeiq_v7_2_feature_flag' in text and '=== "ON"' in text
fallback_refs = all(x in text for x in ['fair_price','ui_fair_price','live_price','rated_price'])
old_fields = fallback_refs
v72_refs = len(re.findall(r'edgeiq_v7_2|V7_2|V72', text))
unconditional = False
for field in ['edgeiq_v7_2_preview_probability','edgeiq_v7_2_preview_fair_price','edgeiq_v7_2_preview_display_fair_price']:
    for m in re.finditer(field, text):
        window = text[max(0, m.start()-500):m.start()]
        if 'isV72FeatureOn' not in window:
            unconditional = True
rows = [
    {'check':'helper_functions_exist','value':'YES' if helper_exists else 'NO'},
    {'check':'render_references_helper_functions','value':'YES' if render_refs else 'NO'},
    {'check':'no_unconditional_preview_usage','value':'YES' if not unconditional else 'NO'},
    {'check':'feature_flag_on_condition_exists','value':'YES' if flag_condition else 'NO'},
    {'check':'fallback_fields_still_referenced','value':'YES' if fallback_refs else 'NO'},
    {'check':'old_price_fields_still_exist','value':'YES' if old_fields else 'NO'},
    {'check':'v7_2_refs_count','value':v72_refs},
]
pd.DataFrame(rows).to_csv(OUT,index=False)
if not TSX.exists() or not helper_exists:
    status = 'UI_RENDER_SWITCH_AUDIT_BLOCKED'
elif render_refs and not unconditional and flag_condition and fallback_refs:
    status = 'UI_RENDER_SWITCH_AUDIT_PASS'
else:
    status = 'UI_RENDER_SWITCH_AUDIT_REVIEW_REQUIRED'
metrics = {'built_at':datetime.now(timezone.utc).isoformat(),'helper_functions_exist':'YES' if helper_exists else 'NO','render_references_helper_functions':'YES' if render_refs else 'NO','no_unconditional_edgeiq_v7_2_preview_display_fair_price_usage':'YES' if not unconditional else 'NO','feature_flag_on_condition_exists':'YES' if flag_condition else 'NO','fallback_fields_still_referenced':'YES' if fallback_refs else 'NO','old_price_fields_still_exist':'YES' if old_fields else 'NO','v7_2_refs_count':v72_refs,'status':status}
pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_csv(SUM,index=False)
report=f'''EDGEiQ V7.2 UI RENDER SWITCH AUDIT V1

- Status: {status}
- Helper functions exist: {metrics['helper_functions_exist']}
- Render references helper functions: {metrics['render_references_helper_functions']}
- No unconditional V7.2 preview usage: {metrics['no_unconditional_edgeiq_v7_2_preview_display_fair_price_usage']}
- Feature flag ON condition exists: {metrics['feature_flag_on_condition_exists']}
- Fallback fields still referenced: {metrics['fallback_fields_still_referenced']}
- Old price fields still exist: {metrics['old_price_fields_still_exist']}
- V7.2 refs count: {v72_refs}
'''
REP.write_text(report,encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_string(index=False))
print(report)
