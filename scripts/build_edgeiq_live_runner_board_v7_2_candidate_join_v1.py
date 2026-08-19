from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import re

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'public' / 'data'
LIVE = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
CAND = DATA / 'edgeiq_current_day_v7_2_hybrid_candidate_v1.csv'
OUT = DATA / 'edgeiq_live_runner_board_v7_2_candidate.csv'
AUD = DATA / 'edgeiq_live_runner_board_v7_2_candidate_join_audit_v1.csv'
SUM = DATA / 'edgeiq_live_runner_board_v7_2_candidate_join_summary_v1.csv'
REP = DATA / 'edgeiq_live_runner_board_v7_2_candidate_join_report_v1.txt'
APPEND = ['edgeiq_probability_v7_2','edgeiq_fair_price_v7_2','edgeiq_display_fair_price_v7_2','probability_source_v7_2','edgeiq_price_engine_version_v7_2','edgeiq_display_price_engine_version_v7_2','edgeiq_v7_2_feature_flag','edgeiq_v7_2_live_wired_flag','edgeiq_v7_2_production_changed','edgeiq_v7_2_join_key','edgeiq_v7_2_built_at']

def read(p): return pd.read_csv(p, dtype=str, keep_default_na=False, low_memory=False) if p.exists() else pd.DataFrame()
def norm_date(v):
    raw='' if pd.isna(v) else str(v).strip(); dt=pd.to_datetime(raw, errors='coerce')
    return raw.upper() if pd.isna(dt) else dt.strftime('%Y-%m-%d')
def norm_track(v): return re.sub(r'\s+',' ',('' if pd.isna(v) else str(v)).upper().strip())
def norm_race(v):
    raw='' if pd.isna(v) else str(v).upper().strip(); m=re.search(r'\d+', raw)
    return str(int(m.group(0))) if m else raw
def norm_horse(v):
    raw=('' if pd.isna(v) else str(v)).upper().strip(); raw=re.sub(r'[^A-Z0-9\s]','', raw)
    return re.sub(r'\s+',' ', raw).strip()
def key(df): return df['race_date'].map(norm_date)+'|'+df['track'].map(norm_track)+'|'+df['race_no'].map(norm_race)+'|'+df['horse'].map(norm_horse)
def metric_df(m): return pd.DataFrame([{'metric':k,'value':v} for k,v in m.items()])

built_at = datetime.now(timezone.utc).isoformat()
live = read(LIVE); cand = read(CAND)
blocked = live.empty or cand.empty or 'edgeiq_v7_2_join_key' not in cand.columns
if blocked:
    out = live.copy()
    for c in APPEND:
        if c not in out.columns: out[c] = ''
    out['edgeiq_v7_2_join_status'] = 'BLOCKED_SCHEMA_MISSING'
    status = 'BLOCKED_SCHEMA_MISSING'
else:
    out = live.copy(); out['_join_key'] = key(out)
    cols = ['edgeiq_v7_2_join_key'] + [c for c in APPEND if c in cand.columns and c != 'edgeiq_v7_2_join_key']
    cmap = cand[cols].drop_duplicates('edgeiq_v7_2_join_key', keep='first')
    out = out.merge(cmap, left_on='_join_key', right_on='edgeiq_v7_2_join_key', how='left')
    for c in APPEND:
        if c not in out.columns: out[c] = ''
        else: out[c] = out[c].fillna('')
    matched = out['edgeiq_probability_v7_2'].fillna('').astype(str).str.strip().ne('') | out['edgeiq_display_fair_price_v7_2'].fillna('').astype(str).str.strip().ne('')
    out['edgeiq_v7_2_join_status'] = matched.map(lambda x: 'MATCHED' if x else 'UNMATCHED')
    out['edgeiq_v7_2_feature_flag'] = out['edgeiq_v7_2_feature_flag'].replace('', 'OFF')
    out['edgeiq_v7_2_live_wired_flag'] = out['edgeiq_v7_2_live_wired_flag'].replace('', 'NO')
    out['edgeiq_v7_2_production_changed'] = out['edgeiq_v7_2_production_changed'].replace('', 'NO')
    out['edgeiq_v7_2_join_key'] = out['_join_key']
    out = out.drop(columns=['_join_key'], errors='ignore')
    matched_rows = int(matched.sum()); match_rate = round(matched_rows / len(out) * 100, 4) if len(out) else 0
    if len(out) != len(live): status = 'V7_2_LIVE_BOARD_JOIN_BLOCKED_ROW_COUNT_CHANGED'
    elif match_rate >= 99: status = 'V7_2_LIVE_BOARD_JOIN_READY_FOR_REVIEW'
    else: status = 'V7_2_LIVE_BOARD_JOIN_BUILT_WITH_UNMATCHED_REVIEW_REQUIRED'

out.to_csv(OUT, index=False)
matched_rows = int((out.get('edgeiq_v7_2_join_status', pd.Series(dtype=str)) == 'MATCHED').sum()) if len(out) else 0
unmatched = len(out) - matched_rows
match_rate = round(matched_rows / len(out) * 100, 4) if len(out) else 0
audit = pd.DataFrame({'join_key': out.get('edgeiq_v7_2_join_key', pd.Series(['']*len(out))), 'track': out['track'] if 'track' in out.columns else '', 'race_no': out['race_no'] if 'race_no' in out.columns else '', 'horse': out['horse'] if 'horse' in out.columns else '', 'join_status': out.get('edgeiq_v7_2_join_status', pd.Series(['']*len(out))), 'reason': out.get('edgeiq_v7_2_join_status', pd.Series(['']*len(out))).map(lambda x: 'JOINED_ON_CURRENT_DAY_KEY' if x == 'MATCHED' else 'NO_V7_2_CURRENT_DAY_CANDIDATE_MATCH')})
audit.to_csv(AUD, index=False)
metrics = {'built_at': built_at, 'live_source_file_used': str(LIVE.relative_to(BASE)), 'candidate_source_file_used': str(CAND.relative_to(BASE)), 'live_rows': len(live), 'candidate_rows': len(cand), 'output_rows': len(out), 'matched_rows': matched_rows, 'unmatched_rows': unmatched, 'match_rate_pct': match_rate, 'feature_flag_values': ','.join(sorted(out.get('edgeiq_v7_2_feature_flag', pd.Series([''])).astype(str).unique())) if len(out) else '', 'live_wired_values': ','.join(sorted(out.get('edgeiq_v7_2_live_wired_flag', pd.Series([''])).astype(str).unique())) if len(out) else '', 'production_changed_values': ','.join(sorted(out.get('edgeiq_v7_2_production_changed', pd.Series([''])).astype(str).unique())) if len(out) else '', 'duplicate_live_keys': int(key(live).duplicated(keep=False).sum()) if not live.empty else 0, 'duplicate_candidate_keys': int(cand['edgeiq_v7_2_join_key'].duplicated(keep=False).sum()) if 'edgeiq_v7_2_join_key' in cand.columns else 0, 'status': status}
metric_df(metrics).to_csv(SUM, index=False)
report = f'''EDGEiQ LIVE RUNNER BOARD V7.2 CANDIDATE JOIN V1

- Candidate only.
- Append-only live-board candidate.
- No live wiring.
- No production change.
- Feature flag OFF.
- Existing live board columns preserved.
- Live rows: {metrics['live_rows']}
- Candidate rows: {metrics['candidate_rows']}
- Output rows: {metrics['output_rows']}
- Matched rows: {matched_rows}
- Unmatched rows: {unmatched}
- Match rate pct: {match_rate}
- Status: {status}

Review required before any controlled feature-flag wiring.
'''
REP.write_text(report, encoding='utf-8')
print(metric_df(metrics).to_string(index=False))
print(report)
