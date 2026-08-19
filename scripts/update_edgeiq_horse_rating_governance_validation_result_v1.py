from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_DIR = ROOT / "docs" / "performance-intelligence" / "horse-performance-rating" / "method-governance"
COMMANDS = DOC_DIR / "edgeiq_horse_rating_governance_validation_commands_v1.csv"
FINAL = DOC_DIR / "EDGEIQ_HORSE_RATING_GOVERNANCE_SOURCE_RECOVERY_FINAL_REPORT_V1.md"

rows = [
    {"command": "python -m py_compile recovery scripts", "status": "PASS", "details": "All four governed recovery scripts compiled."},
    {"command": "npx.cmd tsc -b", "status": "PASS", "details": "TypeScript project compile completed successfully."},
    {"command": "npm run build", "status": "TIMEOUT", "details": "Timed out after 300 seconds without returned error."},
    {"command": "npm run build", "status": "TIMEOUT", "details": "Timed out after 600 seconds without returned error."},
    {"command": "build process cleanup", "status": "PASS", "details": "Stopped only timed-out npm/vite build children; MCP node process left running."},
]
COMMANDS.parent.mkdir(parents=True, exist_ok=True)
with COMMANDS.open('w', encoding='utf-8', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=["command", "status", "details"], lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)

text = FINAL.read_text(encoding='utf-8') if FINAL.exists() else ''
section = """
## Validation Commands

- Python compile: PASS
- TypeScript compile (`npx.cmd tsc -b`): PASS
- `npm run build`: TIMEOUT after 300 seconds and again after 600 seconds; no build error text was returned before timeout.
- Timed-out npm/vite build processes were cleaned up; the MCP node process was left running.

Validation command ledger: `edgeiq_horse_rating_governance_validation_commands_v1.csv`
"""
if "## Validation Commands" not in text:
    text = text.rstrip() + "\n" + section
FINAL.write_text(text, encoding='utf-8')
print('validation_ledger_written=YES')
print('final_report_updated=YES')
