from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from edgeiq_bias_common_v1 import normalize_horse_key, normalize_track, safe_num, write_csv

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
RUNNER = DATA / 'edgeiq_trainer_jockey_factor_runner_v1.csv'
PACE = DATA / 'edgeiq_pace_advantage_replay_v1.csv'
TRACK_BIAS = DATA / 'edgeiq_track_bias_v1.csv'
BARRIER_BIAS = DATA / 'edgeiq_barrier_bias_v1.csv'
RUN_STYLE_BIAS = DATA / 'edgeiq_run_style_bias_v1.csv'
CONDITION_BIAS = DATA / 'edgeiq_condition_bias_v1.csv'
OUT_DETAIL = DATA / 'edgeiq_bias_factor_relevance_audit_v1.csv'
OUT_SUMMARY = DATA / 'edgeiq_bias_factor_relevance_audit_summary_v1.csv'


def pct(numerator, denominator):
    if denominator == 0:
        return np.nan
    return round(float(numerator) / float(denominator) * 100.0, 2)


def win_pct(frame: pd.DataFrame):
    if len(frame) == 0:
        return np.nan
    return round(float(frame['rank1_won'].mean()) * 100.0, 2)


def prep_runner() -> pd.DataFrame:
    df = pd.read_csv(RUNNER, low_memory=False)
    out = df.copy()
    out['meeting_date'] = pd.to_datetime(out['meeting_date'], errors='coerce').dt.strftime('%Y-%m-%d')
    out['track_norm'] = out['track'].map(normalize_track)
    out['race_no_num'] = safe_num(out['race_no']).astype('Int64')
    out['race_key_norm'] = out['meeting_date'] + '|' + out['track_norm'] + '|R' + out['race_no_num'].fillna(0).astype(int).astype(str)
    out['horse_key_norm'] = out['horse_key'].fillna(out['horse']).map(normalize_horse_key)
    out['runner_rank_num'] = safe_num(out['runner_rank'])
    out['won_num'] = safe_num(out['won']).fillna(safe_num(out.get('won_v1', 0))).fillna(0).astype(int)
    out['trainer_jockey_blend_score_v1'] = safe_num(out['trainer_jockey_blend_score_v1']).fillna(0)
    out['race_reliability_band_v1'] = out['race_reliability_band_v1'].fillna('UNKNOWN').astype(str).str.upper()
    out['trust_profile_v1'] = out['trust_profile_v1'].fillna('UNKNOWN').astype(str).str.upper()
    return out


def prep_sidecar(path: Path, score_cols: list[str], band_cols: list[str]) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    out = pd.DataFrame()
    out['meeting_date'] = pd.to_datetime(df['meeting_date'], errors='coerce').dt.strftime('%Y-%m-%d')
    out['track_norm'] = df['track_norm'] if 'track_norm' in df.columns else df['track'].map(normalize_track)
    out['race_no_num'] = safe_num(df['race_no']).astype('Int64')
    out['horse_key_norm'] = df['horse_key_norm'] if 'horse_key_norm' in df.columns else df.get('horse_key', df.get('horse')).map(normalize_horse_key)
    for col in score_cols:
        if col in df.columns:
            out[col] = safe_num(df[col])
    for col in band_cols:
        if col in df.columns:
            out[col] = df[col].fillna('UNKNOWN').astype(str).str.upper()
    return out.drop_duplicates(subset=['meeting_date', 'track_norm', 'race_no_num', 'horse_key_norm'], keep='first')


def prep_pace() -> pd.DataFrame:
    df = pd.read_csv(PACE, low_memory=False)
    out = pd.DataFrame()
    out['meeting_date'] = pd.to_datetime(df['meeting_date'], errors='coerce').dt.strftime('%Y-%m-%d')
    out['track_norm'] = df['track'].map(normalize_track)
    out['race_no_num'] = safe_num(df['race_no']).astype('Int64')
    out['horse_key_norm'] = df.get('horse_key', df['horse']).map(normalize_horse_key)
    out['pace_advantage_score_v1'] = safe_num(df['pace_advantage_score_v1']).fillna(0)
    out['pace_advantage_band_v1'] = df['pace_advantage_band_v1'].fillna('UNKNOWN').astype(str).str.upper()
    return out.drop_duplicates(subset=['meeting_date', 'track_norm', 'race_no_num', 'horse_key_norm'], keep='first')


def enrich_runner(runner: pd.DataFrame) -> pd.DataFrame:
    keys = ['meeting_date', 'track_norm', 'race_no_num', 'horse_key_norm']
    pace = prep_pace()
    track_bias = prep_sidecar(TRACK_BIAS, ['track_bias_score_v1'], ['track_bias_band_v1'])
    barrier = prep_sidecar(BARRIER_BIAS, ['barrier_advantage_score_v1'], ['barrier_bias_band_v1'])
    run_style = prep_sidecar(RUN_STYLE_BIAS, ['run_style_bias_score_v1'], ['run_style_bias_band_v1', 'run_style_v1'])
    condition = prep_sidecar(CONDITION_BIAS, ['condition_bias_score_v1'], ['condition_bias_band_v1'])
    enriched = runner.merge(pace, on=keys, how='left')
    enriched = enriched.merge(track_bias, on=keys, how='left')
    enriched = enriched.merge(barrier, on=keys, how='left')
    enriched = enriched.merge(run_style, on=keys, how='left')
    enriched = enriched.merge(condition, on=keys, how='left')
    for col in ['pace_advantage_score_v1', 'track_bias_score_v1', 'barrier_advantage_score_v1', 'run_style_bias_score_v1', 'condition_bias_score_v1']:
        if col in enriched.columns:
            enriched[col] = safe_num(enriched[col]).fillna(0)
    for col in ['pace_advantage_band_v1', 'track_bias_band_v1', 'barrier_bias_band_v1', 'run_style_bias_band_v1', 'condition_bias_band_v1', 'run_style_v1']:
        if col in enriched.columns:
            enriched[col] = enriched[col].fillna('UNKNOWN').astype(str).str.upper()
    return enriched


def make_side(frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
    cols = [
        'meeting_date', 'track', 'track_norm', 'race_no_num', 'race_key_norm', 'horse', 'horse_key_norm',
        'runner_rank_num', 'won_num', 'trainer_jockey_blend_score_v1', 'pace_advantage_score_v1', 'pace_advantage_band_v1',
        'track_bias_score_v1', 'track_bias_band_v1', 'barrier_advantage_score_v1', 'barrier_bias_band_v1',
        'run_style_bias_score_v1', 'run_style_bias_band_v1', 'condition_bias_score_v1', 'condition_bias_band_v1',
        'race_reliability_band_v1', 'trust_profile_v1', 'run_style_v1'
    ]
    side = frame[cols].copy()
    rename = {col: f'{prefix}_{col}' for col in cols if col not in ['meeting_date', 'track_norm', 'race_no_num', 'race_key_norm']}
    return side.rename(columns=rename)


def main():
    runner = enrich_runner(prep_runner())
    eligible = (
        runner.groupby('race_key_norm', dropna=False)
        .agg(rank1_count=('runner_rank_num', lambda s: int((s == 1).sum())), winner_count=('won_num', 'sum'))
        .reset_index()
    )
    eligible = eligible[(eligible['rank1_count'] == 1) & (eligible['winner_count'] == 1)][['race_key_norm']]

    rank1 = make_side(runner[runner['runner_rank_num'] == 1], 'rank1')
    winner = make_side(runner[runner['won_num'] == 1], 'winner')
    join_keys = ['race_key_norm', 'meeting_date', 'track_norm', 'race_no_num']
    detail = eligible.merge(rank1, on='race_key_norm', how='inner').merge(winner, on=join_keys, how='inner')
    detail['rank1_won'] = detail['rank1_horse_key_norm'] == detail['winner_horse_key_norm']
    detail['rank1_loss_flag'] = ~detail['rank1_won']

    losses = detail[detail['rank1_loss_flag']].copy()
    losses['tj_superior_flag_v1'] = losses['winner_trainer_jockey_blend_score_v1'] > losses['rank1_trainer_jockey_blend_score_v1']
    losses['pace_superior_flag_v1'] = losses['winner_pace_advantage_score_v1'] > losses['rank1_pace_advantage_score_v1']
    losses['barrier_bias_superior_flag_v1'] = losses['winner_barrier_advantage_score_v1'] > losses['rank1_barrier_advantage_score_v1']
    losses['run_style_bias_superior_flag_v1'] = losses['winner_run_style_bias_score_v1'] > losses['rank1_run_style_bias_score_v1']
    losses['condition_bias_superior_flag_v1'] = losses['winner_condition_bias_score_v1'] > losses['rank1_condition_bias_score_v1']

    detail.to_csv(OUT_DETAIL, index=False)

    strong_reliability = detail['rank1_race_reliability_band_v1'].isin(['POSITIVE', 'ELITE'])
    weak_reliability = detail['rank1_race_reliability_band_v1'].isin(['POOR', 'NEGATIVE'])
    strong_trust = detail['rank1_trust_profile_v1'].isin(['STRONG', 'ELITE'])
    weak_trust = detail['rank1_trust_profile_v1'].isin(['STANDARD', 'CHAOTIC'])
    strong_track_bias = detail['rank1_track_bias_band_v1'].isin(['POSITIVE', 'STRONG_POSITIVE'])
    weak_track_bias = detail['rank1_track_bias_band_v1'].isin(['NEGATIVE', 'STRONG_NEGATIVE'])
    strong_pace_context = detail['rank1_pace_advantage_band_v1'].isin(['POSITIVE', 'ELITE'])
    weak_pace_context = detail['rank1_pace_advantage_band_v1'].isin(['NEGATIVE', 'POOR'])

    tj_pct = pct(int(losses['tj_superior_flag_v1'].sum()), len(losses))
    pace_pct = pct(int(losses['pace_superior_flag_v1'].sum()), len(losses))
    barrier_pct = pct(int(losses['barrier_bias_superior_flag_v1'].sum()), len(losses))
    run_style_pct = pct(int(losses['run_style_bias_superior_flag_v1'].sum()), len(losses))
    condition_pct = pct(int(losses['condition_bias_superior_flag_v1'].sum()), len(losses))

    reliability_lift = round(win_pct(detail[strong_reliability]) - win_pct(detail[weak_reliability]), 2)
    trust_lift = round(win_pct(detail[strong_trust]) - win_pct(detail[weak_trust]), 2)
    track_bias_lift = round(win_pct(detail[strong_track_bias]) - win_pct(detail[weak_track_bias]), 2)
    pace_context_lift = round(win_pct(detail[strong_pace_context]) - win_pct(detail[weak_pace_context]), 2)

    horse_feature_scores = {
        'TJ_BLEND': tj_pct,
        'BARRIER_BIAS': barrier_pct,
        'RUN_STYLE_BIAS': run_style_pct,
        'CONDITION_BIAS': condition_pct,
        'PACE_ADVANTAGE': pace_pct,
    }
    best_horse_feature = max(horse_feature_scores, key=lambda key: (-1 if pd.isna(horse_feature_scores[key]) else horse_feature_scores[key]))
    context_scores = {
        'RACE_RELIABILITY': reliability_lift,
        'TRUST_PROFILE': trust_lift,
        'TRACK_BIAS': track_bias_lift,
        'PACE_CONTEXT': pace_context_lift,
    }
    best_context_feature = max(context_scores, key=lambda key: (-999 if pd.isna(context_scores[key]) else context_scores[key]))

    if any(not pd.isna(v) and v > tj_pct for k, v in horse_feature_scores.items() if k != 'TJ_BLEND'):
        verdict = 'BIAS_FACTOR_BEATS_TJ'
    elif any(not pd.isna(v) and v >= tj_pct - 5 for k, v in horse_feature_scores.items() if k != 'TJ_BLEND'):
        verdict = 'BIAS_FACTOR_APPROACHES_TJ'
    else:
        verdict = 'TJ_REMAINS_STRONGER_THAN_BIAS_FACTORS'

    future_candidates = [name for name, value in horse_feature_scores.items() if name != 'TJ_BLEND' and not pd.isna(value) and value >= 35.0]
    summary_rows = [
        {'metric': 'status', 'value': 'COMPLETE'},
        {'metric': 'races_audited', 'value': int(len(detail))},
        {'metric': 'rank1_wins', 'value': int(detail['rank1_won'].sum())},
        {'metric': 'rank1_losses', 'value': int(len(losses))},
        {'metric': 'losses_winner_better_tj_blend_pct', 'value': tj_pct},
        {'metric': 'losses_winner_better_barrier_bias_pct', 'value': barrier_pct},
        {'metric': 'losses_winner_better_run_style_bias_pct', 'value': run_style_pct},
        {'metric': 'losses_winner_better_condition_bias_pct', 'value': condition_pct},
        {'metric': 'losses_winner_better_pace_advantage_pct', 'value': pace_pct},
        {'metric': 'race_reliability_lift_pts', 'value': reliability_lift},
        {'metric': 'trust_profile_lift_pts', 'value': trust_lift},
        {'metric': 'track_bias_lift_pts', 'value': track_bias_lift},
        {'metric': 'pace_context_lift_pts', 'value': pace_context_lift},
        {'metric': 'best_horse_to_horse_explainer', 'value': best_horse_feature},
        {'metric': 'best_race_context_factor', 'value': best_context_feature},
        {'metric': 'future_v8_bias_candidates', 'value': '|'.join(future_candidates)},
        {'metric': 'verdict', 'value': verdict},
    ]
    write_csv(pd.DataFrame(summary_rows), OUT_SUMMARY.name)

    print('[BIAS_FACTOR_RELEVANCE_AUDIT_V1] COMPLETE')
    print(f'races_audited={len(detail)}')
    print(f'rank1_losses={len(losses)}')
    print(f'tj_pct={tj_pct}')
    print(f'barrier_pct={barrier_pct}')
    print(f'run_style_pct={run_style_pct}')
    print(f'condition_pct={condition_pct}')
    print(f'verdict={verdict}')
    print(f'wrote={OUT_DETAIL}')
    print(f'wrote={OUT_SUMMARY}')


if __name__ == '__main__':
    main()
