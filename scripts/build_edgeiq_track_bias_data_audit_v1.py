from __future__ import annotations

from pathlib import Path

import pandas as pd

from edgeiq_bias_common_v1 import data_path, load_results_base, read_csv, write_csv, write_json

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
OUT_CSV = DATA / 'edgeiq_track_bias_data_audit_v1.csv'
OUT_JSON = DATA / 'edgeiq_track_bias_data_audit_v1.json'


def first_existing(columns, candidates):
    lower = {str(col).lower(): col for col in columns}
    for candidate in candidates:
        if candidate.lower() in lower:
            return lower[candidate.lower()]
    return None


def missing_pct(df: pd.DataFrame, column_name: str | None):
    if not column_name:
        return None
    series = df[column_name]
    missing = series.isna() | series.astype(str).str.strip().eq('') | series.astype(str).str.strip().isin(['-', 'nan', 'NaN', 'None'])
    return round(float(missing.mean()) * 100.0, 2)


def dataset_audit(file_name: str, expected_map: dict[str, list[str]]) -> dict:
    path = data_path(file_name)
    if not path.exists():
        row = {
            'dataset_name': file_name.replace('.csv', '').upper(),
            'file_name': file_name,
            'file_exists': False,
            'rows': 0,
            'unique_races': 0,
            'unique_tracks': 0,
            'min_meeting_date': '',
            'max_meeting_date': '',
        }
        for key in expected_map:
            row[f'has_{key}'] = False
            row[f'missing_{key}_pct'] = None
        return row

    df = pd.read_csv(path, low_memory=False)
    row = {
        'dataset_name': file_name.replace('.csv', '').upper(),
        'file_name': file_name,
        'file_exists': True,
        'rows': int(len(df)),
        'unique_races': 0,
        'unique_tracks': 0,
        'min_meeting_date': '',
        'max_meeting_date': '',
    }

    meeting_col = first_existing(df.columns, ['meeting_date', 'race_date', 'date'])
    track_col = first_existing(df.columns, ['track', 'venue', 'track_name'])
    race_no_col = first_existing(df.columns, ['race_no', 'race_number'])
    race_key_col = first_existing(df.columns, ['race_key', 'race_join_key', 'race_key_norm', 'race_join_key_fixed'])

    if race_key_col:
        row['unique_races'] = int(df[race_key_col].astype(str).nunique())
    elif meeting_col and track_col and race_no_col:
        row['unique_races'] = int(df[[meeting_col, track_col, race_no_col]].astype(str).agg('|'.join, axis=1).nunique())
    if track_col:
        row['unique_tracks'] = int(df[track_col].astype(str).nunique())
    if meeting_col:
        dates = pd.to_datetime(df[meeting_col], errors='coerce').dropna()
        if not dates.empty:
            row['min_meeting_date'] = dates.min().strftime('%Y-%m-%d')
            row['max_meeting_date'] = dates.max().strftime('%Y-%m-%d')

    for key, candidates in expected_map.items():
        actual = first_existing(df.columns, candidates)
        row[f'has_{key}'] = actual is not None
        row[f'missing_{key}_pct'] = missing_pct(df, actual)
    return row


def main():
    datasets = [
        ('edgeiq_racingcom_results_warehouse_v1.csv', {
            'meeting_date': ['meeting_date'],
            'track': ['track'],
            'race_no': ['race_no'],
            'barrier': ['barrier'],
            'distance': ['distance'],
            'track_condition': ['trackCondition', 'track_condition'],
            'finish_position': ['finishPosition', 'finish_position'],
            'horse': ['horseName', 'horse'],
            'horse_key': ['horseKey', 'horse_key'],
            'rail': ['rail', 'railPosition', 'rail_position'],
        }),
        ('edgeiq_tactical_dna_v2.csv', {
            'horse_key': ['horse_key', 'horseKey'],
            'run_style_classification': ['tactical_speed_bucket_v2', 'run_style'],
            'dna_source': ['dna_source'],
            'leader_pct': ['leader_pct_v2'],
            'on_pace_pct': ['on_pace_pct_v2'],
            'midfield_pct': ['midfield_pct_v2'],
            'backmarker_pct': ['backmarker_pct_v2'],
        }),
        ('edgeiq_race_reliability_replay_v1.csv', {
            'meeting_date': ['meeting_date'],
            'track': ['track'],
            'race_no': ['race_no'],
            'horse': ['horse'],
            'runner_rank': ['runner_rank'],
            'won': ['won'],
            'trust_profile': ['trust_profile_v1'],
            'race_reliability_band': ['race_reliability_band_v1'],
        }),
        ('edgeiq_historical_pace_advantage_replay_v1.csv', {
            'meeting_date': ['meeting_date'],
            'track': ['track'],
            'race_no': ['race_no'],
            'horse_key': ['horse_key'],
            'runner_rank': ['runner_rank'],
            'won': ['won'],
            'pace_advantage_band': ['pace_advantage_band_v1'],
            'pace_pressure_band': ['pace_pressure_band_v1'],
        }),
        ('edgeiq_environment_score_replay_v1.csv', {
            'meeting_date': ['meeting_date'],
            'track': ['track'],
            'race_no': ['race_no'],
            'horse': ['horse'],
            'trust_profile': ['trust_profile_v1'],
            'race_reliability_band': ['race_reliability_band_v1'],
            'pace_advantage_band': ['pace_advantage_band_v1'],
            'environment_band': ['environment_band_v1'],
        }),
    ]

    audit_rows = [dataset_audit(file_name, expected_map) for file_name, expected_map in datasets]
    audit_df = pd.DataFrame(audit_rows)
    write_csv(audit_df, OUT_CSV.name)

    raw_results = read_csv('edgeiq_racingcom_results_warehouse_v1.csv')
    raw_finish_num = pd.to_numeric(raw_results.get('finishPosition'), errors='coerce')
    raw_rows = int(len(raw_results))
    scratched_or_nonfinish_rows = int(raw_finish_num.isna().sum())
    results = load_results_base()
    summary = {
        'status': 'COMPLETE',
        'results_rows_available': raw_rows,
        'results_rows_usable_research_base': int(len(results)),
        'results_scratched_or_nonfinish_rows': scratched_or_nonfinish_rows,
        'results_unique_races': int(results['race_key_norm'].nunique()),
        'results_unique_tracks': int(results['track_norm'].nunique()),
        'results_date_coverage_start': str(results['meeting_date'].min()),
        'results_date_coverage_end': str(results['meeting_date'].max()),
        'results_missing_barrier_pct': round(float(results['barrier_num'].isna().mean()) * 100.0, 2),
        'results_missing_condition_pct': round(float(results['track_condition_raw'].eq('').mean()) * 100.0, 2),
        'results_missing_distance_pct': round(float(results['distance_m'].isna().mean()) * 100.0, 2),
        'results_missing_finish_pct': round(float(raw_finish_num.isna().mean()) * 100.0, 2),
        'rail_column_available_anywhere': bool(audit_df.filter(regex='^has_rail$').fillna(False).any().any()),
        'notes': 'Rail position is not present in the current results warehouse inputs. Research engines exclude scratched rows with non-numeric finish positions.' if not bool(audit_df.filter(regex='^has_rail$').fillna(False).any().any()) else 'Research engines exclude scratched rows with non-numeric finish positions.',
        'datasets': audit_rows,
    }
    write_json(summary, OUT_JSON.name)

    print('[TRACK_BIAS_DATA_AUDIT_V1] COMPLETE')
    print(f"rows_available={summary['results_rows_available']}")
    print(f"rows_usable_research_base={summary['results_rows_usable_research_base']}")
    print(f"scratched_or_nonfinish_rows={summary['results_scratched_or_nonfinish_rows']}")
    print(f"unique_races={summary['results_unique_races']}")
    print(f"unique_tracks={summary['results_unique_tracks']}")
    print(f"date_coverage={summary['results_date_coverage_start']} to {summary['results_date_coverage_end']}")
    print(f"missing_barrier_pct={summary['results_missing_barrier_pct']}")
    print(f"missing_condition_pct={summary['results_missing_condition_pct']}")
    print(f"missing_distance_pct={summary['results_missing_distance_pct']}")
    print(f"missing_finish_pct={summary['results_missing_finish_pct']}")
    print(f"wrote={OUT_CSV}")
    print(f"wrote={OUT_JSON}")


if __name__ == '__main__':
    main()
