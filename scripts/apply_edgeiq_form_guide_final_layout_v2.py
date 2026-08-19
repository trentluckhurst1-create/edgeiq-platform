from __future__ import annotations
from pathlib import Path
import json
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
TSX = ROOT / 'src' / 'edgeiq-os' / 'race' / 'components' / 'RaceFormGuideWorkspace.tsx'
CSS = ROOT / 'src' / 'edgeiq-os' / 'styles' / 'edgeiqOsV2.css'
REPORT = ROOT / 'docs' / 'product-specification' / 'FORM_GUIDE_FINAL_LAYOUT_APPLY_V2.json'
CHECKS = [('root_marker', 'tsx', 'data-edgeiq-workspace="form-guide-final-locked"'), ('race_selector_suppressed', 'tsx', 'eiq-form-final-tools'), ('final_css_scope', 'css', 'EDGEIQ FORM GUIDE FINAL LOCKED V2 START')]

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
