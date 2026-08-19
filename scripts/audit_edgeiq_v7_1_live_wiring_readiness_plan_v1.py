import csv
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
OUT = DATA / 'edgeiq_v7_1_live_wiring_readiness_plan_v1.csv'
OUT_SUMMARY = DATA / 'edgeiq_v7_1_live_wiring_readiness_plan_v1_summary.csv'
OUT_REPORT = DATA / 'edgeiq_v7_1_live_wiring_readiness_plan_v1_report.txt'

FILES = [
    DATA / 'edgeiq_live_runner_board_v1.csv',
    DATA / 'edgeiq_live_runner_board_governed_v1.csv',
    DATA / 'edgeiq_live_terminal_feed_v1.csv',
    DATA / 'edgeiq_vic_live_terminal_feed_v1.csv',
    DATA / 'edgeiq_live_horse_profile_current.csv',
    DATA / 'edgeiq_horse_intelligence_drawer_current.csv',
    ROOT / 'src' / 'components' / 'RaceIntelligenceScreen.tsx',
    DATA / 'edgeiq_fair_price_engine_v7_1_candidate.csv',
    DATA / 'edgeiq_probability_engine_v7.csv',
]
KEY_TERMS = ['race_date', 'current_race_date', 'track', 'race_no', 'race_number', 'horse', 'horse_key']
PROB_TERMS = ['probability', 'prob', 'win_pct']
FAIR_TERMS = ['fair_price', 'rated_price']
LIVE_TERMS = ['live_price', 'tab_fixed_win', 'display_live_price', 'market_price']
DISPLAY_TERMS = ['display', 'ui_']
MARKET_TERMS = ['market', 'tab_', 'sp_price']


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def csv_header_and_count(path):
    if not path.exists():
        return [], 0
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return [], 0
        count = sum(1 for _ in reader)
    return header, count


def matching_columns(cols, terms):
    found = []
    for col in cols:
        low = col.lower()
        if any(term in low for term in terms):
            found.append(col)
    return ';'.join(found)


def inspect_csv(path):
    cols, row_count = csv_header_and_count(path)
    low_name = path.name.lower()
    if 'v7_1_candidate' in low_name:
        action = 'future source for display fair price join; do not live-wire yet'
    elif 'probability_engine_v7' in low_name:
        action = 'future source for calibrated V7 probability join; preserve separately from display price'
    elif 'live_runner_board' in low_name:
        action = 'future primary live-board join target after backup and feature flag approval'
    elif 'terminal_feed' in low_name:
        action = 'future downstream feed audit target only after live-board join is approved'
    else:
        action = 'inspect as downstream context; no modification now'
    return {
        'file': str(path.relative_to(ROOT)),
        'exists': 'YES',
        'file_type': 'CSV',
        'row_count': row_count,
        'column_count': len(cols),
        'key_columns_found': matching_columns(cols, KEY_TERMS),
        'probability_columns_found': matching_columns(cols, PROB_TERMS),
        'fair_price_columns_found': matching_columns(cols, FAIR_TERMS),
        'live_price_columns_found': matching_columns(cols, LIVE_TERMS),
        'display_columns_found': matching_columns(cols, DISPLAY_TERMS),
        'market_columns_found': matching_columns(cols, MARKET_TERMS),
        'contains_fair_price_text': '',
        'contains_display_fair_text': '',
        'contains_live_price_text': '',
        'contains_market_text': '',
        'recommended_action': action,
        'modification_required_future': 'YES' if 'live_runner_board' in low_name or 'terminal_feed' in low_name else 'NO_OR_REVIEW',
        'modified_now': 'NO',
    }


def inspect_tsx(path):
    content = path.read_text(encoding='utf-8', errors='ignore') if path.exists() else ''
    low = content.lower()
    return {
        'file': str(path.relative_to(ROOT)),
        'exists': 'YES',
        'file_type': 'TSX',
        'row_count': '',
        'column_count': '',
        'key_columns_found': '',
        'probability_columns_found': '',
        'fair_price_columns_found': '',
        'live_price_columns_found': '',
        'display_columns_found': '',
        'market_columns_found': '',
        'contains_fair_price_text': 'YES' if 'fair' in low and 'price' in low else 'NO',
        'contains_display_fair_text': 'YES' if 'display_fair' in low or 'display fair' in low else 'NO',
        'contains_live_price_text': 'YES' if 'live_price' in low or 'live price' in low else 'NO',
        'contains_market_text': 'YES' if 'market' in low else 'NO',
        'recommended_action': 'future UI read audit only; do not edit until live-board feature-flag plan is approved',
        'modification_required_future': 'YES_AFTER_APPROVAL',
        'modified_now': 'NO',
    }


def missing_row(path):
    return {
        'file': str(path.relative_to(ROOT)),
        'exists': 'NO',
        'file_type': path.suffix.upper().lstrip('.') or 'UNKNOWN',
        'row_count': '',
        'column_count': '',
        'key_columns_found': '',
        'probability_columns_found': '',
        'fair_price_columns_found': '',
        'live_price_columns_found': '',
        'display_columns_found': '',
        'market_columns_found': '',
        'contains_fair_price_text': '',
        'contains_display_fair_text': '',
        'contains_live_price_text': '',
        'contains_market_text': '',
        'recommended_action': 'file missing; skip unless future wiring plan requires it',
        'modification_required_future': 'NO',
        'modified_now': 'NO',
    }


def main():
    rows = []
    for path in FILES:
        if not path.exists():
            rows.append(missing_row(path))
        elif path.suffix.lower() == '.csv':
            rows.append(inspect_csv(path))
        elif path.suffix.lower() == '.tsx':
            rows.append(inspect_tsx(path))
        else:
            rows.append(missing_row(path))
    fields = list(rows[0].keys())
    write_csv(OUT, rows, fields)

    built_at = datetime.now(timezone.utc).isoformat(timespec='seconds')
    found = [r for r in rows if r['exists'] == 'YES']
    csv_found = [r for r in found if r['file_type'] == 'CSV']
    tsx_found = [r for r in found if r['file_type'] == 'TSX']
    candidate_exists = 'YES' if any(r['file'].endswith('edgeiq_fair_price_engine_v7_1_candidate.csv') and r['exists'] == 'YES' for r in rows) else 'NO'
    prob_exists = 'YES' if any(r['file'].endswith('edgeiq_probability_engine_v7.csv') and r['exists'] == 'YES' for r in rows) else 'NO'
    live_board_exists = 'YES' if any(r['file'].endswith('edgeiq_live_runner_board_v1.csv') and r['exists'] == 'YES' for r in rows) else 'NO'
    terminal_exists = 'YES' if any('terminal_feed' in r['file'] and r['exists'] == 'YES' for r in rows) else 'NO'
    ui_exists = 'YES' if any(r['file'].endswith('RaceIntelligenceScreen.tsx') and r['exists'] == 'YES' for r in rows) else 'NO'
    ready = 'YES' if candidate_exists == 'YES' and prob_exists == 'YES' and live_board_exists == 'YES' else 'NO'
    summary = [
        {'metric': 'built_at', 'value': built_at},
        {'metric': 'files_inspected', 'value': len(rows)},
        {'metric': 'csv_files_found', 'value': len(csv_found)},
        {'metric': 'tsx_files_found', 'value': len(tsx_found)},
        {'metric': 'candidate_exists', 'value': candidate_exists},
        {'metric': 'probability_engine_exists', 'value': prob_exists},
        {'metric': 'current_live_board_exists', 'value': live_board_exists},
        {'metric': 'terminal_feed_exists', 'value': terminal_exists},
        {'metric': 'ui_component_exists', 'value': ui_exists},
        {'metric': 'ready_for_future_wiring_plan', 'value': ready},
        {'metric': 'live_wired_now', 'value': 'NO'},
        {'metric': 'production_changed', 'value': 'NO'},
        {'metric': 'status', 'value': 'V7_1_LIVE_WIRING_READINESS_PLAN_BUILT_NO_CHANGES'},
    ]
    write_csv(OUT_SUMMARY, summary, ['metric', 'value'])

    found_lines = []
    for r in rows:
        found_lines.append(f"- {r['file']}: exists={r['exists']} type={r['file_type']} rows={r['row_count']} action={r['recommended_action']}")
    report = f'''EDGEiQ V7.1 LIVE WIRING READINESS PLAN V1

1. Status
- Planning only.
- No files modified.
- live_wired_now=NO.
- production_changed=NO.
- Status: V7_1_LIVE_WIRING_READINESS_PLAN_BUILT_NO_CHANGES.

2. Candidate artifacts
- V7 probability artifact: public/data/edgeiq_probability_engine_v7.csv exists={prob_exists}.
- V7.1 display candidate: public/data/edgeiq_fair_price_engine_v7_1_candidate.csv exists={candidate_exists}.
- Final checkpoint handoff remains the human-review checkpoint before any live wiring.

3. Current live-feed targets found
{chr(10).join(found_lines)}

4. Recommended future wiring strategy
- Step 1 backup current live runner board and terminal feed.
- Step 2 create a feature-flagged V7.1 join layer.
- Step 3 join V7/V7.1 by normalized race_date/track/race_no/horse.
- Step 4 preserve old fair_price as fallback.
- Step 5 add new fields:
  edgeiq_probability_v7
  edgeiq_fair_price_v7_calibrated
  edgeiq_display_fair_price_v7_1
  edgeiq_price_engine_version
  edgeiq_display_price_engine_version
  edgeiq_v7_1_live_wired_flag
- Step 6 run live board audit.
- Step 7 run UI read audit.
- Step 8 only then update UI labels if approved.

5. Do not execute yet
- No live wiring has occurred.
- No joined live feed has been created.
- No TSX has been edited.
- No terminal feed has been modified.
- No live runner board has been modified.

6. Human approval required before next step
- Human review must approve the V7/V7.1 evidence and this wiring plan before any implementation begins.
- Next implementation should create a separate plan/checkpoint first, not directly modify production feeds.
'''
    OUT_REPORT.write_text(report, encoding='utf-8')
    print(f'Wrote {OUT}')

if __name__ == '__main__':
    main()
