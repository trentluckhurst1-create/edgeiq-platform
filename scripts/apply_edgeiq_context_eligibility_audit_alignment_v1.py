from __future__ import annotations
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'scripts' / 'audit_edgeiq_race_entry_context_eligibility_fact_v1.py'
CHECKPOINT = ROOT / 'docs' / 'victoria-performance-intelligence-race-context-authority-v1' / 'checkpoints' / 'audit_edgeiq_race_entry_context_eligibility_fact_v1_PRE_CURRENT_ELIGIBILITY_AUDIT_ALIGNMENT.py'
CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
if not CHECKPOINT.exists():
    shutil.copy2(TARGET, CHECKPOINT)
text = TARGET.read_text(encoding='utf-8')
start = text.index('    current_population_expected = (\n        len(source_rows) == 0')
end = text.index('    failed_checks = [', start)
new = '''    check(
        "current_population_expected",
        len(fact_rows) == len(source_rows),
        {
            "source_context_rows": len(source_rows),
            "eligibility_rows": len(fact_rows),
            "complete_context_eligible_rows": eligible_rows,
            "complete_context_ineligible_rows": ineligible_rows,
        },
    )

'''
text = text[:start] + new + text[end:]
text = text.replace('"audit_version": "1.0.0"', '"audit_version": "1.1.0_current_context_rows_allowed"')
TARGET.write_text(text, encoding='utf-8')
print('EDGEIQ_CONTEXT_ELIGIBILITY_AUDIT_ALIGNMENT_APPLIED')
print(f'checkpoint={CHECKPOINT}')
print(f'target={TARGET}')
