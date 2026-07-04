from pathlib import Path
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'

TERMINAL = DATA / 'edgeiq_live_terminal_feed_v1.csv'
RUNNER_BOARD = DATA / 'edgeiq_live_runner_board_v1.csv'

OUT = DATA / 'edgeiq_blank_jockey_source_audit_v1.csv'
OUT_SUMMARY = DATA / 'edgeiq_blank_jockey_source_audit_summary_v1.csv'

VIC_TRACKS = {
    'CASTERTON', 'FLEMINGTON', 'SWAN HILL', 'HORSHAM', 'CAULFIELD', 'MOE', 'PAKENHAM',
    'SALE', 'BALLARAT', 'SANDOWN', 'BENDIGO', 'CRANBOURNE', 'GEELONG', 'WARRNAMBOOL',
    'MORNINGTON', 'TERANG', 'WODONGA', 'MILDURA', 'STAWELL', 'ECHUCA', 'ARARAT',
    'COLAC', 'KYNETON', 'TRARALGON', 'SEYMOUR', 'WANGARATTA', 'YARRA VALLEY', 'PAKENHAM SYNTHETIC'
}


def norm_text(value):
    if pd.isna(value):
        return ''
    return str(value).strip().upper()



def clean_jockey_text(value):
    text = norm_text(value)
    text = text.replace('(LATE ALT)', ' ')
    text = re.sub(r'\(A[0-9.]*\/?[0-9A-Z.]*KG?\)', ' ', text)
    text = re.sub(r'\(A[0-9.]*\)', ' ', text)
    text = re.sub(r'\([^)]*\)', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text



def compact(value):
    return re.sub(r'[^A-Z0-9]+', '', norm_text(value))



def safe_string(value):
    if pd.isna(value):
        return ''
    return str(value).strip()



def first_present(row, columns):
    for column in columns:
        if column in row and safe_string(row.get(column, '')):
            return safe_string(row.get(column, ''))
    return ''



def normalize_terminal(df):
    rows = []
    for _, row in df.iterrows():
        meeting_date = first_present(row, ['race_date', 'date'])
        track = first_present(row, ['track'])
        race_no = first_present(row, ['race_no', 'race_number'])
        horse = first_present(row, ['horse'])
        horse_key = first_present(row, ['horse_key']) or compact(horse)
        state = first_present(row, ['state'])
        trainer = first_present(row, ['trainer'])
        jockey = first_present(row, ['jockey'])
        cleaned_jockey = clean_jockey_text(jockey)
        rows.append({
            'source_file_v1': TERMINAL.name,
            'source_role_v1': 'UPSTREAM_TERMINAL',
            'meeting_date': meeting_date,
            'state': state,
            'track': track,
            'race_no': race_no,
            'horse': horse,
            'horse_key_v1': horse_key,
            'trainer': trainer,
            'jockey': jockey,
            'cleaned_jockey_v1': cleaned_jockey,
            'blank_jockey_flag_v1': 'YES' if cleaned_jockey == '' else 'NO',
            'source_url': first_present(row, ['source_url']),
            'scraped_at': first_present(row, ['scraped_at']),
            'final_fields_last_published': first_present(row, ['final_fields_last_published']),
            'riders_must_be_declared_before': first_present(row, ['riders_must_be_declared_before']),
        })
    out = pd.DataFrame(rows)
    out['join_key_v1'] = out.apply(lambda r: f"{r['meeting_date']}|{compact(r['track'])}|R{r['race_no']}|{compact(r['horse_key_v1'])}", axis=1)
    out['is_victoria_v1'] = out.apply(lambda r: 'YES' if norm_text(r['state']) == 'VIC' or norm_text(r['track']) in VIC_TRACKS else 'NO', axis=1)
    return out



def normalize_runner_board(df):
    rows = []
    for _, row in df.iterrows():
        meeting_date = first_present(row, ['race_date', 'date'])
        track = first_present(row, ['track'])
        race_no = first_present(row, ['race_no', 'race_number'])
        horse = first_present(row, ['horse'])
        horse_key = first_present(row, ['horse_canon', 'horse_key']) or compact(horse)
        trainer = first_present(row, ['trainer'])
        jockey = first_present(row, ['jockey'])
        cleaned_jockey = clean_jockey_text(jockey)
        rows.append({
            'source_file_v1': RUNNER_BOARD.name,
            'source_role_v1': 'DOWNSTREAM_RUNNER_BOARD',
            'meeting_date': meeting_date,
            'state': 'VIC',
            'track': track,
            'race_no': race_no,
            'horse': horse,
            'horse_key_v1': horse_key,
            'trainer': trainer,
            'jockey': jockey,
            'cleaned_jockey_v1': cleaned_jockey,
            'blank_jockey_flag_v1': 'YES' if cleaned_jockey == '' else 'NO',
            'source_url': '',
            'scraped_at': '',
            'final_fields_last_published': '',
            'riders_must_be_declared_before': '',
        })
    out = pd.DataFrame(rows)
    out['join_key_v1'] = out.apply(lambda r: f"{r['meeting_date']}|{compact(r['track'])}|R{r['race_no']}|{compact(r['horse_key_v1'])}", axis=1)
    out['is_victoria_v1'] = 'YES'
    return out



def make_presence_map(df, blank_column):
    if df.empty:
        return {}
    grouped = df.groupby('join_key_v1')[blank_column].apply(lambda s: 'YES' if (s == 'YES').any() else 'NO')
    return grouped.to_dict()



def main():
    required = [TERMINAL, RUNNER_BOARD]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f'Missing required files: {missing}')

    terminal = normalize_terminal(pd.read_csv(TERMINAL, low_memory=False))
    runner_board = normalize_runner_board(pd.read_csv(RUNNER_BOARD, low_memory=False))

    upstream_blank_map = make_presence_map(terminal, 'blank_jockey_flag_v1')
    downstream_blank_map = make_presence_map(runner_board, 'blank_jockey_flag_v1')

    blank_rows = []
    for source_df in [terminal, runner_board]:
        for _, row in source_df[source_df['blank_jockey_flag_v1'] == 'YES'].iterrows():
            join_key = row['join_key_v1']
            blank_rows.append({
                'source_file_v1': row['source_file_v1'],
                'source_role_v1': row['source_role_v1'],
                'meeting_date': row['meeting_date'],
                'state': row['state'],
                'track': row['track'],
                'race_no': row['race_no'],
                'horse': row['horse'],
                'horse_key_v1': row['horse_key_v1'],
                'trainer': row['trainer'],
                'jockey': row['jockey'],
                'cleaned_jockey_v1': row['cleaned_jockey_v1'],
                'blank_jockey_flag_v1': row['blank_jockey_flag_v1'],
                'source_url': row['source_url'],
                'scraped_at': row['scraped_at'],
                'final_fields_last_published': row['final_fields_last_published'],
                'riders_must_be_declared_before': row['riders_must_be_declared_before'],
                'is_victoria_v1': row['is_victoria_v1'],
                'join_key_v1': join_key,
                'blank_exists_upstream_v1': upstream_blank_map.get(join_key, 'NO'),
                'blank_exists_downstream_v1': downstream_blank_map.get(join_key, 'NO'),
            })

    out = pd.DataFrame(blank_rows)
    if not out.empty:
        out = out.sort_values(['source_file_v1', 'meeting_date', 'track', 'race_no', 'horse']).reset_index(drop=True)
    out.to_csv(OUT, index=False)

    upstream_blank_join_keys = {key for key, value in upstream_blank_map.items() if value == 'YES'}
    downstream_blank_join_keys = {key for key, value in downstream_blank_map.items() if value == 'YES'}

    summary_rows = [
        {'section': 'OVERVIEW', 'metric': 'terminal_rows', 'value': len(terminal), 'source_file': TERMINAL.name, 'track': '', 'race_no': '', 'source_url': ''},
        {'section': 'OVERVIEW', 'metric': 'runner_board_rows', 'value': len(runner_board), 'source_file': RUNNER_BOARD.name, 'track': '', 'race_no': '', 'source_url': ''},
        {'section': 'OVERVIEW', 'metric': 'terminal_blank_rows', 'value': int((terminal['blank_jockey_flag_v1'] == 'YES').sum()), 'source_file': TERMINAL.name, 'track': '', 'race_no': '', 'source_url': ''},
        {'section': 'OVERVIEW', 'metric': 'runner_board_blank_rows', 'value': int((runner_board['blank_jockey_flag_v1'] == 'YES').sum()), 'source_file': RUNNER_BOARD.name, 'track': '', 'race_no': '', 'source_url': ''},
        {'section': 'OVERVIEW', 'metric': 'terminal_blank_rows_victoria_only', 'value': int(((terminal['blank_jockey_flag_v1'] == 'YES') & (terminal['is_victoria_v1'] == 'YES')).sum()), 'source_file': TERMINAL.name, 'track': '', 'race_no': '', 'source_url': ''},
        {'section': 'OVERVIEW', 'metric': 'runner_board_blank_rows_victoria_only', 'value': int(((runner_board['blank_jockey_flag_v1'] == 'YES') & (runner_board['is_victoria_v1'] == 'YES')).sum()), 'source_file': RUNNER_BOARD.name, 'track': '', 'race_no': '', 'source_url': ''},
        {'section': 'OVERVIEW', 'metric': 'blank_join_keys_upstream_only', 'value': len(upstream_blank_join_keys - downstream_blank_join_keys), 'source_file': '', 'track': '', 'race_no': '', 'source_url': ''},
        {'section': 'OVERVIEW', 'metric': 'blank_join_keys_downstream_only', 'value': len(downstream_blank_join_keys - upstream_blank_join_keys), 'source_file': '', 'track': '', 'race_no': '', 'source_url': ''},
        {'section': 'OVERVIEW', 'metric': 'blank_join_keys_both_upstream_and_downstream', 'value': len(upstream_blank_join_keys & downstream_blank_join_keys), 'source_file': '', 'track': '', 'race_no': '', 'source_url': ''},
    ]

    for source_df, source_name in [(terminal, TERMINAL.name), (runner_board, RUNNER_BOARD.name)]:
        source_blank = source_df[source_df['blank_jockey_flag_v1'] == 'YES']
        summary_rows.append({
            'section': 'BY_SOURCE_FILE',
            'metric': 'blank_rows',
            'value': len(source_blank),
            'source_file': source_name,
            'track': '',
            'race_no': '',
            'source_url': ''
        })

    combined_blank = pd.concat([
        terminal[terminal['blank_jockey_flag_v1'] == 'YES'],
        runner_board[runner_board['blank_jockey_flag_v1'] == 'YES']
    ], ignore_index=True)

    if not combined_blank.empty:
        grouped = (
            combined_blank
            .groupby(['source_file_v1', 'meeting_date', 'state', 'track', 'race_no', 'source_url'], dropna=False)
            .size()
            .reset_index(name='blank_rows')
            .sort_values(['blank_rows', 'meeting_date', 'track', 'race_no'], ascending=[False, True, True, True])
        )
        for _, row in grouped.iterrows():
            summary_rows.append({
                'section': 'BY_TRACK_RACE_SOURCE',
                'metric': 'blank_rows',
                'value': int(row['blank_rows']),
                'source_file': row['source_file_v1'],
                'track': f"{row['meeting_date']}|{row['state']}|{row['track']}",
                'race_no': row['race_no'],
                'source_url': row['source_url'],
            })

    pd.DataFrame(summary_rows).to_csv(OUT_SUMMARY, index=False)

    print('[BLANK_JOCKEY_SOURCE_AUDIT_V1] COMPLETE')
    print(f'terminal_blank_rows={int((terminal["blank_jockey_flag_v1"] == "YES").sum())}')
    print(f'runner_board_blank_rows={int((runner_board["blank_jockey_flag_v1"] == "YES").sum())}')
    print(f'blank_join_keys_both={len(upstream_blank_join_keys & downstream_blank_join_keys)}')
    print(f'blank_join_keys_upstream_only={len(upstream_blank_join_keys - downstream_blank_join_keys)}')
    print(f'blank_join_keys_downstream_only={len(downstream_blank_join_keys - upstream_blank_join_keys)}')
    print(f'wrote={OUT}')
    print(f'wrote={OUT_SUMMARY}')


if __name__ == '__main__':
    main()
