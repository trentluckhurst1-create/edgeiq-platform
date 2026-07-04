from pathlib import Path
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'

LIVE = DATA / 'edgeiq_live_runner_board_v1.csv'
TRAINER = DATA / 'edgeiq_trainer_factor_v1.csv'
JOCKEY = DATA / 'edgeiq_jockey_factor_v1.csv'
COMBO = DATA / 'edgeiq_trainer_jockey_combo_factor_v1.csv'
SEED = DATA / 'edgeiq_trainer_jockey_live_alias_seed_v1.csv'
V1_SUMMARY = DATA / 'edgeiq_live_trainer_jockey_factor_feed_v1_summary.csv'

OUT = DATA / 'edgeiq_live_trainer_jockey_factor_feed_v3.csv'
OUT_SUMMARY = DATA / 'edgeiq_live_trainer_jockey_factor_feed_v3_summary.csv'
OUT_UNMATCHED = DATA / 'edgeiq_live_trainer_jockey_factor_feed_v3_unmatched.csv'

TITLE_TOKENS = {'MS', 'MR', 'MRS', 'MISS'}
SUFFIX_TOKENS = {'JNR', 'JR', 'SNR', 'SR', 'II', 'III', 'IV'}
COMMON_AMBIGUOUS_SURNAMES = {
    'BATES', 'CARTWRIGHT', 'FIELD', 'HILL', 'JOHNSTONE', 'KELLY', 'MURPHY',
    'PAYNE', 'RYAN', 'SMITH', 'STANLEY', 'TAYLOR', 'THOMPSON', 'WALKER', 'WILLIAMS'
}


def norm_text(value):
    if pd.isna(value):
        return ''
    return str(value).strip().upper()



def clean_name(value):
    text = norm_text(value)
    text = text.replace('(LATE ALT)', ' ')
    text = re.sub(r'\(A[0-9.]*\/?[0-9A-Z.]*KG?\)', ' ', text)
    text = re.sub(r'\(A[0-9.]*\)', ' ', text)
    text = re.sub(r'\([^)]*\)', ' ', text)
    text = text.replace('&', ' ')
    text = text.replace(',', ' ')
    text = text.replace("'", ' ')
    text = re.sub(r'[^A-Z0-9 ]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    tokens = [token for token in text.split(' ') if token and token not in TITLE_TOKENS]
    return ' '.join(tokens)



def compact(value):
    return re.sub(r'[^A-Z0-9]+', '', norm_text(value))



def tokens_from_name(value):
    cleaned = clean_name(value)
    if not cleaned:
        return []
    return [token for token in cleaned.split(' ') if token]



def surname_key_from_tokens(tokens):
    if not tokens:
        return ''
    if len(tokens) >= 2 and tokens[-1] in SUFFIX_TOKENS:
        return compact(''.join(tokens[-2:]))
    return compact(tokens[-1])



def lead_tokens(tokens):
    if not tokens:
        return []
    if len(tokens) >= 2 and tokens[-1] in SUFFIX_TOKENS:
        return tokens[:-2]
    return tokens[:-1]



def first_initial_surname_key(tokens):
    lead = lead_tokens(tokens)
    surname_key = surname_key_from_tokens(tokens)
    if not lead or not surname_key:
        return ''
    return compact(lead[0][0] + surname_key)



def prepare_factor(df, entity_type):
    if entity_type == 'TRAINER':
        key_col = 'trainer_key'
        name_col = 'trainer'
    else:
        key_col = 'jockey_key'
        name_col = 'jockey'

    prepared = df.copy()
    prepared['key_norm'] = prepared[key_col].map(compact)
    prepared['name_clean'] = prepared[name_col].map(clean_name)
    prepared['name_compact'] = prepared['name_clean'].map(compact)
    prepared['surname_key'] = prepared[name_col].map(lambda value: surname_key_from_tokens(tokens_from_name(value)))
    return prepared



def load_seed(path):
    if not path.exists():
        return pd.DataFrame(columns=['entity_type', 'live_name', 'live_clean_key', 'factor_key', 'factor_name', 'reason'])
    seed = pd.read_csv(path, low_memory=False)
    for col in ['entity_type', 'live_name', 'live_clean_key', 'factor_key', 'factor_name', 'reason']:
        if col not in seed.columns:
            seed[col] = ''
    seed['entity_type'] = seed['entity_type'].map(norm_text)
    seed['live_clean_key_norm'] = seed['live_clean_key'].map(compact)
    seed['factor_key_norm'] = seed['factor_key'].map(compact)
    return seed



def build_indexes(prepared_df, entity_type):
    key_col = 'trainer_key' if entity_type == 'TRAINER' else 'jockey_key'
    by_key = {}
    by_name_compact = {}
    by_surname = {}

    for _, row in prepared_df.iterrows():
        row_dict = row.to_dict()
        key_norm = row_dict['key_norm']
        if key_norm and key_norm not in by_key:
            by_key[key_norm] = row_dict

        name_compact = row_dict['name_compact']
        if name_compact:
            by_name_compact.setdefault(name_compact, []).append(row_dict)

        surname_key = row_dict['surname_key']
        if surname_key:
            by_surname.setdefault(surname_key, []).append(row_dict)

    return key_col, by_key, by_name_compact, by_surname



def match_entity(live_name, entity_type, indexes, seed_df):
    key_col, by_key, by_name_compact, by_surname = indexes
    cleaned_name = clean_name(live_name)
    clean_key = compact(cleaned_name)
    tokens = tokens_from_name(live_name)
    surname_key = surname_key_from_tokens(tokens)
    generated_key = first_initial_surname_key(tokens)

    result = {
        'matched_row': None,
        'match_method': 'UNMATCHED',
        'cleaned_name': cleaned_name,
        'clean_key': clean_key,
        'generated_key': generated_key,
        'surname_key': surname_key,
        'seed_applied': 'NO',
    }

    if not cleaned_name:
        result['match_method'] = 'BLANK_LIVE_NAME'
        return result

    if clean_key in by_key:
        result['matched_row'] = by_key[clean_key]
        result['match_method'] = 'EXACT_KEY_MATCH'
        return result

    exact_name_rows = by_name_compact.get(clean_key, [])
    if len(exact_name_rows) == 1:
        result['matched_row'] = exact_name_rows[0]
        result['match_method'] = 'EXACT_COMPACT_NAME_MATCH'
        return result

    seed_match = seed_df[
        (seed_df['entity_type'] == entity_type) &
        (seed_df['live_clean_key_norm'] == clean_key)
    ]
    if len(seed_match) == 1:
        factor_key_norm = seed_match.iloc[0]['factor_key_norm']
        if factor_key_norm in by_key:
            result['matched_row'] = by_key[factor_key_norm]
            result['match_method'] = 'EXPLICIT_ALIAS_SEED'
            result['seed_applied'] = 'YES'
            return result

    if generated_key and generated_key in by_key:
        result['matched_row'] = by_key[generated_key]
        result['match_method'] = 'FIRST_INITIAL_SURNAME_EXACT'
        return result

    surname_rows = by_surname.get(surname_key, [])
    if (
        surname_key and
        surname_key not in COMMON_AMBIGUOUS_SURNAMES and
        len(surname_rows) == 1
    ):
        result['matched_row'] = surname_rows[0]
        result['match_method'] = 'UNIQUE_SURNAME_FALLBACK'
        return result

    return result



def combo_lookup_key(trainer_row, jockey_row):
    if not trainer_row or not jockey_row:
        return ''
    trainer_key = compact(trainer_row.get('trainer_key', ''))
    jockey_key = compact(jockey_row.get('jockey_key', ''))
    if not trainer_key or not jockey_key:
        return ''
    return compact(trainer_key + '|' + jockey_key)



def band_from_blend(score):
    if score >= 1.25:
        return 'ELITE'
    if score >= 0.50:
        return 'POSITIVE'
    if score <= -1.25:
        return 'POOR'
    if score <= -0.50:
        return 'NEGATIVE'
    return 'NEUTRAL'



def load_v1_summary(path):
    if not path.exists():
        return {}
    summary_df = pd.read_csv(path)
    if 'metric' not in summary_df.columns or 'value' not in summary_df.columns:
        return {}
    return dict(zip(summary_df['metric'], summary_df['value']))



def main():
    required = [LIVE, TRAINER, JOCKEY, COMBO, SEED]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f'Missing required files: {missing}')

    live = pd.read_csv(LIVE, low_memory=False)
    trainer = prepare_factor(pd.read_csv(TRAINER, low_memory=False), 'TRAINER')
    jockey = prepare_factor(pd.read_csv(JOCKEY, low_memory=False), 'JOCKEY')
    combo = pd.read_csv(COMBO, low_memory=False)
    seed = load_seed(SEED)
    v1_summary = load_v1_summary(V1_SUMMARY)

    trainer_indexes = build_indexes(trainer, 'TRAINER')
    jockey_indexes = build_indexes(jockey, 'JOCKEY')

    combo_lookup = {}
    for _, row in combo.iterrows():
        combo_key = compact(row.get('trainer_jockey_key', ''))
        if combo_key:
            combo_lookup[combo_key] = row.to_dict()

    rows = []
    for _, live_row in live.iterrows():
        base = live_row.to_dict()

        trainer_match = match_entity(live_row.get('trainer', ''), 'TRAINER', trainer_indexes, seed)
        jockey_match = match_entity(live_row.get('jockey', ''), 'JOCKEY', jockey_indexes, seed)

        trainer_row = trainer_match['matched_row']
        jockey_row = jockey_match['matched_row']
        combo_key = combo_lookup_key(trainer_row, jockey_row)
        combo_row = combo_lookup.get(combo_key)

        trainer_score = float(trainer_row.get('trainer_factor_score_v1', 0)) if trainer_row else 0.0
        jockey_score = float(jockey_row.get('jockey_factor_score_v1', 0)) if jockey_row else 0.0
        combo_score = float(combo_row.get('combo_factor_score_v1', 0)) if combo_row else 0.0
        blend_score = round((trainer_score * 0.35) + (jockey_score * 0.45) + (combo_score * 0.20), 3)
        blend_band = band_from_blend(blend_score)

        if trainer_row and jockey_row and combo_row:
            verdict = 'COMPLETE'
        elif trainer_row and jockey_row:
            verdict = 'TRAINER_JOCKEY_ONLY'
        elif trainer_row or jockey_row:
            verdict = 'PARTIAL'
        else:
            verdict = 'UNMATCHED'

        base.update({
            'trainer_live_clean_key_v3': trainer_match['clean_key'],
            'jockey_live_clean_key_v3': jockey_match['clean_key'],
            'trainer_generated_key_v3': trainer_match['generated_key'],
            'jockey_generated_key_v3': jockey_match['generated_key'],
            'trainer_factor_key_matched_v3': trainer_row.get('trainer_key', '') if trainer_row else '',
            'jockey_factor_key_matched_v3': jockey_row.get('jockey_key', '') if jockey_row else '',
            'combo_factor_key_matched_v3': combo_row.get('trainer_jockey_key', '') if combo_row else '',
            'trainer_factor_matched_v3': 'YES' if trainer_row else 'NO',
            'jockey_factor_matched_v3': 'YES' if jockey_row else 'NO',
            'combo_factor_matched_v3': 'YES' if combo_row else 'NO',
            'trainer_match_method_v3': trainer_match['match_method'],
            'jockey_match_method_v3': jockey_match['match_method'],
            'trainer_seed_applied_v3': trainer_match['seed_applied'],
            'jockey_seed_applied_v3': jockey_match['seed_applied'],
            'trainer_factor_band_v1': trainer_row.get('trainer_factor_band_v1', 'UNKNOWN') if trainer_row else 'UNKNOWN',
            'trainer_factor_score_v1': trainer_score,
            'trainer_factor_starts_v1': trainer_row.get('trainer_starts_v1', '') if trainer_row else '',
            'trainer_win_pct_v1': trainer_row.get('trainer_win_pct_v1', '') if trainer_row else '',
            'trainer_place_pct_v1': trainer_row.get('trainer_place_pct_v1', '') if trainer_row else '',
            'jockey_factor_band_v1': jockey_row.get('jockey_factor_band_v1', 'UNKNOWN') if jockey_row else 'UNKNOWN',
            'jockey_factor_score_v1': jockey_score,
            'jockey_factor_starts_v1': jockey_row.get('jockey_starts_v1', '') if jockey_row else '',
            'jockey_win_pct_v1': jockey_row.get('jockey_win_pct_v1', '') if jockey_row else '',
            'jockey_place_pct_v1': jockey_row.get('jockey_place_pct_v1', '') if jockey_row else '',
            'combo_factor_band_v1': combo_row.get('combo_factor_band_v1', 'UNKNOWN') if combo_row else 'UNKNOWN',
            'combo_factor_score_v1': combo_score,
            'combo_factor_starts_v1': combo_row.get('combo_starts_v1', '') if combo_row else '',
            'combo_win_pct_v1': combo_row.get('combo_win_pct_v1', '') if combo_row else '',
            'combo_place_pct_v1': combo_row.get('combo_place_pct_v1', '') if combo_row else '',
            'trainer_jockey_blend_score_v3': blend_score,
            'trainer_jockey_blend_band_v3': blend_band,
            'tj_edge_label_v3': 'TJ Edge: ' + blend_band,
            'tj_factor_verdict_v3': verdict,
            'observation_only_v3': 'YES',
            'price_or_execution_changed': 'NO',
        })
        rows.append(base)

    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)

    unmatched = out[out['tj_factor_verdict_v3'] != 'COMPLETE'].copy()
    unmatched.to_csv(OUT_UNMATCHED, index=False)

    live_rows = len(out)
    trainer_matched = int((out['trainer_factor_matched_v3'] == 'YES').sum())
    jockey_matched = int((out['jockey_factor_matched_v3'] == 'YES').sum())
    combo_matched = int((out['combo_factor_matched_v3'] == 'YES').sum())
    complete_rows = int((out['tj_factor_verdict_v3'] == 'COMPLETE').sum())
    partial_or_unmatched_rows = int(live_rows - complete_rows)
    jockey_nonblank_rows = int((out['jockey'].fillna('').astype(str).str.strip() != '').sum())
    jockey_matched_nonblank = int(((out['jockey'].fillna('').astype(str).str.strip() != '') & (out['jockey_factor_matched_v3'] == 'YES')).sum())

    trainer_match_pct = round((trainer_matched / live_rows) * 100, 2) if live_rows else 0.0
    jockey_match_pct = round((jockey_matched / live_rows) * 100, 2) if live_rows else 0.0
    combo_match_pct = round((combo_matched / live_rows) * 100, 2) if live_rows else 0.0
    complete_rows_pct = round((complete_rows / live_rows) * 100, 2) if live_rows else 0.0
    jockey_match_pct_ex_blank = round((jockey_matched_nonblank / jockey_nonblank_rows) * 100, 2) if jockey_nonblank_rows else 0.0

    v1_trainer = float(v1_summary.get('trainer_match_pct', 0) or 0)
    v1_jockey = float(v1_summary.get('jockey_match_pct', 0) or 0)
    v1_combo = float(v1_summary.get('combo_match_pct', 0) or 0)
    v1_complete = int(float(v1_summary.get('complete_rows', 0) or 0))

    beats_v1_trainer = 'YES' if trainer_match_pct > v1_trainer else 'NO'
    beats_v1_jockey = 'YES' if jockey_match_pct > v1_jockey else 'NO'
    beats_v1_combo = 'YES' if combo_match_pct > v1_combo else 'NO'
    beats_v1_complete = 'YES' if complete_rows > v1_complete else 'NO'
    beats_v1_overall = 'YES' if all(flag == 'YES' for flag in [beats_v1_trainer, beats_v1_jockey, beats_v1_combo, beats_v1_complete]) else 'NO'
    recommended_live_version = 'V3' if beats_v1_overall == 'YES' else 'KEEP_V1'

    summary_rows = [
        {'metric': 'source_file_used', 'value': LIVE.name},
        {'metric': 'alias_seed_file_used', 'value': SEED.name},
        {'metric': 'live_rows', 'value': live_rows},
        {'metric': 'trainer_matched', 'value': trainer_matched},
        {'metric': 'trainer_match_pct', 'value': trainer_match_pct},
        {'metric': 'jockey_matched', 'value': jockey_matched},
        {'metric': 'jockey_match_pct', 'value': jockey_match_pct},
        {'metric': 'jockey_nonblank_rows', 'value': jockey_nonblank_rows},
        {'metric': 'jockey_matched_nonblank', 'value': jockey_matched_nonblank},
        {'metric': 'jockey_match_pct_ex_blank', 'value': jockey_match_pct_ex_blank},
        {'metric': 'combo_matched', 'value': combo_matched},
        {'metric': 'combo_match_pct', 'value': combo_match_pct},
        {'metric': 'complete_rows', 'value': complete_rows},
        {'metric': 'complete_rows_pct', 'value': complete_rows_pct},
        {'metric': 'partial_or_unmatched_rows', 'value': partial_or_unmatched_rows},
        {'metric': 'trainer_seed_applied_rows', 'value': int((out['trainer_seed_applied_v3'] == 'YES').sum())},
        {'metric': 'jockey_seed_applied_rows', 'value': int((out['jockey_seed_applied_v3'] == 'YES').sum())},
        {'metric': 'observation_only', 'value': 'YES'},
        {'metric': 'price_or_execution_changed', 'value': 'NO'},
        {'metric': 'v1_trainer_match_pct_reference', 'value': v1_trainer},
        {'metric': 'v1_jockey_match_pct_reference', 'value': v1_jockey},
        {'metric': 'v1_combo_match_pct_reference', 'value': v1_combo},
        {'metric': 'v1_complete_rows_reference', 'value': v1_complete},
        {'metric': 'beats_v1_trainer', 'value': beats_v1_trainer},
        {'metric': 'beats_v1_jockey', 'value': beats_v1_jockey},
        {'metric': 'beats_v1_combo', 'value': beats_v1_combo},
        {'metric': 'beats_v1_complete_rows', 'value': beats_v1_complete},
        {'metric': 'beats_v1_overall', 'value': beats_v1_overall},
        {'metric': 'recommended_live_version', 'value': recommended_live_version},
    ]
    pd.DataFrame(summary_rows).to_csv(OUT_SUMMARY, index=False)

    print('[LIVE_TRAINER_JOCKEY_FACTOR_FEED_V3] COMPLETE')
    print(f'source_file_used={LIVE.name}')
    print(f'live_rows={live_rows}')
    print(f'trainer_match_pct={trainer_match_pct}')
    print(f'jockey_match_pct={jockey_match_pct}')
    print(f'jockey_match_pct_ex_blank={jockey_match_pct_ex_blank}')
    print(f'combo_match_pct={combo_match_pct}')
    print(f'complete_rows={complete_rows}')
    print(f'beats_v1_overall={beats_v1_overall}')
    print(f'recommended_live_version={recommended_live_version}')
    print(f'wrote={OUT}')
    print(f'wrote={OUT_SUMMARY}')
    print(f'wrote={OUT_UNMATCHED}')


if __name__ == '__main__':
    main()


