from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import re

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'public' / 'data'
LIVE_PREF = [DATA/'edgeiq_live_runner_board_governed_v1.csv', DATA/'edgeiq_live_runner_board_v1.csv']
TERMINAL = DATA/'edgeiq_live_terminal_feed_v1.csv'
OUT = DATA/'edgeiq_current_day_v7_1_source_columns_v1.csv'
SUM = DATA/'edgeiq_current_day_v7_1_source_columns_v1_summary.csv'
REP = DATA/'edgeiq_current_day_v7_1_source_columns_v1_report.txt'

KEYWORDS = ['score','rating','probability','win_pct','rank']
EXACTS = {'rating','rated_price','win_pct','V6_1_RESEARCH_price_rank','race_target_rating_v5_2','projected_spd','runner_score_v2','runner_score_v3','runner_raw_score_v2','runner_raw_score_v3','runner_dna_v6_2_score','confidence_score'}

def read(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False) if path.exists() else pd.DataFrame()

def pick_live():
    for p in LIVE_PREF:
        if p.exists(): return p
    return None

def rel(p):
    return str(p.relative_to(BASE)) if p else 'MISSING'

def role_for(col, s):
    lc = col.lower()
    numeric = pd.to_numeric(s.replace('', pd.NA), errors='coerce')
    n = int(numeric.notna().sum())
    if n == 0: return 'NOT_NUMERIC'
    mx = float(numeric.max()) if n else None
    mn = float(numeric.min()) if n else None
    if 'rank' in lc:
        return 'RANK_INPUT_CANDIDATE'
    if lc in ['win_pct','probability','edgeiq_probability'] or 'probability' in lc or 'win_pct' in lc:
        return 'PROBABILITY_INPUT_CANDIDATE'
    if 'rating' in lc or 'score' in lc:
        return 'RATING_INPUT_CANDIDATE'
    return 'NUMERIC_CONTEXT'

def priority(row):
    col = row['column'].lower()
    role = row['recommended_role']
    n = int(row['numeric_rows'])
    if n <= 0: return -1
    if col == 'total_rating_points': return 100
    if col == 'projected_rating_v6_1_research': return 95
    if col == 'projected_rating_v5_2': return 90
    if col == 'dfs_form_rating': return 82
    if col == 'tech_form_rating': return 80
    if role == 'RATING_INPUT_CANDIDATE': return 70
    if col == 'win_pct': return 60
    if role == 'PROBABILITY_INPUT_CANDIDATE': return 55
    if role == 'RANK_INPUT_CANDIDATE': return 40
    return 1

live_path = pick_live()
live = read(live_path) if live_path else pd.DataFrame()
term = read(TERMINAL)
rows=[]
for file_label, df in [(rel(live_path), live), (rel(TERMINAL), term)]:
    for col in df.columns:
        lc = col.lower()
        if col in EXACTS or any(k in lc for k in KEYWORDS):
            numeric = pd.to_numeric(df[col].replace('', pd.NA), errors='coerce')
            non_null = int((df[col].astype(str).str.strip()!='').sum())
            nums = numeric.dropna()
            role = role_for(col, df[col])
            rows.append({
                'file': file_label,
                'column': col,
                'numeric_rows': int(nums.shape[0]),
                'non_null_rows': non_null,
                'min': '' if nums.empty else float(nums.min()),
                'max': '' if nums.empty else float(nums.max()),
                'mean': '' if nums.empty else float(nums.mean()),
                'unique_values': int(df[col].nunique(dropna=False)),
                'recommended_role': role,
            })

detail = pd.DataFrame(rows)
if detail.empty:
    rec_col = ''
    status = 'SOURCE_SCHEMA_BLOCKED_NO_RATING_INPUT'
    counts = {'rating':0,'prob':0,'rank':0}
else:
    live_detail = detail[detail['file'] == rel(live_path)].copy()
    live_detail['priority'] = live_detail.apply(priority, axis=1) if not live_detail.empty else []
    viable = live_detail[live_detail['priority'] > 0].sort_values(['priority','numeric_rows'], ascending=[False,False])
    rec_col = '' if viable.empty else str(viable.iloc[0]['column'])
    status = 'SOURCE_COLUMNS_AUDITED_REVIEW_REQUIRED' if rec_col else 'SOURCE_SCHEMA_BLOCKED_NO_RATING_INPUT'
    counts = {
        'rating': int((live_detail['recommended_role']=='RATING_INPUT_CANDIDATE').sum()),
        'prob': int((live_detail['recommended_role']=='PROBABILITY_INPUT_CANDIDATE').sum()),
        'rank': int((live_detail['recommended_role']=='RANK_INPUT_CANDIDATE').sum()),
    }
    detail = detail.drop(columns=['priority'], errors='ignore')

detail.to_csv(OUT, index=False)
summary = pd.DataFrame([
    {'metric':'built_at','value':datetime.now(timezone.utc).isoformat()},
    {'metric':'live_source_file_used','value':rel(live_path)},
    {'metric':'live_rows','value':len(live)},
    {'metric':'terminal_rows','value':len(term)},
    {'metric':'rating_input_candidates','value':counts['rating'] if detail.shape[0] else 0},
    {'metric':'probability_input_candidates','value':counts['prob'] if detail.shape[0] else 0},
    {'metric':'rank_input_candidates','value':counts['rank'] if detail.shape[0] else 0},
    {'metric':'recommended_primary_input_column','value':rec_col},
    {'metric':'status','value':status},
    {'metric':'production_changed','value':'NO'},
])
summary.to_csv(SUM, index=False)
report = f'''EDGEiQ CURRENT-DAY V7.1 SOURCE COLUMNS V1

- Live source file used: {rel(live_path)}
- Live rows: {len(live)}
- Terminal rows: {len(term)}
- Rating input candidates: {counts['rating'] if detail.shape[0] else 0}
- Probability input candidates: {counts['prob'] if detail.shape[0] else 0}
- Rank input candidates: {counts['rank'] if detail.shape[0] else 0}
- Recommended primary input column: {rec_col or 'NONE'}
- Status: {status}
- Production changed: NO

Recommended input explanation:
The preferred current-day driver is selected from numeric live-board rating/score/probability/rank fields. Ratings and scores are preferred over existing displayed prices because V7 should produce calibrated probabilities first, with V7.1 remaining a display layer.

No live files were modified.
'''
REP.write_text(report, encoding='utf-8')
print(summary.to_string(index=False))
print(report)
