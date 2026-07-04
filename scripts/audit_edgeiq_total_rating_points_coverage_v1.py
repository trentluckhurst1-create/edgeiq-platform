from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import re

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'public' / 'data'
INPUT = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
OUT = DATA / 'edgeiq_total_rating_points_coverage_v1.csv'
SUM = DATA / 'edgeiq_total_rating_points_coverage_v1_summary.csv'
REP = DATA / 'edgeiq_total_rating_points_coverage_v1_report.txt'

TARGET_REPLACEMENTS = [
    'runner_score','runner_score_v2','runner_score_v3','governed_projection_rating_v6','race_target_rating_v5_2',
    'confidence_adjusted_rating_v6','strength_adjusted_rating_v6','projected_rating_v5_2','runner_dna_v6_2_score','win_pct'
]
BASE_COLS = ['race_date','track','race_no','horse','barrier','jockey','trainer']

def numeric_like_columns(df):
    cols = []
    for col in df.columns:
        lc = col.lower()
        if any(k in lc for k in ['score','rating','probability','win_pct','rank']):
            vals = pd.to_numeric(df[col].replace('', pd.NA), errors='coerce')
            if vals.notna().sum() > 0 or any(k in lc for k in ['score','rating','probability','win_pct','rank']):
                cols.append(col)
    return cols

def summarize_col(df, col):
    if col not in df.columns:
        return {'column': col, 'exists': 'NO', 'numeric_rows': 0, 'non_blank_rows': 0, 'zero_rows': 0, 'min': '', 'max': '', 'mean': '', 'candidate_role': 'MISSING'}
    raw = df[col].astype(str).str.strip()
    nums = pd.to_numeric(df[col].replace('', pd.NA), errors='coerce')
    n = int(nums.notna().sum())
    role = 'REPLACEMENT_CANDIDATE' if n > 0 else 'NOT_USABLE'
    return {'column': col, 'exists': 'YES', 'numeric_rows': n, 'non_blank_rows': int(raw.ne('').sum()), 'zero_rows': int((nums == 0).sum()), 'min': '' if n == 0 else float(nums.min()), 'max': '' if n == 0 else float(nums.max()), 'mean': '' if n == 0 else float(nums.mean()), 'candidate_role': role}

built_at = datetime.now(timezone.utc).isoformat()
if not INPUT.exists():
    detail = pd.DataFrame([{'status':'BLOCKED_INPUT_MISSING','reason':str(INPUT)}])
    summary_metrics = {'built_at': built_at, 'rows': 0, 'races': 0, 'rows_with_total_rating_points': 0, 'rows_without_total_rating_points': 0, 'coverage_pct': 0, 'status': 'BLOCKED_INPUT_MISSING', 'production_changed': 'NO'}
else:
    df = pd.read_csv(INPUT, dtype=str, keep_default_na=False, low_memory=False)
    trp = pd.to_numeric(df.get('total_rating_points', pd.Series(['']*len(df))).replace('', pd.NA), errors='coerce')
    with_trp = trp.notna() & (df.get('total_rating_points', pd.Series(['']*len(df))).astype(str).str.strip() != '')
    missing_mask = ~with_trp
    score_cols = numeric_like_columns(df)
    missing_cols = [c for c in BASE_COLS if c in df.columns] + score_cols
    detail = df.loc[missing_mask, missing_cols].copy()
    detail.insert(0, 'missing_reason', df.get('total_rating_points', pd.Series(['']*len(df))).astype(str).map(lambda x: 'BLANK' if x.strip()=='' else 'ZERO' if pd.to_numeric(pd.Series([x]), errors='coerce').iloc[0] == 0 else 'NON_NUMERIC'))
    detail.to_csv(OUT, index=False)
    race_key = df.get('race_date','').astype(str)+'|'+df.get('track','').astype(str)+'|'+df.get('race_no','').astype(str)
    rows = len(df); with_count = int(with_trp.sum()); without_count = int(missing_mask.sum())
    coverage = round(with_count / rows * 100, 4) if rows else 0
    replacement_stats = [summarize_col(df.loc[missing_mask].copy(), c) for c in TARGET_REPLACEMENTS]
    repl_df = pd.DataFrame(replacement_stats)
    usable = repl_df[(repl_df['exists']=='YES') & (repl_df['numeric_rows']>0)].sort_values('numeric_rows', ascending=False)
    top_replacements = '; '.join([f"{r.column}:{r.numeric_rows}" for r in usable.itertuples(index=False)]) if not usable.empty else 'NONE'
    summary_metrics = {'built_at': built_at, 'input_file': str(INPUT.relative_to(BASE)), 'rows': rows, 'races': int(race_key.nunique()), 'rows_with_total_rating_points': with_count, 'rows_without_total_rating_points': without_count, 'coverage_pct': coverage, 'top_candidate_replacement_columns': top_replacements, 'status': 'TOTAL_RATING_POINTS_COVERAGE_AUDITED', 'production_changed': 'NO'}
    summary = pd.DataFrame([{'metric':k,'value':v} for k,v in summary_metrics.items()])
    summary.to_csv(SUM, index=False)
    report = f'''EDGEiQ TOTAL RATING POINTS COVERAGE V1

- Input: {INPUT.relative_to(BASE)}
- Rows: {rows}
- Races: {int(race_key.nunique())}
- Rows with total_rating_points: {with_count}
- Rows without total_rating_points: {without_count}
- Coverage pct: {coverage}
- Top candidate replacement columns on missing rows: {top_replacements}
- Status: TOTAL_RATING_POINTS_COVERAGE_AUDITED
- Production changed: NO

Purpose answers:
1. total_rating_points is missing/blank for {without_count} rows.
2. Missing-row detail is written with available score/rating/probability/rank columns.
3. Replacement candidates are ranked by numeric coverage on the missing rows.
4. No live files were modified.
'''
    REP.write_text(report, encoding='utf-8')
    print(summary.to_string(index=False))
    print(report)
    raise SystemExit

detail.to_csv(OUT, index=False)
summary = pd.DataFrame([{'metric':k,'value':v} for k,v in summary_metrics.items()])
summary.to_csv(SUM, index=False)
REP.write_text('EDGEiQ TOTAL RATING POINTS COVERAGE V1\n\nBlocked: input missing.\nProduction changed: NO\n', encoding='utf-8')
print(summary.to_string(index=False))
print(REP.read_text(encoding='utf-8'))
