import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
TSX = ROOT / 'src' / 'components' / 'RaceIntelligenceScreen.tsx'
GOV = DATA / 'edgeiq_live_runner_board_governed_v1.csv'
CMD = DATA / 'edgeiq_command_enrichment_feed_v3.csv'
OUT = DATA / 'edgeiq_command_final_integrity_audit_v1.csv'
RACE = DATA / 'edgeiq_command_final_integrity_race_summary_v1.csv'
REPORT = DATA / 'edgeiq_command_final_integrity_report_v1.txt'

FIX_CLASSES = {'JOIN_FAILED', 'FIELD_NAME_MISMATCH', 'UI_FALLBACK_MISSING', 'FEED_FAILURE'}
SECTION_NAMES = [
    'Intelligence Brief', 'Horse Profiles of Interest', 'Race Shape Command', 'Key Questions',
    'Market Command', 'Connection Command', 'EDGEiQ Score Breakdown', 'Evidence Footer'
]
EVIDENCE_NAMES = [
    'Prices', 'Pace', 'DNA', 'Connections', 'Scores', 'Market', 'Hidden Gem',
    'Campaign', 'History', 'Trajectory'
]


def read_csv(path):
    if not path.exists():
        return [], []
    with path.open('r', newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def clean(value):
    return ' '.join(str(value or '').strip().upper().replace('\u00a0', ' ').split())


def clean_horse(value):
    return ''.join(ch for ch in clean(value) if ch.isalnum())


def race_no(value):
    raw = clean(value).replace('RACE ', '').replace('R', '')
    return raw.lstrip('0') or raw


def runner_key(row):
    return (
        clean(row.get('race_date') or row.get('current_race_date')),
        clean(row.get('track')),
        race_no(row.get('race_no')),
        clean_horse(row.get('horse') or row.get('horse_key')),
    )


def race_key(row):
    return runner_key(row)[:3]


def yes(value):
    return clean(value) in {'YES', 'TRUE', '1', 'Y', 'ON'}


def populated(value):
    return str(value or '').strip() not in {'', '-', '--', 'N/A', 'NA', 'NULL'}


def non_zero(value):
    return str(value or '').strip() not in {'', '-', '--', 'N/A', 'NA', 'NULL', '0', '0.0', '0.00'}


def status(ok, missing_class, reason_ok, reason_missing):
    if ok:
        return 'OK', reason_ok
    return missing_class, reason_missing


def feed_status(joined, ok, missing_class, ok_reason, missing_reason):
    if not joined:
        return 'JOIN_FAILED', 'Runner exists in governed board but not in COMMAND V3 feed.'
    return status(ok, missing_class, ok_reason, missing_reason)


def section_status(race_metrics, section):
    field_size = race_metrics['field_size']
    if section == 'Intelligence Brief':
        ok = race_metrics['market_ok'] > 0 and race_metrics['pace_ok'] > 0
        return ('OK', 'Race has market and pace context for the brief.') if ok else ('FEED_FAILURE', 'Brief lacks both required race-level context families.')
    if section == 'Horse Profiles of Interest':
        ok = race_metrics['score_ok'] > 0 or race_metrics['connection_ok'] > 0 or race_metrics['trajectory_ok'] > 0 or race_metrics['campaign_ok'] > 0
        return ('OK', 'At least one profile evidence family is available for the race.') if ok else ('FEED_FAILURE', 'No profile evidence families are available for the race.')
    if section == 'Race Shape Command':
        ok = race_metrics['pace_ok'] == field_size
        return ('OK', 'Pace/run-style coverage is available for the full race.') if ok else ('FEED_FAILURE', 'Race shape is missing pace/run-style coverage.')
    if section == 'Key Questions':
        ok = race_metrics['market_ok'] > 0 and race_metrics['pace_ok'] > 0
        return ('OK', 'Race has enough market and pace context for key questions.') if ok else ('FEED_FAILURE', 'Key questions lack market or pace context.')
    if section == 'Market Command':
        ok = race_metrics['market_ok'] > 0
        return ('OK', 'Market command has current market evidence.') if ok else ('TRUE_ZERO', 'No actionable market evidence is currently triggered for this race.')
    if section == 'Connection Command':
        ok = race_metrics['connection_ok'] > 0 or race_metrics['connection_true_zero'] == field_size
        return ('OK', 'Connection command has evidence or a proven no-angle state.') if ok else ('FEED_FAILURE', 'Connection command lacks evidence and lacks a proven no-angle state.')
    if section == 'EDGEiQ Score Breakdown':
        ok = race_metrics['score_ok'] > 0
        return ('OK', 'Score breakdown has score evidence for at least one runner and can suppress proven gaps.') if ok else ('FEED_FAILURE', 'Score breakdown has no score evidence for the race.')
    if section == 'Evidence Footer':
        required = {'race_connection_available_count_v3', 'race_market_available_count_v3', 'race_field_size_v3', 'race_edgeiq_price_available_count_v3_1', 'race_trajectory_available_count_v3_2', 'race_campaign_available_count_v3_3'}
        missing = sorted(required - race_metrics['command_fields'])
        return ('OK', 'Footer count fields exist in COMMAND feed.') if not missing else ('FIELD_NAME_MISMATCH', 'Missing footer count fields: ' + ', '.join(missing))
    return 'OK', 'Section audited.'


gov, gov_fields = read_csv(GOV)
cmd, cmd_fields = read_csv(CMD)
cmd_by_key = {runner_key(row): row for row in cmd}
cmd_fields_set = set(cmd_fields)
tsx_text = TSX.read_text(encoding='utf-8') if TSX.exists() else ''
ui_labels = {
    'Market Command': 'MARKET COMMAND',
    'Connection Command': 'CONNECTION COMMAND',
    'EDGEiQ Score Breakdown': 'EDGEIQ SCORE BREAKDOWN',
    'Evidence Footer': 'EVIDENCE FOOTER',
    'Race Shape Command': 'RACE SHAPE COMMAND',
    'Key Questions': 'KEY QUESTIONS',
    'Horse Profiles of Interest': 'HORSE PROFILES OF INTEREST',
}
ui_label_presence = {name: (label in tsx_text.upper()) for name, label in ui_labels.items()}
ui_fallback_ok = all(ui_label_presence.values())

rows = []
race_members = defaultdict(list)
for governed in gov:
    rk = race_key(governed)
    race_members[rk].append(governed)

# First build runner-level evidence classifications.
for governed in gov:
    key = runner_key(governed)
    command = cmd_by_key.get(key, {})
    joined = bool(command)

    price_ok = populated(command.get('edgeiq_active_display_fair_price') or governed.get('edgeiq_active_display_fair_price_shadow') or governed.get('display_fair_price') or governed.get('ui_fair_price') or governed.get('fair_price'))
    price_truth = clean(command.get('edgeiq_price_truth_status_v3_1'))
    if price_truth == 'SCRATCHED_PRICE_SUPPRESSED':
        price_missing = 'TRUE_ZERO'; price_reason = 'Price intentionally suppressed for scratched/non-priced runner.'
    elif price_truth == 'EDGEIQ_PRICE_SOURCE_MISSING':
        price_missing = 'SOURCE_MISSING'; price_reason = 'No EDGEiQ price source exists for this runner.'
    else:
        price_missing = 'SOURCE_MISSING'; price_reason = 'No populated price field found.'

    pace_ok = populated(governed.get('early_speed_band')) or non_zero(governed.get('early_speed_rating')) or populated(governed.get('run_style')) or populated(governed.get('speed_map_bucket'))
    dna_ok = populated(governed.get('runner_dna_v6_2_score')) or populated(command.get('edgeiq_score_overall_v3')) or populated(governed.get('total_rating_points')) or populated(governed.get('projected_rating_v5_2'))
    connection_ok = yes(command.get('edgeiq_connection_evidence_available_v3'))
    connection_truth = clean(command.get('edgeiq_connection_truth_status_v3'))
    connection_missing = 'SOURCE_MISSING' if connection_truth == 'SOURCE_MISSING_OR_JOIN_FAILED' else 'TRUE_ZERO'
    connection_reason = 'No trainer, jockey or combination angle currently triggered.' if connection_missing == 'TRUE_ZERO' else 'Connection source missing or unmatched.'
    score_ok = populated(command.get('edgeiq_score_overall_v3'))
    market_ok = yes(command.get('edgeiq_market_evidence_available_v3'))
    hidden_ok = yes(command.get('edgeiq_hidden_gem_evidence_available_v3'))
    hidden_truth = clean(command.get('edgeiq_hidden_gem_truth_status_v3'))
    hidden_missing = 'SOURCE_MISSING' if hidden_truth == 'HIDDEN_GEM_SOURCE_MISSING_OR_JOIN_FAILED' else 'TRUE_ZERO'
    hidden_reason = 'No actionable hidden-gem signal currently triggered.' if hidden_missing == 'TRUE_ZERO' else 'Hidden-gem source missing or unmatched.'
    campaign_ok = yes(command.get('edgeiq_campaign_available_v3_3'))
    campaign_truth = clean(command.get('edgeiq_campaign_truth_status_v3_3'))
    campaign_missing = 'SOURCE_MISSING' if campaign_truth in {'CAMPAIGN_SOURCE_MISSING', 'CAMPAIGN_SOURCE_MISSING_OR_JOIN_FAILED'} else 'TRUE_ZERO'
    campaign_reason = 'Limited/no campaign history available.' if campaign_missing == 'TRUE_ZERO' else 'Campaign source missing or unmatched.'
    trajectory_ok = yes(command.get('edgeiq_trajectory_available_v3_2'))
    trajectory_truth = clean(command.get('edgeiq_trajectory_truth_status_v3_2'))
    trajectory_missing = 'TRUE_ZERO' if trajectory_truth == 'TRUE_ZERO_NO_TRAJECTORY_HISTORY' else 'SOURCE_MISSING'
    trajectory_reason = 'No historical trajectory available for this runner.' if trajectory_missing == 'TRUE_ZERO' else 'Trajectory source missing or unmatched.'
    history_ok = trajectory_ok
    history_missing = trajectory_missing
    history_reason = 'History represented by trajectory feed; no historical starts found.' if history_missing == 'TRUE_ZERO' else 'History represented by trajectory feed; source missing or unmatched.'

    evidence_defs = {
        'Prices': feed_status(joined, price_ok, price_missing, 'EDGEiQ display price is populated.', price_reason),
        'Pace': feed_status(joined, pace_ok, 'SOURCE_MISSING', 'Pace/run-style field is populated.', 'No pace/run-style source field is populated.'),
        'DNA': feed_status(joined, dna_ok, 'SOURCE_MISSING', 'DNA/rating proxy is populated.', 'No DNA/rating proxy is populated.'),
        'Connections': feed_status(joined, connection_ok, connection_missing, 'Connection evidence is available.', connection_reason),
        'Scores': feed_status(joined, score_ok, 'TRUE_ZERO', 'Overall score is populated.', 'No score was produced for this runner.'),
        'Market': feed_status(joined, market_ok, 'SOURCE_MISSING', 'Market evidence is available.', 'Market source missing or unmatched.'),
        'Hidden Gem': feed_status(joined, hidden_ok, hidden_missing, 'Hidden-gem evidence is available.', hidden_reason),
        'Campaign': feed_status(joined, campaign_ok, campaign_missing, 'Campaign evidence is available.', campaign_reason),
        'History': feed_status(joined, history_ok, history_missing, 'History is covered through trajectory feed.', history_reason),
        'Trajectory': feed_status(joined, trajectory_ok, trajectory_missing, 'Trajectory evidence is available.', trajectory_reason),
    }

    row = {
        'race_date': governed.get('race_date', ''),
        'track': governed.get('track', ''),
        'race_no': governed.get('race_no', ''),
        'horse': governed.get('horse', ''),
        'runner_join_status': 'OK' if joined else 'JOIN_FAILED',
    }
    for name, (classification, reason) in evidence_defs.items():
        row[f'{name}_classification'] = classification
        row[f'{name}_reason'] = reason
    rows.append(row)

# Add race-level section classifications to each runner row.
rows_by_race = defaultdict(list)
for row in rows:
    rows_by_race[(clean(row['race_date']), clean(row['track']), race_no(row['race_no']))].append(row)

race_summaries = []
for rk, members in sorted(rows_by_race.items()):
    metrics = {
        'field_size': len(members),
        'command_fields': cmd_fields_set,
        'market_ok': sum(1 for row in members if row['Market_classification'] == 'OK'),
        'pace_ok': sum(1 for row in members if row['Pace_classification'] == 'OK'),
        'score_ok': sum(1 for row in members if row['Scores_classification'] == 'OK'),
        'connection_ok': sum(1 for row in members if row['Connections_classification'] == 'OK'),
        'connection_true_zero': sum(1 for row in members if row['Connections_classification'] == 'TRUE_ZERO'),
        'trajectory_ok': sum(1 for row in members if row['Trajectory_classification'] == 'OK'),
        'campaign_ok': sum(1 for row in members if row['Campaign_classification'] == 'OK'),
    }
    section_results = {name: section_status(metrics, name) for name in SECTION_NAMES}
    for row in members:
        for name, (classification, reason) in section_results.items():
            row[f'{name}_classification'] = classification
            row[f'{name}_reason'] = reason
        row['UI_fallback_classification'] = 'OK' if ui_fallback_ok else 'UI_FALLBACK_MISSING'
        row['UI_fallback_reason'] = 'COMMAND labels are mounted in RaceIntelligenceScreen.tsx.' if ui_fallback_ok else 'Missing COMMAND labels: ' + ', '.join(name for name, present in ui_label_presence.items() if not present)

    race = {'race_date': rk[0], 'track': rk[1], 'race_no': rk[2], 'field_size': len(members)}
    fix_count = 0
    true_zero = 0
    source_missing = 0
    for name in SECTION_NAMES + EVIDENCE_NAMES + ['UI_fallback']:
        col = f'{name}_classification'
        counts = defaultdict(int)
        for row in members:
            counts[row.get(col, '')] += 1
        race[f'{name}_ok_count'] = counts['OK']
        race[f'{name}_true_zero_count'] = counts['TRUE_ZERO']
        race[f'{name}_source_missing_count'] = counts['SOURCE_MISSING']
        race[f'{name}_fix_required_count'] = sum(counts[c] for c in FIX_CLASSES)
        fix_count += race[f'{name}_fix_required_count']
        true_zero += counts['TRUE_ZERO']
        source_missing += counts['SOURCE_MISSING']
    race['fix_required_count'] = fix_count
    race['true_zero_count'] = true_zero
    race['source_missing_count'] = source_missing
    race['status'] = 'FIX_REQUIRED' if fix_count else 'COMMAND_FINAL_VERIFIED_WITH_PROVEN_GAPS'
    race_summaries.append(race)

# Arrange output columns.
base_fields = ['race_date', 'track', 'race_no', 'horse', 'runner_join_status']
section_fields = []
for name in SECTION_NAMES:
    section_fields += [f'{name}_classification', f'{name}_reason']
evidence_fields = []
for name in EVIDENCE_NAMES:
    evidence_fields += [f'{name}_classification', f'{name}_reason']
fields = base_fields + section_fields + evidence_fields + ['UI_fallback_classification', 'UI_fallback_reason']

fix_required = sum(1 for row in rows for name in SECTION_NAMES + EVIDENCE_NAMES + ['UI_fallback'] if row.get(f'{name}_classification') in FIX_CLASSES)
status_text = 'COMMAND_FINAL_INTEGRITY_FIX_REQUIRED' if fix_required else 'COMMAND_FINAL_INTEGRITY_PASS'

write_csv(OUT, rows, fields)
write_csv(RACE, race_summaries, list(race_summaries[0].keys()) if race_summaries else [])

summary_lines = []
for name in SECTION_NAMES + EVIDENCE_NAMES + ['UI_fallback']:
    counts = defaultdict(int)
    for row in rows:
        counts[row.get(f'{name}_classification', '')] += 1
    summary_lines.append(f'{name}: ' + ', '.join(f'{key}={value}' for key, value in sorted(counts.items())))

report_lines = [
    'EDGEiQ Command Final Integrity Audit V1',
    '=' * 46,
    f'Generated: {datetime.now().isoformat(timespec="seconds")}',
    f'Status: {status_text}',
    f'Governed rows/races: {len(gov)}/{len(race_members)}',
    f'COMMAND rows: {len(cmd)}',
    f'Fix-required classifications: {fix_required}',
    f'UI label presence: {ui_label_presence}',
    '',
    'Section/evidence classification counts:',
    *summary_lines,
    '',
    'Race statuses:',
]
report_lines.extend(
    f'{race["track"]} R{race["race_no"]}: {race["status"]}, fix_required={race["fix_required_count"]}, true_zero={race["true_zero_count"]}, source_missing={race["source_missing_count"]}'
    for race in race_summaries
)
REPORT.write_text('\n'.join(report_lines) + '\n', encoding='utf-8')

print(status_text)
print(f'governed_rows={len(gov)}')
print(f'governed_races={len(race_members)}')
print(f'fix_required={fix_required}')
