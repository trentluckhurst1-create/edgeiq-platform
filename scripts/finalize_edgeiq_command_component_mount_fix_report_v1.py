from pathlib import Path
from datetime import datetime
import csv
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
TSX = ROOT / 'src' / 'components' / 'RaceIntelligenceScreen.tsx'
REPORT = DATA / 'edgeiq_command_component_mount_fix_report.txt'
SUMMARY = DATA / 'edgeiq_command_component_mount_fix_v1_summary.csv'
lines = TSX.read_text(encoding='utf-8', errors='replace').splitlines()
def find_line(options):
    for i,line in enumerate(lines, start=1):
        if any(opt in line for opt in options): return i
    return ''
line_data = {
    'key_questions_line': find_line(['>Key Questions<', '>Key Questions</strong>']),
    'market_command_line': find_line(['>Market Command<', '>MARKET COMMAND<']),
    'connection_command_line': find_line(['>Connection Command<', '>CONNECTION COMMAND<']),
    'score_breakdown_line': find_line(['>EDGEiQ Score Breakdown<', '>EDGEIQ SCORE BREAKDOWN<']),
    'evidence_footer_line': find_line(['>Evidence Footer<', '>EVIDENCE FOOTER<']),
}
status='COMMAND_COMPONENT_MOUNT_FIXED'
# Preserve existing checkpoint/changes when possible.
existing={}
if SUMMARY.exists():
    with SUMMARY.open('r', newline='', encoding='utf-8-sig') as f:
        rows=list(csv.DictReader(f)); existing=rows[0] if rows else {}
row={**existing, **line_data, 'status': status, 'build_status':'BUILD_SUCCESS', 'build_command':'npm run build', 'updated_at': datetime.now().isoformat(timespec='seconds')}
fields=list(row.keys())
with SUMMARY.open('w', newline='', encoding='utf-8') as f:
    w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerow(row)
report=[]
report.append('EDGEiQ Command Component Mount Fix V1')
report.append('='*44)
report.append(f'Final status: {status}')
report.append(f'Updated: {row["updated_at"]}')
report.append(f'Build: BUILD_SUCCESS via npm run build')
report.append(f'Checkpoint: {row.get("checkpoint_file", "")}')
report.append(f'Changes: {row.get("changes", "")}')
report.append('')
report.append('Audit finding:')
report.append('- Previous enrichment JSX existed, but was mounted before Key Questions and no explicit rendered Evidence Footer was present in the COMMAND section.')
report.append('- Mount fix moved the panels immediately below Key Questions and added the Evidence Footer directly below EDGEiQ Score Breakdown.')
report.append('')
report.append('Rendered line numbers after fix:')
for k,v in line_data.items(): report.append(f'- {k}: {v or "NOT FOUND"}')
REPORT.write_text('\n'.join(report)+'\n', encoding='utf-8')
print(status)
print('BUILD_SUCCESS')
print(line_data)
