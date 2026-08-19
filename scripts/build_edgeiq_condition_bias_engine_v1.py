from __future__ import annotations

from pathlib import Path

import pandas as pd

from edgeiq_bias_common_v1 import aggregate_bias_table, load_results_with_run_style, wet_flag, write_csv

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
OUT_MAIN = DATA / 'edgeiq_condition_bias_v1.csv'
OUT_BY_TRACK = DATA / 'edgeiq_condition_bias_by_track_v1.csv'
OUT_SUMMARY = DATA / 'edgeiq_condition_bias_summary_v1.csv'


def main():
    results = load_results_with_run_style()
    by_track = aggregate_bias_table(
        results,
        group_cols=['track_norm', 'condition_group_v1', 'run_style_v1'],
        context_cols=['track_norm', 'condition_group_v1'],
        score_col='condition_bias_score_v1',
        band_col='condition_bias_band_v1',
    ).sort_values(['condition_bias_score_v1', 'starts'], ascending=[False, False]).reset_index(drop=True)
    by_track['wet_condition_flag_v1'] = by_track['condition_group_v1'].map(wet_flag)

    row_level = results.merge(
        by_track[
            [
                'track_norm',
                'condition_group_v1',
                'run_style_v1',
                'track_display_v1',
                'starts',
                'wins',
                'places',
                'win_pct',
                'place_pct',
                'context_win_pct',
                'context_place_pct',
                'condition_bias_score_v1',
                'condition_bias_band_v1',
            ]
        ].rename(
            columns={
                'starts': 'condition_context_starts_v1',
                'wins': 'condition_context_wins_v1',
                'places': 'condition_context_places_v1',
                'win_pct': 'condition_run_style_win_pct_v1',
                'place_pct': 'condition_run_style_place_pct_v1',
            }
        ),
        on=['track_norm', 'condition_group_v1', 'run_style_v1'],
        how='left',
    )
    write_csv(row_level, OUT_MAIN.name)
    write_csv(by_track, OUT_BY_TRACK.name)

    wet = by_track[(by_track['sample_ge_100_v1']) & (by_track['wet_condition_flag_v1']) & by_track['run_style_v1'].ne('UNKNOWN')]
    wet_leader = wet[wet['run_style_v1'] == 'LEADER'].sort_values('condition_bias_score_v1', ascending=False).head(1)
    wet_back = wet[wet['run_style_v1'] == 'BACKMARKER'].sort_values('condition_bias_score_v1', ascending=False).head(1)
    summary_rows = [
        {'metric': 'status', 'value': 'COMPLETE'},
        {'metric': 'rows', 'value': int(len(row_level))},
        {'metric': 'races', 'value': int(results['race_key_norm'].nunique())},
        {'metric': 'groups', 'value': int(len(by_track))},
        {'metric': 'best_wet_leader_track', 'value': wet_leader['track_display_v1'].iloc[0] if not wet_leader.empty else ''},
        {'metric': 'best_wet_leader_score_v1', 'value': round(float(wet_leader['condition_bias_score_v1'].iloc[0]), 3) if not wet_leader.empty else ''},
        {'metric': 'best_wet_backmarker_track', 'value': wet_back['track_display_v1'].iloc[0] if not wet_back.empty else ''},
        {'metric': 'best_wet_backmarker_score_v1', 'value': round(float(wet_back['condition_bias_score_v1'].iloc[0]), 3) if not wet_back.empty else ''},
    ]
    write_csv(pd.DataFrame(summary_rows), OUT_SUMMARY.name)

    print('[CONDITION_BIAS_ENGINE_V1] COMPLETE')
    print(f'rows={len(row_level)}')
    print(f'races={results["race_key_norm"].nunique()}')
    print(f'groups={len(by_track)}')
    print(f'wrote={OUT_MAIN}')
    print(f'wrote={OUT_BY_TRACK}')
    print(f'wrote={OUT_SUMMARY}')


if __name__ == '__main__':
    main()
