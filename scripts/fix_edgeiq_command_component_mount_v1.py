import csv
import shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
TSX = ROOT / 'src' / 'components' / 'RaceIntelligenceScreen.tsx'
CP = ROOT / 'src' / 'components' / 'checkpoints'
REPORT = DATA / 'edgeiq_command_component_mount_fix_report.txt'
DETAIL = DATA / 'edgeiq_command_component_mount_fix_v1.csv'
SUMMARY = DATA / 'edgeiq_command_component_mount_fix_v1_summary.csv'

status = 'COMMAND_COMPONENT_MOUNT_FIXED'
error = ''
backup = ''
changes = []
line_report = {}

try:
    if not TSX.exists():
        raise FileNotFoundError(TSX)
    CP.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = CP / f'RaceIntelligenceScreen_BEFORE_COMMAND_COMPONENT_MOUNT_FIX_{stamp}.tsx'
    shutil.copy2(TSX, backup_path)
    backup = str(backup_path)

    text = TSX.read_text(encoding='utf-8')
    original = text

    market_start = text.find('              <section style={{ border: "1px solid rgba(80,120,180,.28)", borderRadius: 12, padding: 12, background: "rgba(8,15,28,.74)" }}>\n                <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center", marginBottom: 10 }}>\n                  <strong style={{ color: "#f8fafc", fontSize: 13, textTransform: "uppercase", letterSpacing: ".08em" }}>Market Command</strong>')
    key_marker = '              {/* Key Questions */}\n'
    key_start = text.find(key_marker)
    if market_start == -1:
        raise RuntimeError('Market Command block not found')
    if key_start == -1:
        raise RuntimeError('Key Questions marker not found')
    if market_start > key_start:
        status = 'COMMAND_COMPONENT_ALREADY_RENDERING_BELOW_FOLD'
        changes.append('market_block_already_after_key_questions')
    else:
        panel_block = text[market_start:key_start]
        text = text[:market_start] + text[key_start:]
        changes.append('removed_panel_block_from_above_key_questions')

        key_start2 = text.find(key_marker)
        if key_start2 == -1:
            raise RuntimeError('Key Questions marker lost after removal')
        # Find the end of the Key Questions section by locating the next section close before the command wrapper close.
        search_from = key_start2
        section_end_marker = '              </section>\n\n'
        key_end = text.find(section_end_marker, search_from)
        if key_end == -1:
            raise RuntimeError('Could not find Key Questions section end')
        key_end += len(section_end_marker)

        evidence_footer = '''              <section style={{ border: "1px solid rgba(80,120,180,.24)", borderRadius: 12, padding: 10, background: "rgba(5,12,22,.68)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center", marginBottom: 8 }}>
                  <strong style={{ color: "#f8fafc", fontSize: 12, textTransform: "uppercase", letterSpacing: ".08em" }}>Evidence Footer</strong>
                  <span style={{ color: "#94a3b8", fontSize: 10.5, fontWeight: 900 }}>current race coverage</span>
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>
                  {[
                    { label: "Pace Map", count: paceCoverageCount },
                    { label: "DNA", count: dnaCoverageCount },
                    { label: "Hidden Gem", count: hiddenGemCoverageCount },
                    { label: "Campaign", count: campaignCoverageCount },
                    { label: "Connections", count: connectionsCoverageCount },
                    { label: "History", count: historyCoverageCount },
                    { label: "Trajectory", count: coverageCount((row) => hasEvidenceText(firstText(row.item.runnerTrajectory, ["trajectory_direction"], "")) || firstNum(row.item.runnerTrajectory, ["trajectory_score"]) !== null) },
                    { label: "Market", count: marketCoverageCount },
                    { label: "EDGEiQ Price", count: coverageCount((row) => fairPrice(row.item.row, row.item.bet) !== null) },
                  ].map((entry) => (
                    <span key={`command-evidence-footer-${entry.label}`} style={{ border: "1px solid rgba(125,211,252,.18)", borderRadius: 999, padding: "5px 8px", color: "#cbd5e1", background: "rgba(15,23,42,.72)", fontSize: 10.5, fontWeight: 900 }}>
                      {entry.label} {entry.count}/{factorFieldSize}
                    </span>
                  ))}
                </div>
              </section>

'''
        text = text[:key_end] + panel_block + evidence_footer + text[key_end:]
        changes.append('inserted_panels_below_key_questions')
        changes.append('inserted_explicit_evidence_footer_below_score_breakdown')

    if text != original:
        TSX.write_text(text, encoding='utf-8')

    final_lines = TSX.read_text(encoding='utf-8', errors='replace').splitlines()
    def find_line(options):
        for i, line in enumerate(final_lines, start=1):
            if any(opt in line for opt in options):
                return i
        return ''
    line_report = {
        'key_questions_line': find_line(['>Key Questions<', '>Key Questions</strong>']),
        'market_command_line': find_line(['>Market Command<', '>MARKET COMMAND<']),
        'connection_command_line': find_line(['>Connection Command<', '>CONNECTION COMMAND<']),
        'score_breakdown_line': find_line(['>EDGEiQ Score Breakdown<', '>EDGEIQ SCORE BREAKDOWN<']),
        'evidence_footer_line': find_line(['>Evidence Footer<', '>EVIDENCE FOOTER<']),
    }
except Exception as exc:
    status = 'BLOCKED'
    error = str(exc)

row = {
    'status': status,
    'generated_at': datetime.now().isoformat(timespec='seconds'),
    'checkpoint_file': backup,
    'changes': '|'.join(changes),
    'error': error,
    **line_report,
}
for path in [DETAIL, SUMMARY]:
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        w.writeheader(); w.writerow(row)

report = []
report.append('EDGEiQ Command Component Mount Fix V1')
report.append('=' * 44)
report.append(f'Status: {status}')
report.append(f'Generated: {row["generated_at"]}')
report.append(f'Checkpoint: {backup}')
report.append(f'Changes: {row["changes"] or "None"}')
report.append(f'Error: {error or "None"}')
report.append('')
report.append('Rendered line numbers after fix:')
for key in ['key_questions_line','market_command_line','connection_command_line','score_breakdown_line','evidence_footer_line']:
    report.append(f'- {key}: {row.get(key, "") or "NOT FOUND"}')
REPORT.write_text('\n'.join(report) + '\n', encoding='utf-8')

print(status)
print('changes', row['changes'])
print('lines', {k: row.get(k,'') for k in ['key_questions_line','market_command_line','connection_command_line','score_breakdown_line','evidence_footer_line']})
if error:
    print('error', error)
