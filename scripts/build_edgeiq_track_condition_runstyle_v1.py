from __future__ import annotations

from pathlib import Path

import pandas as pd

from edgeiq_bias_common_v1 import aggregate_bias_table, load_results_with_run_style, wet_flag, write_csv

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
OUT_MAIN = DATA / 'edgeiq_track_condition_runstyle_v1.csv'
OUT_SUMMARY = DATA / 'edgeiq_track_condition_runstyle_summary_v1.csv'


def main():
    results = load_results_with_run_style()
    matrix = aggregate_bias_table(
        results,
        group_cols=['track_norm', 'condition_group_v1', 'run_style_v1'],
        context_cols=['track_norm', 'condition_group_v1'],
        score_col='track_condition_runstyle_score_v1',
        band_col='track_condition_runstyle_band_v1',
    )
    matrix['wet_condition_flag_v1'] = matrix['condition_group_v1'].map(wet_flag)
    matrix['ranking_eligible_v1'] = (
        matrix['starts'] >= 100
    ) & matrix['condition_group_v1'].isin(['GOOD', 'SOFT', 'HEAVY']) & matrix['run_style_v1'].ne('UNKNOWN')
    matrix = matrix.sort_values(['track_condition_runstyle_score_v1', 'starts'], ascending=[False, False]).reset_index(drop=True)
    write_csv(matrix, OUT_MAIN.name)

    best = matrix[matrix['ranking_eligible_v1']].head(1)
    worst = matrix[matrix['ranking_eligible_v1']].sort_values(['track_condition_runstyle_score_v1', 'starts'], ascending=[True, False]).head(1)
    summary_rows = [
        {'metric': 'status', 'value': 'COMPLETE'},
        {'metric': 'rows', 'value': int(len(matrix))},
        {'metric': 'eligible_rows', 'value': int(matrix['ranking_eligible_v1'].sum())},
        {'metric': 'best_combo', 'value': f"{best['track_display_v1'].iloc[0]} | {best['condition_group_v1'].iloc[0]} | {best['run_style_v1'].iloc[0]}" if not best.empty else ''},
        {'metric': 'best_score_v1', 'value': round(float(best['track_condition_runstyle_score_v1'].iloc[0]), 3) if not best.empty else ''},
        {'metric': 'worst_combo', 'value': f"{worst['track_display_v1'].iloc[0]} | {worst['condition_group_v1'].iloc[0]} | {worst['run_style_v1'].iloc[0]}" if not worst.empty else ''},
        {'metric': 'worst_score_v1', 'value': round(float(worst['track_condition_runstyle_score_v1'].iloc[0]), 3) if not worst.empty else ''},
    ]
    write_csv(pd.DataFrame(summary_rows), OUT_SUMMARY.name)

    print('[TRACK_CONDITION_RUNSTYLE_V1] COMPLETE')
    print(f'rows={len(matrix)}')
    print(f'eligible_rows={int(matrix["ranking_eligible_v1"].sum())}')
    print(f'wrote={OUT_MAIN}')
    print(f'wrote={OUT_SUMMARY}')


if __name__ == '__main__':
    main()
