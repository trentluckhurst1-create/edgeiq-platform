from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from edgeiq_bias_common_v1 import load_results_with_run_style, pct_from_counts, write_csv

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
OUT_MAIN = DATA / 'edgeiq_track_distance_bias_v1.csv'
OUT_SUMMARY = DATA / 'edgeiq_track_distance_bias_summary_v1.csv'


def pct_series(wins, starts):
    return np.where(starts > 0, wins / starts * 100.0, np.nan)


def main():
    results = load_results_with_run_style()
    results['inside_flag_v1'] = results['barrier_num'].between(1, 4, inclusive='both')
    results['wide_flag_v1'] = results['barrier_num'] >= 9
    results['front_flag_v1'] = results['run_style_v1'].isin(['LEADER', 'ON_PACE'])
    results['back_flag_v1'] = results['run_style_v1'].isin(['MIDFIELD', 'BACKMARKER'])

    grouped = (
        results.groupby(['track_norm', 'distance_band_v1'], dropna=False)
        .agg(
            starts=('won', 'size'),
            races=('race_key_norm', 'nunique'),
            wins=('won', 'sum'),
            places=('placed', 'sum'),
            track_display_v1=('track_raw', lambda s: s.mode().iat[0] if not s.mode().empty else s.iloc[0]),
            inside_starts=('inside_flag_v1', 'sum'),
            inside_wins=('won', lambda s: int(s[results.loc[s.index, 'inside_flag_v1']].sum())),
            wide_starts=('wide_flag_v1', 'sum'),
            wide_wins=('won', lambda s: int(s[results.loc[s.index, 'wide_flag_v1']].sum())),
            front_starts=('front_flag_v1', 'sum'),
            front_wins=('won', lambda s: int(s[results.loc[s.index, 'front_flag_v1']].sum())),
            back_starts=('back_flag_v1', 'sum'),
            back_wins=('won', lambda s: int(s[results.loc[s.index, 'back_flag_v1']].sum())),
        )
        .reset_index()
    )
    grouped['win_pct'] = pct_series(grouped['wins'], grouped['starts']).round(2)
    grouped['place_pct'] = pct_series(grouped['places'], grouped['starts']).round(2)
    grouped['inside_win_pct'] = pct_series(grouped['inside_wins'], grouped['inside_starts']).round(2)
    grouped['wide_win_pct'] = pct_series(grouped['wide_wins'], grouped['wide_starts']).round(2)
    grouped['front_win_pct'] = pct_series(grouped['front_wins'], grouped['front_starts']).round(2)
    grouped['back_win_pct'] = pct_series(grouped['back_wins'], grouped['back_starts']).round(2)
    grouped['inside_minus_wide_win_pts'] = (grouped['inside_win_pct'] - grouped['wide_win_pct']).round(2)
    grouped['front_minus_back_win_pts'] = (grouped['front_win_pct'] - grouped['back_win_pct']).round(2)
    grouped['track_distance_uniqueness_score_v1'] = (
        grouped['inside_minus_wide_win_pts'].abs().fillna(0) + grouped['front_minus_back_win_pts'].abs().fillna(0)
    ).round(3)
    for threshold in [50, 100, 300]:
        grouped[f'sample_ge_{threshold}_v1'] = grouped['starts'] >= threshold
    grouped = grouped.sort_values(['track_distance_uniqueness_score_v1', 'starts'], ascending=[False, False]).reset_index(drop=True)
    write_csv(grouped, OUT_MAIN.name)

    best_inside = grouped.sort_values('inside_minus_wide_win_pts', ascending=False).head(1)
    best_front = grouped.sort_values('front_minus_back_win_pts', ascending=False).head(1)
    summary_rows = [
        {'metric': 'status', 'value': 'COMPLETE'},
        {'metric': 'rows', 'value': int(len(grouped))},
        {'metric': 'best_inside_track_distance', 'value': f"{best_inside['track_display_v1'].iloc[0]} | {best_inside['distance_band_v1'].iloc[0]}" if not best_inside.empty else ''},
        {'metric': 'best_inside_minus_wide_win_pts', 'value': round(float(best_inside['inside_minus_wide_win_pts'].iloc[0]), 2) if not best_inside.empty else ''},
        {'metric': 'best_front_track_distance', 'value': f"{best_front['track_display_v1'].iloc[0]} | {best_front['distance_band_v1'].iloc[0]}" if not best_front.empty else ''},
        {'metric': 'best_front_minus_back_win_pts', 'value': round(float(best_front['front_minus_back_win_pts'].iloc[0]), 2) if not best_front.empty else ''},
    ]
    write_csv(pd.DataFrame(summary_rows), OUT_SUMMARY.name)

    print('[TRACK_DISTANCE_BIAS_V1] COMPLETE')
    print(f'rows={len(grouped)}')
    print(f'wrote={OUT_MAIN}')
    print(f'wrote={OUT_SUMMARY}')


if __name__ == '__main__':
    main()
