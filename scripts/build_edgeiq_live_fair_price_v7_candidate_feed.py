from pathlib import Path
import re

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'

LIVE_RUNNER_BOARD = DATA / 'edgeiq_live_runner_board_v1.csv'
TJ_V3_FEED = DATA / 'edgeiq_live_trainer_jockey_factor_feed_v3.csv'
CURRENT_FAIR_PRICE = DATA / 'edgeiq_fair_price_v7_2.csv'
OUT = DATA / 'edgeiq_live_fair_price_v7_candidate_feed.csv'

TJ_ADJUSTMENT_PCT = {
    'POOR': -1.0,
    'NEGATIVE': -0.5,
    'NEUTRAL': 0.0,
    'LOW_SAMPLE': 0.0,
    'UNKNOWN': 0.0,
    'POSITIVE': 0.5,
    'ELITE': 1.0,
}

TJ_ACTIVE_VERDICTS = {'COMPLETE', 'TRAINER_JOCKEY_ONLY'}


def clean_text(value):
    if pd.isna(value):
        return ''
    return re.sub(r'[^A-Z0-9]', '', str(value).upper())


def pick_col(df, candidates):
    lower_map = {str(col).lower().strip(): col for col in df.columns}
    for candidate in candidates:
        key = candidate.lower().strip()
        if key in lower_map:
            return lower_map[key]
    return None


def format_date(series):
    parsed = pd.to_datetime(series, errors='coerce')
    formatted = parsed.dt.strftime('%Y-%m-%d')
    return formatted.fillna('')


def num(series):
    return pd.to_numeric(series, errors='coerce')


def build_join_fields(df, date_candidates, track_candidates, race_candidates, horse_key_candidates, horse_name_candidates):
    date_col = pick_col(df, date_candidates)
    track_col = pick_col(df, track_candidates)
    race_col = pick_col(df, race_candidates)
    horse_key_col = pick_col(df, horse_key_candidates)
    horse_name_col = pick_col(df, horse_name_candidates)

    if date_col is None or track_col is None or race_col is None:
        raise ValueError('Missing required join columns.')
    if horse_key_col is None and horse_name_col is None:
        raise ValueError('Missing horse identity columns.')

    joined = df.copy()
    joined['join_meeting_date_v1'] = format_date(joined[date_col])
    joined['join_track_v1'] = joined[track_col].fillna('').astype(str).str.upper().str.strip()
    joined['join_race_no_v1'] = num(joined[race_col])

    if horse_key_col is not None:
        horse_key_series = joined[horse_key_col]
    else:
        horse_key_series = joined[horse_name_col]
    joined['join_horse_key_v1'] = horse_key_series.fillna('').map(clean_text)
    joined['join_race_key_v1'] = (
        joined['join_meeting_date_v1']
        + '|'
        + joined['join_track_v1']
        + '|R'
        + joined['join_race_no_v1'].fillna(0).astype(int).astype(str)
    )
    return joined


def note_for_row(current_fair_price, tj_verdict, tj_band, tj_adjustment_pct):
    if pd.isna(current_fair_price) or current_fair_price <= 0:
        return 'SIDECAR ONLY - no current fair price available'
    if tj_verdict not in TJ_ACTIVE_VERDICTS:
        return f'SIDECAR ONLY - TJ verdict {tj_verdict}; no adjustment applied'
    return f'SIDECAR ONLY - TJ {tj_band} {tj_adjustment_pct:+.1f}% candidate adjustment'


def main():
    required = [LIVE_RUNNER_BOARD, TJ_V3_FEED, CURRENT_FAIR_PRICE]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f'Missing required inputs: {missing}')

    live = pd.read_csv(LIVE_RUNNER_BOARD, low_memory=False)
    tj = pd.read_csv(TJ_V3_FEED, low_memory=False)
    fair = pd.read_csv(CURRENT_FAIR_PRICE, low_memory=False)

    live = build_join_fields(
        live,
        ['race_date', 'meeting_date', 'date'],
        ['track', 'meeting_name', 'location'],
        ['race_no', 'race_number'],
        ['horse_canon', 'horse_key', 'horse_key_join'],
        ['horse', 'runner', 'runner_name'],
    )
    tj = build_join_fields(
        tj,
        ['race_date', 'meeting_date', 'date'],
        ['track', 'meeting_name', 'location'],
        ['race_no', 'race_number'],
        ['horse_canon', 'horse_key', 'horse_key_join'],
        ['horse', 'runner', 'runner_name'],
    )
    fair = build_join_fields(
        fair,
        ['race_date', 'meeting_date', 'date'],
        ['track', 'meeting_name', 'location'],
        ['race_no', 'race_number'],
        ['horse_key', 'horse_key_join', 'horse_canon'],
        ['horse', 'runner', 'runner_name'],
    )

    tj_cols = [
        'join_meeting_date_v1',
        'join_track_v1',
        'join_race_no_v1',
        'join_horse_key_v1',
        'trainer_jockey_blend_band_v3',
        'tj_factor_verdict_v3',
    ]
    fair_price_col = pick_col(fair, ['fair_price_v7_2', 'fair_price', 'ui_fair_price'])
    if fair_price_col is None:
        raise ValueError('No current fair price column found in edgeiq_fair_price_v7_2.csv')

    fair_small = fair[
        [
            'join_meeting_date_v1',
            'join_track_v1',
            'join_race_no_v1',
            'join_horse_key_v1',
            fair_price_col,
        ]
    ].copy()
    fair_small = fair_small.rename(columns={fair_price_col: 'current_fair_price'})

    dedupe_keys = ['join_meeting_date_v1', 'join_track_v1', 'join_race_no_v1', 'join_horse_key_v1']
    tj_small = tj[tj_cols].drop_duplicates(subset=dedupe_keys, keep='first').copy()
    fair_small = fair_small.drop_duplicates(subset=dedupe_keys, keep='first').copy()

    merged = live.merge(tj_small, on=dedupe_keys, how='left')
    merged = merged.merge(fair_small, on=dedupe_keys, how='left')

    merged['current_fair_price'] = num(merged['current_fair_price']).round(2)
    merged['tj_band'] = merged['trainer_jockey_blend_band_v3'].fillna('UNKNOWN').astype(str).str.upper()
    merged['tj_verdict'] = merged['tj_factor_verdict_v3'].fillna('UNMATCHED').astype(str).str.upper()
    merged['tj_adjustment_pct'] = np.where(
        merged['tj_verdict'].isin(TJ_ACTIVE_VERDICTS),
        merged['tj_band'].map(TJ_ADJUSTMENT_PCT).fillna(0.0),
        0.0,
    )

    merged['current_fair_probability_v1'] = np.where(
        merged['current_fair_price'].gt(0),
        1.0 / merged['current_fair_price'],
        np.nan,
    )
    merged['tj_probability_multiplier_v1'] = 1.0 + (merged['tj_adjustment_pct'] / 100.0)
    merged['tj_adjusted_raw_probability_v1'] = (
        merged['current_fair_probability_v1'] * merged['tj_probability_multiplier_v1']
    )

    race_baseline_sum = merged.groupby('join_race_key_v1')['current_fair_probability_v1'].transform('sum')
    race_adjusted_sum = merged.groupby('join_race_key_v1')['tj_adjusted_raw_probability_v1'].transform('sum')
    merged['race_probability_preservation_factor_v1'] = np.where(
        race_adjusted_sum.gt(0),
        race_baseline_sum / race_adjusted_sum,
        np.nan,
    )
    merged['tj_adjusted_probability_v7_candidate'] = (
        merged['tj_adjusted_raw_probability_v1'] * merged['race_probability_preservation_factor_v1']
    )
    merged['tj_adjusted_fair_price_v7_candidate'] = np.where(
        merged['tj_adjusted_probability_v7_candidate'].gt(0),
        1.0 / merged['tj_adjusted_probability_v7_candidate'],
        np.nan,
    )
    merged['tj_adjusted_fair_price_v7_candidate'] = num(merged['tj_adjusted_fair_price_v7_candidate']).round(2)

    merged['v7_candidate_note'] = [
        note_for_row(current_fair_price, tj_verdict, tj_band, tj_adjustment_pct)
        for current_fair_price, tj_verdict, tj_band, tj_adjustment_pct in zip(
            merged['current_fair_price'],
            merged['tj_verdict'],
            merged['tj_band'],
            merged['tj_adjustment_pct'],
        )
    ]

    horse_col = pick_col(merged, ['horse', 'runner', 'runner_name'])
    track_col = pick_col(merged, ['track', 'meeting_name', 'location'])
    race_col = pick_col(merged, ['race_no', 'race_number'])

    out = pd.DataFrame(
        {
            'horse': merged[horse_col].fillna('').astype(str),
            'track': merged[track_col].fillna('').astype(str),
            'race_no': num(merged[race_col]).astype('Int64'),
            'current_fair_price': merged['current_fair_price'].round(2),
            'tj_adjusted_fair_price_v7_candidate': merged['tj_adjusted_fair_price_v7_candidate'].round(2),
            'tj_adjustment_pct': merged['tj_adjustment_pct'].round(1),
            'tj_band': merged['tj_band'],
            'tj_verdict': merged['tj_verdict'],
            'v7_candidate_note': merged['v7_candidate_note'],
        }
    )

    out.to_csv(OUT, index=False)

    live_rows = len(out)
    tj_matched_rows = int(merged['trainer_jockey_blend_band_v3'].notna().sum())
    fair_price_rows = int(merged['current_fair_price'].notna().sum())
    active_tj_rows = int(merged['tj_verdict'].isin(TJ_ACTIVE_VERDICTS).sum())
    candidate_price_rows = int(merged['tj_adjusted_fair_price_v7_candidate'].notna().sum())

    print('[LIVE_FAIR_PRICE_V7_CANDIDATE_FEED] COMPLETE')
    print(f'live_rows={live_rows}')
    print(f'tj_matched_rows={tj_matched_rows}')
    print(f'current_fair_price_rows={fair_price_rows}')
    print(f'active_tj_rows={active_tj_rows}')
    print(f'candidate_price_rows={candidate_price_rows}')
    print(f'wrote={OUT}')


if __name__ == '__main__':
    main()
