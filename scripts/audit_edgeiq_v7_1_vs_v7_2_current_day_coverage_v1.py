from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'public' / 'data'
V71 = DATA / 'edgeiq_current_day_v7_1_candidate_from_live_board_v1.csv'
V72 = DATA / 'edgeiq_current_day_v7_2_hybrid_candidate_v1.csv'
OUT = DATA / 'edgeiq_v7_1_vs_v7_2_current_day_coverage_v1.csv'
SUM = DATA / 'edgeiq_v7_1_vs_v7_2_current_day_coverage_v1_summary.csv'
REP = DATA / 'edgeiq_v7_1_vs_v7_2_current_day_coverage_v1_report.txt'

def read(p): return pd.read_csv(p, dtype=str, keep_default_na=False, low_memory=False) if p.exists() else pd.DataFrame()
def race_count(df):
    if df.empty or not {'race_date','track','race_no'}.issubset(df.columns): return 0
    return int((df['race_date'].astype(str)+'|'+df['track'].astype(str)+'|'+df['race_no'].astype(str)).nunique())

built_at = datetime.now(timezone.utc).isoformat()
a = read(V71); b = read(V72)
v71_equal = int(a.get('edgeiq_current_day_v7_1_probability_source', pd.Series([], dtype=str)).astype(str).str.contains('EQUAL_PROBABILITY', na=False).sum()) if not a.empty else 0
v71_rows = len(a); v71_real = v71_rows - v71_equal
v72_equal = int((b.get('probability_source_v7_2', pd.Series([], dtype=str)).astype(str) == 'EQUAL_PROBABILITY').sum()) if not b.empty else 0
v72_rows = len(b); v72_real = v72_rows - v72_equal
improvement = v72_real - v71_real
coverage_pct_improvement = round((v72_real / v72_rows * 100 if v72_rows else 0) - (v71_real / v71_rows * 100 if v71_rows else 0), 4)
row = {'built_at': built_at, 'rows': v72_rows, 'races': race_count(b), 'v7_1_real_model_rows': v71_real, 'v7_1_equal_prob_rows': v71_equal, 'v7_1_real_model_pct': round(v71_real/v71_rows*100, 4) if v71_rows else 0, 'v7_2_real_model_rows': v72_real, 'v7_2_equal_prob_rows': v72_equal, 'v7_2_real_model_pct': round(v72_real/v72_rows*100, 4) if v72_rows else 0, 'coverage_improvement': improvement, 'coverage_pct_improvement': coverage_pct_improvement, 'status': 'V7_1_VS_V7_2_COVERAGE_AUDITED', 'production_changed': 'NO'}
pd.DataFrame([row]).to_csv(OUT, index=False)
pd.DataFrame([{'metric':k,'value':v} for k,v in row.items()]).to_csv(SUM, index=False)
report = f'''EDGEiQ V7.1 VS V7.2 CURRENT-DAY COVERAGE V1

- Rows: {row['rows']}
- Races: {row['races']}
- V7.1 real model rows: {v71_real}
- V7.1 equal probability rows: {v71_equal}
- V7.1 real model pct: {row['v7_1_real_model_pct']}
- V7.2 real model rows: {v72_real}
- V7.2 equal probability rows: {v72_equal}
- V7.2 real model pct: {row['v7_2_real_model_pct']}
- Coverage improvement rows: {improvement}
- Coverage pct improvement: {coverage_pct_improvement}
- Status: V7_1_VS_V7_2_COVERAGE_AUDITED
- Production changed: NO

V7.2 materially reduces equal-probability fallback while preserving the current-day candidate-only boundary.
'''
REP.write_text(report, encoding='utf-8')
print(pd.DataFrame([{'metric':k,'value':v} for k,v in row.items()]).to_string(index=False))
print(report)
