from __future__ import annotations
from pathlib import Path
import json
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
TSX = ROOT / 'src' / 'edgeiq-os' / 'race' / 'components' / 'RaceFormGuideWorkspace.tsx'
CSS = ROOT / 'src' / 'edgeiq-os' / 'styles' / 'edgeiqOsV2.css'
REPORT = ROOT / 'docs' / 'product-specification' / 'FORM_GUIDE_FINAL_RECENT_FORM_APPLY_V2.json'
CHECKS = [('recent_component', 'tsx', 'function RecentForm'), ('recent_columns', 'tsx', 'POSITION IN RUNNING'), ('sectional_columns', 'tsx', 'run.esi800600'), ('sectional_legend', 'tsx', 'data-region="sectional_legend"')]

def main():
    tsx = TSX.read_text(encoding='utf-8') if TSX.exists() else ''
    css = CSS.read_text(encoding='utf-8') if CSS.exists() else ''
    rows = []
    for name, target, needle in CHECKS:
        haystack = tsx if target == 'tsx' else css
        rows.append({'check': name, 'target': target, 'passed': needle in haystack})
    status = 'PASS' if all(row['passed'] for row in rows) else 'FAIL'
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({'status': status, 'timestamp': datetime.now().isoformat(timespec='seconds'), 'checks': rows}, indent=2), encoding='utf-8')
    print(status)
    if status != 'PASS':
        raise SystemExit(1)

if __name__ == '__main__':
    main()
