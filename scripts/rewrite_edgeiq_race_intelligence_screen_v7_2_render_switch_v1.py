from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'public' / 'data'
TSX = BASE / 'src' / 'components' / 'RaceIntelligenceScreen.tsx'
IMPACT_SUM = DATA / 'edgeiq_v7_2_feature_flag_on_impact_v1_summary.csv'
CP_SUM = DATA / 'edgeiq_ui_checkpoint_before_v7_2_render_switch_v1_summary.csv'
OUT = DATA / 'edgeiq_ui_v7_2_render_switch_v1.csv'
SUM = DATA / 'edgeiq_ui_v7_2_render_switch_v1_summary.csv'
REP = DATA / 'edgeiq_ui_v7_2_render_switch_v1_report.txt'
OLD_FAIR = '''function fairPrice(row: Row, bet?: Row): number | null {
  return firstNum(row, ["display_fair_price", "fair_price", "rated_price", "ui_fair_price", "edgeiq_price"]) ??
    firstNum(bet, ["bet_quality_fair_price_used_v1_1", "fair_price"]);
}
'''
NEW_FAIR = '''function fairPrice(row: Row, bet?: Row): number | null {
  return getV72AwareDisplayFairPrice(row) ??
    firstNum(bet, ["bet_quality_fair_price_used_v1_1", "fair_price"]);
}
'''
OLD_WIN = '''function winPct(row: Row, bet?: Row): number | null {
  const p = firstNum(row, ["v3_probability", "edgeiq_probability", "rated_probability", "win_probability"]) ??
    firstNum(bet, ["v3_probability"]);

  if (p !== null && p > 0) return p > 1 ? p : p * 100;

  const fair = fairPrice(row, bet);
  return fair && fair > 0 ? 100 / fair : null;
}
'''
NEW_WIN = '''function winPct(row: Row, bet?: Row): number | null {
  const p = getV72AwareProbability(row) ??
    firstNum(row, ["v3_probability", "edgeiq_probability", "rated_probability", "win_probability"]) ??
    firstNum(bet, ["v3_probability"]);

  if (p !== null && p > 0) return p > 1 ? p : p * 100;

  const fair = fairPrice(row, bet);
  return fair && fair > 0 ? 100 / fair : null;
}
'''

def metrics(path):
    if not path.exists(): return {}
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    return dict(zip(df['metric'], df['value'])) if {'metric','value'}.issubset(df.columns) else {}

built_at = datetime.now(timezone.utc).isoformat()
impact = metrics(IMPACT_SUM); cp = metrics(CP_SUM)
checkpoint_ok = cp.get('status') == 'UI_RENDER_SWITCH_CHECKPOINT_CREATED'
impact_ok = impact.get('status') == 'FEATURE_FLAG_ON_IMPACT_PASS_REVIEW_REQUIRED'
text_before = TSX.read_text(encoding='utf-8') if TSX.exists() else ''
modified = 'NO'; status = 'UI_V7_2_RENDER_SWITCH_BLOCKED_SAFE_NO_CHANGE'; reason = ''
text_after = text_before
if not TSX.exists():
    reason = 'TSX missing'
elif not checkpoint_ok:
    reason = 'Render-switch checkpoint missing'
elif not impact_ok:
    reason = 'Impact audit not pass/review-required'
elif 'function isV72FeatureOn' not in text_before:
    reason = 'V7.2 helpers missing'
elif OLD_FAIR not in text_before or OLD_WIN not in text_before:
    reason = 'Safe render switch insertion pattern not found'
else:
    text_after = text_before.replace(OLD_FAIR, NEW_FAIR, 1).replace(OLD_WIN, NEW_WIN, 1)
    TSX.write_text(text_after, encoding='utf-8')
    modified = 'YES'
    status = 'UI_V7_2_RENDER_SWITCH_COMPLETE_FEATURE_FLAG_CONTROLLED'
    reason = 'fairPrice and winPct routed through V7.2-aware helpers with fallback preserved'
row = {'built_at': built_at, 'tsx_modified': modified, 'render_references_helper_functions': 'YES' if all(x in text_after for x in ['getV72AwareDisplayFairPrice(row)', 'getV72AwareProbability(row)']) else 'NO', 'fallback_logic_preserved': 'YES' if all(x in text_after for x in ['fair_price','ui_fair_price','live_price','firstNum(bet']) else 'NO', 'feature_flag_controlled': 'YES' if 'edgeiq_v7_2_feature_flag' in text_after and '=== "ON"' in text_after else 'NO', 'reason': reason, 'status': status}
pd.DataFrame([row]).to_csv(OUT, index=False)
pd.DataFrame([{'metric':k,'value':v} for k,v in row.items()]).to_csv(SUM, index=False)
report = f'''EDGEiQ UI V7.2 RENDER SWITCH V1

- TSX modified: {modified}
- Render references helper functions: {row['render_references_helper_functions']}
- Fallback logic preserved: {row['fallback_logic_preserved']}
- Feature flag controlled: {row['feature_flag_controlled']}
- Status: {status}
- Reason: {reason}

The switch routes central price/probability rendering through V7.2-aware helpers. V7.2 values are still only used when edgeiq_v7_2_feature_flag is exactly ON; otherwise existing fallback fields remain active.
'''
REP.write_text(report, encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in row.items()]).to_string(index=False))
print(report)
