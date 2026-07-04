from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from edgeiq_bias_common_v1 import write_csv, write_json

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
TRACK_BIAS = DATA / 'edgeiq_track_bias_by_track_v1.csv'
BARRIER = DATA / 'edgeiq_barrier_bias_by_track_v1.csv'
RUN_STYLE = DATA / 'edgeiq_run_style_bias_by_track_v1.csv'
CONDITION = DATA / 'edgeiq_condition_bias_by_track_v1.csv'
TRACK_DISTANCE = DATA / 'edgeiq_track_distance_bias_v1.csv'
TRACK_CONDITION_RUNSTYLE = DATA / 'edgeiq_track_condition_runstyle_v1.csv'
OUT_CSV = DATA / 'edgeiq_bias_discovery_report_v1.csv'
OUT_SUMMARY = DATA / 'edgeiq_bias_discovery_report_v1_summary.csv'
OUT_JSON = DATA / 'edgeiq_bias_discovery_report_v1.json'


def load_required(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f'Missing input: {path}')
    return pd.read_csv(path, low_memory=False)


def ranked_section(df: pd.DataFrame, section: str, score_col: str, label_builder, extra_cols: list[str], min_starts: int = 100, top_n: int = 25) -> pd.DataFrame:
    work = df.copy()
    if 'starts' in work.columns:
        work = work[work['starts'] >= min_starts].copy()
    work = work.dropna(subset=[score_col]).copy()
    work['section'] = section
    work['finding_label_v1'] = work.apply(label_builder, axis=1)
    work['ranking_score_abs_v1'] = work[score_col].abs()
    work = work.sort_values(['ranking_score_abs_v1', 'starts'], ascending=[False, False]).head(top_n).reset_index(drop=True)
    work['rank_v1'] = work.index + 1
    keep = ['section', 'rank_v1', 'finding_label_v1', score_col, 'ranking_score_abs_v1'] + [col for col in extra_cols if col in work.columns]
    return work[keep]


def main():
    track_bias = load_required(TRACK_BIAS)
    barrier = load_required(BARRIER)
    run_style = load_required(RUN_STYLE)
    condition = load_required(CONDITION)
    track_distance = load_required(TRACK_DISTANCE)
    tcr = load_required(TRACK_CONDITION_RUNSTYLE)

    barrier_top = ranked_section(
        barrier[barrier['barrier_bucket_v1'] != 'UNKNOWN'],
        'Top 25 Barrier Biases',
        'barrier_advantage_score_v1',
        lambda row: f"{row.get('track_display_v1', row['track_norm'])} | {row['distance_band_v1']} | {row['condition_group_v1']} | Barrier {row['barrier_bucket_v1']}",
        ['track_display_v1', 'track_norm', 'distance_band_v1', 'condition_group_v1', 'barrier_bucket_v1', 'starts', 'win_pct', 'place_pct'],
    )
    run_style_top = ranked_section(
        run_style[run_style['run_style_v1'] != 'UNKNOWN'],
        'Top 25 Run Style Biases',
        'run_style_bias_score_v1',
        lambda row: f"{row.get('track_display_v1', row['track_norm'])} | {row['run_style_v1']}",
        ['track_display_v1', 'track_norm', 'run_style_v1', 'starts', 'win_pct', 'place_pct'],
    )
    wet_top = ranked_section(
        condition[(condition['condition_group_v1'].isin(['SOFT', 'HEAVY'])) & (condition['run_style_v1'] != 'UNKNOWN')],
        'Top 25 Wet Track Biases',
        'condition_bias_score_v1',
        lambda row: f"{row.get('track_display_v1', row['track_norm'])} | {row['condition_group_v1']} | {row['run_style_v1']}",
        ['track_display_v1', 'track_norm', 'condition_group_v1', 'run_style_v1', 'starts', 'win_pct', 'place_pct'],
    )
    track_distance_top = ranked_section(
        track_distance,
        'Top 25 Track-Distance Biases',
        'track_distance_uniqueness_score_v1',
        lambda row: f"{row.get('track_display_v1', row['track_norm'])} | {row['distance_band_v1']}",
        ['track_display_v1', 'track_norm', 'distance_band_v1', 'starts', 'inside_minus_wide_win_pts', 'front_minus_back_win_pts'],
    )
    tcr_top = ranked_section(
        tcr[tcr['ranking_eligible_v1']],
        'Top 25 Track-Condition-Run Style Biases',
        'track_condition_runstyle_score_v1',
        lambda row: f"{row.get('track_display_v1', row['track_norm'])} | {row['condition_group_v1']} | {row['run_style_v1']}",
        ['track_display_v1', 'track_norm', 'condition_group_v1', 'run_style_v1', 'starts', 'win_pct', 'place_pct'],
    )
    report = pd.concat([barrier_top, run_style_top, wet_top, track_distance_top, tcr_top], ignore_index=True)
    write_csv(report, OUT_CSV.name)

    best_leader = run_style[(run_style['run_style_v1'] == 'LEADER') & (run_style['starts'] >= 100)].sort_values('run_style_bias_score_v1', ascending=False).head(1)
    best_back = run_style[(run_style['run_style_v1'] == 'BACKMARKER') & (run_style['starts'] >= 100)].sort_values('run_style_bias_score_v1', ascending=False).head(1)
    best_low_barrier = barrier[(barrier['barrier_bucket_v1'].isin(['1-2', '3-4'])) & (barrier['starts'] >= 100)].sort_values('barrier_advantage_score_v1', ascending=False).head(1)
    best_wide_barrier = barrier[(barrier['barrier_bucket_v1'].isin(['11-12', '13+'])) & (barrier['starts'] >= 100)].sort_values('barrier_advantage_score_v1', ascending=False).head(1)
    most_unique_distance = track_distance[track_distance['starts'] >= 100].sort_values('track_distance_uniqueness_score_v1', ascending=False).head(1)
    strongest_track_bias = track_bias[track_bias['starts'] >= 300].sort_values('track_bias_score_v1', ascending=False).head(1)

    summary_rows = [
        {'metric': 'status', 'value': 'COMPLETE'},
        {'metric': 'report_rows', 'value': int(len(report))},
        {'metric': 'strongest_leader_track', 'value': best_leader['track_display_v1'].iloc[0] if not best_leader.empty else ''},
        {'metric': 'strongest_backmarker_track', 'value': best_back['track_display_v1'].iloc[0] if not best_back.empty else ''},
        {'metric': 'strongest_low_barrier_track', 'value': best_low_barrier['track_display_v1'].iloc[0] if not best_low_barrier.empty else ''},
        {'metric': 'strongest_wide_barrier_track', 'value': best_wide_barrier['track_display_v1'].iloc[0] if not best_wide_barrier.empty else ''},
        {'metric': 'most_unique_track_distance', 'value': f"{most_unique_distance['track_display_v1'].iloc[0]} | {most_unique_distance['distance_band_v1'].iloc[0]}" if not most_unique_distance.empty else ''},
        {'metric': 'strongest_track_bias_track', 'value': strongest_track_bias['track_display_v1'].iloc[0] if not strongest_track_bias.empty else ''},
    ]
    write_csv(pd.DataFrame(summary_rows), OUT_SUMMARY.name)

    payload = {
        'status': 'COMPLETE',
        'top_25_barrier_biases': barrier_top.to_dict(orient='records'),
        'top_25_run_style_biases': run_style_top.to_dict(orient='records'),
        'top_25_wet_track_biases': wet_top.to_dict(orient='records'),
        'top_25_track_distance_biases': track_distance_top.to_dict(orient='records'),
        'top_25_track_condition_runstyle_biases': tcr_top.to_dict(orient='records'),
    }
    write_json(payload, OUT_JSON.name)

    print('[BIAS_DISCOVERY_REPORT_V1] COMPLETE')
    print(f'report_rows={len(report)}')
    print(f'wrote={OUT_CSV}')
    print(f'wrote={OUT_SUMMARY}')
    print(f'wrote={OUT_JSON}')


if __name__ == '__main__':
    main()
