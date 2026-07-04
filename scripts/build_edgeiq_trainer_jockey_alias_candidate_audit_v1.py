from pathlib import Path
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'

LIVE = DATA / 'edgeiq_live_runner_board_v1.csv'
TRAINER = DATA / 'edgeiq_trainer_factor_v1.csv'
JOCKEY = DATA / 'edgeiq_jockey_factor_v1.csv'
ALIAS_MAP = DATA / 'edgeiq_trainer_jockey_alias_map_v1.csv'

OUT_TRAINER = DATA / 'edgeiq_live_trainer_alias_candidates_v1.csv'
OUT_JOCKEY = DATA / 'edgeiq_live_jockey_alias_candidates_v1.csv'
OUT_SUMMARY = DATA / 'edgeiq_live_trainer_jockey_alias_candidate_summary_v1.csv'

TITLE_TOKENS = {'MS', 'MR', 'MRS', 'MISS'}
SUFFIX_TOKENS = {'JNR', 'JR', 'SNR', 'SR', 'II', 'III', 'IV'}


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



def exact_compact_key_from_tokens(tokens):
    return compact(''.join(tokens))



def first_initial_surname_key_from_tokens(tokens):
    lead = lead_tokens(tokens)
    surname_key = surname_key_from_tokens(tokens)
    if not lead or not surname_key:
        return ''
    return compact(lead[0][0] + surname_key)



def first_middle_initial_surname_key_from_tokens(tokens):
    lead = lead_tokens(tokens)
    surname_key = surname_key_from_tokens(tokens)
    if len(lead) < 2 or not surname_key:
        return ''
    return compact(lead[0][0] + lead[1][0] + surname_key)



def all_initials_surname_key_from_tokens(tokens):
    lead = lead_tokens(tokens)
    surname_key = surname_key_from_tokens(tokens)
    if not lead or not surname_key:
        return ''
    initials = ''.join(token[0] for token in lead if token)
    return compact(initials + surname_key)



def first_name_surname_key_from_tokens(tokens):
    lead = lead_tokens(tokens)
    surname_key = surname_key_from_tokens(tokens)
    if not lead or not surname_key:
        return ''
    return compact(lead[0] + surname_key)



def factor_columns(entity_type):
    if entity_type == 'TRAINER':
        return 'trainer_key', 'trainer'
    return 'jockey_key', 'jockey'



def prepare_factor(df, entity_type):
    key_col, name_col = factor_columns(entity_type)
    prepared = df.copy()
    prepared['factor_key_norm'] = prepared[key_col].map(compact)
    prepared['factor_name_norm'] = prepared[name_col].map(norm_text)
    prepared['factor_name_clean'] = prepared[name_col].map(clean_name)
    prepared['factor_name_compact'] = prepared['factor_name_clean'].map(compact)
    prepared['factor_tokens'] = prepared['factor_name_clean'].map(tokens_from_name)
    prepared['factor_surname_key'] = prepared['factor_tokens'].map(surname_key_from_tokens)
    prepared['factor_display_key'] = prepared[key_col]
    prepared['factor_display_name'] = prepared[name_col]
    return prepared



def prepare_alias_map(path):
    if not path.exists():
        return pd.DataFrame()

    alias_map = pd.read_csv(path, low_memory=False)
    if alias_map.empty:
        return alias_map

    alias_map = alias_map.copy()
    for col in ['original_name', 'original_key', 'canonical_name', 'canonical_key', 'entity_type']:
        if col not in alias_map.columns:
            alias_map[col] = ''
    alias_map['entity_type'] = alias_map['entity_type'].map(norm_text)
    alias_map['original_name_clean'] = alias_map['original_name'].map(clean_name)
    alias_map['original_key_norm'] = alias_map['original_key'].map(compact)
    alias_map['canonical_key_norm'] = alias_map['canonical_key'].map(compact)
    return alias_map



def generate_candidates(live_name, factor_prepared, alias_prepared, entity_type):
    tokens = tokens_from_name(live_name)
    cleaned_live_name = clean_name(live_name)
    exact_compact_key = exact_compact_key_from_tokens(tokens)
    first_initial_surname_key = first_initial_surname_key_from_tokens(tokens)
    first_middle_initial_surname_key = first_middle_initial_surname_key_from_tokens(tokens)
    all_initials_surname_key = all_initials_surname_key_from_tokens(tokens)
    first_name_surname_key = first_name_surname_key_from_tokens(tokens)
    surname_key = surname_key_from_tokens(tokens)

    variant_map = {
        'EXACT_COMPACT_KEY': exact_compact_key,
        'FIRST_INITIAL_SURNAME_KEY': first_initial_surname_key,
        'FIRST_MIDDLE_INITIAL_SURNAME_KEY': first_middle_initial_surname_key,
        'ALL_INITIALS_SURNAME_KEY': all_initials_surname_key,
        'FIRST_NAME_SURNAME_KEY': first_name_surname_key,
    }

    candidate_map = {}

    def add_candidate(row, method):
        factor_key = row['factor_display_key']
        if factor_key not in candidate_map:
            candidate_map[factor_key] = {
                'factor_key': factor_key,
                'factor_name': row['factor_display_name'],
                'methods': []
            }
        if method not in candidate_map[factor_key]['methods']:
            candidate_map[factor_key]['methods'].append(method)

    for _, row in factor_prepared.iterrows():
        methods = []
        key_norm = row['factor_key_norm']
        name_compact = row['factor_name_compact']
        factor_surname_key = row['factor_surname_key']

        if exact_compact_key and key_norm == exact_compact_key:
            methods.append('EXACT_COMPACT_KEY_MATCH')
        if exact_compact_key and name_compact == exact_compact_key:
            methods.append('EXACT_COMPACT_NAME_MATCH')
        if first_initial_surname_key and key_norm == first_initial_surname_key:
            methods.append('FIRST_INITIAL_SURNAME_KEY_MATCH')
        if first_middle_initial_surname_key and key_norm == first_middle_initial_surname_key:
            methods.append('FIRST_MIDDLE_INITIAL_SURNAME_KEY_MATCH')
        if all_initials_surname_key and key_norm == all_initials_surname_key:
            methods.append('ALL_INITIALS_SURNAME_KEY_MATCH')
        if first_name_surname_key and key_norm == first_name_surname_key:
            methods.append('FIRST_NAME_SURNAME_KEY_MATCH')
        if surname_key and factor_surname_key == surname_key:
            methods.append('SURNAME_GROUP_MATCH')
        if surname_key and key_norm.endswith(surname_key) and 'SURNAME_GROUP_MATCH' not in methods:
            methods.append('SURNAME_SUFFIX_MATCH')

        if methods:
            for method in methods:
                add_candidate(row, method)

    if not alias_prepared.empty and exact_compact_key:
        alias_rows = alias_prepared[
            (alias_prepared['entity_type'] == entity_type) &
            (
                (alias_prepared['original_key_norm'] == exact_compact_key) |
                (alias_prepared['original_name_clean'].map(compact) == exact_compact_key)
            )
        ]
        for _, alias_row in alias_rows.iterrows():
            canonical_key = alias_row.get('canonical_key_norm', '')
            matched = factor_prepared[factor_prepared['factor_key_norm'] == canonical_key]
            for _, row in matched.iterrows():
                add_candidate(row, 'EXISTING_ALIAS_MAP_CANDIDATE')

    candidates = list(candidate_map.values())

    suggested_factor_key = ''
    suggested_factor_name = ''
    suggested_match_method = ''
    safe_to_auto_apply = 'NO'

    if candidates:
        precedence = [
            'EXACT_COMPACT_KEY_MATCH',
            'EXACT_COMPACT_NAME_MATCH',
            'FIRST_MIDDLE_INITIAL_SURNAME_KEY_MATCH',
            'ALL_INITIALS_SURNAME_KEY_MATCH',
            'FIRST_INITIAL_SURNAME_KEY_MATCH',
            'FIRST_NAME_SURNAME_KEY_MATCH',
            'EXISTING_ALIAS_MAP_CANDIDATE',
            'SURNAME_GROUP_MATCH',
            'SURNAME_SUFFIX_MATCH',
        ]

        for method in precedence:
            method_candidates = [candidate for candidate in candidates if method in candidate['methods']]
            if len(method_candidates) == 1:
                chosen = method_candidates[0]
                suggested_factor_key = chosen['factor_key']
                suggested_factor_name = chosen['factor_name']
                suggested_match_method = method

                if method in {
                    'EXACT_COMPACT_KEY_MATCH',
                    'EXACT_COMPACT_NAME_MATCH',
                    'FIRST_MIDDLE_INITIAL_SURNAME_KEY_MATCH',
                    'ALL_INITIALS_SURNAME_KEY_MATCH',
                    'FIRST_INITIAL_SURNAME_KEY_MATCH',
                    'FIRST_NAME_SURNAME_KEY_MATCH',
                    'EXISTING_ALIAS_MAP_CANDIDATE',
                }:
                    safe_to_auto_apply = 'YES'
                else:
                    lead = lead_tokens(tokens)
                    first_initial = lead[0][0] if lead else ''
                    factor_key_norm = compact(suggested_factor_key)
                    if first_initial and factor_key_norm.startswith(first_initial):
                        suggested_match_method = method + '_WITH_INITIAL_SUPPORT'
                        safe_to_auto_apply = 'YES'
                    else:
                        safe_to_auto_apply = 'NO'
                break

    return {
        'cleaned_live_name': cleaned_live_name,
        'exact_compact_key': exact_compact_key,
        'first_initial_surname_key': first_initial_surname_key,
        'first_middle_initial_surname_key': first_middle_initial_surname_key,
        'all_initials_surname_key': all_initials_surname_key,
        'surname_key': surname_key,
        'candidate_factor_keys': ' | '.join(candidate['factor_key'] for candidate in candidates),
        'candidate_factor_names': ' | '.join(candidate['factor_name'] for candidate in candidates),
        'candidate_match_methods': ' | '.join(
            f"{candidate['factor_key']}=>{','.join(candidate['methods'])}" for candidate in candidates
        ),
        'candidate_count': len(candidates),
        'suggested_factor_key': suggested_factor_key,
        'suggested_factor_name': suggested_factor_name,
        'suggested_match_method': suggested_match_method,
        'safe_to_auto_apply': safe_to_auto_apply,
    }



def build_entity_audit(live_df, factor_df, entity_type, live_column, horse_column, alias_prepared):
    factor_prepared = prepare_factor(factor_df, entity_type)
    grouped = (
        live_df.assign(live_name=live_df[live_column].fillna(''))
        .groupby('live_name', dropna=False)
        .agg(
            live_rows=('live_name', 'size'),
            sample_horses=(horse_column, lambda s: ' | '.join(pd.Series(s).fillna('').astype(str).str.strip().replace('', pd.NA).dropna().drop_duplicates().head(5)))
        )
        .reset_index()
        .rename(columns={'live_name': 'live_name'})
    )

    rows = []
    for _, row in grouped.iterrows():
        live_name = row['live_name']
        candidate_payload = generate_candidates(live_name, factor_prepared, alias_prepared, entity_type)
        rows.append({
            'entity_type': entity_type,
            'live_name': live_name,
            'cleaned_live_name': candidate_payload['cleaned_live_name'],
            'live_rows': int(row['live_rows']),
            'sample_horses': row['sample_horses'],
            'exact_compact_key': candidate_payload['exact_compact_key'],
            'first_initial_surname_key': candidate_payload['first_initial_surname_key'],
            'first_middle_initial_surname_key': candidate_payload['first_middle_initial_surname_key'],
            'all_initials_surname_key': candidate_payload['all_initials_surname_key'],
            'surname_key': candidate_payload['surname_key'],
            'candidate_factor_keys': candidate_payload['candidate_factor_keys'],
            'candidate_factor_names': candidate_payload['candidate_factor_names'],
            'candidate_match_methods': candidate_payload['candidate_match_methods'],
            'candidate_count': int(candidate_payload['candidate_count']),
            'suggested_factor_key': candidate_payload['suggested_factor_key'],
            'suggested_factor_name': candidate_payload['suggested_factor_name'],
            'suggested_match_method': candidate_payload['suggested_match_method'],
            'safe_to_auto_apply': candidate_payload['safe_to_auto_apply'],
        })

    out = pd.DataFrame(rows)
    sort_columns = ['safe_to_auto_apply', 'candidate_count', 'live_rows', 'live_name']
    out = out.sort_values(sort_columns, ascending=[False, True, False, True]).reset_index(drop=True)
    return out



def summarise(entity_df, entity_type):
    total_unique = len(entity_df)
    total_rows = int(entity_df['live_rows'].sum()) if not entity_df.empty else 0
    blank_names = int((entity_df['cleaned_live_name'] == '').sum()) if not entity_df.empty else 0
    safe_unique = int((entity_df['safe_to_auto_apply'] == 'YES').sum()) if not entity_df.empty else 0
    safe_rows = int(entity_df.loc[entity_df['safe_to_auto_apply'] == 'YES', 'live_rows'].sum()) if not entity_df.empty else 0
    candidate_unique = int((entity_df['candidate_count'] > 0).sum()) if not entity_df.empty else 0
    ambiguous_unique = int(((entity_df['candidate_count'] > 1) & (entity_df['safe_to_auto_apply'] == 'NO')).sum()) if not entity_df.empty else 0
    unmatched_unique = int((entity_df['candidate_count'] == 0).sum()) if not entity_df.empty else 0

    return [
        {'entity_type': entity_type, 'metric': 'unique_live_names', 'value': total_unique},
        {'entity_type': entity_type, 'metric': 'live_rows', 'value': total_rows},
        {'entity_type': entity_type, 'metric': 'blank_live_names', 'value': blank_names},
        {'entity_type': entity_type, 'metric': 'rows_with_candidates_unique_names', 'value': candidate_unique},
        {'entity_type': entity_type, 'metric': 'safe_to_auto_apply_unique_names', 'value': safe_unique},
        {'entity_type': entity_type, 'metric': 'safe_to_auto_apply_live_rows', 'value': safe_rows},
        {'entity_type': entity_type, 'metric': 'ambiguous_unique_names', 'value': ambiguous_unique},
        {'entity_type': entity_type, 'metric': 'unmatched_unique_names', 'value': unmatched_unique},
    ]



def main():
    required = [LIVE, TRAINER, JOCKEY]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f'Missing required files: {missing}')

    live = pd.read_csv(LIVE, low_memory=False)
    trainer = pd.read_csv(TRAINER, low_memory=False)
    jockey = pd.read_csv(JOCKEY, low_memory=False)
    alias_prepared = prepare_alias_map(ALIAS_MAP)

    trainer_audit = build_entity_audit(live, trainer, 'TRAINER', 'trainer', 'horse', alias_prepared)
    jockey_audit = build_entity_audit(live, jockey, 'JOCKEY', 'jockey', 'horse', alias_prepared)

    trainer_audit.to_csv(OUT_TRAINER, index=False)
    jockey_audit.to_csv(OUT_JOCKEY, index=False)

    summary_rows = []
    summary_rows.extend(summarise(trainer_audit, 'TRAINER'))
    summary_rows.extend(summarise(jockey_audit, 'JOCKEY'))
    summary_rows.append({'entity_type': 'GLOBAL', 'metric': 'live_source_file', 'value': LIVE.name})
    summary_rows.append({'entity_type': 'GLOBAL', 'metric': 'alias_map_loaded', 'value': 'YES' if ALIAS_MAP.exists() else 'NO'})

    pd.DataFrame(summary_rows).to_csv(OUT_SUMMARY, index=False)

    print('[TRAINER_JOCKEY_ALIAS_CANDIDATE_AUDIT_V1] COMPLETE')
    print(f'trainer_unique_live_names={len(trainer_audit)}')
    print(f'jockey_unique_live_names={len(jockey_audit)}')
    print(f'trainer_safe_to_auto_apply={int((trainer_audit["safe_to_auto_apply"] == "YES").sum())}')
    print(f'jockey_safe_to_auto_apply={int((jockey_audit["safe_to_auto_apply"] == "YES").sum())}')
    print(f'wrote={OUT_TRAINER}')
    print(f'wrote={OUT_JOCKEY}')
    print(f'wrote={OUT_SUMMARY}')


if __name__ == '__main__':
    main()
