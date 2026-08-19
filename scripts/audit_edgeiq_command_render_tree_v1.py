import csv
import re
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
TSX = ROOT / 'src' / 'components' / 'RaceIntelligenceScreen.tsx'
REPORT = DATA / 'edgeiq_command_render_tree_v1_report.txt'
DETAIL = DATA / 'edgeiq_command_render_tree_v1.csv'
SUMMARY = DATA / 'edgeiq_command_render_tree_v1_summary.csv'

terms = [
    'intelMode === "COMMAND"',
    'activeWorkspace === "COMMAND"',
    'COMMAND workspace',
    'Race Control Room',
    'Horse Profiles of Interest',
    'Race Shape Command',
    'Key Questions',
    'Market Command',
    'MARKET COMMAND',
    'Connection Command',
    'CONNECTION COMMAND',
    'EDGEiQ Score Breakdown',
    'EDGEIQ SCORE BREAKDOWN',
    'Evidence Footer',
    'factorCoverageTiles',
]

text = TSX.read_text(encoding='utf-8', errors='replace') if TSX.exists() else ''
lines = text.splitlines()
rows = []
for i, line in enumerate(lines, start=1):
    stripped = line.strip()
    hits = [t for t in terms if t in line]
    if hits or re.search(r'\breturn\b\s*\(?', line):
        branch_context = []
        window_start = max(1, i - 12)
        window_end = min(len(lines), i + 12)
        window = '\n'.join(lines[window_start-1:window_end])
        if 'intelMode === "COMMAND"' in window:
            branch_context.append('NEAR_INTELMODE_COMMAND')
        if 'activeWorkspace === "COMMAND"' in window:
            branch_context.append('NEAR_ACTIVEWORKSPACE_COMMAND')
        if 'return (' in line or re.search(r'\breturn\b', line):
            branch_context.append('RETURN_STATEMENT')
        rows.append({
            'line_number': i,
            'matched_terms': '|'.join(hits) if hits else 'RETURN',
            'branch_context': '|'.join(branch_context),
            'code': stripped[:500],
        })

def find_lines(needle_options):
    out = []
    for i, line in enumerate(lines, start=1):
        if any(n in line for n in needle_options):
            out.append(i)
    return out

command_branch_lines = find_lines(['intelMode === "COMMAND"', 'activeWorkspace === "COMMAND"'])
key_question_lines = find_lines(['Key Questions'])
market_lines = find_lines(['Market Command', 'MARKET COMMAND'])
connection_lines = find_lines(['Connection Command', 'CONNECTION COMMAND'])
score_lines = find_lines(['EDGEiQ Score Breakdown', 'EDGEIQ SCORE BREAKDOWN'])
footer_lines = find_lines(['Evidence Footer', 'factorCoverageTiles'])
race_shape_lines = find_lines(['Race Shape Command'])
horse_profile_lines = find_lines(['Horse Profiles of Interest'])
race_control_lines = find_lines(['Race Control Room'])

# Determine relative mount order inside source.
components_exist = bool(market_lines and connection_lines and score_lines)
footer_exists = bool(footer_lines)
key_exists = bool(key_question_lines)
likely_below_fold = False
mount_issue = 'UNKNOWN'
if components_exist and key_exists:
    first_key = min(key_question_lines)
    first_market = min(market_lines)
    first_conn = min(connection_lines)
    first_score = min(score_lines)
    first_footer = min(footer_lines) if footer_lines else None
    if first_market < first_key or first_conn < first_key or first_score < first_key:
        mount_issue = 'PANELS_RENDER_BEFORE_KEY_QUESTIONS'
    elif first_footer and (first_market > first_footer or first_conn > first_footer or first_score > first_footer):
        mount_issue = 'PANELS_RENDER_AFTER_FOOTER'
    else:
        mount_issue = 'PANELS_EXIST_IN_EXPECTED_SOURCE_ORDER_OR_BELOW_FOLD'
        likely_below_fold = True
else:
    mount_issue = 'PANELS_MISSING_FROM_JSX'

status = 'COMMAND_RENDER_TREE_AUDIT_COMPLETE' if TSX.exists() else 'BLOCKED_TSX_MISSING'
summary = [{
    'status': status,
    'generated_at': datetime.now().isoformat(timespec='seconds'),
    'tsx_exists': 'YES' if TSX.exists() else 'NO',
    'command_branch_lines': '|'.join(map(str, command_branch_lines)),
    'return_statement_count': sum(1 for r in rows if r['matched_terms'] == 'RETURN'),
    'race_control_lines': '|'.join(map(str, race_control_lines)),
    'horse_profiles_lines': '|'.join(map(str, horse_profile_lines)),
    'race_shape_lines': '|'.join(map(str, race_shape_lines)),
    'key_questions_lines': '|'.join(map(str, key_question_lines)),
    'market_command_lines': '|'.join(map(str, market_lines)),
    'connection_command_lines': '|'.join(map(str, connection_lines)),
    'score_breakdown_lines': '|'.join(map(str, score_lines)),
    'evidence_footer_lines': '|'.join(map(str, footer_lines)),
    'components_exist_in_jsx': 'YES' if components_exist else 'NO',
    'evidence_footer_exists': 'YES' if footer_exists else 'NO',
    'likely_below_fold': 'YES' if likely_below_fold else 'NO',
    'mount_issue': mount_issue,
    'recommended_action': 'RUN_MOUNT_FIX_AFTER_KEY_QUESTIONS' if mount_issue != 'PANELS_EXIST_IN_EXPECTED_SOURCE_ORDER_OR_BELOW_FOLD' or not footer_exists else 'REPORT_ALREADY_RENDERING_BELOW_FOLD_OR_CSS_VISIBILITY',
}]

with DETAIL.open('w', newline='', encoding='utf-8') as f:
    fields = list(rows[0].keys()) if rows else ['line_number','matched_terms','branch_context','code']
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader(); w.writerows(rows)
with SUMMARY.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
    w.writeheader(); w.writerows(summary)

report = []
report.append('EDGEiQ Command Render Tree Audit V1')
report.append('=' * 44)
report.append(f'Status: {status}')
report.append(f'Generated: {summary[0]["generated_at"]}')
report.append('')
report.append(f'COMMAND branch lines: {summary[0]["command_branch_lines"] or "NONE"}')
report.append(f'Return statements found: {summary[0]["return_statement_count"]}')
report.append('')
report.append('Known COMMAND sections:')
report.append(f'- Race Control Room lines: {summary[0]["race_control_lines"] or "NONE"}')
report.append(f'- Horse Profiles of Interest lines: {summary[0]["horse_profiles_lines"] or "NONE"}')
report.append(f'- Race Shape Command lines: {summary[0]["race_shape_lines"] or "NONE"}')
report.append(f'- Key Questions lines: {summary[0]["key_questions_lines"] or "NONE"}')
report.append('')
report.append('Requested enrichment sections:')
report.append(f'- MARKET COMMAND lines: {summary[0]["market_command_lines"] or "NONE"}')
report.append(f'- CONNECTION COMMAND lines: {summary[0]["connection_command_lines"] or "NONE"}')
report.append(f'- EDGEIQ SCORE BREAKDOWN lines: {summary[0]["score_breakdown_lines"] or "NONE"}')
report.append(f'- EVIDENCE FOOTER / factorCoverageTiles lines: {summary[0]["evidence_footer_lines"] or "NONE"}')
report.append('')
report.append(f'Components exist in JSX: {summary[0]["components_exist_in_jsx"]}')
report.append(f'Evidence footer exists: {summary[0]["evidence_footer_exists"]}')
report.append(f'Likely below fold: {summary[0]["likely_below_fold"]}')
report.append(f'Mount issue: {mount_issue}')
report.append(f'Recommended action: {summary[0]["recommended_action"]}')
REPORT.write_text('\n'.join(report) + '\n', encoding='utf-8')
print(status)
print('mount_issue', mount_issue)
print('market_lines', summary[0]['market_command_lines'] or 'NONE')
print('connection_lines', summary[0]['connection_command_lines'] or 'NONE')
print('score_lines', summary[0]['score_breakdown_lines'] or 'NONE')
print('footer_lines', summary[0]['evidence_footer_lines'] or 'NONE')
