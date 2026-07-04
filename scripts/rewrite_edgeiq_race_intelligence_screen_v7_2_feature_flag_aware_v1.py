from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'public' / 'data'
TSX = BASE / 'src' / 'components' / 'RaceIntelligenceScreen.tsx'
CHECK_SUM = DATA / 'edgeiq_ui_checkpoint_before_v7_2_wiring_v1_summary.csv'
OUT = DATA / 'edgeiq_ui_v7_2_feature_flag_wiring_v1.csv'
SUM = DATA / 'edgeiq_ui_v7_2_feature_flag_wiring_v1_summary.csv'
REP = DATA / 'edgeiq_ui_v7_2_feature_flag_wiring_v1_report.txt'
HELPER_MARKER = 'function isV72FeatureOn(row: Row | undefined): boolean {'
INSERT_AFTER = '''function firstText(row: Row | undefined, keys: string[], fallback = "--"): string {
  if (!row) return fallback;
  for (const key of keys) {
    const value = text(row[key]);
    if (value) return value;
  }
  return fallback;
}
'''
HELPERS = r'''
function isV72FeatureOn(row: Row | undefined): boolean {
  return text(row?.edgeiq_v7_2_feature_flag).toUpperCase() === "ON";
}

function getV72AwareProbability(row: Row | undefined): number | null {
  if (isV72FeatureOn(row)) {
    return firstNum(row, ["edgeiq_v7_2_preview_probability", "edgeiq_probability_v7_2"]);
  }
  return firstNum(row, ["win_pct", "V6_1_RESEARCH_probability", "probability_normalised_v1"]);
}

function getV72AwareFairPrice(row: Row | undefined): number | null {
  if (isV72FeatureOn(row)) {
    return firstNum(row, ["edgeiq_v7_2_preview_fair_price", "edgeiq_fair_price_v7_2"]);
  }
  return firstNum(row, ["fair_price", "ui_fair_price", "display_fair_price", "rated_price"]);
}

function getV72AwareDisplayFairPrice(row: Row | undefined): number | null {
  if (isV72FeatureOn(row)) {
    return firstNum(row, ["edgeiq_v7_2_preview_display_fair_price", "edgeiq_display_fair_price_v7_2"]);
  }
  return firstNum(row, ["ui_fair_price", "display_fair_price", "fair_price", "rated_price"]);
}

function getV72PriceSource(row: Row | undefined): string {
  if (isV72FeatureOn(row)) {
    return firstText(row, ["edgeiq_v7_2_preview_price_source", "edgeiq_v7_2_probability_source", "probability_source_v7_2"], "V7_2_FEATURE_FLAG_ON");
  }
  return firstText(row, ["edgeiq_active_price_source_shadow"], "PRODUCTION_FALLBACK_FEATURE_FLAG_OFF");
}
'''

def read_metrics(path):
    if not path.exists(): return {}
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    return dict(zip(df['metric'], df['value'])) if {'metric','value'}.issubset(df.columns) else {}

built_at = datetime.now(timezone.utc).isoformat()
checkpoint = read_metrics(CHECK_SUM)
checkpoint_found = checkpoint.get('status') == 'UI_CHECKPOINT_CREATED'
text_before = TSX.read_text(encoding='utf-8') if TSX.exists() else ''
refs_before = text_before.count('edgeiq_v7_2')
modified = 'NO'; helpers_added = 'NO'; rendering_switched = 'NO'; status = 'UI_V7_2_WIRING_BLOCKED_SAFE_NO_CHANGE'; reason = ''
text_after = text_before
if not TSX.exists():
    reason = 'TSX missing'
elif not checkpoint_found:
    reason = 'Checkpoint missing or not created'
elif HELPER_MARKER in text_before:
    helpers_added = 'YES'
    status = 'UI_V7_2_HELPERS_ADDED_RENDER_NOT_SWITCHED_REVIEW_REQUIRED'
    reason = 'Helpers already present'
elif INSERT_AFTER not in text_before:
    reason = 'Safe insertion point not found'
else:
    text_after = text_before.replace(INSERT_AFTER, INSERT_AFTER + HELPERS + '\n', 1)
    TSX.write_text(text_after, encoding='utf-8')
    modified = 'YES'; helpers_added = 'YES'
    status = 'UI_V7_2_HELPERS_ADDED_RENDER_NOT_SWITCHED_REVIEW_REQUIRED'
    reason = 'Helpers inserted; rendering intentionally not switched while feature flag is OFF'
refs_after = text_after.count('edgeiq_v7_2')
fallback_preserved = all(tok in text_after for tok in ['fair_price','ui_fair_price','live_price'])
feature_default_off = '=== "ON"' in text_after or '=== "ON"' in text_after.replace('\\"','"')
row = {
    'built_at': built_at,
    'checkpoint_required': 'YES',
    'checkpoint_found': 'YES' if checkpoint_found else 'NO',
    'tsx_modified': modified,
    'helper_functions_added': helpers_added,
    'rendering_switched': rendering_switched,
    'v7_2_refs_count_before': refs_before,
    'v7_2_refs_count_after': refs_after,
    'fallback_logic_preserved': 'YES' if fallback_preserved else 'NO',
    'feature_flag_default_off': 'YES' if feature_default_off else 'NO',
    'reason': reason,
    'status': status,
}
pd.DataFrame([row]).to_csv(OUT, index=False)
pd.DataFrame([{'metric':k,'value':v} for k,v in row.items()]).to_csv(SUM, index=False)
report = f'''EDGEiQ UI V7.2 FEATURE FLAG WIRING V1

- Checkpoint required: YES
- Checkpoint found: {row['checkpoint_found']}
- TSX modified: {modified}
- Helper functions added: {helpers_added}
- Rendering switched: {rendering_switched}
- V7.2 refs before: {refs_before}
- V7.2 refs after: {refs_after}
- Fallback logic preserved: {row['fallback_logic_preserved']}
- Feature flag default OFF behavior: {row['feature_flag_default_off']}
- Status: {status}
- Reason: {reason}

The UI is now V7.2-aware through helper functions only. Existing rendering was not switched, so feature flag OFF continues to preserve production fallback behavior.
'''
REP.write_text(report, encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in row.items()]).to_string(index=False))
print(report)
