from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import re

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'public' / 'data'
TSX = BASE / 'src' / 'components' / 'RaceIntelligenceScreen.tsx'
BOARD = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
OUT = DATA / 'edgeiq_v7_2_ui_post_wiring_v1.csv'
SUM = DATA / 'edgeiq_v7_2_ui_post_wiring_v1_summary.csv'
REP = DATA / 'edgeiq_v7_2_ui_post_wiring_v1_report.txt'
HELPERS = ['isV72FeatureOn','getV72AwareFairPrice','getV72AwareDisplayFairPrice','getV72AwareProbability','getV72PriceSource']

def read(path): return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False) if path.exists() else pd.DataFrame()
def values(df,col): return ','.join(sorted(df[col].fillna('').astype(str).unique())) if col in df.columns and len(df) else ''

text = TSX.read_text(encoding='utf-8', errors='ignore') if TSX.exists() else ''
board = read(BOARD)
v72_refs = len(re.findall(r'edgeiq_v7_2|V7_2|V72', text))
helpers_exist = all(h in text for h in HELPERS)
flag_check_exists = 'edgeiq_v7_2_feature_flag' in text and '=== "ON"' in text
fallback_refs = all(tok in text for tok in ['fair_price','ui_fair_price','live_price'])
# Exact ON comparison is allowed; assignment or CSV activation is not.
feature_on_hardcoded = bool(re.search(r'edgeiq_v7_2_feature_flag\s*[:=]\s*["\']ON["\']', text))
unconditional_forced = False
for field in ['edgeiq_v7_2_preview_probability','edgeiq_v7_2_preview_fair_price','edgeiq_v7_2_preview_display_fair_price']:
    for m in re.finditer(field, text):
        window = text[max(0, m.start()-500):m.start()]
        if 'isV72FeatureOn' not in window:
            unconditional_forced = True
rows = [
    {'check':'tsx_exists','value':'YES' if TSX.exists() else 'NO'},
    {'check':'v7_2_refs_count','value':v72_refs},
    {'check':'feature_flag_check_exists','value':'YES' if flag_check_exists else 'NO'},
    {'check':'helper_functions_exist','value':'YES' if helpers_exist else 'NO'},
    {'check':'fallback_references_still_exist','value':'YES' if fallback_refs else 'NO'},
    {'check':'no_feature_flag_on_hardcoded','value':'YES' if not feature_on_hardcoded else 'NO'},
    {'check':'no_v7_2_preview_forced_unconditionally','value':'YES' if not unconditional_forced else 'NO'},
    {'check':'live_board_feature_flag_values','value':values(board,'edgeiq_v7_2_feature_flag')},
    {'check':'live_board_production_changed_values','value':values(board,'edgeiq_v7_2_production_changed')},
]
pd.DataFrame(rows).to_csv(OUT, index=False)
if not TSX.exists() or v72_refs == 0:
    status = 'UI_POST_WIRING_AUDIT_BLOCKED'
elif flag_check_exists and helpers_exist and fallback_refs and not feature_on_hardcoded and not unconditional_forced and values(board,'edgeiq_v7_2_feature_flag') == 'OFF' and values(board,'edgeiq_v7_2_production_changed') == 'NO':
    status = 'UI_POST_WIRING_AUDIT_PASS_FLAG_OFF'
else:
    status = 'UI_POST_WIRING_AUDIT_REVIEW_REQUIRED'
metrics = {
    'built_at': datetime.now(timezone.utc).isoformat(),
    'tsx_exists':'YES' if TSX.exists() else 'NO',
    'v7_2_refs_count':v72_refs,
    'feature_flag_check_exists':'YES' if flag_check_exists else 'NO',
    'helper_functions_exist':'YES' if helpers_exist else 'NO',
    'fallback_references_still_exist':'YES' if fallback_refs else 'NO',
    'no_feature_flag_on_hardcoded':'YES' if not feature_on_hardcoded else 'NO',
    'no_v7_2_preview_forced_unconditionally':'YES' if not unconditional_forced else 'NO',
    'live_board_feature_flag_values':values(board,'edgeiq_v7_2_feature_flag'),
    'live_board_production_changed_values':values(board,'edgeiq_v7_2_production_changed'),
    'status':status,
}
pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_csv(SUM, index=False)
report = f'''EDGEiQ V7.2 UI POST WIRING V1

- Status: {status}
- TSX exists: {metrics['tsx_exists']}
- V7.2 refs count: {v72_refs}
- Feature flag check exists: {metrics['feature_flag_check_exists']}
- Helper functions exist: {metrics['helper_functions_exist']}
- Fallback references still exist: {metrics['fallback_references_still_exist']}
- No feature flag ON hardcoded: {metrics['no_feature_flag_on_hardcoded']}
- No V7.2 preview forced unconditionally: {metrics['no_v7_2_preview_forced_unconditionally']}
- Live board feature flag values: {metrics['live_board_feature_flag_values']}
- Live board production changed values: {metrics['live_board_production_changed_values']}
'''
REP.write_text(report, encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in metrics.items()]).to_string(index=False))
print(report)
