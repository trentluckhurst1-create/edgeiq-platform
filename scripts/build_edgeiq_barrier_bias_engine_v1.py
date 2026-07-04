from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from edgeiq_bias_common_v1 import aggregate_bias_table, load_results_base, wet_flag, write_csv

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
OUT_MAIN = DATA / 'edgeiq_barrier_bias_v1.csv'
OUT_BY_TRACK = DATA / 'edgeiq_barrier_bias_by_track_v1.csv'
OUT_SUMMARY = DATA / 'edgeiq_barrier_bias_summary_v1.csv'

INSIDE_BUCKETS = {'1-2', '3-4'}
WIDE_BUCKETS = {'9-10', '11-12', '13+'}


def main():
    results = load_results_base()
    by_track = aggregate_bias_table(
        results,
        group_cols=['track_norm', 'distance_band_v1', 'condition_group_v1', 'barrier_bucket_v1'],
        context_cols=['track_norm', 'distance_band_v1', 'condition_group_v1'],
        score_col='barrier_advantage_score_v1',
        band_col='barrier_bias_band_v1',
    ).sort_values(['barrier_advantage_score_v1', 'starts'], ascending=[False, False]).reset_index(drop=True)
    by_track['wet_condition_flag_v1'] = by_track['condition_group_v1'].map(wet_flag)

    row_level = results.merge(
        by_track[
            [
                'track_norm',
                'distance_band_v1',
                'condition_group_v1',
                'barrier_bucket_v1',
                'track_display_v1',
                'starts',
                'wins',
                'places',
                'win_pct',
                'place_pct',
                'context_win_pct',
                'context_place_pct',
                'barrier_advantage_score_v1',
                'barrier_bias_band_v1',
            ]
        ].rename(
            columns={
                'starts': 'barrier_context_starts_v1',
                'wins': 'barrier_context_wins_v1',
                'places': 'barrier_context_places_v1',
                'win_pct': 'barrier_win_pct_v1',
                'place_pct': 'barrier_place_pct_v1',
            }
        ),
        on=['track_norm', 'distance_band_v1', 'condition_group_v1', 'barrier_bucket_v1'],
        how='left',
    )
    write_csv(row_level, OUT_MAIN.name)
    write_csv(by_track, OUT_BY_TRACK.name)

    profile = (
        by_track[by_track['sample_ge_100_v1']]
        .assign(
            inside_bucket=lambda df: df['barrier_bucket_v1'].isin(INSIDE_BUCKETS),
            wide_bucket=lambda df: df['barrier_bucket_v1'].isin(WIDE_BUCKETS),
        )
    )
    inside = (
        profile[profile['inside_bucket']]
        .groupby('track_norm', dropna=False)
        .agg(inside_score_v1=('barrier_advantage_score_v1', 'mean'), track_display_v1=('track_display_v1', 'first'))
        .reset_index()
    )
    wide = (
        profile[profile['wide_bucket']]
        .groupby('track_norm', dropna=False)
        .agg(wide_score_v1=('barrier_advantage_score_v1', 'mean'))
        .reset_index()
    )
    wet = (
        profile[profile['wet_condition_flag_v1']]
        .groupby(['track_norm', 'barrier_bucket_v1'], dropna=False)
        .agg(wet_score_v1=('barrier_advantage_score_v1', 'mean'))
        .reset_index()
    )
    good = (
        profile[profile['condition_group_v1'] == 'GOOD']
        .groupby(['track_norm', 'barrier_bucket_v1'], dropna=False)
        .agg(good_score_v1=('barrier_advantage_score_v1', 'mean'))
        .reset_index()
    )
    reversals = wet.merge(good, on=['track_norm', 'barrier_bucket_v1'], how='inner')
    reversals['reversal_flag_v1'] = np.sign(reversals['wet_score_v1']).ne(np.sign(reversals['good_score_v1']))

    best_inside = inside.sort_values('inside_score_v1', ascending=False).iloc[0] if not inside.empty else None
    best_wide = wide.sort_values('wide_score_v1', ascending=False).iloc[0] if not wide.empty else None
    reversal_count = int(reversals['reversal_flag_v1'].sum()) if not reversals.empty else 0

    summary_rows = [
        {'metric': 'status', 'value': 'COMPLETE'},
        {'metric': 'rows', 'value': int(len(row_level))},
        {'metric': 'races', 'value': int(results['race_key_norm'].nunique())},
        {'metric': 'groups', 'value': int(len(by_track))},
        {'metric': 'best_inside_track', 'value': best_inside['track_display_v1'] if best_inside is not None else ''},
        {'metric': 'best_inside_score_v1', 'value': round(float(best_inside['inside_score_v1']), 3) if best_inside is not None else ''},
        {'metric': 'best_wide_track', 'value': inside.loc[inside['track_norm'].eq(best_wide['track_norm']), 'track_display_v1'].iloc[0] if best_wide is not None and best_wide['track_norm'] in set(inside['track_norm']) else ''},
        {'metric': 'best_wide_score_v1', 'value': round(float(best_wide['wide_score_v1']), 3) if best_wide is not None else ''},
        {'metric': 'wet_reversal_group_count', 'value': reversal_count},
    ]
    write_csv(pd.DataFrame(summary_rows), OUT_SUMMARY.name)

    print('[BARRIER_BIAS_ENGINE_V1] COMPLETE')
    print(f'rows={len(row_level)}')
    print(f'races={results["race_key_norm"].nunique()}')
    print(f'groups={len(by_track)}')
    print(f'wet_reversal_group_count={reversal_count}')
    print(f'wrote={OUT_MAIN}')
    print(f'wrote={OUT_BY_TRACK}')
    print(f'wrote={OUT_SUMMARY}')


if __name__ == '__main__':
    main()
